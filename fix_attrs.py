with open("demo_dash.py") as f:
    c = f.read()
c = c.replace('], fluid=True, attrs={"lang": "es"})', '], fluid=True)')
open("demo_dash.py", "w").write(c)
print("Fixed attrs")
