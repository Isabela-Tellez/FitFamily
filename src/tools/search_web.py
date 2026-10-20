"""Search web tool for the FitFamily research module.

Provides the `search_web(query, max_results)` function used by the
investigator agent to find competitor and market information.

Responsibilities:
- Validate the query and max_results parameters.
- Use a real, maintained search provider.
- Return links and metadata in a structured format.
- Preserve the original URL and provider data when available.
- Handle errors of connection, provider limits and invalid responses.
- Apply a maximum of results configurable but bounded.

Exploration order for search providers:
1. If TAVILY_API_KEY is set in environment, use tavily-python (preferred if key available).
2. Use DuckDuckGo via ddgs library (fallback when no tavily key).
3. If no search provider is available, raise a clear error.

Never include real credentials in the repository. Never simulate search results
in the production implementation. If the search service is not available,
return a clear error that the investigation cannot proceed without network access.
"""

from __future__ import annotations

import json
import logging
import os
from typing import List, Dict, Any, Optional

from pydantic import BaseModel, Field, model_validator

logger = logging.getLogger(__name__)


# ── Configuración y detección de proveedores ──────────────────────────────

# Intentar importar tavily-python; si no está instalado, quedará como None
try:
    import tavily
    TAVILY_AVAILABLE = True
except ImportError:
    TAVILY_AVAILABLE = False

try:
    from ddgs import DDGS
    DDGS_AVAILABLE = True
except ImportError:
    DDGS_AVAILABLE = False

# Determinar qué proveedor usar por defecto
# Prioridad: tavily (si tiene key) > ddgs (siempre que esté instalado)
_SEARCH_PROVIDER: Optional[str] = None


def _get_search_provider() -> str:
    """Determine which search provider to use.

    Returns:
        'tavily' if Tavily API key is configured,
        'ddgs' if DuckDuckGo is available and Tavily is not,
        'none' if no provider is available.
    """
    global _SEARCH_PROVIDER
    if _SEARCH_PROVIDER is not None:
        return _SEARCH_PROVIDER

    # 1. Intentar Tavily si tiene clave configurada
    tavily_key = os.environ.get("TAVILY_API_KEY")
    if tavily_key and TAVILY_AVAILABLE:
        _SEARCH_PROVIDER = "tavily"
        logger.info("Using Tavily search provider (API key configured)")
        return _SEARCH_PROVIDER

    # 2. Fallback a DuckDuckGo via ddgs
    if DDGS_AVAILABLE:
        _SEARCH_PROVIDER = "ddgs"
        logger.info("Using DuckDuckGo (ddgs) search provider")
        return _SEARCH_PROVIDER

    # 3. Ningún proveedor disponible
    _SEARCH_PROVIDER = "none"
    logger.warning("No search provider available (neither Tavily nor ddgs)")
    return "none"


# ── Modelo de resultado estructurado ──────────────────────────────────────

class SearchResult(BaseModel):
    """Estructurado resultado de una búsqueda web."""

    title: str = Field(description="Título del resultado de búsqueda.")
    url: str = Field(description="URL original del resultado de búsqueda.")
    snippet: str = Field(
        description="Fragmento o descripción meta del resultado de búsqueda."
    )
    provider: str = Field(
        default="unknown", description="Proveedor de búsqueda utilizado."
    )
    retrieved_at: str = Field(
        default_factory=lambda: __import__("datetime").datetime.now().isoformat(),
        description="Marca de tiempo ISO cuándo se recuperó el resultado.",
    )

    @model_validator(mode="after")
    def validate_url_scheme(self) -> "SearchResult":
        """Asegurar que la URL empieza con http:// o https://."""
        if self.url and not self.url.lower().startswith(("http://", "https://")):
            raise ValueError(f"URL must start with http:// or https://, got: {self.url}")
        return self


# ── Funciones auxiliares ──────────────────────────────────────────────────

def _normalize_url(url: str) -> str:
    """Normalizar URL para deduplicación: quita parámetros de tracking y minusculas."""
    if not url:
        return ""
    # Eliminar fragmentos (parte después de #)
    url = url.split("#")[0]
    # Eliminar parámetros de tracking comunes de Google/DDG
    from urllib.parse import urlparse, parse_qsl, urlencode
    parsed = urlparse(url)
    # Mantener solo los parámetros esenciales
    query = dict(parse_qsl(parsed.query))
    # Quitar tracking well conocido
    for key in ["utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content"]:
        query.pop(key, None)
    query_string = urlencode(query)
    normalized = f"?{query_string}" if query_string else ""
    return f"{parsed.scheme}://{parsed.netloc}{parsed.path}{normalized}"


# ── Motor de búsqueda Tavily ──────────────────────────────────────────────

