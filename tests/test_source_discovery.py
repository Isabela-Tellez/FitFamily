"""Tests for the source discovery tool (Persona 1 - Juan).

All unit tests use simulated responses: no network access.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from unittest.mock import patch

from src.tools.source_discovery import (
    build_queries,
    check_variable,
    discover_sources,
    extract_table,
    looks_like_dataset,
    required_terms,
    summarize,
)


class _Result:
    def __init__(self, url, title=""):
        self.url = url
        self.title = title
        self.snippet = ""


class _Page:
    def __init__(self, body_text):
        self.body_text = body_text
        self.title = "titulo"


def test_build_queries_covers_several_formulations():
    queries = build_queries("renta neta media por seccion censal", "El Cañaveral, Madrid")
    assert len(queries) >= 4
    assert queries[0].startswith("renta neta media por seccion censal")
    assert any("datos abiertos" in q for q in queries)
    assert any("site:ine.es" in q for q in queries)
    assert any("site:datos.madrid.es" in q for q in queries)
    # No hay duplicados.
    assert len(set(queries)) == len(queries)


def test_build_queries_without_variable_is_empty():
    assert build_queries("") == []


def test_required_terms_ignores_generic_words():
    terms = required_terms("datos de renta media")
    assert "renta" in terms
    assert "datos" not in terms


def test_looks_like_dataset_separates_pages_from_resources():
    assert looks_like_dataset("https://datos.madrid.es/dataset/200085-0-censo-locales")
    assert looks_like_dataset("https://example.com/descargas/datos.csv")
    assert looks_like_dataset("https://example.com/api/v1/datos")
    assert not looks_like_dataset("https://www.ejemplo.es/noticia-de-prensa")
    # Una pagina que lo anuncia tambien se detecta por su contenido.
    assert looks_like_dataset("https://www.ejemplo.es/datasets", "Descargar CSV y JSON")


def test_extract_table_from_csv_text():
    rows = extract_table("seccion;poblacion\n19052;2091\n19053;2414")
    assert len(rows) == 2
    assert rows[0]["poblacion"] == "2091"


def test_extract_table_from_html():
    html = ("<table><tr><th>seccion</th><th>renta</th></tr>"
            "<tr><td>19052</td><td>31200</td></tr></table>")
    rows = extract_table(html)
    assert rows and rows[0]["seccion"] == "19052"


def test_check_variable_requires_the_key_terms():
    ok = check_variable("Renta neta media por seccion censal de los hogares", "renta neta media")
    assert ok["covered"] is True
    ko = check_variable("Poblacion total del municipio", "renta neta media")
    assert ko["covered"] is False
    assert "no menciona" in ko["reason"]
    # Whole words: "rentabilidad" is not the variable "renta".
    assert check_variable("Informe de rentabilidad del sector", "renta media")["covered"] is False


def test_discover_sources_marks_states_and_keeps_traceability():
    pages = {
        "https://datos.madrid.es/dataset/300557-0-poblacion-distrito-barrio": _Page(
            "Poblacion por distrito y barrio a 1 de enero. Descargas en CSV."),
        "https://www.ejemplo.es/renta-media": _Page("Un articulo sobre el precio de la vivienda en la zona."),
    }

    def fake_search(query, max_results=5):
        if "site:" in query:
            return []
        return [
            _Result("https://datos.madrid.es/dataset/300557-0-poblacion-distrito-barrio",
                    "Poblacion por distrito y barrio"),
            _Result("https://www.ejemplo.es/renta-media", "Renta media"),
        ]

    def fake_read(url):
        return pages[url]

    results = discover_sources(
        "renta neta media por seccion censal", "El Cañaveral",
        search_callable=fake_search, read_callable=fake_read,
    )
    by_url = {r["url"]: r for r in results if r["url"]}
    dataset = by_url["https://datos.madrid.es/dataset/300557-0-poblacion-distrito-barrio"]
    assert dataset["state"] in ("accessible", "extracted", "validated")
    assert dataset["is_dataset"] is True
    assert dataset["organism"] == "datos.madrid.es"
    assert dataset["query"]
    # La pagina que no menciona la variable no se da por validada.
    article = by_url["https://www.ejemplo.es/renta-media"]
    assert article["state"] != "validated"


def test_discover_sources_uses_alternative_queries_when_one_fails():
    calls = []

    def fake_search(query, max_results=5):
        calls.append(query)
        if len(calls) == 1:
            raise RuntimeError("provider caido")
        return [_Result("https://datos.gob.es/es/catalogo/adrh", "Atlas de Distribucion de Renta")]

    def fake_read(url):
        return _Page("Renta neta media por seccion censal de los hogares. CSV.")

    results = discover_sources("renta neta media por seccion censal", "Madrid",
                               search_callable=fake_search, read_callable=fake_read)
    assert len(calls) > 1
    rejected = [r for r in results if r["state"] == "rejected"]
    assert rejected and "fallo" in rejected[0]["reason"]
    validated = [r for r in results if r["state"] == "validated"]
    assert validated and validated[0]["url"] == "https://datos.gob.es/es/catalogo/adrh"
    assert validated[0]["organism"] == "datos.gob.es"


def test_discover_sources_rejects_inaccessible_resources():
    def fake_search(query, max_results=5):
        return [_Result("https://datos.gob.es/es/catalogo/x", "Dataset")]

    def fake_read(url):
        raise RuntimeError("HTTP 404")

    results = discover_sources("renta media", "Madrid",
                               search_callable=fake_search, read_callable=fake_read)
    assert results[0]["state"] == "rejected"
    assert "No se pudo acceder" in results[0]["reason"]
    assert summarize(results) == {"rejected": 1}


def test_discover_sources_reports_empty_queries():
    def fake_search(query, max_results=5):
        return []

    results = discover_sources("variable inexistente", "Madrid",
                               search_callable=fake_search, read_callable=lambda u: _Page(""))
    assert results
    assert all(r["state"] == "rejected" for r in results)
    assert "no devolvio resultados" in results[0]["reason"]


def test_research_flow_still_works_after_the_changes():
    """El flujo de investigacion no se rompe por los cambios."""
    from src.schemas import ResearchBrief
    from src.agents.researcher import run_research
    from src.tools.search_web import SearchResult

    with patch("src.agents.researcher.search_web", return_value=[
        SearchResult(title="Gimnasio", url="https://example.com/gym", snippet="s", provider="ddgs")
    ]), patch("src.agents.researcher.competitor_search",
              return_value={"competitors": [], "evidences": []}):
        brief = ResearchBrief(business_type="gimnasio con ludoteca", location="Madrid",
                              study_area="El Cañaveral", questions=["precios"])
        result = run_research(brief)
    assert result.evidences
    assert result.evidences[0].source_url == "https://example.com/gym"


def test_brief_with_missing_variables_returns_discovered_sources():
    """Las variables pendientes disparan una busqueda de fuentes trazable."""
    from src.schemas import ResearchBrief
    from src.agents.researcher import run_research
    from src.tools.source_discovery import discover_sources

    candidates = [{
        "url": "https://datos.madrid.es/dataset/300557-0-poblacion-distrito-barrio",
        "title": "Poblacion por distrito y barrio",
        "query": "poblacion por barrio",
        "organism": "datos.madrid.es",
        "variable": "poblacion",
        "state": "validated",
        "reason": "Contiene los terminos clave de la variable.",
        "is_dataset": True,
        "matched_terms": ["poblacion"],
    }]

    with patch("src.agents.researcher.search_web", return_value=[]), \
         patch("src.agents.researcher.competitor_search",
               return_value={"competitors": [], "evidences": []}), \
         patch("src.tools.source_discovery.discover_sources", return_value=candidates):
        brief = ResearchBrief(business_type="gimnasio con ludoteca", location="Madrid",
                              study_area="El Cañaveral",
                              missing_variables=["poblacion por barrio"])
        result = run_research(brief)

    sources = [e for e in result.evidences if e.source_url and "datos.madrid.es" in e.source_url]
    assert sources
    assert "validated" in sources[0].claim
    assert sources[0].limitations


def test_discovery_respects_brief_limits_and_produces_stable_ids():
    """The brief limit reaches the search and the evidence ids are reproducible."""
    from src.schemas import ResearchBrief
    from src.agents.researcher import discover_sources_for_brief

    candidates = [{
        "url": "https://datos.madrid.es/dataset/300557-0-poblacion-distrito-barrio",
        "title": "Poblacion por distrito y barrio",
        "query": "poblacion por barrio",
        "organism": "datos.madrid.es",
        "variable": "poblacion por barrio",
        "state": "validated",
        "reason": "Contiene los terminos clave de la variable.",
        "is_dataset": True,
        "matched_terms": ["poblacion"],
    }]
    captured = {}

    def fake_discover(variable, area=None, max_results_per_query=None):
        captured["max_results"] = max_results_per_query
        return candidates

    brief = ResearchBrief(
        business_type="gimnasio con ludoteca",
        location="Madrid",
        study_area="El Cañaveral",
        missing_variables=["poblacion por barrio"],
        search_limits={"max_results": 3},
    )
    with patch("src.tools.source_discovery.discover_sources", side_effect=fake_discover):
        first = discover_sources_for_brief(brief)
        second = discover_sources_for_brief(brief)

    assert captured["max_results"] == 3
    assert [e.evidence_id for e in first] == [e.evidence_id for e in second]
    assert first[0].evidence_id.startswith("source_poblacion_por_barrio_")
