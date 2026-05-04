class AirQualityAgent:
    def analyze(self, state, config):
        co2 = state["co2"]

        if co2 >= config.co2_critical_ppm:
            return {
                "agent": "air_quality",
                "severity": 3,
                "status": "critical",
                "recommended_vmc": "alta",
                "reason": "CO2 critica: serve ventilazione alta."
            }

        if co2 >= config.co2_warning_ppm:
            return {
                "agent": "air_quality",
                "severity": 2,
                "status": "warning",
                "recommended_vmc": "alta",
                "reason": "CO2 sopra soglia attenzione: aumento ventilazione."
            }

        if co2 >= config.co2_comfort_ppm:
            return {
                "agent": "air_quality",
                "severity": 1,
                "status": "moderate",
                "recommended_vmc": "media",
                "reason": "CO2 sopra comfort: ventilazione media."
            }

        return {
            "agent": "air_quality",
            "severity": 0,
            "status": "good",
            "recommended_vmc": "bassa",
            "reason": "CO2 buona: ventilazione bassa sufficiente."
        }