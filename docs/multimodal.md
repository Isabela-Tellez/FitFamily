# Análisis multimodal de gráficos

## Configuración

El analizador visual reutiliza `GROQ_API_KEY`, pero requiere una variable independiente:

```env
VISION_LLM_MODEL=groq/NOMBRE_DEL_MODELO_CON_CAPACIDAD_VISUAL
```

No reutilices automáticamente `WRITER_LLM_MODEL`: el modelo de redacción configurado en el proyecto es de texto y no se debe asumir que acepta imágenes. Configura `VISION_LLM_MODEL` con el identificador exacto de un modelo visual disponible en tu cuenta de Groq.

## Uso

```python
from src.analysis.charts import build_price_chart
from src.multimodal.image_analyzer import (
    analyze_image,
    append_image_observations_to_report,
)

metadata = build_price_chart(competitors)
observation = analyze_image(
    metadata["path"],
    context=metadata,
    image_id="price-comparison-001",
    source_artifact_id=metadata["chart_type"],
)

# Tras construir el ReportDraft:
append_image_observations_to_report(draft, [observation])
```

La imagen se envía realmente al modelo visual. La respuesta se guarda como observación asistida por IA, no como hecho verificado. Las limitaciones se conservan en `draft.limitations` y la sección del informe mantiene el identificador del gráfico, el modelo y la ruta del archivo.

## Pruebas

Pruebas sin red:

```bash
python -m pytest tests/test_image_analyzer.py -v
```

Prueba opcional del proveedor real (requiere un PNG de prueba y credenciales):

```bash
FITFAMILY_VISION_TEST_IMAGE=artifacts/price_comparison.png python -m pytest tests/test_image_analyzer_integration.py -v
```

En Windows PowerShell, configura la variable con `$env:FITFAMILY_VISION_TEST_IMAGE="artifacts/price_comparison.png"` antes de ejecutar pytest.
