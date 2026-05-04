import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt

from config import Config
from simulation import run_simulation


# =========================================================
# PAGE CONFIG
# =========================================================

st.set_page_config(
    page_title="VMC Smart Control System",
    layout="wide",
)

st.title("VMC Smart Control System")
st.caption(
    "Simulatore multi-agente con controllo MPC leggero per qualità dell’aria indoor, "
    "CO₂, umidità, portata reale, pressione condotta e costo energetico."
)


# =========================================================
# SIDEBAR
# =========================================================

with st.sidebar:
    st.header("Parametri")

    hours = st.slider("Durata simulazione (ore)", 6, 72, 24)

    timestep_minutes = st.selectbox(
        "Step temporale (minuti)",
        [1, 5, 10, 15],
        index=1,
    )

    fixed_occupants = st.slider(
        "Occupanti principali",
        1,
        10,
        3,
    )

    room_volume_m3 = st.slider(
        "Volume ambiente (m³)",
        40,
        300,
        120,
    )

    outdoor_humidity = st.slider(
        "Umidità esterna (%)",
        20,
        100,
        65,
    )

    outdoor_temp = st.slider(
        "Temperatura esterna (°C)",
        -10,
        40,
        10,
    )

    indoor_temp = st.slider(
        "Temperatura interna (°C)",
        15,
        30,
        22,
    )

    electricity_price = st.number_input(
        "Prezzo energia (€/kWh)",
        min_value=0.05,
        max_value=1.00,
        value=0.30,
        step=0.01,
    )

    st.subheader("Parametri tecnici VMC")

    filter_status = st.selectbox(
        "Stato filtro VMC",
        ["Pulito", "Medio", "Sporco"],
    )

    duct_area_m2 = st.slider(
        "Sezione condotta (m²)",
        min_value=0.010,
        max_value=0.080,
        value=0.031,
        step=0.001,
    )

    control_mode = st.selectbox(
        "Modalità controllo",
        ["Reattivo", "Predittivo"],
        index=1,
    )

# =========================================================
# CONFIG
# =========================================================

def make_config(mode):
    return Config(
        hours=hours,
        timestep_minutes=timestep_minutes,
        fixed_occupants=fixed_occupants,
        room_volume_m3=room_volume_m3,
        outdoor_humidity_pct=outdoor_humidity,
        outdoor_temp_c=outdoor_temp,
        indoor_temp_c=indoor_temp,
        electricity_price_eur_kwh=electricity_price,
        filter_status=filter_status,
        duct_area_m2=duct_area_m2,
        control_mode=mode,
    )


config = make_config(control_mode)


# =========================================================
# RUN SIMULATION
# =========================================================

df = run_simulation(config)

df_reactive = run_simulation(make_config("Reattivo"))
df_predictive = run_simulation(make_config("Predittivo"))

hours_factor = config.timestep_minutes / 60
last = df.iloc[-1]


# =========================================================
# KPI PRINCIPALI
# =========================================================

col1, col2, col3, col4 = st.columns(4)

col1.metric("CO₂ media", f"{df['co2_ppm'].mean():.0f} ppm")
col2.metric("Picco CO₂", f"{df['co2_ppm'].max():.0f} ppm")
col3.metric("Umidità media", f"{df['humidity_pct'].mean():.1f}%")
col4.metric("Costo totale", f"€ {df['cumulative_cost_eur'].iloc[-1]:.2f}")

col5, col6, col7 = st.columns(3)

col5.metric(
    "Ore VMC alta",
    f"{(df['vmc'] == 'alta').sum() * hours_factor:.1f} h",
)

col6.metric(
    "Ore deumidificatore ON",
    f"{df['dehumidifier'].sum() * hours_factor:.1f} h",
)

col7.metric(
    "Ore finestra aperta",
    f"{df['window_open'].sum() * hours_factor:.1f} h",
)

st.divider()

# =========================================================
# CONFRONTO REATTIVO VS PREDITTIVO
# =========================================================


