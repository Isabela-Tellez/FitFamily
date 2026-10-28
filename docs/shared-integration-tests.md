# Pruebas compartidas: Laura, Gema, María e Isabella

Base inspeccionada: dev 6d38f55, ZIP del 28 de octubre de 2026.
Solo se añaden dos archivos de pruebas y este registro. No cambian los nodos,
contratos, cálculos, redactores ni configuración de pytest.

## Ejecutar ahora

python -m pytest tests/test_shared_report_integration.py -q

Diez casos: constructor con use_llm=True (solo proveedor simulado),
texto/campos/notas, Markdown, recorrido JSON con reconstrucción explícita
de ReportClaim, vigencia del contexto, rutas y límite de revisiones,
notas omitidas y resultado no disponible. No consulta Internet ni consume API.

La reconstrucción JSON del test demuestra el contrato correcto; NO prueba
que el workflow actual ya lo implemente. Para eso está el bloque siguiente.
El constructor y revisor reales se ejecutan sin mocks.

## Aceptación del workflow cuando Isabella lo actualice

python -m pytest tests/workflow_shared_acceptance.py -vv

El nombre no comienza por test_: no se ejecuta automáticamente en la suite
habitual. Se ejecuta explícitamente contra la nueva versión de Isabella.
No se ocultan fallos con xfail ni se consideran implementaciones completas
unos tests que solo compilan el grafo.

Tres comprobaciones de los nodos reales:
1. El análisis conserva cuatro cálculos originales y una métrica contextual
   de punto de equilibrio con identidad de escenario.
2. La redacción incorpora esa métrica mediante el constructor de Gema.
3. La revisión reconstruye las afirmaciones y ejecuta el revisor real.

En 6d38f55 estas tres conexiones están pendientes: los fallos son criterios
de aceptación, no motivo para modificar el workflow desde la rama de María.

## Cierre todavía pendiente

Estas pruebas no ejecutan todo LangGraph ni una aprobación/entrega completa.
Cuando Isabella defina dónde devuelve la ruta y guarda revision_count, añadir
la prueba del nodo que conserve revise_research/revise_analysis/revise_writing
y blocked. No inventar ahora nombres de campos de su estado.

Antes de aprobación, comprobar las huellas con el contexto actualizado.
La UI debe conservar la decisión humana explícita; pending_review no es aprobación.
La redacción libre del LLM sigue necesitando revisión humana.

## Registro de integración

- CalculationResult, escenario, adaptador y revisor: presentes en el ZIP.
- build_break_even_claim y build_report con calculated_metrics: presentes.
- Rama de María: feature/review-quality; merge comunicado como up to date.
- Nuevos avances posteriores a 6d38f55: no inspeccionados.
- Paquete documental anterior: en pausa; no aplicar sobre esta base sin actualizarlo.
- Esta entrega no sustituye ni duplica tests/test_calculated_claims.py:
  amplía el contrato con llamada LLM simulada, serialización y rutas.

Pruebas amplias y recorrido de entrega: reservar para el cierre de integración.
