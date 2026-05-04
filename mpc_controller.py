# =========================================================
# MPC CONTROLLER LEGGERO PER SISTEMA VMC
# =========================================================
# Questo modulo prova diverse azioni future e sceglie quella
# con il miglior compromesso tra:
# - qualità aria CO2
# - umidità
# - costo energetico
# - rischio rumore
# - stabilità del sistema
# =========================================================


try:
    from agents.duct import DuctAgent
except Exception:
    DuctAgent = None


class MPCController:
    def __init__(self, config):
        self.config = config

        if DuctAgent is not None:
            self.duct_agent = DuctAgent()
        else:
            self.duct_agent = None

        self.horizon_minutes = 30

        self.candidate_actions = [
            {"vmc": "bassa", "dehum": False},
            {"vmc": "media", "dehum": False},
            {"vmc": "alta", "dehum": False},
            {"vmc": "bassa", "dehum": True},
            {"vmc": "media", "dehum": True},
            {"vmc": "alta", "dehum": True},
        ]

    def choose_action(self, state, previous_vmc="bassa"):
        """
        Sceglie la migliore azione simulando il futuro breve.
        """

        best_action = None
        best_score = float("inf")
        best_report = None

        for action in self.candidate_actions:
            report = self._simulate_action(
                state=state,
                action=action,
                previous_vmc=previous_vmc,
            )

            if report["score"] < best_score:
                best_score = report["score"]
                best_action = action
                best_report = report

        reason = (
            f"MPC ha scelto VMC={best_action['vmc']} "
            f"e deumidificatore={'ON' if best_action['dehum'] else 'OFF'} "
            f"perché produce il punteggio migliore nei prossimi "
            f"{self.horizon_minutes} minuti. "
            f"CO2 prevista finale={best_report['final_co2']:.0f} ppm, "
            f"umidità prevista finale={best_report['final_humidity']:.1f}%, "
            f"costo previsto={best_report['energy_cost']:.3f} €."
        )

        return {
            "vmc": best_action["vmc"],
            "dehum": best_action["dehum"],
            "score": best_score,
            "reason": reason,
            "forecast": best_report,
        }

    def _simulate_action(self, state, action, previous_vmc):
        """
        Simula una singola azione mantenuta per l'orizzonte MPC.
        """

        config = self.config

        timestep_minutes = getattr(config, "timestep_minutes", 5)
        dt_h = timestep_minutes / 60
        steps = int(self.horizon_minutes / timestep_minutes)

        co2 = float(state.get("co2", 800))
        humidity = float(state.get("humidity", 58))
        occupants = int(state.get("occupants", getattr(config, "fixed_occupants", 3)))

        vmc = action["vmc"]
        dehum = action["dehum"]

        total_energy_cost = 0.0
        total_penalty = 0.0

        for _ in range(steps):
            duct = self._duct_analysis(vmc)

            airflow = duct["real_airflow_m3h"]
            noise_risk = duct["noise_risk"]

            co2 = self._next_co2(
                co2=co2,
                occupants=occupants,
                airflow_m3h=airflow,
                dt_h=dt_h,
            )

            humidity = self._next_humidity(
                humidity=humidity,
                airflow_m3h=airflow,
                dehum=dehum,
                occupants=occupants,
                dt_h=dt_h,
            )

            step_cost = self._energy_cost(vmc, dehum, dt_h)
            total_energy_cost += step_cost

            total_penalty += self._score_step(
                co2=co2,
                humidity=humidity,
                step_cost=step_cost,
                noise_risk=noise_risk,
                vmc=vmc,
                previous_vmc=previous_vmc,
            )

        return {
            "score": total_penalty,
            "final_co2": co2,
            "final_humidity": humidity,
            "energy_cost": total_energy_cost,
            "vmc": vmc,
            "dehum": dehum,
        }

    def _duct_analysis(self, vmc):
        """
        Usa DuctAgent se esiste.
        Altrimenti usa valori standard.
        """

        if self.duct_agent is not None:
            return self.duct_agent.analyze(vmc, self.config)

        fallback_airflow = {
            "bassa": 60,
            "media": 120,
            "alta": 220,
        }

        return {
            "real_airflow_m3h": fallback_airflow.get(vmc, 120),
            "duct_pressure_pa": 60,
            "air_velocity_ms": 1.0,
            "noise_risk": "low",
        }

    def _next_co2(self, co2, occupants, airflow_m3h, dt_h):
        """
        Modello semplificato CO2:
        CO2 cresce per presenza persone e diminuisce per ventilazione.
        """

        config = self.config

        room_volume = getattr(config, "room_volume_m3", 120)
        outdoor_co2 = getattr(config, "outdoor_co2_ppm", 420)

        co2_generation_ppm_h_per_person = 130

        generation = occupants * co2_generation_ppm_h_per_person
        ach = airflow_m3h / room_volume

        dco2 = generation + ach * (outdoor_co2 - co2)

        return max(outdoor_co2, co2 + dco2 * dt_h)

    def _next_humidity(self, humidity, airflow_m3h, dehum, occupants, dt_h):
        """
        Modello semplificato umidità.
        """

        config = self.config

        room_volume = getattr(config, "room_volume_m3", 120)
        outdoor_humidity = getattr(config, "outdoor_humidity_pct", 65)

        humidity_generation_pct_h_per_person = 0.20
        dehum_removal_pct_h = 4.0 if dehum else 0.0

        ach = airflow_m3h / room_volume

        dh = (
            occupants * humidity_generation_pct_h_per_person
            + 0.15 * ach * (outdoor_humidity - humidity)
            - dehum_removal_pct_h
        )

        return max(35, min(85, humidity + dh * dt_h))

    def _energy_cost(self, vmc, dehum, dt_h):
        """
        Costo energetico stimato.
        """

        config = self.config
        price = getattr(config, "electricity_price_eur_kwh", 0.30)

        vmc_power_kw = {
            "bassa": 0.04,
            "media": 0.08,
            "alta": 0.16,
        }.get(vmc, 0.08)

        dehum_power_kw = 0.30 if dehum else 0.0

        return (vmc_power_kw + dehum_power_kw) * dt_h * price

    def _score_step(self, co2, humidity, step_cost, noise_risk, vmc, previous_vmc):
        """
        Funzione obiettivo MPC.
        Più il punteggio è basso, migliore è la scelta.
        """

        config = self.config

        co2_comfort = getattr(config, "co2_comfort_ppm", 800)
        co2_warning = getattr(config, "co2_warning_ppm", 1000)

        humidity_warning = getattr(config, "humidity_warning_pct", 60)

        score = 0.0

        # Penalità CO2
        if co2 > co2_comfort:
            score += ((co2 - co2_comfort) / 50) ** 2

        if co2 > co2_warning:
            score += 20 + ((co2 - co2_warning) / 30) ** 2 * 5

        # Penalità umidità più severa
        if humidity > 58:
            score += ((humidity - 58) / 2) ** 2 * 4

        if humidity > humidity_warning:
            score += 10 + ((humidity - humidity_warning) / 1.5) ** 2 * 8

        # Costo energia
        score += step_cost * 80

        # Penalità rumore
        if noise_risk == "medium":
            score += 3
        elif noise_risk == "high":
            score += 15

        # Penalità cambio livello VMC
        if vmc != previous_vmc:
            score += 1.5

        # Piccola penalità per VMC alta continua
        if vmc == "alta":
            score += 2

        return score