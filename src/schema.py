from typing import Dict, Generic, List, Optional, Set, TypeVar
from pydantic import BaseModel, Field, UUID4

# Define a generic type variable for our wrapper
T = TypeVar('T')

class ProvenanceMetadata(BaseModel):
    """Tracks exactly where a single data point came from."""
    source: str
    method: str

class FieldContainer(BaseModel, Generic[T]):
    """
    A generic wrapper for any canonical field.
    Stores the normalized value alongside confidence and origin.
    """
    value: Optional[T] = None
    confidence: float = 0.0
    provenance: List[ProvenanceMetadata] = Field(default_factory=list)

# ---------------------------------------------------------
# Nested Structural Models
# ---------------------------------------------------------

class Location(BaseModel):
    city: FieldContainer[str] = Field(default_factory=FieldContainer)
    region: FieldContainer[str] = Field(default_factory=FieldContainer)
    country: FieldContainer[str] = Field(default_factory=FieldContainer)  # ISO-3166 alpha-2

class Links(BaseModel):
    linkedin: FieldContainer[str] = Field(default_factory=FieldContainer)
    github: FieldContainer[str] = Field(default_factory=FieldContainer)
    portfolio: FieldContainer[str] = Field(default_factory=FieldContainer)
    other: FieldContainer[List[str]] = Field(default_factory=lambda: FieldContainer(value=[]))

class SkillField(BaseModel):
    name: str
    confidence: float = 0.0
    sources: List[ProvenanceMetadata] = Field(default_factory=list)

class Experience(BaseModel):
    company: FieldContainer[str] = Field(default_factory=FieldContainer)
    title: FieldContainer[str] = Field(default_factory=FieldContainer)
    start_date: FieldContainer[str] = Field(default_factory=FieldContainer)  # YYYY-MM
    end_date: FieldContainer[str] = Field(default_factory=FieldContainer)    # YYYY-MM or null
    is_current: FieldContainer[bool] = Field(default_factory=lambda: FieldContainer(value=False))
    summary: FieldContainer[str] = Field(default_factory=FieldContainer)

class Education(BaseModel):
    institution: FieldContainer[str] = Field(default_factory=FieldContainer)
    degree: FieldContainer[str] = Field(default_factory=FieldContainer)
    field_of_study: FieldContainer[str] = Field(default_factory=FieldContainer)
    end_year: FieldContainer[str] = Field(default_factory=FieldContainer)  # YYYY

class ProvenanceRecord(BaseModel):
    field: str
    source: str
    method: str

# ---------------------------------------------------------
# Master Canonical Model
# ---------------------------------------------------------

class CanonicalProfile(BaseModel):
    """
    The internal, fully-tracked source of truth for a single candidate.
    This is NEVER exposed directly to the final output without passing
    through the projection/config layer first.
    """
    candidate_id: UUID4
    full_name: FieldContainer[str] = Field(default_factory=FieldContainer)
    headline: FieldContainer[str] = Field(default_factory=FieldContainer)

    emails: FieldContainer[Set[str]] = Field(default_factory=lambda: FieldContainer(value=set()))
    phones: FieldContainer[Set[str]] = Field(default_factory=lambda: FieldContainer(value=set()))
    skills: FieldContainer[Dict[str, SkillField]] = Field(default_factory=lambda: FieldContainer(value={}))

    location: Location = Field(default_factory=Location)
    links: Links = Field(default_factory=Links)

    experience: List[Experience] = Field(default_factory=list)
    education: List[Education] = Field(default_factory=list)
    years_experience: FieldContainer[float] = Field(default_factory=FieldContainer)
    provenance: List[ProvenanceRecord] = Field(default_factory=list)

    overall_confidence: float = 0.0