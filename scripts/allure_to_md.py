#!/usr/bin/env python3
from __future__ import annotations

import argparse
from collections import defaultdict
import json
import os
import re
import textwrap
import datetime as dt
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Tuple, Optional

# --- Config ---
RESULTS_DIR = Path("allure-results")
OUT_PATH = Path("allure-report/report.md")

IMAGE_EXTS = {"png", "jpg", "jpeg", "gif", "svg"}
TEXT_EXTS = {"txt", "log", "md"}
MAX_TEXT_ATTACHMENT_BYTES = 200_000
MAX_TEXT_ATTACHMENT_LINES = 500
ATTACHMENT_SINGLE_WIDTH = "78%"
ATTACHMENT_GRID_WIDTH = "48%"
ATTACHMENT_GRID_COLUMNS = 2
KNOWN_STATUSES = {"PASSED", "FAILED", "BROKEN", "SKIPPED"}


@dataclass
class TestVariant:
    status: str
    duration_ms: int
    full_name: str
    test_case: str
    variant_name: str
    description: str
    attachments: List[str]
    start_ms: Optional[int]
    stop_ms: Optional[int]
    package_name: str
    directory_name: str
    file_name: str


# --- Helpers ---
def relpath_from_out_dir(path: Path) -> str:
    """
    Return a POSIX-style relative path from the markdown output directory
    (OUT_PATH.parent) to the given file. This is what pandoc/Quarto will use
    when resolving image paths in the PDF.
    """
    out_dir = OUT_PATH.parent
    try:
        rel = path.relative_to(out_dir)
        return rel.as_posix()
    except ValueError:
        # General case: compute filesystem relative path
        return os.path.relpath(path, out_dir).replace("\\", "/")

def ms_to_iso(ms: Optional[int]) -> str:
    if ms is None:
        return ""
    try:
        return dt.datetime.fromtimestamp(ms / 1000).isoformat(timespec="seconds")
    except Exception:
        return ""

def read_properties_as_dict(path: Path) -> Dict[str, str]:
    d: Dict[str, str] = {}
    if not path.exists():
        return d
    for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if "=" in line:
            k, v = line.split("=", 1)
            d[k.strip()] = v.strip()
    return d

def remote_to_https_base(remote: str) -> str:
    if not remote:
        return ""
    r = remote.strip().rstrip("/")
    if r.endswith(".git"):
        r = r[:-4]
    m = re.match(r"^git@([^:]+):(.+)$", r)
    if m:
        host, path = m.group(1), m.group(2)
        return f"https://{host}/{path}".rstrip("/")
    m = re.match(r"^https?://([^/]+)/(.+)$", r)
    if m:
        host, path = m.group(1), m.group(2)
        return f"https://{host}/{path}".rstrip("/")
    return ""

def split_owner_repo(base_https: str) -> Tuple[str, str]:
    if not base_https:
        return "", ""
    m = re.match(r"^https?://[^/]+/([^/]+)/([^/]+)$", base_https)
    if not m:
        return "", ""
    return m.group(1), m.group(2)

def is_result_json(path: Path) -> bool:
    return path.suffix == ".json" and path.name.endswith("-result.json")

def read_json_safe(path: Path) -> Optional[dict]:
    try:
        return json.loads(path.read_text(encoding="utf-8", errors="replace"))
    except Exception:
        return None

def labels_as_dict(result: dict) -> Dict[str, str]:
    labels: Dict[str, str] = {}
    for label in result.get("labels", []) or []:
        name = label.get("name")
        value = label.get("value")
        if name and value is not None and name not in labels:
            labels[name] = value
    return labels

def normalize_status(status: Optional[str]) -> str:
    status_u = (status or "unknown").upper()
    return status_u if status_u in KNOWN_STATUSES else "UNKNOWN"

def parse_duration_window(result: dict) -> Tuple[int, Optional[int], Optional[int]]:
    time_obj = result.get("time") or {}
    start_ms = time_obj.get("start", result.get("start"))
    stop_ms = time_obj.get("stop", result.get("stop"))
    duration_ms = time_obj.get("duration", result.get("duration"))

    if (duration_ms is None or duration_ms == 0) and isinstance(start_ms, int) and isinstance(stop_ms, int):
        duration_ms = max(0, stop_ms - start_ms)

    try:
        duration_ms_int = int(duration_ms) if duration_ms is not None else 0
    except Exception:
        duration_ms_int = 0
    return duration_ms_int, start_ms if isinstance(start_ms, int) else None, stop_ms if isinstance(stop_ms, int) else None

