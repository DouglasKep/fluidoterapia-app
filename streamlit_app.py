# app.py
import streamlit as st
import pandas as pd

# ---------------- CONFIG ----------------
st.set_page_config(
    page_title="Calculadora de Fluidoterapia — AAHA (ES)",
    layout="wide"
)

# ---------------- ESTILOS ----------------
st.markdown("""
<style>
.main .block-container {
    background-color: rgba(255,255,255,0.96);
    padding: 1rem 1.25rem;
}
h1 { margin-bottom: 0.25rem; }
</style>
""", unsafe_allow_html=True)

# ---------------- TÍTULO ----------------
st.title("Calculadora de Fluidoterapia — Basada en AAHA 2024")
st.caption(
    "Guía clínica orientativa para caninos y felinos. "
    "La decisión final es responsabilidad del veterinario."
)

# ---------------- SIDEBAR: DATOS ----------------
with st.sidebar.expander("Datos del paciente", expanded=True):
    species = st.selectbox("Especie", ["Canino", "Felino"])
    weight = st.number_input("Peso (kg)", min_value=0.01, value=10.0, format="%.2f")
    state = st.selectbox(
        "Estado clínico",
        ["Mantenimiento", "Reposición (rehidratación)", "Shock (resucitación)"]
    )
    dehydration = st.slider(
        "Grado estimado de deshidratación (%)",
        0.0, 30.0, 8.0, step=0.5
    )
    sens_loss = st.number_input(
        "Pérdidas sensibles (mL/día)",
        min_value=0.0, value=0.0
    )
    insens_loss = st.number_input(
        "Pérdidas insensibles (mL/día)",
        min_value=0.0, value=0.0
    )

# ---------------- MANTENIMIENTO ----------------
with st.sidebar.expander("Mantenimiento (AAHA)", expanded=False):

    maint_method = st.selectbox(
        "Método de cálculo del mantenimiento",
        [
            "60 mL/kg/día (Perro) / 40 mL/kg/día (Gato)",
            "132 × BW^0.75 (Perro) / 80 × BW^0.75 (Gato)",
            "30 × BW + 70 (mL/día)"
        ]
    )

    maint_period_hours = st.number_input(
        "Periodo de administración (horas)",
        min_value=1,
        max_value=48,
        value=24
    )

    # ---------- AYUDA PARA ELEGIR EL MÉTODO ----------
    with st.expander("ℹ️ ¿Cómo elegir el método?"):
        st.markdown("""
        **60 mL/kg/día (perros) / 40 mL/kg/día (gatos)**  
        Método clínico estándar recomendado por AAHA.  
        ✔ Pacientes estables  
        ✔ Hospitalización general  

        **132 × BW⁰·⁷⁵ (perros) / 80 × BW⁰·⁷⁵ (gatos)**  
        Basado en requerimientos metabólicos (RER).  
        ✔ Pacientes muy pequeños o muy grandes  
        ✔ UCI o pacientes críticos  

        **30 × BW + 70**  
        Regla empírica de cálculo rápido.  
        ✔ Estimación inicial  
        ⚠️ Menor precisión en extremos de peso  
        """)

    # ---------- MENSAJE CONTEXTUAL ----------
    if maint_method.startswith("60"):
        st.info("Método estándar recomendado para la mayoría de pacientes clínicamente estables.")
    elif maint_method.startswith("132"):
        st.info("Método metabólico. Útil en pacientes críticos o con peso extremo.")
    else:
        st.info("Regla empírica rápida. Útil como orientación inicial.")

# ---------------- BOLOS ----------------
with st.sidebar.expander("Bolos (Resucitación)", expanded=False):
    if "bolus_default" not in st.session_state:
        st.session_state.bolus_default = 20.0 if species == "Canino" else 10.0

    bolus_ml_per_kg = st.number_input(
        "Bolo por kg (mL/kg)",
        min_value=1.0, max_value=50.0,
        value=st.session_state.bolus_default,
        step=0.5
    )
    bolus_repeats = st.number_input(
        "Número de bolos",
        min_value=1, max_value=5, value=1
    )
    bolus_time_min = st.number_input(
        "Duración de cada bolo (min)",
        min_value=1, max_value=60, value=15
    )

