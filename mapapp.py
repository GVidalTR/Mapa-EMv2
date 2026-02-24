import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Estudio de Mercado Pro", layout="wide", initial_sidebar_state="collapsed")

# --- ESTILOS CSS TEMA OSCURO (Para el Dashboard, no afecta al mapa) ---
st.markdown("""
<style>
header[data-testid="stHeader"] { display: none !important; }
.block-container { padding-top: 1rem !important; padding-bottom: 1rem !important; max-width: 98% !important; }
[data-testid="stAppViewContainer"] { background-color: #121212 !important; }
p, h1, h2, h3, h4, h5, h6, label, span { color: #e0e0e0 !important; font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif; }

.app-header {
    background-color: #1e1e1e; padding: 15px 25px; 
    border-bottom: 3px solid #3a86ff; border-radius: 8px;
    margin-bottom: 20px; display: flex; justify-content: space-between; align-items: center;
}
.app-title { font-size: 22px !important; font-weight: 800 !important; margin: 0 !important; color: #ffffff !important; }

.promo-card {
    background-color: #252525; border: 1px solid #3a3a3a; border-radius: 8px;
    padding: 12px; margin-bottom: 10px; transition: all 0.2s;
}
.promo-card:hover { border-color: #3a86ff; }
.promo-header { display: flex; align-items: center; gap: 10px; margin-bottom: 8px; }
.promo-circle-ui {
    background-color: #3a86ff; color: white; border-radius: 50%;
    width: 24px; height: 24px; display: flex; justify-content: center;
    align-items: center; font-size: 11px; font-weight: bold; flex-shrink: 0;
}
.promo-name { font-weight: 700 !important; color: #ffffff !important; font-size: 13px !important; margin: 0 !important; }
.promo-details { font-size: 11px !important; color: #b0b0b0 !important; line-height: 1.6 !important; }
.promo-details b { color: #ffffff !important; }

div[data-baseweb="select"] > div { background-color: #252525 !important; border-color: #3a3a3a !important; color: white !important;}
div[data-baseweb="tag"] { background-color: #3a86ff !important; color: white !important; border: none; }
.stMultiSelect label { font-size: 12px !important; font-weight: bold !important; color: #e0e0e0 !important;}
</style>
""", unsafe_allow_html=True)

# --- HEADER VISUAL ---
st.markdown('<div class="app-header"><p class="app-title">ESTUDIO DE MERCADO PRO</p><p style="font-size:12px; color:#b0b0b0; margin:0;">Análisis de Entorno & Pricing</p></div>', unsafe_allow_html=True)

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
        st.markdown("##### FUENTE DE DATOS")
        file = st.file_uploader("Subir Excel", type=['xlsx'], label_visibility="collapsed")
        
        if file:
            df_raw, cols = load_data(file)
            if not df_raw.empty:
                st.markdown("---")
                st.markdown("##### FILTROS DE ESTUDIO")
                
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
                <div class="promo-header"><div class="promo-circle-ui">{start_idx+i+1}</div><p class="promo-name">{row[cols['ref']]}</p></div>
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

    # Generar Mapa (Capas robustas de Google)
    with col_mapa:
        m = folium.Map(tiles=None, control_scale=True)
        
        # Capa Satélite Híbrido Estándar (Fiable)
        folium.TileLayer(
            tiles="https://mt1.google.com/vt/lyrs=y&x={x}&y={y}&z={z}",
            attr="Google",
            name="Satélite Híbrido",
            control=True
        ).add_to(m)

        # Capa Callejero Estándar (Fiable)
        folium.TileLayer(
            tiles="https://mt1.google.com/vt/lyrs=m&x={x}&y={y}&z={z}",
            attr="Google",
            name="Callejero",
            control=True
        ).add_to(m)

        sw, ne = df_promo[['lat', 'lon']].min().values.tolist(), df_promo[['lat', 'lon']].max().values.tolist()
        m.fit_bounds([sw, ne])
        
        for i, row in df_promo.iterrows():
            val_vrm = row.get(cols['vrm'], 0)
            
            # Marcador 1: El círculo azul con el número (Estilos en línea forzados)
            circle_html = f"""
            <div style="background-color: #3a86ff; color: white; border-radius: 50%; width: 24px; height: 24px; 
                        display: flex; justify-content: center; align-items: center; font-size: 11px; 
                        font-weight: bold; border: 2px solid white; box-shadow: 0 2px 5px rgba(0,0,0,0.5);
                        font-family: Arial, sans-serif;">
                {i+1}
            </div>
            """
            folium.Marker(
                [row['lat'], row['lon']], 
                icon=folium.DivIcon(html=circle_html, icon_anchor=(12, 12))
            ).add_to(m)
            
            # Marcador 2: La etiqueta de precio (Estilos en línea forzados)
            label_html = f"""
            <div style="background-color: white; border: 2px solid #3a86ff; border-radius: 4px; 
                        padding: 3px 6px; font-size: 11px; font-weight: bold; color: #121212; 
                        white-space: nowrap; box-shadow: 0 2px 6px rgba(0,0,0,0.4); 
                        font-family: Arial, sans-serif;">
                {val_vrm:,.0f} €/m²
            </div>
            """
            folium.Marker(
                [row['lat'], row['lon']], 
                icon=folium.DivIcon(html=label_html, icon_anchor=(-15, 12))
            ).add_to(m)

        folium.LayerControl(position='topright').add_to(m)
        st_folium(m, width="100%", height=ALTURA_CONTENEDOR, key="main_map")

else:
    # --- PANTALLA DE INICIO ---
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
