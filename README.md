# AstroGuard AI

### Astronaut Health Monitoring & Decision-Support System

**NASA Space Apps Challenge 2026 | November 14–15, 2026**

*Monitor. Assess. Understand. Act.*

AstroGuard AI is an astronaut-first health monitoring and educational decision-support prototype designed to help astronauts track their health, understand physiological changes, and access relevant guidance during long-duration space missions.

The platform combines **daily health check-ins, simulated automatic sensor telemetry, interactive health visualizations, historical trends, explainable health assessments, and spaceflight hazard awareness** in one application.

> **Project Status:** 🚧 Under Development — NASA Space Apps Challenge 2026

> **Medical Disclaimer:** AstroGuard AI is a hackathon prototype for educational and demonstration purposes. It is not a certified medical device, does not provide clinical diagnoses, and does not replace flight surgeons or approved mission medical procedures. All simulated telemetry is fictional. This project is not endorsed by NASA.

---

##  The Problem

As humanity prepares for longer missions to the Moon, Mars, and beyond, astronaut health monitoring becomes increasingly important.

NASA's Human Research Program identifies five major hazards of human spaceflight:

1. **Space Radiation** — Exposure to high-energy radiation that can increase long-term health risks.
2. **Isolation and Confinement** — Psychological and behavioral challenges from extended periods in confined environments.
3. **Distance from Earth** — Communication delays and limited access to immediate medical support.
4. **Gravity Fields** — Physiological changes caused by microgravity and partial gravity, including muscle and bone loss.
5. **Hostile and Closed Environments** — Risks associated with spacecraft environmental conditions and life-support systems.

These challenges make regular health monitoring, understandable medical information, and greater crew autonomy essential.

## 💡 Our Solution

AstroGuard AI provides a centralized platform where astronauts can:

- Record daily health measurements and symptoms.
- Monitor fictional real-time sensor telemetry during demonstrations.
- Visualize health trends across days and weeks.
- Review explainable alerts about potentially concerning patterns.
- Access sourced educational health guidance.
- Understand how the five hazards of spaceflight may affect their bodies.
- Track daily wellness routines and exercise activities.
- Review historical health records and prepare summaries for medical support.

The system is designed with offline-capable operation as an architectural goal, recognizing that deep-space missions may experience communication delays.

## ✨ Core Features

### 1. Daily Health Check-In

Astronauts can manually enter:

- Heart rate (bpm)
- Blood pressure (mmHg)
- Blood glucose (mg/dL)
- Body temperature (°C)
- Blood oxygen saturation (%)
- Sleep duration (hours)
- Mood and stress indicators
- Symptoms and additional notes

### 2. Simulated Automatic Sensor Monitoring

A built-in telemetry simulator generates fictional readings for:

- Heart rate
- Blood oxygen saturation
- Body temperature
- Cabin CO₂ concentration
- Radiation exposure scenarios

Simulation modes include routine monitoring, exercise, unusual health trends, and environmental changes.

All generated data is explicitly identified as simulated.

### 3. Interactive Health Dashboard

A responsive dashboard displays the latest measurements, health trends, mission context, check-in status, and recent notifications.

### 4. Health History & Visualization

Interactive charts help astronauts review changes in health indicators over time and compare current measurements with previous records.

### 5. Explainable Health Assessments

A transparent, configurable rules engine evaluates available measurements and trends to generate demonstration assessment results.

Assessment explanations describe which data contributed to an alert and identify when crew medical review may be appropriate.

The system does not claim to diagnose medical conditions.

### 6. Educational Health Guidance

Astronauts can access understandable explanations of health indicators, measurement instructions, relevant spaceflight risks, and general preventive information.

Medical escalation guidance must be distinguished from approved mission-specific procedures.

### 7. Spaceflight Hazard Explorer

An educational interface explains NASA's five hazards of human spaceflight and connects them to relevant health indicators.

### 8. Interactive Body-System Explorer

A planned visualization allows astronauts to explore the cardiovascular, musculoskeletal, respiratory, and behavioral health systems.

### 9. Offline-Capable Design

Local data storage and bundled educational resources are intended to reduce dependence on continuous internet connectivity.

Full offline functionality will be validated as development progresses.

---

## 🏗️ System Architecture

AstroGuard AI uses a modular three-layer architecture.

```text
              ASTRONAUT
                  |
                  v
         FRONTEND (React)
      Dashboard | Check-In
      Charts | Guidance | Alerts
                  |
             REST API
                  |
                  v
         BACKEND (FastAPI)
      Validation | Assessment
      Simulator | Guidance
                  |
             SQLAlchemy
                  |
                  v
          DATABASE (SQLite)
      Astronauts | Missions
      Readings | Check-Ins
      Assessments | Alerts
```

The frontend communicates with the backend through REST APIs. The backend manages application logic and accesses the SQLite database through a dedicated persistence package.

## 🛠️ Technology Stack

| Layer | Technologies |
|---|---|
| Frontend | React, Vite, Tailwind CSS |
| Visualizations | Recharts |
| Backend | Python, FastAPI, Pydantic |
| Database | SQLite, SQLAlchemy |
| Migrations | Alembic |
| API Communication | REST, JSON |
| Testing | Pytest and frontend build checks |
| Development | VS Code, Codex, GitHub |

## 📁 Project Structure

