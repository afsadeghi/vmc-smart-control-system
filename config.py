from dataclasses import dataclass


@dataclass
class Config:
    # tempo simulazione
    hours: int = 24
    timestep_minutes: int = 5

    # ambiente
    room_volume_m3: float = 120.0

    # condizioni esterne
    outdoor_co2_ppm: float = 420.0
    outdoor_humidity_pct: float = 65.0
    outdoor_temp_c: float = 10.0
    indoor_temp_c: float = 22.0

    # condizioni iniziali interne
    initial_co2_ppm: float = 600.0
    initial_humidity_pct: float = 55.0
    initial_wall_moisture_pct: float = 55.0

    # occupanti
    fixed_occupants: int = 3

    # produzione interna
    co2_generation_per_person_ppm_step: float = 18.0
    humidity_generation_per_person_pct_step: float = 0.08

    # VMC portate
    vmc_low_m3h: float = 60.0
    vmc_medium_m3h: float = 120.0
    vmc_high_m3h: float = 220.0

    # potenze elettriche
    vmc_low_power_w: float = 18.0
    vmc_medium_power_w: float = 45.0
    vmc_high_power_w: float = 95.0
    dehumidifier_power_w: float = 350.0

    # deumidificazione
    dehumidifier_removal_pct_step: float = 0.75

    # finestra
    window_extra_airflow_m3h: float = 450.0

    # energia
    electricity_price_eur_kwh: float = 0.30

    # soglie comfort
    co2_comfort_ppm: float = 800.0
    co2_warning_ppm: float = 1000.0
    co2_critical_ppm: float = 1200.0

    humidity_comfort_pct: float = 55.0
    humidity_warning_pct: float = 60.0
    humidity_critical_pct: float = 68.0

    # massa igroscopica edificio
    moisture_mass_strength: float = 0.08

    # filtro VMC
    filter_status: str = "Pulito"  # Pulito, Medio, Sporco

    # condotta
    duct_area_m2: float = 0.0314  # circa condotta diametro 200 mm
    fan_available_pressure_pa: float = 120.0

    # perdite di carico
    base_pressure_drop_pa: float = 20.0
    pressure_loss_coeff: float = 18.0

    filter_pressure_clean_pa: float = 20.0
    filter_pressure_medium_pa: float = 45.0
    filter_pressure_dirty_pa: float = 80.0

    control_mode: str = "Predittivo"  # Reattivo oppure Predittivo