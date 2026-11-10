"""Calculadora orientativa de fluidoterapia para caninos y felinos.

La aplicación separa mantenimiento, reposición del déficit y pérdidas
continuadas para que puedan pautarse con soluciones distintas si procede.
"""

from __future__ import annotations

import pandas as pd
import streamlit as st
import unicodedata
import altair as alt


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
    "merck_prokinetics": {
        "title": "Merck Veterinary Manual — Gastrointestinal Prokinetic Drugs Used in Monogastric Animals",
        "type": "Manual clínico de consulta",
        "updated": "Consulta: noviembre de 2026",
        "url": "https://www.merckvetmanual.com/pharmacology/systemic-pharmacotherapeutics-of-the-digestive-system/gastrointestinal-prokinetic-drugs-used-in-monogastric-animals",
    },
    "acvim_htn": {
        "title": "ACVIM Consensus Statement — Systemic Hypertension in Dogs and Cats",
        "type": "Consenso ACVIM",
        "updated": "Publicado en 2018",
        "url": "https://academic.oup.com/jvim/article/32/6/1803/8471027",
    },
    "hydralazine_cases": {
        "title": "Evaluation of presentation, treatment and outcome in hypertensive emergency in dogs and cats: 15 cases",
        "type": "Serie clínica retrospectiva revisada por pares",
        "updated": "Publicado en 2022",
        "url": "https://pmc.ncbi.nlm.nih.gov/articles/PMC9796549/",
    },
    "acvim_seizures": {
        "title": "ACVIM Consensus Statement — Status Epilepticus and Cluster Seizures in Dogs and Cats",
        "type": "Consenso ACVIM con recomendaciones graduadas",
        "updated": "Publicado en 2024",
        "url": "https://pmc.ncbi.nlm.nih.gov/articles/PMC10800221/",
    },
    "midazolam_seizure_study": {
        "title": "Continuous rate infusion of midazolam as emergent treatment for seizures in dogs",
        "type": "Estudio clínico retrospectivo revisado por pares",
        "updated": "Publicado en 2020",
        "url": "https://doi.org/10.1111/jvim.15993",
    },
    "diazepam_seizure_study": {
        "title": "Constant rate infusion of diazepam or propofol for canine cluster seizures or status epilepticus",
        "type": "Estudio clínico retrospectivo revisado por pares",
        "updated": "Publicado en 2022",
        "url": "https://doi.org/10.3389/fvets.2022.1005948",
    },
    "tranexamic_dog_study": {
        "title": "Effects of intravenous tranexamic acid in healthy adult dogs",
        "type": "Estudio farmacocinético y farmacodinámico revisado por pares",
        "updated": "Publicado en 2015",
        "url": "https://doi.org/10.1111/vec.12319",
    },
    "aminocaproic_dog_study": {
        "title": "The effect of ε-aminocaproic acid in severely thrombocytopenic dogs",
        "type": "Estudio clínico prospectivo con controles históricos revisado por pares",
        "updated": "Publicado en 2024",
        "url": "https://pmc.ncbi.nlm.nih.gov/articles/PMC10937475/",
    },
    "famotidine_cri_study": {
        "title": "Evaluation of the effect of a famotidine continuous rate infusion on intragastric pH in healthy dogs",
        "type": "Ensayo aleatorizado cruzado revisado por pares",
        "updated": "Publicado en 2018",
        "url": "https://doi.org/10.1111/jvim.15558",
    },
    "metoclopramide_pk_study": {
        "title": "Bolus and infusions of metoclopramide: insights on benefits and risks from pharmacokinetic modelling",
        "type": "Reanálisis farmacocinético y modelización en perros revisado por pares",
        "updated": "Publicado en 2026",
        "url": "https://pubmed.ncbi.nlm.nih.gov/42178715/",
    },
}

# Catálogo inicial de referencias publicadas para CRI en perros y gatos.
# Mantiene el contexto por especie/indicación y no rellena la dosis prescrita.
CRI_DOSE_REFERENCES = [
    {
        "aliases": ["hidralazina", "hydralazine"],
        "species": "Canino",
        "regimen": "Tras carga IV de 0,1 mg/kg: 1,5–5 µg/kg/min IV CRI.",
        "context": "Opción parenteral descrita por el consenso ACVIM para hipertensión sistémica en perros. La evidencia clínica veterinaria es limitada; titular con monitorización continua de presión arterial y valorar respuesta y perfusión.",
        "source": "acvim_htn",
    },
    {
        "aliases": ["hidralazina", "hydralazine"],
        "species": "Canino / Felino",
        "regimen": "En una serie de urgencias hipertensivas, 2 perros/gatos recibieron CRI de 1–5 µg/kg/min tras una carga de hidralazina.",
        "context": "Serie retrospectiva pequeña; no establece eficacia comparativa ni una pauta universal. La publicación señala que la evidencia clínica veterinaria es escasa.",
        "source": "hydralazine_cases",
    },
    {
        "aliases": ["acido tranexamico", "tranexamic acid", "tranexamato"],
        "species": "Canino",
        "regimen": "10 mg/kg IV de carga, seguido de 10 mg/kg/h IV CRI durante 3 h.",
        "context": "En estudio farmacocinético/farmacodinámico de perros sanos, esta pauta fue tolerada, pero los efectos antifibrinolíticos en TEG fueron inconsistentes. No demuestra beneficio clínico ni valida su uso rutinario en trauma.",
        "source": "tranexamic_dog_study",
    },
    {
        "aliases": ["acido aminocaproico", "aminocaproic acid", "aminocaproato", "epsilon aminocaproico"],
        "species": "Canino",
        "regimen": "En un estudio clínico: 100 mg/kg IV en 15 min, seguido de 400 mg/kg/24 h (16,7 mg/kg/h) IV CRI.",
        "context": "Estudio prospectivo pequeño con controles históricos en perros con trombocitopenia grave. Aumentó la fuerza del coágulo, pero no redujo transfusiones, estancia ni mortalidad; no se recomienda como tratamiento rutinario. Considerar solo en contexto especializado de hemorragia grave.",
        "source": "aminocaproic_dog_study",
    },
    {
        "aliases": ["midazolam"],
        "species": "Canino",
        "regimen": "Estudio clínico retrospectivo: mediana 0,3 mg/kg/h IV CRI (rango observado 0,1–2,5 mg/kg/h).",
        "context": "Para estatus epiléptico o convulsiones en racimo resistentes al tratamiento inicial. El rango es el observado en un estudio, no una dosis universal; el consenso ACVIM recomienda midazolam IV CRI en perros y requiere monitorización intensiva.",
        "source": "midazolam_seizure_study",
    },
    {
        "aliases": ["midazolam"],
        "species": "Felino",
        "regimen": "El consenso ACVIM recomienda midazolam IV CRI como benzodiacepina de elección; no establece una tasa felina universal en el texto principal.",
        "context": "La recomendación para gatos tiene evidencia inferior a la canina. No extrapolar automáticamente la dosis canina; requiere un protocolo veterinario de urgencias y monitorización intensiva.",
        "source": "acvim_seizures",
    },
    {
        "aliases": ["diazepam"],
        "species": "Canino",
        "regimen": "0,5 mg/kg/h IV CRI, pauta empleada en un estudio clínico retrospectivo de convulsiones en perros.",
        "context": "Para convulsiones en racimo o estatus epiléptico resistentes al tratamiento inicial. ACVIM recomienda considerar midazolam antes que diazepam, y advierte que diazepam se adsorbe al plástico y es fotosensible: línea dedicada, preparación inmediata y protección de la luz.",
        "source": "diazepam_seizure_study",
    },
    {
        "aliases": ["famotidina", "famotidine"],
        "species": "Canino",
        "regimen": "1 mg/kg IV de carga, seguido de 8 mg/kg/día (0,333 mg/kg/h) en CRI.",
        "context": "Ensayo cruzado aleatorizado en 9 perros Beagle sanos: la CRI elevó el pH gástrico más que famotidina IV cada 12 h. Es un resultado farmacodinámico en perros sanos, no demuestra mejoría clínica en pacientes enfermos.",
        "source": "famotidine_cri_study",
    },
    {
        "aliases": [
            "metoclopramida", "metoclopramide", "metoclopramida clorhidrato",
            "metoclopramide hydrochloride", "metoclopramide hcl", "primperan",
        ],
        "species": "Canino",
        "regimen": "Modelización de infusión: 1–2 mg/kg/día (0,042–0,083 mg/kg/h) IV. El modelo estima cargas de 0,05 mg/kg para 1 mg/kg/día y 0,1 mg/kg para 2 mg/kg/día.",
        "context": "Reanálisis farmacocinético y modelización basado en datos de perros; no es un ensayo clínico de eficacia. Descarta obstrucción, hemorragia o perforación gastrointestinal. No extrapolar la pauta modelada a gatos.",
        "source": "metoclopramide_pk_study",
    },
    {
        "aliases": [
            "metoclopramida", "metoclopramide", "metoclopramida clorhidrato",
            "metoclopramide hydrochloride", "metoclopramide hcl", "primperan",
        ],
        "species": "Felino",
        "regimen": "0,01–0,02 mg/kg/h IV en infusión continua.",
        "context": "Rango de manual clínico; no es una pauta validada por el estudio farmacocinético de 2026, que se hizo en perros. Descarta obstrucción, hemorragia o perforación gastrointestinal; el efecto antiemético puede ser limitado en gatos.",
        "source": "merck_prokinetics",
    },
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
                or (
                    len(normalize_drug_name(alias)) >= 8
                    and normalize_drug_name(alias) in normalized_name
                )
                for alias in reference["aliases"]
            )
            and normalize_drug_name(species)
            in [normalize_drug_name(item.strip()) for item in reference["species"].split("/")]
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
    "con los datos introducidos. La orientación de dosis es una referencia para revisar con el veterinario, "
    "no una prescripción automática."
)

