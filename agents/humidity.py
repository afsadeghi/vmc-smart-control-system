class HumidityAgent:
    def analyze(self, state, config):
        humidity = state["humidity"]
        outdoor_humidity = config.outdoor_humidity_pct

        outside_more_humid = outdoor_humidity > humidity

        if humidity >= config.humidity_critical_pct:
            return {
                "agent": "humidity",
                "severity": 3,
                "status": "critical",
                "recommended_dehum": True,
                "avoid_extra_ventilation": outside_more_humid,
                "reason": "Umidità critica: deumidificatore necessario."
            }

        if humidity >= config.humidity_warning_pct:
            return {
                "agent": "humidity",
                "severity": 2,
                "status": "warning",
                "recommended_dehum": True,
                "avoid_extra_ventilation": outside_more_humid,
                "reason": "Umidità sopra soglia: attivo deumidificazione."
            }

        return {
            "agent": "humidity",
            "severity": 0,
            "status": "good",
            "recommended_dehum": False,
            "avoid_extra_ventilation": outside_more_humid,
            "reason": "Umidità sotto controllo."
        }