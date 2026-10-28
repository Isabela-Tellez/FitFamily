with open('README.md', 'r', encoding='utf-8', errors='ignore') as f:
    content = f.read()
old = '<p align="center">\n  <img src="assets/logo-fitfamily.png" alt="FitFamily: investigación de mercado para un gimnasio con ludoteca" width="360">\n</p>'
new = '<p align="center">\n  <img src="assets/banner-fitfamily.svg" alt="FitFamily — investigación de mercado y bienestar familiar" width="100%" style="max-width:800px; height:auto; border-radius:12px;">\n</p>'
if old in content:
    content = content.replace(old, new, 1)
    content = content.replace('logo=python&amp;logoColor=white">\n  <img alt="MCP', 'logo=python&amp;logoColor=white">\n  <img alt="SQLite" src="https://img.shields.io/badge/SQLite-persistence-003B5C?logo=sqlite&amp;logoColor=white">\n  <img alt="MCP')
    with open('README.md', 'w', encoding='utf-8') as f:
        f.write(content)
    print('ACTUALIZADO: banner + SQLite badge')
else:
    print('YA ACTUALIZADO o bloque no encontrado')
