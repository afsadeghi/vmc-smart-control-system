# VMC Smart Control System

A multi-agent simulation dashboard for indoor air quality control using a lightweight Model Predictive Control (MPC) strategy.

The project simulates a smart VMC system that monitors CO₂, humidity, airflow, duct pressure, air velocity, energy cost and noise risk.  
It compares a traditional reactive control strategy with a predictive MPC-based strategy.

---

## Project Goal

The goal of this project is to demonstrate how an AI-driven multi-agent architecture can support decision-making in ventilation systems.

The system evaluates:

- indoor CO₂ concentration
- indoor humidity
- outdoor humidity and temperature
- number of occupants
- room volume
- VMC airflow level
- duct pressure
- air velocity
- noise risk
- energy cost

The dashboard shows how a predictive MPC controller can reduce CO₂ peaks while keeping energy cost under control.

---

## Main Result

In the current demo scenario, the MPC-based predictive control reduces the CO₂ peak compared to the reactive control:

| Metric | Reactive | Predictive / MPC |
|---|---:|---:|
| Average CO₂ | 729 ppm | 711 ppm |
| CO₂ peak | 1002 ppm | 899 ppm |
| Average humidity | 53.2% | 52.9% |
| Total cost | € 0.33 | € 0.41 |
| VMC high level | 5.8 h | 6.2 h |
| Dehumidifier ON | 0.0 h | 0.0 h |
| MPC intervention | 0.0 h | 9.2 h |

The MPC controller reduces the CO₂ peak by about 103 ppm with an additional energy cost of about € 0.08.

---

## System Architecture

The project is organized around a multi-agent control logic.

```text
Sensors / simulated environment
        ↓
Specialized agents
        ↓
Orchestrator
        ↓
Lightweight MPC controller
        ↓
Actuator decisions
        ↓
VMC level / dehumidifier / window logic