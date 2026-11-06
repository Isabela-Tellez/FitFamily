"""Guarda un ResearchResult real (web + MCP) en JSON para que el equipo lo reutilice.

No modifica codigo compartido. Salida: data/raw/research_result_real.json
"""
import sys, asyncio, crewai  # noqa
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.agents.researcher import run_research
from src.schemas import ResearchBrief, Evidence
from src.mcp.client import connect_mcp, call_area_statistics
OUT = ROOT / "data" / "raw" / "research_result_real.json"
OUT.parent.mkdir(parents=True, exist_ok=True)

brief = ResearchBrief(
    business_type="gimnasio con ludoteca",
    location="Madrid",
    study_area="El Canaveral",
    questions=["Que competidores existen y que tarifas documentadas hay?"],
)

research = run_research(brief)

async def fetch_mcp():
    async with connect_mcp() as session:
        return await call_area_statistics(session, "El Canaveral", None)

mcp_result = asyncio.run(fetch_mcp())
for key, info in mcp_result.get("results", {}).items():
    if info.get("verification_status") == "verified" and info.get("value") is not None:
        research.evidences.append(Evidence(
            evidence_id=f"mcp_{key}",
            claim=f"{key}: {info['value']} {info['unit']}",
            value=info["value"],
            unit=info["unit"],
            source_url=info.get("source_url"),
            limitations=info.get("limitations", ""),
        ))

OUT.write_text(research.model_dump_json(indent=2), encoding="utf-8")
print("Guardado:", OUT)
print("Evidencias:", len(research.evidences), "Competidores:", len(research.competitors))
