"""Calculadora orientativa de fluidoterapia para caninos y felinos.

La aplicación separa mantenimiento, reposición del déficit y pérdidas
continuadas para que puedan pautarse con soluciones distintas si procede.
"""

from __future__ import annotations

import pandas as pd
import streamlit as st
import unicodedata


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


CRI_REFERENCE_SOURCES = {
    "wsava_pain": {
        "title": "WSAVA — 2022 Global Guidelines for the Recognition, Assessment and Treatment of Pain",
        "type": "Guía internacional de consenso",
        "updated": "Guía 2022 · publicada en 2023",
        "url": "https://onlinelibrary.wiley.com/doi/10.1111/jsap.13566",
    },
    "recover_cpr": {
        "title": "RECOVER — 2024 CPR Guidelines for Dogs and Cats",
        "type": "Consenso internacional basado en revisión sistemática y metodología GRADE",
        "updated": "Publicadas en junio de 2024",
        "url": "https://onlinelibrary.wiley.com/doi/10.1111/vec.13391",
    },
    "acvim_mitral": {
        "title": "ACVIM Consensus Statement — Myxomatous Mitral Valve Disease in Dogs",
        "type": "Consenso ACVIM (nivel de evidencia bajo para esta recomendación)",
        "updated": "Publicado en 2019",
        "url": "https://academic.oup.com/jvim/article/33/3/1127/8448111",
    },
    "methadone_review": {
        "title": "Incorporating methadone into companion animal anesthesia and analgesic protocols: A narrative review",
        "type": "Revisión narrativa revisada por pares; no es un consenso",
        "updated": "Publicado en 2023",
        "url": "https://pmc.ncbi.nlm.nih.gov/articles/PMC10581351/",
    },
    "septic_peritonitis_review": {
        "title": "Perioperative management of septic peritonitis in small animals: A review",
        "type": "Revisión clínica revisada por pares; no es un consenso",
        "updated": "Publicado en enero de 2026",
        "url": "https://pmc.ncbi.nlm.nih.gov/articles/PMC12810469/",
    },
    "propofol_spc": {
        "title": "Ficha técnica oficial veterinaria — Propofol 10 mg/mL",
        "type": "Ficha técnica regulatoria de medicamento veterinario",
        "updated": "Revisada en marzo de 2024",
        "url": "https://www.vmd.defra.gov.uk/productinformationdatabase/files/QRD_Documents/QRD-Auth_2543398.PDF",
    },
    "merck_pressors": {
        "title": "Merck Veterinary Manual — Initial Triage and Resuscitation of Small Animal Emergency Patients",
        "type": "Manual clínico de consulta",
        "updated": "Actualizado en abril de 2026",
        "url": "https://www.merckvetmanual.com/emergency-medicine-and-critical-care/evaluation-and-initial-treatment-of-small-animal-emergency-patients/initial-triage-and-resuscitation-of-small-animal-emergency-patients",
    },
    "merck_pressors_es": {
        "title": "Manual de veterinaria de Merck — Triaje inicial y resucitación de urgencia en pequeños animales",
        "type": "Manual clínico de consulta",
        "updated": "Actualizado en abril de 2026",
        "url": "https://www.merckvetmanual.com/es-us/medicina-de-urgencia-y-cuidados-intensivos/evaluaci%C3%B3n-y-tratamiento-inicial-de-pacientes-de-urgencias-en-peque%C3%B1os-animales/triaje-inicial-y-resucitaci%C3%B3n-de-urgencia-en-peque%C3%B1os-animales",
    },
    "merck_analgesics": {
        "title": "Merck Veterinary Manual — Analgesics Used in Animals",
        "type": "Manual clínico de consulta",
        "updated": "Actualizado en septiembre de 2024",
        "url": "https://www.merckvetmanual.com/therapeutics/pain-assessment-and-management/analgesics-used-in-animals",
    },
    "merck_cardio_therapy": {
        "title": "Merck Veterinary Manual — Principles of Therapy of Cardiovascular Disease in Animals",
        "type": "Manual clínico de consulta",
        "updated": "Actualizado en mayo de 2025",
        "url": "https://www.merckvetmanual.com/circulatory-system/cardiovascular-system-introduction/principles-of-therapy-of-cardiovascular-disease-in-animals",
    },
}