def _search_tavily(query: str, max_results: int = 10) -> List[Dict[str, Any]]:
    """Buscar usando la API de Tavily.

    Requiere que TAVILY_API_KEY esté configurada en el entorno.

    Args:
        query: La consulta de búsqueda.
        max_results: Número máximo de resultados a devolver.

    Returns:
        Lista de diccionarios con claves 'title', 'url', 'snippet'.
    """
    if not os.environ.get("TAVILY_API_KEY"):
        raise RuntimeError("TAVILY_API_KEY no configurada en el entorno")

    try:
        import tavily as tly
        client = tly.TavilyClient(api_key=os.environ["TAVILY_API_KEY"])
        response = client.search(query, max_results=max_results)
        # Normalizar resultados: la API de Tavily devuelve dicts con 'title', 'url', 'content'
        results = []
        for item in response.get("results", []):
            results.append(
                {
                    "title": item.get("title", ""),
                    "url": item.get("url", ""),
                    "snippet": item.get("content", ""),
                }
            )
        return results
    except Exception as e:
        logger.error(f"Error en búsqueda Tavily: {e}")
        raise


# ── Motor de búsqueda DuckDuckGo (ddgs) ───────────────────────────────────

def _search_ddgs(query: str, max_results: int = 10) -> List[Dict[str, Any]]:
    """Buscar usando DuckDuckGo via la librería ddgs.

    Args:
        query: La consulta de búsqueda.
        max_results: Número máximo de resultados a devolver.

    Returns:
        Lista de diccionarios con claves 'title', 'url', 'snippet'.
    """
    results: List[Dict[str, Any]] = []
    try:
        with DDGS() as ddgs:
            # Usar el método text de ddgs (la API ha cambiado)
            # No pasar timeout parámetro ya que ddgs no lo acepta
            search_iter = ddgs.text(query, max_results=max_results)
            for idx, result in enumerate(search_iter):
                if idx >= max_results:
                    break
                if result.get("href"):
                    results.append(
                        {
                            "title": result.get("title", ""),
                            "url": result.get("href"),
                            "snippet": result.get("body", ""),
                        }
                    )
    except Exception as e:
        logger.error(f"Error en búsqueda DDGS: {e}")
        raise
    return results


# ── Función pública ───────────────────────────────────────────────────────

def search_web(query: str, max_results: int = 10) -> List[SearchResult]:
    """Search the web for a given query and return structured results.

    Args:
        query: The search query string.
        max_results: Maximum number of results to return (default: 10, max: 20).

    Returns:
        A list of SearchResult objects containing title, URL, snippet, and provider.

    Raises:
        ValueError: If the query is empty or max_results is out of bounds.
        RuntimeError: If no search provider is available or the provider fails.
    """
    # Validar query
    if not query or not query.strip():
        raise ValueError("Search query must be a non-empty string.")

    # Validar max_results
    if not isinstance(max_results, int) or max_results < 1:
        raise ValueError("max_results must be a positive integer.")
    if max_results > 20:
        logger.warning(f"max_results capped from {max_results} to 20")
        max_results = 20

    # Determinar qué proveedor usar
    provider = _get_search_provider()

    # Si no hay proveedor disponible, fallar explicítamente
    if provider == "none":
        raise RuntimeError(
            "No search provider available. "
            "Set TAVILY_API_KEY environment variable to use Tavily, "
            "or ensure ddgs is installed for DuckDuckGo support."
        )

    # Ejecutar búsqueda según el proveedor seleccionado
    try:
        if provider == "tavily":
            raw_results = _search_tavily(query, max_results=max_results)
        else:  # ddgs
            raw_results = _search_ddgs(query, max_results=max_results)

        # Construir resultados estructurados
        search_results: List[SearchResult] = []
        seen_urls: set = set()

        for item in raw_results:
            if len(search_results) >= max_results:
                break

            url = item.get("url", "") or item.get("href", "")
            normalized_url = _normalize_url(url)

            # Deduplicar por URL normalizada
            if normalized_url.lower() in seen_urls:
                continue
            seen_urls.add(normalized_url.lower())

            title = item.get("title", "").strip()
            snippet = item.get("snippet", "").strip()

            # Saltar si no hay título ni URL
            if not title and not url:
                continue

            search_result = SearchResult(
                title=title,
                url=url,
                snippet=snippet,
                provider=provider,
            )
            search_results.append(search_result)

        logger.info(f"Search completed: provider={provider}, query='{query[:60]}...', results={len(search_results)}")
        return search_results

    except Exception as e:
        logger.error(f"Search failed for query '{query}': {e}")
        raise RuntimeError(
            f"Search provider failed: {e}. "
            "Check your network connectivity and that the search service is available."
        ) from e