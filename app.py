import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import glob
import re
import os

# -----------------------------------------------------------------------------
# 1. Configuración y Estilos
# -----------------------------------------------------------------------------
st.set_page_config(page_title="Monitor Admisión v3.0", layout="wide", page_icon="🎓")

st.markdown("""
<style>
    .metric-card {
        background-color: #f8f9fa;
        padding: 15px;
        border-radius: 8px;
        border-left: 5px solid #4e8cff;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    .stTabs [data-baseweb="tab-list"] { gap: 20px; }
    .stTabs [data-baseweb="tab"] { height: 50px; white-space: pre-wrap; background-color: #f0f2f6; border-radius: 4px; }
    .stTabs [aria-selected="true"] { background-color: #4e8cff; color: white; }
</style>
""", unsafe_allow_html=True)

st.title("🎓 Monitor de Evolución: Admisión Educación Superior (v3.0)")
st.markdown("Plataforma de análisis micro (detallado) y macro (histórico) para pruebas PSU, PDT y PAES.")

# -----------------------------------------------------------------------------
# 2. Motor de Procesamiento de Datos
# -----------------------------------------------------------------------------

def detectar_anio(filename):
    """Extrae el año del nombre del archivo (ej: ArchivoC_Adm2004.csv -> 2004)"""
    match = re.search(r'(\d{4})', filename)
    if match:
        return int(match.group(1))
    return 0

def homologar_columnas(df):
    """Estandariza nombres de columnas entre eras (PSU -> PAES)."""
    mapa_maestro = {
        'ID': ['ID_aux', 'MRUN'],
        'NEM': ['PTJE_NEM', 'PTJE_NEM_ACTUAL'],
        'RANKING': ['PTJE_RANKING'],
        'NOTAS': ['PROM_NOTAS', 'PROMEDIO_NOTAS'],
        'MATEMATICA': ['MATE_ACTUAL', 'MATE1_REG_ACTUAL', 'PDT_MATE'], 
        'MATEMATICA_2': ['MATE2_REG_ACTUAL'], 
        'LENGUAJE': ['LENG_ACTUAL', 'CLEC_REG_ACTUAL', 'PDT_LENG', 'CLEC_ACTUAL'],
        'CIENCIAS': ['CIEN_ACTUAL', 'CIEN_REG_ACTUAL', 'PDT_CIEN'],
        'HISTORIA': ['HCSO_ACTUAL', 'HCSOC_REG_ACTUAL', 'PDT_HCSO'],
        'REGION': ['CODIGO_REGION', 'COD_REGION'],
        'COMUNA': ['CODIGO_COMUNA', 'COD_COMUNA'],
        'DEPENDENCIA': ['GRUPO_DEPENDENCIA', 'COD_DEPE'],
        'RAMA': ['RAMA', 'COD_RAMA', 'RAMA_EDUCACIONAL'],
        'SITUACION_EGRESO': ['SITUACION_EGRESO']
    }
    
    renames = {}
    cols_existentes = df.columns.tolist()
    for estandar, variantes in mapa_maestro.items():
        for variante in variantes:
            if variante in cols_existentes:
                renames[variante] = estandar
                break 
    return df.rename(columns=renames)

def normalizar_dependencia(df, anio):
    """
    Normaliza los códigos de dependencia a texto.
    Lógica: Antes de 2011 (aprox) -> 1:Muni, 3:Pagado.
            Desde 2011 (aprox) -> 1:Pagado, 3:Muni.
    """
    if 'DEPENDENCIA' not in df.columns:
        return df
    
    # Heurística temporal (ajustable)
    es_esquema_nuevo = anio >= 2011 
    
    if es_esquema_nuevo:
        mapa = {1: 'Part. Pagado', 2: 'Part. Subvencionado', 3: 'Municipal', 4: 'SLEP', 5: 'SLEP'}
    else:
        mapa = {1: 'Municipal', 2: 'Part. Subvencionado', 3: 'Part. Pagado', 4: 'Corp.'}
        
    df['Dependencia_Texto'] = df['DEPENDENCIA'].map(mapa).fillna("Otro")
    return df

@st.cache_data
def cargar_archivo_detalle(filepath, anio):
    """Carga un archivo específico para la vista detallada"""
    try:
        # Intentar detectar separador
        df = pd.read_csv(filepath, sep=';', low_memory=False)
        if df.shape[1] < 2: df = pd.read_csv(filepath, sep=',', low_memory=False)
    except:
        return pd.DataFrame()
        
    df = homologar_columnas(df)
    df = normalizar_dependencia(df, anio)
    
    # Limpieza de Rama (Mapeo genérico)
    if 'RAMA' in df.columns:
        def clean_rama(x):
            s = str(x).upper()
            if 'H' in s: return 'Científico-Humanista'
            if 'T' in s: return 'Técnico-Profesional'
            return str(x)
        df['Rama_Texto'] = df['RAMA'].apply(clean_rama)
    else:
        df['Rama_Texto'] = 'Sin Info'
        
    return df

