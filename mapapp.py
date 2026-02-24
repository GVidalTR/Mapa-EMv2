import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
import googlemaps
from folium.plugins import Fullscreen

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="PropTech Analytics Pro", layout="wide")

# Carga de API Key desde Secrets
try:
    API_KEY = st.secrets["GOOGLE_MAPS_API_KEY"]
    gmaps = googlemaps.Client(key=API_KEY)
except:
    st.error("⚠️ Configura 'GOOGLE_MAPS_API_KEY' en los Secrets de Streamlit.")
    st.stop()

# --- FUNCIONES ---
@st.cache_data
def procesar_excel(file):
    try:
        xls = pd.ExcelFile(file)
        nombre_pestana = 'EEMM'
        
        # Verificamos si existe la pestaña EEMM
        if nombre_pestana not in xls.sheet_names:
            st.error(f"❌ No se encontró la pestaña '{nombre_pestana}' en el archivo.")
            return pd.DataFrame(), {}
        
        # Leemos solo esa pestaña
        df = pd.read_excel(xls, sheet_name=nombre_pestana)
        df.columns = [str(c).strip().upper() for c in df.columns]
        
        # Verificamos si existe la columna COORD
        col_coord = next((c for c in df.columns if 'COORD' in c), None)
        
        if not col_coord:
            st.error(f"❌ La pestaña '{nombre_pestana}' no tiene una columna llamada 'COORD'.")
            return pd.DataFrame(), {}

        # Identificar otras columnas clave
        col_ref = next((c for c in df.columns if any(k in c for k in ['REF', 'PROMOCION', 'NOMBRE'])), df.columns[0])
        col_pvp = next((c for c in df.columns if any(k in c for k in ['PVP', 'PRECIO'])), None)
        
        # Limpiar y separar coordenadas
        # Maneja casos con espacios: "42.5, 1.5" -> ["42.5", "1.5"]
        coords = df[col_coord].astype(str).str.replace(' ', '').str.split(',', expand=True)
        df['lat'] = pd.to_numeric(coords[0], errors='coerce')
        df['lon'] = pd.to_numeric(coords[1], errors='coerce')
        
        # Eliminar filas sin coordenadas válidas
        df = df.dropna(subset=['lat', 'lon'])
        
        st.sidebar.success(f"✅ Datos cargados correctamente de '{nombre_pestana}'")
        return df, {'ref': col_ref, 'pvp': col_pvp, 'coord': col_coord}

    except Exception as e:
        st.error(f"Error técnico al procesar el Excel: {e}")
        return pd.DataFrame(), {}

# --- INTERFAZ ---
st.title("🏗️ Market Study: Análisis de Obra Nueva")

with st.sidebar:
    st.header("📂 Gestión de Datos")
    archivo = st.file_uploader("Subir Excel (Pestaña EEMM)", type=['xlsx'])
    if st.button("Limpiar Caché"): st.cache_data.clear()

if archivo:
    df, cols = procesar_excel(archivo)
    
    if not df.empty:
        col_mapa, col_info = st.columns([2, 1])

        with col_mapa:
            # Creamos el mapa centrado en los puntos
            m = folium.Map(
                location=[df['lat'].mean(), df['lon'].mean()], 
                zoom_start=14,
                tiles="https://mt1.google.com/vt/lyrs=y&x={x}&y={y}&z={z}",
                attr="Google"
            )
            
            for _, row in df.iterrows():
                # Formatear el precio para el popup
                precio_val = row.get(cols['pvp'])
                precio_str = f"{precio_val:,.0f}€" if pd.notnull(precio_val) else "Consultar"
                
                folium.Marker(
                    [row['lat'], row['lon']],
                    popup=folium.Popup(f"<b>{row[cols['ref']]}</b><br>PVP: {precio_str}", max_width=300),
                    tooltip=str(row[cols['ref']]),
                    icon=folium.Icon(color="darkblue", icon="home")
                ).add_to(m)
            
            Fullscreen().add_to(m)
            st_folium(m, width="100%", height=700, key="mapa_eemm")

        with col_info:
            st.subheader(f"📊 Resumen Pestaña EEMM")
            st.metric("Total Unidades", len(df))
            if cols['pvp']:
                st.metric("PVP Promedio", f"{df[cols['pvp']].mean():,.0f} €")
            
            st.dataframe(df[[cols['ref'], 'COORD']].head(20), use_container_width=True)
