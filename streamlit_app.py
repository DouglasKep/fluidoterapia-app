# app.py
import streamlit as st
import pandas as pd

# ---------- Configuración ----------
st.set_page_config(page_title="Calculadora de Fluidoterapia — AAHA (ES)", layout="wide")

# ---------- Estilos ----------
st.markdown("""
<style>
.main .block-container { background-color: rgba(255,255,255,0.96); padding: 1rem 1.25rem; }
h1 { margin-bottom: 0.25rem; }
.small-note { font-size: 0.9rem; color: #444; }
.alert { color: #b00020; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

st.title("Calculadora de Fluidoterapia — Basada en AAHA 2024")
st.caption("Guía clínica para planificación de terapia de fluidos en caninos y felinos. Esto es una ayuda; la decisión clínica es responsabilidad del veterinario.")

# ---------- Entradas (sidebar) ----------
with st.sidebar.expander("Datos del paciente", expanded=True):
    species = st.selectbox("Especie", ["Canino", "Felino"])
    weight = st.number_input("Peso (kg)", min_value=0.01, value=10.0, format="%.2f")
    state = st.selectbox("Estado clínico", ["Mantenimiento", "Reposición (rehidratación)", "Shock (resucitación)"])
    dehydration = st.slider("Grado estimado de deshidratación (%)", 0.0, 30.0, 8.0, step=0.5)
    sens_loss = st.number_input("Pérdidas sensibles (mL/día) — p.ej. vómito/diarrea", min_value=0.0, value=0.0, format="%.1f")
    insens_loss = st.number_input("Pérdidas insensibles (mL/día) — p.ej. respiración, temperatura", min_value=0.0, value=0.0, format="%.1f")

with st.sidebar.expander("Mantenimiento (métodos AAHA)", expanded=False):
    maint_method = st.selectbox("Método de cálculo del mantenimiento",
                                [
                                    "60 mL/kg/día (Perro) / 40 mL/kg/día (Gato)",
                                    "132 × BW^0.75 (Perro) / 80 × BW^0.75 (Gato)",
                                    "30 × BW + 70 (mL/día)"
                                ])
    maint_period_hours = st.number_input("Periodo para administrar mantenimiento (horas)", min_value=1, max_value=48, value=24)

with st.sidebar.expander("Bolos (Resucitación)", expanded=False):
    default_bolus = 20.0 if species == "Canino" else 10.0
    bolus_ml_per_kg = st.number_input("Bolo (mL/kg) — valor por bolo", min_value=1.0, max_value=50.0, value=float(default_bolus), step=0.5)
    bolus_repeats = st.number_input("Número de bolos a administrar", min_value=1, max_value=5, value=1, step=1)
    bolus_time_min = st.number_input("Duración de cada bolo (min)", min_value=1, max_value=60, value=15, step=1)

with st.sidebar.expander("Venoclisis y goteo", expanded=False):
    venous_set = st.selectbox("Tipo de venoclisis", ["Macrogoteo 20 gtt/mL", "Macrogoteo 10 gtt/mL", "Microgoteo 60 gtt/mL"])
    drop_factor = 20 if "20" in venous_set else (10 if "10" in venous_set else 60)

with st.sidebar.expander("Rehidratación (tiempo de reposición)", expanded=False):
    reh_time_hours = st.slider("Tiempo para rehidratación (horas)", min_value=6, max_value=48, value=24)

# ---------- Validaciones ----------
errors = []
if weight <= 0: errors.append("El peso debe ser mayor que 0 kg.")
if state == "Reposición (rehidratación)" and reh_time_hours <= 0: errors.append("El tiempo de rehidratación debe ser mayor que 0 horas.")
if maint_period_hours <= 0: errors.append("El periodo de mantenimiento debe ser mayor que 0 horas.")
if state == "Shock (resucitación)" and bolus_time_min <= 0: errors.append("La duración del bolo debe ser mayor que 0 minutos.")
if errors:
    for e in errors: st.error(e)
    st.stop()

# ---------- Funciones de cálculo ----------
def calcular_mantenimiento(species, weight, method):
    if method.startswith("60 mL/kg"):
        return (60.0 * weight) if species == "Canino" else (40.0 * weight)
    elif method.startswith("132"):
        return 132.0 * (weight ** 0.75) if species == "Canino" else 80.0 * (weight ** 0.75)
    else:
        return 30.0 * weight + 70.0

def calcular_deficit(weight, dehydration_percent):
    return (dehydration_percent / 100.0) * weight * 1000.0  # mL

mantenimiento_ml_dia = calcular_mantenimiento(species, weight, maint_method)
deficit_ml = calcular_deficit(weight, dehydration)

# ---------- Determinar volumen base y periodo ----------
if state == "Mantenimiento":
    base_ml = mantenimiento_ml_dia
    base_period_hours = maint_period_hours
elif state == "Reposición (rehidratación)":
    mantenimiento_para_periodo = mantenimiento_ml_dia * (reh_time_hours / 24.0)
    base_ml = mantenimiento_para_periodo + deficit_ml
    base_period_hours = reh_time_hours
else:  # Shock
    bolo_total_ml = bolus_ml_per_kg * weight * bolus_repeats
    base_ml = bolo_total_ml
    base_period_hours = (bolus_time_min / 60.0) * bolus_repeats

vol_total_ml = base_ml + sens_loss + insens_loss

ml_per_hr = vol_total_ml / base_period_hours
ml_per_min = ml_per_hr / 60.0
ml_per_kg_per_hr = ml_per_hr / weight
ml_per_kg_per_day = ml_per_kg_per_hr * 24.0
drops_per_min = ml_per_min * drop_factor
drops_per_sec = drops_per_min / 60.0
sec_per_drop = 1.0 / drops_per_sec if drops_per_sec > 0 else None

# ---------- Avisos clínicos ----------
warnings = []
if state != "Shock (resucitación)":
    thr = 5.0 if species=="Canino" else 4.0
    if ml_per_kg_per_hr > thr:
        warnings.append(f"Precaución: la tasa calculada (~{ml_per_kg_per_hr:.2f} mL/kg/h) excede rango esperado para mantenimiento/rehidratación.")

if state == "Shock (resucitación)":
    if bolus_time_min > 30: warnings.append("AAHA sugiere bolos rápidos (p.ej. 15 min).")
    if bolus_ml_per_kg > 30: warnings.append("Bolos >30 mL/kg son inusuales; revisar indicación y monitorización estricta.")

if sec_per_drop is not None and sec_per_drop < 0.2:
    warnings.append("Goteo extremadamente rápido (intervalo <0.2 s/gota). Verificar equipo o usar microgoteo/bomba.")

# ---------- Resultados ----------
st.header("Resultados clínicos")
col1, col2, col3 = st.columns([1.2,1,1])
col1.metric("Mantenimiento (mL/día)", f"{mantenimiento_ml_dia:.1f}")
col2.metric("Déficit (mL)", f"{deficit_ml:.1f}")
col3.metric("Volumen total planificado (mL)", f"{vol_total_ml:.1f}")

st.subheader("Detalle técnico")
with st.expander("Tasas y goteo"):
    st.markdown(f"- **ml/h:** {ml_per_hr:.1f}")
    st.markdown(f"- **ml/min:** {ml_per_min:.3f}")
    st.markdown(f"- **ml/kg/h:** {ml_per_kg_per_hr:.3f}")
    st.markdown(f"- **ml/kg/día:** {ml_per_kg_per_day:.1f}")
    st.markdown(f"- **gtt/min:** {drops_per_min:.1f}")
    st.markdown(f"- **seg/gota:** {sec_per_drop:.2f}" if sec_per_drop else "-")

if warnings:
    st.subheader("Avisos clínicos")
    for w in warnings:
        st.warning(w)

# ---------- Resumen clínico ----------
st.markdown("---")
st.markdown(
    "**Observaciones clínicas:**\n\n"
    "- Valores orientativos según guías AAHA 2024. Ajustar según perfusión, FR, PA, diuresis, peso y hallazgos clínicos.\n"
    "- En shock: administre bolos y reevalúe tras cada bolo. En rehidratación, distribuya déficit
