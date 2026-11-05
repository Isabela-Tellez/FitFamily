# Revisión de cuatro indicadores económicos

Base inspeccionada: dev 763a5f0 (5 de noviembre de 2026).

El adaptador transporta el valor junto a su escenario, cálculo original,
unidad, evidencias, supuestos y limitaciones. El informe utiliza ese valor.
El revisor comprueba que lo transportado corresponde al cálculo original.

Ahora se admiten ingresos mensuales, costes variables mensuales, resultado
mensual y punto de equilibrio. Para comprobarlos se llaman las funciones de
Laura; no se escribe otra versión de las fórmulas. El resultado mensual se
contrasta también con los ingresos y costes derivados del escenario.
Los UUID generados durante la comprobación no reemplazan la referencia original.

Los resultados negativos son válidos para el resultado mensual. Un resultado
no disponible sigue siendo None; no se convierte en cero. Se conserva la
compatibilidad anterior de métricas sin contexto, pero estas no acreditan
procedencia completa. Los identificadores del adaptador requieren contexto.

## Coordinación con Isabela

El instalador modifica el revisor y añade pruebas y esta documentación.
El parche docs/workflow-economic-adapter.patch NO se aplica automáticamente.
Isabela debe sustituir la construcción manual de las métricas en analysis_node
por metric_from_scenario_calculation para las cuatro, sin cambiar los cálculos.
Desde la raíz del repositorio, después de coordinar quién realiza el cambio:

```bash
git apply --check docs/workflow-economic-adapter.patch
git apply docs/workflow-economic-adapter.patch
```

Si el archivo ha cambiado, revisar el parche; no forzar su aplicación.
La modificación del revisor por sí sola no resuelve el error del nodo.

## Verificación

```bash
python -m unittest tests.test_economic_review_contract -v
python -m pytest tests/test_calculation_contract_integration.py tests/test_numeric_validation.py tests/test_economic_review_contract.py -q
```

La primera comprobación es local, determinista y no necesita pytest ni LLM.
Ocho métodos cubren los cuatro indicadores, 32 alteraciones, resultados ausentes,
pérdidas, falta de contexto/evidencia y revisiones obsoletas. No es una prueba del
workflow completo. La regresión con pytest debe ejecutarse antes de integrar.
Después de aplicar también el cambio del nodo, ejecutar las pruebas del workflow.
