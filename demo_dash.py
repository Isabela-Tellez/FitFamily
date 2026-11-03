"""Dash demo profesional — datos reales (MCP + Tavily + PR #39).
No modifica código compartido; solo presenta análisis existente.
Requires: pip install dash plotly (ya disponible en entorno)
"""
from dash import Dash, dcc, html
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd

# Datos reales del proyecto
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

df_scenarios = pd.DataFrame({
    "Escenario": ["Básico", "Intermedio", "Optimista"],
    "Clientes necesarios": [150, 200, 250],
    "Cuota (EUR/mes)": [35, 40, 55],
    "Ingresos mensuales (EUR)": [5250, 8000, 13750],
})

app = Dash(__name__)

# ----- Gráficos con estética profesional y sin barras de herramientas (elimina errores WAVE) -----
fig_indicators = px.bar(
    x=list(indicators.values()), y=list(indicators.keys()),
    orientation="h", title="Indicadores verificados — El Cañaveral (MCP, oct 2026)",
    color=list(indicators.values()), color_continuous_scale="Teal",
    labels={"x": "Valor", "y": "Indicador"}, text=[str(v) for v in indicators.values()],
)
fig_indicators.update_traces(textposition="outside", textfont=dict(size=11, color="#172B2A"))
fig_indicators.update_layout(
    height=480, template="plotly_white", font=dict(family="Arial, sans-serif", size=12),
    paper_bgcolor="#F8F9FA", plot_bgcolor="#FFFFFF",
    title_font=dict(size=18, color="#172B2A"),
    coloraxis_showscale=True,
    margin=dict(l=120, r=20, t=60, b=40),
    config={"displayModeBar": False},
)

fig_scenarios = px.bar(
    df_scenarios, x="Escenario", y="Ingresos mensuales (EUR)",
    color="Cuota (EUR/mes)", title="Escenarios económicos — Punto de equilibrio",
    labels={"color": "Cuota mensual (EUR)"}, text="Ingresos mensuales (EUR)",
)
fig_scenarios.update_traces(textposition="outside", textfont=dict(size=11, color="#172B2A"))
fig_scenarios.update_layout(
    height=380, template="plotly_white", font=dict(family="Arial, sans-serif", size=12),
    paper_bgcolor="#F8F9FA", plot_bgcolor="#FFFFFF",
    title_font=dict(size=18, color="#172B2A"),
    coloraxis_showscale=False,
    margin=dict(l=40, r=20, t=60, b=40),
    config={"displayModeBar": False},
)

fig_pipeline = go.Figure(data=[go.Table(
    header=dict(values=["Etapa", "Estado", "Datos / Evidencias"],
                fill_color="#172B2A", align="left", font=dict(color="#D7A96B", size=13)),
    cells=dict(values=[
        ["Investigación (Tavily + MCP)", "Análisis (escenarios)", "Redacción (LLM/Det)", "Revisión (María)", "Aprobación (Isabella)", "Exportación"],
        ["Completado", "Completado", "Completado", "Completado", "Pendiente (UI)", "Demo completado"],
        ["19 evidencias", "11 indicadores", "1 borrador", "0 issues", "ApprovalRecord sim.", "MD / PDF / CSV"],
    ], fill_color="#FFFFFF", align="left", font=dict(color="#172B2A", size=12),
    height=28),
)])
fig_pipeline.update_layout(
    title="Estado actual del pipeline — docs/update (PR #39 integrado)",
    height=320, template="plotly_white",
    paper_bgcolor="#F8F9FA", plot_bgcolor="#FFFFFF",
    title_font=dict(size=16, color="#172B2A"),
    margin=dict(l=40, r=20, t=60, b=40),
    config={"displayModeBar": False},
)

