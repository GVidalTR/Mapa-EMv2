import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
import googlemaps
from folium.plugins import Fullscreen

# --- CONFIGURACIÓN DE PÁGINA (ESTRICTO SIN SCROLL) ---
st.set_page_config(page_title="PropTech Analytics", layout="wide", initial_sidebar_state="collapsed")

st.markdown("""
    <style>
    /* Reset total de márgenes */
    [data-testid="stHeader"], .block-container { padding: 0rem !important; }
    html, body, [data-testid="stAppViewContainer"] { 
        overflow: hidden; height: 100vh; background-color: #ffffff; 
    }
    
    /* Contenedores laterales con altura fija y scroll */
    .column-scroll { 
        height: 98vh; overflow-y: auto; padding: 10px; border-right: 1px solid #eee;
    }
    
    /* Cuadros de datos comprimidos (Estilo imagen) */
    .promo-card {
        background-color: #eef6ff; border: 1.5px solid #d1e3f8; border-radius: 8px;
        padding: 8px; margin-bottom: 8px; font-family: 'Helvetica', sans-serif;
    }
    .promo-header { display: flex; align-items: center; gap: 8px; margin-bottom: 4px; }
    .promo-number {
        background-color: #003366; color: white; border-radius: 50%;
        width: 20px; height: 20px; display: flex; justify-content: center;
        align-items: center; font-size: 11px; font-weight: bold; flex-shrink: 0;
    }
    .promo-title { font-weight: 700; color: #003366; font-size: 12px; margin: 0; line-height: 1.1; }
    .promo-info { font-size: 11px; line-height: 1.3; color: #444; }
    
    /* Etiquetas del mapa (Recuadro Blanco) */
    .map-label {
        background: white !important; border: 2px solid #003366 !important; border-radius: 4px !important;
        padding: 2px 6px !important; font-size: 11px !important; font-weight: bold !important; 
        color: #003366 !important; white-space: nowrap !important; 
        box-shadow: 2px 2px 6px rgba(0,0,0,0.3) !important;
        display: block !important;
    }

    /* Filtros comprimidos columna derecha */
    .filter-section { font-size: 11px !important; margin-top: 15px; }
    .stMultiSelect div { min-height: 28px !important; }
    .stMultiSelect span { font-size: 10px !important; }
    div[data-baseweb="select"] { font-size: 11px !important; }
    </style>
    """, unsafe_allow_html=True)

# --- CARGA DE DATOS ---
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
        coords = df[c['coord']].astype(str).str.replace(' ', '').str.split(',', expand=True)
        df['lat'] = pd.to_numeric(coords[0], errors='coerce')
        df['lon'] = pd.to_numeric(coords[1], errors='coerce')
        return df.dropna(subset=['lat', 'lon']), c
    except: return pd.DataFrame(), {}

# --- ESTRUCTURA DE 4 COLUMNAS ---
c_izq, c_mapa, c_der, c_filtros = st.columns([1, 3.2, 1, 0.9])

# Inicialización de variables
df_f = pd.DataFrame()
map_center = [41.6, 1.8] # Centro Cataluña
map_zoom = 8