st.subheader("Confronto diretto: Reattivo vs Predittivo")

reactive_cost = df_reactive["cumulative_cost_eur"].iloc[-1]predictive_cost = df_predictive["cumulative_cost_eur"].iloc[-1]

reactive_high_h = (df_reactive["vmc"] == "alta").sum() * hours_factor
predictive_high_h = (df_predictive["vmc"] == "alta").sum() * hours_factor

reactive_dehum_h = df_reactive["dehumidifier"].sum() * hours_factor
predictive_dehum_h = df_predictive["dehumidifier"].sum() * hours_factor

reactive_boost_h = df_reactive["predictive_boost"].sum() * hours_factor
predictive_boost_h = df_predictive["predictive_boost"].sum() * hours_factor

comparison_data = {
    "Parametro": [
        "CO₂ media",
        "Picco CO₂",
        "Umidità media",
        "Costo totale",
        "Ore VMC alta",
        "Ore deumidificatore",
        "Ore intervento MPC",
    ],
    "Reattivo": [
        f"{df_reactive['co2_ppm'].mean():.0f} ppm",
        f"{df_reactive['co2_ppm'].max():.0f} ppm",
        f"{df_reactive['humidity_pct'].mean():.1f}%",
        f"€ {reactive_cost:.2f}",
        f"{reactive_high_h:.1f} h",
        f"{reactive_dehum_h:.1f} h",
        f"{reactive_boost_h:.1f} h",
    ],
    "Predittivo / MPC": [
        f"{df_predictive['co2_ppm'].mean():.0f} ppm",
        f"{df_predictive['co2_ppm'].max():.0f} ppm",
        f"{df_predictive['humidity_pct'].mean():.1f}%",
        f"€ {predictive_cost:.2f}",
        f"{predictive_high_h:.1f} h",
        f"{predictive_dehum_h:.1f} h",
        f"{predictive_boost_h:.1f} h",
    ],
}

comparison_df = pd.DataFrame(comparison_data)
st.table(comparison_df.set_index("Parametro"))

delta_peak = df_predictive["co2_ppm"].max() - df_reactive["co2_ppm"].max()
delta_cost = predictive_cost - reactive_cost

if delta_peak < 0:
    st.success(
        f"Il controllo MPC riduce il picco CO₂ di {abs(delta_peak):.0f} ppm "
        f"con una variazione di costo pari a € {delta_cost:.2f}."
)
else:
    st.warning(
        f"In questo scenario il controllo predittivo non riduce il picco CO₂. "
        f"Variazione picco: {delta_peak:.0f} ppm, variazione costo: € {delta_cost:.2f}."
    )
st.subheader("Confronto andamento CO₂")

fig_compare, ax_compare = plt.subplots()

ax_compare.plot(
    df_reactive["ora"],
    df_reactive["co2_ppm"],
    label="Controllo reattivo",
)

ax_compare.plot(
    df_predictive["ora"],
    df_predictive["co2_ppm"],
    label="Controllo predittivo",
)

ax_compare.axhline(
    config.co2_comfort_ppm,
    linestyle="--",
    label="Soglia comfort",
)

ax_compare.axhline(
    config.co2_warning_ppm,
    linestyle=":",
    label="Soglia attenzione",
)

ax_compare.set_xlabel("Ora")
ax_compare.set_ylabel("CO₂ (ppm)")
ax_compare.legend()

st.pyplot(fig_compare)

st.divider()

# =========================================================
# DECISIONE MULTI-AGENTE
# =========================================================

st.subheader("Decisione multi-agente")

col_a, col_b, col_c, col_d = st.columns(4)

col_a.metric("Stato qualità aria", last["air_quality_status"])
col_b.metric("Stato umidità", last["humidity_status"])
col_c.metric("VMC attuale", last["vmc"])
col_d.metric("Deumidificatore", "ON" if last["dehumidifier"] else "OFF")

with st.expander("Spiegazione degli agenti"):
    st.write("**Energy Agent:**", last["energy_reason"])
    st.write("**Window Agent:**", last["window_reason"])

