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
st.set_page_config(page_title="Monitor Admisión v4.1 (Debug)", layout="wide", page_icon="🎓")

st.markdown("""
<style>
    .metric-card {
        background-color: #f8f9fa;
        padding: 15px;
        border-radius: 8px;
        border-left: 5px solid #4e8cff;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
</style>
""", unsafe_allow_html=True)

st.title("🎓 Monitor de Evolución: Admisión Educación Superior")

# -----------------------------------------------------------------------------
# 2. SECCIÓN DE DIAGNÓSTICO (Solo visible si hay problemas)
# -----------------------------------------------------------------------------
# Buscamos archivos ignorando mayúsculas/minúsculas en la extensión
csv_files = []
for file in os.listdir("."):
    if file.lower().endswith(".csv"):
        csv_files.append(file)

st.write(f"📂 **Diagnóstico de Archivos en el Servidor:** Se encontraron {len(csv_files)} archivos CSV en total.")

# Filtramos los que no son datos (ignorar requisitos, códigos, etc.)
patron_ignorar = r"(requirements|Libro_C|Anexo|Codigos|Diccionario)"
archivos_datos = [f for f in csv_files if not re.search(patron_ignorar, f, re.IGNORECASE)]
archivos_datos = sorted(archivos_datos)

if not archivos_datos:
    st.error("🛑 **ERROR CRÍTICO:** No se detectaron archivos de datos válidos (tipo 'ArchivoC_Adm20XX.csv').")
    st.warning("Archivos encontrados en la carpeta (que fueron ignorados):")
    st.write(csv_files)
    st.info("""
    **Posibles causas:**
    1. No has subido los archivos .csv al repositorio de GitHub (quizás solo subiste el código).
    2. Los nombres de los archivos no coinciden con el formato esperado.
    3. Git LFS: Si los archivos son muy grandes, quizás solo subiste el 'puntero' y no el archivo real.
    """)
    st.stop()
else:
    with st.expander("✅ Archivos de datos detectados (Click para ver)", expanded=False):
        st.write(archivos_datos)

# -----------------------------------------------------------------------------
# 3. Funciones de Procesamiento (Tu lógica core)
# -----------------------------------------------------------------------------

def detectar_anio(filename):
    match = re.search(r'(\d{4})', filename)
    if match: return int(match.group(1))
    return 0

