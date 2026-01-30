# Polygon Problem Generator

This project builds or updates a Polygon problem from `problem.yaml` and local assets.

## Setup

1) Create a virtual environment
```
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

2) Install dependencies
```
pip install -r requirements.txt
```

3) Configure environment
Create a `.env` file with:
```
POLYGON_KEY=your_api_key
POLYGON_SECRET=your_api_secret
# Optional:
# POLYGON_BASE_URL=https://polygon.codeforces.com/api
```

## Project structure

- `src/` Python modules
- `problem.yaml` Main config (schema is fixed by the repo)
- `assets/statement/` Statement parts (`legend.md`, `input.md`, `output.md`, optional `notes.md`, `tutorial.md`, `images/`)
- `files/` Validator/solutions/checker
- `tests/` Sample/manual tests and generators

## Build

Dry run (no API calls):
```
python -m src.build --config problem.yaml --dry-run --verbose
```

Actual build:
```
python -m src.build --config problem.yaml --verbose
```

## Smoke test

List problems (checks API access):
```
python -m src.smoke_test
```

## Notes

- Polygon API method names live in `src/polygon_methods.py`. Update them to the exact names for your Polygon instance.
- If a method is unconfirmed, the build will raise a clear error telling you the assumed name.
- Tests files are expected at `tests/samples.yaml` and `tests/manuals.yaml` as referenced in `problem.yaml`.
