# PROMPT DE TRABAJO — FITFAMILY ENTERPRISE

Actúa como Staff Software Engineer, Product Designer y QA Lead especializado en Python, Streamlit, LangGraph, MCP, sistemas de evidencias y aplicaciones de investigación. Trabaja sobre el repositorio LOCAL de FitFamily, usando `feat/completado-limpio` como referencia. No des por hecho que la rama local está sincronizada con GitHub: inspecciona primero el disco y Git.

## Objetivo

Perfecciona la interfaz de FitFamily hasta convertirla en una aplicación Enterprise: visualmente potente, intuitiva para una persona no técnica, accesible, trazable, segura y estable. Debe ejecutar el flujo verdadero de investigación → MCP → análisis → redacción → revisión → aprobación humana → exportación. No construyas una demo paralela.

## Primera tarea: auditar antes de tocar

1. Ejecuta `git status --short`, `git branch --show-current`, `git log -5 --oneline` y revisa todos los cambios locales. No elimines ni sobrescribas trabajo ajeno.
2. Lee como mínimo `src/ui/app.py`, `src/ui/controller.py`, `src/ui/report_preview.py`, `src/graph/state.py`, `src/graph/workflow.py`, `src/graph/persistence.py`, `src/mcp/client.py`, `src/mcp/server.py`, `src/agents/researcher.py`, `src/tools/search_web.py`, `src/automation/models.py`, `src/automation/exporter.py`, `src/automation/delivery.py`, `src/review/quality_checks.py`, `src/graph/review_routes.py`, `src/reporting/report_builder.py`, `src/reporting/calculated_claims.py` y `src/analysis/calculation_adapter.py`.
3. Ejecuta la suite existente antes de cambiar nada y registra qué fallaba previamente.
4. Compara el paquete FitFamily Studio suministrado con el código local. Integra sus mejoras de forma selectiva; no copies ciegamente.

## Reglas de integridad — obligatorias

- No inventes métricas, cifras, periodos, competidores, tarifas, fuentes, resultados de tests, estados de proveedores ni puntuaciones.
- No hardcodees valores MCP en la UI. Consulta el servidor MCP real y recorre dinámicamente su respuesta.
- Un valor `null` debe seguir siendo «No disponible» con su limitación; jamás lo conviertas en cero, promedio o ausencia de servicio.
- Distingue de forma visible: observado, derivado/calculado, supuesto introducido por la persona, observación asistida por IA y no disponible.
- Respeta los periodos de referencia individuales. No mezcles, por ejemplo, población de 2026 con hogares de 2025 sin advertencia visible.
- No uses `coverage_percentage` como representatividad del mercado si el backend no lo define y calcula como tal.
- No afirmes que Tavily fue el proveedor si la ejecución usó DDGS u otro fallback. Muestra el proveedor que realmente se utilizó; si el backend no lo expone, añade trazabilidad para exponerlo o muestra «proveedor no identificado».
- Ninguna llamada web, MCP, agente o LLM debe ejecutarse al importar la app ni al cambiar de página. Solo bajo acciones explícitas. Añade timeout, mensajes accionables y política de reintento controlada.
- Nunca muestres claves API, variables `.env`, tokens o secretos en logs, errores, capturas o informes.
- Mantén intactos los módulos de dominio y los contratos existentes salvo que haya una razón técnica documentada y tests de regresión.

## Hallazgos del paquete inicial que debes resolver

1. `src/ui/app.py` usa `st.session_state` para conservar la aprobación y el puntero del estudio. El workflow sí usa SQLite, pero una recarga o una sesión nueva puede perder la aprobación visible. Persiste `ApprovalRecord`, decisión, huella, acciones, timestamp, resultado de entrega e identidad de ejecución en un registro durable (preferiblemente SQLite/auditoría ligado al `run_id`) y permite recuperar el historial de ejecuciones. No dependas solo de `st.session_state`.
2. La página de indicadores MCP consulta el servidor real por separado. Integra los indicadores MCP válidos al contexto de investigación/informe como evidencias estructuradas o como un anexo inequívoco del informe. Conserva valor, unidad, fuente, ámbito, periodo, fecha de consulta y limitaciones. Los indicadores sin valor no generan afirmaciones numéricas.
3. El área MCP debe provenir del encargo/selector de área, no de una constante interna. Si el servidor solo soporta El Cañaveral, comunica «área no soportada» y no extrapoles resultados.
4. El código de UI y el workflow deben estar cubiertos por pruebas ejecutables. Valida especialmente el estado real de los tests existentes: no declares «509 tests» ni porcentajes de cobertura a partir de texto estático.
5. El diseño carga fuentes tipográficas externas. Incluye fallback robusto y no hagas depender la UI de CDN; el contenido y controles deben seguir funcionando offline.

## Workflow y análisis

- `analysis_node` solo debe calcular cuando la persona ha introducido los parámetros completos. No rellenes valores por defecto silenciosos.
- Los parámetros de negocio introducidos en el formulario son `assumptions`, no hechos observados.
- El `break_even` debe convertirse con `metric_from_break_even(scenario, calculation)` para conservar `CalculationContext`, entradas, unidades, supuestos y operación original. No reescribas la fórmula ni generes un `CalculatedMetric` sin contexto.
- El constructor de claims actual admite el punto de equilibrio. No trates ingresos, costes variables o resultado mensual como si fueran punto de equilibrio.
- Conecta las métricas reales de análisis con `build_report(...)`; no las pierdas en un redactor aislado.
- La revisión debe bloquear por incidencias de severidad `error`, no por la mera existencia de cualquier warning.
- Si no hay evidencias web utilizables, la revisión/aprobación debe quedar bloqueada. La presencia de indicadores municipales no demuestra por sí misma investigación suficiente de competidores.