# =========================================================
# CO2 TREND / PREVISIONE BREVE
# =========================================================

st.subheader("Trend CO₂ e previsione breve")

col_p1, col_p2, col_p3, col_p4, col_p5 = st.columns(5)

col_p1.metric(
    "Trend CO₂",
    f"{last['co2_trend_ppm_h']:.0f} ppm/h",
)

col_p2.metric(
    "Previsione 15 min",
    f"{last['co2_forecast_15m']:.0f} ppm",
)

col_p3.metric(
    "Previsione 30 min",
    f"{last['co2_forecast_30m']:.0f} ppm",
)

col_p4.metric(
    "Stato trend",
    last["co2_trend_status"],
)

col_p5.metric(
    "MPC attivo ora",
    "ON" if last["predictive_boost"] else "OFF",
)

if last["predictive_boost"]:
    st.warning(last["predictive_reason"])
else:
    st.info(last["predictive_reason"])



# =================# =========================================================
# RIEPILOGO DECISIONI
# =========================================================

st.subheader("Riepilogo decisioni del sistema")

vmc_counts = df["vmc"].value_counts()

vmc_bassa_h = vmc_counts.get("bassa", 0) * hours_factor
vmc_media_h = vmc_counts.get("media", 0) * hours_factor
vmc_alta_h = vmc_counts.get("alta", 0) * hours_factor
dehum_h = df["dehumidifier"].sum() * hours_factor

boost_series = df["predictive_boost"].astype(bool)
predictive_boost_h = boost_series.sum() * hours_factor
predictive_boost_count = (boost_series & ~boost_series.shift(fill_value=False)).sum()

col_r1, col_r2, col_r3, col_r4 = st.columns(4)

col_r1.metric("VMC bassa", f"{vmc_bassa_h:.1f} h")
col_r2.metric("VMC media", f"{vmc_media_h:.1f} h")
col_r3.metric("VMC alta", f"{vmc_alta_h:.1f} h")
col_r4.metric("Deumidificatore", f"{dehum_h:.1f} h")

col_b1, col_b2 = st.columns(2)

col_b1.metric(
    "Ore intervento MPC",
    f"{predictive_boost_h:.1f} h",
)

col_b2.metric(
    "Interventi MPC",
    f"{predictive_boost_count}"
)

# =========================================================
# ANALISI TECNICA VMC
# =========================================================

st.subheader("Analisi tecnica VMC")

col_t1, col_t2, col_t3, col_t4 = st.columns(4)

col_t1.metric("Portata reale", f"{last['airflow_real_m3h']:.0f} m³/h")
col_t2.metric("Pressione condotta", f"{last['duct_pressure_pa']:.0f} Pa")
col_t3.metric("Velocità aria", f"{last['air_velocity_ms']:.1f} m/s")
col_t4.metric("Rischio rumore", last["noise_risk"])

with st.expander("Spiegazione tecnica VMC"):
    st.write(last["duct_reason"])

# =========================================================
# INTERPRETAZIONE AUTOMATICA
# =========================================================

co2_mean = df["co2_ppm"].mean()
co2_peak = df["co2_ppm"].max()
humidity_mean = df["humidity_pct"].mean()

if co2_peak > config.co2_warning_ppm:
    st.warning(
        f"CO₂ media buona ({co2_mean:.0f} ppm), "
        f"ma ci sono picchi fino a {co2_peak:.0f} ppm."
    )
elif co2_mean < config.co2_comfort_ppm:
    st.success("Qualità aria buona: CO₂ media sotto soglia comfort.")
else:
    st.warning("Qualità aria accettabile, ma migliorabile.")

if humidity_mean < config.humidity_warning_pct:
    st.success("Umidità sotto controllo.")
else:
    st.warning("Umidità elevata: possibile rischio comfort/muffa.")


# =========================================================
# GRAFICO CO2
# =========================================================

st.subheader("Andamento CO₂")

