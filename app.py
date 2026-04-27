import streamlit as st
import pandas as pd
import numpy as np

# ==========================================
# CONFIGURACIÓN DE LA PÁGINA
# ==========================================
st.set_page_config(page_title="Centro de Estrategia Adif", page_icon="🏛️", layout="wide")
st.title("🏛️ Centro de Estrategia Adif")

# ==========================================
# LÓGICA DE CÁLCULO
# ==========================================
def calcular_adif(df, presupuesto):
    n = len(df)
    if n == 0: return df, 0, 0, 0, 0, 0, ""

    # Asegurar numéricos
    df['Baja'] = pd.to_numeric(df['Baja'], errors='coerce').fillna(0)
    df['Pt'] = pd.to_numeric(df['Pt'], errors='coerce').fillna(0)
    
    bm = df['Baja'].mean()
    br = df['Baja'].mean()
    desv_tipica = df['Baja'].std(ddof=0) # Desviación típica poblacional
    if pd.isna(desv_tipica): desv_tipica = 0.0
    
    if n < 5:
        ut = 100 / (5 * bm) if bm > 0 else 2.5
        limite = bm + ut
        criterio = "n < 5 (Límite = BM + UT)"
    else:
        ut = 100 / (5 * br) if br > 0 else 2.5
        limite = br + ut
        criterio = "n >= 5 (Límite = BR + UT)"
        
    df['En Temeridad'] = df['Baja'] > limite
    mejor_baja = df[~df['En Temeridad']]['Baja'].max()
    if pd.isna(mejor_baja) or mejor_baja == 0: mejor_baja = df['Baja'].max()
        
    df['Pe'] = (df['Baja'] / mejor_baja) * 51 if mejor_baja > 0 else 0
    df.loc[df['En Temeridad'], 'Pe'] = 0 
    
    df['Total'] = df['Pe'] + df['Pt']
    df = df.sort_values('Total', ascending=False).reset_index(drop=True)
    df.index = df.index + 1 
    
    return df, bm, br, ut, limite, desv_tipica, criterio, mejor_baja

# ==========================================
# INTERFAZ DE USUARIO (SIDEBAR Y TABLA)
# ==========================================
st.sidebar.header("⚙️ Configuración Inicial")
presupuesto = st.sidebar.number_input("Presupuesto Base (€)", value=64697149.91, step=1000.0)
n_licitadores = st.sidebar.number_input("Nº de Licitadores", min_value=1, value=5, step=1)

# Inicializar datos en la sesión
if 'datos' not in st.session_state or len(st.session_state.datos) != n_licitadores:
    datos_iniciales = []
    for i in range(n_licitadores):
        es_mi_empresa = (i == 0)
        datos_iniciales.append({
            "Empresa": "MI EMPRESA" if es_mi_empresa else f"Competidor {i}",
            "Pt": 47.19 if es_mi_empresa else 40.0,
            "Oferta (€)": round(presupuesto * (1 - (9.86 if es_mi_empresa else 10.5)/100), 2),
            "Baja (%)": 9.86 if es_mi_empresa else 10.5
        })
    st.session_state.datos = pd.DataFrame(datos_iniciales)

st.subheader("📝 1. Datos de la Apertura")
st.write("Edita directamente la tabla. Si cambias la Oferta o la Baja, pulsa 'Sincronizar' antes de Analizar.")

# Tabla editable
df_editado = st.data_editor(st.session_state.datos, num_rows="dynamic", use_container_width=True)

# Sincronización manual para web
col_sync1, col_sync2 = st.columns(2)
with col_sync1:
    if st.button("🔄 Calcular % desde Oferta (€)"):
        df_editado['Baja (%)'] = round((1 - (df_editado['Oferta (€)'] / presupuesto)) * 100, 4)
        st.session_state.datos = df_editado
        st.rerun()
with col_sync2:
    if st.button("🔄 Calcular Oferta (€) desde %"):
        df_editado['Oferta (€)'] = round(presupuesto * (1 - (df_editado['Baja (%)'] / 100)), 2)
        st.session_state.datos = df_editado
        st.rerun()

st.divider()

# ==========================================
# RESULTADOS Y SIMULADOR
# ==========================================
if st.button("📊 Analizar Adjudicación", type="primary"):
    # Limpiamos nombres de columnas para el cálculo
    df_calc = df_editado.rename(columns={"Baja (%)": "Baja"})
    df_res, bm, br, ut, limite, desv, crit, m_baja = calcular_adif(df_calc, presupuesto)
    
    adjudicatario = df_res.iloc[0]['Empresa']
    
    st.success(f"🏆 **Adjudicatario Provisional:** {adjudicatario}")
    
    # Métricas clave con la Desviación Típica añadida
    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("Baja Media (BM)", f"{bm:.4f}%")
    col2.metric("Desviación Típica (σ)", f"{desv:.4f}%")
    col3.metric("Baja Referencia (BR)", f"{br:.4f}%")
    col4.metric("Umbral Temeridad (UT)", f"{ut:.4f}%")
    col5.metric("⛔ Límite Temeridad", f"> {limite:.4f}%", delta_color="inverse")
    
    # Formatear tabla de salida
    df_display = df_res.copy()
    df_display['En Temeridad'] = df_display['En Temeridad'].apply(lambda x: '❌ SÍ' if x else '✅ NO')
    st.dataframe(df_display[['Empresa', 'Pt', 'Baja', 'Pe', 'Total', 'En Temeridad']], use_container_width=True)
    
    st.divider()
    
    # Módulo Estratégico (Punto Óptimo)
    st.subheader("🎯 Oráculo Estratégico (Punto Óptimo)")
    mi_fila = df_res[df_res['Empresa'] == "MI EMPRESA"]
    if not mi_fila.empty:
        mi_fila = mi_fila.iloc[0]
        if mi_fila['Empresa'] == adjudicatario:
            st.info("✅ **¡Felicidades!** Has ganado la licitación con la oferta actual.")
        else:
            pts_necesarios = df_res.iloc[0]['Total'] - mi_fila['Pt']
            baja_necesaria = (pts_necesarios * m_baja) / 51 if pts_necesarios > 0 else 0
            
            if pts_necesarios > 51:
                st.error("❌ **Inviable:** La distancia técnica es tan grande que no ganarías ni ofertando un 0%.")
            else:
                st.warning(f"""
                Para superar a **{adjudicatario}**, necesitabas sacar {pts_necesarios:.2f} puntos económicos.
                Esto equivale a presentar una baja mínima del **{baja_necesaria:.2f}%**.
                *(Recuerda que el límite de temeridad estaba en {limite:.2f}%)*
                """)