@st.cache_data
def generar_historico_macro():
    """
    Escanea TODOS los CSV, calcula promedios y retorna un DataFrame resumen.
    Crucial para la pestaña 'Macro'.
    """
    archivos = glob.glob("*.csv")
    archivos = [f for f in archivos if "requirements" not in f and "Adm" in f] # Filtro simple
    
    history_data = []
    
    for f in archivos:
        anio = detectar_anio(f)
        if anio == 0: continue
            
        try:
            # Leer solo columnas necesarias para optimizar memoria
            df_iter = pd.read_csv(f, sep=';', low_memory=False, nrows=5) # Peek para ver columnas
            sep = ';'
            if df_iter.shape[1] < 2: sep = ','
            
            # Cargar dataset completo
            df = pd.read_csv(f, sep=sep, low_memory=False)
            df = homologar_columnas(df)
            df = normalizar_dependencia(df, anio)
            
            # Calcular promedios por Dependencia
            if 'DEPENDENCIA' in df.columns:
                agrupado = df.groupby('Dependencia_Texto')[['MATEMATICA', 'LENGUAJE']].mean().reset_index()
                agrupado['Año'] = anio
                history_data.append(agrupado)
                
        except Exception as e:
            continue
            
    if history_data:
        return pd.concat(history_data, ignore_index=True)
    return pd.DataFrame()

# -----------------------------------------------------------------------------
# 3. Interfaz de Usuario
# -----------------------------------------------------------------------------

# --- PESTAÑAS PRINCIPALES ---
tab_micro, tab_corr, tab_macro = st.tabs(["🔬 Microanálisis (Detalle Anual)", "📉 Correlaciones", "📅 Tendencias Históricas (Macro)"])

# =============================================================================
# TAB 1: MICROANÁLISIS (Con Filtros Avanzados)
# =============================================================================
with tab_micro:
    st.sidebar.header("🗂️ Selector de Datos (Micro)")
    archivos_csv = sorted(glob.glob("*.csv"))
    archivos_datos = [f for f in archivos_csv if "requirements" not in f]
    
    if not archivos_datos:
        st.error("No se encontraron archivos CSV.")
        st.stop()
        
    # Selección de Archivo
    archivo_sel = st.sidebar.selectbox("Selecciona Año/Archivo:", archivos_datos, index=len(archivos_datos)-1)
    anio_actual = detectar_anio(archivo_sel)
    
    # Cargar Datos
    df_micro = cargar_archivo_detalle(archivo_sel, anio_actual)
    st.sidebar.success(f"Cargado: {anio_actual} ({len(df_micro):,} reg.)")
    
    # --- BARRA LATERAL: FILTROS MULTIPLES ---
    st.sidebar.markdown("---")
    st.sidebar.subheader("🔍 Filtros Avanzados")
    
    with st.sidebar.expander("Geografía (Región/Comuna)", expanded=True):
        # 1. Región
        regiones_disp = sorted(df_micro['REGION'].unique()) if 'REGION' in df_micro.columns else []
        sel_regiones = st.multiselect("Regiones:", regiones_disp, default=[13] if 13 in regiones_disp else [])
        
        # 2. Comuna (Dependiente de Región)
        if 'COMUNA' in df_micro.columns:
            if sel_regiones:
                comunas_disp = sorted(df_micro[df_micro['REGION'].isin(sel_regiones)]['COMUNA'].unique())
            else:
                comunas_disp = sorted(df_micro['COMUNA'].unique())
            sel_comunas = st.multiselect("Comunas:", comunas_disp)
        else:
            sel_comunas = []

    with st.sidebar.expander("Características Colegio", expanded=False):
        # 3. Dependencia
        deps_disp = sorted(df_micro['Dependencia_Texto'].unique()) if 'Dependencia_Texto' in df_micro.columns else []
        sel_deps = st.multiselect("Dependencia:", deps_disp, default=deps_disp)
        
        # 4. Rama
        ramas_disp = sorted(df_micro['Rama_Texto'].unique()) if 'Rama_Texto' in df_micro.columns else []
        sel_ramas = st.multiselect("Rama Educacional:", ramas_disp, default=ramas_disp)

    with st.sidebar.expander("Estudiante", expanded=False):
        # 5. Situación Egreso
        egreso_disp = sorted(df_micro['SITUACION_EGRESO'].unique()) if 'SITUACION_EGRESO' in df_micro.columns else []
        sel_egreso = st.multiselect("Situación Egreso:", egreso_disp, default=[1] if 1 in egreso_disp else egreso_disp)

    # --- APLICACIÓN DE FILTROS ---
    mask = pd.Series(True, index=df_micro.index)
    
    if sel_regiones: mask &= df_micro['REGION'].isin(sel_regiones)
    if sel_comunas: mask &= df_micro['COMUNA'].isin(sel_comunas)
    if sel_deps: mask &= df_micro['Dependencia_Texto'].isin(sel_deps)
    if sel_ramas: mask &= df_micro['Rama_Texto'].isin(sel_ramas)
    if sel_egreso: mask &= df_micro['SITUACION_EGRESO'].isin(sel_egreso)
    
    df_filtrado = df_micro[mask]
    
    # --- VISUALIZACIÓN MICRO ---
    col_main, col_stats = st.columns([3, 1])
    
    with col_main:
        st.markdown(f"### Distribución de Puntajes ({len(df_filtrado):,} estudiantes)")
        var_plot = st.selectbox("Variable a graficar:", ['MATEMATICA', 'LENGUAJE', 'CIENCIAS', 'HISTORIA'], key='v1')
        
        if var_plot in df_filtrado.columns:
            df_plot = df_filtrado[df_filtrado[var_plot] > 0] # Eliminar ceros
            
            fig, ax = plt.subplots(figsize=(10, 5))
            sns.boxplot(data=df_plot, x='Dependencia_Texto', y=var_plot, palette="Set2", ax=ax)
            ax.set_title(f"Distribución {var_plot} por Dependencia")
            ax.grid(True, alpha=0.3)
            st.pyplot(fig)
        else:
            st.warning("Variable no disponible.")
            
    with col_stats:
        st.markdown("#### Estadísticas")
        if var_plot in df_filtrado.columns and not df_filtrado.empty:
            resumen = df_filtrado.groupby('Dependencia_Texto')[var_plot].mean()
            st.dataframe(resumen.round(1))
        else:
            st.write("Sin datos.")

