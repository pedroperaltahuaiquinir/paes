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
st.set_page_config(page_title="Monitor Admisión ES", layout="wide", page_icon="🎓")

# Estilos CSS para Tarjetas KPI y Tabs
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
    /* Ajuste para que los gráficos no queden pegados */
    .stPlotlyChart { margin-bottom: 30px; }
</style>
""", unsafe_allow_html=True)

st.title("🎓 Monitor de Admisión Educación Superior")
st.markdown("**Herramienta de Inteligencia de Datos para Dirección Académica**")

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
    """
    mapa = {
        # Identificación
        'ID': ['ID_aux', 'MRUN', 'ID'],
        'RBD': ['RBD', 'COD_ESTABLECIMIENTO', 'CODIGO_ESTABLECIMIENTO', 'RBD_EGRESO'],
        
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
def cargar_datos_micro(filepath):
    """Carga un solo archivo para la vista Micro."""
    try:
        df = pd.read_csv(filepath, sep=None, engine='python')
    except Exception as e:
        return None, 0
    
    anio = detectar_anio(filepath)
    df = homologar_columnas(df)
    df = procesar_dependencia(df, anio)
    if 'RBD' in df.columns:
        df['RBD'] = pd.to_numeric(df['RBD'], errors='coerce')
    return df, anio

@st.cache_data
def generar_consolidado_historico():
    """Escanea TODOS los CSVs para la vista Macro (Tendencias)."""
    archivos = sorted([f for f in glob.glob("*.csv") if not re.search(r"(Libro|Codigo|Anexo|requirement)", f, re.IGNORECASE)])
    consolidado = []

    for f in archivos:
        anio = detectar_anio(f)
        if anio == 0: continue
        try:
            df_temp = pd.read_csv(f, sep=None, engine='python') 
            df_temp = homologar_columnas(df_temp)
            df_temp = procesar_dependencia(df_temp, anio)
            
            cols_metricas = [c for c in ['MATEMATICA', 'LENGUAJE', 'NEM'] if c in df_temp.columns]
            
            if cols_metricas and 'Dependencia_Texto' in df_temp.columns:
                # Agrupación Nacional
                grp_dep = df_temp.groupby('Dependencia_Texto')[cols_metricas].mean(numeric_only=True).reset_index()
                grp_dep['Año'] = anio
                grp_dep['Tipo'] = 'Nacional'
                consolidado.append(grp_dep)
                
                # Agrupación Regional
                if 'REGION' in df_temp.columns:
                    grp_reg = df_temp.groupby('REGION')[cols_metricas].mean(numeric_only=True).reset_index()
                    grp_reg['Año'] = anio
                    grp_reg['Tipo'] = 'Regional'
                    consolidado.append(grp_reg)
        except: continue

    if consolidado: return pd.concat(consolidado, ignore_index=True)
    return pd.DataFrame()

@st.cache_data
def generar_historia_rbd(lista_rbds):
    """Busca historia específica de colegios (RBD)."""
    archivos = sorted([f for f in glob.glob("*.csv") if not re.search(r"(Libro|Codigo|Anexo|requirement)", f, re.IGNORECASE)])
    historia_colegios = []
    referencia_nacional = []

    for f in archivos:
        anio = detectar_anio(f)
        if anio == 0: continue
        try:
            # Leer Header
            df_iter = pd.read_csv(f, sep=None, engine='python', nrows=5)
            df_iter = homologar_columnas(df_iter)
            
            if 'RBD' in df_iter.columns:
                df = pd.read_csv(f, sep=None, engine='python')
                df = homologar_columnas(df)
                
                # Benchmark Nacional
                if 'MATEMATICA' in df.columns:
                    referencia_nacional.append({
                        'Año': anio, 
                        'MATEMATICA': df['MATEMATICA'].mean(), 
                        'LENGUAJE': df['LENGUAJE'].mean()
                    })

                # Filtrar RBDs
                df_rbd = df[df['RBD'].isin(lista_rbds)].copy()
                if not df_rbd.empty:
                    stats = df_rbd.groupby('RBD')[['MATEMATICA', 'LENGUAJE']].mean(numeric_only=True).reset_index()
                    stats['Año'] = anio
                    historia_colegios.append(stats)
        except: continue
            
    df_main = pd.concat(historia_colegios, ignore_index=True) if historia_colegios else pd.DataFrame()
    df_ref = pd.DataFrame(referencia_nacional) if referencia_nacional else pd.DataFrame()
    return df_main, df_ref

# -----------------------------------------------------------------------------
# 3. INTERFAZ DE CARGA (SIDEBAR)
# -----------------------------------------------------------------------------
st.sidebar.header("🗂️ Archivos")
archivos_csv = sorted([f for f in glob.glob("*.csv") if not re.search(r"(Libro|Codigo|Anexo|requirement)", f, re.IGNORECASE)])

if not archivos_csv:
    st.error("No se encontraron archivos CSV de datos en el repositorio.")
    st.stop()

# -----------------------------------------------------------------------------
# 4. PESTAÑAS PRINCIPALES
# -----------------------------------------------------------------------------
tab1, tab2, tab3 = st.tabs(["📊 Radiografía Anual", "📈 Evolución Histórica", "🏢 Ficha por Colegio"])

# === TAB 1: MICRO ===
with tab1:
    archivo_sel = st.sidebar.selectbox("Seleccionar Año (Pestaña 1):", archivos_csv, index=len(archivos_csv)-1)
    df_raw, anio_actual = cargar_datos_micro(archivo_sel)

    if df_raw is not None:
        st.markdown(f"### 🔎 Análisis Detallado: Proceso {anio_actual}")
        
        # Filtros Cascada
        with st.expander("🛠️ Filtros de Segmentación", expanded=True):
            col_f1, col_f2, col_f3, col_f4 = st.columns(4)
            regs_disp = sorted(df_raw['REGION'].unique()) if 'REGION' in df_raw.columns else []
            sel_reg = col_f1.selectbox("1. Región", [None] + regs_disp, format_func=lambda x: "Todas" if x is None else f"Región {x}")
            
            mask_geo = pd.Series(True, index=df_raw.index)
            if sel_reg:
                mask_geo &= (df_raw['REGION'] == sel_reg)
                comunas_disp = sorted(df_raw[mask_geo]['COMUNA'].unique()) if 'COMUNA' in df_raw.columns else []
            else:
                comunas_disp = []
                
            sel_com = col_f2.selectbox("2. Comuna", [None] + comunas_disp, disabled=(sel_reg is None), format_func=lambda x: "Todas" if x is None else f"Cod {x}")
            if sel_com: mask_geo &= (df_raw['COMUNA'] == sel_com)
            
            deps_disp = sorted(df_raw['Dependencia_Texto'].unique()) if 'Dependencia_Texto' in df_raw.columns else []
            sel_deps = col_f3.multiselect("3. Dependencia", deps_disp, default=deps_disp)
            if sel_deps: mask_geo &= (df_raw['Dependencia_Texto'].isin(sel_deps))

        df_filtrado = df_raw[mask_geo]
        
        if not df_filtrado.empty:
            # KPIs
            k1, k2, k3, k4 = st.columns(4)
            def card(col, lbl, val):
                col.markdown(f"""<div class="metric-container"><div class="metric-label">{lbl}</div><div class="metric-value">{val}</div></div>""", unsafe_allow_html=True)
            
            card(k1, "N° Estudiantes", f"{len(df_filtrado):,}")
            if 'MATEMATICA' in df_filtrado.columns: card(k2, "Prom. Matemática", f"{df_filtrado['MATEMATICA'].mean():.0f}")
            if 'LENGUAJE' in df_filtrado.columns: card(k3, "Prom. Lenguaje", f"{df_filtrado['LENGUAJE'].mean():.0f}")
            if 'NEM' in df_filtrado.columns: card(k4, "Prom. NEM", f"{df_filtrado['NEM'].mean():.0f}")
            
            st.markdown("---")
            
            # Gráficos
            c_graf, c_tab = st.columns([2, 1])
            with c_graf:
                var_analisis = st.radio("Variable:", ["MATEMATICA", "LENGUAJE", "NEM"], horizontal=True)
                if var_analisis in df_filtrado.columns:
                    tab_g1, tab_g2 = st.tabs(["Cajas", "Curva"])
                    orden = [x for x in ['Municipal', 'Part. Subvencionado', 'Part. Pagado', 'SLEP'] if x in df_filtrado['Dependencia_Texto'].unique()]
                    with tab_g1:
                        fig, ax = plt.subplots(figsize=(10, 5))
                        sns.boxplot(data=df_filtrado, x='Dependencia_Texto', y=var_analisis, order=orden, palette="Set2", ax=ax)
                        ax.grid(True, alpha=0.3)
                        st.pyplot(fig)
                    with tab_g2:
                        fig2, ax2 = plt.subplots(figsize=(10, 5))
                        sns.kdeplot(data=df_filtrado, x=var_analisis, hue='Dependencia_Texto', hue_order=orden, fill=True, palette="Set2", ax=ax2)
                        st.pyplot(fig2)
            
            with c_tab:
                if var_analisis in df_filtrado.columns:
                    st.dataframe(df_filtrado.groupby('Dependencia_Texto')[var_analisis].mean().to_frame().style.format("{:.1f}"))

# === TAB 2: MACRO ===
with tab2:
    st.markdown("### 📈 Tendencias Históricas (2004 - 2026)")
    with st.spinner("Procesando histórico masivo..."):
        df_hist = generar_consolidado_historico()
    
    if not df_hist.empty:
        var_hist = st.selectbox("Variable Macro:", ["MATEMATICA", "LENGUAJE", "NEM"])
        
        # A. Line Chart Nacional
        df_nac = df_hist[(df_hist['Tipo'] == 'Nacional') & (df_hist[var_hist].notna())].sort_values('Año')
        if not df_nac.empty:
            fig_l, ax_l = plt.subplots(figsize=(12, 6))
            sns.lineplot(data=df_nac, x='Año', y=var_hist, hue='Dependencia_Texto', marker='o', palette="tab10", ax=ax_l)
            plt.axvline(x=2022.5, color='gray', linestyle='--')
            ax_l.set_title(f"Evolución Nacional: {var_hist}")
            ax_l.grid(True, linestyle='--')
            st.pyplot(fig_l)
            
        # B. Heatmap Regional
        st.markdown("#### Mapa de Calor Regional")
        df_reg = df_hist[df_hist['Tipo'] == 'Regional']
        if not df_reg.empty:
            pivote = df_reg.pivot(index='REGION', columns='Año', values=var_hist).sort_index()
            fig_h, ax_h = plt.subplots(figsize=(12, 8))
            sns.heatmap(pivote, cmap="YlGnBu", annot=False, ax=ax_h)
            st.pyplot(fig_h)

# === TAB 3: RBD ===
with tab3:
    st.markdown("### 🏢 Benchmarking por Colegio")
    col_i, col_v = st.columns([2, 1])
    with col_i:
        rbd_str = st.text_input("Ingresa RBDs (ej: 1, 9001):")
    with col_v:
        var_comp = st.selectbox("Comparar:", ["MATEMATICA", "LENGUAJE"])
        
    if st.button("Buscar Historia RBD") and rbd_str:
        try:
            target_rbds = [int(x.strip()) for x in rbd_str.split(',') if x.strip().isdigit()]
            with st.spinner("Buscando..."):
                df_col, df_ref = generar_historia_rbd(target_rbds)
            
            if not df_col.empty:
                fig_b, ax_b = plt.subplots(figsize=(12, 6))
                # Nacional
                if not df_ref.empty:
                    sns.lineplot(data=df_ref, x='Año', y=var_comp, color='gray', linestyle='--', label='Promedio Nacional', ax=ax_b)
                # Colegios
                df_col['RBD_Label'] = df_col['RBD'].astype(str)
                sns.lineplot(data=df_col, x='Año', y=var_comp, hue='RBD_Label', marker='o', linewidth=2.5, palette="bright", ax=ax_b)
                
                plt.axvline(x=2022.5, color='red', linestyle=':', alpha=0.3)
                ax_b.set_title(f"Historia Comparada: {var_comp}")
                ax_b.grid(True)
                st.pyplot(fig_b)
                
                st.dataframe(df_col.pivot(index='Año', columns='RBD', values=var_comp).style.format("{:.0f}"))
            else:
                st.warning("No se encontraron datos para esos RBDs en los archivos cargados.")
        except Exception as e:
            st.error(f"Error: {e}")
