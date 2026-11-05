import sys
sys.path.insert(0, r'C:\Users\JUAN\Desktop\Proyectos\FitFamily_PR40_PR41_Integration')

p = r'C:\Users\JUAN\Desktop\Proyectos\FitFamily_PR40_PR41_Integration\src\agents\strategic_writer.py'
with open(p, 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Reemplazar desde la línea 611 (if len(drafts) == 1:) hasta la línea 637 (_marcar_contradicciones)
nuevas_lineas = [
    '    if len(drafts) == 1:\n',
    '        # Un único lote: usamos directamente su borrador.\n',
    '        draft = drafts[0]\n',
    '    else:\n',
    '        # Varios lotes: consolidamos secciones, afirmaciones y resumen.\n',
    '        sections = _consolidate_sections(drafts)\n',
    '        claims = _deduplicate_claims(drafts)\n',
    '        sources = list(dict.fromkeys(s for part in drafts for s in part.sources))\n',
    '        limitations = list(dict.fromkeys(s for part in drafts for s in part.limitations))\n',
    '        limitations.append(\n',
    '            f"Informe consolidado a partir de {len(batches)} lotes de investigación: "\n',
    '            "se unificaron las afirmaciones repetidas y se conserva la trazabilidad "\n',
    '            "de cada evidencia citada."\n',
    '        )\n',
    '        sections[0] = "Resumen ejecutivo\\n" + _build_global_summary(\n',
    '            drafts, research_result, brief\n',
    '        )\n',
    '        draft = drafts[0]\n',
    '        draft.sections = sections\n',
    '        draft.claims = claims\n',
    '        draft.sources = sources\n',
    '        draft.limitations = limitations\n',
    '    # Recolectar las claims originales de todos los drafts antes de\n',
    '    # sobrescribir draft.claims con las consolidadas.\n',
    '    todas_las_claims: list[ReportClaim] = []\n',
    '    for d in drafts:\n',
    '        todas_las_claims.extend(d.claims)\n',
    '    # Rellenar apartados vacíos con datos disponibles (aplica a single y multi-batch).\n',
    '    _fill_missing_sections(draft, research_result, brief)\n',
    '    # Detectar contradicciones entre afirmaciones (ej. Winfit con/sin tarifa).\n',
    '    _marcar_contradicciones(draft, todas_las_claims)\n',
]

# Reemplazar líneas 611-637 (1-indexed) = índices 610-636 (0-indexed)
for i, nueva_linea in enumerate(nuevas_lineas):
    lines[610 + i] = nueva_linea

with open(p, 'w', encoding='utf-8') as f:
    f.writelines(lines)

print("Reemplazo realizado correctamente")
