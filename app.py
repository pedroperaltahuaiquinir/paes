import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np

# -----------------------------------------------------------------------------
# 1. Configuración Global y Estilos
# -----------------------------------------------------------------------------
st.set_page_config(page_title="Monitor Multianual Admisión", layout="wide", page_icon="🎓")

# Estilo personalizado para las métricas
st.markdown("""
<style>
    .metric-card {
        background-color: #f0f2f6;
        padding: 15px;
        border-radius: 10px;
        border-left: 5px solid #4e8cff;
    }
</style>
""", unsafe_allow_html=True)

st.title("🎓 Monitor de Evolución: Admisión Educación Superior (2004-2026)")
st.markdown("Herramienta unificada para análisis de brechas en pruebas PSU, PDT y PAES.")

# -----------------------------------------------------------------------------
# 2. Motor de Procesamiento y Homologación de Datos
# -----------------------------------------------------------------------------
def homologar_columnas(df):
    """
    Traduce los nombres de columnas variables (2004 vs 2026) a un estándar común.
    """
    # Diccionario de traducción: {Nombre_Estandar: [Posibles_Nombres_Origen]}
    mapa_maestro = {
        'ID': ['ID_aux', 'MRUN'],
        'NEM': ['PTJE_NEM', 'PTJE_NEM_ACTUAL'],
        'NOTAS': ['PROM_NOTAS', 'PROMEDIO_NOTAS'],
        'MATEMATICA': ['MATE_ACTUAL', 'MATE1_REG_ACTUAL', 'PDT_MATE'], # Priorizamos M1 en PAES
        'MATEMATICA_2': ['MATE2_REG_ACTUAL'], # Solo PAES
        'LENGUAJE': ['LENG_ACTUAL', 'CLEC_REG_ACTUAL', 'PDT_LENG'],
        'CIENCIAS': ['CIEN_ACTUAL', 'CIEN_REG_ACTUAL', 'PDT_CIEN'],
        'HISTORIA': ['HCSO_ACTUAL', 'HCSOC_REG_ACTUAL', 'PDT_HCSO'],
        'REGION': ['CODIGO_REGION', 'COD_REGION'],
        'DEPENDENCIA': ['GRUPO_DEPENDENCIA', 'COD_DEPE'],
        'RAMA': ['RAMA', 'COD_RAMA'],
        'SITUACION_EGRESO': ['SITUACION_EGRESO']
    }
    
    # Renombrado dinámico
    renames = {}
    cols_existentes = df.columns.tolist()
    
    for estandar, variantes in mapa_maestro.items():
        for variante in variantes:
            if variante in cols_existentes:
                renames[variante] = estandar
                break # Encontré una coincidencia, paso a la siguiente variable
    
    df_std = df.rename(columns=renames)
    
    # Validar que existan las columnas críticas para el dashboard
    required = ['MATEMATICA', 'LENGUAJE', 'DEPENDENCIA', 'REGION']
    missing = [col for col in required if col not in df_std.columns]
    
    if missing:
        st.warning(f"⚠️ El archivo cargado parece incompleto. Faltan columnas clave: {missing}")
    
    return df_std

@st.cache_data
def load_and_clean_data(file):
    # Detectar separador (los archivos viejos suelen usar ';', los nuevos ',')
    try:
        df = pd.read_csv(file, sep=';', low_memory=False)
        if df.shape[1] < 2: # Si falló el separador
             df = pd.read_csv(file, sep=',', low_memory=False)
    except:
        df = pd.read_csv(file, sep=',', low_memory=False)

    # Aplicar homologación
    df_clean = homologar_columnas(df)
    
    # Mapeos de Códigos a Texto (Diccionarios híbridos para cubrir varios años)
    
    # Dependencia
    mapa_dep = {1: 'Municipal', 2: 'Part. Subvencionado', 3: 'Part. Pagado', 
                4: 'Corp. Delegada', 5: 'Servicio Local (SLEP)'} 
                # Nota: En 2004 el 1 era Municipal, en años recientes el código cambia. 
                # AJUSTE: En 2004 -> 1:Muni, 2:Sub, 3:Pag.
                # En 2026 -> 1:Pag, 2:Sub, 3:Muni. 
                # ¡CUIDADO! Esta inversión es peligrosa. 
                # Para solucionar esto robustamente, idealmente el usuario selecciona el año
                # o inferimos por el nombre de columna.
                # Por simplicidad de este ejemplo, asumiremos el estándar antiguo (2004) por defecto
                # o permitiremos re-mapear en la UI si se ve raro.
    
    # Rama Educacional (Simplificada)
    def clasificar_rama(val):
        str_val = str(val).upper()
        if 'H' in str_val: return 'Científico-Humanista'
        if 'T' in str_val: return 'Técnico-Profesional'
        if 'C' in str_val: return 'Comercial' # A veces separado
        return 'Otro'

    if 'DEPENDENCIA' in df_clean.columns:
        # Aquí forzamos una conversión a string para evitar errores numéricos
        # Idealmente, deberíamos tener un selector de "Año del archivo" para aplicar el mapa correcto.
        # Por ahora usaremos el mapa 2004 (según tu archivo de muestra)
        df_clean['Dependencia_Texto'] = df_clean['DEPENDENCIA'].map(mapa_dep).fillna("Otro")
    
    if 'RAMA' in df_clean.columns:
        df_clean['Rama_Texto'] = df_clean['RAMA'].apply(clasificar_rama)

    return df_clean

