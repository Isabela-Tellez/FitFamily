"""Dash demo mejorado — visual interactivo con datos reales del proyecto.
No modifica código compartido; solo presenta análisis existente.
Requiere: pip install dash plotly (ya disponible en entorno)
"""
from dash import Dash, dcc, html
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import os
from pathlib import Path

# Datos del demo real (MCP + web) — no inventados
# 11 indicadores verificados de El Cañaveral
indicators = {
    "Población total": 27480,
    "Hogares": 8140,
    "Gimnasios registrados": 9,
    "Locales abiertos": 234,
    "Hogares con menores": 3071,
    "Menores < 20 años": 28.29,
    "Población 2025": 21492,
    "Tamaño hogar": 2.64,
    "Deporte/recreación": 4,
    "Ocio infantil": 3,
    "Piscinas comunitarias": 3,
}

# Comparación de cuotas con escenarios (Laura / análisis)
df_scenarios = pd.DataFrame({
    "Escenario": ["Básico", "Intermedio", "Optimista"],
    "Clientes necesarios (punto de equilibrio)": [150, 200, 250],
    "Cuota estimada (EUR/mes)": [35, 40, 55],
    "Ingresos mensuales (EUR)": [5250, 8000, 13750],
})

app = Dash(__name__)

# Gráfico 1: Indicadores municipales (barra horizontal, real)
fig1 = px.bar(
    x=list(indicators.values()),
    y=list(indicators.keys()),
    orientation="h",
    title="El Cañaveral — Indicadores municipales verificados (MCP, oct 2026)",
    color=list(indicators.values()),
    color_continuous_scale="Teal",
    labels={"x": "Valor", "y": "Indicador"},
    text=[f"{v}" for v in indicators.values()],
)
fig1.update_traces(textposition="outside")
fig1.update_layout(height=520, template="plotly_white")

# Gráfico 2: Escenarios económicos (del análisis)
fig2 = px.bar(
    df_scenarios,
    x="Escenario",
    y="Ingresos mensuales (EUR)",
    color="Cuota estimada (EUR/mes)",
    title="Escenarios económicos — Punto de equilibrio (Fuente: análisis)",
    labels={"color": "Cuota mensual (EUR)"},
    text="Ingresos mensuales (EUR)",
)
fig2.update_traces(textposition="outside")
fig2.update_layout(height=420, template="plotly_white")

# Gráfico 3: Composición del informe (pipeline real)
df_pipeline = pd.DataFrame({
    "Etapa": ["Investigación (web+MCP)", "Análisis (escenarios)", "Redacción (LLM/Det)", "Revisión (María)", "Aprobación (Isabella)", "Exportación"],
    "Estado": ["Completado", "Completado", "Completado", "Completado", "Pendiente (UI)", "Completado (demo)"],
    "Evidencias / Datos": ["19 evidencias", "11 indicadores", "1 borrador", "0 issues", "ApprovalRecord sim.", "MD/PDF/CSV"],
})
fig3 = go.Figure(data=[go.Table(
    header=dict(values=["Etapa", "Estado", "Datos"], fill_color="#172B2A", align="left", font=dict(color="#D7A96B")),
    cells=dict(values=[
        df_pipeline["Etapa"],
        df_pipeline["Estado"],
        df_pipeline["Evidencias / Datos"]
    ], fill_color="#2A2A2A", align="left", font=dict(color="white")),
)])
fig3.update_layout(title="Pipeline FitFamily — Estado hoy (docs/update)", height=250)

app.layout = html.Div([
    html.Div([html.H1("FitFamily — Panel de análisis integrado"),
              html.P("Datos del demo real: Tavily + MCP (11 indicadores verificados) + análisis de escenarios. PR #39 integrado.")],
             style={"padding": "20px", "backgroundColor": "#172B2A", "color": "#D7A96B"}),
    html.Div([
        dcc.Graph(figure=fig1),
    ], style={"padding": "10px"}),
    html.Div([
        dcc.Graph(figure=fig2),
    ], style={"padding": "10px"}),
    html.Div([
        dcc.Graph(figure=fig3),
    ], style={"padding": "10px"}),
    html.Div([
        html.P("Nota técnica: Este panel es un demo de presentación. El flujo completo requiere aprobación humana (Persona 5 — Isabella) y conexión al workflow LangGraph para ejecución end-to-end sin red."),
        html.P("Proyecto abierto — no producto de inversión terminado. Requiere revisión humana antes de publicar resultados."),
    ], style={"padding": "10px", "fontSize": "12px", "color": "#666"}),
])

if __name__ == "__main__":
    app.run(debug=True, port=8050)
