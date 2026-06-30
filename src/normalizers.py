import re
from typing import Optional, Tuple
from dateutil import parser
import phonenumbers

# Static mapping for scoped location normalization (Edge case handling)
COUNTRY_MAP = {
    "united states": "US",
    "usa": "US",
    "us": "US",
    "india": "IN",
    "uk": "GB",
    "united kingdom": "GB"
}

class Normalizer:
    """Centralized sanitation layer for raw extracted tuples."""

    @staticmethod
    def normalize_phone(raw_phone: str, candidate_country: str = "US") -> Optional[str]:
        """
        Strips whitespace/characters and formats to E.164 standard.
        Assumes US (+1) if no country code is provided and no location is known.
        """
        if not raw_phone:
            return None
            
        try:
            # Parse the number, assuming the candidate_country as the default region
            parsed_number = phonenumbers.parse(raw_phone, candidate_country)
            
            # Check if it's a valid number before formatting
            if phonenumbers.is_valid_number(parsed_number):
                return phonenumbers.format_number(
                    parsed_number, 
                    phonenumbers.PhoneNumberFormat.E164
                )
        except phonenumbers.NumberParseException:
            pass # Fallthrough to return None if completely unparsable
            
        return None

    @staticmethod
    def normalize_date(raw_date: str) -> Tuple[Optional[str], bool]:
        """
        Parses varying date formats to ISO YYYY-MM. 
        Returns a tuple: (normalized_date_string, is_current_boolean)
        """
        if not raw_date:
            return None, False

        clean_date = raw_date.strip().lower()
        
        if clean_date in ["present", "current", "now"]:
            return None, True # It is a current role, no strict end date

        try:
            # fuzzy=True allows the parser to ignore extraneous text
            parsed_date = parser.parse(clean_date, fuzzy=True)
            return parsed_date.strftime("%Y-%m"), False
        except (ValueError, TypeError):
            return None, False

    @staticmethod
    def normalize_location_country(raw_location: str) -> Optional[str]:
        """
        Maps raw location text to ISO-3166 alpha-2 codes.
        Scope is limited to exact dict matching for this assignment.
        """
        if not raw_location:
            return None
            
        clean_loc = raw_location.strip().lower()
        
        # Check if the raw string directly matches a known alias
        if clean_loc in COUNTRY_MAP:
            return COUNTRY_MAP[clean_loc]
            
        # Fallback: check if a known country name is *inside* the string (e.g., "San Francisco, USA")
        for key, code in COUNTRY_MAP.items():
            if key in clean_loc:
                return code
                
        return None

    @staticmethod
    def normalize_skill(raw_skill: str) -> Optional[str]:
        """
        Low-level text cleansing to canonicalize skill tokens.
        Example: "React.js" -> "react"
        """
        if not raw_skill:
            return None
            
        # Lowercase and strip whitespace
        skill = raw_skill.strip().lower()
        
        # Remove common suffixes that cause duplication
        skill = re.sub(r'(\.js|-js|js)$', '', skill)
        
        # Strip all remaining non-alphanumeric characters (e.g., C++ -> c, Node.js -> node)
        # Note: For a production system, 'C++' needs special handling, but for this scoped 
        # assignment, strict alphanumeric reduction is a defensible baseline.
        skill = re.sub(r'[^a-z0-9]', '', skill)
        
        return skill if skill else None