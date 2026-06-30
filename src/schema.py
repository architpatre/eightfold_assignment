from typing import List, Optional, Set, Generic, TypeVar, Dict
from pydantic import BaseModel, Field, UUID4
from datetime import date

# Define a generic type variable for our wrapper
T = TypeVar('T')

class ProvenanceMetadata(BaseModel):
    """Tracks exactly where a single data point came from."""
    source: str
    method: str

class FieldContainer(BaseModel, Generic[T]):
    """
    A generic wrapper for any canonical field. 
    Allows us to store the normalized value alongside its confidence and origin.
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
    country: FieldContainer[str] = Field(default_factory=FieldContainer) # ISO-3166 alpha-2

class Links(BaseModel):
    linkedin: FieldContainer[str] = Field(default_factory=FieldContainer)
    github: FieldContainer[str] = Field(default_factory=FieldContainer)
    portfolio: FieldContainer[str] = Field(default_factory=FieldContainer)
    other: FieldContainer[List[str]] = Field(default_factory=lambda: FieldContainer(value=[]))

class Experience(BaseModel):
    company: FieldContainer[str] = Field(default_factory=FieldContainer)
    title: FieldContainer[str] = Field(default_factory=FieldContainer)
    start_date: FieldContainer[str] = Field(default_factory=FieldContainer) # YYYY-MM
    end_date: FieldContainer[str] = Field(default_factory=FieldContainer)   # YYYY-MM or null
    is_current: FieldContainer[bool] = Field(default_factory=lambda: FieldContainer(value=False))
    summary: FieldContainer[str] = Field(default_factory=FieldContainer)

class Education(BaseModel):
    institution: FieldContainer[str] = Field(default_factory=FieldContainer)
    degree: FieldContainer[str] = Field(default_factory=FieldContainer)
    field_of_study: FieldContainer[str] = Field(default_factory=FieldContainer)
    end_year: FieldContainer[str] = Field(default_factory=FieldContainer) # YYYY

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
    
    # We use Sets here for O(1) deduplication of primitive strings during the merge phase
    emails: FieldContainer[Set[str]] = Field(default_factory=lambda: FieldContainer(value=set()))
    phones: FieldContainer[Set[str]] = Field(default_factory=lambda: FieldContainer(value=set()))
    skills: FieldContainer[Set[str]] = Field(default_factory=lambda: FieldContainer(value=set()))
    
    location: Location = Field(default_factory=Location)
    links: Links = Field(default_factory=Links)
    
    experience: List[Experience] = Field(default_factory=list)
    education: List[Education] = Field(default_factory=list)
    
    overall_confidence: float = 0.0