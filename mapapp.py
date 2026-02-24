import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
from folium.plugins import Fullscreen

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Estudio de Mercado Pro", layout="wide", initial_sidebar_state="collapsed")

# --- ESTILOS CSS TEMA OSCURO (Seguro para Streamlit) ---
CSS = """
<style>
/* Ocultar cabecera por defecto y ajustar márgenes */
header[data-testid="stHeader"] { display: none !important; }
.block-container { padding-top: 1rem !important; padding-bottom: 1rem !important; max-width: 98% !important; }

/* Forzar fondo oscuro en la aplicación */
[data-testid="stAppViewContainer"] {
    background-color: #121212 !important;
}

/* Textos globales */
p, h1, h2, h3, h4, h5, h6, label, span {
    color: #e0e0e0 !important;
}

/* Header Profesional Oscuro */
.app-header {
    background-color: #1e1e1e; padding: 15px 25px; 
    border-bottom: 2px solid #3a86ff; border-radius: 8px;
    margin-bottom: 20px; display: flex; justify-content: space-between; align-items: center;
}
.app-title { font-size: 20px !important; font-weight: 800 !important; margin: 0 !important; color: #ffffff !important; }

/* Tarjetas de Promoción */
.promo-card {
    background-color: #2d2d2d; border: 1px solid #404040; border-radius: 6px;
    padding: 12px; margin-bottom: 10px; transition: 0.2s;
}
.promo-card:hover { border-color: #3a86ff; }
.promo-header { display: flex; align-items: center; gap: 10px; margin-bottom: 8px; }
.promo-circle {
    background-color: #3a86ff; color: white; border-radius: 50%;
    width: 24px; height: 24px; display: flex; justify-content: center;
    align-items: center; font-size: 11px; font-weight: bold; flex-shrink: 0;
}
.promo-name { font-weight: 700 !important; color: #ffffff !important; font-size: 13px !important; margin: 0 !important; }
.promo-details { font-size: 11px !important; color: #a0a0a0 !important; line-height: 1.5 !important; }
.promo-details b { color: #ffffff !important
