from __future__ import annotations

from typing import Any

from app.models.project_health import DOMAIN_KEYS, OPENING_FIELD_KEYS, CoverageState

MIN_TEAM_TURNS = 10
MAX_TEAM_TURNS_HARD = 100


def create_initial_opening_field_state() -> dict[str, bool]:
    return dict.fromkeys(OPENING_FIELD_KEYS, False)


def create_initial_coverage_state() -> CoverageState:
    return CoverageState(
        domains_touched={},
        domains_with_evidence=[],
        suggested_next_domain=DOMAIN_KEYS[0],
        interview_phase="opening",
        turn_count=0,
        opening_fields=create_initial_opening_field_state(),
        missing_opening_fields=list(OPENING_FIELD_KEYS),
    )


def normalize_coverage_state(coverage: dict[str, Any] | None) -> CoverageState:
    base = create_initial_coverage_state()
    if not coverage:
        return base

    raw_fields = coverage.get("opening_fields") or {}
    opening_fields = {**base.opening_fields, **raw_fields}

    provided_missing = {
        field
        for field in coverage.get("missing_opening_fields") or []
        if field in OPENING_FIELD_KEYS
    }
    derived_missing = {field for field in OPENING_FIELD_KEYS if not opening_fields.get(field)}
    missing = [
        field
        for field in OPENING_FIELD_KEYS
        if field in provided_missing or field in derived_missing
    ]

    return CoverageState(
        domains_touched=coverage.get("domains_touched") or base.domains_touched,
        domains_with_evidence=coverage.get("domains_with_evidence") or base.domains_with_evidence,
        suggested_next_domain=coverage.get("suggested_next_domain"),
        interview_phase=coverage.get("interview_phase") or base.interview_phase,
        turn_count=int(coverage.get("turn_count") or 0),
        opening_fields=opening_fields,
        missing_opening_fields=missing,
    )


def get_covered_domains(coverage: CoverageState) -> list[str]:
    covered = set(coverage.domains_with_evidence)
    return [domain for domain in DOMAIN_KEYS if domain in covered]


def get_missing_domains(coverage: CoverageState) -> list[str]:
    covered = set(get_covered_domains(coverage))
    return [domain for domain in DOMAIN_KEYS if domain not in covered]


def get_missing_opening_fields(coverage: CoverageState) -> list[str]:
    return [field for field in OPENING_FIELD_KEYS if not coverage.opening_fields.get(field)]


def can_complete_interview(coverage: CoverageState, team_turn_count: int) -> bool:
    return (
        team_turn_count >= MIN_TEAM_TURNS
        and not get_missing_opening_fields(coverage)
        and not get_missing_domains(coverage)
    )


def can_force_complete_interview(coverage: CoverageState, team_turn_count: int) -> bool:
    """Looser gate used by the admin force-complete path. Requires the minimum
    number of team turns and all opening fields, but tolerates missing domain
    coverage so an admin can rescue interviews that stalled before reaching
    full breadth."""
    return team_turn_count >= MIN_TEAM_TURNS and not get_missing_opening_fields(coverage)
