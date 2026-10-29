# Demo del revisor de María — guion de cinco minutos

Base revisada: dev 4b52500, 29 de octubre de 2026. Usa los cálculos y el adaptador
de análisis, el constructor y Markdown de Gema, y la revisión y rutas de María.

## Ejecución en WSL, desde la raíz de FitFamily

```bash
source .venv/bin/activate
python demo_review.py
```

Para enseñar además la vista previa con las referencias numéricas:

```bash
python demo_review.py --markdown
```

No usa claves API, Internet, LLM ni datos reales. No modifica archivos ni concede
aprobación. No es una ejecución del grafo LangGraph de Isabella.

## Guion

**Primer minuto — propósito.**
«Mi módulo comprueba el informe antes de la aprobación humana. Detecta diferencias
entre cifras y cálculos, conserva su contexto y señala a qué etapa devolverlo.»

**Segundo minuto — escenario y resultado correcto.**
Mostrar costes fijos de 1.000 EUR/mes, cuota de 50 EUR/cliente/mes y coste variable
de 10 EUR/cliente/mes. Todos son supuestos ficticios. La función real de Laura
devuelve 25 clientes; Gema genera la frase y registra valor, unidad e indicador.
La demo no implementa otra fórmula.
Salida: CASO 1 → pending_review. «Esto no significa que el negocio sea viable
ni que el informe esté aprobado.»

**Tercer minuto — error de redacción.**
La demo altera una copia del informe: el texto y el campo declarado dicen 30.
El cálculo sigue siendo 25. Salida: metric_value_mismatch → revise_writing.
«El revisor detecta la diferencia y la devuelve a redacción; no corrige
automáticamente el contenido.»

**Cuarto minuto — revisión obsoleta.**
Añadir un supuesto narrativo al escenario, reconstruir su métrica y tratar de
reutilizar la revisión anterior. Salida: El análisis cambió después de la revisión.
«Aunque la cifra siga siendo 25, el contexto ha cambiado y hay que revisar de nuevo.»

**Quinto minuto — presentación y límites.**
La opción --markdown muestra el borrador y los campos numéricos añadidos por Gema.
«Comprobamos referencias y coherencia numérica; no demostramos que una fuente
sea verdadera ni interpretamos todas las cifras del texto libre.»

## Qué demuestra y qué no

- Se ejecutan las funciones reales de análisis, construcción, revisión y rutas.
- Se comprueba también que Markdown conserve indicador, valor y unidad.
- Se validan los once apartados comunes y la inclusión del punto de equilibrio
  en Escenarios económicos. Los apartados pendientes no son investigación realizada.
- El segundo caso altera texto y campo para aislar una discrepancia con el cálculo.
  No demuestra detección semántica de una frase incorrecta con campos correctos.
- El tercero modifica el original y reconstruye el adaptador; una copia antigua
  no detecta por sí sola cambios de un objeto externo.
- Los borradores original y alterado permanecen separados.
- No se invoca revisión humana, exportación PDF ni persistencia.
- La aceptación del workflow continúa en tests/workflow_shared_acceptance.py.

## Verificación mínima

Para este bloque basta ejecutar python demo_review.py. La propia demo comprueba
los tres resultados y termina con error si alguno no se cumple.
No requiere repetir la batería de 218 pruebas.
