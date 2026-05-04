class DuctAgent:
    def analyze(self, requested_vmc, config):
        if requested_vmc == "alta":
            target_airflow_m3h = config.vmc_high_m3h
        elif requested_vmc == "media":
            target_airflow_m3h = config.vmc_medium_m3h
        else:
            target_airflow_m3h = config.vmc_low_m3h

        if config.filter_status == "Sporco":
            filter_drop_pa = config.filter_pressure_dirty_pa
        elif config.filter_status == "Medio":
            filter_drop_pa = config.filter_pressure_medium_pa
        else:
            filter_drop_pa = config.filter_pressure_clean_pa

        duct_drop_pa = (
            config.base_pressure_drop_pa
            + config.pressure_loss_coeff * (target_airflow_m3h / 100) ** 2
        )

        total_pressure_pa = duct_drop_pa + filter_drop_pa

        if total_pressure_pa <= config.fan_available_pressure_pa:
            real_airflow_m3h = target_airflow_m3h
        else:
            reduction_factor = (config.fan_available_pressure_pa / total_pressure_pa) ** 0.5
            real_airflow_m3h = target_airflow_m3h * reduction_factor

        air_velocity_ms = (real_airflow_m3h / 3600) / config.duct_area_m2

        if air_velocity_ms > 4.0:
            noise_risk = "high"
        elif air_velocity_ms > 2.5:
            noise_risk = "medium"
        else:
            noise_risk = "low"

        if total_pressure_pa > config.fan_available_pressure_pa:
            pressure_status = "critical"
        elif total_pressure_pa > 0.8 * config.fan_available_pressure_pa:
            pressure_status = "warning"
        else:
            pressure_status = "good"

        return {
            "agent": "duct",
            "requested_vmc": requested_vmc,
            "target_airflow_m3h": target_airflow_m3h,
            "real_airflow_m3h": real_airflow_m3h,
            "duct_pressure_pa": total_pressure_pa,
            "filter_drop_pa": filter_drop_pa,
            "air_velocity_ms": air_velocity_ms,
            "noise_risk": noise_risk,
            "pressure_status": pressure_status,
            "reason": (
                f"Portata reale {real_airflow_m3h:.0f} m³/h, "
                f"pressione {total_pressure_pa:.0f} Pa, "
                f"velocità {air_velocity_ms:.1f} m/s."
            )
        }