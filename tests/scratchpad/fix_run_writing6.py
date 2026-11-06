import sys
sys.path.insert(0, r'C:\Users\JUAN\Desktop\Proyectos\FitFamily_PR40_PR41_Integration')

p = r'C:\Users\JUAN\Desktop\Proyectos\FitFamily_PR40_PR41_Integration\src\agents\strategic_writer.py'
with open(p, 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Find line 637 (0-indexed: 636) which has _marcar_contradicciones(draft, todas_las_claims)
# We need to insert todas_las_claims definition before line 637
# Find the exact line numbers
for i, line in enumerate(lines):
    if '_marcar_contradicciones(draft, todas_las_claims)' in line:
        print(f"Found _marcar_contradicciones call at line {i+1}: {repr(line)}")
    if 'todas_las_claims' in line:
        print(f"Found todas_las_claims at line {i+1}: {repr(line)}")

print("\n--- Lines 632-641 ---")
for i in range(632, 641):
    print(f"{i+1}: {repr(lines[i-1])}")
