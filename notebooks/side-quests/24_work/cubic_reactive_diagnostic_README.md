
# Cubic reactive diagnostic setup

This script sets up the first numerical experiment for the cubic three-channel extension:

- cubic character mod 7
- completed/root-number-normalized channels
- critical-line zero finder for the cubic channel
- Fortescue sequence transform
- PSD sanity check on the critical line
- synthetic off-critical insertion into zeta / chi / chibar
- sequence diagnostics including P0, P+, P-, P+-, Q+-

## Files
- `cubic_reactive_diagnostic.py`

## Run
```bash
python cubic_reactive_diagnostic.py
```

## Caveat
The off-critical insertion is synthetic. It is designed to test whether `Q_{+-}` is a useful handedness diagnostic, not to model a real GRH-violating zero pattern.
