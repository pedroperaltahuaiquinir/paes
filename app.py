# =============================================================================
# PESTAÑA 2: EVOLUCIÓN HISTÓRICA (MACRO)
# =============================================================================
with tab2:
    st.markdown("### 📈 Tendencias Históricas (2004 - 2026)")
    st.info("Este módulo consolida la información de todos los archivos cargados en el sistema.")
    
    with st.spinner("Procesando historial masivo..."):
        df_hist = generar_consolidado_historico()
    
    if df_hist.empty:
        st.warning("No hay suficientes datos históricos para generar tendencias. Sube más archivos CSV.")
    else:
        # Controles
        col_ctrl1, col_ctrl2 = st.columns([1, 3])
        with col_ctrl1:
            var_hist = st.selectbox("Variable a Analizar:", ["MATEMATICA", "LENGUAJE", "NEM"], key="hist_var")
        
        # --- SECCIÓN A: TRAYECTORIAS POR DEPENDENCIA ---
        st.markdown("#### A. Evolución de Puntajes por Dependencia")
        
        # Filtramos solo datos nacionales y de dependencia
        df_chart = df_hist[(df_hist['Tipo'] == 'Nacional') & (df_hist[var_hist].notna())]
        
        # Ordenamos años para que el gráfico no salga loco
        df_chart = df_chart.sort_values('Año')
        
        if not df_chart.empty:
            fig_line, ax_line = plt.subplots(figsize=(12, 6))
            
            # Gráfico de líneas
            sns.lineplot(data=df_chart, x='Año', y=var_hist, hue='Dependencia_Texto', 
                         style='Dependencia_Texto', markers=True, dashes=False, 
                         palette="tab10", linewidth=2.5, ax=ax_line)
            
            # Marcador de cambio PSU -> PAES
            plt.axvline(x=2022.5, color='gray', linestyle='--', alpha=0.5)
            plt.text(2022.6, df_chart[var_hist].min(), 'Inicio PAES (Nueva Escala)', rotation=90, color='gray', fontsize=9)
            
            ax_line.set_title(f"Trayectoria Histórica: {var_hist}")
            ax_line.set_ylabel("Puntaje Promedio")
            ax_line.set_xlabel("Año de Admisión")
            ax_line.grid(True, linestyle='--', alpha=0.4)
            
            # Forzar ejes enteros
            ax_line.xaxis.get_major_locator().set_params(integer=True)
            
            st.pyplot(fig_line)
        
        st.markdown("---")
        
        # --- SECCIÓN B: MAPA DE CALOR REGIONAL (HEATMAP) ---
        st.markdown(f"#### B. Mapa de Calor: Evolución Regional ({var_hist})")
        
        df_heat = df_hist[df_hist['Tipo'] == 'Regional']
        
        if not df_heat.empty:
            # Pivotear: Filas=Región, Columnas=Año, Valores=Puntaje
            heatmap_data = df_heat.pivot(index='REGION', columns='Año', values=var_hist)
            heatmap_data = heatmap_data.sort_index() # Ordenar regiones numéricamente
            
            fig_heat, ax_heat = plt.subplots(figsize=(12, 8))
            sns.heatmap(heatmap_data, cmap="YlGnBu", annot=True, fmt=".0f", linewidths=.5, ax=ax_heat)
            
            ax_heat.set_title(f"Intensidad de Puntajes por Región y Año")
            ax_heat.set_ylabel("Código Región")
            st.pyplot(fig_heat)
            
        else:
            st.info("No se encontró información regional suficiente para el mapa de calor.")
