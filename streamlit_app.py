"""Calculadora orientativa de fluidoterapia para caninos y felinos.

La aplicación separa mantenimiento, reposición del déficit y pérdidas
continuadas para que puedan pautarse con soluciones distintas si procede.
"""

from __future__ import annotations

import pandas as pd
import streamlit as st


st.set_page_config(
    page_title="Calculadora de Fluidoterapia — AAHA 2024",
    page_icon="💧",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
      .block-container { max-width: 1300px; padding-top: 2.2rem; padding-bottom: 3rem; }
      h1 { letter-spacing: -0.04em; margin-bottom: 0.2rem; }
      [data-testid="stMetric"] {
          background: #ffffff; border: 1px solid #dbe4ef; border-radius: 14px;
          padding: 1rem 1.1rem; min-height: 128px;
      }
      [data-testid="stMetricLabel"] { color: #334155; font-weight: 650; }
      [data-testid="stMetricValue"] { color: #0f172a; }
      .component-note {
          border-left: 4px solid #0ea5e9; background: #f0f9ff; color: #0f172a;
          padding: 0.85rem 1rem; border-radius: 0 10px 10px 0; margin: 0.7rem 0 1rem 0;
      }
      .clinical-note {
          border-left: 4px solid #f59e0b; background: #fffbeb; color: #713f12;
          padding: 0.85rem 1rem; border-radius: 0 10px 10px 0; margin-top: 1rem;
      }
    </style>
    """,
    unsafe_allow_html=True,
)


def calculate_maintenance(species: str, weight: float, method: str, patient_type: str) -> float:
    """Devuelve el mantenimiento estimado en mL/24 h con la fórmula elegida."""
    if method.startswith("60"):
        maintenance = 60 * weight if species == "Canino" else 40 * weight
    elif method.startswith("132"):
        maintenance = 132 * (weight**0.75) if species == "Canino" else 80 * (weight**0.75)
    else:
        maintenance = 30 * weight + 70

    if patient_type == "Pediátrico":
        maintenance *= 3 if species == "Canino" else 2.5
    return maintenance


def calculate_deficit(weight: float, dehydration: float) -> float:
    """Déficit estimado en mL a partir de peso y porcentaje de deshidratación."""
    return (dehydration / 100) * weight * 1000


def format_volume(value: float) -> str:
    return f"{value:,.1f}".replace(",", "X").replace(".", ",").replace("X", ".")


def format_cri_value(value: float) -> str:
    """Muestra hasta seis cifras significativas, sin ceros decimales superfluos."""
    return format(value, ".6g").replace(".", ",")


st.title("💧 Calculadora de Fluidoterapia")
st.caption("AAHA 2024 · Herramienta clínica orientativa para caninos y felinos. La decisión y la reevaluación corresponden al veterinario responsable.")

with st.sidebar:
    st.header("Datos del paciente")
    species = st.selectbox("Especie", ["Canino", "Felino"])
    patient_type = st.selectbox("Tipo de paciente", ["Adulto", "Pediátrico"])
    weight = st.number_input("Peso (kg)", min_value=0.01, value=10.0, format="%.2f")

    plan_type = st.selectbox(
        "Tipo de plan",
        ["Mantenimiento", "Reposición (rehidratación)", "Shock (resucitación)"],
        help="La reposición muestra por separado el déficit y el mantenimiento; shock se presenta como bolos.",
    )

    st.divider()
    st.subheader("Mantenimiento")
    maintenance_method = st.selectbox(
        "Método de cálculo",
        [
            "60 mL/kg/día (Perro) / 40 mL/kg/día (Gato)",
            "132 × BW^0.75 (Perro) / 80 × BW^0.75 (Gato)",
            "30 × BW + 70 (mL/día)",
        ],
    )
    maintenance_window_hours = st.number_input(
        "Ventana del plan de mantenimiento (horas)", min_value=1, max_value=48, value=24
    )

    st.divider()
    st.subheader("Reposición y pérdidas")
    dehydration = st.slider("Deshidratación estimada (%)", 0.0, 30.0, 8.0, step=0.5)
    replacement_hours = st.select_slider(
        "Reponer el déficit en", options=[6, 8, 12, 18, 24, 36, 48], value=24, format_func=lambda value: f"{value} h"
    )
    sensible_losses_daily = st.number_input("Pérdidas sensibles estimadas (mL/24 h)", min_value=0.0, value=0.0)
    insensible_losses_daily = st.number_input("Pérdidas insensibles estimadas (mL/24 h)", min_value=0.0, value=0.0)

    st.divider()
    st.subheader("Bolos y venoclisis")
    bolus_ml_per_kg = st.number_input(
        "Bolo por kg (mL/kg)", min_value=1.0, max_value=50.0,
        value=20.0 if species == "Canino" else 10.0, step=0.5,
    )
    bolus_repeats = st.number_input("Número de bolos", min_value=1, max_value=5, value=1)
    bolus_time_minutes = st.number_input("Duración de cada bolo (min)", min_value=1, max_value=60, value=15)
    venous_set = st.selectbox("Equipo de venoclisis", ["Macrogoteo 20 gtt/mL", "Macrogoteo 10 gtt/mL", "Microgoteo 60 gtt/mL"])

    with st.expander("ℹ️ Métodos de mantenimiento — AAHA 2024"):
        st.markdown(
            """
            **Adultos — AAHA 2024**

            - **Perro:** 60 mL/kg/día
            - **Gato:** 40 mL/kg/día
            - **Perro:** 132 × BW<sup>0,75</sup> mL/día
            - **Gato:** 80 × BW<sup>0,75</sup> mL/día
            - **Perro y gato:** 30 × BW (kg) + 70 mL/día *(estimación rápida)*

            **Pediatría — Tabla 9 (AAHA)**

            - 🐶 Cachorro: **3 × dosis adulta**
            - 🐱 Gatito: **2,5 × dosis adulta**
            - Administrar como mantenimiento durante **24 h** y ajustar según el paciente.

            La reposición del déficit, las pérdidas continuadas, los bolos y la elección de solución requieren reevaluación clínica.
            [Consultar la Tabla 9 de AAHA](https://www.aaha.org/resources/2024-aaha-fluid-therapy-guidelines-for-dogs-and-cats/section-3-fluids-for-replacement-and-maintenance/)
            """,
            unsafe_allow_html=True,
        )


drop_factor = 20 if "20" in venous_set else 10 if "10" in venous_set else 60
maintenance_daily = calculate_maintenance(species, weight, maintenance_method, patient_type)
maintenance_rate = maintenance_daily / 24
deficit_ml = calculate_deficit(weight, dehydration)
losses_daily = sensible_losses_daily + insensible_losses_daily
losses_rate = losses_daily / 24

if plan_type == "Reposición (rehidratación)":
    plan_hours = float(replacement_hours)
elif plan_type == "Mantenimiento":
    plan_hours = float(maintenance_window_hours)
else:
    plan_hours = float(bolus_time_minutes * int(bolus_repeats) / 60)

replacement_rate = deficit_ml / float(replacement_hours)
replacement_plan_ml = deficit_ml

# Para que el total combinado sea coherente, todos sus componentes usan la
# misma ventana: la elegida para reponer el déficit.
combined_hours = float(replacement_hours)
combined_maintenance_ml = maintenance_rate * combined_hours
combined_losses_ml = losses_rate * combined_hours
combined_plan_ml = combined_maintenance_ml + replacement_plan_ml + combined_losses_ml
combined_rate = maintenance_rate + replacement_rate + losses_rate

# Los bolos se calculan y muestran siempre como una intervención separada.
# No se incorporan al total de mantenimiento/rehidratación.
single_bolus_ml = bolus_ml_per_kg * weight
bolus_total_ml = single_bolus_ml * int(bolus_repeats)
single_bolus_hours = float(bolus_time_minutes) / 60
single_bolus_rate = single_bolus_ml / single_bolus_hours
single_bolus_gtt_minute = (single_bolus_rate / 60) * drop_factor
bolus_seconds_per_drop = 60 / single_bolus_gtt_minute if single_bolus_gtt_minute > 0 else None

if plan_type == "Shock (resucitación)":
    bolus_rate = bolus_total_ml / plan_hours
    title = "Plan de resucitación: bolos"
    included_components = "Los bolos se administran y reevaluan aparte. El total combinado continuo se muestra como referencia y no incluye los bolos."
elif plan_type == "Mantenimiento":
    title = f"Plan de mantenimiento · {int(plan_hours)} h"
    included_components = f"El total combinado muestra mantenimiento + déficit + pérdidas durante {int(combined_hours)} h. Decide clínicamente qué componentes pautar."
else:
    title = f"Plan combinado de rehidratación · {int(plan_hours)} h"
    included_components = "El total combinado incluye mantenimiento, reposición de déficit y pérdidas continuadas en la misma ventana temporal."

total_ml_per_kg_hour = combined_rate / weight
total_gtt_minute = (combined_rate / 60) * drop_factor
seconds_per_drop = 60 / total_gtt_minute if total_gtt_minute > 0 else None

st.subheader(title)
st.markdown(f'<div class="component-note">{included_components}</div>', unsafe_allow_html=True)

component_columns = st.columns(4)
component_columns[0].metric(
    "Mantenimiento",
    f"{format_volume(combined_maintenance_ml)} mL",
    f"{format_volume(maintenance_rate)} mL/h · {format_volume(maintenance_daily)} mL/24 h",
)
component_columns[1].metric(
    "Reposición de déficit",
    f"{format_volume(replacement_plan_ml)} mL",
    f"{format_volume(replacement_rate)} mL/h · en {replacement_hours} h",
)
component_columns[2].metric(
    "Pérdidas continuadas",
    f"{format_volume(combined_losses_ml)} mL",
    f"{format_volume(losses_rate)} mL/h · {format_volume(losses_daily)} mL/24 h",
)
component_columns[3].metric(
    "Total combinado",
    f"{format_volume(combined_plan_ml)} mL",
    f"{format_volume(combined_rate)} mL/h · en {replacement_hours} h",
)

if plan_type == "Shock (resucitación)":
    st.info(f"Bolo acumulado: {format_volume(bolus_total_ml)} mL en {format_volume(plan_hours)} h ({format_volume(bolus_rate)} mL/h).")

st.subheader("Velocidades y administración")
detail_columns = st.columns(4)
detail_columns[0].metric("Mantenimiento", f"{format_volume(maintenance_rate)} mL/h")
detail_columns[1].metric("Reposición", f"{format_volume(replacement_rate)} mL/h")
detail_columns[2].metric("Total combinado", f"{format_volume(combined_rate)} mL/h")
detail_columns[3].metric("Velocidad de goteo", f"{format_volume(total_gtt_minute)} gtt/min")

st.subheader("Bolos de resucitación")
st.caption("Se calculan aparte y no se suman al plan de mantenimiento o rehidratación. Reevaluar tras cada bolo antes de repetirlo.")
bolus_columns = st.columns(4)
bolus_columns[0].metric("Bolo individual", f"{format_volume(single_bolus_ml)} mL", f"{format_volume(bolus_ml_per_kg)} mL/kg")
bolus_columns[1].metric("Número de bolos", f"{int(bolus_repeats)}", f"Total: {format_volume(bolus_total_ml)} mL")
bolus_columns[2].metric("Velocidad por bolo", f"{format_volume(single_bolus_rate)} mL/h", f"Durante {int(bolus_time_minutes)} min")
bolus_columns[3].metric("Goteo por bolo", f"{format_volume(single_bolus_gtt_minute)} gtt/min", f"{format_volume(bolus_seconds_per_drop)} s/gota")

with st.expander("Ver detalle técnico", expanded=False):
    table = pd.DataFrame(
        [
            {"Componente": "Mantenimiento", "Volumen en el plan (mL)": combined_maintenance_ml, "Velocidad (mL/h)": maintenance_rate, "Destino sugerido": "Solución de mantenimiento, si procede"},
            {"Componente": "Reposición del déficit", "Volumen en el plan (mL)": replacement_plan_ml, "Velocidad (mL/h)": replacement_rate, "Destino sugerido": "Solución de reposición, si procede"},
            {"Componente": "Pérdidas continuadas", "Volumen en el plan (mL)": combined_losses_ml, "Velocidad (mL/h)": losses_rate, "Destino sugerido": "Según pérdidas medidas/estimadas"},
            {"Componente": "Total combinado", "Volumen en el plan (mL)": combined_plan_ml, "Velocidad (mL/h)": combined_rate, "Destino sugerido": "Suma de mantenimiento, déficit y pérdidas"},
            {"Componente": "Bolo de resucitación (aparte)", "Volumen en el plan (mL)": single_bolus_ml, "Velocidad (mL/h)": single_bolus_rate, "Destino sugerido": "No incluido en el total; reevaluar antes de repetir"},
        ]
    )
    st.dataframe(
        table.style.format({"Volumen en el plan (mL)": "{:.1f}", "Velocidad (mL/h)": "{:.1f}"}),
        width="stretch",
        hide_index=True,
    )
    st.markdown(f"- **Total:** {format_volume(total_ml_per_kg_hour)} mL/kg/h")
    st.markdown(f"- **Equipo:** {drop_factor} gtt/mL · **goteo total:** {format_volume(total_gtt_minute)} gtt/min")
    st.markdown(f"- **Segundos por gota:** {format_volume(seconds_per_drop)}" if seconds_per_drop else "- **Segundos por gota:** no aplicable")

warnings = []
if patient_type == "Pediátrico" and weight > 10:
    warnings.append("Paciente marcado como pediátrico con peso elevado: confirmar edad, estado y pauta.")
if plan_type != "Shock (resucitación)":
    reference_rate = 5 if species == "Canino" else 4
    if total_ml_per_kg_hour > reference_rate:
        warnings.append("La tasa total es elevada: reevaluar perfusión, pérdidas, comorbilidades y objetivo clínico.")
if plan_type == "Mantenimiento" and dehydration > 0:
    warnings.append("El total combinado incluye el déficit como referencia; confirma si la reposición está indicada para este paciente.")

if warnings:
    st.subheader("Avisos clínicos")
    for warning in warnings:
        st.warning(warning)

st.markdown(
    "<div class='clinical-note'><strong>Uso clínico:</strong> esta herramienta no sustituye la valoración del paciente ni la monitorización. Ajusta el plan según perfusión, diuresis, electrolitos, glucemia, pérdidas y respuesta a la fluidoterapia.</div>",
    unsafe_allow_html=True,
)

if "reeval_history" not in st.session_state:
    st.session_state.reeval_history = []

with st.expander("Historial de reevaluaciones", expanded=False):
    if st.session_state.reeval_history:
        st.dataframe(pd.DataFrame(st.session_state.reeval_history), width="stretch", hide_index=True)
    else:
        st.caption("Todavía no hay reevaluaciones registradas en esta sesión.")

st.divider()
st.header("Cálculo de CRI")
st.caption(
    "Calcula por separado el volumen de varios fármacos para sus respectivas CRI, "
    "eligiendo el volumen final o el ritmo en mL/h. Introduce las dosis prescritas."
)

with st.container(border=True):
    st.markdown("**Fórmula**")
    st.latex(
        r"\text{Cantidad de fármaco (mL)} = "
        r"\frac{\text{Dosis (unidad/kg/h)} \times \text{Peso (kg)} \times "
        r"\text{Duración (h)}}{\text{Concentración (misma unidad/mL)}}"
    )
    st.caption(
        "Cada medicamento se calcula por separado. Puedes indicar el volumen final o el ritmo "
        "deseado; con la duración se calcula el otro. Si indicas ambos, deben coincidir. "
        "El diluyente es el volumen final menos el volumen del medicamento. La dosis y la concentración deben "
        "pertenecer a la misma familia: masa con masa o UI con UI. Las UI no se convierten "
        "a mg porque la equivalencia depende del medicamento."
    )

st.caption(f"Peso aplicado a todos los cálculos: **{weight:.2f} kg** (tomado de Datos del paciente).")
if "cri_medications_v3" not in st.session_state:
    st.session_state.cri_medications_v3 = pd.DataFrame(
        [{
            "Medicamento": "",
            "Dosis prescrita (mg/kg/h)": 0.0,
            "Unidad dosis": "mg/kg/h",
            "Duración (h)": 0.0,
            "Concentración": 0.0,
            "Unidad concentración": "mg/mL",
            "Ritmo objetivo (mL/h)": 0.0,
            "Volumen final deseado (mL)": 0.0,
        }]
    )

cri_inputs = st.data_editor(
    st.session_state.cri_medications_v3,
    key="cri_medications_editor_v3",
    num_rows="dynamic",
    hide_index=True,
    width="stretch",
    column_config={
        "Medicamento": st.column_config.TextColumn(
            "Medicamento",
            width=120,
            help="Nombre para identificar el fármaco; no se sugieren medicamentos.",
        ),
        "Dosis prescrita (mg/kg/h)": st.column_config.NumberColumn(
            "Dosis", width=80, min_value=0.0, step=0.01, format="%.6g"
        ),
        "Unidad dosis": st.column_config.SelectboxColumn(
            "Unidad dosis", width=95,
            options=["µg/kg/h", "mg/kg/h", "g/kg/h", "UI/kg/h"],
            default="mg/kg/h",
        ),
        "Duración (h)": st.column_config.NumberColumn(
            "Duración (h)", width=85, min_value=0.0, step=0.5, format="%.6g"
        ),
        "Concentración": st.column_config.NumberColumn(
            "Conc.", width=80, min_value=0.0, step=0.1, format="%.6g"
        ),
        "Unidad concentración": st.column_config.SelectboxColumn(
            "Unidad conc.", width=95,
            options=["µg/mL", "mg/mL", "g/mL", "UI/mL"],
            default="mg/mL",
        ),
        "Ritmo objetivo (mL/h)": st.column_config.NumberColumn(
            "Ritmo mL/h",
            width=90,
            min_value=0.0,
            step=0.1,
            format="%.6g",
            help="Opcional. Si lo indicas, se calcula el volumen final como ritmo × duración.",
        ),
        "Volumen final deseado (mL)": st.column_config.NumberColumn(
            "Vol. final mL",
            width=100,
            min_value=0.0,
            step=1.0,
            format="%.6g",
            help="Opcional si indicas ritmo. Si ambos están llenos, deben ser coherentes con la duración.",
        ),
    },
)

cri_results = []
cri_errors = []
for row_number, row in cri_inputs.iterrows():
    name = str(row.get("Medicamento", "")).strip()
    dose = row.get("Dosis prescrita (mg/kg/h)")
    dose_unit = row.get("Unidad dosis", "mg/kg/h")
    duration = row.get("Duración (h)")
    concentration = row.get("Concentración")
    concentration_unit = row.get("Unidad concentración", "mg/mL")
    target_rate = row.get("Ritmo objetivo (mL/h)")
    final_volume = row.get("Volumen final deseado (mL)")

    # Ignora filas vacías que quedan disponibles para añadir otro medicamento.
    values = (dose, duration, concentration, target_rate, final_volume)
    if not name and all(pd.isna(value) or value == 0 for value in values):
        continue

    row_label = name or f"Fila {row_number + 1}"
    if not name:
        cri_errors.append(f"Fila {row_number + 1}: indica el nombre del medicamento.")
        continue
    if pd.isna(dose) or dose <= 0:
        cri_errors.append(f"{row_label}: la dosis debe ser mayor que 0 {dose_unit}.")
        continue
    if pd.isna(duration) or duration <= 0:
        cri_errors.append(f"{row_label}: la duración debe ser mayor que 0 h.")
        continue
    if pd.isna(concentration) or concentration <= 0:
        cri_errors.append(f"{row_label}: la concentración debe ser mayor que 0.")
        continue
    has_target_rate = not pd.isna(target_rate) and target_rate > 0
    has_final_volume = not pd.isna(final_volume) and final_volume > 0
    if not has_target_rate and not has_final_volume:
        cri_errors.append(
            f"{row_label}: indica un volumen final mayor que 0 mL o un ritmo objetivo mayor que 0 mL/h."
        )
        continue

    dose_is_ui = dose_unit.startswith("UI/")
    concentration_is_ui = concentration_unit.startswith("UI/")
    if dose_is_ui != concentration_is_ui:
        cri_errors.append(
            f"{row_label}: las unidades no coinciden. Una dosis en UI/kg/h requiere "
            "concentración en UI/mL; las dosis de masa requieren una concentración de masa."
        )
        continue

    mass_to_mg = {"µg/kg/h": 0.001, "mg/kg/h": 1.0, "g/kg/h": 1000.0}
    concentration_to_mg = {"µg/mL": 0.001, "mg/mL": 1.0, "g/mL": 1000.0}
    if dose_is_ui:
        dose_base = float(dose)
        concentration_base = float(concentration)
    else:
        dose_base = float(dose) * mass_to_mg[dose_unit]
        concentration_base = float(concentration) * concentration_to_mg[concentration_unit]

    medication_volume_ml = (dose_base * weight * float(duration)) / concentration_base
    if has_target_rate:
        calculated_final_volume = float(target_rate) * float(duration)
        if has_final_volume and abs(float(final_volume) - calculated_final_volume) > 0.01:
            cri_errors.append(
                f"{row_label}: el ritmo {format_cri_value(float(target_rate))} mL/h durante "
                f"{format_cri_value(float(duration))} h corresponde a "
                f"{format_cri_value(calculated_final_volume)} mL, no a "
                f"{format_cri_value(float(final_volume))} mL. Ajusta uno de los dos valores."
            )
            continue
        calculated_rate = float(target_rate)
    else:
        calculated_final_volume = float(final_volume)
        calculated_rate = calculated_final_volume / float(duration)

    if calculated_final_volume < medication_volume_ml:
        cri_errors.append(
            f"{row_label}: el volumen final ({format_cri_value(calculated_final_volume)} mL) "
            f"no puede ser menor que el volumen del medicamento "
            f"({format_cri_value(medication_volume_ml)} mL)."
        )
        continue
    diluent_volume_ml = calculated_final_volume - medication_volume_ml
    cri_results.append(
        {
            "Medicamento": name,
            "Dosis prescrita": f"{format_cri_value(float(dose))} {dose_unit}",
            "Concentración": f"{format_cri_value(float(concentration))} {concentration_unit}",
            "Medicamento a extraer (mL)": medication_volume_ml,
            "Diluyente a añadir (mL)": diluent_volume_ml,
            "Volumen final (mL)": calculated_final_volume,
            "Ritmo de infusión (mL/h)": calculated_rate,
        }
    )

for error in cri_errors:
    st.error(error)

if cri_results:
    st.subheader("Resultados por medicamento")
    st.dataframe(
        pd.DataFrame(cri_results).style.format(
            {
                "Medicamento a extraer (mL)": format_cri_value,
                "Diluyente a añadir (mL)": format_cri_value,
                "Volumen final (mL)": format_cri_value,
                "Ritmo de infusión (mL/h)": format_cri_value,
            }
        ),
        width="stretch",
        hide_index=True,
    )
elif not cri_errors:
    st.info("Añade una fila e introduce medicamento, dosis, duración y concentración; después elige volumen final o ritmo en mL/h.")

st.caption(
    "El ritmo mostrado corresponde solo a esa preparación de CRI; ten en cuenta los demás fluidos "
    "administrados al valorar el aporte total. El diluyente se calcula como volumen final menos "
    "volumen del medicamento. La app no calcula el aporte combinado de otros fluidos ni confirma "
    "compatibilidad o estabilidad. Verifica siempre "
    "las unidades y la preparación prescrita. Los valores se redondean solo para mostrarse."
)
