
import json
from uuid import UUID
from schema import CanonicalProfile
from extractors import ATSJSONExtractor, GitHubAPIExtractor, MockLinkedInExtractor
from merger import CandidateMerger
from projector import ProfileProjector, ConfigurationError

# ---------------------------------------------------------
# Mock Sample Data Generation
# ---------------------------------------------------------
SAMPLE_ATS_PAYLOAD = json.dumps({
    "candidate": {
        "first_name": "Johnathan",
        "last_name": "Doe",
        "location": "San Francisco, USA",
        "contact": {
            "email": "johndoe@example.com",
            "phone": "510-555-0192"
        },
        "employment_history": [
            {
                "company_name": "TechCorp",
                "job_title": "Software Engineer II",
                "start_date": "2023-01-15",
                "end_date": "Present"
            }
        ]
    }
})

SAMPLE_GITHUB_PAYLOAD = {
    "name": "John Doe",
    "email": "johndoe@example.com",
    "login": "johndoe_dev",
    "bio": "Building scalable backend systems in Python and Go.",
    "top_languages": ["Python", "Go", "React.js"]
}

# ---------------------------------------------------------
# Custom Output Configurations
# ---------------------------------------------------------
CUSTOM_CONFIG_1 = {
    "fields": [
        { "path": "full_name", "required": True },
        { "path": "primary_email", "from": "emails[0]", "required": True },
        { "path": "mobile_phone", "from": "phones[0]" },
        { "path": "tech_stack", "from": "skills" }
    ],
    "include_confidence": True,
    "on_missing": "null"
}

CUSTOM_CONFIG_2 = {
    "fields": [
        { "path": "full_name", "required": True },
        { "path": "current_role", "from": "experience[0].title" }
    ],
    "include_confidence": False,
    "on_missing": "omit"
}

# Custom Pydantic JSON Encoder to handle Python Sets natively
class CanonicalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, set):
            return list(obj)
        if isinstance(obj, UUID):
            return str(obj)
        return super().default(obj)

# ---------------------------------------------------------
# Pipeline Orchestrator Execution
# ---------------------------------------------------------
# ---------------------------------------------------------
# Pipeline Orchestrator Execution
# ---------------------------------------------------------
def run_pipeline():
    import argparse
    from pathlib import Path

    parser = argparse.ArgumentParser(description="Run the candidate transformer pipeline.")
    parser.add_argument("--inputs", nargs="+", help="List of input JSON files or strings to process (optional). If omitted, runs built-in demo.")
    parser.add_argument("--config", help="Optional projection config JSON file")
    args = parser.parse_args()

    print("=== [1] Initializing Extractor Units ===")
    ats_extractor = ATSJSONExtractor()
    github_extractor = GitHubAPIExtractor()
    linkedin_extractor = MockLinkedInExtractor()

    records_batches = []

    if not args.inputs:
        print("No input files provided — running demo samples.")
        tuples_ats = ats_extractor.extract(SAMPLE_ATS_PAYLOAD)
        tuples_github = github_extractor.extract(SAMPLE_GITHUB_PAYLOAD)
        tuples_linkedin = linkedin_extractor.extract()
        records_batches = [tuples_ats, tuples_github, tuples_linkedin]
    else:
        for inpath in args.inputs:
            p = Path(inpath)
            if p.exists():
                try:
                    data = json.loads(p.read_text())
                except Exception:
                    data = p.read_text()
            else:
                try:
                    data = json.loads(inpath)
                except Exception:
                    data = inpath

            if isinstance(data, dict) and ("name" in data or "login" in data):
                records_batches.append(github_extractor.extract(data))
            elif isinstance(data, dict) and ("candidate" in data or "employment_history" in data):
                records_batches.append(ats_extractor.extract(json.dumps(data)))
            else:
                # fallback: treat as unstructured and use the LinkedIn mock extractor
                records_batches.append(linkedin_extractor.extract())

    print("\n=== [2] Executing Entity Resolution & Merge Strategy ===")
    merger = CandidateMerger()
    for batch in records_batches:
        merger.ingest_tuples(batch)

    profiles = merger.build_profiles()
    if not profiles:
        print("Error: No profiles resolved.")
        return

    canonical_record = profiles[0]
    print(f"Identity resolved successfully. Assigned Candidate ID: {canonical_record.candidate_id}")

    print("\n=== [3] Output: Full Canonical State (Internal Format) ===")
    # Support both pydantic v1 (`.dict`) and v2 (`.model_dump`)
    try:
        payload = canonical_record.model_dump()
    except Exception:
        payload = canonical_record.dict()
    print(json.dumps(payload, cls=CanonicalEncoder, indent=2))

    if args.config:
        cfg_path = Path(args.config)
        try:
            cfg = json.loads(cfg_path.read_text())
        except Exception as e:
            print(f"Failed to load config: {e}")
            cfg = None

        if cfg:
            try:
                projector = ProfileProjector(cfg)
                output = projector.project(canonical_record)
                print("\n--- Projected Profile (Custom Config) ---")
                print(json.dumps(output, cls=CanonicalEncoder, indent=2))
            except ConfigurationError as e:
                print(f"Configuration error: {e}")
    else:
        print("No projection config provided — skipping projection step.")

if __name__ == "__main__":
    run_pipeline()