# COLUMNA 4: CARGA Y FILTROS (DERECHA)
with c_filtros:
    st.markdown('<div class="column-scroll">', unsafe_allow_html=True)
    archivo = st.file_uploader("📂 CARGAR EXCEL", type=['xlsx'], label_visibility="visible")
    
    if archivo:
        df_raw, cols = load_data(archivo)
        if not df_raw.empty:
            st.markdown('<p class="filter-section"><b>FILTROS DE BÚSQUEDA</b></p>', unsafe_allow_html=True)
            def simple_filter(label, col):
                return st.multiselect(label, sorted(df_raw[col].dropna().unique().astype(str)), 
                                    default=sorted(df_raw[col].dropna().unique().astype(str)))
            
            f_tipo = simple_filter("Tipología", cols['tipo'])
            f_tier = simple_filter("Tier", cols['tier'])
            f_ciudad = simple_filter("Ciudad", cols['ciudad'])
            f_zona = simple_filter("Zona", cols['zona'])
            f_dorm = simple_filter("Dormitorios", cols['dorm'])

            # Lógica de filtrado
            mask = (df_raw[cols['tipo']].astype(str).isin(f_tipo)) & \
                   (df_raw[cols['tier']].astype(str).isin(f_tier)) & \
                   (df_raw[cols['ciudad']].astype(str).isin(f_ciudad)) & \
                   (df_raw[cols['zona']].astype(str).isin(f_zona)) & \
                   (df_raw[cols['dorm']].astype(str).isin(f_dorm))
            df_f = df_raw[mask]

            if not df_f.empty:
                df_promo = df_f.groupby(cols['ref']).agg({
                    'lat':'first', 'lon':'first', cols['vrm']:'median', cols['pvp']:'mean', 
                    cols['ref']:'count', cols['dorm']: lambda x: "-".join(sorted(x.unique().astype(str)))
                }).rename(columns={cols['ref']: 'UNIDADES'}).reset_index()
                map_center = [df_promo['lat'].mean(), df_promo['lon'].mean()]
                map_zoom = 13
    st.markdown('</div>', unsafe_allow_html=True)

# COLUMNAS 1 Y 3: CUADROS PERIMETRALES
if archivo and not df_f.empty:
    split = len(df_promo) // 2
    def draw_cards(subset, start):
        for i, row in subset.iterrows():
            st.markdown(f"""
            <div class="promo-card">
                <div class="promo-header"><div class="promo-number">{start+i+1}</div><p class="promo-title">{row[cols['ref']]}</p></div>
                <div class="promo-info">
                    <b>Uds:</b> {row['UNIDADES']} | <b>PVP m:</b> {row[cols['pvp']]:,.0f}€<br>
                    <b>Unit:</b> {row[cols['vrm']]:,.0f} €/m² | <b>Tip:</b> {row[cols['dorm']]}D
                </div>
            </div>""", unsafe_allow_html=True)

    with c_izq:
        st.markdown('<div class="column-scroll">', unsafe_allow_html=True)
        draw_cards(df_promo.iloc[:split], 0)
        st.markdown('</div>', unsafe_allow_html=True)

    with c_der:
        st.markdown('<div class="column-scroll">', unsafe_allow_html=True)
        draw_cards(df_promo.iloc[split:], split)
        st.markdown('</div>', unsafe_allow_html=True)

# COLUMNA 2: EL MAPA (SIEMPRE VISIBLE)
with c_mapa:
    m = folium.Map(location=map_center, zoom_start=map_zoom, tiles=None, control_scale=True)
    
    # Capas de Google (lyrs=m es el callejero más limpio)
    folium.TileLayer("https://mt1.google.com/vt/lyrs=y&x={x}&y={y}&z={z}", attr="Google", name="Satélite Híbrido").add_to(m)
    folium.TileLayer("https://mt1.google.com/vt/lyrs=m&x={x}&y={y}&z={z}", attr="Google", name="Callejero Profesional").add_to(m)

    if archivo and not df_f.empty:
        sw, ne = df_promo[['lat', 'lon']].min().values.tolist(), df_promo[['lat', 'lon']].max().values.tolist()
        m.fit_bounds([sw, ne])
        
        for i, row in df_promo.iterrows():
            # El puntero/número azul
            folium.Marker([row['lat'], row['lon']], 
                icon=folium.DivIcon(html=f'<div class="promo-number" style="width:22px; height:22px;">{i+1}</div>')
            ).add_to(m)
            # La etiqueta con fondo blanco y borde
            folium.Marker([row['lat'], row['lon']], 
                icon=folium.DivIcon(html=f'<div class="map-label">{row[cols['vrm']]:,.0f} €/m²</div>', icon_anchor=(-15, 12))
            ).add_to(m)

    folium.LayerControl(position='topright').add_to(m)
    st_folium(m, width="100%", height=950, key="main_map")
