import re
from typing import Any, Dict, List
from schema import CanonicalProfile, FieldContainer

class ConfigurationError(Exception):
    """Raised when a required field is missing and on_missing is set to 'error'."""
    pass

class ProfileProjector:
    """
    Applies a runtime configuration mask to a CanonicalProfile, reshaping 
    the output and dropping internal metadata unless explicitly requested.
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.fields_config = config.get("fields", [])
        self.on_missing = config.get("on_missing", "null") # "null", "omit", "error"
        self.include_confidence = config.get("include_confidence", False)

    def _resolve_path(self, profile: CanonicalProfile, path: str) -> Any:
        """
        A lightweight path evaluator to fetch data from the nested CanonicalProfile.
        Handles simple attributes ('full_name') and array indexing ('emails[0]').
        """
        # Parse standard dot notation and array indices
        parts = re.split(r'\.|\[|\]', path)
        parts = [p for p in parts if p] # Remove empty strings from split
        
        current_context = profile

        try:
            for part in parts:
                # If it's a digit, we are indexing into a list or set
                if part.isdigit():
                    idx = int(part)
                    # Convert sets to lists for indexing (e.g., emails[0])
                    if isinstance(current_context, set):
                        current_context = list(current_context)[idx]
                    elif isinstance(current_context, list):
                        current_context = current_context[idx]
                # Otherwise, it's an attribute name
                else:
                    if hasattr(current_context, part):
                        current_context = getattr(current_context, part)
                    elif isinstance(current_context, dict) and part in current_context:
                        current_context = current_context[part]
                    else:
                        return None # Path broken
                        
                # Auto-unwrap FieldContainers as we traverse
                if isinstance(current_context, FieldContainer):
                    if not self.include_confidence:
                        current_context = current_context.value
                    # If include_confidence is True, we return the whole container dict
                    # which will be serialized later.
                        
            return current_context
            
        except (IndexError, TypeError, AttributeError):
            return None

    def project(self, profile: CanonicalProfile) -> Dict[str, Any]:
        """
        Executes the mapping configuration against the canonical profile.
        """
        output: Dict[str, Any] = {}
        
        # Always inject the primary identifier
        output["candidate_id"] = str(profile.candidate_id)

        for field_def in self.fields_config:
            target_key = field_def.get("path")
            
            # If 'from' is provided, fetch from there. Otherwise fetch from 'path'.
            source_path = field_def.get("from", target_key)
            is_required = field_def.get("required", False)
            
            # Fetch the value from our rich internal model
            value = self._resolve_path(profile, source_path)
            
            # Handle empty/missing values based on the config strategy
            if value is None or (isinstance(value, list) and not value) or (isinstance(value, set) and not value):
                if is_required and self.on_missing == "error":
                    raise ConfigurationError(f"Required field missing: '{target_key}' mapped from '{source_path}'")
                elif self.on_missing == "omit":
                    continue
                elif self.on_missing == "null":
                    output[target_key] = None
            else:
                # Convert Pydantic models to plain data (support v2 `.model_dump` and v1 `.dict`)
                if hasattr(value, "model_dump"):
                    dumped = value.model_dump()
                elif hasattr(value, "dict"):
                    dumped = value.dict()
                else:
                    dumped = value

                # Special-case: skills stored internally as a dict of SkillField
                # Convert to an array of {name, confidence, sources[]} for external output
                if isinstance(dumped, dict) and all(isinstance(v, dict) and "name" in v for v in dumped.values()):
                    output[target_key] = [v for k, v in dumped.items()]
                    continue

                if isinstance(dumped, list):
                    # Clean up nested Pydantic models in arrays (like Experience)
                    cleaned = []
                    for item in dumped:
                        if hasattr(item, "model_dump"):
                            cleaned.append(item.model_dump())
                        elif hasattr(item, "dict"):
                            cleaned.append(item.dict())
                        else:
                            cleaned.append(item)
                    output[target_key] = cleaned
                    continue

                if isinstance(dumped, set):
                    output[target_key] = list(dumped)
                    continue

                output[target_key] = dumped

        # Attach overall profile confidence if requested globally
        if self.include_confidence:
            output["overall_confidence"] = profile.overall_confidence

        return output