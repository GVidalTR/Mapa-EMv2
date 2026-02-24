import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
import json

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Estudio de Mercado Pro", layout="wide", initial_sidebar_state="collapsed")

# --- ESTILOS CSS TEMA OSCURO ---
CSS = """
<style>
header[data-testid="stHeader"] { display: none !important; }
.block-container { padding-top: 1rem !important; padding-bottom: 1rem !important; max-width: 98% !important; }
[data-testid="stAppViewContainer"] { background-color: #121212 !important; }
p, h1, h2, h3, h4, h5, h6, label, span, div { color: #e0e0e0; font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif; }

/* Header Profesional Oscuro */
.app-header {
    background-color: #1e1e1e; padding: 15px 25px; 
    border-bottom: 3px solid #3a86ff; border-radius: 8px;
    margin-bottom: 20px; display: flex; justify-content: space-between; align-items: center;
    box-shadow: 0 4px 12px rgba(0,0,0,0.3);
}
.app-title { font-size: 22px !important; font-weight: 800 !important; margin: 0 !important; color: #ffffff !important; letter-spacing: 0.5px; }

/* Tarjetas de Promoción */
.promo-card {
    background-color: #252525; border: 1px solid #3a3a3a; border-radius: 8px;
    padding: 12px; margin-bottom: 10px; transition: all 0.2s ease-in-out;
}
.promo-card:hover { border-color: #3a86ff; transform: translateY(-2px); box-shadow: 0 4px 8px rgba(58, 134, 255, 0.2); }
.promo-header { display: flex; align-items: center; gap: 10px; margin-bottom: 8px; }
.promo-circle {
    background: linear-gradient(135deg, #3a86ff, #0056b3); color: white; border-radius: 50%;
    width: 26px; height: 26px; display: flex; justify-content: center;
    align-items: center; font-size: 12px; font-weight: bold; flex-shrink: 0;
    box-shadow: 0 2px 4px rgba(0,0,0,0.4); border: 1px solid rgba(255,255,255,0.2);
}
.promo-name { font-weight: 700 !important; color: #ffffff !important; font-size: 13px !important; margin: 0 !important; }
.promo-details { font-size: 11px !important; color: #b0b0b0 !important; line-height: 1.6 !important; }
.promo-details b { color: #ffffff !important; font-weight: 600; }

/* ETIQUETAS DEL MAPA MEJORADAS (Visibles sobre cualquier fondo) */
.map-label-container {
    background-color: #ffffff !important;
    border: 2px solid #3a86ff !important;
    border-radius: 6px !important;
    padding: 4px 8px !important;
    box-shadow: 0 4px 10px rgba(0,0,0,0.4) !important;
    white-space: nowrap !important;
    font-family: 'Helvetica Neue', Arial, sans-serif !important;
    display: flex;
    flex-direction: column;
    align-items: flex-start;
}
.map-label-price {
    font-size: 12px !important;
    font-weight: 800 !important;
    color: #121212 !important; /* Texto oscuro para contraste */
}
.map-label-unit {
    font-size: 9px !important;
    font-weight: 600 !important;
    color: #555555 !important;
    margin-top: -2px;
}

/* Ajustes de Filtros Streamlit */
div[data-baseweb="select"] > div { background-color: #252525 !important; border-color: #3a3a3a !important; color: white !important;}
div[data-baseweb="tag"] { background-color: #3a86ff !important; color: white !important; border: none; }
.stMultiSelect label { color: #e0e0e0 !important; font-weight: 600; font-size: 12px; }
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)

# --- HEADER VISUAL ---
st.markdown('<div class="app-header"><p class="app-title">ESTUDIO DE MERCADO PRO</p><p style="font-size:12px; color:#b0b0b0; margin:0; font-weight: 500;">Análisis de Entorno & Pricing</p></div>', unsafe_allow_html=True)

# --- ESTILO DE MAPA GOOGLE SIN COMERCIOS ---
# JSON de estilo para ocultar puntos de interés comerciales y rotular transporte
google_map_style = [
    {"featureType": "poi", "elementType": "labels", "stylers": [{"visibility": "off"}]},
    {"featureType": "poi.business", "stylers": [{"visibility": "off"}]},
    {"featureType": "poi.attraction", "stylers": [{"visibility": "off"}]},
    {"featureType": "poi.medical", "stylers": [{"visibility": "off"}]},
    {"featureType": "poi.school", "stylers": [{"visibility": "off"}]},
    {"featureType": "transit.station", "elementType": "labels.icon", "stylers": [{"visibility": "on"}]},
    {"featureType": "road.highway", "elementType": "geometry", "stylers": [{"color": "#ffffff"}]},
    {"featureType": "road.arterial", "elementType": "geometry", "stylers": [{"color": "#ffffff"}]},
]
encoded_style = requests.utils.quote(json.dumps(google_map_style)) if 'requests' in locals() else ""
# Nota: Para codificar la URL del estilo se necesita 'requests'. 
# Como alternativa simple, usaremos una cadena pre-codificada para un estilo limpio común.
# Esta es una cadena de estilo de Google Maps que oculta POIs.
STYLE_STRING = "s.e%3Al%7Cp.v%3Aoff%2Cs.t%3A3%7Cs.e%3Ag%7Cp.c%3A%23ffffff%2Cs.t%3A2%7Cs.e%3Ag%7Cp.c%3A%23ffffff"


# --- LÓGICA DE DATOS ---
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
        if c['coord']:
            coords = df[c['coord']].astype(str).str.replace(' ', '').str.split(',', expand=True)
            df['lat'] = pd.to_numeric(coords[0], errors='coerce')
            df['lon'] = pd.to_numeric(coords[1], errors='coerce')
            return df.dropna(subset=['lat', 'lon']), c
        return pd.DataFrame(), {}
    except Exception as e: 
        st.error(f"Error al procesar: {e}")
        return pd.DataFrame(), {}

# --- LAYOUT DE COLUMNAS ---
col_izq, col_mapa, col_der, col_ctrl = st.columns([1, 3.5, 1, 1.1])

df_final = pd.DataFrame()
ALTURA_CONTENEDOR = 800 

# --- PANEL DERECHO (CONTROL) ---
with col_ctrl:
    with st.container(height=ALTURA_CONTENEDOR, border=False):
        st.markdown("##### 📂 FUENTE DE DATOS")
        file = st.file_uploader("Subir Excel", type=['xlsx'], label_visibility="collapsed")
        
        if file:
            df_raw, cols = load_data(file)
            if not df_raw.empty:
                st.markdown("---")
                st.markdown("##### 🔍 FILTROS DE ESTUDIO")
                
                def mk_filter(lbl, col_name):
                    if col_name and col_name in df_raw.columns:
                        opts = sorted(df_raw[col_name].dropna().unique().astype(str))
                        return st.multiselect(lbl, opts, default=opts)
                    return []
                
                f_tipo = mk_filter("Tipología", cols['tipo'])
                f_tier = mk_filter("Tier", cols['tier'])
                f_zona = mk_filter("Zona", cols['zona'])
                f_ciudad = mk_filter("Ciudad", cols['ciudad'])
                f_planta = mk_filter("Planta", cols['planta'])
                f_dorm = mk_filter("Dormitorios", cols['dorm'])

                mask = pd.Series(True, index=df_raw.index)
                if cols['tipo']: mask &= df_raw[cols['tipo']].astype(str).isin(f_tipo)
                if cols['tier']: mask &= df_raw[cols['tier']].astype(str).isin(f_tier)
                if cols['zona']: mask &= df_raw[cols['zona']].astype(str).isin(f_zona)
                if cols['ciudad']: mask &= df_raw[cols['ciudad']].astype(str).isin(f_ciudad)
                if cols['planta']: mask &= df_raw[cols['planta']].astype(str).isin(f_planta)
                if cols['dorm']: mask &= df_raw[cols['dorm']].astype(str).isin(f_dorm)
                
                df_final = df_raw[mask]
                
                if not df_final.empty:
                    agg_rules = {
                        'lat':'first', 'lon':'first', 
                        cols['vrm']:'median' if cols['vrm'] in df_final.columns else 'first',
                        cols['pvp']:'mean' if cols['pvp'] in df_final.columns else 'first', 
                        cols['ref']:'count'
                    }
                    if cols['dorm']: agg_rules[cols['dorm']] = lambda x: "-".join(sorted(x.unique().astype(str)))
                    
                    df_promo = df_final.groupby(cols['ref']).agg(agg_rules).rename(columns={cols['ref']: 'UDS'}).reset_index()

# --- VISTA CENTRAL Y LATERALES ---
if file and not df_final.empty:
    
    def render_promo_cards(data, start_idx):
        for i, row in data.iterrows():
            st.markdown(f"""
            <div class="promo-card">
                <div class="promo-header"><div class="promo-circle">{start_idx+i+1}</div><p class="promo-name">{row[cols['ref']]}</p></div>
                <div class="promo-details">
                    Uds: <b>{row['UDS']}</b> | PVP med: <b>{row.get(cols['pvp'], 0):,.0f}€</b><br>
                    Unitario: <b>{row.get(cols['vrm'], 0):,.0f} €/m²</b><br>
                    Tipologías: {row.get(cols['dorm'], 'N/A')}D
                </div>
            </div>""", unsafe_allow_html=True)

    mid = len(df_promo) // 2
    with col_izq:
        with st.container(height=ALTURA_CONTENEDOR, border=False):
            render_promo_cards(df_promo.iloc[:mid], 0)

    with col_der:
        with st.container(height=ALTURA_CONTENEDOR, border=False):
            render_promo_cards(df_promo.iloc[mid:], mid)

    # Generar Mapa (Con Estilos Limpios de Google)
    with col_mapa:
        m = folium.Map(tiles=None, control_scale=True)
        
        # Capa Híbrida Limpia (Satélite + Calles sin comercios)
        # Usamos 'lyrs=y' para híbrido y aplicamos el estilo para ocultar POIs
        folium.TileLayer(
            tiles=f"https://mt1.google.com/vt/lyrs=y&x={{x}}&y={{y}}&z={{z}}&apistyle={STYLE_STRING}",
            attr="Google",
            name="Satélite Limpio",
            overlay=False,
            control=True
        ).add_to(m)

        # Capa Callejero Limpio (Solo carreteras y transporte)
        # Usamos 'lyrs=m' para mapa estándar y aplicamos el estilo
        folium.TileLayer(
            tiles=f"https://mt1.google.com/vt/lyrs=m&x={{x}}&y={{y}}&z={{z}}&apistyle={STYLE_STRING}",
            attr="Google",
            name="Callejero Limpio",
            overlay=False,
            control=True
        ).add_to(m)

        sw, ne = df_promo[['lat', 'lon']].min().values.tolist(), df_promo[['lat', 'lon']].max().values.tolist()
        m.fit_bounds([sw, ne])
        
        for i, row in df_promo.iterrows():
            # Marcador circular numerado (Más vibrante)
            folium.Marker([row['lat'], row['lon']], 
                icon=folium.DivIcon(html=f'<div class="promo-circle">{i+1}</div>'),
                z_index_offset=1000 # Asegura que el círculo esté sobre la etiqueta
            ).add_to(m)
            
            # Etiqueta de Precio Unitario (Recuadro blanco con texto oscuro)
            val_vrm = row.get(cols['vrm'], 0)
            label_html = f"""
            <div class="map-label-container">
                <span class="map-label-price">{val_vrm:,.0f} €/m²</span>
                <span class="map-label-unit">Precio Unitario</span>
            </div>
            """
            folium.Marker([row['lat'], row['lon']], 
                icon=folium.DivIcon(html=label_html, icon_anchor=(-18, 20)), # Posición ajustada
                z_index_offset=900
            ).add_to(m)

        folium.LayerControl(position='topright').add_to(m)
        st_folium(m, width="100%", height=ALTURA_CONTENEDOR, key="main_map")

else:
    # --- PANTALLA DE INICIO OSCURA ---
    with col_mapa:
        st.markdown("""
        <div style="background-color: #1e1e1e; padding: 60px 40px; border-radius: 12px; text-align: center; border-top: 4px solid #3a86ff; margin-top: 80px; box-shadow: 0 10px 30px rgba(0,0,0,0.5);">
            <h1 style="color: #ffffff; font-weight: 800; letter-spacing: -0.5px; margin-bottom: 10px;">ESTUDIO DE MERCADO PRO</h1>
            <h4 style="color: #a0a0a0; font-weight: 300; margin-bottom: 40px;">Plataforma de Inteligencia Inmobiliaria</h4>
            <div style="background-color: #252525; padding: 25px; border-radius: 8px; text-align: left; display: inline-block; width: 100%; max-width: 500px; border: 1px solid #3a3a3a;">
                <h4 style="color: #ffffff; font-size: 16px; margin-top: 0; margin-bottom: 15px;">Instrucciones de Inicio:</h4>
                <ol style="color: #e0e0e0; font-size: 14px; line-height: 1.8; margin-bottom: 0; padding-left: 20px;">
                    <li>Carga tu archivo Excel en el panel lateral derecho.</li>
                    <li>El sistema procesará la pestaña <b>EEMM</b> automáticamente.</li>
                    <li>Se requieren las columnas clave: COORD, REF, PVP y VRM SCIC.</li>
                    <li>Utiliza los filtros para segmentar el mercado en tiempo real.</li>
                </ol>
            </div>
        </div>
        """, unsafe_allow_html=True)
