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

# --- ESTILO CSS PARA INTERFAZ FIJA Y MODERNA ---
st.markdown("""
    <style>
    /* Estética General */
    .main { background-color: #f8fafc; }
    h1 { color: #1e293b; font-weight: 700; padding-bottom: 20px; }
    
    /* Bloquear scroll innecesario y bordes redondeados */
    [data-testid="stAppViewContainer"] { overflow: hidden; }
    .stMetric { 
        background: white; 
        padding: 15px; 
        border-radius: 12px; 
        box-shadow: 0 1px 3px rgba(0,0,0,0.1); 
    }
    
    /* Ajustar el contenedor del mapa */
    iframe { border-radius: 15px; box-shadow: 0 4px 12px rgba(0,0,0,0.1); }
    </style>
    """, unsafe_allow_html=True)

# --- FUNCIONES DE APOYO ---
@st.cache_data
def load_data(file):
    try:
        xls = pd.ExcelFile(file)
        df = pd.read_excel(xls, sheet_name='EEMM' if 'EEMM' in xls.sheet_names else 0)
        df.columns = [str(c).strip() for c in df.columns]
        
        # Identificar columnas por contenido
        col_coord = next((c for c in df.columns if 'COORD' in c.upper()), None)
        col_ref = next((c for c in df.columns if 'REF' in c.upper()), None)
        col_planta = next((c for c in df.columns if 'PLANTA' in c.upper()), None)
        col_ciudad = next((c for c in df.columns if 'CIUDAD' in c.upper() or 'MUNICIPIO' in c.upper()), None)
        
        if col_coord:
            df[['lat', 'lon']] = df[col_coord].astype(str).str.split(',', expand=True)
            df['lat'] = pd.to_numeric(df['lat'], errors='coerce')
            df['lon'] = pd.to_numeric(df['lon'], errors='coerce')
            df = df.dropna(subset=['lat', 'lon'])
            
        return df, col_ref, col_planta, col_ciudad
    except Exception as e:
        return None, None, None, None

# --- TÍTULO DE LA APP ---
st.title("Mapa de Promociones")

# --- BARRA LATERAL (SIDEBAR) ---
with st.sidebar:
    st.subheader("📁 Carga de Datos")
    uploaded_file = st.file_uploader("Sube tu archivo Excel (.xlsx)", type=['xlsx'])
    
    if st.button("🔄 Resetear Aplicación"):
        st.rerun()
    
    st.divider()
    st.subheader("📊 Indicadores")
    metric_container = st.container()

# --- LÓGICA DE DATOS Y MAPA ---
# Inicializar variables de filtrado
df_filtered = pd.DataFrame()
map_center = [41.6, 2.2]  # Centro por defecto: Catalunya
zoom_level = 8

if uploaded_file:
    df_raw, col_ref, col_planta, col_ciudad = load_data(uploaded_file)
    
    if df_raw is not None and not df_raw.empty:
        # Filtros dinámicos
        with st.sidebar:
            st.subheader("🔍 Filtros")
            
            # Filtro Ciudad
            ciudades = sorted(df_raw[col_ciudad].unique().astype(str)) if col_ciudad else []
            sel_ciudades = st.multiselect("Municipios", ciudades, default=ciudades)
            
            # Filtro Planta
            plantas = sorted(df_raw[col_planta].unique().astype(str)) if col_planta else []
            sel_plantas = st.multiselect("Plantas", plantas, default=plantas)
            
            # Aplicar filtros
            df_filtered = df_raw.copy()
            if col_ciudad: df_filtered = df_filtered[df_filtered[col_ciudad].astype(str).isin(sel_ciudades)]
            if col_planta: df_filtered = df_filtered[df_filtered[col_planta].astype(str).isin(sel_plantas)]
            
            # Actualizar Título si hay ciudades seleccionadas
            if col_ciudad and sel_ciudades:
                st.write(f"**Viendo:** {', '.join(sel_ciudades[:3])}{'...' if len(sel_ciudades)>3 else ''}")
        
        # Actualizar métricas en la sidebar
        with metric_container:
            st.metric("Promociones", len(df_filtered[col_ref].unique()) if col_ref else 0)
            st.metric("Total Unidades", len(df_filtered))
            if 'PVP' in df_filtered.columns:
                st.metric("PVP Medio", f"€{df_filtered['PVP'].mean():,.0f}")

        # Centrar mapa en los datos cargados
        if not df_filtered.empty:
            map_center = [df_filtered['lat'].mean(), df_filtered['lon'].mean()]
            zoom_level = 11

# --- RENDERIZADO DEL MAPA ---
m = folium.Map(location=map_center, zoom_start=zoom_level, tiles=None)

# Añadir Capas
folium.TileLayer('OpenStreetMap', name='Callejero').add_to(m)
folium.TileLayer(
    tiles='https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
    attr='Esri', name='Satélite'
).add_to(m)
folium.TileLayer(
    tiles='https://server.arcgisonline.com/ArcGIS/rest/services/Reference/World_Boundaries_and_Places/MapServer/tile/{z}/{y}/{x}',
    attr='Esri', name='Límites y Calles', overlay=True
).add_to(m)

# Marcadores (solo si hay datos)
if not df_filtered.empty and col_ref:
    # Agrupar por promoción para no repetir puntos si hay varias plantas en la misma coordenada
    for i, (name, group) in enumerate(df_filtered.groupby(col_ref), 1):
        row = group.iloc[0]
        html_popup = f"<b>Ref: {name}</b><br>Unidades: {len(group)}"
        
        folium.Marker(
            location=[row['lat'], row['lon']],
            icon=folium.DivIcon(html=f"""
                <div style="background:#2563eb;color:white;border-radius:50%;width:28px;height:28px;
                display:flex;justify-content:center;align-items:center;font-weight:bold;border:2px solid white;
                box-shadow:0 2px 4px rgba(0,0,0,0.3);font-size:12px;">{i}</div>"""),
            popup=folium.Popup(html_popup, max_width=200)
        ).add_to(m)

Fullscreen().add_to(m)
folium.LayerControl(position='bottomright').add_to(m)

# Mostrar el mapa (Ocupa el 75% de la pantalla para evitar scroll)
st_folium(m, width="100%", height=700, returned_objects=[])

if not uploaded_file:
    st.info("💡 Sube un archivo Excel en la barra lateral para visualizar los datos en el mapa.")