def parse_hierarchy(result: dict) -> Tuple[str, str, str, str, str]:
    labels = labels_as_dict(result)
    package_name = labels.get("package") or ""
    full_name = (result.get("fullName") or "").strip()
    raw_name = (result.get("name") or "Unnamed").strip()

    module_name = ""
    test_case = raw_name.split("[", 1)[0] if raw_name else "Unnamed"

    if "#" in full_name:
        module_name, full_name_test = full_name.split("#", 1)
        if full_name_test:
            test_case = full_name_test.strip() or test_case
    elif package_name:
        module_name = package_name
    elif full_name:
        module_name = full_name

    if not package_name:
        package_name = module_name

    module_parts = [part for part in package_name.split(".") if part]
    if not module_parts and module_name:
        module_parts = [part for part in module_name.split(".") if part]

    if module_parts:
        file_stem = module_parts[-1]
        dir_parts = module_parts[:-1]
    else:
        file_stem = "unknown"
        dir_parts = []

    file_name = f"{file_stem}.py"
    directory_name = "/".join(dir_parts) if dir_parts else "."
    variant_name = raw_name or test_case
    return package_name or module_name or file_stem, directory_name, file_name, test_case, variant_name

def empty_stats() -> Dict[str, int]:
    return {
        "total": 0,
        "PASSED": 0,
        "FAILED": 0,
        "BROKEN": 0,
        "SKIPPED": 0,
        "UNKNOWN": 0,
        "duration_ms": 0,
    }

def accumulate_stats(stats: Dict[str, int], status: str, duration_ms: int) -> None:
    stats["total"] += 1
    stats[status] += 1
    stats["duration_ms"] += duration_ms

def format_status_label(status: str) -> str:
    return status[:1] + status[1:].lower() if status else "Unknown"

def format_directory_label(directory_name: str) -> str:
    return "./" if directory_name == "." else f"{directory_name}/"

def format_stats_inline(stats: Dict[str, int]) -> str:
    return (
        f"{stats['total']} total, "
        f"{stats['PASSED']} passed, "
        f"{stats['FAILED']} failed, "
        f"{stats['BROKEN']} broken, "
        f"{stats['SKIPPED']} skipped, "
        f"{stats['duration_ms']} ms"
    )

def build_markdown_table(title: str, headers: List[str], rows: List[List[str]]) -> List[str]:
    lines = [title, ""]
    lines.append("| " + " | ".join(headers) + " |")
    lines.append("| " + " | ".join(["---"] * len(headers)) + " |")
    for row in rows:
        lines.append("| " + " | ".join(row) + " |")
    lines.append("")
    return lines

def render_variant_section(details_lines: List[str], variant: TestVariant) -> None:
    details_lines.append(
        f"##### {format_status_label(variant.status)} -- {variant.variant_name} -- {variant.duration_ms}ms"
    )
    details_lines.append("")
    if variant.description:
        details_lines.append(f"_{variant.description}_")
        details_lines.append("")

    if variant.attachments:
        details_lines.append("Attachments")
        details_lines.append("")
        image_batch: List[Path] = []

        def flush_image_batch() -> None:
            nonlocal image_batch
            if not image_batch:
                return
            details_lines.extend(render_image_attachment_gallery(image_batch))
            image_batch = []

        for src in variant.attachments:
            apath = RESULTS_DIR / src
            ext = apath.suffix.lower().lstrip(".")
            if ext in IMAGE_EXTS:
                image_batch.append(apath)
            elif ext in TEXT_EXTS:
                flush_image_batch()
                details_lines.extend(render_text_attachment(apath))
            else:
                flush_image_batch()
                rel = relpath_from_out_dir(apath)
                details_lines.append(f"- `{rel}`")
        flush_image_batch()
        details_lines.append("")

def collect_all_attachments(result: dict) -> List[str]:
    atts = []
    for a in result.get("attachments", []) or []:
        src = a.get("source")
        if src:
            atts.append(src)
    for step in result.get("steps", []) or []:
        for a in step.get("attachments", []) or []:
            src = a.get("source")
            if src:
                atts.append(src)
    return atts

def render_text_attachment(path: Path) -> List[str]:
    lines: List[str] = ["", "```"]
    try:
        b = path.read_bytes()
        if len(b) > MAX_TEXT_ATTACHMENT_BYTES:
            b = b[:MAX_TEXT_ATTACHMENT_BYTES]
        text = b.decode("utf-8", errors="replace")
        snippet_lines = text.splitlines()
        if len(snippet_lines) > MAX_TEXT_ATTACHMENT_LINES:
            snippet_lines = snippet_lines[:MAX_TEXT_ATTACHMENT_LINES]
            snippet_lines.append("... (truncated) ...")
        lines.extend(snippet_lines)
    except Exception as e:
        lines.append(f"[error reading {path.name}: {e}]")
    lines.append("```")
    lines.append("")
    return lines

