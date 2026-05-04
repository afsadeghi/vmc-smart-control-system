from agents.air_quality import AirQualityAgent
from agents.humidity import HumidityAgent
from agents.energy import EnergyAgent
from agents.window import WindowAgent
from agents.duct import DuctAgent
from mpc_controller import MPCController


class Orchestrator:
    def __init__(self, config):
        self.config = config

        self.air_quality_agent = AirQualityAgent()
        self.humidity_agent = HumidityAgent()
        self.energy_agent = EnergyAgent()
        self.window_agent = WindowAgent()
        self.duct_agent = DuctAgent()
        self.mpc_controller = MPCController(config)

        # Memoria del sistema
        self.prev_vmc = "bassa"
        self.prev_dehum = False
        self.prev_window = False

        # Anti-spike VMC alta
        self.min_high_runtime_minutes = 15
        self.min_high_steps = max(
            1,
            int(round(self.min_high_runtime_minutes / config.timestep_minutes))
        )
        self.high_hold_remaining = 0

        # Memoria CO2 per trend / previsione
        self.co2_history = []
        self.co2_trend_window_minutes = 15

    def decide(self, state):
        config = self.config

        # ==========================
        # 1. Gli agenti analizzano
        # ==========================

        air_report = self.air_quality_agent.analyze(state, config)
        humidity_report = self.humidity_agent.analyze(state, config)
        energy_report = self.energy_agent.analyze(state, config)
        window_report = self.window_agent.analyze(state, config)

        co2 = state["co2"]
        humidity = state["humidity"]

        occupants = state.get(
            "occupants",
            getattr(config, "fixed_occupants", getattr(config, "occupants", 3))
        )

        co2_trend_ppm_h, co2_forecast = self._compute_co2_forecast(co2)

        # ==========================
        # 2. Decisione VMC reattiva
        # ==========================

        vmc = air_report["recommended_vmc"]

        # Se fuori è più umido, evito ventilazione forte quando la CO2 non è grave.
        if humidity_report["avoid_extra_ventilation"] and air_report["severity"] <= 1:
            vmc = "bassa"

        elif humidity_report["avoid_extra_ventilation"] and air_report["severity"] == 2:
            # Se la CO2 è appena sopra comfort, evito VMC alta.
            # Ma se supera 1000 ppm, do priorità alla qualità aria.
            if vmc == "alta" and co2 < 1000:
                vmc = "media"

        # Se il comfort è buono, risparmio energia.
        if (
            energy_report["save_energy"]
            and air_report["severity"] == 0
            and humidity_report["severity"] == 0
        ):
            vmc = "bassa"

        # Isteresi base per evitare continui cambi bassa/media/alta.
        vmc = self._smooth_vmc(vmc, co2)

        # ==========================
        # 2A. MPC leggero predittivo
        # ==========================

        predictive_boost = False
        predictive_reason = "Controllo reattivo: MPC predittivo disattivato."
        mpc_dehum_override = None

        reactive_vmc_candidate = vmc
        control_mode = getattr(config, "control_mode", "Predittivo")

        if control_mode == "Predittivo":
            mpc_result = self.mpc_controller.choose_action(
                state={
                    "co2": co2,
                    "humidity": humidity,
                    "occupants": occupants,
                },
                previous_vmc=self.prev_vmc,
            )

            vmc = mpc_result["vmc"]
            mpc_dehum_override = mpc_result["dehum"]

            predictive_boost = vmc != reactive_vmc_candidate

            if predictive_boost:
                predictive_reason = (
                    "MPC attivo: ha modificato la decisione VMC rispetto al controllo reattivo. "
                    + mpc_result["reason"]
                )
            else:
                predictive_reason = (
                    "MPC valutato: la scelta coincide con il controllo reattivo. "
                    + mpc_result["reason"]
                )

        # ==========================
        # 2B. Analisi tecnica condotta
        # ==========================

        duct_report = self.duct_agent.analyze(vmc, config)

        # Se rischio rumore alto e la CO2 non è critica,
        # evito VMC alta e passo a media.
        if duct_report["noise_risk"] == "high" and co2 < config.co2_critical_ppm:
            if vmc == "alta":
                vmc = "media"
                duct_report = self.duct_agent.analyze(vmc, config)

        # ==========================
        # 2C. Anti-spike VMC alta
        # ==========================

        vmc = self._apply_high_minimum_runtime(vmc)

        # Se l'anti-spike ha cambiato il livello, ricalcolo la condotta.
        duct_report = self.duct_agent.analyze(vmc, config)

        # ==========================
        # 3. Decisione deumidificatore
        # ==========================

        if mpc_dehum_override is not None:
            dehum = mpc_dehum_override
        else:
            if self.prev_dehum:
                dehum = humidity > 57
            else:
                dehum = humidity > 61

        # ==========================
        # 4. Decisione finestra
        # ==========================

        window_open = window_report["recommended_window_open"]

        # Protezione: se fuori è più umido, apro solo in emergenza CO2.
        if humidity_report["avoid_extra_ventilation"] and co2 < 1400:
            window_open = False

        # ==========================
        # 5. Aggiorno memoria
        # ==========================

        self.prev_vmc = vmc
        self.prev_dehum = dehum
        self.prev_window = window_open

        return {
            "vmc": vmc,
            "dehum": dehum,
            "window_open": window_open,

            "airflow_real_m3h": duct_report["real_airflow_m3h"],
            "duct_pressure_pa": duct_report["duct_pressure_pa"],
            "air_velocity_ms": duct_report["air_velocity_ms"],
            "noise_risk": duct_report["noise_risk"],

            "co2_trend_ppm_h": co2_trend_ppm_h,
            "co2_forecast_15m": co2_forecast["15m"],
            "co2_forecast_30m": co2_forecast["30m"],
            "co2_forecast_45m": co2_forecast["45m"],
            "co2_trend_status": co2_forecast["status"],

            "predictive_boost": predictive_boost,
            "predictive_reason": predictive_reason,

            "reports": {
                "air_quality": air_report,
                "humidity": humidity_report,
                "energy": energy_report,
                "window": window_report,
                "duct": duct_report,
            }
        }

    def _smooth_vmc(self, requested_vmc, co2):
        config = self.config

        if requested_vmc == "alta":
            if self.prev_vmc == "bassa" and co2 < config.co2_critical_ppm:
                return "media"
            return "alta"

        if requested_vmc == "media":
            if self.prev_vmc == "alta" and co2 > 850:
                return "alta"
            if self.prev_vmc == "bassa" and co2 < 850:
                return "bassa"
            return "media"

        # requested_vmc == "bassa"
        if self.prev_vmc == "alta" and co2 > 850:
            return "media"

        if self.prev_vmc == "media" and co2 > 700:
            return "media"

        return "bassa"

    def _apply_high_minimum_runtime(self, requested_vmc):
        """
        Anti-spike:
        se la VMC entra in alta, resta alta almeno per min_high_steps.
        """

        # Caso 1: entro ora in alta
        if requested_vmc == "alta" and self.prev_vmc != "alta":
            self.high_hold_remaining = self.min_high_steps - 1
            return "alta"

        # Caso 2: ero già in alta
        if self.prev_vmc == "alta":
            if self.high_hold_remaining > 0:
                self.high_hold_remaining -= 1
                return "alta"

            return requested_vmc

        # Caso 3: non sono in alta
        return requested_vmc

    def _compute_co2_forecast(self, co2):
        """
        Calcola trend CO2 usando una finestra breve.
        Più stabile rispetto al confronto con un solo step precedente.
        """

        config = self.config
        dt_hours = config.timestep_minutes / 60

        window_steps = max(
            2,
            int(round(self.co2_trend_window_minutes / config.timestep_minutes))
        )

        self.co2_history.append(co2)

        if len(self.co2_history) > window_steps:
            self.co2_history = self.co2_history[-window_steps:]

        if len(self.co2_history) < 2:
            trend_ppm_h = 0.0
        else:
            delta_co2 = self.co2_history[-1] - self.co2_history[0]
            delta_time_h = (len(self.co2_history) - 1) * dt_hours
            trend_ppm_h = delta_co2 / delta_time_h

        forecast_15m = max(config.outdoor_co2_ppm, co2 + trend_ppm_h * 0.25)
        forecast_30m = max(config.outdoor_co2_ppm, co2 + trend_ppm_h * 0.50)
        forecast_45m = max(config.outdoor_co2_ppm, co2 + trend_ppm_h * 0.75)

        if trend_ppm_h > 80:
            status = "rising_fast"
        elif trend_ppm_h > 20:
            status = "rising"
        elif trend_ppm_h < -80:
            status = "falling_fast"
        elif trend_ppm_h < -20:
            status = "falling"
        else:
            status = "stable"

        return trend_ppm_h, {
            "15m": forecast_15m,
            "30m": forecast_30m,
            "45m": forecast_45m,
            "status": status,
        }