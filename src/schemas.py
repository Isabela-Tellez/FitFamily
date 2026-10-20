"""Shared Pydantic schemas for the FitFamily research module.

Defines the data models for research briefs, evidence, competitors,
and research results. These are the shared contracts that Persona 1
(Investigador) must use and may extend but not replace.
"""

from __future__ import annotations

from pydantic import BaseModel, Field, model_validator
from typing import List, Optional, Dict, Any


class Evidence(BaseModel):
    """A single piece of evidence supporting a claim or data point.

    An evidence record allows another person to trace back to the original
    source and understand what supports the assertion.
    """

    evidence_id: str = Field(
        description="Unique identifier for this evidence record."
    )
    claim: str = Field(
        description="The claim or data point being supported."
    )
    value: Optional[Any] = Field(
        default=None,
        description="The observed value, if applicable (e.g., a price).",
    )
    unit: Optional[str] = Field(
        default=None,
        description="Unit of measurement for the value, if applicable.",
    )
    frequency: Optional[str] = Field(
        default=None,
        description=(
            "Payment frequency when the value is a price: "
            "'monthly', 'one-time', 'annual', or None if unknown."
        ),
    )
    source_url: Optional[str] = Field(
        default=None,
        description="URL or document where the evidence was found.",
    )
    snippet: Optional[str] = Field(
        default=None,
        description="A short fragment from the source that supports the claim.",
    )
    date_observed: Optional[str] = Field(
        default=None,
        description="Date when the evidence was observed or recorded.",
    )
    geo_scope: Optional[str] = Field(
        default=None,
        description="Geographic scope to which the evidence applies.",
    )
    limitations: Optional[str] = Field(
        default=None,
        description="Known limitations or caveats about the evidence.",
    )

    @model_validator(mode="after")
    def require_claim(self) -> "Evidence":
        if not self.claim or not self.claim.strip():
            raise ValueError("Evidence must have a non-empty 'claim'.")
        return self


class Competitor(BaseModel):
    """Identifies a competitor business that could affect the gym/ludoteca venture.

    Fields where the source does not provide data should be `null` or empty
    lists, never inferred or faked.
    """

    identifier: Optional[str] = Field(
        default=None,
        description="Stable identifier for the competitor (e.g., domain or ID).",
    )
    name: Optional[str] = Field(
        default=None,
        description="Name of the competitor business.",
    )
    location: Optional[str] = Field(
        default=None,
        description="City / neighborhood / address of the competitor.",
    )
    services: List[str] = Field(
        default_factory=list,
        description="List of services offered by the competitor.",
    )
    tariffs: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Tariff/pricing information with conditions.",
    )
    evidences: List[Evidence] = Field(
        default_factory=list,
        description="Evidence records that justify the competitor data.",
    )
    postal_code: Optional[str] = Field(
        default=None,
        description="Postal code of the premises, when the source provides it.",
    )
    latitude: Optional[float] = Field(
        default=None,
        description=(
            "Latitude in WGS84 decimal degrees (EPSG:4326). The municipal registry "
            "publishes EPSG:25830 metres; the conversion is documented in the "
            "evidence. None when the source has no usable coordinates."
        ),
    )
    longitude: Optional[float] = Field(
        default=None,
        description="Longitude in WGS84 decimal degrees (EPSG:4326).",
    )
    census_section: Optional[str] = Field(
        default=None,
        description="Census section assigned to the premises by the registry.",
    )
    license_status: Optional[str] = Field(
        default=None,
        description=(
            "Administrative status of the activity licence, verbatim from the "
            "source. None means 'no information available', never 'denied'."
        ),
    )
    license_type: Optional[str] = Field(
        default=None,
        description="Type of activity licence, verbatim from the source.",
    )
    license_date: Optional[str] = Field(
        default=None,
        description="Date declared in the licence record (source wording).",
    )
    has_playroom: Optional[bool] = Field(
        default=None,
        description=(
            "True/False only with reliable evidence that the service is or is not "
            "offered. None means unknown: the source does not mention it."
        ),
    )
    verification_status: Optional[str] = Field(
        default=None,
        description=(
            "Verification status of the official identity data: 'verified', "
            "'unverified' or 'unavailable'. Commercial data (price, playroom) "
            "carries its own evidence and limitation."
        ),
    )
    consulted_at: Optional[str] = Field(
        default=None,
        description="ISO timestamp of the last retrieval of this record.",
    )

    @model_validator(mode="after")
    def normalize_coordinates(self) -> "Competitor":
        """Treat missing or implausible coordinates as unavailable.

        The municipal registry uses 0,0 for premises without georeferenced
        position, and only publishes EPSG:25830 metres for the rest. Values
        outside the UTM 30N envelope of the Community of Madrid are rejected
        so that they are never used for distances or clustering.
        """
        lat, lon = self.latitude, self.longitude
        if lat is None or lon is None:
            self.latitude = None
            self.longitude = None
            return self
        if not (-90.0 <= lat <= 90.0 and -180.0 <= lon <= 180.0):
            self.latitude = None
            self.longitude = None
            return self
        # 0,0 and the Gulf of Guinea are the classic "no data" markers.
        if abs(lat) < 1e-6 and abs(lon) < 1e-6:
            self.latitude = None
            self.longitude = None
        return self

    @model_validator(mode="after")
    def normalize_services(self) -> "Competitor":
        services = self.services or []
        self.services = [
            s.strip() for s in services if s and s.strip()
        ] or []
        return self

    @model_validator(mode="after")
    def normalize_tariffs(self) -> "Competitor":
        tariffs = self.tariffs or []
        if tariffs:
            normalized = []
            for t in tariffs:
                if isinstance(t, dict) and t.get("value") is not None:
                    normalized.append(
                        {
                            "value": t["value"],
                            "unit": t.get("unit"),
                            "condition": t.get("condition", ""),
                            "frequency": t.get("frequency", ""),
                        }
                    )
                else:
                    normalized.append(
                        {
                            "value": None,
                            "unit": None,
                            "condition": str(t) if t else "",
                            "frequency": "",
                        }
                    )
            self.tariffs = normalized
        else:
            self.tariffs = []
        return self


