import re
from typing import Dict, Optional, Tuple
from dateutil import parser
import phonenumbers

# Static mapping for location normalization and country ISO codes
COUNTRY_MAP: Dict[str, str] = {
    "united states": "US",
    "usa": "US",
    "us": "US",
    "india": "IN",
    "uk": "GB",
    "united kingdom": "GB",
    "germany": "DE",
    "canada": "CA",
    "australia": "AU"
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
            parsed_number = phonenumbers.parse(raw_phone, candidate_country)
            if phonenumbers.is_valid_number(parsed_number):
                return phonenumbers.format_number(parsed_number, phonenumbers.PhoneNumberFormat.E164)
        except phonenumbers.NumberParseException:
            return None

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
        if clean_date in {"present", "current", "now", "today"}:
            return None, True

        try:
            parsed_date = parser.parse(clean_date, fuzzy=True)
            return parsed_date.strftime("%Y-%m"), False
        except (ValueError, TypeError):
            return None, False

    @staticmethod
    def normalize_location(raw_location: str) -> Dict[str, Optional[str]]:
        """
        Splits a raw location string into city, region, and country codes.
        """
        if not raw_location:
            return {"city": None, "region": None, "country": None}

        clean_location = raw_location.strip()
        tokens = [token.strip() for token in re.split(r"[,|;-]", clean_location) if token.strip()]
        country_code = None
        city = None
        region = None

        if tokens:
            if len(tokens) == 1:
                city = tokens[0]
            elif len(tokens) == 2:
                city, country_token = tokens
                country_code = Normalizer.normalize_country_code(country_token)
            else:
                city, region, country_token = tokens[0], tokens[1], tokens[-1]
                country_code = Normalizer.normalize_country_code(country_token)

        if not country_code:
            country_code = Normalizer.normalize_country_code(clean_location)

        return {"city": city, "region": region, "country": country_code}

    @staticmethod
    def normalize_country_code(raw_country: str) -> Optional[str]:
        if not raw_country:
            return None

        clean_country = raw_country.strip().lower()
        if clean_country in COUNTRY_MAP:
            return COUNTRY_MAP[clean_country]

        for key, iso in COUNTRY_MAP.items():
            if key in clean_country:
                return iso

        return None

    @staticmethod
    def normalize_skill(raw_skill: str) -> Optional[str]:
        """
        Low-level text cleansing to canonicalize skill tokens.
        Example: "React.js" -> "react"
        """
        if not raw_skill:
            return None

        skill = raw_skill.strip().lower()
        skill = re.sub(r"(\.js|-js|js)$", "", skill)
        skill = re.sub(r"[^a-z0-9\+#+ ]", "", skill)
        skill = re.sub(r"\s+", " ", skill).strip()

        if not skill:
            return None

        # Normalize some known variants
        skill_map = {
            "reactjs": "react",
            "react": "react",
            "nodejs": "node",
            "node": "node",
            "c++": "c++",
            "python": "python",
            "golang": "go",
            "js": "javascript",
        }

        canonical = skill_map.get(skill, skill)
        return canonical if canonical else None