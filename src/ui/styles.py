
import streamlit as st


def apply_styles():
    st.markdown(
        """
        <style>
        :root {
            --primary: #527A60;
            --primary-dark: #365744;
            --coral: #D98C79;
            --sage: #DCE9DF;
            --lavender: #E9E4F2;
            --peach: #F5E8DA;
            --background: #F7F6F2;
            --surface: #FFFFFF;
            --text: #293B32;
            --muted: #879189;
            --border: #EAECE6;
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
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: 16px;
            padding: 20px;
            box-shadow: 0 2px 8px rgba(40, 60, 45, 0.025);
        }

        [data-testid="stMetricLabel"] {
            color: var(--muted) !important;
        }

        [data-testid="stMetricValue"] {
            color: var(--primary-dark) !important;
            font-weight: 750;
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

        footer {
            visibility: hidden;
        }

        </style>
        """,
        unsafe_allow_html=True,
    )
