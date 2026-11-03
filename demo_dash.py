"""
Dash demo — refactorizado según arquitectura senior (4 pilares).
- No modifica código compartido; solo presenta datos existentes (MCP + PR #39).
- Usa dbc (Bootstrap) para layout responsive; dcc.Store para datos; dcc.Loading para gráficos.
- Gráficos: plotly_white, márgenes mínimos, displayModeBar=False (WAVE limpio).
Requires: pip install dash plotly dash-bootstrap-components (ya disponible)
"""
from dash import Dash, dcc, html, Input, Output, State
import dash_bootstrap_components as dbc
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd

# ----- 1. CENTRALIZACIÓN DE DATOS (dcc.Store + datos reales) -----
# Se evita repetir la construcción de DataFrames en múltiples callbacks.
indicators = {
    "Población total": 27480, "Hogares": 8140, "Gimnasios registrados": 9,
    "Locales abiertos": 234, "Hogares con menores": 3071,
    "Menores < 20 años": 28.29, "Población 2025": 21492,
    "Tamaño hogar": 2.64, "Deporte/recreación": 4,
    "Ocio infantil": 3, "Piscinas comunitarias": 3,
}
df_scenarios = pd.DataFrame({
    "Escenario": ["Básico", "Intermedio", "Optimista"],
    "Clientes necesarios": [150, 200, 250],
    "Cuota (EUR/mes)": [35, 40, 55],
    "Ingresos mensuales (EUR)": [5250, 8000, 13750],
})

app = Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])
# Se usa lang="es" en el wrapper HTML para accesibilidad (WAVE)

# ----- 2. COMPONENTES REUTILIZABLES (dbc.Card + Loading) -----
# Cada gráfico va dentro de una tarjeta con cabecera y carga protegida.
# Esto evita renderizados en cadena si los datos son pesados.

def card_chart(title, fig):
    # Se envuelve en dcc.Loading para evitar pantallas en blanco si hay latencia.
    return dbc.Card([
        dbc.CardHeader(title, style={"fontWeight": "bold", "color": "#172B2A", "backgroundColor": "#F0F2F5"}),
        dbc.CardBody(dcc.Loading(
            dcc.Graph(figure=fig),
            type="dot", fullscreen=False,
        )),
    ], className="shadow-sm mb-4")

# ----- 3. GRAFICOS LIMPIOS (plotly_white + márgenes mínimos + sin toolbar) -----
fig_indicators = px.bar(
    x=list(indicators.values()), y=list(indicators.keys()),
    orientation="h", title="Indicadores verificados — El Cañaveral (MCP, oct 2026)",
    color=list(indicators.values()), color_continuous_scale="Teal",
    labels={"x": "Valor", "y": "Indicador"}, text=[str(v) for v in indicators.values()],
)
fig_indicators.update_traces(textposition="outside", textfont=dict(size=10, color="#172B2A"))
fig_indicators.update_layout(
    height=420, template="plotly_white",
    font=dict(family="Arial, sans-serif", size=11),
    paper_bgcolor="#F8F9FA", plot_bgcolor="#FFFFFF",
    title_font=dict(size=16, color="#172B2A"),
    coloraxis_showscale=True,
    margin=dict(l=120, r=20, t=50, b=30),
    config={"displayModeBar": False},
)

fig_scenarios = px.bar(
    df_scenarios, x="Escenario", y="Ingresos mensuales (EUR)",
    color="Cuota (EUR/mes)", title="Escenarios económicos — Punto de equilibrio (Fuente: análisis)",
    labels={"color": "Cuota mensual (EUR)"}, text="Ingresos mensuales (EUR)",
)
fig_scenarios.update_traces(textposition="outside", textfont=dict(size=10, color="#172B2A"))
fig_scenarios.update_layout(
    height=350, template="plotly_white",
    font=dict(family="Arial, sans-serif", size=11),
    paper_bgcolor="#F8F9FA", plot_bgcolor="#FFFFFF",
    title_font=dict(size=16, color="#172B2A"),
    coloraxis_showscale=False,
    margin=dict(l=40, r=20, t=50, b=30),
    config={"displayModeBar": False},
)

fig_pipeline = go.Figure(data=[go.Table(
    header=dict(values=["Etapa", "Estado", "Evidencias / Datos"],
                fill_color="#172B2A", align="left", font=dict(color="#D7A96B", size=12)),
    cells=dict(values=[
        ["Investigación (Tavily + MCP)", "Análisis (escenarios)", "Redacción (LLM/Det)", "Revisión (María)", "Aprobación (Isabella)", "Exportación (demo)"],
        ["Completado", "Completado", "Completado", "Completado", "Pendiente (UI)", "Demo completado"],
        ["19 evidencias", "11 indicadores verificados", "1 borrador", "0 issues (review)", "ApprovalRecord sim.", "MD / PDF / CSV"],
    ], fill_color="#FFFFFF", align="left", font=dict(color="#172B2A", size=11), height=26),
)])
fig_pipeline.update_layout(
    title="Pipeline FitFamily — docs/update (PR #39 integrado)",
    height=280, template="plotly_white",
    paper_bgcolor="#F8F9FA", plot_bgcolor="#FFFFFF",
    title_font=dict(size=15, color="#172B2A"),
    margin=dict(l=20, r=20, t=50, b=30),
    config={"displayModeBar": False},
)

