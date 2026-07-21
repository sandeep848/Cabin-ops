# ApexAir In-Flight Service Portal & Cabin Command Center: Project Audit & Roadmap

This document serves as a comprehensive guide to the current implementation state of the **CabinOps AI** system. It details the existing architecture, highlights the core issues preventing it from being fully production-grade, and outlines a clear, step-by-step roadmap for future development.

---

## 🏗️ 1. Project Architecture

The system coordinates simulated passenger requests (text, quick-button, or voice) with crew dispatch zones using a FastAPI backend and two separate Vite/React frontends.

```mermaid
graph TD
    subgraph Frontend Portals
        P_UI["Passenger Seatback Screen (Port 5173)"]
        C_UI["Crew Control Dashboard (Port 5174)"]
    end

    subgraph FastAPI Backend (Port 8000)
        API["FastAPI Controller (main.py)"]
        Parser["Intent Parser (intent_parser.py)"]
        Rules["Flight Rules Engine (flight_rules.py)"]
        Router["Zone Router (router.py)"]
        Inv["Inventory Manager (inventory.py)"]
    end

    subgraph Data & Storage
        DB[("SQLite Database (cabinops.db)")]
        LocalFiles[("Local JSON Configs")]
    end

    %% Ingress and flow
    P_UI -->|POST /request| API
    C_UI -->|GET /crew/tasks| API
    C_UI -->|POST /flight-context| API
    
    API --> Parser
    Parser --> Router
    API --> Rules
    Rules --> Inv
    API --> DB
    API --> LocalFiles
```

### 🧱 Core Modules
1. **API Controller (`backend/main.py`)**: Runs the FastAPI app, manages REST endpoints, handles session tokens for the crew, controls rate limits, and processes ingress tasks.
2. **Intent Parser (`backend/services/intent_parser.py`)**: Classifies text queries into 13 distinct intents, assigns initial urgency (low, medium, high), and extracts entity slots (e.g., `symptom = chest pain`, `item = coffee`).
3. **Flight Rules Engine (`backend/services/flight_rules.py`)**: Restricts standard service dispatches during takeoff, landing, or landing preparation. It overrides requests and marks them as `delayed` with custom alerts.
4. **Zone Router (`backend/services/router.py`)**: Maps passenger seat numbers to cabin segments:
   - Rows 1–10 $\to$ `fore_cabin`
   - Rows 11–20 $\to$ `mid_cabin`
   - Rows 21–30 $\to$ `aft_cabin`
5. **Inventory Manager (`backend/services/inventory.py`)**: Tracks items in real-time. Automatically checks if items are in stock, depletes inventory upon booking, and suggests alternatives when out of stock.

---

## 🔍 2. Issues & Gaps (Why it is not "Foolproof")

While the implementation checklist passes, several operational vulnerabilities exist:

| Issue / Gap | Impact | Description |
|---|---|---|
| **Phase-Specific Dispatch Inconsistencies** | **Low Accuracy (84.90%)** | The evaluation dataset expects service requests (like water) to have `crew_required = true` even during takeoff, landing, or taxi, whereas the rules engine blocks them. Taxi and boarding phases are completely missing from the rules engine checks. |
| **Seat Spoofing Vulnerability** | **Security Risk** | Passenger requests are submitted by seat number without validation. Any passenger can send requests on behalf of other seats by changing the request payload. |
| **Mocked Audio Transcription** | **Feature Stub** | The transcription endpoint `/transcribe` uses a hardcoded stub that always returns `"I feel dizzy. Can someone help?"`. No real speech-to-text is performed. |
| **Polling-Based Sync** | **High Server Load** | Both frontends query the database via HTTP polling every 2–3 seconds. This results in latency and high overhead. |

---

## 🚀 3. Multi-Phase Roadmap

To make the CabinOps AI system robust, secure, and production-ready, we should execute the following plan:

### 📍 Phase 1: Standardizing Flight Rules & Evaluation
- **Task**: Align `flight_rules.py` and the evaluation dataset. Include taxi and boarding phases under restricted flight safety checks.
- **Goal**: Reach **100% Evaluation Accuracy** on the full 510-row dataset while adhering strictly to safety regulations.

### 🔒 Phase 2: Secure Passenger Authentication Ingress
- **Task**: Enforce token verification for passengers.
  - Implement a lightweight authentication handshake using `/auth/passenger`.
  - Require the passenger token for `POST /request` and `GET /passenger/requests` endpoints.
  - Update the passenger screen to lock inputs until authenticated with their seat and booking reference.

### ⚡ Phase 3: Real-Time Communication (SSE / WebSockets)
- **Task**: Implement Server-Sent Events (SSE) or WebSockets at `/events`.
  - Push flight context modifications and new tasks immediately.
  - Remove frontend interval polling. This improves update times from 3 seconds to sub-100ms.

### 🎙️ Phase 4: Lightweight Speech-to-Text Integration
- **Task**: Replace the STT static stub.
  - Integrate a lightweight local python speech-to-text library or dictionary-based simulation that maps audio patterns to common seat requests.

### 🎨 Phase 5: Premium UI/UX Polish
- **Task**: Add micro-animations and a glassmorphic aesthetic to frontends.
  - **Seat Map Hovers**: Hovering over seats displays a beautiful glass card showing occupant details.
  - **Task Queue Animations**: Attendants see smooth slide transitions when accepting or clearing tasks.
  - **Voice Waves**: Replace static audio buttons with a breathing audio gradient wave during voice input recording.