fig1, ax1 = plt.subplots()
ax1.plot(df["ora"], df["co2_ppm"], label="CO₂ interna")
ax1.axhline(config.co2_comfort_ppm, linestyle="--", label="Soglia comfort")
ax1.axhline(config.co2_warning_ppm, linestyle=":", label="Soglia attenzione")
ax1.set_xlabel("Ora")
ax1.set_ylabel("CO₂ (ppm)")
ax1.legend()
st.pyplot(fig1)
st.subheader("Previsione CO₂ a breve termine")

fig_pred, ax_pred = plt.subplots()
ax_pred.plot(df["ora"], df["co2_ppm"], label="CO₂ reale")
ax_pred.plot(df["ora"], df["co2_forecast_15m"], label="Previsione 15 min")
ax_pred.plot(df["ora"], df["co2_forecast_30m"], label="Previsione 30 min")
ax_pred.axhline(config.co2_warning_ppm, linestyle=":", label="Soglia attenzione")
ax_pred.set_xlabel("Ora")
ax_pred.set_ylabel("CO₂ (ppm)")
ax_pred.legend()
st.pyplot(fig_pred)


# =========================================================
# GRAFICO UMIDITÀ
# =========================================================

st.subheader("Andamento umidità")

fig2, ax2 = plt.subplots()
ax2.plot(df["ora"], df["humidity_pct"], label="Umidità aria")
ax2.plot(df["ora"], df["wall_moisture_pct"], label="Massa edificio")
ax2.axhline(config.humidity_warning_pct, linestyle="--", label="Soglia umidità")
ax2.set_xlabel("Ora")
ax2.set_ylabel("Umidità (%)")
ax2.legend()
st.pyplot(fig2)


# =========================================================
# GRAFICO LIVELLO VMC
# =========================================================

st.subheader("Livello VMC")

vmc_map = {
    "bassa": 1,
    "media": 2,
    "alta": 3,
}

df["vmc_numeric"] = df["vmc"].map(vmc_map)

fig3, ax3 = plt.subplots()
ax3.step(df["ora"], df["vmc_numeric"], where="post")
ax3.set_yticks([1, 2, 3])
ax3.set_yticklabels(["bassa", "media", "alta"])
ax3.set_xlabel("Ora")
ax3.set_ylabel("Livello VMC")
st.pyplot(fig3)


# =========================================================
# GRAFICI TECNICI VMC
# =========================================================

st.subheader("Andamento tecnico VMC")

fig4, ax4 = plt.subplots()
ax4.plot(df["ora"], df["airflow_real_m3h"], label="Portata reale")
ax4.set_xlabel("Ora")
ax4.set_ylabel("Portata (m³/h)")
ax4.legend()
st.pyplot(fig4)

fig5, ax5 = plt.subplots()
ax5.plot(df["ora"], df["duct_pressure_pa"], label="Pressione condotta")
ax5.axhline(config.fan_available_pressure_pa, linestyle="--", label="Pressione disponibile ventilatore")
ax5.set_xlabel("Ora")
ax5.set_ylabel("Pressione (Pa)")
ax5.legend()
st.pyplot(fig5)

fig6, ax6 = plt.subplots()
ax6.plot(df["ora"], df["air_velocity_ms"], label="Velocità aria")
ax6.axhline(2.5, linestyle="--", label="Soglia rischio medio")
ax6.axhline(4.0, linestyle=":", label="Soglia rischio alto")
ax6.set_xlabel("Ora")
ax6.set_ylabel("Velocità (m/s)")
ax6.legend()
st.pyplot(fig6)


# =========================================================
# REGISTRO SIMULAZIONE
# =========================================================

with st.expander("Registro simulazione"):
    st.dataframe(df, use_container_width=True)


# =========================================================
# DOWNLOAD CSV
# =========================================================

csv = df.to_csv(index=False).encode("utf-8")

st.download_button(
    label="Scarica CSV",
    data=csv,
    file_name="vmc_smart_control_results.csv",
    mime="text/csv",
)