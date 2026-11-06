import sys
sys.path.insert(0, r'C:\Users\JUAN\Desktop\Proyectos\FitFamily_PR40_PR41_Integration')

p = r'C:\Users\JUAN\Desktop\Proyectos\FitFamily_PR40_PR41_Integration\src\agents\strategic_writer.py'
with open(p, 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Buscar las líneas a reemplazar
for i, line in enumerate(lines):
    if '        draft = drafts[0]' in line:
        print(f"Línea {i+1}: {repr(line)}")
    if '        draft.claims = claims' in line:
        print(f"Línea {i+1}: {repr(line)}")
    if '    _marcar_contradicciones(draft, claims)' in line:
        print(f"Línea {i+1}: {repr(line)}")
