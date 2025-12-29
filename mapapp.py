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

# --- ESTILO CSS AVANZADO (Etiquetas, Exportación y Anti-solapamiento) ---
st.markdown("""
    <style>
    html, body, [data-testid="stAppViewContainer"] {
        overflow: hidden;
        height: 100vh;
    }
    .block-container { padding-top: 1rem; }
    
    /* Estilo de las Etiquetas de Datos */
    .promo-label {
        background: white;
        border: 1px solid #2563eb;
        border-radius: 5px;
        padding: 5px 8px;
        font-size: 11px;
        font-weight: bold;
        box-shadow: 2px 2px 5px rgba(0,0,0,0.2);
        white-space: nowrap;
        color: #1e293b;
        position: relative;
    }

    /* Conector de flecha */
    .promo-label::after {
        content: "";
        position: absolute;
        top: 100%;
        left: 50%;
        border-width: 5px;
        border-style: solid;
        border-color: #2563eb transparent transparent transparent;
    }

    /* Ocultar botones para exportación mediante clase print */
    @media print {
        .leaflet-control-zoom, .leaflet-control-layers, .leaflet-control-fullscreen {
            display: none !important;
        }
    }

    div[data-testid="stMetric"] {
        background-color: rgba(125, 125, 125, 0.1);
        border: 1px solid rgba(125, 125, 125, 0.2);
        padding: 10px;
        border-radius: 12px;
    }
    </style>
    """, unsafe_allow_html=True)

# --- FUNCIONES ---
@st.cache_data
def load_data(file):
    try:
        xls = pd.ExcelFile(file)
        df = pd.read_excel(xls, sheet_name='EEMM' if 'EEMM' in xls.sheet_names else 0)
        df.columns = [str(c).strip() for c in df.columns]
        
        cols = {
            'coord': next((c for c in df.columns if 'COORD' in c.upper()), None),
            'ref': next((c for c in df.columns if 'REF' in c.upper()), None),
            'planta': next((c for c in df.columns if 'PLANTA' in c.upper()), None),
            'ciudad': next((c for c in df.columns if 'CIUDAD' in c.upper() or 'MUNICIPIO' in c.upper()), None),
            'tier': next((c for c in df.columns if 'TIER' in c.upper()), None),
            'tipo': next((c for c in df.columns if 'TIPOLOGIA' in c.upper()), None),
            'dorm': next((c for c in df.columns if 'DORM' in c.upper()), None),
            'pvp': next((c for c in df.columns if 'PVP' in c.upper()), None)
        }
        
        if cols['coord']:
            df[['lat', 'lon']] = df[cols['coord']].astype(str).str.split(',', expand=True)
            df['lat'] = pd.to_numeric(df['lat'], errors='coerce')
            df['lon'] = pd.to_numeric(df['lon'], errors='coerce')
            df = df.dropna(subset=['lat', 'lon'])
        return df, cols
    except:
        return None, None

# --- ESTRUCTURA ---
st.title("Mapa de Promociones")

col_mapa, col_stats = st.columns([3, 1])

with st.sidebar:
    st.header("📂 Gestión")
    uploaded_file = st.file_uploader("Subir Excel", type=['xlsx'])
    
    # Interruptor de Etiquetas
    show_labels = st.toggle("Mostrar Etiquetas de Datos", value=True)
    
    # Botón de Exportar (Simulado mediante Print del navegador)
    if st.button("🖼️ Preparar Mapa para Exportar"):
        st.warning("Usa 'Ctrl+P' o 'Imprimir' en tu navegador. Los controles del mapa se ocultarán automáticamente.")

    if st.button("🔄 Resetear"): st.rerun()
    st.divider()

if uploaded_file:
    df_raw, cols = load_data(uploaded_file)
    
    if df_raw is not None:
        with st.sidebar:
            st.header("🔍 Filtros")
            with st.expander("📍 Ciudad / Zona"):
                c_opts = sorted(df_raw[cols['ciudad']].unique().astype(str)) if cols['ciudad'] else []
                sel_c = st.multiselect("Municipios", c_opts, default=c_opts)
            
            with st.expander("🏢 Planta"):
                p_opts = sorted(df_raw[cols['planta']].unique().astype(str)) if cols['planta'] else []
                sel_p = st.multiselect("Plantas", p_opts, default=p_opts)

            # Filtrado
            df_filtered = df_raw.copy()
            if cols['ciudad']: df_filtered = df_filtered[df_filtered[cols['ciudad']].astype(str).isin(sel_c)]
            if cols['planta']: df_filtered = df_filtered[df_filtered[cols['planta']].astype(str).isin(sel_p)]

        with col_stats:
            st.subheader("📊 Estadísticas")
            if not df_filtered.empty:
                st.metric("Promociones", len(df_filtered[cols['ref']].unique()))
                st.metric("Unidades", len(df_filtered))
                if cols['pvp']:
                    st.metric("PVP Medio", f"€{df_filtered[cols['pvp']].mean():,.0f}")
            else:
                st.info("Sin datos")

        with col_mapa:
            if not df_filtered.empty:
                center = [df_filtered['lat'].mean(), df_filtered['lon'].mean()]
                m = folium.Map(location=center, zoom_start=12, tiles=None, control_scale=True)
                sw = df_filtered[['lat', 'lon']].min().values.tolist()
                ne = df_filtered[['lat', 'lon']].max().values.tolist()
                m.fit_bounds([sw, ne])
            else:
                m = folium.Map(location=[41.6, 2.2], zoom_start=8, tiles=None)

            # Capas
            folium.TileLayer('OpenStreetMap', name='Callejero').add_to(m)
            folium.TileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', 
                             attr='Esri', name='Satélite').add_to(m)

            # Marcadores y Etiquetas
            if not df_filtered.empty:
                for i, (name, group) in enumerate(df_filtered.groupby(cols['ref']), 1):
                    row = group.iloc[0]
                    
                    # Marcador numérico
                    folium.Marker(
                        location=[row['lat'], row['lon']],
                        icon=folium.DivIcon(html=f"""
                            <div style="background:#2563eb;color:white;border-radius:50%;width:24px;height:24px;
                            display:flex;justify-content:center;align-items:center;font-weight:bold;border:2px solid white;
                            box-shadow:0 2px 4px rgba(0,0,0,0.3);font-size:10px;">{i}</div>""")
                    ).add_to(m)

                    # Etiqueta de Datos (Permanent Tooltip)
                    if show_labels:
                        label_content = f"""
                        <div class="promo-label">
                            <span style="color:#2563eb">#{i}</span> | {name}<br>
                            {len(group)} uds.
                        </div>
                        """
                        folium.Marker(
                            location=[row['lat'], row['lon']],
                            icon=folium.DivIcon(html=label_content, icon_anchor=(15, 35))
                        ).add_to(m)

            Fullscreen().add_to(m)
            # Solo añadir LayerControl si NO estamos en modo exportación
            folium.LayerControl(position='topright').add_to(m)
            
            st_folium(m, width="100%", height=750, key="mapa_v12")
