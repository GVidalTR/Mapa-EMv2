import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
from folium.plugins import Fullscreen

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Estudio de Mercado Pro", layout="wide", initial_sidebar_state="collapsed")

# --- ESTILOS CSS TEMA OSCURO (Basado en la imagen de referencia) ---
st.markdown("""
    <style>
    /* Reset y variables de color */
    :root {
        --bg-main: #121212;       /* Fondo principal muy oscuro */
        --bg-secondary: #1e1e1e;  /* Sidebar y Header */
        --bg-card: #2d2d2d;       /* Fondo de tarjetas y paneles */
        --text-primary: #e0e0e0;  /* Texto principal claro */
        --text-secondary: #a0a0a0; /* Texto secundario gris */
        --accent-blue: #3a86ff;   /* Color de acento vibrante */
        --border-color: #404040;  /* Bordes sutiles */
    }

    /* Estructura global y scroll */
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

    /* Contenedores y Textos */
    h5 { color: var(--text-primary) !important; font-weight: 600 !important; }
    hr { border-color: var(--border-color) !important; }
    .stMarkdown p { color: var(--text-secondary) !important; }

    /* Tarjetas de Promoción (Estilo Oscuro) */
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

    /* Etiquetas del Mapa (Estilo Oscuro) */
    .map-label {
