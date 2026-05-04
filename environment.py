class Environment:
    def __init__(self, config):
        self.config = config

    def evolve(
        self,
        co2,
        humidity,
        wall_moisture,
        occupants,
        vmc_level,
        dehumidifier_on,
        window_open,
        airflow_real_m3h=None,
    ):
        config = self.config

        # 1. Produzione interna
        co2 += occupants * config.co2_generation_per_person_ppm_step
        humidity += occupants * config.humidity_generation_per_person_pct_step

        # 2. Portata VMC reale o teorica
        if airflow_real_m3h is not None:
            airflow = airflow_real_m3h
        else:
            if vmc_level == "alta":
                airflow = config.vmc_high_m3h
            elif vmc_level == "media":
                airflow = config.vmc_medium_m3h
            else:
                airflow = config.vmc_low_m3h

        # 3. Effetto finestra
        if window_open:
            airflow += config.window_extra_airflow_m3h

        # 4. Frazione di ricambio aria nello step
        air_change_fraction = min(
            (airflow * (config.timestep_minutes / 60)) / config.room_volume_m3,
            1.0,
        )

        # 5. CO2 tende verso valore esterno
        co2 = co2 * (1 - air_change_fraction) + config.outdoor_co2_ppm * air_change_fraction

        # 6. Umidità tende verso valore esterno
        humidity = humidity * (1 - air_change_fraction) + config.outdoor_humidity_pct * air_change_fraction

        # 7. Deumidificatore
        if dehumidifier_on:
            humidity -= config.dehumidifier_removal_pct_step

        # 8. Massa igroscopica edificio
        moisture_exchange = (humidity - wall_moisture) * config.moisture_mass_strength
        humidity -= moisture_exchange
        wall_moisture += moisture_exchange * 0.25

        # 9. Limiti fisici
        co2 = max(config.outdoor_co2_ppm, co2)
        humidity = min(max(humidity, 20), 95)
        wall_moisture = min(max(wall_moisture, 20), 95)

        return co2, humidity, wall_moisture