# =============================================================================
# TAB 2: CORRELACIONES
# =============================================================================
with tab_corr:
    st.markdown("### ¿Qué tanto influye el colegio (NEM) en el resultado?")
    
    if not df_filtrado.empty and 'NEM' in df_filtrado.columns and var_plot in df_filtrado.columns:
        col_c1, col_c2 = st.columns([3, 1])
        
        with col_c1:
            # Sampling para velocidad
            data_scatter = df_filtrado[(df_filtrado[var_plot] > 0) & (df_filtrado['NEM'] > 0)]
            if len(data_scatter) > 2000: data_scatter = data_scatter.sample(2000)
            
            fig2, ax2 = plt.subplots(figsize=(10, 6))
            sns.scatterplot(data=data_scatter, x='NEM', y=var_plot, hue='Dependencia_Texto', alpha=0.5, palette="Set2", ax=ax2)
            ax2.set_title(f"NEM vs {var_plot}")
            st.pyplot(fig2)
            
        with col_c2:
            st.markdown("#### Coeficiente Pearson")
            if len(data_scatter) > 1:
                corr = data_scatter[['NEM', var_plot]].corr().iloc[0,1]
                st.metric("Correlación Global", f"{corr:.3f}")
                st.info("Mientras más cerca de 1.0, más fuerte es la relación.")
    else:
        st.warning("Se necesitan datos filtrados con variables NEM y Puntaje.")

# =============================================================================
# TAB 3: MACRO HISTÓRICO
# =============================================================================
with tab_macro:
    st.markdown("### 📅 Evolución Histórica de Brechas (2004 - 2026)")
    st.markdown("Promedios calculados automáticamente cruzando todos los archivos del repositorio.")
    
    with st.spinner("Procesando historial... esto puede tomar unos segundos..."):
        df_historia = generar_historico_macro()
    
    if not df_historia.empty:
        var_hist = st.radio("Selecciona Prueba para ver tendencia:", ["MATEMATICA", "LENGUAJE"], horizontal=True)
        
        # Filtro visual
        deps_hist = st.multiselect("Filtrar Dependencias:", df_historia['Dependencia_Texto'].unique(), default=['Municipal', 'Part. Pagado', 'Part. Subvencionado'])
        df_hist_plot = df_historia[df_historia['Dependencia_Texto'].isin(deps_hist)]
        
        fig3, ax3 = plt.subplots(figsize=(12, 6))
        sns.lineplot(data=df_hist_plot, x='Año', y=var_hist, hue='Dependencia_Texto', marker='o', linewidth=2, palette="tab10", ax=ax3)
        
        ax3.set_title(f"Evolución Promedio: {var_hist}")
        ax3.set_ylabel("Puntaje Promedio")
        ax3.grid(True, linestyle='--', alpha=0.5)
        st.pyplot(fig3)
        
        st.markdown("#### Datos Consolidados")
        st.dataframe(df_hist_plot.pivot(index='Año', columns='Dependencia_Texto', values=var_hist).style.format("{:.1f}"))
        
    else:
        st.error("No se pudo generar el histórico. Verifica que los archivos CSV estén disponibles y tengan nombres tipo 'ArchivoC_Adm20XX.csv'.")
