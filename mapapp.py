import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium

# --- CONFIGURACION DE PAGINA Y MEMORIA ---
st.set_page_config(page_title="Estudio de Mercado Pro", layout="wide", initial_sidebar_state="collapsed")

# Memoria de la aplicacion
if 'hidden_promos' not in st.session_state:
    st.session_state.hidden_promos = set()
if 'reset_key' not in st.session_state:
    st.session_state.reset_key = 0
if 'do_filter_view' not in st.session_state:
    st.session_state.do_filter_view = False

# --- ESTILOS CSS TEMA OSCURO ---
st.markdown("""
<style>
header[data-testid="stHeader"] { display: none !important; }
.block-container { padding-top: 1rem !important; padding-bottom: 1rem !important; max-width: 99% !important; }
[data-testid="stAppViewContainer"] { background-color: #121212 !important; }
p, h1, h2, h3, h4, h5, h6, label, span { color: #e0e0e0 !important; font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif; margin-bottom: 2px !important;}

/* Header */
.app-header {
    background-color: #1e1e1e; padding: 8px 20px; 
    border-bottom: 2px solid #3a86ff; border-radius: 6px;
    margin-bottom: 10px; display: flex; justify-content: space-between; align-items: center;
}
.app-title { font-size: 16px !important; font-weight: 800 !important; margin: 0 !important; color: #ffffff !important; }

/* Tarjetas Flexibles */
.promo-card {
    background-color: #252525; border: 1px solid #3a3a3a; border-radius: 6px;
    padding: 8px 10px; margin-bottom: 4px; transition: all 0.2s;
    min-height: 70px; display: flex; flex-direction: column; justify-content: center; position: relative;
}
.promo-card:hover { border-color: #3a86ff; }
.promo-header { display: flex; align-items: center; gap: 8px; margin-bottom: 4px; padding-right: 15px;}
.promo-pill-ui {
    background-color: #3a86ff; color: white; border-radius: 10px;
    min-width: 26px; height: 18px; display: flex; justify-content: center;
    align-items: center; font-size: 10px; font-weight: bold; flex-shrink: 0; padding: 0 5px;
}
.promo-name { 
    font-weight: 700 !important; color: #ffffff !important; font-size: 11px !important; margin: 0 !important; 
    white-space: nowrap; overflow: hidden; text-overflow: ellipsis; width: 100%;
}
.promo-details { font-size: 10px !important; color: #b0b0b0 !important; line-height: 1.3 !important; }
.promo-details b { color: #ffffff !important; }

/* Filtros Ultra-Compactos */
div[data-baseweb="select"] > div { background-color: #252525 !important; border-color: #3a3a3a !important; min-height: 24px !important; padding: 2px !important;}
span[data-baseweb="tag"] { background-color: #3a86ff !important; color: white !important; font-size: 9px !important; padding: 2px 4px !important; height: 18px !important; margin: 2px !important;}
.stMultiSelect label { font-size: 10px !important; font-weight: bold !important; color: #a0a0a0 !important; padding-bottom: 0px !important;}

/* Botones Nativos Streamlit (Adaptables) */
div.stButton > button {
    padding: 2px 6px !important; font-size: 10px !important; min-height: 24px !important;
    background-color: transparent; border: 1px solid #3a3a3a; color: #a0a0a0; border-radius: 4px; display: flex; margin: auto;
}
div.stButton > button:hover { border-color: #3a86ff; color: #ffffff; background-color: #1e1e1e; }

/* Boton de la Tarjeta (Micro-cruz) */
.btn-micro > div > button { height: 18px !important; width: 18px !important; font-size: 9px !important; border: none !important;}
</style>
""", unsafe_allow_html=True)

# --- HEADER VISUAL ---
st.markdown('<div class="app-header"><p class="app-title">ESTUDIO DE MERCADO PRO</p><p style="font-size:10px; color:#b0b0b0; margin:0;">Analisis de Entorno & Pricing</p></div>', unsafe_allow_html=True)