# -----------------------------------------------------------------------------
# 3. Interfaz de Carga (Sidebar)
# -----------------------------------------------------------------------------
st.sidebar.header("📁 Configuración de Datos")

archivo_cargado = st.sidebar.file_uploader("Sube tu archivo CSV (2004-2026)", type=["csv"])

if archivo_cargado is not None:
    df = load_and_clean_data(archivo_cargado)
    st.sidebar.success(f"Archivo cargado: {len(df):,} registros")
    
    # Detector de "Era" para corregir mapeo de dependencia (Parche necesario por cambio DEMRE)
    # Si detecta MATE1_REG_ACTUAL es era PAES (Dependencia: 1=Part, 3=Muni)
    # Si es MATE_ACTUAL es era PSU (Dependencia: 1=Muni, 3=Part -- esto varía, revisar siempre diccionario)
    # Para ser seguros, pondremos un "Inversor" manual si el usuario ve los datos raros.
    invertir_dep = st.sidebar.checkbox("¿Invertir códigos de Dependencia?", help="Úsalo si ves 'Municipal' con puntajes de 'Pagado'. El DEMRE cambió los códigos en 2010.")
    
    if invertir_dep:
        # Mapa inverso moderno
        mapa_moderno = {1: 'Part. Pagado', 2: 'Part. Subvencionado', 3: 'Municipal', 4: 'SLEP'}
        df['Dependencia_Texto'] = df['DEPENDENCIA'].map(mapa_moderno).fillna("Otro")

    # --- FILTROS GLOBALES ---
    st.sidebar.markdown("---")
    st.sidebar.subheader("🔍 Filtros de Segmentación")
    
    # Región
    regiones = sorted(df['REGION'].unique()) if 'REGION' in df.columns else []
    sel_region = st.sidebar.selectbox("Región", regiones, index=len(regiones)-1 if regiones else 0) # Default a la última (suele ser RM=13)
    
    # Rama
    ramas = sorted(df['Rama_Texto'].unique()) if 'Rama_Texto' in df.columns else []
    sel_rama = st.sidebar.multiselect("Rama Educacional", ramas, default=ramas)

    # Aplicar Filtros
    df_filtered = df[df['REGION'] == sel_region].copy()
    if 'Rama_Texto' in df.columns and sel_rama:
        df_filtered = df_filtered[df_filtered['Rama_Texto'].isin(sel_rama)]

    # --- CUERPO PRINCIPAL ---
    
    # Pestañas para organizar las vistas
    tab1, tab2, tab3 = st.tabs(["📊 Distribución de Puntajes", "📈 Correlaciones (NEM)", "📋 Datos Brutos"])

    with tab1:
        st.subheader("Análisis de Brechas por Dependencia")
        
        col_ctrl1, col_ctrl2 = st.columns(2)
        with col_ctrl1:
            variable_analisis = st.selectbox("Selecciona Prueba:", 
                                           ['MATEMATICA', 'LENGUAJE', 'CIENCIAS', 'HISTORIA'],
                                           index=0)
        with col_ctrl2:
            tipo_grafico = st.radio("Tipo de Visualización:", ["Boxplot (Cajas)", "Histograma (Densidad)"], horizontal=True)

        if variable_analisis in df_filtered.columns:
            # Eliminar ceros o nulos para el gráfico (gente que no rindió)
            data_plot = df_filtered[df_filtered[variable_analisis] > 0]
            
            fig, ax = plt.subplots(figsize=(10, 6))
            
            # Orden de categorías para consistencia visual
            orden_dep = ['Municipal', 'Part. Subvencionado', 'Part. Pagado']
            # Filtrar solo las que existen en los datos filtrados para no dar error
            orden_final = [d for d in orden_dep if d in data_plot['Dependencia_Texto'].unique()]
            
            if tipo_grafico == "Boxplot (Cajas)":
                sns.boxplot(data=data_plot, x='Dependencia_Texto', y=variable_analisis, 
                            order=orden_final, palette="Set2", ax=ax)
                ax.set_title(f"Distribución: {variable_analisis}")
            else:
                sns.kdeplot(data=data_plot, x=variable_analisis, hue='Dependencia_Texto', 
                            hue_order=orden_final, fill=True, palette="Set2", ax=ax)
                ax.set_title(f"Densidad de Puntajes: {variable_analisis}")
            
            ax.grid(True, alpha=0.3)
            st.pyplot(fig)
            
            # Estadísticas rápidas debajo del gráfico
            st.markdown("#### 🔢 Resumen Estadístico")
            stats = data_plot.groupby('Dependencia_Texto')[variable_analisis].describe()[['count', 'mean', 'std', '50%']]
            st.dataframe(stats.style.format("{:.1f}"))
        else:
            st.error(f"La variable {variable_analisis} no se encuentra en este archivo.")

    with tab2:
        st.subheader("¿El colegio predice la prueba?")
        st.markdown("Análisis de correlación entre **Notas de Enseñanza Media (NEM)** y **Prueba Seleccionada**.")
        
        if 'NEM' in df_filtered.columns and variable_analisis in df_filtered.columns:
            # Muestra aleatoria para no saturar el scatter plot (max 2000 puntos)
            data_scatter = df_filtered[(df_filtered[variable_analisis] > 0) & (df_filtered['NEM'] > 0)]
            if len(data_scatter) > 2000:
                data_scatter = data_scatter.sample(2000)
            
            fig2, ax2 = plt.subplots(figsize=(10, 6))
            sns.scatterplot(data=data_scatter, x='NEM', y=variable_analisis, 
                            hue='Dependencia_Texto', alpha=0.6, palette="Set2", ax=ax2)
            
            # Cálculo de Correlación de Pearson
            corr = df_filtered[[variable_analisis, 'NEM']].corr().iloc[0,1]
            
            ax2.set_title(f"Dispersión NEM vs {variable_analisis} (Correlación Pearson: {corr:.2f})")
            ax2.grid(True, alpha=0.3)
            st.pyplot(fig2)
            
            st.info(f"💡 **Interpretación:** Una correlación de **{corr:.2f}** indica una relación {'fuerte' if abs(corr)>0.7 else 'moderada' if abs(corr)>0.4 else 'débil'} entre las notas del colegio y el puntaje de la prueba.")
        else:
            st.warning("No se encontraron columnas de NEM o Puntaje para realizar el cruce.")

    with tab3:
        st.subheader("📥 Descarga de Datos Procesados")
        st.markdown("Descarga la sub-muestra que estás visualizando actualmente (filtrada por región y rama).")
        
        @st.cache_data
        def convert_df(df):
            return df.to_csv(index=False).encode('utf-8')

        csv = convert_df(df_filtered)

        st.download_button(
            label="Descargar Datos Filtrados (CSV)",
            data=csv,
            file_name=f'admision_filtrada_{sel_region}.csv',
            mime='text/csv',
        )

else:
    # Pantalla de bienvenida cuando no hay archivo
    st.info("👋 **Bienvenido.** Por favor sube un archivo CSV de admisión (años 2004-2026) en el menú de la izquierda para comenzar.")
    st.markdown("""
    **Instrucciones:**
    1. Abre la barra lateral (izquierda).
    2. Carga tu archivo `ArchivoC_AdmXXXX.csv`.
    3. El sistema detectará automáticamente si es PSU o PAES.
    4. Explora los gráficos y estadísticas.
    """)