def render_image_attachment(path: Path, width: str) -> str:
    rel = relpath_from_out_dir(path)
    # Keep attachment images inline with no filename caption so they can share rows.
    return f"![]({rel}){{width={width}}}"

def render_image_attachment_gallery(paths: List[Path]) -> List[str]:
    if not paths:
        return []
    if len(paths) == 1:
        return [render_image_attachment(paths[0], ATTACHMENT_SINGLE_WIDTH)]

    rows: List[str] = []
    for i in range(0, len(paths), ATTACHMENT_GRID_COLUMNS):
        row_paths = paths[i:i + ATTACHMENT_GRID_COLUMNS]
        row = " ".join(
            render_image_attachment(path, ATTACHMENT_GRID_WIDTH)
            for path in row_paths
        )
        rows.append(row)
    return rows

def build_hierarchical_report(results: List[TestVariant]) -> List[str]:
    grouped: Dict[str, Dict[str, List[TestVariant]]] = defaultdict(lambda: defaultdict(list))
    directory_stats: Dict[str, Dict[str, int]] = defaultdict(empty_stats)
    file_stats: Dict[Tuple[str, str], Dict[str, int]] = defaultdict(empty_stats)

    for result in results:
        grouped[result.directory_name][result.file_name].append(result)
        accumulate_stats(directory_stats[result.directory_name], result.status, result.duration_ms)
        accumulate_stats(file_stats[(result.directory_name, result.file_name)], result.status, result.duration_ms)

    lines: List[str] = ["## Report Overview", ""]

    dir_rows = [
        [
            format_directory_label(directory_name),
            str(stats["total"]),
            str(stats["PASSED"]),
            str(stats["FAILED"]),
            str(stats["BROKEN"]),
            str(stats["SKIPPED"]),
            str(stats["duration_ms"]),
        ]
        for directory_name, stats in sorted(directory_stats.items())
    ]
    lines.extend(
        build_markdown_table(
            "### By Directory",
            ["Directory", "Total", "Passed", "Failed", "Broken", "Skipped", "Duration (ms)"],
            dir_rows,
        )
    )

    file_rows = [
        [
            f"{format_directory_label(directory_name)}{file_name}" if directory_name != "." else file_name,
            str(stats["total"]),
            str(stats["PASSED"]),
            str(stats["FAILED"]),
            str(stats["BROKEN"]),
            str(stats["SKIPPED"]),
            str(stats["duration_ms"]),
        ]
        for (directory_name, file_name), stats in sorted(file_stats.items())
    ]
    lines.extend(
        build_markdown_table(
            "### By File",
            ["File", "Total", "Passed", "Failed", "Broken", "Skipped", "Duration (ms)"],
            file_rows,
        )
    )
    lines.append("\\newpage")
    lines.append("")

    for directory_name in sorted(grouped):
        dir_files = grouped[directory_name]
        dir_label = format_directory_label(directory_name)
        lines.append(f"## Directory: {dir_label}")
        lines.append("")
        lines.append(f"_Summary: {format_stats_inline(directory_stats[directory_name])}_")
        lines.append("")

        for file_name in sorted(dir_files):
            file_results = sorted(dir_files[file_name], key=lambda item: (item.test_case, item.variant_name))
            lines.append(f"### File: {file_name}")
            lines.append("")
            lines.append(f"_Summary: {format_stats_inline(file_stats[(directory_name, file_name)])}_")
            lines.append("")

            test_groups: Dict[str, List[TestVariant]] = defaultdict(list)
            for result in file_results:
                test_groups[result.test_case].append(result)

            for test_case in sorted(test_groups):
                variants = sorted(test_groups[test_case], key=lambda item: item.variant_name)
                test_stats = empty_stats()
                for variant in variants:
                    accumulate_stats(test_stats, variant.status, variant.duration_ms)

                lines.append(f"#### Test Case: {test_case}")
                lines.append("")
                lines.append(f"_Variants: {len(variants)}. Summary: {format_stats_inline(test_stats)}_")
                lines.append("")

                for variant in variants:
                    render_variant_section(lines, variant)

    return lines

