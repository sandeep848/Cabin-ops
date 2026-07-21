# CabinOps AI - Codebase Audit & Improvement Plan

This document outlines the findings of a comprehensive code audit of the CabinOps AI codebase. It identifies errors, missing components, architectural bottlenecks, and provides a clear roadmap for advancements and UI/UX fixtures.

---

## 🔍 1. Current Issues & Discrepancies

### A. Phase-Specific Crew Dispatch Inconsistencies (84.90% Accuracy)
* **The Problem**: Running the evaluation suite (`scripts/evaluate_parser.py`) yields **84.90% Crew Dispatch Accuracy** (433/510 correct), despite having 100% Intent and Urgency accuracy.
* **The Cause**: Mismatches between the ground-truth expectation in `cabinops_requests.csv` and `backend/services/flight_rules.py`:
  1. During the **takeoff** phase, the dataset expects certain standard service requests (e.g., `water_request` at row 38) to have `crew_required = true`. However, the flight rules engine in `flight_rules.py` delays all standard comfort services during takeoff/landing prep, marking them as `crew_required = false` (delayed status).
  2. The **taxi** and **boarding** phases are in the dataset but completely omitted from the restricted-phase check in `flight_rules.py`, even though cabin crew are restricted from service during taxiing and boarding processes.
* **Impact**: Under realistic operations, the crew dispatch status must align perfectly with FAA safety guidelines and the evaluation dataset.

### B. Seat Spoofing & Missing Passenger Authentication
* **The Problem**: The database defines a `bookings` table containing seat numbers and booking references, and `database.py` contains `verify_booking(seat, booking_reference)`. However:
  1. The API route `POST /request` takes a seat number but does not validate if the passenger has authenticated.
  2. The passenger frontend allows users to edit their seat (e.g., changing from `12D` to `3A`) with zero verification or auth headers.
* **Impact**: Security vulnerability where any passenger (or external script) can spoof requests on behalf of other seats.

---

## 🛠️ 2. Missing Components & Stubs

### A. Mocked Speech-to-Text (STT) Service
* **The Problem**: The backend speech transcription (`backend/services/speech_to_text.py`) contains a static stub:
  ```python
  def transcribe_audio_stub(audio_bytes: bytes) -> str:
      return "I feel dizzy. Can someone help?"
  ```
  Every voice upload returns this identical text, while the frontend passenger screen simulates transcription by typing out pre-selected strings letter-by-letter.
* **Impact**: No real voice recognition is occurring. 

### B. Real-Time Status Push (WebSockets or Server-Sent Events)
* **The Problem**: Frontends sync state using HTTP interval polling (`setInterval` every 2s for crew dashboard, 3s for passenger screen).
* **Impact**: Suboptimal performance, high server load (dozens of database requests per minute per open tab), and a latency delay in dispatch updates (up to 3 seconds before a passenger sees that a crew member accepted their call).

---

## 🚀 3. Proposed Advancements & Enhancements

### A. Robust Flight Rules & Corrected Ground-Truth Evaluator
* Fix the restricted-phase logic so that restricted phases (`taxi`, `takeoff`, `landing_preparation`, `landing`) consistently delay comfort/service tasks, and update the dataset evaluation parameters or code logic to achieve a true **100% compliance score**.

### B. Secure Token-Based Passenger Authentication Ingress
* Add a lightweight `/auth/passenger` endpoint that takes a seat number and booking reference and returns a secure HMAC passenger token.
* Require passenger tokens for `POST /request` and `GET /passenger/requests`, preventing unauthorized cross-seat requests.

### C. Live Communication via WebSockets or Server-Sent Events (SSE)
* Replace frontend intervals with a WebSocket connection or SSE stream at `/events` to push instant state transitions (e.g., `Claimed`, `Delivered`, `Restricted Phase Active`) to the screens.

### D. Enhanced Speech-to-Text Pipeline
* Replace the hardcoded STT stub with a lightweight open-source NLP dictionary search, or install `openai-whisper` dynamically if the GPU/CPU permits, allowing local speech-to-text validation during demonstration.

---

## 🎨 4. Premium UI/UX & Aesthetic Fixtures

### A. Advanced Cabin Map Hovers & Interactive Tooltips
* **Currently**: Clicking a seat displays passenger information in a box at the bottom right.
* **UX Fixture**: Hovering over a seat should instantly display a beautiful glassmorphic popover showing the passenger's name, booking reference, and active requests. Clicking the seat locks the popover and opens detailed action controls.

### B. Refined Glassmorphism & Micro-Animations
* Add deep HSL-tailored dark modes and glass overlays using CSS variable bindings:
  ```css
  background: rgba(15, 23, 42, 0.45);
  backdrop-filter: blur(16px);
  border: 1px solid rgba(255, 255, 255, 0.08);
  ```
* Introduce CSS keyframe animations for the voice recording visualizer (a breathing gradient wave instead of static bars) and flashing urgency indicators on the seat map.
* Implement smooth transitions when cards enter or leave the passenger duty queue.

---

## 🔮 5. Additional Recommendations & Feature Advancements

### A. Dynamic Announcements & Flight Broadcasting
* **The Problem**: Public announcements are static after seeding. There is no API or UI for the Captain or Crew to post new announcements during the flight.
* **Advancement**: Create a `POST /announcements` endpoint. Integrate an announcement composer in the Crew Command Center to broadcast announcements (e.g., flight status updates or weather delays) to all passenger seatbacks in real-time.

### B. Galley Inventory Management & Restock Controls
* **The Problem**: Inventory depletion works atomically via `reserve_item`, but there are no endpoints to query current levels or trigger replenishment.
* **Advancement**: Add `GET /crew/inventory` and `POST /crew/inventory/restock` APIs. Implement a real-time galley inventory dashboard widget in the crew interface so attendants can monitor and restock items.

### C. Cockpit Simulation Controller
* **The Problem**: Flight context data (ETA, altitude, flight phase) is static unless manually changed by overrides.
* **Advancement**: Create a mock Cockpit / Flight Deck panel that simulates auto-flight updates (updates ETA, triggers turbulence context, or updates altitude) and pushes notifications to both crew and passengers.

### D. Avionics Audio & Visual Alerting Systems
* **Advancement**: Implement audio alarms for critical alerts:
  1. Crew Dashboard: Play a warning chime when a high-urgency call (emergency/medical) enters the queue.
  2. Passenger Screen: Play a cockpit chime sound when the seatbelt sign state switches.

