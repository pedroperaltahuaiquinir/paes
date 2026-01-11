{\rtf1\ansi\ansicpg1252\cocoartf2709
\cocoatextscaling0\cocoaplatform0{\fonttbl\f0\fswiss\fcharset0 Helvetica;}
{\colortbl;\red255\green255\blue255;}
{\*\expandedcolortbl;;}
\margl1440\margr1440\vieww11520\viewh8400\viewkind0
\pard\tx720\tx1440\tx2160\tx2880\tx3600\tx4320\tx5040\tx5760\tx6480\tx7200\tx7920\tx8640\pardirnatural\partightenfactor0

\f0\fs24 \cf0 import streamlit as st\
import pandas as pd\
import matplotlib.pyplot as plt\
import seaborn as sns\
\
# 1. Configuraci\'f3n de la p\'e1gina\
st.set_page_config(page_title="Monitor de Admisi\'f3n 2004", layout="wide")\
st.title("\uc0\u55357 \u56522  An\'e1lisis de Brechas Educativas - Admisi\'f3n 2004")\
\
# 2. Carga de datos (con cach\'e9 para que no recargue a cada clic)\
@st.cache_data\
def load_data():\
    # Aseg\'farate de tener el archivo en la misma carpeta\
    df = pd.read_csv('ArchivoC_Adm2004.csv', sep=';')\
    # Pre-procesamiento b\'e1sico\
    mapa_dep = \{1: 'Municipal', 2: 'Part. Subvencionado', 3: 'Part. Pagado', 4: 'Corp. Delegada'\}\
    df['Dependencia_Texto'] = df['GRUPO_DEPENDENCIA'].map(mapa_dep)\
    return df\
\
df = load_data()\
\
# 3. Barra Lateral (Sidebar) para Filtros Interactivos\
st.sidebar.header("Filtros de Segmentaci\'f3n")\
\
# Filtro 1: Regi\'f3n\
regiones_disponibles = sorted(df['CODIGO_REGION'].unique())\
region_sel = st.sidebar.selectbox("Selecciona una Regi\'f3n:", regiones_disponibles, index=13) # Default RM\
\
# Filtro 2: Prueba a Analizar\
prueba_sel = st.sidebar.radio("Selecciona la Prueba:", \
                              ('MATE_ACTUAL', 'LENG_ACTUAL', 'CIEN_ACTUAL', 'HCSO_ACTUAL'))\
\
# Filtro 3: Situaci\'f3n de Egreso\
egreso_sel = st.sidebar.multiselect("Situaci\'f3n de Egreso:", \
                                    sorted(df['SITUACION_EGRESO'].unique()),\
                                    default=[1])\
\
# 4. Filtrar el Dataset seg\'fan selecci\'f3n\
df_filtrado = df[\
    (df['CODIGO_REGION'] == region_sel) & \
    (df['SITUACION_EGRESO'].isin(egreso_sel))\
]\
\
# 5. Panel Principal: M\'e9tricas y Gr\'e1ficos\
col1, col2 = st.columns(2)\
\
with col1:\
    st.markdown(f"### \uc0\u55357 \u56525  Regi\'f3n \{region_sel\} | \{prueba_sel\}")\
    st.metric("Total Estudiantes", f"\{len(df_filtrado):,\}")\
    \
    # Gr\'e1fico: Boxplot\
    fig, ax = plt.subplots(figsize=(8, 6))\
    sns.boxplot(data=df_filtrado, x='Dependencia_Texto', y=prueba_sel, \
                order=['Municipal', 'Part. Subvencionado', 'Part. Pagado'],\
                palette='Set2', ax=ax)\
    plt.title(f"Distribuci\'f3n de Puntajes: \{prueba_sel\}")\
    plt.grid(True, linestyle='--', alpha=0.3)\
    st.pyplot(fig)\
\
with col2:\
    st.markdown("### \uc0\u55357 \u56520  Estad\'edsticas Clave")\
    # Tabla resumen din\'e1mica\
    resumen = df_filtrado.groupby('Dependencia_Texto')[prueba_sel].describe()[['count', 'mean', 'std', 'max']]\
    st.dataframe(resumen.style.format("\{:.1f\}"))\
\
    st.markdown("---")\
    st.info("Este dashboard permite identificar r\'e1pidamente c\'f3mo var\'eda la brecha educativa seg\'fan la geograf\'eda.")\
\
# Para correrlo, abre tu terminal y escribe:\
# streamlit run app.py}