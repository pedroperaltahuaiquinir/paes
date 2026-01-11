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
    archivos = sorted([f for f in glob.glob("*.csv") if not re.search(r"(Libro|