# Catálogo inicial de referencias publicadas para CRI en perros y gatos.
# Mantiene el contexto por especie/indicación y no rellena la dosis prescrita.
CRI_DOSE_REFERENCES = [
    {
        "aliases": ["nora", "norepinefrina", "noradrenalina", "noraadrenalina", "norepinephrine", "noradrenaline"],
        "species": "Canino / Felino",
        "regimen": "0,05–2 µg/kg/min IV CRI.",
        "context": "Soporte vasopresor en pacientes pequeños; la fuente indica usar tras valorar/reponer adecuadamente el volumen intravascular, iniciar en el extremo bajo y titular con monitorización de presión y perfusión.",
        "source": "merck_pressors",
    },
    {
        "aliases": ["nora", "norepinefrina", "noradrenalina", "noraadrenalina", "norepinephrine", "noradrenaline"],
        "species": "Canino / Felino",
        "regimen": "0,1–1 µg/kg/min IV CRI.",
        "context": "Referencia para shock séptico asociado a peritonitis séptica, tras reponer el volumen intravascular. La revisión indica que no hay consensos específicos para peritonitis séptica en perros y gatos; no extrapolar este rango a otras causas de shock.",
        "source": "septic_peritonitis_review",
    },
    {
        "aliases": ["dopamina", "dopamine"],
        "species": "Canino / Felino",
        "regimen": "5–20 µg/kg/min IV CRI.",
        "context": "Opción presora para soporte de presión arterial; titular a la respuesta y vigilar perfusión de órganos y arritmias.",
        "source": "merck_pressors",
    },
    {
        "aliases": ["adrenalina", "epinefrina", "epinephrine"],
        "species": "Canino / Felino",
        "regimen": "0,125–2 µg/kg/min IV CRI.",
        "context": "Opción presora en pacientes pequeños; la indicación y titulación dependen del cuadro clínico.",
        "source": "merck_pressors",
    },
    {
        "aliases": ["fenilefrina", "phenylephrine"],
        "species": "Canino / Felino",
        "regimen": "1–3 µg/kg/min IV CRI.",
        "context": "Opción presora en pacientes pequeños; monitorizar presión arterial y perfusión.",
        "source": "merck_pressors",
    },
    {
        "aliases": ["vasopresina", "vasopressina", "vasopressin"],
        "species": "Canino / Felino",
        "regimen": "0,5–5 mUI/kg/min IV CRI.",
        "context": "Opción presora en pacientes pequeños; la fuente informa la dosis en miliunidades.",
        "source": "merck_pressors",
    },
    {
        "aliases": ["dobutamina", "dobutamine"],
        "species": "Canino",
        "regimen": "1–15 µg/kg/min IV CRI.",
        "context": "Referencia para enfermedad cardiovascular; otra referencia de urgencias presenta un rango distinto para hipotensión/shock.",
        "source": "merck_cardio_therapy",
    },
    {
        "aliases": ["dobutamina", "dobutamine"],
        "species": "Felino",
        "regimen": "0,5–5 µg/kg/min IV CRI.",
        "context": "Referencia para enfermedad cardiovascular; otra referencia de urgencias presenta un rango distinto para hipotensión/shock.",
        "source": "merck_cardio_therapy",
    },
    {
        "aliases": ["dobutamina", "dobutamine"],
        "species": "Canino",
        "regimen": "2–20 µg/kg/min IV CRI; dosis inicial indicada: 2–5 µg/kg/min.",
        "context": "Referencia en triaje y soporte de presión arterial para pacientes de urgencias; requiere titulación y monitorización.",
        "source": "merck_pressors",
    },
    {
        "aliases": ["dobutamina", "dobutamine"],
        "species": "Felino",
        "regimen": "1–5 µg/kg/min IV CRI.",
        "context": "Referencia de urgencias para gatos con miocardiopatía dilatada.",
        "source": "merck_pressors_es",
    },
    {
        "aliases": ["furosemida", "furosemide"],
        "species": "Canino",
        "regimen": "0,25–1 mg/kg/h IV CRI.",
        "context": "Referencia de tratamiento agudo de enfermedad cardiovascular; la fuente también describe cargas intermitentes y manejo a largo plazo.",
        "source": "merck_cardio_therapy",
    },
    {
        "aliases": ["furosemida", "furosemide"],
        "species": "Canino",
        "regimen": "Tras carga IV de 2 mg/kg: 0,66–1 mg/kg/h IV CRI hasta que disminuya el distrés respiratorio o por un máximo de 4 h.",
        "context": "Consenso ACVIM para perros con enfermedad mitral en estadio D y fallo cardiaco refractario. La recomendación tiene nivel de evidencia bajo; la carga no se calcula en este apartado.",
        "source": "acvim_mitral",
    },
    {
        "aliases": ["furosemida", "furosemide"],
        "species": "Felino",
        "regimen": "0,25–0,6 mg/kg/h IV CRI.",
        "context": "Referencia de tratamiento agudo de enfermedad cardiovascular; la fuente también describe cargas intermitentes y manejo a largo plazo.",
        "source": "merck_cardio_therapy",
    },
    {
        "aliases": ["nitroprusiato", "nitroprusiato de sodio", "sodium nitroprusside", "nitroprusside"],
        "species": "Canino",
        "regimen": "Inicio: 1 µg/kg/min IV CRI; titular cada 15–30 min hasta 10–15 µg/kg/min como máximo.",
        "context": "Referencia cardiovascular para vasodilatación aguda; la fuente indica no administrar en bolo y limitar el tratamiento a 24–48 h.",
        "source": "merck_cardio_therapy",
    },
    {
        "aliases": ["nitroprusiato", "nitroprusiato de sodio", "sodium nitroprusside", "nitroprusside"],
        "species": "Felino",
        "regimen": "Inicio: 1 µg/kg/min IV CRI; titular hasta 3 µg/kg/min si es necesario.",
        "context": "Referencia cardiovascular para vasodilatación aguda; la fuente indica no administrar en bolo y limitar el tratamiento a 24–48 h.",
        "source": "merck_cardio_therapy",
    },
    {
        "aliases": ["esmolol"],
        "species": "Canino / Felino",
        "regimen": "10–200 µg/kg/min IV CRI si es necesario, tras bolo IV lento de 0,1–0,5 mg/kg.",
        "context": "Referencia cardiovascular; el cálculo CRI no incluye el bolo y requiere monitorización y titulación clínica.",
        "source": "merck_cardio_therapy",
    },
    {
        "aliases": ["lidocaina", "lidocaine", "lignocaina", "lignocaine"],
        "species": "Canino",
        "regimen": "20–50 µg/kg/min IV CRI; el cuadro también describe una dosis de carga de 1–2 mg/kg IV.",
        "context": "Referencia analgésica para perros; la dosis de carga no se calcula en este apartado.",
        "source": "merck_analgesics",
    },
    {
        "aliases": ["lidocaina", "lidocaine", "lignocaina", "lignocaine"],
        "species": "Felino",
        "regimen": "La fuente indica que no se recomienda como CRI en gatos.",
        "context": "Merck advierte que los gatos son sensibles a los efectos sobre el sistema nervioso central y cardiovascular.",
        "source": "merck_analgesics",
    },
    {
        "aliases": ["lidocaina", "lidocaine", "lignocaina", "lignocaine"],
        "species": "Canino",
        "regimen": "25–80 µg/kg/min IV CRI tras una dosis de carga.",
        "context": "Referencia para tratamiento de arritmias; la dosis de carga no se calcula en este apartado.",
        "source": "merck_cardio_therapy",
    },
    {
        "aliases": ["lidocaina", "lidocaine", "lignocaina", "lignocaine"],
        "species": "Felino",
        "regimen": "10–20 µg/kg/min IV CRI si es eficaz, tras una dosis de carga.",
        "context": "Referencia para arritmias; la fuente recomienda una dosis menor por la sensibilidad de los gatos a los efectos sobre el sistema nervioso central.",
        "source": "merck_cardio_therapy",
    },
    {
        "aliases": ["amiodarona", "amiodarone"],
        "species": "Canino",
        "regimen": "Infusión IV inicial de 2–5 mg/kg durante 30–60 min; después 0,8 mg/kg/h durante 6 h y luego 0,5 mg/kg/h.",
        "context": "Referencia cardiovascular para arritmias. Es un esquema escalonado de infusión, no una dosis única; verificar formulación y monitorización ECG/hemodinámica.",
        "source": "merck_cardio_therapy",
    },
    {
        "aliases": ["procainamida", "procainamide"],
        "species": "Canino",
        "regimen": "25–40 µg/kg/min IV CRI tras un bolo IV lento titulado al efecto.",
        "context": "Referencia para arritmias; la dosis de carga no se calcula en este apartado.",
        "source": "merck_cardio_therapy",
    },
    {
        "aliases": ["fentanilo", "fentanyl"],
        "species": "Canino",
        "regimen": "0,01 mg/kg IV de carga, seguido de 0,01 mg/kg/h IV CRI.",
        "context": "Referencia analgésica; la fuente advierte del inicio retardado de la analgesia con parche transdérmico.",
        "source": "merck_analgesics",
    },
    {
        "aliases": ["fentanilo", "fentanyl"],
        "species": "Canino",
        "regimen": "2–5 µg/kg IV de carga, seguido de 3–6 µg/kg/h IV CRI.",
        "context": "Guía WSAVA para analgesia en perros; puede requerir titulación individual. El rango difiere de algunos manuales clínicos.",
        "source": "wsava_pain",
    },
    {
        "aliases": ["ketamina", "ketamine"],
        "species": "Canino / Felino",
        "regimen": "2–10 µg/kg/min IV CRI; la guía describe un bolo inicial de 0,2–0,5 mg/kg y uso perioperatorio de hasta 72 h.",
        "context": "Guía de dolor perioperatorio. La tasa se ajusta al procedimiento y respuesta clínica; los rangos más altos se usan durante cirugía y se reducen después.",
        "source": "wsava_pain",
    },
    {
        "aliases": ["dexmedetomidina", "dexmedetomidine"],
        "species": "Canino / Felino",
        "regimen": "1 µg/kg/h IV CRI; los estudios citados la preceden con una carga de 1–2 µg/kg.",
        "context": "Rango investigado para sedación/analgesia perioperatoria. La guía destaca cambios hemodinámicos relevantes y que suele reservarse a pacientes que puedan tolerarlos.",
        "source": "wsava_pain",
    },
    {
        "aliases": ["lidocaina", "lidocaine", "lignocaina", "lignocaine"],
        "species": "Canino",
        "regimen": "Se han estudiado 50 µg/kg/min IV CRI; la guía señala que las tasas varían entre estudios.",
        "context": "Uso perioperatorio analgésico/anestésico. Considerar el efecto ahorrador de anestésico inhalado; cautela al combinar con bloqueos de anestésico local.",
        "source": "wsava_pain",
    },
    {
        "aliases": ["lidocaina", "lidocaine", "lignocaina", "lignocaine"],
        "species": "Felino",
        "regimen": "No establece una tasa universal de CRI; uso controvertido y con cautela por riesgo de depresión hemodinámica.",
        "context": "La guía describe evidencia limitada y efectos hemodinámicos negativos en estudios felinos; no extrapolar la dosis canina.",
        "source": "wsava_pain",
    },
    {
        "aliases": ["esmolol"],
        "species": "Canino / Felino",
        "regimen": "50 µg/kg/min IV CRI, tras 0,5 mg/kg IV/IO durante 3–5 min.",
        "context": "Uso exclusivo en RCP para ritmos desfibrilables que persisten tras la primera desfibrilación; no es una pauta general para otras indicaciones.",
        "source": "recover_cpr",
    },
    {
        "aliases": ["fentanilo", "fentanyl"],
        "species": "Felino",
        "regimen": "0,01 mg/kg IV de carga, seguido de 0,01 mg/kg/h IV CRI.",
        "context": "Referencia analgésica; la carga no se calcula en este apartado.",
        "source": "merck_analgesics",
    },
    {
        "aliases": ["fentanilo", "fentanyl"],
        "species": "Felino",
        "regimen": "1–3 µg/kg IV de carga, seguido de 2–3 µg/kg/h IV CRI.",
        "context": "Guía WSAVA para analgesia en gatos; puede requerir titulación individual. El rango difiere de algunos manuales clínicos.",
        "source": "wsava_pain",
    },
    {
        "aliases": ["ketamina", "ketamine"],
        "species": "Canino",
        "regimen": "0,5–1 mg/kg IV de carga, seguido de 0,12–0,6 mg/kg/h IV CRI.",
        "context": "Adjunto analgésico; la fuente indica que puede ser neurotóxica por vía epidural o intratecal.",
        "source": "merck_analgesics",
    },
    {
        "aliases": ["ketamina", "ketamine"],
        "species": "Felino",
        "regimen": "0,5–1 mg/kg IV de carga, seguido de 0,1–0,6 mg/kg/h IV CRI.",
        "context": "Adjunto analgésico; la fuente indica que puede ser neurotóxica por vía epidural o intratecal.",
        "source": "merck_analgesics",
    },
    {
        "aliases": ["dexmedetomidina", "dexmedetomidine"],
        "species": "Canino",
        "regimen": "0,001–0,002 mg/kg IV de carga, seguido de 0,0007–0,001 mg/kg/h IV CRI.",
        "context": "Adjunto analgésico con efectos sedantes y cardiovasculares importantes.",
        "source": "merck_analgesics",
    },
    {
        "aliases": ["dexmedetomidina", "dexmedetomidine"],
        "species": "Felino",
        "regimen": "0,5 µg/kg IV de carga, seguido de 0,5 µg/kg/h IV CRI.",
        "context": "Adjunto analgésico; consultar la fuente para efectos cardiovasculares y otros contextos de uso.",
        "source": "merck_analgesics",
    },
    {
        "aliases": ["maropitant", "maropitante"],
        "species": "Canino",
        "regimen": "1 mg/kg IV durante 1–2 min, seguido de 0,03 mg/kg/h IV CRI.",
        "context": "La fuente advierte que la inyección IV rápida puede causar hipotensión grave.",
        "source": "merck_analgesics",
    },
    {
        "aliases": ["maropitant", "maropitante"],
        "species": "Felino",
        "regimen": "1 mg/kg IV durante 1–2 min, seguido de 0,1 mg/kg/h IV CRI.",
        "context": "La fuente advierte que la inyección IV rápida puede causar hipotensión grave.",
        "source": "merck_analgesics",
    },
    {
        "aliases": ["butorfanol", "butorphanol"],
        "species": "Canino",
        "regimen": "0,2 mg/kg IV de carga, seguido de 0,1–0,24 mg/kg/h IV CRI.",
        "context": "La fuente indica una duración corta del efecto y señala que la dosis puede reducirse en perros con mutación ABCB1-1Delta.",
        "source": "merck_analgesics",
    },
    {
        "aliases": ["butorfanol", "butorphanol"],
        "species": "Felino",
        "regimen": "0,2–0,4 mg/kg IV de carga, seguido de 0,1–0,24 mg/kg/h IV CRI.",
        "context": "Referencia analgésica para gatos; consulta la fuente para la información adicional del fármaco.",
        "source": "merck_analgesics",
    },
    {
        "aliases": ["buprenorfina", "buprenorphine"],
        "species": "Canino / Felino",
        "regimen": "0,005–0,01 mg/kg IV de carga, seguido de 0,002–0,004 mg/kg/h IV CRI.",
        "context": "La referencia corresponde a la formulación inyectable de 0,3 mg/mL; no confundir con formulaciones concentradas de acción prolongada.",
        "source": "merck_analgesics",
    },
    {
        "aliases": ["hidromorfona", "hydromorphone"],
        "species": "Canino",
        "regimen": "0,025–0,05 mg/kg IV de carga, seguido de 0,03 mg/kg/h IV CRI.",
        "context": "Referencia analgésica para perros.",
        "source": "merck_analgesics",
    },
    {
        "aliases": ["hidromorfona", "hydromorphone"],
        "species": "Felino",
        "regimen": "0,025 mg/kg IV de carga, seguido de 0,01–0,05 mg/kg/h IV CRI.",
        "context": "Referencia analgésica para gatos.",
        "source": "merck_analgesics",
    },
    {
        "aliases": ["metadona", "methadone"],
        "species": "Canino",
        "regimen": "0,1–0,2 mg/kg IV de carga, seguido de 0,12 mg/kg/h IV CRI.",
        "context": "Tabla de referencia analgésica de Merck para perros. Una revisión clínica de 2023 describe 0,2 mg/kg IV de carga y 0,1 mg/kg/h en perros, con ajuste por respuesta.",
        "source": "merck_analgesics",
    },
    {
        "aliases": ["metadona", "methadone"],
        "species": "Canino",
        "regimen": "0,2 mg/kg IV de carga, seguido de 0,1 mg/kg/h IV CRI.",
        "context": "Revisión narrativa clínica para analgesia en perros; basada en literatura limitada, no en un consenso. No presentar como dosis establecida para gatos.",
        "source": "methadone_review",
    },
    {
        "aliases": ["metadona", "methadone"],
        "species": "Felino",
        "regimen": "0,1–0,2 mg/kg IV de carga, seguido de 0,12 mg/kg/h IV CRI.",
        "context": "Rango de manual clínico para gatos. La revisión clínica de 2023 citada para perros no establece una tasa CRI felina.",
        "source": "merck_analgesics",
    },
    {
        "aliases": ["propofol"],
        "species": "Canino",
        "regimen": "0,2–0,4 mg/kg/min IV CRI para mantenimiento anestésico; hasta 0,6 mg/kg/min durante periodos cortos según respuesta.",
        "context": "Ficha técnica oficial. Es mantenimiento de anestesia general, no una pauta analgésica; exige anestesia y monitorización cardiorrespiratoria.",
        "source": "propofol_spc",
    },
    {
        "aliases": ["propofol"],
        "species": "Felino",
        "regimen": "0,1–0,3 mg/kg/min IV CRI para mantenimiento anestésico, ajustada a respuesta individual.",
        "context": "Ficha técnica oficial. Es mantenimiento de anestesia general, no una pauta analgésica; la exposición prolongada puede retrasar la recuperación, especialmente en gatos.",
        "source": "propofol_spc",
    },
    {
        "aliases": ["morfina", "morphine"],
        "species": "Canino",
        "regimen": "0,3–0,5 mg/kg IV (administrada lentamente) de carga, seguido de 0,1–1 mg/kg/h IV CRI.",
        "context": "La fuente advierte que la administración IV rápida puede causar excitación del sistema nervioso central.",
        "source": "merck_analgesics",
    },
    {
        "aliases": ["morfina", "morphine"],
        "species": "Felino",
        "regimen": "0,1–0,25 mg/kg IV de carga, seguido de 0,05–0,1 mg/kg/h IV CRI.",
        "context": "La fuente advierte que la administración IV rápida puede causar excitación y que puede producir hipertermia en gatos.",
        "source": "merck_analgesics",
    },
    {
        "aliases": ["alfentanilo", "alfentanil"],
        "species": "Canino",
        "regimen": "0,5–1 µg/kg IV de carga, seguido de 0,5–1 µg/kg/min IV CRI.",
        "context": "Opioide de acción muy corta; la fuente lo describe como CRI para alcanzar efecto.",
        "source": "merck_analgesics",
    },
    {
        "aliases": ["alfentanilo", "alfentanil"],
        "species": "Felino",
        "regimen": "5–10 µg/kg IV de carga, seguido de 0,8–1 µg/kg/min IV CRI.",
        "context": "Opioide de acción muy corta; la fuente lo describe como CRI para alcanzar efecto.",
        "source": "merck_analgesics",
    },
    {
        "aliases": ["remifentanilo", "remifentanil"],
        "species": "Canino",
        "regimen": "1 µg/kg IV de carga, seguido de 0,1–0,3 µg/kg/min IV CRI.",
        "context": "La fuente señala su duración de acción extremadamente corta.",
        "source": "merck_analgesics",
    },
    {
        "aliases": ["remifentanilo", "remifentanil"],
        "species": "Canino",
        "regimen": "6–12 µg/kg/h IV CRI; la guía no especifica bolo.",
        "context": "Referencia WSAVA para analgesia; la dosis puede ajustarse según efecto y necesidad anestésica.",
        "source": "wsava_pain",
    },
    {
        "aliases": ["remifentanilo", "remifentanil"],
        "species": "Felino",
        "regimen": "2,5 µg/kg IV de carga, seguido de 0,2–0,4 µg/kg/min IV CRI.",
        "context": "La fuente señala su duración de acción extremadamente corta.",
        "source": "merck_analgesics",
    },
    {
        "aliases": ["remifentanilo", "remifentanil"],
        "species": "Felino",
        "regimen": "4–6 µg/kg/h IV CRI; la guía no especifica bolo.",
        "context": "Referencia WSAVA para analgesia; la dosis puede ajustarse según efecto y necesidad anestésica.",
        "source": "wsava_pain",
    },
    {
        "aliases": ["sufentanilo", "sufentanil"],
        "species": "Canino / Felino",
        "regimen": "0,5–1 µg/kg IV lentamente de carga, seguido de 0,5–1 µg/kg/h IV CRI.",
        "context": "Referencia analgésica para perros y gatos.",
        "source": "merck_analgesics",
    },
]