if species == "Canino":
    insulin_options = [
        "Insulina porcina lente (U-40)", "NPH (U-100)", "PZI / protamina zinc (U-40)",
        "Glargina U-100", "Glargina U-300", "Degludec", "Detemir", "Otra / no consta",
    ]
else:
    insulin_options = [
        "Glargina U-100", "PZI / protamina zinc (U-40)", "Insulina porcina lente (U-40)",
        "Glargina U-300", "Degludec", "NPH (U-100)", "Otra / no consta", "No usa insulina (SGLT2)",
    ]

insulin_cols = st.columns(3)
insulin_type = insulin_cols[0].selectbox("Tipo de insulina", insulin_options, key="curve_insulin_type")
current_dose = insulin_cols[1].number_input(
    "Dosis prescrita actual (U por administración)", min_value=0.0, value=0.0,
    step=0.5, format="%.2f", help="Opcional: anota la dosis que ya prescribió el veterinario.",
    key="curve_insulin_dose",
)
dosing_interval = insulin_cols[2].selectbox(
    "Intervalo prescrito", ["Cada 12 h", "Cada 24 h", "Otro / no consta"],
    key="curve_insulin_interval",
)
st.caption(
    "Anota la dosis en unidades (U), no en mL. Comprueba que la concentración de la insulina "
    "(p. ej., U-40 o U-100) coincide con la jeringa o dispositivo utilizado."
)
if species == "Canino" and insulin_type in {"Insulina porcina lente (U-40)", "NPH (U-100)"}:
    st.caption(
        "Referencia AAHA 2026 de inicio para estas insulinas: 0,25–0,5 U/kg cada 12 h. "
        "La guía recomienda calcular con el peso ideal estimado y redondear hacia abajo a unidades enteras; "
        "esto no es una recomendación para cambiar la dosis actual."
    )
elif species == "Felino" and insulin_type in {"Glargina U-100", "PZI / protamina zinc (U-40)"}:
    st.caption(
        "Referencia AAHA 2026 de inicio: habitualmente 1 U por gato cada 12 h para glargina U-100 o PZI. "
        "Es una dosis inicial de referencia, no una recomendación para cambiar el tratamiento actual."
    )
