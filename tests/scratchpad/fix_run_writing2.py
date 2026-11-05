import sys
sys.path.insert(0, r'C:\Users\JUAN\Desktop\Proyectos\FitFamily_PR40_PR41_Integration')

p = r'C:\Users\JUAN\Desktop\Proyectos\FitFamily_PR40_PR41_Integration\src\agents\strategic_writer.py'
with open(p, 'r', encoding='utf-8') as f:
    content = f.read()

old = '''        draft = drafts[0]
        draft.sections = sections
        draft.claims = claims
        draft.sources = sources
        draft.limitations = limitations
    # Rellenar apartados vacíos con datos disponibles (aplica a single y multi-batch).
    _fill_missing_sections(draft, research_result, brief)
    # Detectar contradicciones entre afirmaciones (ej. Winfit con/sin tarifa).
    _marcar_contradicciones(draft, claims)'''

new = '''        # Recolectar las claims originales de todos los drafts antes de
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
    _marcar_contradicciones(draft, todas_las_claims)'''

if old in content:
    content = content.replace(old, new, 1)
    with open(p, 'w', encoding='utf-8') as f:
        f.write(content)
    print("Reemplazo realizado correctamente")
else:
    print("No se encontró el oldString")
    # Mostrar qué hay alrededor de la línea 628
    lineas = content.splitlines()
    for i in range(626, 640):
        print(f"{i+1}: {repr(lineas[i])}")
