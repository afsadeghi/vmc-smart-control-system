import pandas as pd

from config import Config
from environment import Environment
from orchestrator import Orchestrator


def occupant_profile(hour, fixed_occupants):
    """
    Profilo base:
    - notte: 2 persone
    - mattina: fixed_occupants
    - giorno: 0 persone
    - sera: fixed_occupants
    """

    if 0 <= hour < 7:
        return min(2, fixed_occupants)

    if 7 <= hour < 9:
        return fixed_occupants

    if 9 <= hour < 18:
        return 0

    if 18 <= hour < 23:
        return fixed_occupants

    return min(2, fixed_occupants)


def compute_step_cost(vmc_level, dehumidifier_on, config):
    hours = config.timestep_minutes / 60

    if vmc_level == "alta":
        power_w = config.vmc_high_power_w
    elif vmc_level == "media":
        power_w = config.vmc_medium_power_w
    else:
        power_w = config.vmc_low_power_w

    if dehumidifier_on:
        power_w += config.dehumidifier_power_w

    return (power_w / 1000) * hours * config.electricity_price_eur_kwh


def run_simulation(config: Config):
    environment = Environment(config)
    orchestrator = Orchestrator(config)

    steps_per_hour = int(60 / config.timestep_minutes)
    total_steps = config.hours * steps_per_hour

    co2 = config.initial_co2_ppm
    humidity = config.initial_humidity_pct
    wall_moisture = config.initial_wall_moisture_pct

    cumulative_cost = 0.0
    rows = []

    for step in range(total_steps):
        hour = step / steps_per_hour

        occupants = occupant_profile(hour, config.fixed_occupants)

        state = {
            "hour": hour,
            "co2": co2,
            "humidity": humidity,
            "wall_moisture": wall_moisture,
            "occupants": occupants,
        }

        decision = orchestrator.decide(state)

        vmc_level = decision["vmc"]
        dehumidifier_on = decision["dehum"]
        window_open = decision["window_open"]
        airflow_real_m3h = decision["airflow_real_m3h"]

        step_cost = compute_step_cost(
            vmc_level=vmc_level,
            dehumidifier_on=dehumidifier_on,
            config=config,
        )

        cumulative_cost += step_cost

        co2, humidity, wall_moisture = environment.evolve(
            co2=co2,
            humidity=humidity,
            wall_moisture=wall_moisture,
            occupants=occupants,
            vmc_level=vmc_level,
            dehumidifier_on=dehumidifier_on,
            window_open=window_open,
            airflow_real_m3h=airflow_real_m3h,
        )

        rows.append(
            {
                "ora": hour,
                "occupants": occupants,
                "co2_ppm": co2,
                "humidity_pct": humidity,
                "wall_moisture_pct": wall_moisture,
                "vmc": vmc_level,
                "dehumidifier": dehumidifier_on,
                "window_open": window_open,
                "step_cost_eur": step_cost,
                "cumulative_cost_eur": cumulative_cost,
                "air_quality_status": decision["reports"]["air_quality"]["status"],
                "humidity_status": decision["reports"]["humidity"]["status"],
                "energy_reason": decision["reports"]["energy"]["reason"],
                "window_reason": decision["reports"]["window"]["reason"],
                "airflow_real_m3h": decision["airflow_real_m3h"],
                "duct_pressure_pa": decision["duct_pressure_pa"],
                "air_velocity_ms": decision["air_velocity_ms"],
                "noise_risk": decision["noise_risk"],
                "duct_reason": decision["reports"]["duct"]["reason"],
                "co2_trend_ppm_h": decision["co2_trend_ppm_h"],
                "co2_forecast_15m": decision["co2_forecast_15m"],
                "co2_forecast_30m": decision["co2_forecast_30m"],
                "co2_forecast_45m": decision["co2_forecast_45m"],
                "co2_trend_status": decision["co2_trend_status"],
                "predictive_boost": decision["predictive_boost"],
                "predictive_reason": decision["predictive_reason"],
	
            }
        )

    return pd.DataFrame(rows)