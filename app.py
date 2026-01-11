import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import glob
import re
import os

# -----------------------------------------------------------------------------
# 1. CONFIGURACIÓN INICIAL Y ESTILOS
# -----------------------------------------------------------------------------
st.set_page_config(page_title="Monitor Admisión ES", layout="wide", page_icon="📊")

# CSS para tarjetas de KPIs y estilo general
st.markdown("""
<style>
    .metric-container {
        background-color: #f8f9fa;
        border-left: 5px solid #4e8cff;
        padding: 15px;
        border-radius: 5px;
        box-shadow: 1px 1px 3px rgba(0,0,0,0.1);
    }
    .metric-label { font-size: 14px; color: #666; margin-bottom: 5px; }
    .metric-value { font-size: 24px; font-weight: bold; color: #333; }
</style>
""", unsafe_allow_html=True)

st.title("🎓 Monitor de Admisión Educación Superior")
st.markdown("**Herramienta de Análisis Técnico para Dirección Académica**")

# -----------------------------------------------------------------------------
# 2. MOTOR DE PROCESAMIENTO (ETL)
# -----------------------------------------------------------------------------

def detectar_anio(filename):
    """Extrae el año del nombre del archivo."""
    match = re.search(r'(\d{4})', filename)
    if match: return int(match.group(1))
    return 0

def homologar_columnas(df):
    """
    Normaliza los nombres de variables históricas (2004-2026) a un estándar único.
    Basado en los Libros de Códigos suministrados.
    """
    mapa = {
        # Identificación
        'ID': ['ID_aux', 'MRUN', 'ID'],
        'RBD': ['RBD', 'COD_ESTABLECIMIENTO', 'CODIGO_ESTABLECIMIENTO'],
        
        # Notas y NEM
        'NEM': ['PTJE_NEM', 'PTJE_NEM_ACTUAL', 'NEM'],
        'RANKING': ['PTJE_RANKING', 'RANKING'],
        'NOTAS': ['PROM_NOTAS', 'PROMEDIO_NOTAS', 'NOTAS'],
        
        # Pruebas (Prioridad: Regular Actual > Actual > Anterior)
        'MATEMATICA': ['MATE1_REG_ACTUAL', 'MATE_ACTUAL', 'PDT_MATE', 'MATE_1_ACTUAL'], 
        'MATEMATICA_2': ['MATE2_REG_ACTUAL', 'MATE_2_ACTUAL'], 
        'LENGUAJE': ['CLEC_REG_ACTUAL', 'LENG_ACTUAL', 'CLEC_ACTUAL', 'PDT_LENG'],
        'CIENCIAS': ['CIEN_REG_ACTUAL', 'CIEN_ACTUAL', 'PDT_CIEN'],
        'HISTORIA': ['HCSOC_REG_ACTUAL', 'HCSO_ACTUAL', 'PDT_HCSO'],
        
        # Segmentación
        'REGION': ['CODIGO_REGION', 'COD_REGION', 'REGION_EGRESO', 'COD REG.', 'COD_REG_EGRESO'],
        'COMUNA': ['CODIGO_COMUNA', 'COD_COMUNA', 'COMUNA_EGRESO', 'COD_COM_EGRESO'],
        'DEPENDENCIA': ['GRUPO_DEPENDENCIA', 'COD_DEPE', 'DEPENDENCIA'],
        'RAMA': ['RAMA', 'COD_RAMA', 'RAMA_EDUCACIONAL'],
        'SITUACION_EGRESO': ['SITUACION_EGRESO']
    }
    
    renames = {}
    cols_origen = df.columns.tolist()
    
    for estandar, variantes in mapa.items():
        for variante in variantes:
            if variante in cols_origen:
                renames[variante] = estandar
                break 
    return df.rename(columns=renames)

def procesar_dependencia(df, anio):
    """Aplica la heurística de corrección de códigos de dependencia."""
    if 'DEPENDENCIA' not in df.columns: return df
    
    # Lógica: Antes de 2011 (aprox) 1=Muni, 3=Pagado. Después se invierte.
    es_esquema_nuevo = anio >= 2011
    
    if es_esquema_nuevo:
        mapa = {1: 'Part. Pagado', 2: 'Part. Subvencionado', 3: 'Municipal', 4: 'SLEP', 5: 'SLEP', 6: 'SLEP'}
    else:
        mapa = {1: 'Municipal', 2: 'Part. Subvencionado', 3: 'Part. Pagado', 4: 'Corp.'}
        
    df['Dependencia_Texto'] = df['DEPENDENCIA'].map(mapa).fillna("Otro")
    return df

