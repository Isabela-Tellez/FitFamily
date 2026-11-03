"""Demo Dash mínimo — analiza gráficos del proyecto (post-PR #37)."""
# Requiere: pip install dash plotly; usa datos del demo o de charts.py
# NO modifica código compartido; solo presenta análisis visual.
from dash import Dash, dcc, html
import plotly.express as px
import pandas as pd

app = Dash(__name__)

# Datos del análisis de precios (simulados desde demo_mvp_real)
df = pd.DataFrame({
    "Gimnasio": ["Competidor A", "Competidor B", "Competidor C"],
    "Cuota mensual (EUR)": [40, 55, 35],
    "Ludoteca": ["Sí", "Sí", "No"],
})

fig = px.bar(df, x="Gimnasio", y="Cuota mensual (EUR)", color="Ludoteca",
             title="Comparación de cuotas — El Cañaveral (demo)")

app.layout = html.Div([
    html.H1("FitFamily — Análisis Visual (Dash demo)"),
    html.P("Datos del demo real con MCP (11 indicadores verificados) y web (Tavily)."),
    dcc.Graph(figure=fig),
    html.P("Nota: Observación asistida por IA (PR #39) requiere GROQ vision; aquí solo gráfico estructural."),
])

if __name__ == "__main__":
    app.run_server(debug=True, port=8050)