def build_front_matter(
    owner: str,
    repo: str,
    branch: str,
    describe: str,
    commit_url: str,
    executor: Optional[dict] = None,
) -> str:
    yml = textwrap.dedent(f"""
    ---
    title: "{owner} / {repo} / {branch} / {describe}"
    abstract: |-
      This report was auto-generated with a custom CI pipeline.
    format:
      pdf:
        pdf-engine: tectonic
        number-sections: true
        shift-heading-level-by: -1
        toc: true
        toc-depth: 2
        fontsize: 11pt
        geometry: margin=1in
    header-includes: |
      \\usepackage[none]{{hyphenat}}
      \\sloppy
      \\usepackage{{tabularx}}
      \\usepackage{{array}}
      \\usepackage{{makecell}}
      \\newcolumntype{{L}}{{>{{\\raggedright\\arraybackslash}}p{{0.32\\textwidth}}}}
      \\newcolumntype{{R}}{{>{{\\raggedleft\\arraybackslash}}X}}
    ---
    """).strip("\n")

    # --- Links under the front matter ---
    commit_section = ""
    if commit_url:
        commit_section += f"\n[Commit URL]({commit_url})  \n\n"

    # Try to add executor link if executor.json is present and has URLs
    if executor:
        exec_name = executor.get("name") or "Executor"
        build_name = executor.get("buildName") or ""
        build_url = executor.get("buildUrl") or ""

        if build_url:
            # e.g. "Executor: GitHub Actions, Run #10"
            label = f"Executor: {exec_name}"
            if build_name:
                label = f"{label}, {build_name}"
            commit_section += f"[{label}]({build_url})\n"

    return yml + "\n" + commit_section + "\\newpage\n"

def build_summary_table(stats: dict, t_start_ms: Optional[int], t_stop_ms: Optional[int]) -> List[str]:
    total = stats.get("total", 0)
    passed = stats.get("PASSED", 0)
    failed = stats.get("FAILED", 0)
    broken = stats.get("BROKEN", 0)
    skipped = stats.get("SKIPPED", 0)
    unknown = stats.get("UNKNOWN", 0)
    duration_ms = stats.get("duration_ms", 0)

    pass_rate = (100.0 * passed / total) if total else 0.0
    start_iso = ms_to_iso(t_start_ms)
    stop_iso = ms_to_iso(t_stop_ms)

    def _tex_escape(s: Optional[str]) -> str:
        """Escape LaTeX special chars for use inside tabular/tabularx."""
        if s is None:
            return "—"
        s = str(s)
        # Order matters: escape backslash first
        replacements = {
            "\\": r"\textbackslash{}",
            "&": r"\&",
            "%": r"\%",
            "$": r"\$",
            "#": r"\#",
            "_": r"\_",
            "{": r"\{",
            "}": r"\}",
            "~": r"\textasciitilde{}",
            "^": r"\textasciicircum{}",
        }
        for old, new in replacements.items():
            s = s.replace(old, new)
        return s

    lines: List[str] = []

    # ======================
    # Execution Summary
    # ======================
    lines.extend([
        "## Execution Summary",
        "",
        "```{=latex}",
        r"\begin{tabularx}{\textwidth}{L R}",
        r"\Xhline{2\arrayrulewidth}",
        r"\textbf{Metric} & \textbf{Value} \\",
        r"\hline",
        rf"Total tests & {total} \\",
        rf"Passed & {passed} \\",
        rf"Failed & {failed} \\",
        rf"Broken & {broken} \\",
        rf"Skipped & {skipped} \\",
        rf"Unknown & {unknown} \\",
        rf"Pass rate & {pass_rate:.1f}\% \\",
        rf"Total duration & {duration_ms} ms \\",
    ])

    if start_iso:
        lines.append(rf"Execution start & {start_iso} \\")
    if stop_iso:
        lines.append(rf"Execution stop & {stop_iso} \\")

    lines.extend([
        r"\Xhline{2\arrayrulewidth}",
        r"\end{tabularx}",
        "```",
        "",
    ])

    # ======================
    # Environment Summary
    # ======================
    props = read_properties_as_dict(RESULTS_DIR / "environment.properties") or {}

    if props:
        lines.extend([
            "## Environment Summary",
            "",
            "```{=latex}",
            r"\begin{tabularx}{\textwidth}{L R}",
            r"\Xhline{2\arrayrulewidth}",
            r"\textbf{Property} & \textbf{Value} \\",
            r"\hline",
        ])

        for k, v in sorted(props.items(), key=lambda kv: str(kv[0]).lower()):
            key_tex = _tex_escape(k)
            val_tex = _tex_escape(v)
            lines.append(rf"{key_tex} & {val_tex} \\")

        lines.extend([
            r"\Xhline{2\arrayrulewidth}",
            r"\end{tabularx}",
            "```",
            "",
            "\\newpage",
        ])

    return lines

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Convert an Allure results directory into a markdown report."
    )
    parser.add_argument(
        "--results-dir",
        type=Path,
        default=RESULTS_DIR,
        help=f"Path to the Allure results directory (default: {RESULTS_DIR})",
    )
    parser.add_argument(
        "--out-path",
        type=Path,
        default=OUT_PATH,
        help=f"Path to write the generated markdown report (default: {OUT_PATH})",
    )
    return parser.parse_args()