def homologar_columnas(df):
    mapa_maestro = {
        'ID': ['ID_aux', 'MRUN', 'ID'],
        'RBD': ['RBD', 'COD_ESTABLECIMIENTO', 'CODIGO_ESTABLECIMIENTO', 'RBD_EGRESO'],
        'NEM': ['PTJE_NEM', 'PTJE_NEM_ACTUAL', 'NEM'],
        'RANKING': ['PTJE_RANKING', 'RANKING'],
        'MATEMATICA': ['MATE_ACTUAL', 'MATE1_REG_ACTUAL', 'PDT_MATE', 'MATE_1_ACTUAL'], 
        'LENGUAJE': ['LENG_ACTUAL', 'CLEC_REG_ACTUAL', 'PDT_LENG', 'CLEC_ACTUAL'],
        'CIENCIAS': ['CIEN_ACTUAL', 'CIEN_REG_ACTUAL', 'PDT_CIEN'],
        'HISTORIA': ['HCSO_ACTUAL', 'HCSOC_REG_ACTUAL', 'PDT_HCSO'],
        'REGION': ['CODIGO_REGION', 'COD_REGION', 'REGION_EGRESO'],
        'DEPENDENCIA': ['GRUPO_DEPENDENCIA', 'COD_DEPE', 'DEPENDENCIA'],
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
    if 'DEPENDENCIA' not in df.columns: return df
    mapa = {1: 'Part. Pagado', 2: 'Part. Subvencionado', 3: 'Municipal', 4: 'SLEP', 5: 'SLEP'}
    if anio > 0 and anio < 2010:
        mapa = {1: 'Municipal', 2: 'Part. Subvencionado', 3: 'Part. Pagado', 4: 'Corp.'}
    df['Dependencia_Texto'] = df['DEPENDENCIA'].map(mapa).fillna("Otro")
    return df

@st.cache_data
def cargar_archivo_detalle(filepath, anio):
    try:
        # Forzamos lectura flexible de separadores
        df = pd.read_csv(filepath, sep=None, engine='python')
    except: return pd.DataFrame()
    
    df = homologar_columnas(df)
    df = normalizar_dependencia(df, anio)
    
    if 'RAMA' in df.columns:
        def clean_rama(x):
            s = str(x).upper()
            if 'H' in s: return 'Científico-Humanista'
            if 'T' in s: return 'Técnico-Profesional'
            return str(x)
        df['Rama_Texto'] = df['RAMA'].apply(clean_rama)
    
    return df

@st.cache_data
def generar_historico_rbd(lista_archivos, rbds_objetivo):
    historia = []
    for f in lista_archivos:
        anio = detectar_anio(f)
        if anio == 0: continue
        try:
            df_iter = pd.read_csv(f, sep=None, engine='python', nrows=5)
            df_iter = homologar_columnas(df_iter)
            if 'RBD' in df_iter.columns:
                df = pd.read_csv(f, sep=None, engine='python') # Carga completa flexible
                df = homologar_columnas(df)
                df_rbd = df[df['RBD'].isin(rbds_objetivo)].copy()
                if not df_rbd.empty:
                    stats = df_rbd.groupby('RBD')[['MATEMATICA', 'LENGUAJE']].mean(numeric_only=True).reset_index()
                    stats['Año'] = anio
                    historia.append(stats)
        except: continue
    if historia: return pd.concat(historia, ignore_index=True)
    return pd.DataFrame()

# -----------------------------------------------------------------------------
# 4. Construcción de la App
# -----------------------------------------------------------------------------

# --- Sidebar ---
st.sidebar.header("🗂️ Configuración")
archivo_sel = st.sidebar.selectbox("Selecciona Año:", archivos_datos, index=len(archivos_datos)-1)

if archivo_sel:
    anio_actual = detectar_anio(archivo_sel)
    df_micro = cargar_archivo_detalle(archivo_sel, anio_actual)
    
    # --- Pestañas ---
    tab_micro, tab_corr, tab_rbd = st.tabs(["🔬 Microanálisis", "📉 Correlaciones", "🏢 Buscador Colegios (RBD)"])

    # === TAB MICRO ===
    with tab_micro:
        st.subheader(f"Vista Detallada: {anio_actual}")
        
        # Filtros en Sidebar (para limpiar la vista principal)
        regs = sorted(df_micro['REGION'].unique()) if 'REGION' in df_micro.columns else []
        sel_regs = st.sidebar.multiselect("Región (Micro)", regs, default=[13] if 13 in regs else [])
        
        mask = pd.Series(True, index=df_micro.index)
        if sel_regs: mask &= df_micro['REGION'].isin(sel_regs)
        df_filtrado = df_micro[mask]
        
        col_g1, col_g2 = st.columns([3, 1])
        with col_g1:
            var_plot = st.selectbox("Variable:", ['MATEMATICA', 'LENGUAJE', 'CIENCIAS', 'HISTORIA'], key='v_micro')
            if var_plot in df_filtrado.columns and 'Dependencia_Texto' in df_filtrado.columns:
                data_p = df_filtrado[df_filtrado[var_plot] > 0]
                if not data_p.empty:
                    fig, ax = plt.subplots(figsize=(10, 5))
                    sns.boxplot(data=data_p, x='Dependencia_Texto', y=var_plot, palette="Set2", ax=ax)
                    ax.set_title(f"Distribución {var_plot} ({anio_actual})")
                    ax.grid(True, alpha=0.3)
                    st.pyplot(fig)
                else:
                    st.warning("No hay datos para graficar con los filtros actuales.")
        
        with col_g2:
            if var_plot in df_filtrado.columns:
                st.dataframe(df_filtrado.groupby('Dependencia_Texto')[var_plot].mean(numeric_only=True).round(1))

    # === TAB CORRELACIONES ===
    with tab_corr:
        st.markdown("### NEM vs Puntaje")
        if not df_filtrado.empty and 'NEM' in df_filtrado.columns and var_plot in df_filtrado.columns:
            data_s = df_filtrado[(df_filtrado[var_plot] > 0) & (df_filtrado['NEM'] > 0)]
            if not data_s.empty:
                if len(data_s) > 2000: data_s = data_s.sample(2000)
                fig2, ax2 = plt.subplots(figsize=(10, 6))
                sns.scatterplot(data=data_s, x='NEM', y=var_plot, hue='Dependencia_Texto', alpha=0.5, palette="Set2", ax=ax2)
                st.pyplot(fig2)
            else:
                st.warning("No hay datos válidos (mayores a 0) para correlacionar.")

    # === TAB RBD ===
    with tab_rbd:
        st.markdown("### 🕵️ Comparador Histórico (RBD)")
        col_input, col_view = st.columns([1, 3])
        
        with col_input:
            rbds_input = st.text_input("Ingresa RBDs (ej: 1, 100):")
            var_evolucion = st.radio("Prueba:", ["MATEMATICA", "LENGUAJE"], key='v_macro')
            btn_buscar = st.button("Generar Gráfico")
        
        with col_view:
            if btn_buscar and rbds_input:
                try:
                    lista_rbds = [int(x.strip()) for x in rbds_input.split(',') if x.strip().isdigit()]
                    with st.spinner("Escaneando historial..."):
                        df_hist_rbd = generar_historico_rbd(archivos_datos, lista_rbds)
                    
                    if not df_hist_rbd.empty:
                        fig3, ax3 = plt.subplots(figsize=(12, 6))
                        sns.lineplot(data=df_hist_rbd, x='Año', y=var_evolucion, hue='RBD', 
                                     palette="tab10", marker='o', linewidth=2.5, ax=ax3)
                        ax3.grid(True, linestyle='--')
                        ax3.xaxis.get_major_locator().set_params(integer=True) # Años enteros
                        st.pyplot(fig3)
                    else:
                        st.warning("No se encontraron datos históricos para esos RBDs.")
                except Exception as e:
                    st.error(f"Error al procesar: {e}")
