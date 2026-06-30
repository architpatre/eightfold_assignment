import json
from typing import List, Tuple, Any, Dict
from abc import ABC, abstractmethod

# Tuple signature: (field_path, raw_value, source_name, extraction_method)
ExtractedTuple = Tuple[str, Any, str, str]

class BaseExtractor(ABC):
    """Abstract base class for all data source extractors."""
    
    def __init__(self, source_name: str, weight: float):
        self.source_name = source_name
        self.weight = weight # Used later in the merge phase

    @abstractmethod
    def extract(self, raw_input: Any) -> List[ExtractedTuple]:
        """Parses raw input and yields flat tuples for the normalizer."""
        pass

# ---------------------------------------------------------
# Structured Extractor: ATS JSON
# ---------------------------------------------------------

class ATSJSONExtractor(BaseExtractor):
    def __init__(self):
        super().__init__(source_name="ATS_JSON", weight=0.95)
    
    def extract(self, raw_input: str) -> List[ExtractedTuple]:
        """
        Expects a JSON string. Maps foreign ATS keys to our internal paths.
        """
        records: List[ExtractedTuple] = []
        method = "Direct Key Mapping"
        
        try:
            data = json.loads(raw_input)
        except json.JSONDecodeError:
            # Graceful degradation: return empty if garbage source
            return records 

        # Example ATS JSON might have nested contact info and an array of jobs
        candidate = data.get("candidate", {})
        
        if first_name := candidate.get("first_name"):
            last_name = candidate.get("last_name", "")
            records.append(("full_name", f"{first_name} {last_name}".strip(), self.source_name, method))
            
        if email := candidate.get("contact", {}).get("email"):
            records.append(("emails", email, self.source_name, method))
            
        if phone := candidate.get("contact", {}).get("phone"):
            records.append(("phones", phone, self.source_name, method))

        if location := candidate.get("location"):
             # We pass the raw string; the Normalizer will break it into city/region/country
             records.append(("location", location, self.source_name, method))

        # Handle nested arrays using indexed dot-notation for the path
        for i, job in enumerate(candidate.get("employment_history", [])):
            if company := job.get("company_name"):
                records.append((f"experience[{i}].company", company, self.source_name, method))
            if title := job.get("job_title"):
                records.append((f"experience[{i}].title", title, self.source_name, method))
            if start := job.get("start_date"):
                records.append((f"experience[{i}].start_date", start, self.source_name, method))
            if end := job.get("end_date"):
                records.append((f"experience[{i}].end_date", end, self.source_name, method))

        return records

# ---------------------------------------------------------
# Unstructured Extractor: GitHub API
# ---------------------------------------------------------

class GitHubAPIExtractor(BaseExtractor):
    def __init__(self):
        super().__init__(source_name="GitHub_API", weight=0.85)
        
    def extract(self, raw_input: dict) -> List[ExtractedTuple]:
        """
        Expects a dictionary (simulating a parsed REST API response).
        """
        records: List[ExtractedTuple] = []
        method = "REST API Parsing"
        
        if name := raw_input.get("name"):
            records.append(("full_name", name, self.source_name, method))
            
        if email := raw_input.get("email"):
            records.append(("emails", email, self.source_name, method))
            
        if bio := raw_input.get("bio"):
            records.append(("headline", bio, self.source_name, method))
            
        if login := raw_input.get("login"):
            records.append(("links.github", f"https://github.com/{login}", self.source_name, method))

        # We can extract skills heuristically from a list of user repositories/languages
        for lang in raw_input.get("top_languages", []):
            records.append(("skills", lang, self.source_name, "Heuristic Array Extraction"))

        return records

# ---------------------------------------------------------
# Unstructured Extractor: Mock LinkedIn Profile
# ---------------------------------------------------------

class MockLinkedInExtractor(BaseExtractor):
    def __init__(self):
        super().__init__(source_name="LinkedIn_Mock", weight=0.90)
        
    def extract(self, raw_input: Any = None) -> List[ExtractedTuple]:
        """
        Since scraping LinkedIn is blocked, we use this mock extractor 
        to inject deterministic data into the pipeline for the assignment demo.
        """
        method = "Mock Fixture Injection"
        
        return [
            ("full_name", "Johnathan Doe", self.source_name, method),
            ("headline", "Senior Software Engineer @ TechCorp", self.source_name, method),
            ("links.linkedin", "https://linkedin.com/in/johndoe", self.source_name, method),
            ("skills", "Python", self.source_name, method),
            ("skills", "React.js", self.source_name, method),
            ("skills", "System Architecture", self.source_name, method),
            ("experience[0].company", "TechCorp", self.source_name, method),
            ("experience[0].title", "Senior Software Engineer", self.source_name, method),
            ("experience[0].start_date", "Jan 2023", self.source_name, method),
            ("experience[0].end_date", "Present", self.source_name, method),
        ]