# --- Main ---
def main() -> int:
    global RESULTS_DIR, OUT_PATH
    args = parse_args()
    RESULTS_DIR = args.results_dir
    OUT_PATH = args.out_path

    props = read_properties_as_dict(RESULTS_DIR / "environment.properties")

    # --- Remote / repo URL ---
    remote = props.get("git.remote") or props.get("ci.repo", "")
    base = remote_to_https_base(remote)
    owner, repo = split_owner_repo(base)

    # --- Branch / ref ---
    branch = props.get("git.branch") or props.get("ci.ref_name") or ""
    if not branch:
        ci_ref = props.get("ci.ref", "")
        if ci_ref.startswith("refs/heads/") or ci_ref.startswith("refs/tags/"):
            branch = ci_ref.split("/", 2)[-1]
        elif ci_ref.startswith("refs/pull/"):
            parts = ci_ref.split("/")
            # refs/pull/1/merge  -> PR-1-merge
            if len(parts) >= 4:
                branch = f"PR-{parts[2]}-{parts[3]}"
            else:
                branch = ci_ref

    # --- Describe / label for this run ---
    sha = props.get("git.sha") or props.get("ci.sha") or ""
    short_sha = props.get("git.short_sha") or (sha[:7] if sha else "")

    describe = props.get("git.describe") or ""
    if not describe:
        wf = props.get("ci.workflow", "")
        run_no = props.get("ci.run_number", "")
        if wf and run_no and short_sha:
            describe = f"{wf} #{run_no} ({short_sha})"
        elif wf and run_no:
            describe = f"{wf} #{run_no}"
        elif props.get("ci.ref"):
            describe = props["ci.ref"]
        elif short_sha:
            describe = short_sha

    commit_url = f"{base}/commit/{sha}" if (base and sha) else ""

    # Optional executor info from Allure's executor.json
    executor_path = RESULTS_DIR / "executor.json"
    executor = read_json_safe(executor_path) if executor_path.exists() else None

    # Final safeties so we never end up with an empty title
    owner_f = owner or "unknown-owner"
    repo_f = repo or "unknown-repo"
    branch_f = branch or props.get("ci.job", "") or "unknown-branch"
    describe_f = describe or "unnamed-run"

    lines: List[str] = []
    lines.append(
        build_front_matter(
            owner_f,
            repo_f,
            branch_f,
            describe_f,
            commit_url,
            executor=executor,
        )
    )

    # Summary accumulators
    stats = empty_stats()
    earliest_start: Optional[int] = None
    latest_stop: Optional[int] = None

    # Iterate test result JSONs
    json_files = sorted(p for p in RESULTS_DIR.glob("*.json") if is_result_json(p))
    normalized_results: List[TestVariant] = []

    for jf in json_files:
        data = read_json_safe(jf)
        if not data:
            continue

        status = normalize_status(data.get("status"))
        duration_ms, start_ms, stop_ms = parse_duration_window(data)
        accumulate_stats(stats, status, duration_ms)

        if start_ms is not None:
            earliest_start = start_ms if earliest_start is None else min(earliest_start, start_ms)
        if stop_ms is not None:
            latest_stop = stop_ms if latest_stop is None else max(latest_stop, stop_ms)

        package_name, directory_name, file_name, test_case, variant_name = parse_hierarchy(data)
        normalized_results.append(
            TestVariant(
                status=status,
                duration_ms=duration_ms,
                full_name=(data.get("fullName") or "").strip() or variant_name,
                test_case=test_case,
                variant_name=variant_name,
                description=(data.get("description") or "").strip(),
                attachments=collect_all_attachments(data),
                start_ms=start_ms,
                stop_ms=stop_ms,
                package_name=package_name,
                directory_name=directory_name,
                file_name=file_name,
            )
        )

    # Add summary table before details
    lines.extend(build_summary_table(stats, earliest_start, latest_stop))
    lines.extend(build_hierarchical_report(normalized_results))

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote {OUT_PATH}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
