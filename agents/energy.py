class EnergyAgent:
    def analyze(self, state, config):
        co2 = state["co2"]
        humidity = state["humidity"]

        comfort_ok = (
            co2 < config.co2_comfort_ppm
            and humidity < config.humidity_warning_pct
        )

        if comfort_ok:
            return {
                "agent": "energy",
                "save_energy": True,
                "reason": "Comfort buono: possibile risparmio energetico."
            }

        return {
            "agent": "energy",
            "save_energy": False,
            "reason": "Comfort non ideale: priorità a qualità aria/umidità."
        }