import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Estudio de Mercado Pro", layout="wide", initial_sidebar_state="collapsed")

# --- ESTILOS CSS TEMA OSCURO ---
CSS = """
<style>
/* Reset y variables de color */
:root {
    --bg-main: #121212;
    --bg-secondary: #1e1e1e;
    --bg-card: #2d2d2d;
    --text-primary: #e0e0e0;
    --text-secondary: #a0a0a0;
    --accent-blue: #3a86ff;
    --border-color: #404040;
}

[data-testid="stHeader"], .block-container { padding: 0 !important; }
html, body, [data-testid="stAppViewContainer"] { 
    overflow: hidden; height: 100vh; background-color: var(--bg-main) !important; color: var(--text-primary) !important;
}

/* Header Profesional Oscuro */
.app-header {
    background-color: var(--bg-secondary); padding: 15px 25px; color: var(--text-primary);
    display: flex; justify-content: space-between; align-items: center;
    border-bottom: 1px solid var(--border-color); height: 60px;
}
.app-title { font-size: 20px; font-weight: 700; letter-spacing: 0.5px; margin: 0; }

/* Tarjetas de Promoción */
.promo-card {
    background-color: var(--bg-card); border: 1px solid var(--border-color); border-radius: 6px;
    padding: 12px; margin-bottom: 10px; transition: 0.2s;
}
.promo-card:hover { border-color: var(--accent-blue); }
.promo-header { display: flex; align-items: center; gap: 10px; margin-bottom: 8px; }
.promo-circle {
    background-color: var(--accent-blue); color: white; border-radius: 50%;
    width: 24px; height: 24px; display: flex; justify-content: center;
    align-items: center; font-size: 11px; font-weight: bold; flex-shrink: 0;
    box-shadow: 0 2px 5px rgba(0,0,0,0.3);
}
.promo-name { font-weight: 700; color: var(--text-primary); font-size: 13px; margin: 0; line-height: 1.2;}
.promo-details { font-size: 11px; color: var(--text-secondary); line-height: 1.6; }
.promo-details b { color: var(--text-primary); }

/* Etiquetas del Mapa */
.map-label {
    background: var(--bg-card) !important; border: 1px solid var(--accent-blue) !important;
    border-radius: 4px !important; padding: 4px 8px !important;
    font-size: 11px !important; font-weight: bold !important;
    color: var(--text-primary) !important; box-shadow: 2px 2px 10px rgba(0,0,0,0.5) !important;
    white-space: nowrap !important;
}

/* UI Streamlit */
.stFileUploader > div > div { background-color: var(--bg-card) !important; border-color: var(--border-color) !important; }
.stMultiSelect div[data-baseweb="select"] { background-color: var(--bg-card) !important; border-color: var(--border-color) !important; color: var(--text-primary) !important; }
.stMultiSelect div[data-baseweb="tag"] { background-color: var(--accent-blue) !important; color: white !important; }
.stMultiSelect label { font-size: 12px !important; font-weight: 600 !important; color: var(--text-primary) !important;}
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)

# --- HEADER VISUAL ---
st.markdown('<div class="app-header"><p class="app-title">ESTUDIO DE MERCADO PRO</p><p style="font-size:12px; color:#a0a0a0; margin:0;">Análisis de Entorno & Pricing</p></div>', unsafe_allow_html=True)

# --- LÓGICA DE DATOS ---
@st.cache_data
def load_data(file):
    try:
        xls = pd.ExcelFile(file)
        df = pd.read_excel(xls, sheet_name='EEMM')
        df.columns = [str(c).strip().upper() for c in df.columns]
        c = {
            'coord': next((x for x in df.columns if 'COORD' in x), None),
            'ref': next((x for x in df.columns if any(k in x for k in ['REF', 'PROMOCION', 'NOMBRE'])), None),
            'vrm': 'VRM SCIC', 'pvp': 'PVP', 'tipo': next((x for x in df.columns if 'TIPOLOGI' in x), None),
            'tier': 'TIER', 'zona': 'ZONA', 'ciudad': next((x for x in df.columns if 'CIUDAD' in x), None),
            'planta': 'PLANTA', 'dorm': 'Nº DORM'
        }
        if c['coord']:
            coords = df[c['coord']].astype(str).str.replace(' ', '').str.split(',', expand=True)
            df['lat'] = pd.to_numeric(coords[0], errors='coerce')
            df['lon'] = pd.to_numeric(coords[1], errors='coerce')
            return df.dropna(subset=['lat', 'lon']), c
        return pd.DataFrame(), {}
    except Exception as e: 
        st.error(f"Error al procesar: {e}")
        return pd.DataFrame(), {}

# --- LAYOUT DE COLUMNAS ---
st.write("") 
col_izq, col_mapa, col_der, col_ctrl = st.columns([1, 3.5, 1, 1.1])

df_final = pd.DataFrame()
