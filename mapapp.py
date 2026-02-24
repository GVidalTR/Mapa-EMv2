import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
import googlemaps
from folium.plugins import Fullscreen

# --- CONFIGURACIÓN DE PÁGINA (SIN MARGENES Y SIN SCROLL) ---
st.set_page_config(page_title="Analytics Pro", layout="wide", initial_sidebar_state="collapsed")

st.markdown("""
    <style>
    /* Eliminar cabeceras y márgenes superiores */
    [data-testid="stHeader"], .block-container { padding-top: 0rem !important; padding-bottom: 0rem !important; }
    html, body, [data-testid="stAppViewContainer"] { overflow: hidden; height: 100vh; background-color: #f0f2f6; }
    
    /* Contenedores con scroll interno para evitar scroll global */
    .column-scroll { height: 92vh; overflow-y: auto; padding: 5px; }
    
    /* Cuadros perimetrales pequeños */
    .promo-card {
        background-color: #e3f2fd; border: 1px solid #bbdefb; border-radius: 6px;
        padding: 6px; margin-bottom: 6px; font-family: 'Segoe UI', sans-serif;
    }
    .promo-header { display: flex; align-items: center; gap: 6px; margin-bottom: 2px; }
    .promo-number {
        background-color: #0d47a1; color: white; border-radius: 50%;
        width: 18px; height: 18px; display: flex; justify-content: center;
        align-items: center; font-size: 10px; font-weight: bold;
    }
    .promo-title { font-weight: bold; color: #1a237e; font-size: 11px; margin: 0; }
    .promo-info { font-size: 10px; line-height: 1.2; color: #333; }
    
    /* Etiquetas del mapa */
    .map-label {
        background: white; border: 1px solid #0d47a1; border-radius: 3px;
        padding: 1px 4px; font-size: 10px; font-weight: bold; color: #0d47a1;
        white-space: nowrap; box-shadow: 1px 1px 3px rgba(0,0,0,0.2);
    }
    
    /* Filtros comprimidos a la derecha */
    .filter-container { font-size: 10px !important; }
    .stMultiSelect div { min-height: 25px !important; }
    .stMultiSelect span { font-size: 10px !important; }
    </style>
    """, unsafe_allow_html=True)

# Carga segura de API Key
try:
    API_KEY = st.secrets["GOOGLE_MAPS_API_KEY"]
    gmaps = googlemaps.Client(key=API_KEY)
except:
    st.error("Configura API Key en Secrets.")
    st.stop()

@st.cache_data
def load_data(file):
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

# --- LÓGICA PRINCIPAL ---
c_izq, c_mapa, c_der, c_filtros = st.columns([1, 2.8, 1, 0.8])

# Columna de carga y Filtros (Derecha)
with c_filtros:
    st.markdown('<div class="column-scroll">', unsafe_allow_html=True)
    archivo = st.file_uploader("Excel", type=['xlsx'], label_visibility="collapsed")
    if archivo:
        df_raw, cols = load_data(archivo)
        
        st.caption("FILTROS")
        def multi(label, col): return st.multiselect(label, sorted(df_raw[col].dropna().unique().astype(str)), default=sorted(df_raw[col].dropna().unique().astype(str)))
        
        f_tipo = multi("Tipología", cols['tipo'])
        f_tier = multi("Tier", cols['tier'])
        f_ciudad = multi("Ciudad", cols['ciudad'])
        f_zona = multi("Zona", cols['zona'])
        f_dorm = multi("Dormitorios", cols['dorm'])

        # Filtrado
        df_f = df_raw[ (df_raw[cols['tipo']].astype(str).isin(f_tipo)) & (df_raw[cols['tier']].astype(str).isin(f_tier)) & (df_raw[cols['ciudad']].astype(str).isin(f_ciudad)) & (df_raw[cols['zona']].astype(str).isin(f_zona)) & (df_raw[cols['dorm']].astype(str).isin(f_dorm)) ]
        
        df_promo = df_f.groupby(cols['ref']).agg({'lat':'first', 'lon':'first', cols['vrm']:'median', cols['pvp']:'mean', cols['ref']:'count', cols['dorm']: lambda x: "-".join(sorted(x.unique().astype(str)))}).rename(columns={cols['ref']: 'UNIDADES'}).reset_index()
    st.markdown('</div>', unsafe_allow_html=True)

if archivo and not df_f.empty:
    split = len(df_promo) // 2
    
    def render_cards(subset, start_idx):
        for i, row in subset.iterrows():
            st.markdown(f"""
            <div class="promo-card">
                <div class="promo-header"><div class="promo-number">{start_idx+i+1}</div><p class="promo-title">{row[cols['ref']]}</p></div>
                <div class="promo-info">
                    <b>Uds:</b> {row['UNIDADES']} | <b>PVP:</b> {row[cols['pvp']]:,.0f}€<br>
                    <b>Unit:</b> {row[cols['vrm']]:,.0f} €/m² | <b>Tip:</b> {row[cols['dorm']]}D
                </div>
            </div>
            """, unsafe_allow_html=True)

    with c_izq:
        st.markdown('<div class="column-scroll">', unsafe_allow_html=True)
        render_cards(df_promo.iloc[:split], 0)
        st.markdown('</div>', unsafe_allow_html=True)

    with c_mapa:
        m = folium.Map(tiles=None, control_scale=True)
        sw, ne = df_promo[['lat', 'lon']].min().values.tolist(), df_promo[['lat', 'lon']].max().values.tolist()
        m.fit_bounds([sw, ne])

        # CAPAS SELECTORAS
        folium.TileLayer("https://mt1.google.com/vt/lyrs=y&x={x}&y={y}&z={z}", attr="Google", name="Satélite Híbrido").add_to(m)
        folium.TileLayer("https://mt1.google.com/vt/lyrs=m&x={x}&y={y}&z={z}", attr="Google", name="Callejero Limpio").add_to(m)

        for i, row in df_promo.iterrows():
            # Punto con número
            folium.Marker([row['lat'], row['lon']], icon=folium.DivIcon(html=f'<div class="promo-number">{i+1}</div>')).add_to(m)
            # Etiqueta de precio
            folium.Marker([row['lat'], row['lon']], icon=folium.DivIcon(html=f'<div class="map-label">{row[cols['vrm']]:,.0f}€</div>', icon_anchor=(-10, 10))).add_to(m)

        folium.LayerControl(position='topright').add_to(m)
        st_folium(m, width="100%", height=800, key="mapa_v6")

    with c_der:
        st.markdown('<div class="column-scroll">', unsafe_allow_html=True)
        render_cards(df_promo.iloc[split:], split)
        st.markdown('</div>', unsafe_allow_html=True)
