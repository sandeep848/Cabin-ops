# ApexAir In-Flight Service Portal & Cabin Command Center

ApexAir is an enterprise-grade, in-flight passenger service request dispatching and flight operations system. It routes passenger requests (text, voice, or quick selections) directly to cabin crew teams based on seat layout sectors, and dynamically enforces airline safety rules during critical flight phases (takeoff, cruising, landing preparation).

---

## 📁 Project Structure & Key Files

- **`backend/`**: Core FastAPI backend application.
  - [main.py](file:///C:/Users/Sandip/OneDrive/Desktop/CV/cabinops-ai/backend/main.py): REST API endpoints and application lifecycle events.
  - [models.py](file:///C:/Users/Sandip/OneDrive/Desktop/CV/cabinops-ai/backend/models.py): Pydantic data validation schemas.
  - [database.py](file:///C:/Users/Sandip/OneDrive/Desktop/CV/cabinops-ai/backend/database.py): SQLite helper functions for CRUD operations.
  - [config.py](file:///C:/Users/Sandip/OneDrive/Desktop/CV/cabinops-ai/backend/config.py): Project paths, ports, and high-urgency intent lists.
  - **`cabinops.db`**: SQLite database storing the task records.
  - **`services/`**: Core business logic modules.
    - [intent_parser.py](file:///C:/Users/Sandip/OneDrive/Desktop/CV/cabinops-ai/backend/services/intent_parser.py): Parses text requests into intents, urgency, and slots.
    - [flight_rules.py](file:///C:/Users/Sandip/OneDrive/Desktop/CV/cabinops-ai/backend/services/flight_rules.py): Applies phase-specific behavior (e.g., landing rules).
    - [router.py](file:///C:/Users/Sandip/OneDrive/Desktop/CV/cabinops-ai/backend/services/router.py): Assigns passenger seats to specific cabin zones.
    - [inventory.py](file:///C:/Users/Sandip/OneDrive/Desktop/CV/cabinops-ai/backend/services/inventory.py): Deducts and checks item availability in real time.
  - **`data/`**: Configuration metadata (seat map, inventory, flight context, announcements).
- **`frontend/`**:
  - **`passenger_screen/`**: React application for submitting requests.
  - **`crew_dashboard/`**: React console for crew showing queue, seat map, and phase controls.
- **`start_all.py`**: Auto-launcher that starts the backend & both frontends concurrently with dev proxy port alignment.
- **`check.py`**: Full local system integration check suite.
- **`checklist.py`**: Codebase implementation compliance checker.
- **`scripts/evaluate_parser.py`**: Evaluation script for measuring parser accuracy.

---

## 🛠️ Prerequisites & Environment Setup

This project runs best using the existing Conda environment `CV`.

1. Open your terminal (PowerShell or Command Prompt).
2. Activate the Conda environment:
   ```bash
   conda activate CV
   ```
3. Navigate to the project folder:
   ```bash
   cd C:\Users\Sandip\OneDrive\Desktop\CV\cabinops-ai
   ```

---

## 🩺 How to Check Everything

You can run automated checkers and test suites to verify that the project is set up correctly and all features are functioning:

### 1. Run the Implementation Checklist
Audits the codebase to show what parts are fully implemented, partial, or missing:
```bash
python checklist.py
```

### 2. Run the Full Health Checker
Starts a temporary server, performs active write/read requests to verify database integrations, routes, and flight rule enforcement, and automatically cleans up:
```bash
python check.py
```

### 3. Run the Unit Test Suite
Runs the pytest suite to verify intent parsing, flight phase rules, API endpoints, and zone routing:
```bash
C:\Users\Sandip\.vscode\anaconda\envs\CV\python.exe -m pytest
```

### 4. Run the Model Parser Evaluation
Evaluates parsing accuracy (intents, urgency, crew routing) against the 35 ground-truth requests:
```bash
C:\Users\Sandip\.vscode\anaconda\envs\CV\python.exe scripts/evaluate_parser.py
```

---

## 🚀 How to Startup Everything

### Option A: One-Command Startup (Recommended)
This script runs the FastAPI backend, passenger React frontend, and crew dashboard React frontend together, performs a quick health check, and opens the URLs in your default browser:
```bash
python start_all.py
```

### Option B: Manual Startup

If you prefer to run the servers separately in different terminal windows:

#### 1. Start the FastAPI Backend Server:
```bash
python -m uvicorn backend.main:app --reload --port 8000
```
*   **API Documentation**: http://127.0.0.1:8000/docs
*   **Health Status**: http://127.0.0.1:8000/health

#### 2. Start the Passenger Screen Frontend:
```bash
cd frontend/passenger_screen
npm install
npm run dev
```
*   **Passenger Screen URL**: http://127.0.0.1:5173

#### 3. Start the Crew Dashboard Frontend:
```bash
cd frontend/crew_dashboard
npm install
npm run dev
```
*   **Crew Dashboard URL**: http://127.0.0.1:5174

---

## 💾 How to Check the Database

The database is a single-table SQLite database file located at `backend/cabinops.db`.

### 1. Check via Web API (No SQL tools needed)
Query stored tasks directly from your browser or terminal using the API:
- **Task List Endpoint:** http://127.0.0.1:8000/crew/tasks
- **Analytics Endpoint:** http://127.0.0.1:8000/analytics/summary

### 2. Check via SQLite Command Line Interface
If you have SQLite installed, query the database directly:
```bash
sqlite3 backend/cabinops.db
```
Inside the sqlite3 terminal shell:
```sql
.headers on
.mode column
SELECT id, seat, zone, intent, urgency, status, action FROM tasks;
.exit
```

---

## 🧪 Example API Request

To manually submit a request using curl:
```bash
curl -X POST http://127.0.0.1:8000/request \
     -H "Content-Type: application/json" \
     -d '{"seat":"22A","text":"I feel dizzy. Can someone help?","input_modality":"text"}'
```
