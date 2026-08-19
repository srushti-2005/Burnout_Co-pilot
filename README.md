# 🛡️ Prediction of Fall Detector System using ML

**Phase I: Prototype Dashboard & Forecasting Engine** **Team Role:** Person 3 - Integrator (Kshitija Chipkar)

## 📋 Project Overview
This system utilizes Machine Learning to predict fall risks and monitor burnout via a Cognitive Load Index (CLI). This dashboard integrates real-time data simulation, 7-day forecasting, and model explainability.

## 📂 Project Structure
- `app.py`: Main entry point for the Streamlit dashboard.
- `src/forecaster.py`: Time-series logic for 7-day trend prediction.
- `src/ui/components.py`: Reusable UI elements and Gauge charts.
- `requirements.txt`: Python dependencies for the 3.11 environment.

## ⚙️ Setup Instructions
1. **Environment:** Ensure you are using **Python 3.11**.
2. **Install Dependencies:**
   ```bash
   pip install -r requirements.txt