import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
import googlemaps
from folium.plugins import Fullscreen

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="PropTech Analytics Pro", layout="wide", initial_sidebar_state="expanded")

# CSS para reducir márgenes superiores y dar estilo a las tarjetas
st.markdown("""
    <style>
    .block-container { padding-top: 1rem; padding-bottom: 0rem; }
    .side-scroll { height: 700px; overflow-y: auto; padding-right: 10px; }
    .promo-card {
        background-color: #e3f2fd;
        border: 1px solid #bbdefb;
        border-radius: 10px;
        padding: 12px;
        margin-bottom: 10px;
        font-family: sans-serif;
    }
    .promo-header { display: flex; align-items: center; gap: 10px; margin-bottom: 8px; }
    .promo-number {
        background-color: #0d47a1; color: white; border-radius: 50%;
        width: 24px; height: 24px; display: flex; justify-content: center;
        align-items: center; font-size: 12px; font-weight: bold;
    }
    .promo-title { font-weight: bold; color: #1a237e; font-size: 14px; margin: 0; }
    .promo-info { font-size: 12px; line-height: 1.4; color: #333; }
    .promo-label-map {
        background: white; border: 1.5px solid #0d47a1; border-radius: 4px;
        padding: 2px 6px; font-size: 11px; font-weight: bold; color: #0d47a1;
        white-space: nowrap; box-shadow: 2px 2px 5px rgba(0,0,0,0.1);
    }
    </style>
    """, unsafe_allow_html=True)

# Carga de API Key
try:
    API_KEY = st.secrets["GOOGLE_MAPS_API_KEY"]
    gmaps = googlemaps.Client(key=API_KEY)
except:
    st.error("⚠️ Configura 'GOOGLE_MAPS_API_KEY' en Secrets.")
    st.stop()

@st.cache_data
def load_data(file):
    try:
        xls = pd.ExcelFile(file)
        df = pd.read_excel(xls, sheet_name='EEMM')
        df.columns = [str(c).strip().upper() for c in df.columns]
        
        # Mapeo de columnas necesarias
        cols = {
            'coord': next((c for c in df.columns if 'COORD' in c), None),
            'ref': next((c for c in df.columns if any(k in c for k in ['REF', 'PROMOCION', 'NOMBRE'])), None),
            'vrm': 'VRM SCIC',
            'pvp': 'PVP',
            'tipo': next((c for c in df.columns if 'TIPOLOGI' in c), None),
            'tier': 'TIER',
            'zona': 'ZONA',
            'ciudad': next((c for c in df.columns if any(k in c for k in ['CIUDAD', 'MUNICIPIO'])), None),
            'planta': 'PLANTA',
            'dorm': 'Nº DORM'
        }

        if cols['coord']:
            coords = df[cols['coord']].astype(str).str.replace(' ', '').str.split(',', expand=True)
            df['lat'] = pd.to_numeric(coords[0], errors='coerce')
            df['lon'] = pd.to_numeric(coords[1], errors='coerce')
            df = df.dropna(subset=['lat', 'lon'])
        return df, cols
    except Exception as e:
        st.error(f"Error al cargar el archivo: {e}")
        return pd.DataFrame(), {}

# --- LÓGICA DE APP ---
archivo = st.sidebar.file_uploader("Subir Excel", type=['xlsx'])

