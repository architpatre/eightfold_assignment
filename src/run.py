
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
    print("=== [1] Initializing Extractor Units ===")
    ats_extractor = ATSJSONExtractor()
    github_extractor = GitHubAPIExtractor()
    linkedin_extractor = MockLinkedInExtractor()

    print("\n=== [2] Extracting Messy Inputs into Metadata Tuples ===")
    tuples_ats = ats_extractor.extract(SAMPLE_ATS_PAYLOAD)
    tuples_github = github_extractor.extract(SAMPLE_GITHUB_PAYLOAD)
    tuples_linkedin = linkedin_extractor.extract()

    print(f"-> ATS generated {len(tuples_ats)} tuples.")
    print(f"-> GitHub generated {len(tuples_github)} tuples.")
    print(f"-> LinkedIn Mock generated {len(tuples_linkedin)} tuples.")

    print("\n=== [3] Executing Entity Resolution & Merge Strategy ===")
    merger = CandidateMerger()
    merger.ingest_tuples(tuples_ats)
    merger.ingest_tuples(tuples_github)
    merger.ingest_tuples(tuples_linkedin)

    profiles = merger.build_profiles()
    if not profiles:
        print("Error: No profiles resolved.")
        return
        
    canonical_record = profiles[0]
    print(f"Identity resolved successfully. Assigned Candidate ID: {canonical_record.candidate_id}")

    print("\n=== [4] Output: Full Canonical State (Internal Format) ===")
    print(json.dumps(canonical_record.model_dump(), cls=CanonicalEncoder, indent=2))

    print("\n=== [5] Projecting to Custom Configurations ===")
    
    # Run Custom Config 1 (Includes mapped entries, sets, and confidence telemetry)
    projector_1 = ProfileProjector(CUSTOM_CONFIG_1)
    output_1 = projector_1.project(canonical_record)
    print("\n--- Projected Profile (Config 1: Technical Summary) ---")
    # FIX: Pass the CanonicalEncoder to serialize nested sets inside the model dict
    print(json.dumps(output_1, cls=CanonicalEncoder, indent=2))

    # Run Custom Config 2 (Aggressive pruning, omitted empty entries)
    projector_2 = ProfileProjector(CUSTOM_CONFIG_2)
    output_2 = projector_2.project(canonical_record)
    print("\n--- Projected Profile (Config 2: Minimal Role Traversal) ---")
    # FIX: Pass the CanonicalEncoder for safety across any complex config variation
    print(json.dumps(output_2, cls=CanonicalEncoder, indent=2))

if __name__ == "__main__":
    run_pipeline()