class ResearchBrief(BaseModel):
    """The investigation brief: what must be researched and within what bounds.

    This is the contract passed to `run_research(brief, context)`.
    """

    business_type: str = Field(
        description="Type of business being researched (e.g., 'gimnasio con ludoteca')."
    )
    location: str = Field(
        description="City or neighborhood where the business will operate."
    )
    study_area: str = Field(
        description="Specific area or district within the city."
    )
    questions: List[str] = Field(
        default_factory=list,
        description="Explicit questions the investigation must answer.",
    )
    assumed_params: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Assumptions about the market, demographics, etc.",
    )
    search_limits: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Configurable limits: max_results, max_pages, timeout, etc.",
    )
    assumed: bool = Field(
        default=False,
        description="Whether the brief contains assumed/placeholder data.",
    )
    missing_variables: List[str] = Field(
        default_factory=list,
        description=(
            "Variables that the research still needs and that are not covered by "
            "the available sources. When present, the researcher runs a source "
            "discovery pass and returns the candidates as evidences."
        ),
    )

    @model_validator(mode="after")
    def normalize_spaces(self) -> "ResearchBrief":
        """Strip whitespace from string fields and reject blank inputs."""
        for field_name in ["business_type", "location", "study_area"]:
            if getattr(self, field_name, None):
                setattr(self, field_name, getattr(self, field_name).strip())
        return self

    @model_validator(mode="after")
    def reject_blank_questions(self) -> "ResearchBrief":
        """Filter out empty questions after stripping."""
        self.questions = [
            q.strip() for q in self.questions if q and q.strip()
        ] or []
        return self


class ResearchResult(BaseModel):
    """The result of a research investigation.

    Contains evidences, competitors found, coverage info, and unresolved questions.
    """

    evidences: List[Evidence] = Field(
        default_factory=list,
        description="All evidence gathered during the investigation.",
    )
    competitors: List[Competitor] = Field(
        default_factory=list,
        description="Competitors identified with supporting data.",
    )
    coverage_percentage: float = Field(
        default=0.0,
        description="Estimated coverage of the requested questions (0-100).",
    )
    unresolved_questions: List[str] = Field(
        default_factory=list,
        description="Questions from the brief that could not be answered.",
    )
    search_performed: str = Field(
        default_factory=str,
        description="Human-readable summary of what was searched.",
    )
    notes: str = Field(
        default="",
        description="Additional notes about the investigation process.",
    )

    @model_validator(mode="after")
    def set_defaults_on_success(self) -> "ResearchResult":
        """Ensure coverage is in [0,100] and unresolved questions are a list."""
        self.coverage_percentage = max(
            0.0, min(100.0, self.coverage_percentage)
        )
        if self.unresolved_questions is None:
            self.unresolved_questions = []
        elif not isinstance(self.unresolved_questions, list):
            self.unresolved_questions = [str(self.unresolved_questions)]
        else:
            self.unresolved_questions = [
                q for q in self.unresolved_questions if q
            ]
        return self