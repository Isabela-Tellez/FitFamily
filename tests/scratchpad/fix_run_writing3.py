import sys
sys.path.insert(0, r'C:\Users\JUAN\Desktop\Proyectos\FitFamily_PR40_PR41_Integration')

p = r'C:\Users\JUAN\Desktop\Proyectos\FitFamily_PR40_PR41_Integration\src\agents\strategic_writer.py'
with open(p, 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Las líneas a reemplazar son las 628-637 (1-indexed), que son índices 627-636 (0-indexed)
# Verificamos qué hay en esas líneas
for i in range(627, 640):
    print(f"{i+1}: {repr(lines[i])}")

print("\n--- Reemplazando ---")

# Reemplazar las líneas 628-637 (1-indexed)
nuevas_lineas = [
    '        # Recolectar las claims originales de todos los drafts antes de\n',
    '        # sobrescribir draft.claims con las consolidadas.\n',
    '        todas_las_claims: list[ReportClaim] = []\n',
    '        for d in drafts:\n',
    '            todas_las_claims.extend(d.claims)\n',
    '        draft = drafts[0]\n',
    '        draft.sections = sections\n',
    '        draft.claims = claims\n',
    '        draft.sources = sources\n',
    '        draft.limitations = limitations\n',
]

# Reemplazar líneas 628-637 (1-indexed) = índices 627-636
for i, nueva_linea in enumerate(nuevas_lineas):
    lines[627 + i] = nueva_linea

with open(p, 'w', encoding='utf-8') as f:
    f.writelines(lines)

print("Reemplazo realizado correctamente")
