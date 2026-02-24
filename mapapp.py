import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
from folium.plugins import Fullscreen

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Generador Mapas EM", layout="wide", initial_sidebar_state="collapsed")

# --- ESTILOS CSS AVANZADOS ---
st.markdown("""
    <style>
    /* Reset total y fondo */
    [data-testid="stHeader"], .block-container { padding: 0 !important; }
    html, body, [data-testid="stAppViewContainer"] { 
        overflow: hidden; height: 100vh; background-color: #f4f7f9; 
    }
    
    /* Header Profesional */
    .app-header {
        background-color: #001f3f; padding: 12px 25px; color: white;
        display: flex; justify-content: space-between; align-items: center;
        box-shadow: 0 2px 5px rgba(0,0,0,0.2); height: 60px;
    }
    .app-title { font-size: 22px; font-weight: 800; letter-spacing: 1px; margin: 0; }

    /* Tarjetas de Promoción */
    .promo-card {
        background-color: #eef6ff; border: 1.5px solid #bbdefb; border-radius: 8px;
        padding: 10px; margin-bottom: 10px; transition: 0.3s;
    }
    .promo-card:hover { border-color: #0d47a1; box-shadow: 0 2px 8px rgba(0,0,0,0.1); }
    .promo-header { display: flex; align-items: center; gap: 8px; margin-bottom: 5px; }
    .promo-circle {
        background-color: #001f3f; color: white; border-radius: 50%;
        width: 22px; height: 22px; display: flex; justify-content: center;
        align-items: center; font-size: 11px; font-weight: bold; flex-shrink: 0;
    }
    .promo-name { font-weight: 700; color: #001f3f; font-size: 13px; margin: 0; line-height: 1.2;}
    .promo-details { font-size: 11px; color: #444; line-height: 1.5; }

    /* Etiquetas del Mapa */
    .map-label {
        background: white !important; border: 2px solid #001f3f !important;
        border-radius: 4px !important; padding: 2px 6px !important;
        font-size: 11px !important; font-weight: bold !important;
        color: #001f3f !important; box-shadow: 2px 2px 5px rgba(0,0,0,0.3) !important;
        white-space: nowrap !important;
    }

    /* Textos UI */
    .stMultiSelect label { font-size: 12px !important; font-weight: bold !important; color: #001f3f;}
    </style>
    """, unsafe_allow_html=True)

# --- HEADER VISUAL ---
st.markdown('<div class="app-header"><p class="app-title">GENERADOR MAPAS EM</p><p style="font-size:12px; opacity:0.8; margin:0;">Market Study Intelligence</p></div>', unsafe_allow_html=True)

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

# --- LAYOUT DE 4 COLUMNAS ---
st.write("") 
col_izq, col_mapa, col_der, col_ctrl = st.columns([1, 3.5, 1, 1.2])

df_final = pd.DataFrame()
ALTURA_CONTENEDOR = 800 

