# FitFamily Studio — paquete de mejora UI

Este paquete es un **overlay de integración** para la rama local `feat/completado-limpio`. No contiene datos de investigación, no reemplaza `.env`, no copia checkpoints y no contiene aprobaciones ficticias.

## Incluye

- `src/ui/app.py`: Streamlit multipágina, flujo guiado, revisión y exportación con los módulos existentes. Incluye una ilustración vectorial animada original en SVG/CSS y movimiento reducido.
- `src/ui/controller.py`: reconstrucción de modelos y creación de `ApprovalRecord` ligado a la huella real y revisión actual.
- `src/graph/state.py` y `src/graph/workflow.py`: workflow con redacción determinista por defecto, integración del punto de equilibrio y bloqueo si no hay evidencias.
- `tests/`: pruebas de regresión para controlador y workflow.
- `docs/streamlit-studio.md`: guía de funcionamiento.
- `PROMPT_AGENTE_ENTERPRISE.md`: prompt ampliado para que tu agente cierre los pendientes y valide la integración local.

## Aplicación sobre tu repositorio

Haz una copia de seguridad y revisa `git status` antes de copiar. Mantén tu `.env` local y no lo incluyas en Git.

En PowerShell, desde la raíz de FitFamily (después de extraer el ZIP):

```powershell
Copy-Item .\fitfamily_upgrade\src\ui\app.py .\src\ui\app.py -Force
Copy-Item .\fitfamily_upgrade\src\ui\controller.py .\src\ui\controller.py -Force
Copy-Item .\fitfamily_upgrade\src\graph\state.py .\src\graph\state.py -Force
Copy-Item .\fitfamily_upgrade\src\graph\workflow.py .\src\graph\workflow.py -Force
Copy-Item .\fitfamily_upgrade\tests\test_ui_controller.py .\tests\test_ui_controller.py -Force
Copy-Item .\fitfamily_upgrade\tests\test_ui_workflow_integration.py .\tests\test_ui_workflow_integration.py -Force
Add-Content .\requirements.txt "`nstreamlit>=1.40,<2.0"
```

En macOS/Linux, desde la raíz del repositorio y una vez extraído el ZIP:

```bash
cp fitfamily_upgrade/src/ui/app.py src/ui/app.py
cp fitfamily_upgrade/src/ui/controller.py src/ui/controller.py
cp fitfamily_upgrade/src/graph/state.py src/graph/state.py
cp fitfamily_upgrade/src/graph/workflow.py src/graph/workflow.py
cp fitfamily_upgrade/tests/test_ui_controller.py tests/test_ui_controller.py
cp fitfamily_upgrade/tests/test_ui_workflow_integration.py tests/test_ui_workflow_integration.py
echo 'streamlit>=1.40,<2.0' >> requirements.txt
```

## Instalar, validar y arrancar

```bash
python -m pip install -r requirements.txt
python -m compileall -q src/ui src/graph tests/test_ui_controller.py tests/test_ui_workflow_integration.py
python -m pytest tests/test_ui_controller.py tests/test_ui_workflow_integration.py tests/test_workflow.py tests/test_exporter.py tests/test_delivery.py -q
python -m streamlit run src/ui/app.py --server.port 8501
```

Abre `http://localhost:8501`. Conserva `TAVILY_API_KEY` en `.env` si quieres usar Tavily. El modo LLM requiere `GROQ_API_KEY`; el modo determinista no requiere esa clave.

## Pendientes antes de producción Enterprise

Esta entrega es una **base visual/funcional avanzada**, no una certificación de producción. El agente debe resolver y probar expresamente:

1. Persistencia durable del `ApprovalRecord` y de la decisión humana. La versión inicial usa `st.session_state` para mantener la aprobación durante la sesión; debe sobrevivir a un reinicio/recarga mediante un registro durable vinculado a `run_id`.
2. Integración de la respuesta MCP en el contenido/evidencias del informe. La versión inicial consulta MCP en su página propia, pero no convierte por sí misma esos indicadores en evidencias del `ResearchResult`.
3. Historial recuperable de ejecuciones, revisión de accesibilidad manual y prueba real de extremo a extremo con las credenciales/servidor locales.
4. Confirmar tests completos y compatibilidad con las versiones del entorno de la máquina local.

Consulta `PROMPT_AGENTE_ENTERPRISE.md`: contiene los hallazgos, salvaguardas, cambios requeridos y la Definition of Done. No declares la integración completa hasta ejecutar esas comprobaciones en tu repositorio y entorno.
