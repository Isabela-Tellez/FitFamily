"""Presupuesto y conservación de contexto, sin llamadas a Groq."""

import json
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from crewai.hooks import HookAborted

from src.agents.writer_payload import compact_writer_payload, partition_writer_research
from src.agents.writer_budget import (
    WRITER_ROLE, WRITER_TASK_TOKEN_LIMIT, count_writer_tokens,
)
from src.agents.strategic_writer import (
    _writing_task_content, run_writing, count_writing_task_tokens,
)
from src.agents.writer_llm import remove_groq_cache_breakpoints
from src.reporting.models import ReportDraft, ReportClaim
from src.reporting.templates import REPORT_SECTION_TITLES, MISSING_SECTION_TEXT
from src.schemas import Competitor, Evidence, ResearchBrief, ResearchResult


@pytest.fixture
def brief():
    return ResearchBrief(business_type="gimnasio", location="Madrid", study_area="Zona de prueba")


def make_research(size):
    competitors = []
    for i in range(size):
        evidence = Evidence(
            evidence_id=f"local_{i}", claim=f"El registro {i} declara un gimnasio.",
            source_url=f"https://example.com/local/{i}",
            snippet="Actividad declarada; no acredita funcionamiento comercial.",
            limitations=f"Limitación del registro {i}: no acredita demanda.",
            geo_scope="Zona de prueba", date_observed="2026-10-21",
            value=0, unit="EUR", frequency="monthly",
        )
        competitors.append(Competitor(
            identifier=str(i), name=f"Local {i}", location=f"Calle {i}",
            services=["gimnasio"], evidences=[evidence], has_playroom=False,
        ))
    return ResearchResult(
        competitors=competitors, evidences=[e for c in competitors for e in c.evidences],
        search_performed="Lectura de un archivo guardado; sin consultas web.",
        notes="Muestra administrativa, sin verificación comercial.",
        unresolved_questions=["¿Existe demanda?"],
    )


def task_fits(brief, research):
    content = _writing_task_content(brief, research, None)
    return count_writing_task_tokens(content, "groq/openai/gpt-oss-120b") <= WRITER_TASK_TOKEN_LIMIT


def test_payload_deduplicates_without_losing_fields_or_mutating(brief):
    research = make_research(3)
    before = research.model_dump()
    payload = compact_writer_payload(brief, research)
    data = json.loads(payload)["research"]
    assert len(data["evidences"]) == 3
    assert "evidences" not in data["competitors"][0]
    assert data["competitors"][0]["evidence_ids"] == ["local_0"]
    assert data["competitors"][0]["has_playroom"] is False
    assert data["evidences"][0]["value"] == 0
    assert data["evidences"] == [e.model_dump(mode="json", exclude_none=True) for e in research.evidences]
    assert research.model_dump() == before
    assert len(payload) < len(json.dumps({"brief": brief.model_dump(), "research": before}, ensure_ascii=False))


def test_conflicting_evidence_is_rejected(brief):
    research = make_research(1)
    research.evidences = [research.evidences[0].model_copy(update={"claim": "Otra versión"})]
    with pytest.raises(ValueError, match="contradictoria"):
        compact_writer_payload(brief, research)


def test_large_research_batches_have_bounded_prompts_and_keep_every_record(brief):
    research = make_research(100)
    general = Evidence(evidence_id="general", claim="Dato general no ligado a un local.")
    research.evidences.append(general)
    batches = partition_writer_research(research, lambda r: task_fits(brief, r))
    assert len(batches) > 1
    assert all(task_fits(brief, batch) for batch in batches)
    assert [c.identifier for b in batches for c in b.competitors] == [str(i) for i in range(100)]
    assert {e.evidence_id for b in batches for e in b.evidences} == {e.evidence_id for e in research.evidences}
    for batch in batches:
        assert batch.notes == research.notes
        assert batch.search_performed == research.search_performed
        assert batch.unresolved_questions == research.unresolved_questions


