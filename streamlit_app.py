# app_full_pro.py
import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from io import BytesIO
from fpdf import FPDF

st.set_page_config(page_title="Fluidoterapia Full Pro — AAHA 2024", layout="wide")

# ---------- Estilos ----------
st.markdown("""
<style>
.main .block-container { background-color: rgba(255,255,255,0.96); padding: 1rem 1.25rem; }
.alert-red { background-color:#b00020;color:white;font-weight:bold; }
.alert-orange { background-color:#ff6f00;color:white;font-weight:bold; }
.alert-green { background-color:#00a152;color:white;font-weight:bold; }
</style>
""", unsafe_allow_html=True)

st.title("Calculadora Full Pro de Fluidoterapia — AAHA 2024")
st.caption("Guía clínica para planificación de terapia de fluidos en caninos y felinos. La decisión final es responsabilidad del veterinario.")

# ---------- Sidebar: Datos del paciente ----------
with st.sidebar.expander("Datos del paciente", expanded=True):
    species = st.selectbox("Especie", ["Canino", "Felino"])
    weight = st.number_input("Peso (kg)", min_value=0.01, value=10.0, format="%.2f")
    state = st.selectbox("Estado clínico", ["Mantenimiento", "Reposición", "Shock"])
    dehydration = st.slider("Grado estimado de deshidratación (%)", 0.0, 30.0, 8.0, step=0.5)
    sens_loss = st.number_input("Pérdidas sensibles (mL/día)", min_value=0.0, value=0.0, format="%.1f")
    insens_loss = st.number_input("Pérdidas insensibles (mL/día)", min_value=0.0, value=0.0, format="%.1f")

# ---------- Sidebar: Reevaluación clínica ----------
st.sidebar.subheader("Reevaluación clínica")
with st.sidebar.form("reeval_form"):
    diuresis = st.number_input("💧 Diuresis (mL/kg/h)", min_value=0.0, step=0.1, value=2.0)
    fc = st.number_input("❤️ Frecuencia cardíaca (lpm)", min_value=20, max_value=300, value=100, step=1)
    tlc = st.number_input("⏱️ Tiempo llenado capilar (s)", min_value=0.0, max_value=10.0, value=1.5, step=0.1)
    mucosas = st.selectbox("👅 Color de mucosas", ["Rosadas", "Pálidas", "Congestivas", "Cianóticas"])
    pa = st.number_input("🩸 Presión arterial sistólica (mmHg)", min_value=40, max_value=250, value=110, step=1)
    peso_actual = st.number_input("⚖️ Peso actual (kg)", min_value=0.01, value=weight, step=0.1)
    hto = st.number_input("🧪 Hematocrito (%)", min_value=10, max_value=70, value=40, step=1)
    reevaluate_btn = st.form_submit_button("Registrar reevaluación y ajustar plan")

# ---------- Inicialización del historial ----------
if "reeval_history" not in st.session_state:
    st.session_state.reeval_history = pd.DataFrame(columns=[
        "Hora", "Diuresis", "FC", "TLC", "Mucosas", "PA", "Peso", "Hto",
        "ml/kg/h ajustado", "gtt/min ajustado", "seg/gota ajustado", "Recomendación", "Nivel riesgo"
    ])

# ---------- Función de ajuste de fluidos ----------
def ajustar_fluido(base_ml, base_period_hours, weight, diuresis, fc, tlc, pa, peso_actual, hto):
    ajustes = []
    nivel_riesgo = "Normal"
    ml_per_hr = base_ml / base_period_hours

    if diuresis < 1:
        ml_per_hr *= 1.2
        ajustes.append("Diuresis baja → aumentar 20% tasa")
        nivel_riesgo = "Crítico"
    if fc > 140:
        ajustes.append("Taquicardia → monitorizar")
        if nivel_riesgo != "Crítico": nivel_riesgo = "Alerta"
    if tlc > 2:
        ml_per_hr *= 1.1
        ajustes.append("Llenado capilar lento → aumentar 10% tasa")
        if nivel_riesgo != "Crítico": nivel_riesgo = "Alerta"
    if pa < 90:
        ml_per_hr *= 1.15
        ajustes.append("Hipotensión → aumentar 15% tasa")
        nivel_riesgo = "Crítico"
    if peso_actual > weight*1.05:
        ml_per_hr *= 0.85
        ajustes.append("Peso +5% → reducir 15% tasa")
        if nivel_riesgo != "Crítico": nivel_riesgo = "Alerta"
    if hto > 55:
        ml_per_hr *= 0.9
        ajustes.append("Hematocrito alto → reducir 10% tasa")
        if nivel_riesgo != "Crítico": nivel_riesgo = "Alerta"

    return ml_per_hr, ajustes, nivel_riesgo