## Aprobación, persistencia y exportación

- Nunca precargues una aprobación ficticia o un fingerprint artesanal.
- Solo crea `ApprovalRecord(approved=True)` tras una acción afirmativa inequívoca de una persona que ha visto el informe y sus incidencias.
- Vincula la aprobación a `run_id`, `draft_id`, versión, `calculate_draft_fingerprint(draft)`, acciones exactas y `datetime.now(timezone.utc)`.
- Antes de aprobar, ejecuta `validate_review_matches_draft`, `validate_review_matches_research` y `validate_review_matches_analysis` con los objetos recuperados del checkpoint actual.
- Antes de exportar, vuelve a comprobar huella, identidad, versión, autorización de cada acción y zona horaria.
- Una modificación de investigación, análisis o borrador invalida la revisión y la aprobación anteriores.
- Usa exclusivamente `export_approved_report` y los exportadores existentes. No escribas directamente en `reports/generated` desde los botones de Streamlit.
- Conserva `DeliveryResult` para reintentos idempotentes; comunica claramente entregas parciales y errores por acción.
- Un rechazo humano debe quedar registrado y nunca crear exportaciones.

## Experiencia de producto

Mantén navegación simple, con estas áreas: Visión general, Nuevo estudio, Indicadores oficiales, Investigación/competidores, Análisis, Informe/revisión, Aprobación/entrega e Historial.

La persona debe entender rápidamente: qué ha ocurrido, qué fuente lo respalda, qué significa cada unidad/periodo, qué está pendiente, por qué una acción está bloqueada y qué se ha exportado.

Diseño:
- Estética premium contemporánea, verde bosque/menta con acentos cálidos discretos, tipografía legible, jerarquía fuerte y espacio en blanco.
- Responsive, con tablas limpias, unidades claras, estados y mensajes en lenguaje no técnico.
- Gráficos únicamente cuando los datos sean comparables (misma unidad, ámbito y periodo compatibles). No compares escalas incompatibles ni combines nulos.
- KPIs calculados desde datos que haya devuelto la ejecución actual. Nada de números de demo.
- Filtros, búsqueda de evidencias y detalles desplegables sin sobrecargar la pantalla.

## Animación y demo

Conserva/mejora personajes vectoriales originales que representen a una familia y el concepto de bienestar. La ilustración es decorativa: no debe distraer, cubrir controles ni implicar que una actividad/servicio existe en la zona. Usa SVG/CSS/HTML local, sin dependencias CDN; respeta `prefers-reduced-motion` y aporta alternativa textual o marca la ilustración como decorativa. Crea una pequeña animación web de bienvenida y un guion de demo. Si generas un MP4/GIF, grábalo desde una ejecución real de la app; nunca simules capturas de pantalla ni inventes resultados.

## Accesibilidad

- Idioma del documento español, labels asociados, foco visible, navegación por teclado y orden lógico de tabulación.
- Contraste WCAG AA como objetivo; no uses solo color para comunicar error/éxito.
- Encabezados jerárquicos sin saltos, tablas con cabeceras, controles con instrucciones claras y mensajes accesibles.
- Sin `tabindex` positivo ni ARIA redundante.
- Respeta movimiento reducido. Ejecuta revisión automatizada y pruebas manuales de teclado/lector de pantalla.

## Tests de aceptación que debes añadir

- Conversión MCP: valor real conservado, periodo/fuente/limitaciones conservados, y `null` nunca se transforma.
- Persistencia y recuperación de `run_id`, checkpoint, ApprovalRecord, decisión, delivery result y auditoría después de recrear la app.
- MCP no disponible / área no soportada / proveedor de búsqueda alternativo.
- El flujo conecta `analysis_node` → `build_report` → revisión con `CalculationContext` intacto.
- Supuestos incompletos no producen métricas.
- Un `break_even` sí incluye contexto verificable y una métrica ausente no se convierte en cero.
- Errores bloquean; warnings no bloquean por sí solos.
- La revisión obsoleta, huella alterada, otra versión u otra investigación impiden aprobar/exportar.
- No existe ApprovalRecord aprobado antes del clic humano.
- Un rechazo no crea archivos.
- Acción no autorizada, aprobación ausente o timezone naïve impiden escribir.
- Entregas parciales y reintentos no duplican ni sobrescriben archivos distintos.
- La UI no inicia búsquedas/MCP al cargar ni al navegar.

## Entrega y Definition of Done

1. `python -m compileall -q src tests` pasa.
2. Suite completa `python -m pytest -q` pasa o se enumeran fallos previos/externos con evidencia.
3. Arranca `python -m streamlit run src/ui/app.py --server.port 8501`.
4. Se recorre un caso real con `.env`, MCP y proveedor web disponibles. No llames «prueba real» a un mock o a una pantalla estática.
5. Se valida recuperación tras reiniciar Streamlit y persistencia de la aprobación.
6. Se inspeccionan visualmente desktop y móvil; accesibilidad automática y manual.
7. Se ejecuta `git diff --check`, revisión de secretos y lectura completa del diff.
8. Se crea una rama/commit/PR solo si los permisos están disponibles. No hagas reset duro, force push ni descartes cambios locales.

Al cerrar, entrega un resumen conciso de arquitectura, archivos cambiados, comandos y resultados de validación reales, limitaciones pendientes y referencias commit/PR. No afirmes «Enterprise completado» sin cumplir los criterios anteriores.
