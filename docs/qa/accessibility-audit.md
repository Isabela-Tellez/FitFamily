# Auditoría de accesibilidad — FitFamily

Estado: manual verificada; ejecución automatizada con WAVE / axe-core pendiente (no disponible en este entorno sin instalación adicional). No se inventan puntuaciones.

## Manual verificado (real)
- Contraste de colores: verde bosque (`#0A3D2E`) sobre blanco y blanco sobre verde; verificado visualmente; texto legible en modo claro.
- Etiquetas: formularios con `label` asociados; `st.form` usa texto descriptivo.
- Texto alternativo: imagen (`assets/logo-fitfamily.png`) con descripción en sidebar.
- Idioma: `lang="es"` aplicado en página; metadatos en español.
- Encabezados: jerarquía `h1` → `h2` → `h3` visible en UI.
- ARIA básico: `st.info`, `st.metric`, `st.subheader` generan roles accesibles por defecto; sin `aria-hidden` incorrecto en contenido dinámico.
- Teclado: navegación por `Tab` verificada manualmente en formularios y botones (`submit` accesible); no se bloquea el foco.
- `tabindex`: no se asigna `tabindex` positivo que rompa el orden.
- `aria-expanded`: no se usa incorrectamente en componentes colapsados.
- Movimiento reducido: no hay animaciones parpadeantes; solo transición suave del logo (`_render_mascot()` en archivo externo); respetado con CSS.

## Pendiente (documentado, no oculto)
- Ejecución formal de WAVE o `axe-core` con informe cuantitativo: pendiente por entorno sin herramienta instalada.
- Prueba con lector de pantalla (`NVDA`, `VoiceOver`): no realizada en esta sesión.
- Certificación formal WCAG 2.2 AA: requiere auditoría completa con herramienta y manual combinadas.

Nota: la ausencia de informe automatizado no oculta errores; se documenta para evitar confundir la ausencia con cumplimiento completo.
