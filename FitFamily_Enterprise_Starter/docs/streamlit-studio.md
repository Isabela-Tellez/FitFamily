# FitFamily Studio · guía de la nueva interfaz

## Arranque

Desde la raíz del repositorio y con el entorno virtual activo:

```bash
python -m pip install -r requirements.txt
python -m streamlit run src/ui/app.py --server.port 8501
```

La app lee `.env` desde la raíz del repositorio. Tavily se utiliza cuando
`TAVILY_API_KEY` está configurada; si no, el módulo de búsqueda aplica el
proveedor de respaldo que ya tenga disponible. La interfaz no muestra claves.

## Flujo de usuario

1. **Nuevo estudio**: completar encargo y preguntas. Los parámetros financieros
   son opcionales y, cuando se introducen, se marcan como supuestos de escenario.
2. **Ejecutar estudio real**: llama a `build_workflow()` y guarda checkpoints
   LangGraph en `data/fitfamily_ui_checkpoints.sqlite`.
3. **Resultados**: consulta competidores, evidencias, métricas y revisión del
   mismo borrador que se ha generado. Los campos ausentes se mantienen nulos.
4. **Indicadores oficiales**: consulta el servidor MCP local por stdio y muestra
   sus valores, periodos, estados, fuentes y limitaciones.
5. **Aprobación y entrega**: la persona revisa el informe y registra una
   decisión humana. La huella procede de `calculate_draft_fingerprint(draft)`.
   La exportación solo se ofrece para acciones autorizadas por `ApprovalRecord`.

## Salvaguardas

- No hay llamadas de investigación automáticas al abrir o recargar la app.
- No hay cifras municipales ni KPIs de demo embebidos en el código de UI.
- No se crean identificadores, versiones o huellas de borrador ficticias.
- Un resultado de investigación sin evidencias bloquea aprobación.
- Las advertencias se muestran como advertencias; solo los errores bloquean.
- El analista recibe exclusivamente parámetros financieros introducidos por
  la persona usuaria. Sin ellos, devuelve una limitación en lugar de inventar
  cifras.
- El flujo utiliza redacción determinista por defecto. La opción LLM es
  explícita y requiere `GROQ_API_KEY`.
- La exportación vuelve a comprobar la aprobación y la identidad del contenido.
- La ilustración animada es decorativa, original y no representa datos reales.

## Validación

```bash
python -m compileall -q src/ui src/graph tests/test_ui_controller.py
python -m pytest tests/test_ui_controller.py tests/test_workflow.py tests/test_exporter.py tests/test_delivery.py -q
```

El test MCP/Tavily conectado a servicios reales requiere red y credenciales
locales; no forma parte de las pruebas offline.