elif species == "Felino" and insulin_type == "Glargina U-300":
    st.caption(
        "Referencia AAHA 2026 de inicio para glargina U-300: 0,5 U/kg cada 12–24 h o 2 U por gato cada 24 h, "
        "según el protocolo y el paciente. No se debe extrapolar a otras insulinas ni usar para ajustar esta curva."
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
hyperglycemia_signs = {"Poliuria", "Polidipsia", "Polifagia", "Pérdida de peso"}.intersection(clinical_signs)

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
            help="Registra la medición basal en hora 0, justo antes de la comida y la dosis; luego anota el tiempo transcurrido.",
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
        chart_data = valid_curve.copy()
        chart_data["Hora de toma"] = chart_data["Tiempo desde comida/insulina (h)"].map(lambda h: f"{h:g} h")
        hour_ticks = sorted(chart_data["Tiempo desde comida/insulina (h)"].astype(float).unique().tolist())
        x_field = "Tiempo desde comida/insulina (h)"
        y_field = "Glucemia (mg/dL)"
        chart_base = alt.Chart(chart_data)
        glucose_line = chart_base.mark_line(color="#1677d2", strokeWidth=3).encode(
            x=alt.X(
                f"{x_field}:Q", title="Horas desde comida/insulina",
                scale=alt.Scale(domain=[0, max(12.0, float(max(hour_ticks)))], nice=False),
                axis=alt.Axis(values=hour_ticks, labelExpr="datum.value + ' h'", labelAngle=0),
            ),
            y=alt.Y(f"{y_field}:Q", title="Glucemia (mg/dL)", scale=alt.Scale(zero=False)),
            tooltip=[alt.Tooltip("Hora de toma:N"), alt.Tooltip(f"{y_field}:Q", format=".0f")],
        )
        glucose_points = chart_base.mark_circle(size=130, color="#0759a8", stroke="white", strokeWidth=1.5).encode(
            x=alt.X(f"{x_field}:Q"), y=alt.Y(f"{y_field}:Q"),
            tooltip=[alt.Tooltip("Hora de toma:N"), alt.Tooltip(f"{y_field}:Q", format=".0f")],
        )
        glucose_labels = chart_base.mark_text(dy=-15, fontSize=12, fontWeight="bold", color="#17324d").encode(
            x=alt.X(f"{x_field}:Q"), y=alt.Y(f"{y_field}:Q"),
            text=alt.Text(f"{y_field}:Q", format=".0f"),
        )
        st.altair_chart(
            alt.layer(glucose_line, glucose_points, glucose_labels)
            .properties(height=380)
            .interactive(),
            use_container_width=True,
        )
        st.caption("Cada punto marca una toma real; el eje X muestra las horas anotadas y la cifra sobre cada punto es la glucemia.")

        nadir_row = valid_curve.loc[valid_curve["Glucemia (mg/dL)"].idxmin()]
        nadir = float(nadir_row["Glucemia (mg/dL)"])
        nadir_time = float(nadir_row["Tiempo desde comida/insulina (h)"])
        duration_h = float(valid_curve["Tiempo desde comida/insulina (h)"].max())
        metrics = st.columns(4)
        metrics[0].metric(
            "Mínimo basal" if nadir_time == 0 else "Nadir observado",
            f"{nadir:.0f} mg/dL",
        )
        metrics[1].metric("Hora del nadir", f"{nadir_time:g} h")
        metrics[2].metric("Duración registrada", f"{duration_h:g} h")
        metrics[3].metric(
            "Rango medido",
            f"{valid_curve['Glucemia (mg/dL)'].min():.0f}–{valid_curve['Glucemia (mg/dL)'].max():.0f} mg/dL",
            f"{len(valid_curve)} mediciones",
        )
        with st.expander("Ver mediciones de la curva", expanded=False):
            st.dataframe(
                valid_curve.rename(
                    columns={
                        "Tiempo desde comida/insulina (h)": "Tiempo (h)",
                        "Glucemia (mg/dL)": "Glucemia (mg/dL)",
                    }
                ).style.format({"Tiempo (h)": "{:.1f}", "Glucemia (mg/dL)": "{:.0f}"}),
                width="stretch",
                hide_index=True,
            )

        st.subheader("Orientación según AAHA 2026")
        st.write(
            f"**Insulina registrada:** {insulin_type} · **Dosis anotada:** "
            f"{current_dose:g} U por administración · **Intervalo:** {dosing_interval}."
        )
        if nadir_time == 0:
            st.warning(
                "La medición más baja es la basal de hora 0, antes de la comida y la insulina. "
                "Todavía no identifica el nadir posterior a la dosis; interpreta las mediciones siguientes con el veterinario."
            )
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
            glucose_target_description = "80–300 mg/dL durante la curva y <200 mg/dL durante la mayor parte del intervalo"

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

        st.markdown("**Qué revisar sobre la dosis**")
        if species == "Canino":
            if nadir < 60:
                st.warning(
                    "AAHA 2026: un nadir <60 mg/dL o hipoglucemia confirmada requiere revisión. "
                    "La guía contempla discutir una reducción aproximada del 10–25% si la hipoglucemia "
                    "prolongada está confirmada sin signos; con signos, la actuación y reducción deben "
                    "individualizarse con atención veterinaria. Confirma las lecturas bajas de CGM con "
                    "glucómetro veterinario cuando no haya signos."
                )
            elif nadir > 150 and hyperglycemia_signs:
                if current_dose > 0:
                    small_medium_candidates = f"{current_dose + 0.5:g}–{current_dose + 1.0:g} U"
                    medium_large_candidates = f"{current_dose + 1.0:g}–{current_dose + 2.0:g} U"
                    st.info(
                        f"Con nadir >150 mg/dL y signos clínicos, AAHA 2026 describe valorar con el veterinario "
                        f"un incremento habitual según tamaño: 0,5–1 U en perros pequeños/medianos "
                        f"(dosis resultante orientativa: {small_medium_candidates}) o 1–2 U en medianos/grandes "
                        f"(dosis resultante orientativa: {medium_large_candidates}). Parte de las {current_dose:g} U "
                        "anotadas; elige el contexto con el veterinario, no se aplica automáticamente. "
                        "Repetir curva/CGM en 5–14 días."
                    )
                else:
                    st.info(
                        "Con nadir >150 mg/dL y signos, AAHA 2026 contempla valorar un aumento; en perros "
                        "describe incrementos habituales de 0,5–1 U en pequeños/medianos y 1–2 U en grandes. "
                        "No puede contextualizarse sin conocer la dosis y el tamaño del paciente; reevaluar en 5–14 días."
                    )
            elif nadir > 150:
                st.info(
                    "Si no hay signos y el peso está estable, AAHA 2026 recomienda mantener la pauta y "
                    "reevaluar en 1–3 meses; si hay pérdida de peso no intencionada, ampliar la evaluación "
                    "y considerar ajuste supervisado."
                )
            else:
                st.info(
                    "Con nadir de 60–150 mg/dL, si los signos están controlados no suele requerirse ajuste. "
                    "Si persisten, valorar duración de acción, horario/frecuencia, CGM u otras enfermedades "
                    "antes de aumentar la dosis."
                )
        else:
            if insulin_type == "No usa insulina (SGLT2)":
                st.info(
                    "Esta interpretación de nadir y ajuste de dosis corresponde a insulina; no se debe aplicar "
                    "a un gato tratado con SGLT2. Sigue el protocolo de monitorización específico del fármaco."
                )
            elif nadir < 60:
                st.warning(
                    "AAHA 2026 recomienda considerar reducir la insulina ante hipoglucemia prolongada (<60 mg/dL) "
                    "o signos compatibles. En gatos, confirma y revisa de inmediato con el veterinario; no calcules "
                    "un cambio basándote solo en esta curva."
                )
            elif nadir > 150:
                st.info(
                    "Si el nadir no es aceptable, AAHA 2026 plantea considerar un aumento solo con evaluación "
                    "completa. En gatos no se recomienda convertir esta curva en una cantidad automática de U: "
                    "considera estrés, signos, peso, tipo de insulina y CGM; las curvas en clínica no se recomiendan "
                    "para el seguimiento rutinario."
                )
            else:
                st.info(
                    "El nadir está en el intervalo objetivo publicado. Si los signos y el peso son adecuados, "
                    "no cambies la dosis por esta curva aislada; monitoriza al gato y revisa la evolución con su veterinario."
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
        if insulin_type in {"Glargina U-300", "Degludec"}:
            st.caption(
                "La insulina seleccionada es basal/de acción prolongada. Una curva puntual de 10–12 h puede "
                "no describir el perfil completo; AAHA destaca valorar monitorización continua (CGM) y "
                "considerar el perfil específico de esta formulación."
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
        "Los objetivos y ajustes dependen de especie, tipo de insulina y contexto del paciente. La dosis "
        "registrada sirve para contextualizar; la app no prescribe ni cambia una pauta."
    )

# Módulo integrado de apoyo renal
st.title("🩺 Apoyo renal veterinario — perros y gatos")
st.caption("Clasificación, problemas tratables, opciones terapéuticas, cálculos de referencia y seguimiento.")
st.warning(
    "Herramienta de apoyo para uso veterinario. No diagnostica ni prescribe automáticamente. "
    "Las dosis son referencias publicadas, no órdenes terapéuticas: confirmar paciente, producto, ficha técnica local, "
    "función renal, comorbilidades, interacciones y monitorización antes de usarlas."
)

with st.sidebar:
    st.header("Datos del paciente")
    species = st.radio("Especie", ["Canino", "Felino"])
    weight = st.number_input("Peso actual (kg)", min_value=0.1, value=5.0, step=0.1, format="%.2f")
    mode = st.radio("Contexto", ["ERC estable", "LRA / cambio agudo", "Agudización de ERC"])
    ckd_confirmed = st.checkbox("ERC confirmada", value=False)
    stable_hydrated = st.checkbox("Paciente estable y adecuadamente hidratado", value=False)
    excluded_prepost = st.checkbox("Causas prerrenales y posrenales investigadas", value=False)
    prior_stage = st.selectbox("Estadio ERC previo (si agudización)", ["No conocido", "IRIS 1", "IRIS 2", "IRIS 3", "IRIS 4"])
    st.caption("La estadificación de ERC requiere diagnóstico previo y mediciones estables, idealmente seriadas.")

st.subheader("Datos clínicos y de laboratorio")
st.caption("Completa los resultados disponibles y marca las casillas clínicas que correspondan. La creatinina actual es necesaria para clasificar ERC o LRA.")
tab_renal, tab_urine_bp, tab_electrolytes, tab_blood, tab_clinical = st.tabs([
    "1 · Función renal", "2 · Orina y presión", "3 · Electrolitos", "4 · Sangre y nutrición", "5 · Estado clínico"
])
with tab_renal:
    st.markdown("#### Creatinina y filtración renal")
    c1, c2 = st.columns(2)
    with c1:
        current_creat = st.number_input("Creatinina actual (mg/dL)", min_value=0.0, value=1.0, step=0.1, format="%.2f", help="Introduce el resultado más reciente. La clasificación IRIS usa creatinina en un paciente estable para ERC y la tendencia para LRA.")
        baseline_creat = st.number_input("Creatinina basal (mg/dL; si se conoce)", min_value=0.0, value=0.0, step=0.1, format="%.2f", help="Usa el valor previo estable. Déjalo en 0 si no hay basal conocida.")
        acute_48h = st.checkbox("Aumento ≥0,3 mg/dL en las últimas 48 horas")
    with c2:
        sdma = st.number_input("SDMA (µg/dL; 0 si no se midió)", min_value=0.0, value=0.0, step=1.0)
        usg = st.number_input("Densidad urinaria (USG; 0 si no se midió)", min_value=0.0, value=0.0, step=0.001, format="%.3f")
        st.info("Interpreta creatinina y SDMA junto con hidratación, masa muscular y mediciones anteriores.")
with tab_urine_bp:
    c1, c2 = st.columns(2)
    with c1:
        upc = st.number_input("Cociente proteína/creatinina urinario (UPC)", min_value=0.0, value=0.0, step=0.05, format="%.2f")
        upc_persistent = st.checkbox("Proteinuria persistente; sedimento y cultivo revisados", help="Para interpretar la proteinuria renal, confirmar persistencia y descartar sedimento activo/infección.")
    with c2:
        sbp = st.number_input("Presión arterial sistólica (mmHg; 0 si no medida)", min_value=0, value=0, step=1)
        bp_confirmed = st.checkbox("Presión confirmada con lecturas seriadas", help="Usa mediciones estandarizadas; ACVIM recomienda descartar la primera y obtener 3–7 lecturas consecutivas.")
        tod = st.checkbox("Daño de órgano diana posiblemente asociado a hipertensión")
with tab_electrolytes:
    c1, c2 = st.columns(2)
    with c1:
        phosphorus = st.number_input("Fósforo (mg/dL; 0 si no medido)", min_value=0.0, value=0.0, step=0.1)
        potassium = st.number_input("Potasio (mmol/L; 0 si no medido)", min_value=0.0, value=0.0, step=0.1)
        low_k_confirmed = st.checkbox("Potasio bajo según el intervalo del laboratorio")
    with c2:
        high_k_confirmed = st.checkbox("Potasio alto según el intervalo del laboratorio")
        bicarbonate = st.number_input("Bicarbonato / CO₂ total (mmol/L; 0 si no medido)", min_value=0.0, value=0.0, step=0.5)
with tab_blood:
    c1, c2 = st.columns(2)
    with c1:
        hct = st.number_input("Hematocrito (%) (0 si no medido)", min_value=0.0, value=0.0, step=1.0)
        anemia_persistent = st.checkbox("Anemia persistente en controles")
        anemia_symptomatic = st.checkbox("Signos compatibles con anemia importante (debilidad, colapso o disnea)")
    with c2:
        albumin = st.number_input("Albúmina (g/dL; 0 si no medida)", min_value=0.0, value=0.0, step=0.1)
        hypoalbuminemia_confirmed = st.checkbox("Albúmina baja según el intervalo del laboratorio")
with tab_clinical:
    c1, c2 = st.columns(2)
    with c1:
        dehydration = st.checkbox("Deshidratación o hipovolemia actual")
        hypotension = st.checkbox("Hipotensión o perfusión inadecuada")
        oliguria = st.checkbox("Oliguria/anuria o diuresis <1 mL/kg/h durante ≥6 h")
        urine_output = st.number_input("Diuresis medida (mL/kg/h; 0 si no disponible)", min_value=0.0, value=0.0, step=0.1)
        volume_overload = st.checkbox("Posible sobrecarga de volumen")
    with c2:
        appetite = st.checkbox("Hiporexia/anorexia")
        nausea = st.checkbox("Náuseas o vómitos")
        weight_loss = st.checkbox("Pérdida de peso o masa muscular")
        infection = st.checkbox("Posible infección/pielonefritis")
        obstruction = st.checkbox("Posible obstrucción urinaria")
        glomerular = st.checkbox("Sospecha de enfermedad glomerular")
        nephrotoxins = st.checkbox("Exposición a fármacos nefrotóxicos")

# Classification functions keep the chronic and acute components separate.
def ckdstage(creat: float, sdma_value: float, sp: str) -> tuple[int, int | None]:
    if sp == "Canino":
        c = 1 if creat < 1.4 else 2 if creat <= 2.7 else 3 if creat <= 5.0 else 4
        s = None if sdma_value <= 0 else 1 if sdma_value <= 17 else 2 if sdma_value <= 35 else 3 if sdma_value <= 54 else 4
    else:
        c = 1 if creat < 1.6 else 2 if creat <= 2.8 else 3 if creat <= 5.0 else 4
        s = None if sdma_value <= 0 else 1 if sdma_value <= 17 else 2 if sdma_value <= 25 else 3 if sdma_value <= 38 else 4
    return c, s

creat_stage, sdma_stage = ckdstage(current_creat, sdma, species)
final_stage = max(creat_stage, sdma_stage or creat_stage)
delta = current_creat - baseline_creat if baseline_creat > 0 else None
acute_signal = acute_48h
oliguria_signal = oliguria or (urine_output > 0 and urine_output < 1.0)
if current_creat < 1.6:
    aki_grade = "I" if acute_signal else "No asignable"
elif current_creat <= 2.5:
    aki_grade = "II"
elif current_creat <= 5.0:
    aki_grade = "III"
elif current_creat <= 10.0:
    aki_grade = "IV"
else:
    aki_grade = "V"

# Issue flags with disease-specific context.
upc_threshold = 0.5 if species == "Canino" else 0.4
ckd_stage_for_decisions = int(prior_stage[-1]) if mode == "Agudización de ERC" and prior_stage != "No conocido" else final_stage if mode == "ERC estable" else None
if species == "Canino":
    proteinuria_threshold_met = ckd_stage_for_decisions is not None and ((ckd_stage_for_decisions >= 2 and upc > 0.5) or (ckd_stage_for_decisions == 1 and upc >= 1.0))
else:
    proteinuria_threshold_met = ckd_stage_for_decisions is not None and upc > 0.4
proteinuric = proteinuria_threshold_met and upc_persistent and ckd_confirmed and mode != "LRA / cambio agudo"
hypertensive = (sbp >= 160 and bp_confirmed) or tod
severely_hypertensive = sbp >= 180 or tod
phosphorus_stage = ckd_stage_for_decisions
stage_eligible_for_phosphorus = phosphorus_stage is not None and mode in {"ERC estable", "Agudización de ERC"} and ckd_confirmed and (mode != "ERC estable" or stable_hydrated)
phosphorus_target = (4.6 if species == "Canino" else 4.5) if phosphorus_stage == 2 else 5.0 if phosphorus_stage == 3 else 6.0 if phosphorus_stage == 4 else None
hyperphos = stage_eligible_for_phosphorus and phosphorus > 0 and phosphorus_target is not None and phosphorus > phosphorus_target
acidotic_cat = species == "Felino" and mode == "ERC estable" and ckd_confirmed and bicarbonate > 0 and bicarbonate < 16
anemia_threshold = (hct < 30 or (hct <= 35 and anemia_persistent)) if species == "Canino" else (hct < 25 or (hct <= 28 and anemia_persistent))
anemia_threshold = anemia_threshold and ckd_confirmed and mode != "LRA / cambio agudo"

# One shared issue list is consumed by treatment and follow-up panels.
issues: list[dict[str, str]] = []
def add_issue(title: str, status: str, action: str, evidence: str, monitoring: str, source: str, limit: str = "") -> None:
    issues.append({"title": title, "status": status, "action": action, "evidence": evidence, "monitoring": monitoring, "source": source, "limit": limit})

def issue_category(title: str) -> str:
    if any(word in title.lower() for word in ("urgencia", "hospitalización", "sintomática")):
        return "Estabilización / derivación"
    if any(word in title.lower() for word in ("infección", "obstrucción", "glomerular", "nefrotóxica", "erc no confirmada", "lra /")):
        return "Diagnóstico / causa"
    if "gastrointestinales" in title.lower():
        return "Soporte sintomático / nutrición"
    if any(word in title.lower() for word in ("confirmada", "agudización")):
        return "Clasificación / contexto"
    return "Complicación tratable"

if mode == "ERC estable":
    if not (ckd_confirmed and stable_hydrated and excluded_prepost):
        add_issue("ERC no confirmada/estable", "Faltan datos", "No asignar estadio definitivo. Confirmar persistencia de alteraciones y excluir componente prerrenal o posrenal; repetir creatinina/SDMA en paciente estable e hidratado.", "Guía IRIS; la estadificación sigue al diagnóstico y exige estabilidad.", "Repetir analítica y evaluación renal según evolución; ante cambio agudo, usar evaluación de LRA.", "https://www.iris-kidney.com/iris-staging-system")
    else:
        add_issue("ERC confirmada", f"Estadio IRIS {final_stage}", "Usar el estadio junto con signos, tendencias y complicaciones para priorizar intervenciones; estadio aislado no prescribe un fármaco.", "Guía IRIS 2026; creatinina/SDMA y evaluación individual.", "Reevaluar creatinina/SDMA y estado clínico tras cambios y longitudinalmente.", "https://www.iris-kidney.com/iris-guidelines-1")
elif mode == "Agudización de ERC":
    add_issue("Agudización de ERC", f"Estadio basal conservado: {prior_stage}; componente agudo aparte", "No reclasificar la creatinina aguda como nuevo estadio de ERC. Evaluar lesión aguda, causas desencadenantes, volemia, diuresis y complicaciones.", "IRIS distingue ERC estable de lesión renal aguda/decompensación; consenso de LRA reconoce etiología y reversibilidad variables.", "Monitorización hospitalaria según gravedad; control tras alta en pocos días y luego seguimiento renal.", "https://www.iris-kidney.com/new-page-5")
else:
    add_issue("LRA / cambio agudo", f"Grado IRIS orientativo {aki_grade}", "Investigar causas prerrenales, renales y posrenales; el grado por creatinina no predice por sí solo reversibilidad ni pronóstico.", "Consenso IRIS de mejores prácticas para LRA (2024), resumen IRIS 2026.", "Diuresis, peso y balance al menos dos veces al día en hospital; electrolitos inicialmente al menos dos veces al día según consenso.", "https://www.iris-kidney.com/new-page-5")
    if aki_grade in {"II", "III", "IV", "V"} or oliguria_signal or volume_overload or obstruction or high_k_confirmed:
        add_issue("Urgencia / hospitalización", "Prioridad alta", "Valoración hospitalaria y monitorización intensiva. Considerar consulta de nefrología/UCI; valorar terapia de reemplazo renal si complicaciones no se controlan médicamente.", "Consenso IRIS LRA; práctica basada en consenso y evidencia veterinaria limitada.", "Vigilancia de diuresis, balance, peso, PA, potasio, creatinina y ácido-base.", "https://www.iris-kidney.com/new-page-5")

if proteinuric:
    add_issue("Proteinuria renal persistente", "Intervención a considerar", "Confirmar origen renal y persistencia; considerar dieta renal y bloqueo RAAS individualizado. No usar ACEI/ARB con deshidratación, hipovolemia, hipotensión, hiperpotasemia o LRA activa.", "Gato: consenso iCatCare 2026 para UPC >0,4; perro: ensayo Brown et al. 2020, con umbrales UPC >0,5 si azotémico y ≥1,0 si no azotémico.", "PA, creatinina y K a 1–2 semanas; UPC a 4 semanas y luego cada 3 meses si estable.", "https://pmc.ncbi.nlm.nih.gov/articles/PMC7694823/", "Evidencia e indicaciones varían por especie; combinación de dos bloqueadores RAAS empeoró azotemia en 4/13 perros del ensayo.")
elif upc >= 0.2:
    add_issue("UPC limítrofe o no confirmada", "Repetir/interpretar", "Revisar sedimento, infección y causas asociadas; repetir UPC antes de tratar como proteinuria persistente.", "Consenso iCatCare 2026 en gatos; guía IRIS para clasificación de UPC.", "Muestras seriadas; presión y UPC en reevaluaciones.", "https://www.iris-kidney.com/iris-staging-system")

if hypertensive:
    add_issue("Hipertensión sistémica", "Intervención a considerar", "Si hay daño de órgano diana, tratar sin esperar repetición; en otro caso confirmar con lecturas estandarizadas. Elegir fármaco por especie, proteinuria, volumen y comorbilidades.", "Consenso ACVIM 2018 y iCatCare 2026; ambas describen manejo individualizado.", "Reevaluar PA a 1–2 semanas tras inicio/ajuste; evitar hipotensión y vigilar creatinina/electrolitos si bloqueo RAAS.", "https://pubmed.ncbi.nlm.nih.gov/30353952/", "La dosis depende de gravedad, respuesta y comorbilidades; una medición aislada puede ser artefacto.")
if hyperphos:
    target = f"<{phosphorus_target:.1f}"
    add_issue("Hiperfosfatemia", "Por encima del objetivo orientativo", f"Revisar dieta terapéutica renal y fósforo dietario; objetivo orientativo para {species.lower()}, estadio {phosphorus_stage}: {target} mg/dL. Si persiste fuera de objetivo tras 4–6 semanas de dieta renal, valorar quelante mezclado con comidas; seleccionar agente según calcio, ingesta y tolerancia.", "Guías IRIS por especie/estadio; consenso iCatCare 2026 para gatos.", "Fósforo y calcio 4–6 semanas tras cambio dietario/quelante, luego cada 12 semanas cuando estable.", "https://www.iris-kidney.com/iris-guidelines-1", "No se calcula dosis de quelante en esta versión: se titula a fósforo y cantidad ingerida; confirmar dosis en documento IRIS vigente por especie.")
if low_k_confirmed:
    add_issue("Hipopotasemia", "Corregir causa y valorar reposición", "En gatos estables, el consenso describe dieta con más K y suplementación oral con gluconato/citrato potásico; acidosis favorece valorar citrato. Hipopotasemia grave/decompensada requiere hospitalización y KCl IV monitorizado. En perros no se genera dosis renal con esta fuente.", "Consenso iCatCare 2026 para gatos; recomendación de consenso, respuesta individual.", "Repetir K y función renal tras iniciar o ajustar; vigilar debilidad, ventroflexión cervical, arritmia y tránsito intestinal.", "https://journals.sagepub.com/doi/10.1177/1098612X261466553", "La pauta felina citada es mEq/gato, no mg/kg. No usar si K alto o no se dispone de control analítico.")
if high_k_confirmed:
    add_issue("Hiperpotasemia", "Prioridad de evaluación", "Confirmar muestra/hemólisis; revisar función renal, diuresis, medicación y obstrucción. Valorar ECG y tratamiento urgente según concentración, cambios electrocardiográficos y estado clínico. La app no calcula medidas de emergencia.", "Consenso IRIS LRA; hiperpotasemia grave o no controlada puede requerir terapia renal sustitutiva.", "Potasio y ECG según gravedad; repetir tras cada intervención.", "https://www.iris-kidney.com/new-page-5", "No existe un umbral único independiente del laboratorio, ECG y presentación.")
if acidotic_cat:
    add_issue("Acidosis metabólica felina", "Valorar corrección", "Revisar dieta renal y causa; el consenso permite considerar citrato potásico o bicarbonato oral para mantener HCO₃⁻ >16 mmol/L. Si hiperpotasemia, evitar la opción con potasio.", "Consenso iCatCare 2026; la pauta se apoya en consenso y literatura clínica, no en una comparación robusta de ensayos.", "HCO₃⁻, K, estado ácido-base y tolerancia digestiva tras ajuste.", "https://journals.sagepub.com/doi/10.1177/1098612X261466553", "La corrección debe basarse en gasometría/química y causa; evitar alcalosis y carga de sodio/potasio inapropiada.")
if anemia_threshold:
    add_issue("Anemia asociada a ERC (posible)", "Investigar y valorar tratamiento", "IRIS 2026 sugiere tratar perros con HCT <30% o anemia persistente 30–35%; gatos <25% o persistente 25–28%. Antes de ESA/HIF-PHI buscar hierro bajo, sangrado, inflamación/infección, parásitos y otras causas.", "Guía IRIS 2026. La guía enumera opciones, pero el umbral no demuestra por sí solo causalidad renal.", "HCT/PCV y PA antes de cada dosis durante inducción; en mantenimiento cada 1–3 meses, además de hierro y efectos adversos.", "https://www.iris-kidney.com/iris-guidelines-1", "Dosis felina de darbepoetina se ofrece como pauta de consenso; perros: no se calcula en esta versión al no integrar una pauta IRIS 2026 específica verificada.")
if anemia_symptomatic:
    add_issue("Anemia sintomática", "Evaluación urgente", "Valorar estabilidad hemodinámica y transfusión/soporte inmediato según signos y hematocrito; los estimulantes eritropoyéticos tardan días-semanas y no sustituyen la estabilización.", "IRIS anemia review describe transfusión como opción para anemia severa/sintomática y señala riesgos de sobrecarga y reacción transfusional.", "HCT/PCV, perfusión, PA, signos respiratorios y sobrecarga durante cualquier transfusión.", "https://www.iris-kidney.com/treatment-of-anemia-in-cats-with-ckd", "La app no calcula transfusión ni sustituye tipaje/pruebas de compatibilidad.")
if nausea or appetite or weight_loss:
    add_issue("Signos gastrointestinales/nutricionales", "Tratar síntomas y causas concurrentes", "Valorar hidratación, estreñimiento, hipopotasemia, acidosis, anemia, dolor y comorbilidades. En gatos, consensos apoyan antieméticos; mirtazapina puede ayudar apetito/peso. Evitar supresión ácida sin sospecha de ulceración.", "Consenso iCatCare 2026; ensayos controlados con placebo en gatos ERC IRIS 2–3: maropitant redujo vómitos; mirtazapina redujo vómitos y aumentó apetito/peso.", "Ingesta, peso/BCS/MCS y vómitos; revisar respuesta y efectos adversos; considerar soporte enteral si hiporexia persistente.", "https://journals.sagepub.com/doi/10.1177/1098612X261466553", "La evidencia citada es felina; no extrapolar las dosis a perros.")
if dehydration:
    add_issue("Deshidratación/hipovolemia", "Corregir antes de ciertos fármacos", "Evaluar perfusión y causa; ajustar reposición bajo vigilancia. Evitar iniciar RAAS-inhibidores en paciente deshidratado/hipovolémico.", "IRIS AKI consensus summary y iCatCare feline CKD consensus.", "Peso, perfusión, hidratación, diuresis, PA y signos de sobrecarga.", "https://www.iris-kidney.com/new-page-5")
if oliguria_signal or volume_overload:
    add_issue("Oliguria/anuria o sobrecarga", "Urgencia", "No aumentar fluidos automáticamente. Revaluar balance y perfusión con urgencia; valorar UCI/nefrología y terapia renal sustitutiva si procede.", "Consenso IRIS LRA; exceso de fluidos puede causar sobrecarga potencialmente mortal.", "Diuresis, peso, balance y exploración al menos dos veces al día en hospital.", "https://www.iris-kidney.com/new-page-5")
if infection or obstruction:
    add_issue("Infección u obstrucción posible", "Buscar causa tratable", "Completar urianálisis/cultivo e imagen según presentación; obstrucción urinaria requiere evaluación inmediata. No iniciar antibiótico o procedimiento automáticamente desde esta herramienta.", "IRIS recomienda diferenciar causas renales, prerrenales y posrenales antes de atribuir azotemia a ERC.", "Cultivo/imagen y respuesta clínica según diagnóstico.", "https://www.iris-kidney.com/iris-staging-system")
if glomerular:
    add_issue("Sospecha de enfermedad glomerular", "Confirmar etiología antes de terapias específicas", "Cuantificar proteinuria, revisar albúmina, presión, sedimento, cultivo y causas infecciosas/sistémicas; valorar imagen, derivación y biopsia según riesgo. No iniciar inmunosupresión empírica desde esta regla.", "Consensos IRIS/ACVIM sobre enfermedad glomerular; la selección de inmunosupresión depende de diagnóstico etiológico y riesgo-beneficio.", "UPC, albúmina, PA, función renal y complicaciones trombóticas según caso.", "https://www.iris-kidney.com/iris-guidelines-1", "Esta versión no calcula inmunosupresores ni antitrombóticos por falta de indicación etiológica individual verificable.")
if hypoalbuminemia_confirmed:
    albumin_text = f"Albúmina medida: {albumin:.2f} g/dL. " if albumin > 0 else ""
    add_issue("Hipoalbuminemia", "Investigar causa y riesgo de complicaciones", albumin_text + "Correlacionar con UPC, pérdidas gastrointestinales, función hepática e inflamación; si coexiste proteinuria marcada, valorar riesgo trombótico individual. No iniciar antitrombótico automáticamente.", "IRIS/ACVIM glomerular kidney disease recommendations; riesgo y tratamiento dependen de diagnóstico y paciente.", "Albúmina, UPC, edema/derrame y signos de tromboembolismo según evolución.", "https://www.iris-kidney.com/iris-guidelines-1", "No hay una dosis antitrombótica renal universal implementada; se requiere valoración individual y evidencia de indicación.")
if nephrotoxins:
    add_issue("Exposición nefrotóxica", "Revisión farmacológica prioritaria", "Revisar indicación, exposición, alternativas, aclaramiento renal e interacciones; suspender/cambiar solo por decisión del veterinario responsable.", "Consenso IRIS LRA; estudios y guías de prevención de nefrotoxicidad.", "Creatinina y diuresis; en riesgo hospitalario, monitorización al menos diaria.", "https://www.iris-kidney.com/new-page-2")

# Clinical blocks.
t1, t2, t3, t4, t5 = st.tabs(["1 · Clasificación", "2 · Problemas", "3 · Plan y dosis", "4 · Evidencia", "5 · Seguimiento"])
with t1:
    st.subheader("Diagnóstico y clasificación")
    if mode == "ERC estable":
        if species == "Canino":
            cr_stage = 1 if current_creat < 1.4 else 2 if current_creat <= 2.7 else 3 if current_creat <= 5.0 else 4
            sdma_thresholds = "≤17 / 18–35 / 36–54 / >54 µg/dL"
        else:
            cr_stage = 1 if current_creat < 1.6 else 2 if current_creat <= 2.8 else 3 if current_creat <= 5.0 else 4
            sdma_thresholds = "≤17 / 18–25 / 26–38 / >38 µg/dL"
        cr_ranges = "<1,4 / 1,4–2,7 / 2,8–5,0 / >5,0 mg/dL" if species == "Canino" else "<1,6 / 1,6–2,8 / 2,9–5,0 / >5,0 mg/dL"
        st.markdown(f"- Estadio por creatinina: **IRIS {cr_stage}**. Cortes I–IV de creatinina: {cr_ranges}. Cortes de SDMA por estadio: {sdma_thresholds}.")
        if sdma > 0:
            st.markdown(f"- Estadio por SDMA: **IRIS {sdma_stage}**; clasificación de apoyo conservadora: **IRIS {final_stage}**.")
            if sdma_stage != cr_stage:
                st.warning("Creatinina y SDMA discrepan. Considerar masa muscular, ensayo de laboratorio, hidratación y repetir en 2–4 semanas; si persiste, IRIS aconseja considerar el estadio superior.")
        if ckd_confirmed and stable_hydrated and excluded_prepost:
            st.success(f"ERC estable: estadio IRIS {final_stage} · UPC {'proteinúrico' if proteinuric else 'limítrofe/no confirmado' if upc >= 0.2 else 'no proteinúrico'} · PA {'hipertensa' if hypertensive else 'sin hipertensión confirmada'}.")
        else:
            st.error("La app no valida un estadio final: confirma ERC, estabilidad/hidratación y exclusión de causas prerrenales/posrenales.")
        st.caption("En perros, estadio 2 llega hasta 2,7 mg/dL en la revisión IRIS vigente. En gatos, estadio 2 llega hasta 2,8 mg/dL. Estadio 1 requiere evidencia renal adicional; el valor aislado no diagnostica ERC.")
        if usg > 0:
            st.caption(f"USG ingresada: {usg:.3f}. Interpretar con hidratación, glucosuria, fármacos y contexto; por sí sola no confirma ERC.")
    else:
        st.write(f"- Creatinina basal: {baseline_creat:g} mg/dL; actual: {current_creat:.2f} mg/dL; cambio: {delta:+.2f} mg/dL" if delta is not None else f"- Sin basal registrada; creatinina actual {current_creat:.2f} mg/dL.")
        st.write(f"- Cambio ≥0,3 mg/dL en 48 h: **{'confirmado' if acute_signal else 'no confirmado'}**" + (f"; diferencia aritmética vs basal {delta:+.2f} mg/dL." if delta is not None else ".") + f" Grado LRA orientativo por creatinina: **{aki_grade}**.")
        if mode == "Agudización de ERC":
            st.info(f"Conservar el estadio basal {prior_stage}; registrar por separado el componente agudo. Un grado LRA no sustituye la etiología ni estima reversibilidad.")
        if aki_grade == "I" and not acute_signal:
            st.warning("No hay criterio de cambio agudo documentado para asignar grado I. Revisar tendencia, diuresis y urianálisis.")
        if oliguria_signal or volume_overload or obstruction or high_k_confirmed or aki_grade in {"II", "III", "IV", "V"}:
            st.error("Criterios de valoración urgente/hospitalaria. No usar la calculadora de fluidos para forzar diuresis.")
    st.markdown("**Subestadificación:** UPC y presión deben interpretarse con mediciones repetidas; la presencia de daño de órgano diana modifica la urgencia.")
with t2:
    st.subheader("Problemas clínicos tratables")
    st.caption("Las reglas resaltan problemas que requieren revisión; no sustituyen diagnóstico etiológico.")
    if not issues:
        st.info("No hay suficientes hallazgos ingresados para generar alertas específicas. Completa laboratorios y signos clínicos.")
    for issue in issues:
        with st.container(border=True):
            st.markdown(f"### [{issue_category(issue['title'])}] {issue['title']} · {issue['status']}")
            st.write(issue["action"])
            st.caption(f"Base: {issue['evidence']}")
            if issue["limit"]:
                st.caption(f"Límite/precaución: {issue['limit']}")
with t3:
    st.subheader("Plan terapéutico y cálculos")
    st.markdown("### Problemas detectados y siguiente paso")
    if issues:
        for issue in issues:
            st.markdown(f"- **{issue_category(issue['title'])} — {issue['title']}:** {issue['action']}")
    else:
        st.info("Completa datos clínicos para construir el plan de revisión.")

    st.markdown("### Calculadora de pautas publicadas")
    st.caption("Elige un régimen que corresponda a un problema confirmado. Se calcula cantidad por toma; no se redondea ni se transforma en receta.")
    options: dict[str, dict] = {}
    common_note = "Confirmación veterinaria, ficha técnica local, producto y monitorización requeridos."
    if species == "Felino":
        options = {
            "Telmisartán · proteinuria": dict(low=1, high=1, unit="mg/kg", interval="PO cada 24 h", kind="mass", issue="proteinuria", raas=True, source="Consenso iCatCare 2026; dosis 1 mg/kg/día para proteinuria felina.", evidence="Consenso de guía con referencias a ensayos clínicos; la publicación no asigna grado GRADE a esta dosis.", url="https://journals.sagepub.com/doi/10.1177/1098612X261466553", monitor="PA, creatinina y potasio a 1–2 semanas; UPC a 4 semanas; luego cada 3 meses si estable."),
            "Benazepril · proteinuria": dict(low=.25, high=.5, unit="mg/kg", interval="PO cada 12 h", kind="mass", issue="proteinuria", raas=True, source="Consenso iCatCare 2026: opción ACEI felina para proteinuria.", evidence="Consenso con datos de estudios clínicos; no se asigna nivel formal de certeza en la tabla de dosis.", url="https://journals.sagepub.com/doi/10.1177/1098612X261466553", monitor="PA, creatinina y potasio a 1–2 semanas; UPC a 4 semanas."),
            "Amlodipino · hipertensión": dict(low=.125, high=.25, unit="mg/kg", interval="PO cada 24 h", kind="mass", issue="hipertensión", raas=False, source="Consenso iCatCare 2026; opción felina de primera línea según gravedad y respuesta.", evidence="Guía/consenso; la dosis se apoya en estudios clínicos felinos.", url="https://journals.sagepub.com/doi/10.1177/1098612X261466553", monitor="PA a 1–2 semanas; vigilar hipotensión, debilidad, taquicardia y edema periférico."),
            "Telmisartán · hipertensión": dict(low=2, high=2, unit="mg/kg", interval="PO cada 24 h", kind="mass", issue="hipertensión", raas=True, source="Consenso iCatCare 2026; opción felina para hipertensión.", evidence="Guía/consenso basada en ensayos clínicos de hipertensión felina.", url="https://journals.sagepub.com/doi/10.1177/1098612X261466553", monitor="PA, creatinina y potasio a 1–2 semanas; vigilar hipotensión y empeoramiento de azotemia."),
            "Maropitant · náuseas/vómitos": dict(low=1, high=1, unit="mg/kg", interval="PO/SC/IV cada 24 h", kind="mass", issue="gastro", raas=False, source="Consenso iCatCare 2026; ensayo controlado en gatos con ERC IRIS 2–3 redujo vómitos.", evidence="Ensayo clínico placebo-controlado citado en consenso; beneficio probado para vómito en la población estudiada.", url="https://journals.sagepub.com/doi/10.1177/1098612X261466553", monitor="Vómitos, apetito, hidratación y dolor local si SC."),
            "Mirtazapina · apetito/náusea": dict(low=2, high=2, unit="mg/gato", interval="PO o transdérmica cada 24 h; considerar cada 48 h en ERC avanzada", kind="fixed", issue="gastro", raas=False, source="Consenso iCatCare 2026: 2 mg/gato; intervalo q48h puede reducir acumulación en ERC avanzada.", evidence="Ensayos controlados citados por consenso mostraron menor vómito y aumento de apetito/peso; la frecuencia q48h se apoya en farmacocinética/experiencia clínica.", url="https://journals.sagepub.com/doi/10.1177/1098612X261466553", monitor="Apetito, peso, vocalización/agitación y reacción cutánea si transdérmica."),
            "Citrato potásico · hipopotasemia": dict(low=1, high=4, unit="mEq/gato", interval="PO cada 12 h; ajustar a respuesta", kind="fixed", issue="potassium", raas=False, source="Consenso iCatCare 2026: 1–4 mEq/gato q12h en pacientes estables con hipopotasemia moderada-severa.", evidence="Recomendación de consenso; titulación por respuesta, no ensayo dosis-respuesta robusto.", url="https://journals.sagepub.com/doi/10.1177/1098612X261466553", monitor="Potasio, creatinina y signos neuromusculares/GI; evitar si hiperpotasemia."),
            "Citrato potásico · acidosis": dict(low=40, high=75, unit="mg/kg", interval="PO cada 12 h", kind="mass", issue="acidosis", raas=False, source="Consenso iCatCare 2026: citrato potásico 40–75 mg/kg q12h para mantener HCO₃⁻ >16 mmol/L.", evidence="Recomendación de consenso; la suplementación está en evaluación.", url="https://journals.sagepub.com/doi/10.1177/1098612X261466553", monitor="HCO₃⁻/CO₂ total, potasio y estado ácido-base; evitar si hiperpotasemia."),
            "Bicarbonato sódico · acidosis": dict(low=10, high=12, unit="mg/kg", interval="PO cada 8–12 h", kind="mass", issue="acidosis", raas=False, source="Consenso iCatCare 2026: bicarbonato sódico 10–12 mg/kg q8–12h para mantener HCO₃⁻ >16 mmol/L.", evidence="Recomendación de consenso; no se asigna grado formal de certeza.", url="https://journals.sagepub.com/doi/10.1177/1098612X261466553", monitor="HCO₃⁻/CO₂ total, sodio, potasio y estado ácido-base."),
            "Darbepoetina · anemia renal": dict(low=.75, high=1, unit="µg/kg", interval="SC cada 7 días durante inducción; espaciar según PCV bajo control veterinario", kind="mass", issue="anemia", raas=False, source="Consenso iCatCare 2026: dosis inicial felina 0,75–1 µg/kg semanal hasta PCV alrededor de 30%; IRIS 2026 define umbrales de intervención más bajos.", evidence="Consenso; respaldado por estudios clínicos de cohorte y práctica clínica, con riesgo de hipertensión y anticuerpos anti-EPO.", url="https://journals.sagepub.com/doi/10.1177/1098612X261466553", monitor="PA y PCV antes de cada dosis en inducción; hierro; luego cada 1–3 meses al estabilizar."),
        }
    else:
        options = {
            "Telmisartán · proteinuria": dict(low=1, high=1, unit="mg/kg", interval="PO cada 24 h", kind="mass", issue="proteinuria", raas=True, source="Brown et al., 2020, doble ciego aleatorizado: 39 perros con ERC/proteinuria; umbral UPC >0,5 si azotémico o ≥1,0 si no azotémico.", evidence="Ensayo clínico aleatorizado; 20 telmisartán vs 19 enalapril, 120 días. La combinación produjo azotemia clínicamente relevante en 4/13; no combinar automáticamente.", url="https://pmc.ncbi.nlm.nih.gov/articles/PMC7694823/", monitor="Creatinina, potasio, PA e hidratación a 1–2 semanas; UPC a 4 semanas y luego según respuesta."),
            "Enalapril · proteinuria": dict(low=.5, high=.5, unit="mg/kg", interval="PO cada 12 h", kind="mass", issue="proteinuria", raas=True, source="Brown et al., 2020, ensayo clínico canino de proteinuria renal persistente; enalapril fue el comparador activo.", evidence="Ensayo clínico aleatorizado de un centro (n=39 total); no usar combinación ACEI+ARB como si fuese segura: empeoramiento de azotemia en 4/13 perros combinados.", url="https://pmc.ncbi.nlm.nih.gov/articles/PMC7694823/", monitor="Creatinina, potasio, PA e hidratación a 1–2 semanas; UPC a 4 semanas."),
            "Telmisartán · hipertensión": dict(low=1, high=1, unit="mg/kg", interval="PO cada 24 h", kind="mass", issue="hipertensión", raas=True, source="Consenso ACVIM 2018: dosis de referencia en hipertensión canina.", evidence="Consenso con evidencia clínica veterinaria limitada; individualizar por proteinuria, PA, hidratación y respuesta.", url="https://pubmed.ncbi.nlm.nih.gov/30353952/", monitor="PA, creatinina, potasio e hidratación 1–2 semanas tras inicio/ajuste."),
            "Darbepoetina · anemia renal": dict(low=.45, high=1, unit="µg/kg", interval="SC cada 7 días durante inducción; espaciar tras respuesta", kind="mass", issue="anemia", raas=False, source="IRIS CKD anemia review: 0,45–1 µg/kg SC semanal; cohorte retrospectiva de 33 perros, 85% alcanzó PCV ≥30%.", evidence="Estudio observacional retrospectivo, no ensayo aleatorizado. IRIS informa hipertensión en 24/25 perros de la cohorte que requirieron tratamiento; revisar autorización local.", url="https://www.iris-kidney.com/treatment-of-anemia-in-cats-with-ckd", monitor="PA y HCT/PCV antes de cada dosis en inducción; hierro; vigilar hipertensión, hiperpotasemia y signos neurológicos."),
            "Amlodipino · hipertensión grave": dict(low=.1, high=.5, unit="mg/kg", interval="PO cada 24 h; solo como parte del plan de hipertensión grave", kind="mass", issue="hypertension_severe", raas=False, source="Consenso ACVIM 2018: en perros con SBP >200 mmHg puede iniciarse RAAS-inhibidor más bloqueador de canal de calcio; intervalo de dosis citado 0,1–0,5 mg/kg q24h.", evidence="Consenso ACVIM; evidencia en hipertensión canina limitada y decisiones individualizadas.", url="https://pubmed.ncbi.nlm.nih.gov/30353952/", monitor="PA seriada estrecha y revisión de perfusión, hidratación y creatinina."),
        }

    selected = st.selectbox("Pauta publicada (la selección no equivale a prescripción)", list(options))
    regimen = options[selected]
    calculate_reference = st.checkbox("Calcular esta pauta de referencia (revisión veterinaria confirmada)")
    if species == "Canino" and selected.startswith("Amlodipino"):
        raas_plan_confirmed = st.checkbox("El plan clínico ya contempla el bloqueador RAAS concomitante para hipertensión canina grave")
    else:
        raas_plan_confirmed = True
    formulation = st.number_input("Concentración (mg/mL o µg/mL según unidad; 0 si no aplica)", min_value=0.0, value=0.0, step=0.1, format="%.3f")
    mEq_conc = st.number_input("Concentración de potasio (mEq/mL; 0 si no aplica)", min_value=0.0, value=0.0, step=0.1, format="%.2f")
    if regimen["issue"] == "proteinuria":
        eligible = proteinuric
    elif regimen["issue"] == "hipertensión":
        eligible = hypertensive
    elif regimen["issue"] == "hypertension_severe":
        eligible = sbp > 200 and (bp_confirmed or tod) and raas_plan_confirmed
    elif regimen["issue"] == "gastro":
        eligible = nausea or appetite or weight_loss
    elif regimen["issue"] == "potassium":
        eligible = low_k_confirmed and species == "Felino"
    elif regimen["issue"] == "acidosis":
        eligible = species == "Felino" and bicarbonate > 0 and bicarbonate < 16
    else:
        eligible = anemia_threshold and hct > 0
    blocked = (mode != "ERC estable" or not ckd_confirmed or not stable_hydrated or dehydration) or (regimen["raas"] and (high_k_confirmed or hypotension or nephrotoxins)) or (selected.startswith("Citrato") and (high_k_confirmed or potassium <= 0)) or (regimen["issue"] == "potassium" and (not low_k_confirmed or potassium <= 0)) or (regimen["issue"] == "anemia" and anemia_symptomatic)
    if not calculate_reference:
        st.info("Selecciona la pauta adecuada y confirma que quieres ver el cálculo aritmético; la aplicación no propone ni inicia el tratamiento automáticamente.")
    elif not eligible:
        st.warning("No se cumplen los datos de elegibilidad registrados para esta indicación; no se calcula una dosis.")
    elif blocked:
        st.error("Cálculo bloqueado por inestabilidad, anemia sintomática, deshidratación/hipovolemia, hipotensión, posible LRA, exposición nefrotóxica o riesgo de potasio. Resolver/revaluar antes de considerar la pauta.")
    else:
        st.markdown(f"**Fuente/tipo:** {regimen['source']}  \n**Evidencia:** {regimen['evidence']}  \n**Monitorización:** {regimen['monitor']}")
        regimen_interval = regimen["interval"]
        if species == "Felino" and selected.startswith("Mirtazapina"):
            regimen_interval = "PO o transdérmica cada 48 h como referencia por ERC avanzada" if final_stage >= 3 else "PO o transdérmica cada 24 h como referencia inicial"
        st.markdown(f"**Vía/intervalo publicado:** {regimen_interval}")
        if regimen["kind"] == "fixed":
            quantity_low, quantity_high = regimen["low"], regimen["high"]
            amount = f"{quantity_low:g} {regimen['unit']} por toma" if quantity_low == quantity_high else f"{quantity_low:g}–{quantity_high:g} {regimen['unit']} por toma"
            if mEq_conc > 0 and regimen["unit"] == "mEq/gato":
                amount += f" · volumen aritmético {quantity_low/mEq_conc:.3g}–{quantity_high/mEq_conc:.3g} mL"
            elif formulation > 0 and regimen["unit"] == "mg/gato":
                amount += f" · volumen aritmético {quantity_low/formulation:.3g} mL"
        else:
            quantity_low = weight * regimen["low"]
            quantity_high = weight * regimen["high"]
            amount = f"{quantity_low:.3g}–{quantity_high:.3g} {regimen['unit'].split('/')[0]} por toma"
            if formulation > 0:
                amount += f" · volumen aritmético {quantity_low/formulation:.3g}–{quantity_high/formulation:.3g} mL"
        st.metric("Cantidad calculada", amount)
        st.info("Resultado matemático sin redondeo. En mirtazapina se calcula por gato; en citrato potásico para hipopotasemia, en mEq/gato. No equivale a una dosis prescrita.")
        st.caption(f"Fuente: [{regimen['url']}]({regimen['url']})")

    with st.expander("Calculadora aritmética de una pauta ya prescrita"):
        st.caption("Úsala solo para transcribir una orden veterinaria confirmada. No selecciona fármaco, dosis ni frecuencia.")
        prescribed = st.number_input("Dosis prescrita (valor numérico)", min_value=0.0, value=0.0, step=0.1, key="custom_dose")
        prescribed_unit = st.selectbox("Unidad de la dosis", ["mg/kg por toma", "µg/kg por toma", "mEq/kg por toma", "mg por gato/toma", "mEq por gato/toma"])
        prescribed_route = st.text_input("Vía indicada en la orden", placeholder="p. ej., PO, SC")
        prescribed_interval = st.text_input("Intervalo indicado en la orden", placeholder="p. ej., cada 12 h")
        product_conc = st.number_input("Concentración del producto (misma unidad base por mL; 0 si no es líquido)", min_value=0.0, value=0.0, step=0.1, key="custom_conc")
        if prescribed > 0:
            per_dose = prescribed * weight if "/kg" in prescribed_unit else prescribed
            base_unit = prescribed_unit.split(" ")[0]
            st.write(f"Cantidad por toma: **{per_dose:.4g} {base_unit}** · Vía: **{prescribed_route or 'no indicada'}** · Intervalo: **{prescribed_interval or 'no indicado'}**")
            if product_conc > 0:
                st.write(f"Volumen aritmético: **{per_dose/product_conc:.4g} mL por toma**")

with t4:
    st.subheader("Evidencia científica y fuentes")
    st.write("La app describe diseño, población y limitaciones disponibles. No convierte tipos de publicación en grados de certeza ni inventa porcentajes de acuerdo.")
    sources = [
        ("IRIS Guidelines 2026", "Guía de consenso actualizada: clasificación/ tratamiento ERC perros y gatos, gradación LRA y nuevos umbrales de anemia. La guía advierte que algunas dosis son empíricas y requieren valoración riesgo-beneficio.", "https://www.iris-kidney.com/iris-guidelines-1"),
        ("IRIS best practice consensus on AKI (2024), resumen 2026", "Consenso de mejores prácticas para perros y gatos, publicado en The Veterinary Journal 305 (2024), 106068; revisión de diagnóstico, fluidos, electrolitos, nefrotóxicos y seguimiento. IRIS señala que parte de las recomendaciones se basa en consenso experto y que el grado no predice por sí solo reversibilidad.", "https://doi.org/10.1016/j.tvjl.2024.106068"),
        ("iCatCare feline CKD consensus 2026", "Consenso clínico para gatos con ERC; revisa estudios primarios por complicación e incluye dosis y monitorización. No usa una escala GRADE explícita en las recomendaciones consultadas.", "https://journals.sagepub.com/doi/10.1177/1098612X261466553"),
        ("ACVIM systemic hypertension consensus 2018", "Consenso para perros y gatos; incluye método de medición, categorías de riesgo y tratamiento individualizado por especie/comorbilidad.", "https://pubmed.ncbi.nlm.nih.gov/30353952/"),
        ("Brown et al., 2020 — telmisartan vs enalapril in dogs", "Ensayo clínico prospectivo, aleatorizado y doble ciego, un centro, 39 perros con ERC/proteinuria, seguimiento 120 días. No es evidencia universal: muestra pequeña; azotemia relevante con combinación en 4/13.", "https://pmc.ncbi.nlm.nih.gov/articles/PMC7694823/"),
        ("Chalhoub et al., 2012 — darbepoetin in cats", "Serie retrospectiva de 25 gatos de 66 tratados, anemia por ERC; 14/25 alcanzaron PCV ≥25% al día 56. Selección por disponibilidad de seguimiento y posibilidad de sesgo; efectos adversos incluyeron hipertensión.", "https://onlinelibrary.wiley.com/doi/10.1111/j.1939-1676.2011.00864.x"),
        ("Fiocchi et al., 2017 — darbepoetin in dogs", "Estudio multicéntrico retrospectivo de 33 perros con ERC; 28/33 alcanzaron PCV ≥30%. No aleatorizado; se notificaron eventos adversos y no equivale a una prescripción segura para todo paciente.", "https://pubmed.ncbi.nlm.nih.gov/28256075/"),
        ("IRIS CKD staging system", "Guía para perros y gatos: diagnosticar antes de estadificar, paciente estable/hidratado, interpretación de creatinina/SDMA, UPC y PA; discordancias requieren contexto y repetición.", "https://www.iris-kidney.com/iris-staging-system"),
    ]
    for title, note, url in sources:
        with st.container(border=True):
            st.markdown(f"**[{title}]({url})**")
            st.write(note)
    st.info("La certeza o el nivel de evidencia se indica solo cuando la fuente lo evalúa explícitamente. ‘Consenso’, ‘ensayo clínico’ y ‘estudio observacional’ son diseños/tipos de evidencia, no equivalen por sí solos a una calificación GRADE.")
with t5:
    st.subheader("Seguimiento y reevaluación")
    if issues:
        for issue in issues:
            st.markdown(f"- **{issue['title']}:** {issue['monitoring']} [Fuente]({issue['source']})")
    st.markdown("#### Objetivos y criterios de respuesta")
    st.markdown("- Proteinuria: documentar tendencia descendente de UPC con creatinina estable; aumento de creatinina/UPC obliga a reevaluar causa y tolerancia.")
    st.markdown("- Hipertensión: reducir riesgo de daño de órgano diana, evitando hipotensión; registrar varias lecturas y técnica.")
    st.markdown("- Fósforo: objetivo depende de especie/estadio y guía vigente; repetir tras cambio dietario/quelante, no ajustar a ciegas.")
    st.markdown("- Anemia: confirmar persistencia y causas corregibles; monitorizar hematocrito, presión, hierro y respuesta antes de cambiar frecuencia.")
    st.markdown("- LRA: primer control pocos días tras alta; IRIS aconseja vigilancia de función renal al menos cada 3 meses durante el primer año tras LRA, ajustada a evolución.")
    st.markdown("#### Criterios de escalada")
    if aki_grade in {"II", "III", "IV", "V"} or oliguria_signal or volume_overload or obstruction or high_k_confirmed or anemia_symptomatic or sbp > 200 or tod:
        st.error("Derivación/hospitalización prioritaria: LRA azotémica, oliguria/anuria, sobrecarga, obstrucción, hiperpotasemia confirmada o hipertensión con daño de órgano diana/grave.")
    elif sbp >= 180:
        st.warning("PA sistólica ≥180 mmHg: confirmación y valoración clínica prioritaria; la hospitalización depende de daño de órgano diana, cifras, estabilidad y contexto.")
    else:
        st.write("Escalar si empeora creatinina/SDMA, UPC, PA, potasio, acidosis, fósforo, hematocrito, ingesta, peso o signos clínicos; valorar nefrología si no se controlan complicaciones.")

st.divider()
st.caption("Alcance actual: cubre clasificación, alertas de complicaciones y varios regímenes con dosis publicadas. Cuando faltan datos, la evidencia es débil o el régimen no está suficientemente respaldado para la especie, la aplicación lo señala y no calcula una dosis. Debe validarse clínicamente antes de uso asistencial.")
