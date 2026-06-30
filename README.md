# Multi-Source Candidate Data Transformer

A deterministic pipeline built to ingest unstructured and semi-structured profile data from disparate sources, perform structural entity resolution, execute rule-based field merging, and project clean candidate records according to an uncompiled runtime schema configuration mask.

## System Dependencies & Setup

This engineering solution targets Python 3.10+ environments. Core parsing features utilize the following libraries:
* `pydantic` - Data modeling, validation, and serialization primitives.
* `phonenumbers` - E.164 compliance and international phone parsing.
* `python-dateutil` - Resilient fuzzy parsing of varied chronological string formats.

Install dependencies directly via standard pip management:
```bash
pip install pydantic phonenumbers python-dateutil