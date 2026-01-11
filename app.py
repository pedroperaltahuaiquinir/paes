import streamlit as st
import os
import pandas as pd

st.title("🚑 Pantalla de Diagnóstico")

st.write("✅ **Streamlit está funcionando.**")

# 1. Ver qué archivos hay en la carpeta
files = os.listdir('.')
st.write("📂 **Archivos detectados en el servidor:**")
st.write(files)

# 2. Buscar CSVs
csvs = [f for f in files if f.endswith('.csv')]
st.write(f"📊 **Archivos CSV encontrados:** {len(csvs)}")
st.write(csvs)

# 3. Intentar leer el primero
if csvs:
    first_csv = csvs[0]
    st.write(f"intentando leer: {first_csv}...")
    try:
        df = pd.read_csv(first_csv, sep=None, engine='python')
        st.success(f"Lectura exitosa. Columnas encontradas: {list(df.columns)}")
    except Exception as e:
        st.error(f"Error al leer el archivo: {e}")
else:
    st.error("❌ NO hay archivos CSV. Súbelos a GitHub.")
