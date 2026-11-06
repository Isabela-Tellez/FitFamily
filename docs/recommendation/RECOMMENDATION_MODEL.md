# Modelo de Recomendación — FitFamily Studio

**Estado**: Implementado (v1.2026-11-03-deterministic) — determinista, explicable, sin datos inventados.

## Objetivo
Evaluar oportunidad de negocio para gimnasio con ludoteca en El Cañaveral usando datos reales existentes.

## Datos de entrada reales
- Indicadores MCP (`mcp_ind_*`) — verificados / no disponibles documentados.
- Registro oficial de competidores (`data/processed/competitor_registry.json`) cargado y clasificado.
- Escenarios económicos (`analysis/economic_calculations.py`) con supuestos del usuario.
- Renta INE (`docs/pendiente-renta-ine.md`) — pendiente; no inventada.

## Variables de entrada
- `scenario_type`: intermediate / basic / optimistic.
- `expected_clients`: entero (supuesto del usuario).
- `monthly_fee`: EUR (supuesto del usuario).
- `fixed_costs`: EUR (supuesto del usuario).
- `variable_cost_per_client`: EUR (supuesto del usuario).

## Variables de salda
- `score_global`: 0-100 (cuando hay cobertura suficiente).
- `score_breakdown`: dimensiones (demanda, competencia, escenario, diferenciación).
- `recommendation`: `promising_conditional` / `review_needed` / `insufficient_evidence`.
- `factors_favorable`: basados en datos verificados.
- `factors_unfavorable`: basados en datos reales (competencia, falta de datos).
- `missing_evidence`: datos faltantes documentados (ej. renta INE, tarifas completas).
- `limitations`: restricciones metodológicas.
- `sources_used`: referencias de datos usados.
- `assumptions_used`: supuestos del usuario claramente etiquetados.

## Restricciones explícitas
- No garantiza rentabilidad.
- No sustituye estudio financiero completo.
- No inventa datos cuando faltan.
- No convierte supuestos en observaciones.
- No declara éxito si datos faltan.

## Integración
- `src/recommendation/service.py`: `recommend()` conecta datos.
- `src/ui/app.py`: pestaña de evaluación con controles reales.
- `docs/recommendation/RECOMMENDATION_MODEL.md`: este archivo.

## Validación
- Prueba con datos reales del proyecto (`fitfamily_approval_real.db` existente).
- Prueba con datos faltantes documentados.
- Prueba con archivo de competidores ausente.
- Prueba con valores extremos.

## Limitaciones conocidas
- Renta INE por sección censal: pendiente (`docs/pendiente-renta-ine.md`).
- Modelo predictivo con ML: fuera de alcance (no hay datos históricos suficientes).
- Tarifas de competidores: incompletas; no inventadas.