```text
astroguard-ai/
├── frontend/
│   └── src/
│       ├── components/
│       ├── pages/
│       ├── services/
│       ├── hooks/
│       └── App.jsx
│
├── backend/
│   ├── app/
│   │   ├── api/
│   │   ├── schemas/
│   │   ├── services/
│   │   ├── repositories/
│   │   └── main.py
│   └── tests/
│
├── database/
│   ├── astroguard_db/
│   │   ├── models.py
│   │   ├── session.py
│   │   └── repositories/
│   ├── migrations/
│   └── tests/
│
├── shared/
│   ├── api-contract.md
│   └── data-dictionary.md
│
├── docs/
├── .gitignore
└── README.md
```

*This is the planned repository structure. Directories and modules will be added as implementation progresses.*

## 🚀 Getting Started

### Prerequisites

Install:

- Node.js LTS and npm
- Python 3.11+
- Git
- Visual Studio Code

### 1. Clone the repository

```bash
git clone https://github.com/YOUR-USERNAME/astroguard-ai.git
cd astroguard-ai
```

Replace `YOUR-USERNAME` with the repository owner's GitHub username.

### 2. Set up the backend

Once the backend and database packages are implemented:

```bash
python -m venv .venv
```

Activate the virtual environment.

On Windows:

```bash
.venv\Scripts\activate
```

On macOS or Linux:

```bash
source .venv/bin/activate
```

Install dependencies from the repository root:

```bash
pip install -e ./database
pip install -r backend/requirements.txt
```

Start the API:

```bash
cd backend
uvicorn app.main:app --reload
```

Backend URL: http://localhost:8000

API documentation: http://localhost:8000/docs

### 3. Set up the frontend

Open a second terminal:

```bash
cd frontend
npm install
npm run dev
```

Frontend URL: http://localhost:5173

**Note:** These are the intended development commands. Database migrations, environment configuration, and final startup instructions will be documented as the corresponding modules are completed.

## 🔗 Planned API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/health` | API health check |
| GET | `/api/astronauts` | List astronauts |
| POST | `/api/astronauts` | Create astronaut profile |
| GET | `/api/astronauts/{id}/readings` | Retrieve health history |
| POST | `/api/astronauts/{id}/readings` | Submit health reading |
| GET | `/api/astronauts/{id}/checkins` | Retrieve check-ins |
| POST | `/api/astronauts/{id}/checkins` | Submit daily check-in |
| POST | `/api/astronauts/{id}/assessments` | Generate assessment |
| GET | `/api/astronauts/{id}/alerts` | Retrieve alerts |
| GET | `/api/guidance` | Educational guidance |
| GET | `/api/hazards` | Spaceflight hazards |
| POST | `/api/simulation/generate` | Generate simulated telemetry |

The shared API contract will define final request and response schemas.

## 👨‍💻 Team Development

The project is being developed collaboratively by three team members.

| Role | Responsibilities | Git Branch |
|---|---|---|
| Frontend Developer | UI, dashboards, charts, forms | `feature/frontend` |
| Backend Developer | APIs, simulator, assessments, guidance | `feature/backend` |
| Database Developer | Schema, models, migrations, persistence | `feature/database` |

Each team member works in their assigned module and integrates changes through GitHub.

### Contribution Workflow

1. Clone the repository.
2. Create or switch to your assigned feature branch.
3. Implement and test your module.
4. Commit your changes with meaningful messages.
5. Push your branch.
6. Open a pull request to merge into `main`.
7. Review and test integration before merging.

All team members must follow the shared API contracts and data definitions.

## 🧪 Demonstration Scenarios

The planned demonstration includes:

**Scenario 1 — Routine Health Monitoring**

An astronaut completes a daily check-in while the simulator generates fictional vital-sign readings.

**Scenario 2 — Health Trend Review**

The application displays a change in historical measurements and generates an explainable demonstration alert.

**Scenario 3 — Sleep and Stress Monitoring**

Several days of reduced sleep and reported stress are visualized to support behavioral health awareness.

**Scenario 4 — Environmental Monitoring**

Simulated cabin conditions or radiation exposure illustrate the importance of monitoring spaceflight hazards.

## 📚 Scientific Resources

The project draws educational context from publicly available space-agency resources:

- [NASA — 5 Hazards of Human Spaceflight](https://www.nasa.gov/hrp/hazards/)
- [NASA — Risks of Human Spaceflight](https://www.nasa.gov/hrp/risks/)
- [NASA — Ongoing Human Research](https://www.nasa.gov/hrp/ongoing-hrp-research/)
- [Canadian Space Agency — Monitoring Radiation for Astronaut Health](https://www.asc-csa.gc.ca/eng/news/articles/2026/2026-02-26-monitoring-radiation-astronaut-health.asp)

References are used for research and educational purposes. They do not imply agency endorsement or clinical validation of this software.

## 🔮 Future Improvements

- Integration with supported wearable sensors
- More advanced, validated health assessment methods
- Expanded offline-first capabilities
- Communication-delay-aware medical reporting
- Mission-specific measurement schedules
- Interactive 3D body-system visualization
- More comprehensive environmental telemetry

## 🏆 NASA Space Apps Challenge 2026

**Challenge:** Create Health Monitoring Software for Astronauts on Space Missions

**Event:** November 14–15, 2026

**Project:** AstroGuard AI

**Mission:** Help astronauts better understand their health, recognize important changes, and access useful guidance during long-duration space exploration.

---

**AstroGuard AI — Monitor. Assess. Understand. Act.**
