import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
import googlemaps
from folium.plugins import Fullscreen

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="PropTech Analytics Pro", layout="wide")

# Carga de la API Key desde Secrets
try:
    API_KEY = st.secrets["GOOGLE_MAPS_API_KEY"]
    gmaps = googlemaps.Client(key=API_KEY)
except:
    st.error("⚠️ No se encontró la Google Maps API Key en los Secrets.")
    st.stop()

# --- FUNCIONES DE ANÁLISIS ---
def buscar_servicios(lat, lon, tipo):
    """Busca lugares cercanos usando Google Places API"""
    try:
        # Buscamos en un radio de 1000 metros
        places_result = gmaps.places_nearby(
            location=(lat, lon),
            radius=1000,
            type=tipo
        )
        return len(places_result.get('results', []))
    except:
        return 0

@st.cache_data
def procesar_excel(file):
    df = pd.read_excel(file)
    df.columns = [str(c).strip().upper() for c in df.columns]
    
    # Buscamos columnas clave
    col_ref = next((c for c in df.columns if 'REF' in c or 'PROMOCION' in c), None)
    col_coord = next((c for c in df.columns if 'COORD' in c), None)
    col_pvp = next((c for c in df.columns if 'PVP' in c or 'PRECIO' in c), None)
    
    if col_coord:
        coords = df[col_coord].astype(str).str.split(',', expand=True)
        df['lat'] = pd.to_numeric(coords[0], errors='coerce')
        df['lon'] = pd.to_numeric(coords[1], errors='coerce')
        df = df.dropna(subset=['lat', 'lon'])
    
    return df, {'ref': col_ref, 'pvp': col_pvp}

# --- INTERFAZ ---
st.title("🏗️ Market Study: Análisis de Obra Nueva")

with st.sidebar:
    st.header("📂 Datos")
    archivo = st.file_uploader("Subir Excel", type=['xlsx'])
    distancia_analisis = st.slider("Radio de análisis (metros)", 500, 2000, 1000)
    if st.button("Limpiar Caché"): st.cache_data.clear()

if archivo:
    df, cols = procesar_excel(archivo)
    
    # Análisis de entorno bajo demanda
    if st.sidebar.button("🔍 Analizar Servicios Cercanos"):
        with st.status("Consultando Google Places..."):
            df['Supermercados'] = df.apply(lambda r: buscar_servicios(r['lat'], r['lon'], 'supermarket'), axis=1)
            df['Colegios'] = df.apply(lambda r: buscar_servicios(r['lat'], r['lon'], 'school'), axis=1)
        st.sidebar.success("¡Análisis completado!")

    # Layout de la App
    col_mapa, col_info = st.columns([2, 1])

    with col_mapa:
        m = folium.Map(
            location=[df['lat'].mean(), df['lon'].mean()], 
            zoom_start=14,
            tiles="https://mt1.google.com/vt/lyrs=y&x={x}&y={y}&z={z}",
            attr="Google"
        )
        
        for _, row in df.iterrows():
            # Color basado en precio (opcional)
            popup_text = f"<b>{row[cols['ref']]}</b><br>PVP: {row[cols['pvp']]:,.0f}€"
            if 'Supermercados' in df.columns:
                popup_text += f"<br>🛒 Supermercados: {row['Supermercados']}<br>🎓 Colegios: {row['Colegios']}"

            folium.Marker(
                [row['lat'], row['lon']],
                popup=folium.Popup(popup_text, max_width=300),
                tooltip=row[cols['ref']],
                icon=folium.Icon(color="darkblue", icon="info-sign")
            ).add_to(m)
        
        Fullscreen().add_to(m)
        st_folium(m, width="100%", height=600)

    with col_info:
        st.subheader("📊 Resumen de Mercado")
        st.dataframe(df[[cols['ref'], cols['pvp']] + (['Supermercados', 'Colegios'] if 'Supermercados' in df.columns else [])], use_container_width=True)
        
        if cols['pvp']:
            st.write(f"**Precio Medio:** {df[cols['pvp']].mean():,.2f} €")