def normalize_drug_name(value: str) -> str:
    """Normaliza acentos y mayúsculas para buscar nombres habituales de fármacos."""
    return "".join(
        character
        for character in unicodedata.normalize("NFKD", value.casefold().strip())
        if not unicodedata.combining(character)
    )


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
    "eligiendo el volumen final o el ritmo en mL/h. Introduce las dosis prescritas; "
    "al escribir un medicamento aparecerán referencias disponibles."
)

with st.container(border=True):
    st.markdown("**Fórmula**")
    st.latex(
        r"\text{Cantidad de fármaco (mL)} = "
        r"\frac{\text{Dosis (unidad/kg/tiempo)} \times \text{Peso (kg)} \times "
        r"\text{Duración (mismo tiempo)}}{\text{Concentración (misma unidad/mL)}}"
    )
    st.caption(
        "Dosis disponibles por hora y por minuto; si eliges /min, las horas de duración "
        "se convierten automáticamente a minutos. Cada medicamento se calcula por separado. "
        "Puedes indicar el volumen final o el ritmo "
        "deseado; con la duración se calcula el otro. Si indicas ambos, deben coincidir. "
        "El diluyente es el volumen final menos el volumen del medicamento. La dosis y la concentración deben "
        "pertenecer a la misma familia: masa con masa o UI/mUI con UI/mUI. La actividad "
        "no se convierte a masa porque la equivalencia depende del medicamento."
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
            options=[
                "µg/kg/h", "µg/kg/min",
                "mg/kg/h", "mg/kg/min",
                "g/kg/h", "g/kg/min",
                "UI/kg/h", "UI/kg/min",
                "mUI/kg/h", "mUI/kg/min",
            ],
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
            options=["µg/mL", "mg/mL", "g/mL", "UI/mL", "mUI/mL"],
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

    dose_is_ui = dose_unit.startswith("UI/") or dose_unit.startswith("mUI/")
    concentration_is_ui = concentration_unit.startswith("UI/") or concentration_unit.startswith("mUI/")
    if dose_is_ui != concentration_is_ui:
        cri_errors.append(
            f"{row_label}: las unidades no coinciden. Una dosis en UI/mUI por kg y tiempo "
            "requiere concentración en UI/mUI por mL; las dosis de masa requieren concentración de masa."
        )
        continue

    dose_to_base_per_hour = {
        "µg/kg/h": ("mass", 0.001, 1.0),
        "µg/kg/min": ("mass", 0.001, 60.0),
        "mg/kg/h": ("mass", 1.0, 1.0),
        "mg/kg/min": ("mass", 1.0, 60.0),
        "g/kg/h": ("mass", 1000.0, 1.0),
        "g/kg/min": ("mass", 1000.0, 60.0),
        "UI/kg/h": ("activity", 1.0, 1.0),
        "UI/kg/min": ("activity", 1.0, 60.0),
        "mUI/kg/h": ("activity", 0.001, 1.0),
        "mUI/kg/min": ("activity", 0.001, 60.0),
    }
    concentration_to_base = {
        "µg/mL": ("mass", 0.001),
        "mg/mL": ("mass", 1.0),
        "g/mL": ("mass", 1000.0),
        "UI/mL": ("activity", 1.0),
        "mUI/mL": ("activity", 0.001),
    }
    dose_family, dose_unit_factor, dose_time_factor = dose_to_base_per_hour[dose_unit]
    concentration_family, concentration_factor = concentration_to_base[concentration_unit]
    if dose_family != concentration_family:
        cri_errors.append(
            f"{row_label}: la dosis y la concentración deben pertenecer a la misma familia "
            "(masa con masa o UI/mUI con UI/mUI). No se convierten unidades de actividad a masa."
        )
        continue

    dose_base = float(dose) * dose_unit_factor * dose_time_factor
    concentration_base = float(concentration) * concentration_factor

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
        minimum_rate = (dose_base * weight) / concentration_base
        if has_target_rate:
            cri_errors.append(
                f"{row_label}: con la dosis y concentración introducidas, se necesitan "
                f"{format_cri_value(medication_volume_ml)} mL de fármaco para {format_cri_value(float(duration))} h. "
                f"Eso requiere al menos {format_cri_value(minimum_rate)} mL/h, pero indicaste "
                f"{format_cri_value(float(target_rate))} mL/h ({format_cri_value(calculated_final_volume)} mL finales). "
                "La combinación no es posible con estos datos. Verifica la prescripción, la concentración "
                "y el objetivo de volumen/ritmo; este cálculo no recomienda ajustar la dosis."
            )
        else:
            cri_errors.append(
                f"{row_label}: el volumen final indicado ({format_cri_value(calculated_final_volume)} mL) "
                f"es menor que los {format_cri_value(medication_volume_ml)} mL de fármaco requeridos "
                f"por la dosis prescrita para {format_cri_value(float(duration))} h. "
                f"Se necesita un volumen final de al menos {format_cri_value(medication_volume_ml)} mL "
                f"(ritmo mínimo {format_cri_value(minimum_rate)} mL/h). Verifica los datos; "
                "este cálculo no recomienda ajustar la dosis."
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

cri_reference_queries = []
for row_number, row in cri_inputs.iterrows():
    medication_name = str(row.get("Medicamento", "")).strip()
    if medication_name:
        cri_reference_queries.append((row_number, medication_name))

if cri_reference_queries:
    st.subheader("Bibliografía de CRI por medicamento")
    st.caption(
        "Catálogo inicial para perros y gatos; no es exhaustivo ni se actualiza automáticamente. "
        "Cuando existe una guía o consenso aplicable a esa indicación, se muestra primero; "
        "los manuales clínicos quedan como referencias complementarias. Cada fuente muestra su fecha."
    )
    for row_number, medication_name in cri_reference_queries:
        normalized_name = normalize_drug_name(medication_name)
        matching_references = [
            reference
            for reference in CRI_DOSE_REFERENCES
            if any(
                normalize_drug_name(alias) == normalized_name
                for alias in reference["aliases"]
            )
            and species in reference["species"]
        ]
        def reference_priority(reference: dict) -> int:
            source_type = CRI_REFERENCE_SOURCES[reference["source"]]["type"]
            if source_type.startswith(("Guía", "Consenso")):
                return 0
            if source_type.startswith("Ficha técnica"):
                return 1
            if "revisada por pares" in source_type:
                return 2
            return 3

        matching_references.sort(key=reference_priority)

        with st.expander(f"{medication_name} · {species}", expanded=bool(matching_references)):
            if not matching_references:
                st.info(
                    "No hay una dosis de CRI con referencia en el catálogo actual para este "
                    "nombre y especie. Usa la dosis prescrita y consulta una fuente veterinaria actual."
                )
                continue

            for reference in matching_references:
                source = CRI_REFERENCE_SOURCES[reference["source"]]
                st.markdown(f"**Especie:** {reference['species']}")
                st.markdown(f"**Régimen de referencia publicado:** {reference['regimen']}")
                st.write(reference["context"])
                st.markdown(
                    f"**Fuente ({source['type']}):** [{source['title']}]({source['url']}) · {source['updated']}"
                )
            st.caption(
                "La referencia no se copia a la dosis del cálculo: verifica indicación, "
                "paciente, formulación y protocolo local antes de prescribir."
            )

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
    "las unidades y la preparación prescrita. Los valores se redondean solo para mostrarse. "
    "La bibliografía disponible es una selección inicial, no una lista de todos los fármacos CRI."
)


st.divider()
st.header("Curva de glucosa")
st.caption(
    "Introduce las mediciones a lo largo del intervalo entre dosis. La gráfica y el resumen se actualizan "
    "con los datos introducidos; los valores no cambian ni recomiendan por sí mismos una pauta de insulina."
)

curve_context = st.radio(
    "Dónde se realizó la curva",
    ["En casa", "En clínica"],
    horizontal=True,
    key="glucose_curve_context",
)
clinical_signs = st.multiselect(
    "Signos observados durante este periodo (opcional)",
    ["Poliuria", "Polidipsia", "Polifagia", "Pérdida de peso", "Signos compatibles con hipoglucemia"],
    key="glucose_curve_signs",
)

if "glucose_curve_data_v1" not in st.session_state:
    st.session_state.glucose_curve_data_v1 = pd.DataFrame(
        {
            "Tiempo desde comida/insulina (h)": [0, 2, 4, 6, 8, 10, 12],
            "Glucemia (mg/dL)": [None] * 7,
        }
    )

curve_inputs = st.data_editor(
    st.session_state.glucose_curve_data_v1,
    key="glucose_curve_editor_v1",
    num_rows="dynamic",
    hide_index=True,
    width="stretch",
    column_config={
        "Tiempo desde comida/insulina (h)": st.column_config.NumberColumn(
            "Tiempo (h)", min_value=0.0, max_value=24.0, step=0.5, format="%.1f",
            help="Hora 0 corresponde a la comida y administración habitual de insulina.",
        ),
        "Glucemia (mg/dL)": st.column_config.NumberColumn(
            "Glucemia (mg/dL)", min_value=0.0, max_value=2000.0, step=1.0, format="%.0f",
        ),
    },
)

valid_curve = curve_inputs.dropna(
    subset=["Tiempo desde comida/insulina (h)", "Glucemia (mg/dL)"]
).copy()
if not valid_curve.empty:
    valid_curve = valid_curve.sort_values("Tiempo desde comida/insulina (h)")
    duplicate_times = valid_curve["Tiempo desde comida/insulina (h)"].duplicated().any()
    if duplicate_times:
        st.warning("Hay horas repetidas. Asigna una hora distinta a cada medición para interpretar la curva.")
    else:
        st.subheader("Gráfica de glucosa")
        st.line_chart(
            valid_curve.set_index("Tiempo desde comida/insulina (h)")["Glucemia (mg/dL)"],
            x_label="Tiempo desde comida/insulina (h)",
            y_label="Glucemia (mg/dL)",
            height=360,
        )

        nadir_row = valid_curve.loc[valid_curve["Glucemia (mg/dL)"].idxmin()]
        nadir = float(nadir_row["Glucemia (mg/dL)"])
        nadir_time = float(nadir_row["Tiempo desde comida/insulina (h)"])
        duration_h = float(valid_curve["Tiempo desde comida/insulina (h)"].max())
        metrics = st.columns(3)
        metrics[0].metric("Nadir observado", f"{nadir:.0f} mg/dL")
        metrics[1].metric("Hora del nadir", f"{nadir_time:g} h")
        metrics[2].metric("Duración registrada", f"{duration_h:g} h")

        st.subheader("Orientación según AAHA 2026")
        if species == "Felino" and curve_context == "En clínica":
            st.warning(
                "AAHA 2026 no recomienda curvas realizadas en clínica para el seguimiento rutinario de gatos: "
                "el estrés puede elevar la glucosa. Valora con el veterinario una curva en casa o monitorización continua (CGM)."
            )
        if species == "Felino":
            st.markdown(
                "Para gatos tratados con insulina, AAHA describe habitualmente mediciones cada 2 horas "
                "durante hasta 10–12 horas. Como referencia para insulinas no basales, el nadir ideal "
                "es 80–150 mg/dL; se interpreta junto con los signos, el peso y el resto del intervalo. "
                "Si recibe un inhibidor SGLT2, esta curva no debe usarse como seguimiento rutinario sin "
                "indicación veterinaria específica."
            )
            low_threshold = 80
            glucose_target_description = "80–300 mg/dL durante la mayor parte del intervalo"
        else:
            st.markdown(
                "Para perros tratados con insulina, AAHA describe mediciones antes de la dosis y luego "
                "cada 2 horas durante hasta 10–12 horas. El nadir ideal es 80–150 mg/dL; también se "
                "valoran el tiempo por debajo de 200 mg/dL, la duración del efecto, los signos y el peso."
            )
            low_threshold = 60
            glucose_target_description = "aproximadamente 80–250 mg/dL al valorar la duración del efecto"

        if nadir < 60:
            st.error(
                "Se registró una glucemia menor de 60 mg/dL. Contacta con el veterinario con urgencia; "
                "si hay debilidad, temblores, desorientación, convulsiones o pérdida de conciencia, es una urgencia inmediata."
            )
        elif nadir < low_threshold:
            st.warning(
                f"El nadir ({nadir:.0f} mg/dL) queda por debajo del intervalo de referencia señalado para esta especie. "
                "Consulta al veterinario para revisar la curva y la seguridad del tratamiento."
            )
        elif nadir <= 150:
            st.success(
                f"El nadir observado está dentro del intervalo de referencia 80–150 mg/dL. "
                f"Valora cuánto tiempo permanece en {glucose_target_description} y si persisten signos clínicos."
            )
        else:
            st.info(
                "El nadir supera 150 mg/dL. Una curva aislada no basta para decidir un cambio: "
                "revisa signos, tendencia del peso, técnica y rutina de administración con el veterinario."
            )

        if clinical_signs:
            st.info(
                "Hay signos clínicos seleccionados. AAHA recomienda interpretarlos junto con la curva; "
                "la glucemia puntual o la curva por sí solas no determinan el control ni justifican ajustar la dosis."
            )
        if duration_h < 10:
            st.caption(
                "La curva cubre menos de 10 horas; puede no mostrar todo el intervalo de acción de la insulina. "
                "La guía describe habitualmente curvas de hasta 10–12 horas para insulinas no basales."
            )

        st.caption(
            "La respuesta puede variar entre días. Mantén, si es posible, la rutina habitual de comida, "
            "insulina, premios y actividad. No ajustes ni suspendas la insulina basándote únicamente en esta gráfica."
        )
else:
    st.info("Introduce al menos una hora y una medición de glucosa para generar la gráfica.")

with st.expander("Fuentes AAHA 2026", expanded=False):
    if species == "Felino":
        st.markdown(
            "- [AAHA 2026, Glucose Monitoring — Cats](https://www.aaha.org/resources/2026-aaha-diabetes-management-guidelines-for-cats/section-13-glucose-monitoring/)\n"
            "- [AAHA 2026, Insulin Treatment and Monitoring — Cats](https://www.aaha.org/resources/2026-aaha-diabetes-management-guidelines-for-cats/section-7-insulin-treatment-and-monitoring/)"
        )
    else:
        st.markdown(
            "- [AAHA 2026, Glucose Monitoring — Dogs](https://www.aaha.org/resources/2026-aaha-diabetes-management-guidelines-for-dogs/section-9-glucose-monitoring/)\n"
            "- [AAHA 2026, Monitoring Dogs Receiving Insulin](https://www.aaha.org/resources/2026-aaha-diabetes-management-guidelines-for-dogs/section-5-monitoring-dogs-receiving-insulin/)"
        )
    st.caption(
        "Los objetivos dependen del tipo de insulina y del contexto del paciente. Esta herramienta ofrece "
        "orientación de monitorización; las decisiones terapéuticas corresponden al veterinario responsable."
    )

