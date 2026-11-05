c = open("demo_dash.py").read()
old = '    config={"displayModeBar": False},\n)'
new = '    )'
c = c.replace(old, new)
open("demo_dash.py", "w").write(c)
print("fixed all")
