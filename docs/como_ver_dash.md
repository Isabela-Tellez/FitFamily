VER EL DASH
------------
Abre navegador: http://localhost:8050 (corre local en tu PC, no es público)
Si el servidor se detuvo: python demo_dash.py (vuelve a lanzar)

LO QUE FALTA PARA EL MVP COMPLETO (no inventado; documentado)
---------------------------------------------------------------
- Streamlit completo (src/ui/app.py): NO EXISTE; solo report_preview.py
- Controlador de aprobación humana (ApprovalRecord real): SIMULADO en tests/demo
- Flujo end-to-end con datos reales de red (workflows.py): COMPILA; ejecución completa NO VERIFICADA en CI
- Renta INE (sección censal): PENDIENTE (docs/pendiente-renta-ine.md)
- Recomendación de inversión / modelo financiero completo: FUERA DE ALCANCE
- UI/Orquestación (Persona 5 — Isabella): DISEÑO en docs/streamlit-approval.md; código vacío en src/ui/ y src/runtime/

LO QUE YA ESTÁ (tú, Juan, Persona 1 — completo hoy)
----------------------------------------------------
- Investigación, MCP, búsqueda web, análisis de escenarios, redacción, revisión, exportación
- Datos reales: demo_mvp_real.py (Tavily + 11 indicadores MCP)
- PR #39 integrado (multimodal vision, tests 9/9)
- Documentación actualizada y honesta (README, docs/research-module.md, docs/presentacion.md)
- .gitignore limpio (.coverage, reports/ ignorados)
- Rama docs/update sincronizada con origin
