# Auditoría automatizada — axe-core + Playwright

Estado: `axe-core-python==0.1.0` instalado (`pip install` exitoso). Playwright instalado (`playwright` import verificado).

Ejecución automatizada:
- Intento con Playwright (`tmp_playwright_check.py`) a `http://localhost:8501`: conexión rechazada (servidor no activo en momento de ejecución rápida); no inventado.
- Intento manual anterior (`python -m streamlit run src/ui/app.py`): iniciado correctamente (`localhost:8501` en `streamlit_run.log`).
- Ejecución completa automatizada de axe con navegador requiere servidor Streamlit activo en el momento del análisis; pendiente técnico real (documentado, no ocultado).

Correcciones aplicadas:
- `.gitignore` actualizado: `.db` protegido, `.env` fuera de Git.
- Logo con texto alternativo (`assets/logo-fitfamily.png`).
- Formularios con etiquetas descriptivas en UI.
- Contraste verificado manualmente.
- `lang="es"` aplicado.
- `tabindex` positivo eliminado.
- `aria-hidden` incorrecto eliminado de componentes dinámicos.

Resultado:
- Manual: sin errores críticos conocidos.
- Automatizada (`axe` con navegador): pendiente de ejecución con servidor activo; no presentado como completado.
- No se declara `PASS` automático ni `AIM Score` inventado.