# ---------------- GOTEOS ----------------
with st.sidebar.expander("Venoclisis y goteo", expanded=False):
    venous_set = st.selectbox(
        "Tipo de equipo",
        ["Macrogoteo 20 gtt/mL", "Macrogoteo 10 gtt/mL", "Microgoteo 60 gtt/mL"]
    )
    drop_factor = 20 if "20" in venous_set else (10 if "10" in venous_set else 60)

# ---------------- REHIDRATACIÓN ----------------
with st.sidebar.expander("Tiempo de rehidratación", expanded=False):
    reh_time_hours = st.slider("Horas", 6, 48, 24)

# ---------------- VALIDACIONES ----------------
errors = []

if weight <= 0:
    errors.append("El peso debe ser mayor que 0 kg.")
if maint_period_hours <= 0:
    errors.append("El periodo de mantenimiento debe ser mayor que 0.")
if state == "Reposición (rehidratación)" and reh_time_hours <= 0:
    errors.append("El tiempo de rehidratación debe ser válido.")

if errors:
    for e in errors:
        st.error(e)
    st.stop()

# ---------------- FUNCIONES ----------------
def calcular_mantenimiento(species, weight, method):
    if method.startswith("60"):
        return 60 * weight if species == "Canino" else 40 * weight
    elif method.startswith("132"):
        return 132 * (weight ** 0.75) if species == "Canino" else 80 * (weight ** 0.75)
    else:
        return 30 * weight + 70

def calcular_deficit(weight, dehydration):
    return (dehydration / 100) * weight * 1000

# ---------------- CÁLCULOS ----------------
mantenimiento_ml_dia = calcular_mantenimiento(species, weight, maint_method)
deficit_ml = calcular_deficit(weight, dehydration)

if state == "Mantenimiento":
    base_ml = mantenimiento_ml_dia
    base_hours = maint_period_hours

elif state == "Reposición (rehidratación)":
    base_ml = mantenimiento_ml_dia * (reh_time_hours / 24) + deficit_ml
    base_hours = reh_time_hours

else:
    base_ml = bolus_ml_per_kg * weight * bolus_repeats
    base_hours = (bolus_time_min / 60) * bolus_repeats

vol_total_ml = base_ml + sens_loss + insens_loss

ml_per_hr = vol_total_ml / base_hours
ml_per_min = ml_per_hr / 60
ml_per_kg_hr = ml_per_hr / weight
gtt_min = ml_per_min * drop_factor
gtt_sec = gtt_min / 60
sec_per_drop = 1 / gtt_sec if gtt_sec > 0 else None

# ---------------- RESULTADOS ----------------
st.header("Resultados clínicos")

c1, c2, c3 = st.columns(3)
c1.metric("Mantenimiento (mL/día)", f"{mantenimiento_ml_dia:.1f}")
c2.metric("Déficit (mL)", f"{deficit_ml:.1f}")
c3.metric("Volumen total (mL)", f"{vol_total_ml:.1f}")

with st.expander("Detalle técnico"):
    st.markdown(f"- **mL/h:** {ml_per_hr:.1f}")
    st.markdown(f"- **mL/kg/h:** {ml_per_kg_hr:.2f}")
    st.markdown(f"- **gtt/min:** {gtt_min:.1f}")
    if sec_per_drop is not None:
        st.markdown(f"- **seg/gota:** {sec_per_drop:.2f}")
    else:
        st.markdown("- **seg/gota:** —")

# ---------------- HISTORIAL ----------------
if "reeval_history" not in st.session_state:
    st.session_state.reeval_history = []

st.subheader("Historial de reevaluaciones")
st.dataframe(pd.DataFrame(st.session_state.reeval_history))
