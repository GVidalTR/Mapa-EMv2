import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
import plotly.express as px
from folium.plugins import Fullscreen

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(
    page_title="Mapa Promociones",
    page_icon="📍",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- ESTILO CSS PARA ESTÉTICA MODERNA Y FIJAR PANTALLA ---
st.markdown("""
    <style>
    /* Tipografía y bordes redondeados */
    html, body, [data-testid="stAppViewContainer"] {
        font-family: 'Inter', sans-serif;
        overflow: hidden; /* Evita scroll general */
    }
    .stMetric {
        background: rgba(240, 242, 246, 0.5);
        padding: 15px;
        border-radius: 15px;
        border: 1px solid #e0e0e0;
    }
    [data-testid="stSidebar"] {
        background-color: #f8fafc;
        border-right: 1px solid #e2e8f0;
    }
    .stButton>button {
        border-radius: 10px;
        transition: all 0.3s;
    }
    /* Estilo para el contenedor del mapa */
    iframe {
        border-radius: 20px;
    }
    </style>
    """, unsafe_allow_html=True)

# --- FUNCIONES DE PROCESAMIENTO ---
@st.cache_data
def load_data(file):
    try:
        xls = pd.ExcelFile(file)
        df = pd.read_excel(xls, sheet_name='EEMM' if 'EEMM' in xls.sheet_names else 0)

        # Normalización de nombres de columnas
        df.columns = [str(c).strip() for c in df.columns]
        
        # Identificar columnas críticas
        col_coord = next((c for c in df.columns if 'COORD' in c.upper()), None)
        col_ref = next((c for c in df.columns if 'REF' in c.upper()), None)
        col_planta = next((c for c in df.columns if 'PLANTA' in c.upper()), None)
        
        if not col_coord:
            st.error("Columna COORD no encontrada.")
            return None

        # Parsing de coordenadas
        df[['lat', 'lon']] = df[col_coord].astype(str).str.split(',', expand=True)
        df['lat'] = pd.to_numeric(df['lat'], errors='coerce')
        df['lon'] = pd.to_numeric(df['lon'], errors='coerce')
        df = df.dropna(subset=['lat', 'lon'])

        return df, col_ref, col_planta
    except Exception as e:
        st.error(f"Error: {e}")
        return None, None, None

# --- LÓGICA DE INTERFAZ ---
with st.sidebar:
    st.title("📊 Estadísticas y Carga")
    uploaded_file = st.file_uploader("Sube tu Excel", type=['xlsx'])
    st.divider()

if uploaded_file:
    df_raw, col_ref, col_planta = load_data(uploaded_file)
    
    if df_raw is not None:
        # Título dinámico basado en municipios únicos
        municipios = df_raw['Ciudad'].unique() if 'Ciudad' in df_raw.columns else []
        nombre_municipios = " - ".join(map(str, municipios))
        st.header(f"Mapa Promociones {nombre_municipios}")

        # --- FILTROS EN SIDEBAR ---
        with st.sidebar:
            if st.button("🔄 Resetear Filtros"):
                st.rerun()
            
            # Filtro de Planta
            opciones_planta = sorted(df_raw[col_planta].unique().astype(str)) if col_planta else []
            plantas_sel = st.multiselect("Filtrar por Planta", opciones_planta, default=opciones_planta)
            
            # Otros filtros (Ciudad, Tipo...)
            ciudades_sel = st.multiselect("Ciudad", sorted(df_raw['Ciudad'].unique()), default=df_raw['Ciudad'].unique())
            
            # Aplicar filtros
            df_filtered = df_raw[
                (df_raw[col_planta].astype(str).isin(plantas_sel)) & 
                (df_raw['Ciudad'].isin(ciudades_sel))
            ]

            # --- MÉTRICAS EN SIDEBAR (Petición 3) ---
            st.divider()
            st.subheader("Indicadores")
            st.metric("Promociones", len(df_filtered[col_ref].unique()))
            st.metric("Unidades Totales", len(df_filtered))
            st.metric("PVP Promedio", f"€{df_filtered['PVP'].mean():,.0f}" if 'PVP' in df_filtered.columns else "N/A")
            st.metric("SCIC Promedio", f"€{df_filtered['VRM SCIC'].mean():,.0f}" if 'VRM SCIC' in df_filtered.columns else "N/A")

        # --- MAPA ---
        # Mapa con capa satélite y etiquetas (Esri World Transportation añade nombres/límites)
        m = folium.Map(location=[df_filtered['lat'].mean(), df_filtered['lon'].mean()], zoom_start=12, tiles=None)
        
        # Capa Satélite
        folium.TileLayer(
            tiles='https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
            attr='Esri',
            name='Satélite'
        ).add_to(m)
        
        # Capa de etiquetas de municipios y límites (Petición 4)
        folium.TileLayer(
            tiles='https://server.arcgisonline.com/ArcGIS/rest/services/Reference/World_Boundaries_and_Places/MapServer/tile/{z}/{y}/{x}',
            attr='Esri',
            name='Límites y Nombres',
            overlay=True
        ).add_to(m)

        # Marcadores con número (Petición 5)
        for i, (idx, row) in enumerate(df_filtered.drop_duplicates(subset=[col_ref]).iterrows(), 1):
            folium.Marker(
                location=[row['lat'], row['lon']],
                icon=folium.DivIcon(html=f"""
                    <div style="
                        background-color: #2563eb;
                        color: white;
                        border-radius: 50%;
                        width: 25px;
                        height: 25px;
                        display: flex;
                        justify-content: center;
                        align-items: center;
                        font-weight: bold;
                        border: 2px solid white;
                        box-shadow: 0px 2px 5px rgba(0,0,0,0.3);
                        font-size: 12px;
                    ">{i}</div>
                """),
                popup=f"Ref: {row[col_ref]}"
            ).add_to(m)

        Fullscreen().add_to(m)
        
        # Mostrar mapa ajustado al alto de pantalla (Petición 1)
        st_folium(m, width="100%", height=700, returned_objects=[])

else:
    st.info("Por favor, sube un archivo Excel para visualizar el mapa.")

# --- SELECTOR DE TEMA (Petición 7) ---
# Nota: Streamlit ya incluye selector de tema en Settings, 
# pero podemos forzar visibilidad con un recordatorio o CSS.
st.sidebar.caption("Ajusta el tema Claro/Oscuro en la configuración de la app (Menú > Settings).")
