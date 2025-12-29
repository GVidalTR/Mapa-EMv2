import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
import plotly.express as px
from folium.plugins import Fullscreen

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="Mapa de Promociones", layout="wide", initial_sidebar_state="expanded")

# --- CSS PERSONALIZADO (Azul Marino y Etiquetas) ---
st.markdown("""
    <style>
    html, body, [data-testid="stAppViewContainer"] { overflow: hidden; height: 100vh; }
    .stButton>button { background-color: #001f3f !important; color: white !important; border-radius: 8px; width: 100%; }
    
    /* Etiquetas: Rectángulo horizontal, semitransparente */
    .promo-label {
        background: rgba(255, 255, 255, 0.85);
        border: 1px solid rgba(0, 31, 63, 0.3);
        border-radius: 4px;
        padding: 2px 6px;
        font-size: 9px !important;
        color: #001f3f;
        box-shadow: 1px 1px 3px rgba(0,0,0,0.1);
        display: flex;
        flex-direction: row;
        gap: 5px;
        align-items: center;
        white-space: nowrap;
    }

    /* Contenedor de métricas */
    div[data-testid="stMetric"] {
        background-color: rgba(0, 31, 63, 0.05);
        border: 1px solid rgba(0, 31, 63, 0.1);
        padding: 8px;
        border-radius: 10px;
    }
    
    /* Ajuste de filtros para ocupar menos espacio vertical */
    .stMultiSelect [data-baseweb="tag"] { background-color: #001f3f !important; }
    </style>
    """, unsafe_allow_html=True)

# --- CARGA DE DATOS ---
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
    except: return None, None

# --- APP PRINCIPAL ---
st.title("Mapa de Promociones")

col_mapa, col_stats = st.columns([3, 1])

with st.sidebar:
    st.header("📂 Gestión")
    uploaded_file = st.file_uploader("Subir Excel", type=['xlsx'])
    show_labels = st.toggle("Etiquetas de Datos", value=True)
    if st.button("🔄 Resetear"): st.rerun()
    st.divider()

if uploaded_file:
    df_raw, cols = load_data(uploaded_file)
    
    if df_raw is not None:
        with st.sidebar:
            st.header("🔍 Filtros")
            
            # Filtros con multiselect directo dentro de expansores
            with st.expander("📍 Ciudad / Zona", expanded=False):
                c_opts = sorted(df_raw[cols['ciudad']].unique().astype(str)) if cols['ciudad'] else []
                sel_c = st.multiselect("Municipios", c_opts, default=c_opts, label_visibility="collapsed")
            
            with st.expander("💎 Tier", expanded=False):
                t_opts = sorted(df_raw[cols['tier']].unique().astype(str)) if cols['tier'] else []
                sel_t = st.multiselect("Tier", t_opts, default=t_opts, label_visibility="collapsed")

            with st.expander("🏢 Planta", expanded=False):
                p_opts = sorted(df_raw[cols['planta']].unique().astype(str)) if cols['planta'] else []
                sel_p = st.multiselect("Plantas", p_opts, default=p_opts, label_visibility="collapsed")

            # Aplicar filtros
            df_filtered = df_raw.copy()
            if cols['ciudad']: df_filtered = df_filtered[df_filtered[cols['ciudad']].astype(str).isin(sel_c)]
            if cols['tier']: df_filtered = df_filtered[df_filtered[cols['tier']].astype(str).isin(sel_t)]
            if cols['planta']: df_filtered = df_filtered[df_filtered[cols['planta']].astype(str).isin(sel_p)]

        with col_stats:
            st.subheader("📊 Estadísticas")
            if not df_filtered.empty:
                st.metric("Promociones", len(df_filtered[cols['ref']].unique()))
                st.metric("Unidades", len(df_filtered))
                if cols['pvp']:
                    st.metric("PVP Medio", f"€{df_filtered[cols['pvp']].mean():,.0f}")
            else: st.info("Filtra para ver datos")

        with col_mapa:
            # Centro y Zoom Automático
            if not df_filtered.empty:
                m = folium.Map(tiles=None)
                # Fit bounds: ajusta el mapa para ver todos los puntos filtrados
                sw = df_filtered[['lat', 'lon']].min().values.tolist()
                ne = df_filtered[['lat', 'lon']].max().values.tolist()
                m.fit_bounds([sw, ne])
            else:
                m = folium.Map(location=[41.6, 2.2], zoom_start=8, tiles=None)

            # Capas y Límites
            folium.TileLayer('OpenStreetMap', name='Callejero').add_to(m)
            sat = folium.FeatureGroup(name="Satélite con Límites")
            folium.TileLayer(
                tiles='https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
                attr='Esri', name='Satélite'
            ).add_to(sat)
            folium.TileLayer(
                tiles='https://server.arcgisonline.com/ArcGIS/rest/services/Reference/World_Boundaries_and_Places/MapServer/tile/{z}/{y}/{x}',
                attr='Esri', name='Límites y Calles', overlay=True
            ).add_to(sat)
            sat.add_to(m)

            if not df_filtered.empty:
                for i, (name, group) in enumerate(df_filtered.groupby(cols['ref']), 1):
                    row = group.iloc[0]
                    
                    # Marcador Punto
                    folium.Marker(
                        location=[row['lat'], row['lon']],
                        icon=folium.DivIcon(html=f"""
                            <div style="background:#001f3f;color:white;border-radius:50%;width:20px;height:20px;
                            display:flex;justify-content:center;align-items:center;font-weight:bold;border:1px solid white;
                            font-size:9px;">{i}</div>""")
                    ).add_to(m)

                    # Etiqueta Horizontal Semitransparente
                    if show_labels:
                        folium.Marker(
                            location=[row['lat'], row['lon']],
                            icon=folium.DivIcon(
                                html=f'<div class="promo-label"><b>#{i}</b> <span>{name}</span></div>',
                                icon_anchor=(-12, 10) # Desplazamiento lateral
                            )
                        ).add_to(m)

            Fullscreen().add_to(m)
            folium.LayerControl(position='topright').add_to(m)
            
            # Key dinámica para evitar recargas completas innecesarias al mover el mapa
            st_folium(m, width="100%", height=780, key="mapa_v15")
