import re
from typing import List, Dict, Any, Tuple
from collections import defaultdict
from uuid import uuid4

# Import from our previous modules
from schema import CanonicalProfile, FieldContainer, ProvenanceMetadata, Location, Links, Experience
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
        # Maps a normalized email to a unique candidate UUID
        self.email_to_id: Dict[str, str] = {}
        # Stores tuples grouped by their assigned UUID
        self.grouped_records: Dict[str, List[Tuple[str, Any, str, str]]] = defaultdict(list)

    def ingest_tuples(self, records: List[Tuple[str, Any, str, str]]):
        """
        Entity Resolution: Scans records to establish an identity key.
        In a production system, this would use union-find or graph resolution.
        Here, we group all incoming tuples by the first normalized email found in the batch.
        """
        batch_id = str(uuid4())
        primary_email = None

        # Pass 1: Hunt for the primary matching key (Email)
        for path, value, _, _ in records:
            if path == "emails" and value:
                clean_email = str(value).strip().lower()
                primary_email = clean_email
                
                # If we've seen this email before, link this batch to the existing UUID
                if clean_email in self.email_to_id:
                    batch_id = self.email_to_id[clean_email]
                else:
                    self.email_to_id[clean_email] = batch_id
                break
        
        # Pass 2: Store all records under the resolved UUID
        self.grouped_records[batch_id].extend(records)

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
                        
                elif path == "emails":
                    norm_val = str(raw_value).strip().lower()
                    profile.emails.value.add(norm_val)
                    profile.emails.provenance.append(ProvenanceMetadata(source=source, method=method))
                    
                elif path == "skills":
                    norm_val = Normalizer.normalize_skill(raw_value)
                    if norm_val:
                        profile.skills.value.add(norm_val)
                        profile.skills.provenance.append(ProvenanceMetadata(source=source, method=method))
                        
                elif path == "full_name":
                    profile.full_name = self._resolve_scalar_conflict(profile.full_name, raw_value, source, method)
                    
                elif path == "headline":
                    profile.headline = self._resolve_scalar_conflict(profile.headline, raw_value, source, method)
                    
                elif path == "links.github":
                    profile.links.github = self._resolve_scalar_conflict(profile.links.github, raw_value, source, method)
                    
                elif path == "links.linkedin":
                    profile.links.linkedin = self._resolve_scalar_conflict(profile.links.linkedin, raw_value, source, method)

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