import sys
sys.path.insert(0, r'C:\Users\JUAN\Desktop\Proyectos\FitFamily_PR40_PR41_Integration')

p = r'C:\Users\JUAN\Desktop\Proyectos\FitFamily_PR40_PR41_Integration\src\agents\strategic_writer.py'
with open(p, 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Check current state around line 628-640
for i in range(627, 641):
    print(f"{i+1}: {repr(lines[i-1])}")

print("\n--- Insertando todas_las_claims después de línea 632 ---")

# Insert after line 632 (draft.limitations = limitations), which is index 631
# Insert antes de la línea 634 (el comentario de "Rellenar apartados vacíos")
insert_pos = 633  # 0-indexed, insert before line 634

lines.insert(insert_pos, '    todas_las_claims: list[ReportClaim] = []\n')
lines.insert(insert_pos + 1, '    for d in drafts:\n')
lines.insert(insert_pos + 2, '        todas_las_claims.extend(d.claims)\n')

with open(p, 'w', encoding='utf-8') as f:
    f.writelines(lines)

print("Inserción realizada correctamente")

# Verify
with open(p, 'r', encoding='utf-8') as f:
    lines = f.readlines()
for i in range(627, 642):
    print(f"{i+1}: {repr(lines[i-1])}")
