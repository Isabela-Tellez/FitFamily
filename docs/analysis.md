# Análisis de mercado y escenarios

Responsable: **Laura (Persona 2)**.

Este módulo convierte datos de competidores en indicadores descriptivos y calcula el número mínimo de clientes para cubrir costes. No inventa datos: los valores ausentes se mantienen como desconocidos.

## Archivos

| Archivo | Contenido |
|---|---|
| `src/analysis/market_analysis.py` | `normalize_playroom_value`, `summarize_competitors` |
| `src/analysis/scenarios.py` | `calculate_break_even_clients` |
| `tests/test_market_analysis.py` | Pruebas de normalización y resumen |
| `tests/test_scenarios.py` | Pruebas de punto de equilibrio y validaciones |

## `summarize_competitors`

```python
def summarize_competitors(data: pd.DataFrame) -> dict:
    ...
```

**Entrada.** Un `DataFrame` con estas columnas obligatorias:

- `gym_name`: nombre del competidor.
- `monthly_price_eur`: cuota mensual en euros.
- `has_playroom`: ludoteca (`True`/`False`, texto o valor ausente).

Si falta alguna columna, lanza `ValueError` con la lista de columnas que faltan.

**Normalización de precios.** `pd.to_numeric(..., errors="coerce")`; los valores no numéricos o ausentes pasan a `NaN` y no se inventan.

**Normalización de ludoteca.** `normalize_playroom_value` acepta:

| Entrada | Resultado |
|---|---|
| `True` / `False` | El mismo booleano |
| `"sí"`, `"si"`, `"true"` (sin distinguir mayúsculas) | `True` |
| `"no"`, `"false"` | `False` |
| `None`, `NaN` o texto no reconocido | `None` |

**Salida.**

| Clave | Significado |
|---|---|
| `competitor_count` | Número de filas |
| `known_price_count` | Filas con precio numérico |
| `average_monthly_price_eur` | Media redondeada a 2 decimales, o `None` si no hay precios |
| `playroom_yes_count` | Competidores con ludoteca confirmada |
| `playroom_no_count` | Competidores sin ludoteca confirmada |
| `playroom_unknown_count` | Competidores sin dato de ludoteca |

**Ejemplo.**

```python
import pandas as pd
from src.analysis.market_analysis import summarize_competitors

data = pd.DataFrame([
    {"gym_name": "A", "monthly_price_eur": 39.9, "has_playroom": "sí"},
    {"gym_name": "B", "monthly_price_eur": 45.0, "has_playroom": "no"},
    {"gym_name": "C", "monthly_price_eur": None, "has_playroom": None},
])

summary = summarize_competitors(data)
# {
#     "competitor_count": 3,
#     "known_price_count": 2,
#     "average_monthly_price_eur": 42.45,
#     "playroom_yes_count": 1,
#     "playroom_no_count": 1,
#     "playroom_unknown_count": 1,
# }
```

## `calculate_break_even_clients`

```python
def calculate_break_even_clients(
    fixed_costs: float,
    monthly_fee: float,
    variable_cost_per_client: float,
) -> int:
    ...
```

Calcula:

```text
margen por cliente = cuota mensual − coste variable por cliente
clientes mínimos   = ceil(costes fijos / margen por cliente)
```

**Validaciones.**

- Todos los importes deben ser números finitos.
- Ningún importe puede ser negativo.
- El margen por cliente debe ser estrictamente positivo; si no, no existe punto de equilibrio finito y lanza `ValueError`.

**Ejemplo.**

```python
from src.analysis.scenarios import calculate_break_even_clients

calculate_break_even_clients(
    fixed_costs=3000,
    monthly_fee=40,
    variable_cost_per_client=5,
)
# 86 clientes
```

## Relación con la investigación

`summarize_competitors` **no consume directamente** un `ResearchResult`. Hoy necesita un `DataFrame` con las columnas indicadas. El adaptador desde `ResearchResult` (y desde el registro de competidores) es una pieza pendiente:

```text
ResearchResult ──► adaptador pendiente ──► DataFrame ──► summarize_competitors
Registro de competidores ──► DataFrame ──► summarize_competitors
```

Mientras no exista el adaptador, el análisis se ejecuta con datos preparados o con un `DataFrame` construido explícitamente.

## Limitaciones

- El resumen es descriptivo; no hace inferencia estadística ni segmentación.
- La media de precios solo considera valores conocidos; no imputa los ausentes.
- El punto de equilibrio usa un modelo mensual simple: no incluye impuestos, financiación, inflación ni estacionalidad.
- No hay análisis de sensibilidad automático; se pueden calcular escenarios alternativos llamando a la función con otros supuestos.
- `coverage_percentage` del `ResearchResult` sigue siendo `0.0`; no hay evaluación de cobertura.

## Pruebas

```bash
python -m pytest tests/test_market_analysis.py tests/test_scenarios.py -q
```