# --- PANEL DERECHO (CONTROL) ---
with col_ctrl:
    with st.container(height=ALTURA_CONTENEDOR, border=False):
        st.markdown("##### 📂 ARCHIVO EXCEL")
        file = st.file_uploader("Sube tu archivo", type=['xlsx'], label_visibility="collapsed")
        
        if file:
            df_raw, cols = load_data(file)
            if not df_raw.empty:
                st.markdown("---")
                st.markdown("##### 🔍 FILTROS")
                
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
    
    # Función para pintar cuadros
    def render_promo_cards(data, start_idx):
        for i, row in data.iterrows():
            st.markdown(f"""
            <div class="promo-card">
                <div class="promo-header"><div class="promo-circle">{start_idx+i+1}</div><p class="promo-name">{row[cols['ref']]}</p></div>
                <div class="promo-details">
                    <b>Uds:</b> {row['UDS']} | <b>PVP m:</b> {row.get(cols['pvp'], 0):,.0f}€<br>
                    <b>Unit:</b> {row.get(cols['vrm'], 0):,.0f} €/m² | <b>Tip:</b> {row.get(cols['dorm'], 'N/A')}D
                </div>
            </div>""", unsafe_allow_html=True)

    # Llenar cuadros Izquierda y Derecha
    mid = len(df_promo) // 2
    with col_izq:
        with st.container(height=ALTURA_CONTENEDOR, border=False):
            render_promo_cards(df_promo.iloc[:mid], 0)

    with col_der:
        with st.container(height=ALTURA_CONTENEDOR, border=False):
            render_promo_cards(df_promo.iloc[mid:], mid)

    # Generar Mapa
    with col_mapa:
        m = folium.Map(tiles=None, control_scale=True)
        folium.TileLayer("https://mt1.google.com/vt/lyrs=y&x={x}&y={y}&z={z}", attr="Google", name="Satélite Híbrido").add_to(m)
        folium.TileLayer("https://mt1.google.com/vt/lyrs=m&x={x}&y={y}&z={z}", attr="Google", name="Callejero Profesional").add_to(m)

        sw, ne = df_promo[['lat', 'lon']].min().values.tolist(), df_promo[['lat', 'lon']].max().values.tolist()
        m.fit_bounds([sw, ne])
        
        for i, row in df_promo.iterrows():
            folium.Marker([row['lat'], row['lon']], 
                icon=folium.DivIcon(html=f'<div class="promo-circle" style="width:24px; height:24px;">{i+1}</div>')
            ).add_to(m)
            val_vrm = row.get(cols['vrm'], 0)
            folium.Marker([row['lat'], row['lon']], 
                icon=folium.DivIcon(html=f'<div class="map-label">{val_vrm:,.0f} €/m²</div>', icon_anchor=(-15, 12))
            ).add_to(m)

        folium.LayerControl(position='topright').add_to(m)
        st_folium(m, width="100%", height=ALTURA_CONTENEDOR, key="main_map")

else:
    # --- PANTALLA DE INICIO (ONBOARDING) ---
    with col_mapa:
        st.markdown("""
        <div style="background-color: #ffffff; padding: 60px 40px; border-radius: 12px; text-align: center; box-shadow: 0 10px 25px rgba(0,31,63,0.08); margin-top: 80px; border-top: 6px solid #001f3f;">
            <div style="font-size: 50px; margin-bottom: 20px;">🏢</div>
            <h1 style="color: #001f3f; font-family: 'Segoe UI', sans-serif; font-weight: 800; letter-spacing: -0.5px; margin-bottom: 5px;">Generador Mapas EM</h1>
            <h4 style="color: #666; font-weight: 300; margin-bottom: 40px;">Inteligencia de Mercado para Obra Nueva</h4>
            
            <div style="background-color: #f8f9fa; padding: 25px; border-radius: 8px; text-align: left; display: inline-block; width: 100%; max-width: 500px; border: 1px solid #e9ecef;">
                <h4 style="color: #001f3f; font-size: 16px; margin-top: 0;">📌 Pasos para empezar:</h4>
                <ol style="color: #444; font-size: 14px; line-height: 1.8; margin-bottom: 0; padding-left: 20px;">
                    <li>Utiliza el panel de la <b>derecha</b> para subir tu archivo Excel.</li>
                    <li>Asegúrate de que tus datos estén en la pestaña <b>EEMM</b>.</li>
                    <li>El sistema requiere las columnas: <br>
                        <code style="background: #e3f2fd; color: #0d47a1; padding: 2px 6px; border-radius: 4px;">COORD</code> 
                        <code style="background: #e3f2fd; color: #0d47a1; padding: 2px 6px; border-radius: 4px;">REF</code> 
                        <code style="background: #e3f2fd; color: #0d47a1; padding: 2px 6px; border-radius: 4px;">PVP</code> 
                        <code style="background: #e3f2fd; color: #0d47a1; padding: 2px 6px; border-radius: 4px;">VRM SCIC</code>
                    </li>
                    <li>Una vez procesado, aparecerá el Dashboard con los filtros dinámicos.</li>
                </ol>
            </div>
        </div>
        """, unsafe_allow_html=True)
