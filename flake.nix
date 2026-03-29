{
  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-25.05";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs = { self, nixpkgs, flake-utils }:
    flake-utils.lib.eachDefaultSystem (system:
      let
        pkgs = import nixpkgs { inherit system; };
      in {
        devShells.default = pkgs.mkShell {
          packages = with pkgs; [
            python3
            poetry
            git
            quarto            # ipynb / qmd / markdown / pdf converter
            tectonic
            zlib
            stdenv.cc.cc.lib  # needed b/c I'm keeping nix env deps separate from python deps (poetry)
          ];
        
        shellHook = ''
          export LD_LIBRARY_PATH=${pkgs.lib.makeLibraryPath [
            pkgs.stdenv.cc.cc.lib
            pkgs.zlib
          ]}:$LD_LIBRARY_PATH

          # Ensure Poetry uses an in-project virtualenv: ./\.venv
          export POETRY_VIRTUALENVS_IN_PROJECT=true

          # Create venv + install deps only when needed
          if [ ! -d .venv ]; then
            echo "[nix] creating Poetry venv + installing deps..."
            poetry install
          else
            # If pyproject or lockfile changed since venv was created/updated, re-sync.
            if [ pyproject.toml -nt .venv ] || [ poetry.lock -nt .venv ]; then
              echo "[nix] pyproject/lock changed -> syncing deps..."
              poetry sync
              # touch the venv dir so the timestamp check works next time
              touch .venv
            fi
          fi

          # Activate the Poetry venv for this shell
          source .venv/bin/activate
          export PATH="$PWD/.venv/bin:$PATH"

          # Nice-to-have: ensure the package entrypoints resolve to the venv
          export PYTHONNOUSERSITE=1
        '';
        };
      });
}
