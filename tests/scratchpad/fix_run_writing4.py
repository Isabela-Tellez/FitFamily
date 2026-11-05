import sys
sys.path.insert(0, r'C:\Users\JUAN\Desktop\Proyectos\FitFamily_PR40_PR41_Integration')

p = r'C:\Users\JUAN\Desktop\Proyectos\FitFamily_PR40_PR41_Integration\src\agents\strategic_writer.py'
with open(p, 'r', encoding='utf-8') as f:
    content = f.read()

old = '''    if len(drafts) == 1:
        # Un único lote: usamos directamente su borrador.
        draft = drafts[0]
    else:
        # Varios lotes: consolidamos secciones, afirmaciones y resumen.
        sections = _consolidate_sections(drafts)
        claims = _deduplicate_claims(drafts)
        sources = list(dict.fromkeys(s for part in drafts for s in part.sources))
        limitations = list(dict.fromkeys(s for part in drafts for s in part.limitations))
        limitations.append(
            f"Informe consolidado a partir de {len(batches)} lotes de investigación: "
            "se unificaron las afirmaciones repetidas y se conserva la trazabilidad "
            "de cada evidencia citada."
        )
        sections[0] = "Resumen ejecutivo\\n" + _build_global_summary(
            drafts, research_result, brief
        )
        # Recolectar las claims originales de todos los drafts antes de
        # sobrescribir draft.claims con las consolidadas.
        todas_las_claims: list[ReportClaim] = []
        for d in drafts:
            todas_las_claims.extend(d.claims)
        draft = drafts[0]
        draft.sections = sections
        draft.claims = claims
        draft.sources = sources
        draft.limitations = limitations
    # Rellenar apartados vacíos con datos disponibles (aplica a single y multi-batch).
    _fill_missing_sections(draft, research_result, brief)
    # Detectar contradicciones entre afirmaciones (ej. Winfit con/sin tarifa).
    _marcar_contradicciones(draft, claims)'''

new = '''    if len(drafts) == 1:
        # Un único lote: usamos directamente su borrador.
        draft = drafts[0]
    else:
        # Varios lotes: consolidamos secciones, afirmaciones y resumen.
        sections = _consolidate_sections(drafts)
        claims = _deduplicate_claims(drafts)
        sources = list(dict.fromkeys(s for part in drafts for s in part.sources))
        limitations = list(dict.fromkeys(s for part in drafts for s in part.limitations))
        limitations.append(
            f"Informe consolidado a partir de {len(batches)} lotes de investigación: "
            "se unificaron las afirmaciones repetidas y se conserva la trazabilidad "
            "de cada evidencia citada."
        )
        sections[0] = "Resumen ejecutivo\\n" + _build_global_summary(
            drafts, research_result, brief
        )
        draft = drafts[0]
        draft.sections = sections
        draft.claims = claims
        draft.sources = sources
        draft.limitations = limitations

    # Recolectar las claims originales de todos los drafts antes de
    # sobrescribir draft.claims con las consolidadas.
    todas_las_claims: list[ReportClaim] = []
    for d in drafts:
        todas_las_claims.extend(d.claims)

    # Rellenar apartados vacíos con datos disponibles (aplica a single y multi-batch).
    _fill_missing_sections(draft, research_result, brief)
    # Detectar contradicciones entre afirmaciones (ej. Winfit con/sin tarifa).
    _marcar_contradicciones(draft, todas_las_claims)'''

if old in content:
    content = content.replace(old, new, 1)
    with open(p, 'w', encoding='utf-8') as f:
        f.write(content)
    print("Reemplazo realizado correctamente")
else:
    print("No se encontró el oldString")
    # Mostrar qué hay en esas líneas para debug
    lineas = content.splitlines()
    for i in range(610, 641):
        print(f"{i+1}: {repr(lineas[i])}")