# --- LOGICA DE DATOS Y LIMPIEZA ---
@st.cache_data
def load_data(file):
    try:
        xls = pd.ExcelFile(file)
        df = pd.read_excel(xls, sheet_name='EEMM')
        df.columns = [str(c).strip().upper() for c in df.columns]
        
        c = {
            'coord': next((x for x in df.columns if 'COORD' in x), None),
            'ref': next((x for x in df.columns if 'REF' in x), None),
            'nombre': next((x for x in df.columns if any(k in x for k in ['PROMOCI', 'NOMBRE', 'PROYECTO'])), None),
            'vrm': 'VRM SCIC', 'pvp': 'PVP', 'tipo': next((x for x in df.columns if 'TIPOLOGI' in x), None),
            'tier': 'TIER', 'zona': 'ZONA', 'ciudad': next((x for x in df.columns if 'CIUDAD' in x), None),
            'planta': 'PLANTA', 'dorm': 'Nº DORM'
        }
        
        if not c['ref']: c['ref'] = c['nombre']
        if not c['nombre']: c['nombre'] = c['ref']

        if c['coord']:
            coords = df[c['coord']].astype(str).str.replace(' ', '').str.split(',', expand=True)
            df['lat'] = pd.to_numeric(coords[0], errors='coerce')
            df['lon'] = pd.to_numeric(coords[1], errors='coerce')
            return df.dropna(subset=['lat', 'lon']), c
        return pd.DataFrame(), {}
    except Exception as e: 
        st.error(f"Error al procesar: {e}")
        return pd.DataFrame(), {}

def clean_dorm(x):
    items = set()
    for i in x.dropna():
        s = str(i).replace('.0', '').strip().upper()
        if s:
            if not s.endswith('D'): s += 'D'
            items.add(s)
    return "-".join(sorted(list(items)))

# --- LAYOUT DE COLUMNAS ---
col_izq, col_mapa, col_der, col_ctrl = st.columns([1, 3.8, 1, 0.9])

df_final = pd.DataFrame()
ALTURA_CONTENEDOR = 820 

# --- PANEL DERECHO (CONTROL Y FILTROS) ---
with col_ctrl:
    with st.container(height=ALTURA_CONTENEDOR, border=False):
        file = st.file_uploader("Subir Excel", type=['xlsx'], label_visibility="collapsed")
        
        if file:
            mostrar_etiquetas = st.toggle("Ver Precios", value=True)
            
            # Controles de Mapa integrados en el lateral
            c_map1, c_map2 = st.columns(2)
            with c_map1:
                tipo_vista = st.selectbox("Vista", ["Satelite", "Callejero"])
            with c_map2:
                estilo_mapa = st.selectbox("Estilo", ["Estandar", "Escala de Grises", "Azul Oscuro"])
            
            st.markdown("---")
            
            # BOTONES DE ACCION GLOBAL
            c_btn1, c_btn2 = st.columns(2)
            with c_btn1:
                if st.button("Reset Filtros", use_container_width=True):
                    st.session_state.reset_key += 1
                    st.rerun()
            with c_btn2:
                if st.button("Reset Ocultos", use_container_width=True):
                    st.session_state.hidden_promos.clear()
                    st.rerun()
            
            # BOTON DE FILTRADO DE VISTA
            if st.button("Filtrar vista", use_container_width=True):
                st.session_state.do_filter_view = True
                    
            st.markdown("---")

            df_raw, cols = load_data(file)
            if not df_raw.empty:
                def mk_filter(lbl, col_name, f_key):
                    if col_name and col_name in df_raw.columns:
                        opts = sorted(df_raw[col_name].dropna().unique().astype(str))
                        return st.multiselect(lbl, opts, default=opts, key=f"{f_key}_{st.session_state.reset_key}")
                    return []
                
                f_tipo = mk_filter("Tipologia", cols['tipo'], "tipo")
                f_tier = mk_filter("Tier", cols['tier'], "tier")
                f_zona = mk_filter("Zona", cols['zona'], "zona")
                f_ciudad = mk_filter("Ciudad", cols['ciudad'], "ciudad")
                f_planta = mk_filter("Planta", cols['planta'], "planta")
                f_dorm = mk_filter("Dormitorios", cols['dorm'], "dorm")

                mask = pd.Series(True, index=df_raw.index)
                if cols['tipo']: mask &= df_raw[cols['tipo']].astype(str).isin(f_tipo)
                if cols['tier']: mask &= df_raw[cols['tier']].astype(str).isin(f_tier)
                if cols['zona']: mask &= df_raw[cols['zona']].astype(str).isin(f_zona)
                if cols['ciudad']: mask &= df_raw[cols['ciudad']].astype(str).isin(f_ciudad)
                if cols['planta']: mask &= df_raw[cols['planta']].astype(str).isin(f_planta)
                if cols['dorm']: mask &= df_raw[cols['dorm']].astype(str).isin(f_dorm)
                
                df_filtered = df_raw[mask]
                
                if not df_filtered.empty:
                    agg_rules = {
                        'lat':'first', 'lon':'first', 
                        cols['vrm']:'median' if cols['vrm'] in df_filtered.columns else 'first',
                        cols['pvp']:'mean' if cols['pvp'] in df_filtered.columns else 'first'
                    }
                    if cols['nombre'] and cols['nombre'] != cols['ref']:
                        agg_rules[cols['nombre']] = 'first'
                    if cols['dorm']: agg_rules[cols['dorm']] = clean_dorm
                    
                    df_promo = df_filtered.groupby(cols['ref']).agg(agg_rules).reset_index()
                    counts = df_filtered.groupby(cols['ref']).size().reset_index(name='UDS')
                    df_promo = pd.merge(df_promo, counts, on=cols['ref'])

                    # LOGICA DE FILTRADO POR VISTA (Bounding Box)
                    if st.session_state.do_filter_view:
                        st.session_state.do_filter_view = False
                        map_data = st.session_state.get("main_map")
                        
                        if map_data and map_data.get("bounds"):
                            b = map_data["bounds"]
                            sw_lat, sw_lon = b['_southWest']['lat'], b['_southWest']['lng']
                            ne_lat, ne_lon = b['_northEast']['lat'], b['_northEast']['lng']
                            
                            for _, row in df_promo.iterrows():
                                lat, lon = row['lat'], row['lon']
                                ref = str(row[cols['ref']])
                                if not (sw_lat <= lat <= ne_lat and sw_lon <= lon <= ne_lon):
                                    st.session_state.hidden_promos.add(ref)
                            
                            st.rerun()
                    
                    # Separar Visibles y Ocultos
                    df_visible = df_promo[~df_promo[cols['ref']].astype(str).isin(st.session_state.hidden_promos)]
                    df_ocultos = df_promo[df_promo[cols['ref']].astype(str).isin(st.session_state.hidden_promos)]

                    st.markdown("---")
                    with st.expander(f"Ocultos ({len(df_ocultos)})"):
                        if not df_ocultos.empty:
                            if st.button("Restaurar Todos", use_container_width=True):
                                st.session_state.hidden_promos.clear()
                                st.rerun()
                            for _, row in df_ocultos.iterrows():
                                ref_oculta = str(row[cols['ref']])
                                nombre_oculto = str(row.get(cols['nombre'], ref_oculta))
                                if nombre_oculto.lower() in ['nan', 'none', '']: nombre_oculto = ref_oculta

                                cx_card, cx_btn = st.columns([0.85, 0.15], vertical_alignment="center")
                                with cx_card:
                                    st.markdown(f"<div style='background:#1e1e1e; padding:5px; border-radius:4px; margin-bottom:4px;'><span style='font-size:10px; color:#3a86ff; font-weight:bold;'>{ref_oculta}</span> <span style='font-size:10px; color:#aaa;'>{nombre_oculto[:12]}...</span></div>", unsafe_allow_html=True)
                                with cx_btn:
                                    if st.button("V", key=f"res_{ref_oculta}"):
                                        st.session_state.hidden_promos.remove(ref_oculta)
                                        st.rerun()