def test_oversized_single_record_fails_before_generation(brief):
    research = make_research(1)
    research.evidences[0].snippet = "dato " * 20000
    with patch("src.agents.strategic_writer.build_writer") as agent, patch("src.agents.strategic_writer.Crew") as crew:
        agent.return_value.llm.model = "groq/openai/gpt-oss-120b"
        with pytest.raises(ValueError, match="registro individual"):
            run_writing(brief, research)
    crew.assert_not_called()


def test_batches_merge_sections_claim_ids_sources_and_limits(brief):
    research = make_research(20)
    visited = []

    def write_batch(brief, batch, agent):
        visited.extend(c.identifier for c in batch.competitors)
        records = batch.evidences
        return ReportDraft(
            title="Prueba", study_area=brief.study_area,
            sections=[title + "\n" + (
                "\n".join(e.claim for e in records) if title == "Competencia" else MISSING_SECTION_TEXT
            ) for title in REPORT_SECTION_TITLES],
            claims=[ReportClaim(claim_id=f"claim_{i}", text=e.claim, kind="fact", evidence_ids=[e.evidence_id]) for i, e in enumerate(records)],
            sources=[e.source_url for e in records], limitations=[e.limitations for e in records],
        )

    with patch("src.agents.strategic_writer.build_writer") as agent, patch("src.agents.strategic_writer._run_writing_single", side_effect=write_batch):
        agent.return_value.llm.model = "groq/openai/gpt-oss-120b"
        draft = run_writing(brief, research)
    assert visited == [str(i) for i in range(20)]
    assert len(draft.claims) == 20
    assert len({c.claim_id for c in draft.claims}) == 20
    assert len(draft.sources) == 20
    assert all(e.limitations in draft.limitations for e in research.evidences)
    assert len(draft.sections) == len(REPORT_SECTION_TITLES)


def test_cache_cleanup_preserves_content_and_other_providers():
    messages = [{"role": "system", "content": "Conservar", "cache_breakpoint": True}]
    context = SimpleNamespace(llm=SimpleNamespace(model="groq/test"), messages=messages, agent=None)
    remove_groq_cache_breakpoints(context)
    assert messages == [{"role": "system", "content": "Conservar"}]
    context.llm.model = "anthropic/test"
    messages[0]["cache_breakpoint"] = True
    remove_groq_cache_breakpoints(context)
    assert messages[0]["cache_breakpoint"] is True


def test_final_message_guard_includes_output_and_blocks_before_request():
    context = SimpleNamespace(
        llm=SimpleNamespace(model="groq/test", max_tokens=4096),
        messages=[{"role": "user", "content": "Largo"}],
        agent=SimpleNamespace(role=WRITER_ROLE),
    )
    with patch("src.agents.writer_llm.count_writer_tokens", return_value=4000), patch("src.agents.writer_llm.reserve_writer_tokens") as reserve:
        with pytest.raises(HookAborted, match="presupuesto"):
            remove_groq_cache_breakpoints(context)
    reserve.assert_not_called()


def test_local_rate_budget_waits_between_requests(monkeypatch):
    from src.agents import writer_budget as budget
    now = [0.0]
    waits = []
    monkeypatch.setattr(budget, "_reservations", budget.deque())
    monkeypatch.setattr(budget.time, "monotonic", lambda: now[0])

    def sleep(seconds):
        waits.append(seconds)
        now[0] += seconds

    monkeypatch.setattr(budget.time, "sleep", sleep)
    budget.reserve_writer_tokens(7000)
    budget.reserve_writer_tokens(7000)
    assert waits == [61]


def test_invalid_json_is_rejected_without_second_llm_call(brief):
    with patch("src.agents.strategic_writer.build_writer"), patch("src.agents.strategic_writer.build_writing_task"), patch("src.agents.strategic_writer.Crew") as crew:
        crew.return_value.kickoff.return_value.raw = '{"sections":'
        with pytest.raises(ValueError, match="JSON"):
            run_writing(brief, ResearchResult())
    crew.return_value.kickoff.assert_called_once()
