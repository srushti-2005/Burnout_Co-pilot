# src/ui/styles.py

import streamlit as st

def hide_toggle_tooltip():
    st.markdown("""
    <script>
    const removeTooltip = () => {
        document.querySelectorAll('[data-testid="collapsedControl"], [data-testid="stSidebarCollapseButton"]')
            .forEach(el => el.removeAttribute('title'));
    };
    removeTooltip();
    new MutationObserver(removeTooltip).observe(document.body, {childList: true, subtree: true});
    </script>
    """, unsafe_allow_html=True)


def apply_custom_styles():
    css = """
    <style>

    /* ── GOOGLE FONTS ──────────────────────────────────────────────────────── */
    @import url('https://fonts.googleapis.com/css2?family=Nunito:wght@400;600;700;800;900&family=Quicksand:wght@500;600;700&display=swap');

    /* ── CSS VARIABLES ─────────────────────────────────────────────────────── */
    :root {
        --clay-bg:        #f0f4ff;
        --clay-surface:   #ffffff;
        --clay-primary:   #ff6b6b;
        --clay-secondary: #4ecdc4;
        --clay-accent:    #ffe66d;
        --clay-purple:    #a8a4ff;
        --clay-green:     #7bed9f;
        --clay-text:      #2d3561;
        --clay-muted:     #8892b0;
        --clay-shadow:    6px 6px 0px #c8d0f0;
        --clay-shadow-sm: 3px 3px 0px #c8d0f0;
        --clay-radius:    20px;
        --clay-radius-sm: 12px;
    }

    /* ── GLOBAL BACKGROUND ─────────────────────────────────────────────────── */
    .stApp {
        background: linear-gradient(135deg, #f0f4ff 0%, #e8f0fe 50%, #f5f0ff 100%) !important;
        font-family: 'Nunito', sans-serif !important;
    }

    /* ── HIDE STREAMLIT CHROME — SIDEBAR TOGGLE FORCED VISIBLE ──────────────
       Only the hamburger menu and footer are hidden. Nothing here touches
       the header shell or its toolbar as a whole, because either of those
       can contain (or be a sibling of) the sidebar toggle button depending
       on Streamlit version, and hiding them was swallowing the toggle.
       The toggle itself is force-shown below with maximum specificity so
       no other rule in this file can hide it again. ────────────────────── */
    #MainMenu { visibility: hidden; }
    footer { visibility: hidden; }

    [data-testid="collapsedControl"] {
        visibility: visible !important;
        display: flex !important;
        opacity: 1 !important;
        pointer-events: auto !important;
        z-index: 999999 !important;
    }
    [data-testid="stSidebarCollapseButton"] {
        visibility: visible !important;
        display: flex !important;
        opacity: 1 !important;
        pointer-events: auto !important;
        z-index: 999999 !important;
    }
    /* Suppresses the floating tooltip box that shows the button's raw
       accessible label ("keyboard_double_arrow_left" etc.) on hover.
       Streamlit renders this via BaseWeb's tooltip/popover component
       (data-baseweb="tooltip"), not as literal text in our own CSS —
       this hides that popover specifically. Note: this hides ALL
       BaseWeb tooltips app-wide, not just this button's, since
       tooltips render in a portal outside the button's own element
       tree and can't be scoped to just one trigger. If you rely on
       hover tooltips elsewhere (e.g. on help icons), those will be
       hidden too — say so if that's a problem and we'll scope it
       differently. */
    div[data-baseweb="tooltip"] {
        display: none !important;
    }

    .block-container {
        padding-top: 2rem !important;
        padding-bottom: 2rem !important;
    }

    /* ── MAIN TITLE ────────────────────────────────────────────────────────── */
    h1 {
        font-family: 'Nunito', sans-serif !important;
        font-weight: 900 !important;
        color: var(--clay-text) !important;
        font-size: 2.2rem !important;
        letter-spacing: -0.5px !important;
    }

    /* ── ALL HEADINGS ──────────────────────────────────────────────────────── */
    h2, h3, h4 {
        font-family: 'Nunito', sans-serif !important;
        font-weight: 800 !important;
        color: var(--clay-text) !important;
    }

    /* ── SIDEBAR ────────────────────────────────────────────────────────────── */
    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #ffffff 0%, #f5f0ff 100%) !important;
        border-right: 3px solid #e0e8ff !important;
        box-shadow: 4px 0 20px rgba(168, 164, 255, 0.15) !important;
    }

    section[data-testid="stSidebar"] .stSelectbox label,
    section[data-testid="stSidebar"] .stSlider label,
    section[data-testid="stSidebar"] p,
    section[data-testid="stSidebar"] span {
        color: var(--clay-text) !important;
        font-family: 'Nunito', sans-serif !important;
        font-weight: 600 !important;
    }

    section[data-testid="stSidebar"] h1,
    section[data-testid="stSidebar"] h2,
    section[data-testid="stSidebar"] h3 {
        color: var(--clay-text) !important;
    }

    /* ── SIDEBAR SUCCESS/WARNING/INFO BOXES ─────────────────────────────────── */
    section[data-testid="stSidebar"] .stAlert {
        border-radius: var(--clay-radius-sm) !important;
        border: 2px solid !important;
        box-shadow: var(--clay-shadow-sm) !important;
        font-family: 'Nunito', sans-serif !important;
        font-weight: 600 !important;
    }

    /* ── SIDEBAR SLIDERS ────────────────────────────────────────────────────── */
    section[data-testid="stSidebar"] .stSlider div[data-baseweb="slider"] > div > div {
        background: var(--clay-primary) !important;
    }
    section[data-testid="stSidebar"] .stSlider div[role="slider"] {
        background: var(--clay-primary) !important;
        border: 3px solid white !important;
        box-shadow: 2px 2px 0px #ffb3b3 !important;
        width: 20px !important;
        height: 20px !important;
        border-radius: 50% !important;
    }

    /* ── SIDEBAR SELECTBOX ──────────────────────────────────────────────────── */
    section[data-testid="stSidebar"] .stSelectbox > div > div {
        background: white !important;
        border: 2px solid #e0e8ff !important;
        border-radius: var(--clay-radius-sm) !important;
        box-shadow: var(--clay-shadow-sm) !important;
        color: var(--clay-text) !important;
        font-family: 'Nunito', sans-serif !important;
        font-weight: 600 !important;
    }

    /* ── METRIC CARDS (the 3 wellness cards) ───────────────────────────────── */
    div[data-testid="stMetric"] {
        background: white !important;
        border-radius: var(--clay-radius) !important;
        border: 2.5px solid #e0e8ff !important;
        box-shadow: var(--clay-shadow) !important;
        padding: 20px 24px !important;
        transition: transform 0.2s ease, box-shadow 0.2s ease !important;
    }

    div[data-testid="stMetric"]:hover {
        transform: translate(-2px, -2px) !important;
        box-shadow: 8px 8px 0px #c8d0f0 !important;
    }

    div[data-testid="stMetric"] label {
        color: var(--clay-muted) !important;
        font-family: 'Nunito', sans-serif !important;
        font-weight: 700 !important;
        font-size: 0.85rem !important;
        text-transform: uppercase !important;
        letter-spacing: 0.5px !important;
    }

    div[data-testid="stMetric"] [data-testid="stMetricValue"] {
        color: var(--clay-text) !important;
        font-family: 'Nunito', sans-serif !important;
        font-weight: 900 !important;
        font-size: 2rem !important;
    }

    div[data-testid="stMetric"] [data-testid="stMetricDelta"] {
        color: var(--clay-muted) !important;
        font-family: 'Nunito', sans-serif !important;
        font-weight: 600 !important;
        font-size: 0.8rem !important;
    }

    /* ── PLOTLY CHART CONTAINERS ────────────────────────────────────────────── */
    div[data-testid="stPlotlyChart"] {
        background: white !important;
        border-radius: var(--clay-radius) !important;
        border: 2.5px solid #e0e8ff !important;
        box-shadow: 6px 6px 0px #c8d0f0 !important;
        padding: 8px !important;
        transition: transform 0.2s ease, box-shadow 0.2s ease !important;
        overflow: hidden !important;
    }

    div[data-testid="stPlotlyChart"]:hover {
        transform: translate(-2px, -2px) !important;
        box-shadow: 8px 8px 0px #c8d0f0 !important;
    }

    /* ── LINE CHART (st.line_chart / Vega) ──────────────────────────────────── */
    div[data-testid="stArrowVegaLiteChart"] {
        background: white !important;
        border-radius: var(--clay-radius) !important;
        border: 2.5px solid #e0e8ff !important;
        box-shadow: 6px 6px 0px #c8d0f0 !important;
        padding: 12px !important;
        transition: transform 0.2s ease, box-shadow 0.2s ease !important;
        overflow: hidden !important;
    }

    div[data-testid="stArrowVegaLiteChart"]:hover {
        transform: translate(-2px, -2px) !important;
        box-shadow: 8px 8px 0px #c8d0f0 !important;
    }

    /* ── VEGA CHART (fallback selector) ─────────────────────────────────────── */
    div[data-testid="stVegaLiteChart"] {
        background: white !important;
        border-radius: var(--clay-radius) !important;
        border: 2.5px solid #e0e8ff !important;
        box-shadow: 6px 6px 0px #c8d0f0 !important;
        padding: 12px !important;
        overflow: hidden !important;
    }

    /* ── DATAFRAME / TABLE ──────────────────────────────────────────────────── */
    div[data-testid="stDataFrame"] {
        background: white !important;
        border-radius: var(--clay-radius) !important;
        border: 2.5px solid #e0e8ff !important;
        box-shadow: var(--clay-shadow) !important;
        overflow: hidden !important;
    }

    /* ── SUBHEADERS ─────────────────────────────────────────────────────────── */
    div[data-testid="stMarkdownContainer"] h3 {
        color: var(--clay-text) !important;
        font-family: 'Nunito', sans-serif !important;
        font-weight: 800 !important;
    }

    /* ── CAPTIONS ───────────────────────────────────────────────────────────── */
    div[data-testid="stCaptionContainer"] p,
    .stCaption p {
        color: var(--clay-muted) !important;
        font-family: 'Quicksand', sans-serif !important;
        font-weight: 500 !important;
    }

    /* ── SPINNER ────────────────────────────────────────────────────────────── */
    .stSpinner > div {
        border-top-color: var(--clay-primary) !important;
    }

    /* ── SUCCESS / WARNING / INFO ALERTS ────────────────────────────────────── */
    div[data-testid="stAlert"] {
        border-radius: var(--clay-radius-sm) !important;
        border-width: 2px !important;
        box-shadow: var(--clay-shadow-sm) !important;
        font-family: 'Nunito', sans-serif !important;
        font-weight: 600 !important;
    }

    /* ── HORIZONTAL RULE ─────────────────────────────────────────────────────── */
    hr {
        border: none !important;
        border-top: 2.5px dashed #d0d8f0 !important;
        margin: 1.5rem 0 !important;
    }

    /* ── SECTION HEADINGS (markdown h3/h4) ──────────────────────────────────── */
    .stMarkdown h3 {
        background: linear-gradient(90deg, var(--clay-text), var(--clay-purple));
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
    }

    /* ── INSIGHT CARDS (the red/green driver cards) ──────────────────────────── */
    /* These are rendered via st.markdown unsafe_allow_html — clay shadow applied */
    .element-container div[style*="border-left"] {
        box-shadow: var(--clay-shadow-sm) !important;
    }

    /* ── COMPARISON CARDS (4 column cards) ──────────────────────────────────── */
    .element-container div[style*="border-radius:10px"] {
        box-shadow: var(--clay-shadow) !important;
        transition: transform 0.2s ease !important;
    }

    /* ── HIDE STREAMLIT DOCS/HELP PANEL IN SIDEBAR ─────────────────────────── */
    section[data-testid="stSidebar"] iframe { display:none !important; }
    section[data-testid="stSidebar"] [data-testid="stHelpText"] { display:none !important; }
    section[data-testid="stSidebar"] .element-container:has(iframe) { display:none !important; }
    /* Hide any auto-generated dark code/docs blocks */
    section[data-testid="stSidebar"] pre { display:none !important; }
    section[data-testid="stSidebar"] code { display:none !important; }
    section[data-testid="stSidebar"] .stCodeBlock { display:none !important; }

    /* ── SCROLLBAR ───────────────────────────────────────────────────────────── */
    ::-webkit-scrollbar { width: 8px; }
    ::-webkit-scrollbar-track { background: #f0f4ff; border-radius: 10px; }
    ::-webkit-scrollbar-thumb {
        background: #c8d0f0;
        border-radius: 10px;
        border: 2px solid #f0f4ff;
    }
    ::-webkit-scrollbar-thumb:hover { background: var(--clay-purple); }

    </style>
    """
    st.markdown(css, unsafe_allow_html=True)

    # ── Inject clay-style page title with emoji badge ─────────────────────────
    st.markdown("""
    <style>
    /* Clay badge on the title icon */
    .title-badge {
        display: inline-flex;
        align-items: center;
        gap: 12px;
    }
    .title-badge .icon {
        background: linear-gradient(135deg, #a8a4ff, #ff6b6b);
        border-radius: 16px;
        width: 48px; height: 48px;
        display: inline-flex; align-items: center; justify-content: center;
        font-size: 1.4rem;
        box-shadow: 4px 4px 0px #c8d0f0;
        border: 2.5px solid white;
    }
    </style>
    """, unsafe_allow_html=True)

    