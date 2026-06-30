# Multi-Source Candidate Data Transformer

A deterministic pipeline built to ingest unstructured and semi-structured profile data from disparate sources, perform structural entity resolution, execute rule-based field merging, and project clean candidate records according to an uncompiled runtime schema configuration mask.

## System Dependencies & Setup

This engineering solution targets Python 3.10+ environments. Core parsing features utilize the following libraries:
* `pydantic` - Data modeling, validation, and serialization primitives.
* `phonenumbers` - E.164 compliance and international phone parsing.
* `python-dateutil` - Resilient fuzzy parsing of varied chronological string formats.
* `pytest` - Project test validation.

Install dependencies using the provided requirements file:
```bash
python -m pip install -r requirements.txt
```

## Run the pipeline

Run the demo mode with built-in sample payloads:
```bash
python src/run.py
```

Run the pipeline with sample input files and a projection config:
```bash
python src/run.py --inputs samples/ats_sample.json samples/github_sample.json --config samples/config_technical.json
```

## Sample files

- `samples/ats_sample.json` — ATS-style candidate payload
- `samples/github_sample.json` — GitHub profile payload
- `samples/config_technical.json` — projection configuration for custom output

## What is implemented

- CLI input support for JSON files and inline strings
- Canonical profile model with field-level provenance and confidence
- Entity resolution across multiple identity keys: email, phone, and fuzzy name matching
- Projection engine that maps internal canonical fields to external output
- Unit tests and regression coverage for pipeline execution and identity merging

## Tests

Run the project test suite with:
```bash
python -m pytest -q
```

## Assumptions and scope

- Some source extractors are mocked for demo purposes (LinkedIn mock). The pipeline is designed to be extended with additional source extractors.
- The merge strategy favors higher-authority sources for scalar fields and accumulates provenance for set/dict fields such as skills.
- Candidate identity resolution is based on normalized email, phone, and fuzzy full-name matching, with transitive merging for linked records.

## Notes

- The project uses `src/` as the source package root. `run.py` loads `schema.py`, `extractors.py`, `merger.py`, `normalizers.py`, and `projector.py`.
- If Python import errors occur, ensure you run commands from the repository root: `c:\Users\archi\OneDrive\Desktop\eightfold`.