# Diseño profesional: cabecera con identidad, cuerpo en 3 columnas, pie técnico
app.layout = html.Div([
    # Cabecera elegante
    html.Div([
        html.H1("FitFamily", style={"fontSize": "36px", "fontWeight": "bold", "margin": "0", "color": "#172B2A"}),
        html.H2("Investigación de mercado — Análisis visual integrado", style={"fontSize": "18px", "fontWeight": "300", "margin": "4px 0 0 0", "color": "#D7A96B"}),
        html.P("Datos reales: Tavily (búsqueda web) + MCP local (11 indicadores verificados de El Cañaveral, oct 2026) + análisis de escenarios. PR #39 integrado.",
               style={"fontSize": "13px", "color": "#555555", "margin": "8px 0 0 0"}),
        html.P("Persona 1 — Juan | Rama docs/update | 03 nov 2026", style={"fontSize": "11px", "color": "#777777", "margin": "4px 0 0 0"}),
    ], style={"padding": "30px 30px 20px 30px", "backgroundColor": "#172B2A", "borderBottom": "4px solid #D7A96B"}),

    # Cuerpo: 3 columnas (indicadores | escenarios | pipeline)
    html.Div([
        html.Div([
            html.H3("Indicadores municipales verificados", style={"fontSize":"14px","fontWeight":"bold","color":"#172B2A","marginBottom":"10px"}),
            dcc.Graph(figure=fig_indicators, config={"displayModeBar": False}),
        ], style={"padding": "15px", "backgroundColor": "#FFFFFF", "borderRadius": "8px", "boxShadow": "0 2px 6px rgba(0,0,0,0.08)"}),
        html.Div([
            html.H3("Escenarios económicos", style={"fontSize":"14px","fontWeight":"bold","color":"#172B2A","marginBottom":"10px"}),
            dcc.Graph(figure=fig_scenarios, config={"displayModeBar": False}),
        ], style={"padding": "15px", "backgroundColor": "#FFFFFF", "borderRadius": "8px", "boxShadow": "0 2px 6px rgba(0,0,0,0.08)"}),
        html.Div([
            html.H3("Estado del flujo (pipeline)", style={"fontSize":"14px","fontWeight":"bold","color":"#172B2A","marginBottom":"10px"}),
            dcc.Graph(figure=fig_pipeline, config={"displayModeBar": False}),
        ], style={"padding": "15px", "backgroundColor": "#FFFFFF", "borderRadius": "8px", "boxShadow": "0 2px 6px rgba(0,0,0,0.08)"}),
    ], style={"display": "flex", "gap": "15px", "padding": "20px", "backgroundColor": "#F0F2F5"}),

    # Pie técnico / legal
    html.Div([
        html.H3("Nota técnica y legal", style={"fontSize":"16px","fontWeight":"bold","color":"#172B2A","margin":"20px 30px 10px 30px"}),
        html.Div([
            html.P("Proyecto abierto — prototipo de investigación. No es un producto de inversión terminado. Requiere aprobación humana (Persona 5) antes de publicar resultados.",
                   style={"fontSize":"12px","lineHeight":"1.6","color":"#555"}),
            html.P("Observación asistida por IA (PR #39): el gráfico de precios se analiza mediante modelo de visión de Groq (VISION_LLM_MODEL=groq/qwen/qwen3.8-27b). La respuesta se registra como observación con limitaciones, no como hecho verificado.",
                   style={"fontSize":"12px","lineHeight":"1.6","color":"#555"}),
            html.P("Datos municipales: 11 indicadores verificados del Padrón Municipal y Censo de Locales (Ayuntamiento de Madrid, datos.madrid.es, oct 2026). 2 no disponibles: familias con hijos; gimnasios con ludoteca (no hay epígrafe combinado).",
                   style={"fontSize":"12px","lineHeight":"1.6","color":"#555"}),
            html.P("Búsqueda web: Tavily (clave configurada localmente, no expuesta). Fallback: DuckDuckGo (ddgs). Cobertura de análisis: ~82% (509 tests pasados). Flujo automático (workflows.py): implementado; ejecución completa con datos reales: verificada en demo local.",
                   style={"fontSize":"12px","lineHeight":"1.6","color":"#555"}),
        ], style={"padding": "0 30px 30px 30px"}),
    ], style={"backgroundColor": "#FFFFFF", "borderTop": "1px solid #EAEAEA"}),
], attrs={"lang": "es"})

if __name__ == "__main__":
    app.run(debug=True, port=8050)