# ---------- Procesar reevaluación ----------
if reevaluate_btn:
    base_ml = 60*weight if species=="Canino" else 40*weight
    base_period_hours = 24
    ml_per_hr_ajustado, ajustes, nivel_riesgo = ajustar_fluido(base_ml, base_period_hours, weight, diuresis, fc, tlc, pa, peso_actual, hto)
    ml_per_min_ajustado = ml_per_hr_ajustado / 60
    ml_per_kg_per_hr_ajustado = ml_per_hr_ajustado / peso_actual
    drops_per_min_ajustado = ml_per_min_ajustado * 20
    sec_per_drop_ajustado = 1.0 / (drops_per_min_ajustado/60)

    st.session_state.reeval_history = pd.concat([
        st.session_state.reeval_history,
        pd.DataFrame([{
            "Hora": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S"),
            "Diuresis": diuresis,
            "FC": fc,
            "TLC": tlc,
            "Mucosas": mucosas,
            "PA": pa,
            "Peso": peso_actual,
            "Hto": hto,
            "ml/kg/h ajustado": ml_per_kg_per_hr_ajustado,
            "gtt/min ajustado": drops_per_min_ajustado,
            "seg/gota ajustado": sec_per_drop_ajustado,
            "Recomendación": "; ".join(ajustes) if ajustes else "Mantener plan",
            "Nivel riesgo": nivel_riesgo
        }])
    ], ignore_index=True)

    st.success("Reevaluación registrada y plan ajustado automáticamente")
    st.info(f"Ajustes: {'; '.join(ajustes) if ajustes else 'Mantener plan actual'}")

# ---------- Mostrar historial con colores ----------
st.subheader("Historial de reevaluaciones")
if not st.session_state.reeval_history.empty:
    def color_riesgo(val):
        if val == "Crítico": return 'background-color: #b00020; color:white'
        if val == "Alerta": return 'background-color: #ff6f00; color:white'
        return ''
    st.dataframe(st.session_state.reeval_history.style.applymap(color_riesgo, subset=["Nivel riesgo"]))

    # ---------- Gráficas interactivas ----------
    hist = st.session_state.reeval_history.copy()
    hist["Hora"] = pd.to_datetime(hist["Hora"])
    
    st.subheader("Gráficas de tendencias")
    st.line_chart(hist.set_index("Hora")[["ml/kg/h ajustado", "Diuresis"]])
    st.line_chart(hist.set_index("Hora")[["Peso", "Hto"]])

    # ---------- Exportar PDF ----------
    def generar_pdf(hist):
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", "B", 16)
        pdf.cell(0, 10, "Resumen de Reevaluaciones - Fluidoterapia", ln=True, align="C")
        pdf.ln(5)
        pdf.set_font("Arial", "", 12)
        for i, row in hist.iterrows():
            pdf.multi_cell(0, 6,
                f"Hora: {row['Hora']}\n"
                f"Diuresis: {row['Diuresis']} mL/kg/h | FC: {row['FC']} lpm | TLC: {row['TLC']} s\n"
                f"Mucosas: {row['Mucosas']} | PA: {row['PA']} mmHg | Peso: {row['Peso']} kg | Hto: {row['Hto']}%\n"
                f"ml/kg/h ajustado: {row['ml/kg/h ajustado']:.2f} | gtt/min: {row['gtt/min ajustado']:.1f} | seg/gota: {row['seg/gota ajustado']:.2f}\n"
                f"Recomendación: {row['Recomendación']} | Nivel riesgo: {row['Nivel riesgo']}\n\n"
            )
        buffer = BytesIO()
        pdf.output(buffer)
        buffer.seek(0)
        return buffer

    pdf_file = generar_pdf(hist)
    st.download_button(
        "📄 Descargar PDF con historial y ajustes",
        pdf_file,
        file_name="reevaluaciones_fluidoterapia.pdf",
        mime="application/pdf"
    )
else:
    st.info("Registra al menos una reevaluación para ver gráficas y generar PDF.")
