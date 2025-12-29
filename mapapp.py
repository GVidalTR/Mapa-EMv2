import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
import plotly.express as px

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(
    page_title="Mapa Promociones Inmobiliarias",
    page_icon="🏗️",
    layout="wide"
)

# --- FUNCIONES DE PROCESAMIENTO ---
@st.cache_data
def load_data(file):
    """Carga y procesa el Excel, limpia coordenadas y calcula promedios."""
    try:
        # Leer Excel (intenta leer la hoja EEMM, si no la primera)
        xls = pd.ExcelFile(file)
        if 'EEMM' in xls.sheet_names:
            df = pd.read_excel(xls, sheet_name='EEMM')
        else:
            df = pd.read_excel(xls, sheet_name=0)

        # 1. NORMALIZACIÓN DE COLUMNAS
        # Buscamos columnas clave ignorando mayúsculas/espacios
        cols = {c.strip().upper(): c for c in df.columns}
        
        # Mapeo inteligente de columnas (ajusta estas claves según tu Excel real si cambian)
        col_ref = next((cols[k] for k in cols if 'REF' in k), None)
        col_coord = next((cols[k] for k in cols if 'COORD' in k), None)
        col_city = next((cols[k] for k in cols if 'CIUDAD' in k), None)
        col_type = next((cols[k] for k in cols if 'TIPOLOG' in k), None) # Tipologia
        col_tier = next((cols[k] for k in cols if 'TIER' in k), None)
        col_pvp = next((cols[k] for k in cols if 'PVP' in k), None)
        col_scic = next((cols[k] for k in cols if 'SCIC' in k), None)

        if not (col_ref and col_coord):
            st.error("❌ No se encontraron las columnas 'Ref.' o 'COORD' en el Excel.")
            return None

        # 2. LIMPIEZA DE COORDENADAS
        # Separar "lat, long" en dos columnas numéricas
        df[['lat', 'lon']] = df[col_coord].astype(str).str.split(',', expand=True)
        df['lat'] = pd.to_numeric(df['lat'], errors='coerce')
        df['lon'] = pd.to_numeric(df['lon'], errors='coerce')
        
        # Eliminar filas sin coordenadas válidas
        df = df.dropna(subset=['lat', 'lon'])

        # 3. LIMPIEZA DE PRECIOS (Convertir a numérico)
        if col_pvp: df[col_pvp] = pd.to_numeric(df[col_pvp], errors='coerce')
        if col_scic: df[col_scic] = pd.to_numeric(df[col_scic], errors='coerce')

        # 4. AGRUPACIÓN Y CÁLCULO DE PROMEDIOS
        # Agrupamos por Referencia para colapsar las filas múltiples en una sola promoción
        agg_rules = {
            'lat': 'first',         # La ubicación es la misma
            'lon': 'first',
            col_ref: 'count'        # Contamos cuántas unidades hay (Total Rows)
        }
        
        if col_city: agg_rules[col_city] = 'first'
        if col_type: agg_rules[col_type] = 'first'
        if col_tier: agg_rules[col_tier] = 'first'
        if col_pvp: agg_rules[col_pvp] = 'mean'   # Promedio de precio
        if col_scic: agg_rules[col_scic] = 'mean' # Promedio de SCIC

        # Realizamos la agrupación
        df_grouped = df.groupby(col_ref).agg(agg_rules).rename(columns={col_ref: 'Unidades'})
        df_grouped = df_grouped.reset_index()

        # Renombrar columnas para uso interno fácil
        rename_map = {
            col_city: 'Ciudad',
            col_type: 'Tipo',
            col_tier: 'Tier',
            col_pvp: 'PVP_Promedio',
            col_scic: 'SCIC_Promedio'
        }
        df_grouped = df_grouped.rename(columns=rename_map)
        
        # Rellenar nulos estéticos
        df_grouped['Ciudad'] = df_grouped['Ciudad'].fillna('Sin Ciudad')
        df_grouped['Tipo'] = df_grouped['Tipo'].fillna('Sin Tipo')
        df_grouped['Tier'] = df_grouped['Tier'].fillna('Sin Tier')

        return df_grouped

    except Exception as e:
        st.error(f"Error procesando el archivo: {e}")
        return None

# --- INTERFAZ PRINCIPAL ---

st.title("🏗️ Mapa Promociones (Versión Python)")

