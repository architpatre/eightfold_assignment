import sys
from pathlib import Path

# Ensure project root is on sys.path for imports like `from schema import ...`
project_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src"))

from src.merger import CandidateMerger


def make_record(path, value, source="ATS_JSON", method="Direct"):
    return (path, value, source, method)


def test_fuzzy_name_merges_batches():
    merger = CandidateMerger()

    # First candidate batch
    batch1 = [
        make_record("full_name", "Jane Doe"),
        make_record("emails", "jane.doe@example.com")
    ]

    # Second candidate batch with slightly misspelled name and different email
    batch2 = [
        make_record("full_name", "Jnae Doe"),
        make_record("emails", "jane.d@example.org")
    ]

    merger.ingest_tuples(batch1)
    merger.ingest_tuples(batch2)

    profiles = merger.build_profiles()
    # Expect fuzzy name matching to merge into a single profile
    assert len(profiles) == 1, f"Expected 1 merged profile, got {len(profiles)}"


def test_transitive_identity_merge():
    merger = CandidateMerger()

    batch1 = [
        make_record("full_name", "Jane Doe"),
        make_record("emails", "jane.doe@example.com")
    ]
    batch2 = [
        make_record("full_name", "Jnae Doe"),
        make_record("phones", "510-555-1234")
    ]
    batch3 = [
        make_record("emails", "jane.d@example.org"),
        make_record("phones", "(510) 555-1234")
    ]

    merger.ingest_tuples(batch1)
    merger.ingest_tuples(batch2)
    merger.ingest_tuples(batch3)

    profiles = merger.build_profiles()
    assert len(profiles) == 1, f"Expected transitive merge into 1 profile, got {len(profiles)}"
    profile = profiles[0]
    assert "jane.doe@example.com" in profile.emails.value
    assert "jane.d@example.org" in profile.emails.value
    assert "+15105551234" in profile.phones.value