@st.cache_data
def cargar_datos(filepath):
    try:
        # Intenta leer flexiblemente (separador ; o ,)
        df = pd.read_csv(filepath, sep=None, engine='python')
    except Exception as e:
        return None
    
    anio = detectar_anio(filepath)
    df = homologar_columnas(df)
    df = procesar_dependencia(df, anio)
    
    # Convertir RBD a numérico si existe
    if 'RBD' in df.columns:
        df['RBD'] = pd.to_numeric(df['RBD'], errors='coerce')
        
    return df, anio

# -----------------------------------------------------------------------------
# 3. INTERFAZ DE CARGA (SIDEBAR GLOBAL)
# -----------------------------------------------------------------------------
st.sidebar.header("🗂️ Fuente de Datos")

# Buscar CSVs excluyendo diccionarios
archivos = sorted([f for f in glob.glob("*.csv") if not re.search(r"(Libro|Codigo|Anexo|requirement)", f, re.IGNORECASE)])

if not archivos:
    st.error("No se encontraron archivos de datos (ArchivoC_Adm...).")
    st.stop()

archivo_sel = st.sidebar.selectbox("Seleccionar Año Académico:", archivos, index=len(archivos)-1)
df_raw, anio_actual = cargar_datos(archivo_sel)

if df_raw is None:
    st.error("Error al leer el archivo.")
    st.stop()

st.sidebar.success(f"Cargado: Admisión {anio_actual} ({len(df_raw):,} registros)")

# -----------------------------------------------------------------------------
# 4. CONSTRUCCIÓN DE PESTAÑAS
# -----------------------------------------------------------------------------
tab1, tab2, tab3 = st.tabs(["📊 Radiografía Anual", "📈 Evolución Histórica", "🏢 Ficha por Colegio"])

