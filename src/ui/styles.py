
import streamlit as st


def apply_styles():
    st.markdown(
        """
        <style>
        :root {
            --background: #EAEFE9;
            --primary: #13404B;
            --primary-dark: #13404B;
            --coral: #E26D5C;
            --sage: #819885;
            --peach: #F4D0A4;
        }

        .stApp {
            background: var(--background);
            color: var(--text);
            font-family: sans-serif;
        }

        [data-testid="stMain"] {
            background: var(--background);
        }

        [data-testid="stMainBlockContainer"] {
            padding-top: 2.5rem;
            padding-bottom: 3rem;
            max-width: 1440px;
        }

        /* SIDEBAR */

        section[data-testid="stSidebar"],
        section[data-testid="stSidebar"] > div {
            background: #FFFFFF !important;
        }

        section[data-testid="stSidebar"] {
            border-right: 1px solid var(--border);
        }

        section[data-testid="stSidebar"] * {
            color: var(--text);
        }

        section[data-testid="stSidebar"] [data-testid="stCaptionContainer"] {
            color: var(--muted) !important;
        }

        section[data-testid="stSidebar"] [data-testid="stSidebarNav"] {
            padding-top: 12px;
        }

        section[data-testid="stSidebar"] [data-testid="stSidebarNav"] a {
            border-radius: 10px;
            padding: 10px 12px;
            margin: 3px 0;
            transition: background 0.2s ease;
        }

        section[data-testid="stSidebar"] [data-testid="stSidebarNav"] a:hover {
            background: var(--sage);
        }

        section[data-testid="stSidebar"] [data-testid="stSidebarNav"]
        a[aria-current="page"] {
            background: var(--sage);
            font-weight: 650;
        }

        /* BRAND */

        .brand {
            padding: 14px 6px 24px;
        }

        .brand h1 {
            color: var(--primary-dark) !important;
            font-size: 29px;
            font-weight: 800;
            letter-spacing: -1.2px;
            margin: 0;
        }

        .brand h1 span {
            color: var(--coral) !important;
        }

        .brand p {
            color: var(--muted) !important;
            font-size: 9px;
            letter-spacing: 2px;
            font-weight: 700;
            margin-top: 5px;
        }

        .brand small {
            color: var(--muted) !important;
            font-size: 10px;
        }

        /* HEADINGS */

        .stApp h1,
        .stApp h2,
        .stApp h3 {
            color: var(--primary-dark);
            letter-spacing: -0.5px;
        }

        /* METRICS */

        [data-testid="stMetric"] {
            background: #FFFFFF !important;
            border: 1px solid #DCE9DF !important;
            border-radius: 16px !important;
            padding: 20px !important;
            min-height: 115px;
            box-shadow: 0 2px 8px rgba(19, 64, 75, 0.06);
        }

        [data-testid="stMetricLabel"] {
            color: #819885 !important;
            font-size: 14px !important;
            font-weight: 600 !important;
        }

        [data-testid="stMetricValue"] {
            color: #13404B !important;
            font-size: clamp(17px, 1.5vw, 28px) !important;
            font-weight: 750 !important;
            white-space: normal !important;
            overflow-wrap: anywhere !important;
            line-height: 1.3 !important;
        }

        /* BUTTONS */

        .stApp [data-testid="stButton"] button {
            background: var(--primary);
            color: white;
            border: 1px solid var(--primary);
            border-radius: 11px;
            min-height: 42px;
            font-weight: 600;
            transition: all 0.2s ease;
        }

        .stApp [data-testid="stButton"] button:hover {
            background: var(--primary-dark);
            border-color: var(--primary-dark);
            color: white;
        }

        /* INPUTS */

        .stApp input,
        .stApp textarea,
        .stApp [data-baseweb="select"] > div {
            border-radius: 10px;
        }

        /* TABLES */

        [data-testid="stDataFrame"] {
            border: 1px solid var(--border);
            border-radius: 14px;
            overflow: hidden;
        }

        /* ALERTS */

        [data-testid="stAlert"] {
            border-radius: 12px;
        }

        /* DIVIDERS */

        hr {
            border-color: var(--border) !important;
        }

        /* REMOVE EXCESS DECORATION */

        #MainMenu {
            visibility: hidden;
        }

        /* RESUMEN INFORMATIVO FITFAMILY */

        .ff-summary {
            background: #E1EDE2;
            border: 1px solid #B9D2BE;
            border-left: 5px solid #819885;
            border-radius: 15px;
            padding: 16px 20px;
            margin: 12px 0 22px;
            color: #13404B;
            font-weight: 600;
            line-height: 1.6;
        }

        .ff-summary p {
            margin: 0;
        }

        .ff-summary strong {
            color: #13404B;
        }

        /* INDICACIÓN DE ESCENARIO DE REFERENCIA */

        .ff-reference {
            background: #E1EDE2;
            border: 1px solid #B9D2BE;
            border-radius: 12px;
            padding: 13px 18px;
            margin: 12px 0 18px;
            color: #13404B;
            font-weight: 650;
            font-size: 15px;
        }

        footer {
            visibility: hidden;
        }

        </style>
        """,
        unsafe_allow_html=True,
    )
