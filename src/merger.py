import re
from typing import List, Dict, Any, Tuple
import difflib
from collections import defaultdict
from uuid import uuid4

# Import from our previous modules
from schema import CanonicalProfile, FieldContainer, ProvenanceMetadata, Location, Links, Experience, SkillField, ProvenanceRecord
from normalizers import Normalizer

# Source authority weights defined in the technical design
SOURCE_WEIGHTS = {
    "ATS_JSON": 0.95,
    "LinkedIn_Mock": 0.90,
    "GitHub_API": 0.85,
    "Recruiter_CSV": 0.75,
    "Resume_PDF": 0.60
}

class CandidateMerger:
    """
    Groups raw extracted tuples into unified candidate profiles, 
    resolving conflicts using a deterministic weighting strategy.
    """

    def __init__(self):
        # Maps any normalized identity key to a unique candidate UUID
        self.key_to_id: Dict[str, str] = {}
        # Stores candidate roots for transitive merges
        self.parent: Dict[str, str] = {}
        # Stores tuples grouped by their assigned UUID
        self.grouped_records: Dict[str, List[Tuple[str, Any, str, str]]] = defaultdict(list)

    def _find_root(self, candidate_id: str) -> str:
        if self.parent[candidate_id] != candidate_id:
            self.parent[candidate_id] = self._find_root(self.parent[candidate_id])
        return self.parent[candidate_id]

    def _union_ids(self, first_id: str, second_id: str) -> str:
        root_a = self._find_root(first_id)
        root_b = self._find_root(second_id)
        if root_a == root_b:
            return root_a

        winner = root_a if root_a < root_b else root_b
        loser = root_b if winner == root_a else root_a
        self.parent[loser] = winner
        self.grouped_records[winner].extend(self.grouped_records.pop(loser, []))
        return winner

    def _normalize_identity_key(self, path: str, value: Any) -> List[str]:
        if not value:
            return []

        if path == "emails":
            return [f"email:{str(value).strip().lower()}"]
        if path == "phones":
            normalized = Normalizer.normalize_phone(value)
            return [f"phone:{normalized}"] if normalized else []
        if path == "full_name":
            name = re.sub(r"\s+", " ", str(value).strip().lower())
            return [f"name:{name}"]

        return []

    def _match_fuzzy_name(self, candidate_names: List[str]) -> str:
        existing_name_keys = [key for key in self.key_to_id.keys() if key.startswith("name:")]
        for name in candidate_names:
            close = difflib.get_close_matches(name, existing_name_keys, n=1, cutoff=0.8)
            if close:
                return close[0]
        return ""

    def ingest_tuples(self, records: List[Tuple[str, Any, str, str]]):
        """
        Entity Resolution: Scans records to establish an identity key.
        Uses unified key mapping and transitive merge logic so that email,
        phone, and fuzzy name matches resolve to the same candidate record.
        """
        found_id = None
        batch_keys: List[str] = []
        candidate_names: List[str] = []

        for path, value, _, _ in records:
            batch_keys.extend(self._normalize_identity_key(path, value))
            if path == "full_name" and value:
                candidate_names.extend(self._normalize_identity_key(path, value))

        existing_ids = {self._find_root(self.key_to_id[key]) for key in batch_keys if key in self.key_to_id}

        if not existing_ids and candidate_names:
            fuzzy_key = self._match_fuzzy_name(candidate_names)
            if fuzzy_key and fuzzy_key in self.key_to_id:
                existing_ids.add(self._find_root(self.key_to_id[fuzzy_key]))

        if existing_ids:
            found_id = min(existing_ids)
            for other_id in existing_ids:
                found_id = self._union_ids(found_id, other_id)
        else:
            found_id = str(uuid4())
            self.parent[found_id] = found_id

        for key in batch_keys:
            self.key_to_id[key] = found_id

        self.grouped_records[found_id].extend(records)

    def _resolve_scalar_conflict(
        self, 
        current_container: FieldContainer, 
        new_value: Any, 
        source: str, 
        method: str
    ) -> FieldContainer:
        """
        Winner-takes-all logic for single fields (e.g., full_name, headline).
        Replaces the value if the new source has a strictly higher authority weight.
        """
        new_weight = SOURCE_WEIGHTS.get(source, 0.0)
        current_weight = current_container.confidence
        
        # If the container is empty, or the new source outranks the current one
        if current_container.value is None or new_weight > current_weight:
            return FieldContainer(
                value=new_value,
                confidence=new_weight,
                provenance=[ProvenanceMetadata(source=source, method=method)]
            )
        
        # If lower or equal weight, we reject the value but could append provenance
        # to show corroboration. For this scope, we preserve the highest-trust winner.
        return current_container

    def _record_provenance(self, profile: CanonicalProfile, field_name: str, source: str, method: str):
        rec = ProvenanceRecord(field=field_name, source=source, method=method)
        if all(not (r.field == rec.field and r.source == rec.source and r.method == rec.method) for r in profile.provenance):
            profile.provenance.append(rec)

    def _update_skill(self, profile: CanonicalProfile, raw_skill: str, source: str, method: str):
        normalized = Normalizer.normalize_skill(raw_skill)
        if not normalized:
            return

        weight = SOURCE_WEIGHTS.get(source, 0.0)
        existing = profile.skills.value.get(normalized)
        if existing is None:
            profile.skills.value[normalized] = SkillField(
                name=normalized,
                confidence=weight,
                sources=[ProvenanceMetadata(source=source, method=method)],
            )
        else:
            existing.confidence = max(existing.confidence, weight)
            if all(not (src.source == source and src.method == method) for src in existing.sources):
                existing.sources.append(ProvenanceMetadata(source=source, method=method))
        # Avoid duplicate provenance entries for the skill collection
        if all(not (p.source == source and p.method == method) for p in profile.skills.provenance):
            profile.skills.provenance.append(ProvenanceMetadata(source=source, method=method))

    def _update_location(self, profile: CanonicalProfile, raw_location: str, source: str, method: str):
        normalized = Normalizer.normalize_location(raw_location)
        if normalized.get("city"):
            profile.location.city = self._resolve_scalar_conflict(
                profile.location.city,
                normalized["city"],
                source,
                method,
            )
        if normalized.get("region"):
            profile.location.region = self._resolve_scalar_conflict(
                profile.location.region,
                normalized["region"],
                source,
                method,
            )
        if normalized.get("country"):
            profile.location.country = self._resolve_scalar_conflict(
                profile.location.country,
                normalized["country"],
                source,
                method,
            )

    def build_profiles(self) -> List[CanonicalProfile]:
        """
        Executes the merge policy across all grouped identities and 
        returns the finalized internal canonical records.
        """
        profiles: List[CanonicalProfile] = []

        for candidate_id, records in self.grouped_records.items():
            profile = CanonicalProfile(candidate_id=candidate_id)
            
            # Temporary dict to hold array objects before flattening them into the profile
            # Key: array index (e.g., '0'), Value: Dict of fields
            temp_experience = defaultdict(dict)

            for path, raw_value, source, method in records:
                if not raw_value:
                    continue

                # Array Path Handling (e.g., "experience[0].company")
                array_match = re.match(r"(\w+)\[(\d+)\]\.(\w+)", path)
                if array_match:
                    field_group, index, sub_field = array_match.groups()
                    if field_group == "experience":
                        temp_experience[index][sub_field] = (raw_value, source, method)
                    continue

                # Scalar & Set Normalization Routing
                if path == "phones":
                    norm_val = Normalizer.normalize_phone(raw_value)
                    if norm_val:
                        profile.phones.value.add(norm_val)
                        profile.phones.provenance.append(ProvenanceMetadata(source=source, method=method))
                        self._record_provenance(profile, "phones", source, method)

                elif path == "emails":
                    norm_val = str(raw_value).strip().lower()
                    profile.emails.value.add(norm_val)
                    profile.emails.provenance.append(ProvenanceMetadata(source=source, method=method))
                    self._record_provenance(profile, "emails", source, method)

                elif path == "skills":
                    self._update_skill(profile, raw_value, source, method)
                    self._record_provenance(profile, "skills", source, method)

                elif path == "location":
                    self._update_location(profile, raw_value, source, method)
                    self._record_provenance(profile, "location", source, method)

                elif path == "full_name":
                    profile.full_name = self._resolve_scalar_conflict(profile.full_name, raw_value, source, method)
                    self._record_provenance(profile, "full_name", source, method)

                elif path == "headline":
                    profile.headline = self._resolve_scalar_conflict(profile.headline, raw_value, source, method)
                    self._record_provenance(profile, "headline", source, method)

                elif path == "links.github":
                    profile.links.github = self._resolve_scalar_conflict(profile.links.github, raw_value, source, method)
                    self._record_provenance(profile, "links.github", source, method)

                elif path == "links.linkedin":
                    profile.links.linkedin = self._resolve_scalar_conflict(profile.links.linkedin, raw_value, source, method)
                    self._record_provenance(profile, "links.linkedin", source, method)

            # Reconstruct Experience Arrays
            for idx, job_data in temp_experience.items():
                exp = Experience()
                for key, (val, src, meth) in job_data.items():
                    if key in ["start_date", "end_date"]:
                        norm_date, is_current = Normalizer.normalize_date(val)
                        if is_current:
                            exp.is_current = FieldContainer(value=True, confidence=SOURCE_WEIGHTS.get(src, 0.0), provenance=[ProvenanceMetadata(source=src, method=meth)])
                        elif norm_date:
                            setattr(exp, key, FieldContainer(value=norm_date, confidence=SOURCE_WEIGHTS.get(src, 0.0), provenance=[ProvenanceMetadata(source=src, method=meth)]))
                    else:
                        setattr(exp, key, FieldContainer(value=val, confidence=SOURCE_WEIGHTS.get(src, 0.0), provenance=[ProvenanceMetadata(source=src, method=meth)]))
                profile.experience.append(exp)

            # Calculate overall confidence
            profile.overall_confidence = self._calculate_overall_confidence(profile)
            profiles.append(profile)

        return profiles

    def _calculate_overall_confidence(self, profile: CanonicalProfile) -> float:
        """Calculates a baseline confidence score with penalties for missing core fields."""
        base = sum(SOURCE_WEIGHTS.values()) / len(SOURCE_WEIGHTS) # Simplified average trust
        penalty = 0.0
        if not profile.emails.value:
            penalty += 0.15
        if not profile.full_name.value:
            penalty += 0.15
            
        return max(0.0, min(1.0, base - penalty))