# --- VISTA CENTRAL Y LATERALES ---
if file and not df_filtered.empty:
    
    def render_promo_card(row, side="right"):
        ref_str = str(row[cols['ref']])
        nombre_str = str(row.get(cols['nombre'], ref_str))
        if nombre_str.lower() in ['nan', 'none', '']: nombre_str = ref_str
        tipos = row.get(cols['dorm'], 'N/A')
        
        card_html = f"""
        <div class="promo-card">
            <div class="promo-header">
                <div class="promo-pill-ui">{ref_str}</div>
                <p class="promo-name" title="{nombre_str}">{nombre_str}</p>
            </div>
            <div class="promo-details">
                Uds: <b>{row['UDS']}</b> | <b>{row.get(cols['vrm'], 0):,.0f} €/m²</b><br>
                Med: <b>{row.get(cols['pvp'], 0):,.0f}€</b> | Tip: {tipos}
            </div>
        </div>"""

        if side == "left":
            c_btn, c_card = st.columns([0.1, 0.9], vertical_alignment="center")
            with c_btn:
                st.markdown("<div class='btn-micro'>", unsafe_allow_html=True)
                if st.button("X", key=f"hide_{ref_str}"):
                    st.session_state.hidden_promos.add(ref_str)
                    st.rerun()
                st.markdown("</div>", unsafe_allow_html=True)
            with c_card:
                st.markdown(card_html, unsafe_allow_html=True)
        else:
            c_card, c_btn = st.columns([0.9, 0.1], vertical_alignment="center")
            with c_card:
                st.markdown(card_html, unsafe_allow_html=True)
            with c_btn:
                st.markdown("<div class='btn-micro'>", unsafe_allow_html=True)
                if st.button("X", key=f"hide_{ref_str}"):
                    st.session_state.hidden_promos.add(ref_str)
                    st.rerun()
                st.markdown("</div>", unsafe_allow_html=True)

    # LOGICA DE REPARTO INTELIGENTE DE TARJETAS
    TOTAL_CARDS = len(df_visible)
    MAX_LEFT_CAPACITY = 10 

    with col_izq:
        with st.container(height=ALTURA_CONTENEDOR, border=False):
            if TOTAL_CARDS <= MAX_LEFT_CAPACITY:
                for _, row in df_visible.iterrows(): render_promo_card(row, side="left")
            else:
                mid = TOTAL_CARDS // 2 + (TOTAL_CARDS % 2) 
                for _, row in df_visible.iloc[:mid].iterrows(): render_promo_card(row, side="left")

    with col_der:
        with st.container(height=ALTURA_CONTENEDOR, border=False):
            if TOTAL_CARDS > MAX_LEFT_CAPACITY:
                mid = TOTAL_CARDS // 2 + (TOTAL_CARDS % 2)
                for _, row in df_visible.iloc[mid:].iterrows(): render_promo_card(row, side="right")

    # Generar Mapa SIN Controles Superpuestos
    with col_mapa:
        m = folium.Map(tiles=None, control_scale=False, zoom_control=False)
        
        # Capa base siempre limpia de negocios
        NO_POI_STYLE = "s.t%3A3%7Cp.v%3Aoff"
        tipo_lyrs = "y" if tipo_vista == "Satelite" else "m"

        folium.TileLayer(
            tiles=f"https://mt1.google.com/vt/lyrs={tipo_lyrs}&x={{x}}&y={{y}}&z={{z}}&apistyle={NO_POI_STYLE}",
            attr="Google", name=tipo_vista, control=False
        ).add_to(m)

        # Inyeccion de filtros CSS a la capa de mapas para colores puros
        map_filter_css = ""
        if estilo_mapa == "Escala de Grises":
            map_filter_css = "<style>.leaflet-tile-pane { filter: grayscale(100%) contrast(110%); }</style>"
        elif estilo_mapa == "Azul Oscuro":
            if tipo_vista == "Callejero":
                map_filter_css = "<style>.leaflet-tile-pane { filter: invert(100%) hue-rotate(180deg) brightness(95%) contrast(90%); }</style>"
            else:
                map_filter_css = "<style>.leaflet-tile-pane { filter: brightness(45%) contrast(120%) saturate(70%); }</style>"

        if map_filter_css:
            m.get_root().html.add_child(folium.Element(map_filter_css))

        if not df_visible.empty:
            if not st.session_state.get('do_filter_view'):
                sw, ne = df_visible[['lat', 'lon']].min().values.tolist(), df_visible[['lat', 'lon']].max().values.tolist()
                m.fit_bounds([sw, ne])
            
            for i, row in df_visible.iterrows():
                ref_str = str(row[cols['ref']])
                val_vrm = row.get(cols['vrm'], 0)
                
                if mostrar_etiquetas:
                    marker_html = f"""
                    <div style="display: flex; align-items: center; drop-shadow: 0 2px 4px rgba(0,0,0,0.6); font-family: Arial, sans-serif;">
                        <div style="background-color: #3a86ff; color: white; border-radius: 12px; min-width: 28px; height: 20px; 
                                    display: flex; justify-content: center; align-items: center; font-size: 10px; 
                                    font-weight: bold; border: 1.5px solid white; z-index: 2; padding: 0 4px;">
                            {ref_str}
                        </div>
                        <div style="background-color: white; border: 1.5px solid #3a86ff; border-radius: 4px; 
                                    padding: 1px 6px 1px 10px; margin-left: -8px; font-size: 10px; font-weight: bold; 
                                    color: #121212; white-space: nowrap; z-index: 1;">
                            {val_vrm:,.0f} €/m²
                        </div>
                    </div>
                    """
                else:
                    marker_html = f"""
                    <div style="drop-shadow: 0 2px 4px rgba(0,0,0,0.6); font-family: Arial, sans-serif;">
                        <div style="background-color: #3a86ff; color: white; border-radius: 12px; min-width: 28px; height: 20px; 
                                    display: flex; justify-content: center; align-items: center; font-size: 10px; 
                                    font-weight: bold; border: 1.5px solid white; padding: 0 4px;">
                            {ref_str}
                        </div>
                    </div>
                    """
                
                folium.Marker(
                    [row['lat'], row['lon']], 
                    icon=folium.DivIcon(html=marker_html, icon_anchor=(14, 10))
                ).add_to(m)

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
                    <li>El sistema procesara la pestana EEMM automaticamente.</li>
                    <li>Se requieren las columnas clave: COORD, REF, PVP y VRM SCIC.</li>
                    <li>Utiliza los filtros para segmentar el mercado en tiempo real.</li>
                </ol>
            </div>
        </div>
        """, unsafe_allow_html=True)
