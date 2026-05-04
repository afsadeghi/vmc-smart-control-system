class WindowAgent:
    def analyze(self, state, config):
        co2 = state["co2"]
        humidity = state["humidity"]
        outdoor_humidity = config.outdoor_humidity_pct

        outside_more_humid = outdoor_humidity > humidity

        if co2 > 1400:
            return {
                "agent": "window",
                "recommended_window_open": True,
                "reason": "Emergenza CO2: apro finestra anche se non ideale."
            }

        if co2 > 1250 and not outside_more_humid:
            return {
                "agent": "window",
                "recommended_window_open": True,
                "reason": "CO2 alta e aria esterna accettabile: apro finestra."
            }

        return {
            "agent": "window",
            "recommended_window_open": False,
            "reason": "Finestra chiusa: non necessaria o esterno sfavorevole."
        }