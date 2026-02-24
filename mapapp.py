import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
import googlemaps
from folium.plugins import Fullscreen

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="PropTech Analytics Pro", layout="wide")

# Carga de API Key
try:
    API_KEY = st.secrets["GOOGLE_MAPS_API_KEY"]
    gmaps = googlemaps.Client(key=API_KEY)
except:
    st.error("⚠️ Configura 'GOOGLE_MAPS_API_KEY' en los Secrets de Streamlit.")
    st.stop()

# --- FUNCIONES DE PROCESAMIENTO ---
@st.cache_data
def procesar_excel(file):
    try:
        xls = pd.ExcelFile(file)
        if 'EEMM' not in xls.sheet_names:
            st.error("❌ No se encontró la pestaña 'EEMM'.")
            return pd.DataFrame(), {}
        
        df = pd.read_excel(xls, sheet_name='EEMM')
        df.columns = [str(c).strip().upper() for c in df.columns]
        
        # Columnas clave
        col_coord = next((c for c in df.columns if 'COORD' in c), None)
        col_ref = next((c for c in df.columns if any(k in c for k in ['REF', 'PROMOCION', 'NOMBRE'])), None)
        col_vrm = 'VRM SCIC' if 'VRM SCIC' in df.columns else None
        col_muni = next((c for c in df.columns if 'CIUDAD' in c or 'MUNICIPIO' in c), None)
        col_pvp = next((c for c in df.columns if 'PVP' in c), None)

        if col_coord:
            coords = df[col_coord].astype(str).str.replace(' ', '').str.split(',', expand=True)
            df['lat'] = pd.to_numeric(coords[0], errors='coerce')
            df['lon'] = pd.to_numeric(coords[1], errors='coerce')
            df = df.dropna(subset=['lat', 'lon'])
            
        return df, {'ref': col_ref, 'vrm': col_vrm, 'muni': col_muni, 'pvp': col_pvp}
    except Exception as e:
        st.error(f"Error: {e}")
        return pd.DataFrame(), {}

# --- INTERFAZ ---
st.title("🏗️ Market Study: Análisis de Entorno")

with st.sidebar:
    st.header("📂 Gestión")
    archivo = st.file_uploader("Subir Excel", type=['xlsx'])
    show_boxes = st.toggle("Mostrar Cuadros de Datos", value=True)
    st.divider()
    st.header("🔍 Filtros")

if archivo:
    df_raw, cols = procesar_excel(archivo)
    
    if not df_raw.empty:
        # --- FILTROS DINÁMICOS EN SIDEBAR ---
        with st.sidebar:
            if cols['muni']:
                muni_opts = sorted(df_raw[cols['muni']].unique().astype(str))
                sel_muni = st.multiselect("Municipios", muni_opts, default=muni_opts)
                df_filtered = df_raw[df_raw[cols['muni']].astype(str).isin(sel_muni)]
            else:
                df_filtered = df_raw.copy()

        # Agrupamos por promoción para obtener la mediana del precio unitario (VRM SCIC)
        # Esto colapsa las múltiples unidades de una promoción en un solo punto en el mapa
        df_promo = df_filtered.groupby(cols['ref']).agg({
            'lat': 'first',
            'lon': 'first',
            cols['vrm']: 'median' if cols['vrm'] else 'mean',
            cols['pvp']: 'mean'
        }).reset_index()

        # --- DISTRIBUCIÓN DE CUADROS (Izquierda, Centro/Mapa, Derecha) ---
        n_promos = len(df_promo)
        # Dividimos las promociones en 3 grupos para repartirlas
        p_izq = df_promo.iloc[:n_promos//3]
        p_der = df_promo.iloc[n_promos//3 : 2*n_promos//3]
        p_inf = df_promo.iloc[2*n_promos//3:]

        c_izq, c_mapa, c_der = st.columns([1, 3, 1])

        # Función para dibujar cuadro
        def draw_card(row, idx):
            st.markdown(f"""
            <div style="border: 1px solid #ddd; padding: 10px; border-radius: 5px; margin-bottom: 10px; background: white; border-left: 5px solid #001f3f;">
                <h6 style="margin:0; color:#001f3f;">#{idx} {row[cols['ref']]}</h6>
                <p style="margin:0; font-size: 12px;"><b>VRM:</b> {row[cols['vrm']]:,.0f} €/m²</p>
                <p style="margin:0; font-size: 11px; color: gray;">Ref: {row[cols['ref']]}</p>
            </div>
            """, unsafe_allow_html=True)

        # Columna Izquierda
        with c_izq:
            if show_boxes:
                for i, row in p_izq.iterrows(): draw_card(row, i+1)

        # Columna Central (MAPA)
        with c_mapa:
            m = folium.Map(tiles=None)
            
            # --- AJUSTE AUTOMÁTICO DE ZOOM (fit_bounds) ---
            sw = df_promo[['lat', 'lon']].min().values.tolist()
            ne = df_promo[['lat', 'lon']].max().values.tolist()
            m.fit_bounds([sw, ne]) # Esto encuadra el zoom al 100% de los puntos

            folium.TileLayer(
                tiles="https://mt1.google.com/vt/lyrs=y&x={x}&y={y}&z={z}",
                attr="Google Hybrid", name="Google Satélite"
            ).add_to(m)

            for i, row in df_promo.iterrows():
                # Etiqueta con el precio unitario (VRM SCIC)
                vrm_label = f"{row[cols['vrm']]:,.0f}€" if pd.notnull(row[cols['vrm']]) else "N/A"
                
                # Marcador numérico
                folium.Marker(
                    [row['lat'], row['lon']],
                    icon=folium.DivIcon(html=f"""
                        <div style="background:#001f3f; color:white; border-radius:50%; width:22px; height:22px; 
                        display:flex; justify-content:center; align-items:center; font-size:10px; border:1px solid white;">
                        {i+1}</div>""")
                ).add_to(m)

                # Etiqueta de Precio Unitario (VRM)
                folium.Marker(
                    [row['lat'], row['lon']],
                    icon=folium.DivIcon(
                        html=f'<div style="background:rgba(255,255,255,0.8); padding:2px 5px; border-radius:3px; font-size:10px; font-weight:bold; color:#001f3f; white-space:nowrap; border:1px solid #001f3f;">{vrm_label}</div>',
                        icon_anchor=(-15, 10)
                    )
                ).add_to(m)

            st_folium(m, width="100%", height=650, key="mapa_v4")

        # Columna Derecha
        with c_der:
            if show_boxes:
                for i, row in p_der.iterrows(): draw_card(row, i+1)

        # Fila Inferior
        if show_boxes and not p_inf.empty:
            st.divider()
            cols_inf = st.columns(4) # Repartimos las restantes en 4 minicolumnas
            for i, (_, row) in enumerate(p_inf.iterrows()):
                with cols_inf[i % 4]:
                    draw_card(row, len(p_izq) + len(p_der) + i + 1)
