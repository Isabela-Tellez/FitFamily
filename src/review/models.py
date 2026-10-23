"""Modelos del resultado de revisión de FitFamily."""

from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True)
class ReviewIssue:
    """Un problema localizado durante la revisión."""

    code: str
    reference_id: str
    message: str
    severity: Literal["error", "warning"]
    correction_stage: Literal["research", "analysis", "writing"]


@dataclass(frozen=True)
class ReviewResult:
    """
    Resultado de las comprobaciones de un borrador concreto.

    No concede aprobación humana ni autoriza exportaciones.
    """

    draft_id: str
    draft_version: int
    draft_fingerprint: str
    issues: tuple[ReviewIssue, ...]
    checks_performed: tuple[str, ...]

    @property
    def status(self) -> Literal["needs_revision", "pending_review"]:
        """Calcula el estado a partir de las incidencias."""
        if any(issue.severity == "error" for issue in self.issues):
            return "needs_revision"

        return "pending_review"