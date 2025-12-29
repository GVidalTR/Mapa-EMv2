import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
import plotly.express as px
from folium.plugins import Fullscreen

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(
    page_title="Mapa de Promociones",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- ESTILO CSS PARA PANTALLA FIJA (NO SCROLL) ---
st.markdown("""
    <style>
    /* Eliminar scroll del cuerpo y ajustar contenedores */
    html, body, [data-testid="stAppViewContainer"] {
        overflow: hidden;
        height: 100vh;
    }
    .block-container {
        padding-top: 1rem;
        padding-bottom: 0rem;
        height: 100vh;
    }
    /* Estética de indicadores y gráficos */
    .stMetric {
        background: #ffffff;
        padding: 10px;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        border: 1px solid #f0f2f6;
    }
    [data-testid="stVerticalBlock"] > div {
        direction: ltr;
    }
    /* Redondear el mapa */
    iframe { border-radius: 15px; }
    </style>
    """, unsafe_allow_html=True)

# --- FUNCIONES DE APOYO ---
@st.cache_data
def load_data(file):
    try:
        xls = pd.ExcelFile(file)
        df = pd.read_excel(xls, sheet_name='EEMM' if 'EEMM' in xls.sheet_names else 0)
        df.columns = [str(c).strip() for c in df.columns]
        
        col_coord = next((c for c in df.columns if 'COORD' in c.upper()), None)
        col_ref = next((c for c in df.columns if 'REF' in c.upper()), None)
        col_planta = next((c for c in df.columns if 'PLANTA' in c.upper()), None)
        col_ciudad = next((c for c in df.columns if 'CIUDAD' in c.upper() or 'MUNICIPIO' in c.upper()), None)
        col_pvp = next((c for c in df.columns if 'PVP' in c.upper()), None)
        
        if col_coord:
            df[['lat', 'lon']] = df[col_coord].astype(str).str.split(',', expand=True)
            df['lat'] = pd.to_numeric(df['lat'], errors='coerce')
            df['lon'] = pd.to_numeric(df['lon'], errors='coerce')
            if col_pvp:
                df[col_pvp] = pd.to_numeric(df[col_pvp], errors='coerce')
            df = df.dropna(subset=['lat', 'lon'])
            
        return df, col_ref, col_planta, col_ciudad, col_pvp
    except Exception as e:
        return None, None, None, None, None

# --- ESTRUCTURA PRINCIPAL ---
st.title("Mapa de Promociones")

# Definición de columnas: 75% Mapa, 25% Estadísticas
col_mapa, col_stats = st.columns([3, 1])

# Inicialización
df_filtered = pd.DataFrame()
map_center = [41.6, 2.2]
zoom_level = 8

with st.sidebar:
    st.subheader("📁 Carga")
    uploaded_file = st.file_uploader("Excel .xlsx", type=['xlsx'])
    if st.button("🔄 Resetear"):
        st.rerun()
    st.divider()

if uploaded_file:
    df_raw, col_ref, col_planta, col_ciudad, col_pvp = load_data(uploaded_file)
    
    if df_raw is not None and not df_raw.empty:
        with st.sidebar:
            st.subheader("🔍 Filtros")
            ciudades = sorted(df_raw[col_ciudad].unique().astype(str)) if col_ciudad else []
            sel_ciudades = st.multiselect("Municipios", ciudades, default=ciudades)
            
            plantas = sorted(df_raw[col_planta].unique().astype(str)) if col_planta else []
            sel_plantas = st.multiselect("Plantas", plantas, default=plantas)
            
            df_filtered = df_raw.copy()
            if col_ciudad: df_filtered = df_filtered[df_filtered[col_ciudad].astype(str).isin(sel_ciudades)]
            if col_planta: df_filtered = df_filtered[df_filtered[col_planta].astype(str).isin(sel_plantas)]

        if not df_filtered.empty:
            map_center = [df_filtered['lat'].mean(), df_filtered['lon'].mean()]
            zoom_level = 11

# --- COLUMNA DERECHA: ESTADÍSTICAS (25%) ---
with col_stats:
    st.subheader("📊 Indicadores")
    if not df_filtered.empty:
        total_promos = len(df_filtered[col_ref].unique()) if col_ref else 0
        st.metric("Promociones", total_promos)
        st.metric("Total Unidades", len(df_filtered))
        
        if col_pvp and not df_filtered[col_pvp].isna().all():
            pvp_med = df_filtered[col_pvp].mean()
            st.metric("PVP Medio", f"€{pvp_med:,.0f}")
        
        # Gráfico pequeño interactivo
        if col_planta:
            fig = px.pie(df_filtered, names=col_planta, hole=0.4, title="Distribución Plantas")
            fig.update_layout(showlegend=False, margin=dict(t=30, b=0, l=0, r=0), height=250)
            st.plotly_chart(fig, use_container_width=True)
    else:
        st.write("Sube datos para ver estadísticas")

# --- COLUMNA IZQUIERDA: MAPA (75%) ---
with col_mapa:
    m = folium.Map(location=map_center, zoom_start=zoom_level, tiles=None)
    
    # Capas
    folium.TileLayer('OpenStreetMap', name='Callejero').add_to(m)
    folium.TileLayer(
        tiles='https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
        attr='Esri', name='Satélite'
    ).add_to(m)
    folium.TileLayer(
        tiles='https://server.arcgisonline.com/ArcGIS/rest/services/Reference/World_Boundaries_and_Places/MapServer/tile/{z}/{y}/{x}',
        attr='Esri', name='Límites y Calles', overlay=True
    ).add_to(m)

    if not df_filtered.empty:
        for i, (name, group) in enumerate(df_filtered.groupby(col_ref), 1):
            row = group.iloc[0]
            folium.Marker(
                location=[row['lat'], row['lon']],
                icon=folium.DivIcon(html=f"""
                    <div style="background:#2563eb;color:white;border-radius:50%;width:26px;height:26px;
                    display:flex;justify-content:center;align-items:center;font-weight:bold;border:2px solid white;
                    box-shadow:0 2px 4px rgba(0,0,0,0.3);font-size:11px;">{i}</div>"""),
                popup=folium.Popup(f"<b>Ref: {name}</b><br>Unidades: {len(group)}", max_width=200)
            ).add_to(m)

    Fullscreen().add_to(m)
    folium.LayerControl(position='topright').add_to(m)
    
    # Renderizar mapa con altura fija para evitar scroll
    st_folium(m, width="100%", height=750, returned_objects=[])
