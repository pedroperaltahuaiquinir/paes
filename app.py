import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import glob
import re

# -----------------------------------------------------------------------------
# 1. Configuración y Estilos
# -----------------------------------------------------------------------------
st.set_page_config(page_title="Monitor Admisión v4.0", layout="wide", page_icon="🎓")

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

st.title("🎓 Monitor de Evolución: Admisión Educación Superior (v4.0)")
st.markdown("Plataforma de análisis micro (detallado), macro (histórico) y seguimiento por colegio (RBD).")

# -----------------------------------------------------------------------------
# 2. Funciones de Procesamiento
# -----------------------------------------------------------------------------

def detectar_anio(filename):
    match = re.search(r'(\d{4})', filename)
    if match: return int(match.group(1))
    return 0

def homologar_columnas(df):
    """Estandariza nombres de columnas (incluyendo RBD)."""
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
        df = pd.read_csv(filepath, sep=None, engine='python')
    except: return pd.DataFrame()
    
    df = homologar_columnas(df)
    df = normalizar_dependencia(df, anio)
    
    if 'RAMA' in df.columns:
        def clean_rama(x):
            s = str(x).upper()
            if 'H' in s: return 'Científico-Humanista'