# 1. SIDEBAR - CARGA Y FILTROS
with st.sidebar:
    st.header("1. Carga de Datos")
    uploaded_file = st.file_uploader("Sube tu Excel (.xlsx)", type=['xlsx', 'xls'])
    
    df_main = None
    
    if uploaded_file:
        df_main = load_data(uploaded_file)
        
        if df_main is not None:
            st.success(f"✅ Cargadas {len(df_main)} promociones únicas.")
            st.divider()
            
            st.header("2. Filtros")
            
            # Filtro Ciudad
            cities = sorted(df_main['Ciudad'].unique())
            selected_cities = st.multiselect("Ciudad", cities, default=cities)
            
            # Filtro Tipo
            types = sorted(df_main['Tipo'].unique())
            selected_types = st.multiselect("Tipo", types, default=types)
            
            # Filtro Tier
            tiers = sorted(df_main['Tier'].unique())
            selected_tiers = st.multiselect("Tier", tiers, default=tiers)
            
            # Aplicar filtros
            df_filtered = df_main[
                (df_main['Ciudad'].isin(selected_cities)) &
                (df_main['Tipo'].isin(selected_types)) &
                (df_main['Tier'].isin(selected_tiers))
            ]
    else:
        st.info("👆 Sube un archivo para comenzar.")

# 2. PANEL PRINCIPAL
if df_main is not None and 'df_filtered' in locals():
    
    # --- KPIs ---
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Promociones", len(df_filtered))
    col2.metric("Unidades Totales", df_filtered['Unidades'].sum())
    
    avg_scic = df_filtered['SCIC_Promedio'].mean()
    col3.metric("Promedio €/m² SCIC", f"€{avg_scic:,.0f}" if pd.notnull(avg_scic) else "N/A")
    
    avg_pvp = df_filtered['PVP_Promedio'].mean()
    col4.metric("Promedio PVP", f"€{avg_pvp:,.0f}" if pd.notnull(avg_pvp) else "N/A")
    
    st.divider()

    # --- MAPA ---
    col_map, col_stats = st.columns([2, 1])
    
    with col_map:
        st.subheader("Mapa Geográfico")
        
        if not df_filtered.empty:
            # Centrar mapa en el promedio de las coordenadas filtradas
            center_lat = df_filtered['lat'].mean()
            center_lon = df_filtered['lon'].mean()
            
            m = folium.Map(location=[center_lat, center_lon], zoom_start=9, tiles="OpenStreetMap")
            
            # Añadir capa Satélite (opcional)
            folium.TileLayer(
                tiles='https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
                attr='Esri',
                name='Satélite'
            ).add_to(m)
            
            folium.LayerControl().add_to(m)

            # Pintar marcadores
            for idx, row in df_filtered.iterrows():
                # Contenido del Popup
                html_popup = f"""
                <div style="font-family: sans-serif; width: 200px;">
                    <h4 style="color: #2563eb; margin-bottom:5px;">{row['Ref.']}</h4>
                    <b>Ciudad:</b> {row['Ciudad']}<br>
                    <b>Tipo:</b> {row['Tipo']}<br>
                    <b>Tier:</b> {row['Tier']}<br>
                    <hr style="margin: 5px 0;">
                    <b>PVP Prom:</b> €{row['PVP_Promedio']:,.0f}<br>
                    <b>SCIC Prom:</b> €{row['SCIC_Promedio']:,.0f}<br>
                    <b>Unidades:</b> {row['Unidades']}
                </div>
                """
                
                folium.Marker(
                    location=[row['lat'], row['lon']],
                    popup=folium.Popup(html_popup, max_width=300),
                    tooltip=row['Ref.'],
                    icon=folium.Icon(color='blue', icon='building', prefix='fa')
                ).add_to(m)

            # Renderizar mapa en Streamlit
            st_folium(m, width="100%", height=500)
        else:
            st.warning("No hay datos para mostrar con los filtros actuales.")

    # --- GRÁFICOS ---
    with col_stats:
        st.subheader("Estadísticas")
        
        # Gráfico de Tipos
        if not df_filtered.empty:
            fig_pie = px.pie(df_filtered, names='Tipo', title='Distribución por Tipología', hole=0.4)
            fig_pie.update_layout(height=300, margin=dict(t=30, b=0, l=0, r=0))
            st.plotly_chart(fig_pie, use_container_width=True)
            
            # Histograma de Precios SCIC
            fig_hist = px.histogram(df_filtered, x='SCIC_Promedio', nbins=20, title='Distribución Precios SCIC')
            fig_hist.update_layout(height=300, margin=dict(t=30, b=0, l=0, r=0), showlegend=False)
            st.plotly_chart(fig_hist, use_container_width=True)

else:
    # Pantalla de bienvenida
    st.markdown("""
    ### 👋 Bienvenido al nuevo visor de Promociones
    
    Esta aplicación reemplaza al antiguo visor HTML.
    
    1. Usa el panel izquierdo para cargar tu archivo Excel.
    2. La aplicación detectará automáticamente las coordenadas y calculará los promedios agrupando por **Referencia**.
    3. Filtra y explora los datos interactivamente.
    """)