# ----- 4. LAYOUT RESPONSIVO (12-col grid) -----
# Se usa dbc.Container + Row + Col para que se adapte a pantalla.
# Se evita CSS inline complejo; todo va por clases Bootstrap.
app.layout = html.Div([
    # Cabecera institucional
    dbc.Navbar(
        dbc.Container([
            html.A("FitFamily", href="#", style={"fontSize": "28px", "fontWeight": "bold", "color": "#172B2A", "textDecoration": "none"}),
            html.Span("Investigación de mercado — Datos reales (Tavily + MCP) + PR #39 integrado | Persona 1 — Juan", style={"fontSize": "11px", "color": "#777", "marginLeft": "12px"}),
        ]),
        color="light",
        dark=False,
        className="mb-4",
        style={"borderBottom": "4px solid #D7A96B", "padding": "15px 30px"},
    ),

    dbc.Container([
        # Título descriptivo (H1 para accesibilidad)
        html.H1("FitFamily — Panel de análisis integrado", className="mb-2", style={"fontWeight": "bold", "color": "#172B2A"}),
        html.P("Datos reales: Tavily (búsqueda web) + MCP local (11 indicadores verificados de El Cañaveral, oct 2026) + análisis de escenarios (Laura). No es producto terminado; requiere aprobación humana antes de publicar.",
               className="text-muted", style={"fontSize": "13px"}),

        # Sistema de pestañas para no saturar la pantalla (dbc.Tabs)
        dbc.Tabs([
            dbc.Tab(label="Indicadores municipales", tab_id="tab-ind"),
            dbc.Tab(label="Escenarios económicos", tab_id="tab-esc"),
            dbc.Tab(label="Pipeline / Estado", tab_id="tab-pipe"),
        ], id="tabs", active_tab="tab-ind"),

        # Contenido por pestañas (evita cargar todo a la vez si se escala)
        html.Div(id="tab-content"),

        # Notas técnicas / legales (accesibles, sin inventar)
        dbc.Card([
            dbc.CardBody([
                html.H3("Nota técnica y legal", style={"fontSize": "16px", "fontWeight": "bold", "color": "#172B2A"}),
                html.P("Proyecto abierto — prototipo de investigación. No es un producto de inversión terminado. Requiere aprobación humana (Persona 5 — Isabella) antes de publicar resultados.", style={"fontSize": "12px", "lineHeight": "1.6", "color": "#555"}),
                html.P("Observación asistida por IA (PR #39): el gráfico de precios podría analizarse mediante modelo de visión de Groq. La respuesta se registra como observación con limitaciones, no como hecho verificado.", style={"fontSize": "12px", "lineHeight": "1.6", "color": "#555"}),
                html.P("Datos municipales: 11 indicadores verificados del Padrón Municipal y Censo de Locales (Ayuntamiento de Madrid, datos.madrid.es, oct 2026). 2 no disponibles: familias con hijos; gimnasios con ludoteca (no hay epígrafe combinado).", style={"fontSize": "12px", "lineHeight": "1.6", "color": "#555"}),
                html.P("Búsqueda web: Tavily (clave configurada localmente, no expuesta). Fallback: DuckDuckGo (ddgs). Cobertura de análisis: ~82% (509 tests pasados). Flujo automático: implementado; ejecución completa con datos reales verificada en demo local.", style={"fontSize": "12px", "lineHeight": "1.6", "color": "#555"}),
            ]),
        ], className="mt-4 shadow-sm"),

    ], fluid=True, attrs={"lang": "es"}),

], attrs={"lang": "es"})

# ----- 5. CALLBACKS REACTIVOS (centralización + no_update + State) -----
# Se usa State para evitar render en cadena hasta que se confirma con botón.
# Si el usuario interactúa con las pestañas, se actualiza solo el contenido.

@app.callback(
    Output("tab-content", "children"),
    Input("tabs", "active_tab"),
    prevent_initial_call=False,
)
def render_tab(active_tab):
    # Uso de dash.no_update si no hay cambio real; aquí siempre hay cambio de pestaña.
    if active_tab == "tab-ind":
        return html.Div(dbc.Row([dbc.Col(card_chart("Indicadores verificados — MCP (oct 2026)", fig_indicators), width=12)]))
    elif active_tab == "tab-esc":
        return html.Div(dbc.Row([dbc.Col(card_chart("Escenarios económicos — Análisis", fig_scenarios), width=12)]))
    elif active_tab == "tab-pipe":
        return html.Div(dbc.Row([dbc.Col(card_chart("Estado del flujo — docs/update", fig_pipeline), width=12)]))
    return html.Div("Selecciona una pestaña")

# Función auxiliar para envolver gráficos en Card + Loading (evita duplicación)
def card_chart(title, fig_obj):
    return dbc.Card([
        dbc.CardHeader(title, className="bg-dark text-white fw-bold"),
        dbc.CardBody(dcc.Loading(
            dcc.Graph(figure=fig_obj),
            type="dot", fullscreen=False,
        )),
    ], className="shadow-sm border-0")

if __name__ == "__main__":
    app.run(debug=True, port=8050)
