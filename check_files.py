import os
for f in ["src/ui/controller.py", "src/graph/state.py"]:
    print(f, "=>", "ENCONTRADO" if os.path.exists(f) else "FALTANTE")
