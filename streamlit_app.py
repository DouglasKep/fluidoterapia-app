import streamlit as st

# --- Configuración de la página ---
title = 'Fluidoterapia Caninos y Felinos'
st.set_page_config(page_title=title, layout='wide')
st.markdown(f"# **{title}**", unsafe_allow_html=True)

# --- Estilos personalizados ---
st.markdown("""
    <style>
    /* Contenedor principal suavizado */
    .main .block-container {
        background-color: rgba(255,255,255,0.85);
        border-radius: 12px;
        padding: 20px;
        box-shadow: 0 8px 24px rgba(0,0,0,0.1);
    }
    /* Sidebar con sombra suave */
    .sidebar .sidebar-content {
        background-color: #ffffffee;
        padding: 20px;
        border-radius: 10px;
        box-shadow: 0 6px 20px rgba(0,0,0,0.08);
    }
    /* Expander como tarjeta */
    .stExpander {
        box-shadow: 0 4px 12px rgba(0,0,0,0.08);
        border-radius: 8px;
    }
    /* Inputs y selects con sombras internas */
    input, select, .stNumberInput>div>div, .stSelectbox>div>div {
        box-shadow: inset 0 2px 6px rgba(0,0,0,0.1);
        border-radius: 6px;
        border: 1px solid #cbd2d9;
    }
    /* Botones primarios estilizados */
    .stButton>button {
        background-color: #0077b6;
        color: white;
        border: none;
        border-radius: 6px;
        padding: 10px 20px;
        font-weight: 600;
        transition: background-color 0.2s ease, transform 0.1s ease;
    }
    .stButton>button:hover {
        background-color: #005f86;
        transform: translateY(-2px);
    }
    /* Métricas en tarjetas interactivas */
    .stMetric {
        background-color: #ffffffdd;
        border-radius: 10px;
        padding: 14px;
        box-shadow: 0 6px 18px rgba(0,0,0,0.1);
        transition: transform 0.2s ease;
        color: #333333;
    }
    .stMetric:hover {
        transform: scale(1.04);
    }
    /* Color de los valores y deltas en metric */
    .stMetric .value {
        color: #000000 !important;
    }
    .stMetric .delta {
        color: #0077b6 !important;
    }
    </style>
""", unsafe_allow_html=True)

# --- Sidebar: Entradas agrupadas ---
with st.sidebar.expander('Datos del Paciente', expanded=True):
    species = st.selectbox('Especie', ['Perro', 'Gato'])
    weight = st.number_input('Peso (kg)', min_value=0.0, format='%.1f')
    dehydration = st.number_input('% Deshidratación', min_value=0.0, format='%.1f')
    state = st.selectbox('Estado', ['Mantenimiento', 'Reposición', 'Shock'])
    sens_loss = st.number_input('Pérdidas sensibles (ml)', min_value=0.0, format='%.1f')
    insens_loss = st.number_input('Pérdidas insensibles (ml)', min_value=0.0, format='%.1f')

with st.sidebar.expander('Venoclisis', expanded=False):
    venous_set = st.selectbox('Tipo de Venoclisis', ['Macrogoteo (20 gtt/ml)', 'Macrogoteo (10 gtt/ml)', 'Microgoteo (60 gtt/ml)'])
    if '10' in venous_set:
        drop_factor = 10
    elif '20' in venous_set:
        drop_factor = 20
    else:
        drop_factor = 60

# --- Referencias ---
with st.expander('Referencias de Guía', expanded=False):
    st.markdown('- **Mantenimiento:** Perro 60 ml/kg/día, Gato 40 ml/kg/día')
    st.markdown('- **Déficit:** (% deshidratación × peso (kg) × 1000) ml')
    st.markdown('- **Shock (bolo):** Perro 20 ml/kg en 15 min, Gato 10 ml/kg en 15 min')
    st.markdown('- **Pérdidas sensibles:** Diarrea/vómitos clínicamente evaluado')
    st.markdown('- **Pérdidas insensibles:** 2–4 ml/kg/h según guía clínica')
    st.markdown(f'- **Venoclisis:** {venous_set}')

# --- Función de cálculo ---
def calculate():
    maint = (60 if species == 'Perro' else 40) * weight
    deficit = (dehydration / 100) * weight * 1000
    if state == 'Mantenimiento':
        base = maint
    elif state == 'Reposición':
        base = maint + deficit
    else:  # Shock
        base = (20 if species == 'Perro' else 10) * weight
    vol_total = base + sens_loss + insens_loss
    ml_per_hr = vol_total / 24 if state != 'Shock' else vol_total / 0.25
    ml_per_min = ml_per_hr / 60
    drops_per_min = ml_per_min * drop_factor
    drops_per_sec = drops_per_min / 60
    sec_per_drop = 1 / drops_per_sec if drops_per_sec > 0 else None
    return maint, deficit, base, sens_loss, insens_loss, vol_total, ml_per_hr, ml_per_min, drops_per_min, drops_per_sec, sec_per_drop

# --- Botón y resultados ---
if st.sidebar.button('Calcular'):
    m, d, b, sl, il, tot, mlh, mlm, dpm, dps, spd = calculate()
    st.subheader('Resultados Rápidos')
    col1, col2, col3 = st.columns(3)
    col1.metric('Mantenimiento (ml)', f'{m:.0f}')
    col2.metric('Déficit (ml)', f'{d:.0f}')
    col3.metric('Total (ml)', f'{tot:.0f}')

    st.subheader('Detalle de Tasas e Intervalos')
    dt1, dt2 = st.columns(2)
    dt1.metric('ml/h', f'{mlh:.1f}')
    dt1.metric('ml/min', f'{mlm:.2f}')
    dt2.metric('gtt/min', f'{dpm:.1f}')
    dt2.metric('gtt/s', f'{dps:.2f}')
    if spd:
        st.write(f'**Intervalo práctico:** 1 gota cada {round(spd)} segundos')

# --- Pie de página ---
st.markdown('---')
st.markdown('⚠️ **Nota:** Reevalúe y recalcule la fluidoterapia periódicamente. Basado en AAHA/AAFP Fluid Therapy Guidelines for Dogs and Cats')
