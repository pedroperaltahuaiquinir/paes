import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

# 1. Configuración de la página
st.set_page_config(page_title="Monitor de Admisión 2004", layout="wide")
st.title("📊 Análisis de Brechas Educativas - Admisión 2004")

# 2. Carga de datos (con caché para que no recargue a cada clic)
@st.cache_data
def load_data():
    # Asegúrate de que el nombre del archivo sea EXACTO (mayúsculas importan)
    df = pd.read_csv('ArchivoC_Adm2004.csv', sep=';')
    # Pre-procesamiento básico
    mapa_dep = {1: 'Municipal', 2: 'Part. Subvencionado', 3: 'Part. Pagado', 4: 'Corp. Delegada'}
    df['Dependencia_Texto'] = df['GRUPO_DEPENDENCIA'].map(mapa_dep)
    return df

try:
    df = load_data()

    # 3. Barra Lateral (Sidebar) para Filtros Interactivos
    st.sidebar.header("Filtros de Segmentación")

    # Filtro 1: Región
    regiones_disponibles = sorted(df['CODIGO_REGION'].unique())
    region_sel = st.sidebar.selectbox("Selecciona una Región:", regiones_disponibles, index=13) # Default RM

    # Filtro 2: Prueba a Analizar
    prueba_sel = st.sidebar.radio("Selecciona la Prueba:", 
                                  ('MATE_ACTUAL', 'LENG_ACTUAL', 'CIEN_ACTUAL', 'HCSO_ACTUAL'))

    # Filtro 3: Situación de Egreso
    egreso_sel = st.sidebar.multiselect("Situación de Egreso:", 
                                        sorted(df['SITUACION_EGRESO'].unique()),
                                        default=[1])

    # 4. Filtrar el Dataset según selección
    df_filtrado = df[
        (df['CODIGO_REGION'] == region_sel) & 
        (df['SITUACION_EGRESO'].isin(egreso_sel))
    ]

    # 5. Panel Principal: Métricas y Gráficos
    col1, col2 = st.columns(2)

    with col1:
        st.markdown(f"### 📍 Región {region_sel} | {prueba_sel}")
        st.metric("Total Estudiantes", f"{len(df_filtrado):,}")
        
        if not df_filtrado.empty:
            # Gráfico: Boxplot
            fig, ax = plt.subplots(figsize=(8, 6))
            sns.boxplot(data=df_filtrado, x='Dependencia_Texto', y=prueba_sel, 
                        order=['Municipal', 'Part. Subvencionado', 'Part. Pagado'],
                        palette='Set2', ax=ax)
            plt.title(f"Distribución de Puntajes: {prueba_sel}")
            plt.grid(True, linestyle='--', alpha=0.3)
            st.pyplot(fig)
        else:
            st.warning("No hay datos para esta selección.")

    with col2:
        st.markdown("### 📈 Estadísticas Clave")
        if not df_filtrado.empty:
            # Tabla resumen dinámica
            resumen = df_filtrado.groupby('Dependencia_Texto')[prueba_sel].describe()[['count', 'mean', 'std', 'max']]
            st.dataframe(resumen.style.format("{:.1f}"))
        else:
            st.warning("Selecciona al menos una situación de egreso.")

        st.markdown("---")
        st.info("Este dashboard permite identificar rápidamente cómo varía la brecha educativa según la geografía.")

except Exception as e:
    st.error(f"Hubo un error al cargar los datos: {e}")