# =============================================================================
# PESTAÑA 1: RADIOGRAFÍA ANUAL (DISEÑO SOLICITADO)
# =============================================================================
with tab1:
    st.markdown(f"### 🔎 Análisis Detallado: Proceso {anio_actual}")
    
    # --- A. BARRA DE FILTROS EN CASCADA (TOP) ---
    with st.expander("🛠️ Filtros de Segmentación", expanded=True):
        col_f1, col_f2, col_f3, col_f4 = st.columns(4)
        
        # 1. Región
        regs_disp = sorted(df_raw['REGION'].unique()) if 'REGION' in df_raw.columns else []
        sel_reg = col_f1.selectbox("1. Región", [None] + regs_disp, format_func=lambda x: "Todas" if x is None else f"Región {x}")
        
        # 2. Comuna (Dinámico)
        mask_geo = pd.Series(True, index=df_raw.index)
        if sel_reg:
            mask_geo &= (df_raw['REGION'] == sel_reg)
            comunas_disp = sorted(df_raw[mask_geo]['COMUNA'].unique()) if 'COMUNA' in df_raw.columns else []
        else:
            comunas_disp = []
            
        sel_com = col_f2.selectbox("2. Comuna", [None] + comunas_disp, disabled=(sel_reg is None), format_func=lambda x: "Todas" if x is None else f"Cod {x}")
        if sel_com: mask_geo &= (df_raw['COMUNA'] == sel_com)
        
        # 3. Dependencia
        deps_disp = sorted(df_raw['Dependencia_Texto'].unique()) if 'Dependencia_Texto' in df_raw.columns else []
        sel_deps = col_f3.multiselect("3. Dependencia", deps_disp, default=deps_disp)
        if sel_deps: mask_geo &= (df_raw['Dependencia_Texto'].isin(sel_deps))
        
        # 4. Rama (Si existe)
        if 'RAMA' in df_raw.columns:
            sel_rama = col_f4.selectbox("4. Rama Educacional", ["Todas", "Científico-Humanista", "Técnico-Profesional"])
            if sel_rama != "Todas":
                term = 'H' if sel_rama == "Científico-Humanista" else 'T'
                mask_geo &= (df_raw['RAMA'].astype(str).str.contains(term))
        else:
            col_f4.info("Rama no disponible")

    # Aplicar Filtros
    df_filtrado = df_raw[mask_geo]
    
    if df_filtrado.empty:
        st.warning("No hay datos con los filtros seleccionados.")
    else:
        # --- B. TARJETAS DE KPIs (Metrics) ---
        st.markdown("#### Indicadores Generales")
        kpi1, kpi2, kpi3, kpi4 = st.columns(4)
        
        # Helper para pintar KPIs
        def card(col, label, value, suffix=""):
            col.markdown(f"""
            <div class="metric-container">
                <div class="metric-label">{label}</div>
                <div class="metric-value">{value}{suffix}</div>
            </div>
            """, unsafe_allow_html=True)

        card(kpi1, "Estudiantes Filtrados", f"{len(df_filtrado):,}")
        
        if 'MATEMATICA' in df_filtrado.columns:
            avg_mat = df_filtrado['MATEMATICA'].mean()
            card(kpi2, "Promedio Matemática", f"{avg_mat:.0f}")
        
        if 'LENGUAJE' in df_filtrado.columns:
            avg_len = df_filtrado['LENGUAJE'].mean()
            card(kpi3, "Promedio Lenguaje", f"{avg_len:.0f}")
            
        if 'NEM' in df_filtrado.columns:
            avg_nem = df_filtrado['NEM'].mean()
            card(kpi4, "Promedio NEM", f"{avg_nem:.0f}")

        st.markdown("---")

        # --- C. GRÁFICOS DE ANÁLISIS ---
        col_graf, col_tabla = st.columns([2, 1])
        
        with col_graf:
            st.subheader("Distribución de Puntajes")
            var_analisis = st.radio("Selecciona Prueba:", ["MATEMATICA", "LENGUAJE", "CIENCIAS", "HISTORIA"], horizontal=True, label_visibility="collapsed")
            
            if var_analisis in df_filtrado.columns:
                data_plot = df_filtrado[df_filtrado[var_analisis] > 0]
                
                # Pestañas internas para tipo de gráfico
                tab_g1, tab_g2 = st.tabs(["Cajas (Comparación)", "Histograma (Densidad)"])
                
                # Definir orden lógico
                orden = ['Municipal', 'Part. Subvencionado', 'Part. Pagado', 'SLEP', 'Corp.']
                orden_real = [x for x in orden if x in data_plot['Dependencia_Texto'].unique()]
                
                with tab_g1:
                    fig, ax = plt.subplots(figsize=(10, 6))
                    sns.boxplot(data=data_plot, x='Dependencia_Texto', y=var_analisis, order=orden_real, palette="Set2", ax=ax)
                    ax.set_title(f"Dispersión: {var_analisis}")
                    ax.grid(axis='y', linestyle='--', alpha=0.5)
                    st.pyplot(fig)
                
                with tab_g2:
                    fig2, ax2 = plt.subplots(figsize=(10, 6))
                    sns.kdeplot(data=data_plot, x=var_analisis, hue='Dependencia_Texto', hue_order=orden_real, fill=True, palette="Set2", ax=ax2)
                    ax2.set_title(f"Curva de Densidad: {var_analisis}")
                    ax2.set_ylabel("Frecuencia")
                    ax2.grid(axis='both', linestyle='--', alpha=0.3)
                    st.pyplot(fig2)
            else:
                st.info(f"La variable {var_analisis} no está disponible en este año.")

        with col_tabla:
            st.subheader("Resumen Estadístico")
            if var_analisis in df_filtrado.columns:
                resumen = df_filtrado.groupby('Dependencia_Texto')[var_analisis].describe()[['count', 'mean', 'std', 'max', 'min']]
                resumen.columns = ['N', 'Media', 'Desv', 'Max', 'Min']
                st.dataframe(resumen.style.format("{:.1f}"), height=400)
            
            # Botón de descarga rápido
            st.download_button(
                "📥 Descargar Datos Filtrados",
                df_filtrado.to_csv(index=False).encode('utf-8'),
                f"datos_{anio_actual}_filtrados.csv",
                "text/csv"
            )

# Placeholder para siguientes pasos
with tab2: st.info("🚧 Pestaña de Evolución Histórica en construcción...")
with tab3: st.info("🚧 Pestaña por Colegio (RBD) en construcción...")