if archivo:
    df_raw, c_map = load_data(archivo)
    
    if not df_raw.empty:
        # --- SIDEBAR: FILTROS ---
        st.sidebar.header("🔍 Filtros")
        show_boxes = st.sidebar.toggle("Mostrar Cuadros de Datos", value=True)
        
        def get_opts(col): return sorted(df_raw[col].dropna().unique().astype(str)) if col in df_raw.columns else []

        f_tipo = st.sidebar.multiselect("Tipología", get_opts(c_map['tipo']), default=get_opts(c_map['tipo']))
        f_tier = st.sidebar.multiselect("Tier", get_opts(c_map['tier']), default=get_opts(c_map['tier']))
        f_ciudad = st.sidebar.multiselect("Ciudad", get_opts(c_map['ciudad']), default=get_opts(c_map['ciudad']))
        f_zona = st.sidebar.multiselect("Zona", get_opts(c_map['zona']), default=get_opts(c_map['zona']))
        f_dorm = st.sidebar.multiselect("Dormitorios", get_opts(c_map['dorm']), default=get_opts(c_map['dorm']))

        # Aplicar Filtros
        df_f = df_raw.copy()
        if c_map['tipo']: df_f = df_f[df_f[c_map['tipo']].astype(str).isin(f_tipo)]
        if c_map['tier']: df_f = df_f[df_f[c_map['tier']].astype(str).isin(f_tier)]
        if c_map['ciudad']: df_f = df_f[df_f[c_map['ciudad']].astype(str).isin(f_ciudad)]
        if c_map['zona']: df_f = df_f[df_f[c_map['zona']].astype(str).isin(f_zona)]
        if c_map['dorm']: df_f = df_f[df_f[c_map['dorm']].astype(str).isin(f_dorm)]

        # Agrupación por Promoción para el Resumen
        agg_dict = {
            'lat': 'first', 'lon': 'first',
            c_map['vrm']: 'median',
            c_map['pvp']: 'mean',
            c_map['ref']: 'count' # Para contar unidades
        }
        if c_map['dorm']: agg_dict[c_map['dorm']] = lambda x: "-".join(sorted(x.unique().astype(str)))
        
        df_promo = df_f.groupby(c_map['ref']).agg(agg_dict).rename(columns={c_map['ref']: 'UNIDADES'}).reset_index()

        # --- LAYOUT ---
        st.subheader("Market Study: Análisis de Entorno")
        col_izq, col_mapa, col_der = st.columns([1, 2.5, 1])

        def render_cards(subset, start_idx):
            for i, row in subset.iterrows():
                num = start_idx + i + 1
                st.markdown(f"""
                <div class="promo-card">
                    <div class="promo-header">
                        <div class="promo-number">{num}</div>
                        <p class="promo-title">{row[c_map['ref']]}</p>
                    </div>
                    <div class="promo-info">
                        <b>Unidades:</b> {row['UNIDADES']}<br>
                        <b>PVP medio:</b> {row[c_map['pvp']]:,.0f} €<br>
                        <b>Precio unit.:</b> {row[c_map['vrm']]:,.0f} €/m²<br>
                        <b>Tipologías:</b> {row.get(c_map['dorm'], 'N/A')}D
                    </div>
                </div>
                """, unsafe_allow_html=True)

        # Distribución de datos
        split = len(df_promo) // 2
        
        with col_izq:
            if show_boxes:
                st.markdown('<div class="side-scroll">', unsafe_allow_html=True)
                render_cards(df_promo.iloc[:split], 0)
                st.markdown('</div>', unsafe_allow_html=True)

        with col_mapa:
            m = folium.Map(tiles=None)
            # Encuadre automático (fit_bounds)
            sw = df_promo[['lat', 'lon']].min().values.tolist()
            ne = df_promo[['lat', 'lon']].max().values.tolist()
            m.fit_bounds([sw, ne])

            folium.TileLayer("https://mt1.google.com/vt/lyrs=y&x={x}&y={y}&z={z}",
                             attr="Google Hybrid", name="Google Satélite").add_to(m)

            for i, row in df_promo.iterrows():
                # Etiqueta de Precio Unitario (VRM)
                vrm_txt = f"{row[c_map['vrm']]:,.0f} €/m²"
                
                # Número azul
                folium.Marker([row['lat'], row['lon']],
                    icon=folium.DivIcon(html=f'<div class="promo-number" style="width:20px; height:20px; font-size:10px;">{i+1}</div>')
                ).add_to(m)
                
                # Recuadro blanco con precio (ahora con ancho dinámico corregido)
                folium.Marker([row['lat'], row['lon']],
                    icon=folium.DivIcon(html=f'<div class="promo-label-map">{vrm_txt}</div>', icon_anchor=(-12, 12))
                ).add_to(m)

            st_folium(m, width="100%", height=700, key="mapa_final")

        with col_der:
            if show_boxes:
                st.markdown('<div class="side-scroll">', unsafe_allow_html=True)
                render_cards(df_promo.iloc[split:], split)
                st.markdown('</div>', unsafe_allow_html=True)
