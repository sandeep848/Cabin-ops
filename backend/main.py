# FastAPI API server for the CabinOps AI application. Imported directly as the entry point in deployment/start scripts.
import json
import asyncio
import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Depends, Security, status, File, UploadFile, Query, Request
from fastapi.responses import StreamingResponse
from fastapi.security import HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware

from backend.services.event_manager import event_manager

from backend.security import (
    generate_token,
    verify_token,
    security,
    get_current_token_data,
    require_role,
    require_crew,
    auth_limiter,
    request_limiter,
    verify_password,
)


from backend.database import (
    init_db,
    insert_task,
    list_tasks,
    update_task_status,
    get_db_flight_context,
    update_db_flight_context,
    get_analytics,
)
from backend.models import (
    PassengerRequest,
    ParsedRequest,
    FlightContext,
    PassengerAuth,
    CrewAuth,
    Announcement,
)
from backend.services.flight_rules import apply_flight_rules
from backend.services.intent_parser import parse_request
from backend.services.inventory import reserve_item, suggest_alternative
from backend.services.speech_to_text import transcribe_audio_stub

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("cabinops")

# Load .env file manually if it exists
def _load_env():
    from pathlib import Path
    env_file = Path(__file__).resolve().parent.parent / ".env"
    if env_file.exists():
        try:
            for line in env_file.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" in line:
                    k, v = line.split("=", 1)
                    k = k.strip()
                    v = v.strip().strip('"').strip("'")
                    if k and k not in os.environ:
                        os.environ[k] = v
        except Exception:
            pass

_load_env()



# Lifespan context manager
@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield

app = FastAPI(title="CabinOps AI Prototype", lifespan=lifespan)

# Environment CORS settings
origins_str = os.getenv("CORS_ALLOWED_ORIGINS", "")
if origins_str:
    origins = [o.strip() for o in origins_str.split(",") if o.strip()]
else:
    # Local development origins
    origins = [
        "http://127.0.0.1:5173",
        "http://localhost:5173",
        "http://127.0.0.1:5174",
        "http://localhost:5174",
    ]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Content-Security-Policy"] = "default-src 'self'; frame-ancestors 'none';"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    if os.getenv("ENV", "production") == "production":
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return response


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/events")
async def events_endpoint(token: str | None = Query(None)):
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token is missing"
        )
    token_data = verify_token(token)
    if not token_data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )

    async def event_generator():
        queue = event_manager.subscribe()
        try:
            yield f"data: {json.dumps({'status': 'connected'})}\n\n"
            while True:
                message = await queue.get()
                data = json.dumps(message) if isinstance(message, (dict, list)) else str(message)
                yield f"data: {data}\n\n"
        except asyncio.CancelledError:
            logger.info("SSE connection cancelled/client disconnected")
            raise
        finally:
            event_manager.unsubscribe(queue)

    return StreamingResponse(event_generator(), media_type="text/event-stream")



@app.post("/auth/crew")
def auth_crew(payload: CrewAuth, _ = Depends(auth_limiter)) -> dict:
    username = payload.username
    password = payload.password
    
    from backend.database import get_user_by_username
    from backend.security import verify_password
    
    user = get_user_by_username(username)
    if not user or not verify_password(user["password_hash"], password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid crew credentials"
        )
        
    role = user["role"]
    token = generate_token({"role": role, "username": username, "permitted_flights": ["APX-001"]})
    return {"status": "success", "token": token, "role": role}

@app.post("/auth/passenger")
def auth_passenger(payload: PassengerAuth, _ = Depends(auth_limiter)) -> dict:
    seat = payload.seat
    booking_ref = payload.booking_reference
    
    from backend.database import verify_booking
    
    if booking_ref.upper() == "DEMO" or verify_booking(seat, booking_ref):
        token = generate_token({"role": "passenger", "seat": seat.upper(), "flight_id": "APX-001"})
        return {"status": "success", "token": token, "role": "passenger"}
        
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid seat or booking reference. Try booking reference 'DEMO'."
    )

# Flight Context Endpoints
@app.get("/flight-context", response_model=FlightContext)
def get_flight_context(flight_id: str = "APX-001") -> dict:
    try:
        return get_db_flight_context(flight_id)
    except Exception as exc:
        logger.error(f"Error getting flight context: {exc}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error retrieving flight context")

@app.post("/flight-context")
async def update_flight_context(payload: FlightContext, token_data: dict = Depends(require_crew)) -> dict:
    try:
        flight_id = token_data.get("flight_id") or (token_data.get("permitted_flights", ["APX-001"])[0] if token_data.get("permitted_flights") else "APX-001")
        ctx_dict = payload.model_dump()
        update_db_flight_context(ctx_dict, flight_id)
        await event_manager.broadcast({"topic": "flight_context", "action": "update"})
        return {"status": "success", "flight_context": ctx_dict}
    except Exception as exc:
        logger.error(f"Error updating flight context: {exc}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error updating flight context")

# Passenger Request Ingress
@app.post("/request", response_model=ParsedRequest)
async def create_request(
    payload: PassengerRequest,
    _ = Depends(request_limiter),
    token_data: dict = Depends(require_role(["passenger"]))
) -> dict:
    if token_data.get("seat", "").upper() != payload.seat.upper():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Seat mismatch: token is for seat {token_data.get('seat')}, but request is for {payload.seat}"
        )
    parsed = parse_request(payload.text, payload.seat)
    flight_id = "APX-001"
    
    try:
        flight_context = get_db_flight_context(flight_id)
        if not flight_context:
            raise ValueError("Flight context not found")
    except Exception as exc:
        logger.error(f"Failed to fetch flight context: {exc}")
        if parsed["intent"] in {"medical_assistance", "emergency"}:
            flight_context = {"flight_phase": "cruise", "seatbelt_sign": False, "meal_service_active": True, "minutes_to_landing": 90}
        else:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Flight operations database is temporarily unavailable. Non-emergency service requests cannot be processed."
            )
        
    parsed = apply_flight_rules(parsed, flight_context)

    # Wire inventory checking and reservation
    item = parsed.get("slots", {}).get("item")
    if item and parsed["crew_required"]:
        if not reserve_item(item):
            parsed["crew_required"] = False
            parsed["assigned_zone"] = None
            parsed["status"] = "rejected"
            alt = suggest_alternative(item)
            if alt:
                parsed["action"] = f"Requested item '{item.replace('_', ' ').capitalize()}' is currently unavailable. Recommended alternative: '{alt.replace('_', ' ').capitalize()}'."
            else:
                parsed["action"] = f"Requested item '{item.replace('_', ' ').capitalize()}' is currently unavailable."
        else:
            parsed["action"] = f"Confirmed: 1x '{item.replace('_', ' ').capitalize()}' allocated from galley inventory. {parsed['action']}"

    # Wire announcement history lookup
    if parsed["intent"] == "missed_announcement":
        try:
            from backend.database import list_announcements
            speaker_filter = "Captain" if "captain" in payload.text.lower() else None
            matched = list_announcements(speaker=speaker_filter, limit=1, flight_id=flight_id)
            if matched:
                latest = matched[0]
                parsed["action"] = f"{latest['speaker']} ({latest['timestamp']}): \"{latest['text']}\""
            else:
                parsed["action"] = "No recent announcements matching your query were found."
        except Exception as e:
            logger.error(f"Unable to retrieve announcements: {e}", exc_info=True)
            parsed["action"] = "Unable to retrieve announcements due to a server error."

    if parsed["crew_required"] and parsed["assigned_zone"]:
        insert_task(
            seat=parsed["seat"],
            zone=parsed["assigned_zone"],
            intent=parsed["intent"],
            urgency=parsed["urgency"],
            status=parsed["status"],
            action=parsed["action"],
            flight_id=flight_id,
        )

    await event_manager.broadcast({"topic": "tasks", "action": "update"})
    return parsed

# Passenger Specific Requests Retrieval
@app.get("/passenger/requests")
def get_passenger_requests(
    seat: str,
    flight_id: str = "APX-001",
    token_data: dict = Depends(require_role(["passenger"]))
) -> list[dict]:
    if token_data.get("seat", "").upper() != seat.upper():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Seat mismatch: token is for seat {token_data.get('seat')}, but requested seat is {seat}"
        )
    try:
        return list_tasks(seat=seat, flight_id=flight_id)
    except Exception as exc:
        logger.error(f"Error fetching passenger requests: {exc}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error fetching your requests")

# Announcements Endpoint
@app.get("/announcements", response_model=list[Announcement])
def get_announcements(flight_id: str = "APX-001") -> list[dict]:
    try:
        from backend.database import list_announcements
        return list_announcements(flight_id=flight_id)
    except Exception as exc:
        logger.error(f"Error loading announcements: {exc}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error loading announcements")

# Crew Bookings Endpoint
@app.get("/crew/bookings/{seat}")
def get_booking_details(seat: str, token_data: dict = Depends(require_crew)) -> dict:
    try:
        from backend.database import get_booking_by_seat
        booking = get_booking_by_seat(seat)
        if not booking:
            raise HTTPException(status_code=404, detail=f"No booking found for seat {seat}")
        return {
            "seat": booking["seat"],
            "passenger_name": booking["passenger_name"],
            "booking_reference": booking["booking_reference"]
        }
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"Error retrieving booking details for seat {seat}: {exc}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error retrieving booking details")

# Crew Dashboard Tasks Retrieval
@app.get("/crew/tasks")
def crew_tasks(
    status: str | None = None,
    seat: str | None = None,
    zone: str | None = None,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    token_data: dict = Depends(require_crew)
) -> list[dict]:
    try:
        flight_id = token_data.get("flight_id") or (token_data.get("permitted_flights", ["APX-001"])[0] if token_data.get("permitted_flights") else "APX-001")
        return list_tasks(status=status, seat=seat, zone=zone, limit=limit, offset=offset, flight_id=flight_id)
    except Exception as exc:
        logger.error(f"Error fetching crew tasks: {exc}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error fetching tasks")

# Crew Dashboard Analytics
@app.get("/analytics/summary")
def analytics_summary(token_data: dict = Depends(require_crew)) -> dict:
    try:
        flight_id = token_data.get("flight_id") or (token_data.get("permitted_flights", ["APX-001"])[0] if token_data.get("permitted_flights") else "APX-001")
        return get_analytics(flight_id=flight_id)
    except Exception as exc:
        logger.error(f"Error aggregating analytics: {exc}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error calculating analytics")

@app.post("/crew/tasks/clear")
async def clear_tasks(token_data: dict = Depends(require_crew)) -> dict:
    try:
        from backend.database import clear_all_tasks
        clear_all_tasks()
        await event_manager.broadcast({"topic": "tasks", "action": "update"})
        return {"status": "success", "message": "All passenger requests cleared and inventory reset."}
    except Exception as exc:
        logger.error(f"Error clearing tasks: {exc}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error clearing tasks")

# Task State Transitions
@app.post("/crew/tasks/{task_id}/accept")
async def accept_task(task_id: int, token_data: dict = Depends(require_crew)) -> dict:
    try:
        permitted = token_data.get("permitted_flights", [])
        success = update_task_status(task_id, "accepted", permitted_flights=permitted)
        if not success:
            raise HTTPException(status_code=404, detail="Task not found or unable to accept")
        await event_manager.broadcast({"topic": "tasks", "action": "update"})
        return {"status": "success", "message": f"Task {task_id} accepted"}
    except HTTPException:
        raise
    except ValueError as val_err:
        if "Permission denied" in str(val_err):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(val_err))
        raise HTTPException(status_code=400, detail=str(val_err))
    except Exception as exc:
        logger.error(f"Error accepting task: {exc}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error updating task status")

@app.post("/crew/tasks/{task_id}/complete")
async def complete_task(task_id: int, token_data: dict = Depends(require_crew)) -> dict:
    try:
        permitted = token_data.get("permitted_flights", [])
        success = update_task_status(task_id, "completed", permitted_flights=permitted)
        if not success:
            raise HTTPException(status_code=404, detail="Task not found or unable to complete")
        await event_manager.broadcast({"topic": "tasks", "action": "update"})
        return {"status": "success", "message": f"Task {task_id} completed"}
    except HTTPException:
        raise
    except ValueError as val_err:
        if "Permission denied" in str(val_err):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(val_err))
        raise HTTPException(status_code=400, detail=str(val_err))
    except Exception as exc:
        logger.error(f"Error completing task: {exc}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error updating task status")

# POST Announcement - Crew Only
@app.post("/announcements")
async def post_announcement(
    payload: Announcement,
    token_data: dict = Depends(require_crew)
) -> dict:
    try:
        from backend.database import add_announcement
        from datetime import datetime, timezone
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        flight_id = token_data.get("flight_id") or (token_data.get("permitted_flights", ["APX-001"])[0] if token_data.get("permitted_flights") else "APX-001")
        ann_id = add_announcement(
            speaker=payload.speaker,
            text=payload.text,
            timestamp=timestamp,
            flight_id=flight_id
        )
        await event_manager.broadcast({"topic": "announcements", "action": "update"})
        return {"status": "success", "id": ann_id, "timestamp": timestamp}
    except Exception as exc:
        logger.error(f"Error posting announcement: {exc}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error posting announcement")

# GET Inventory - Crew Only
@app.get("/crew/inventory")
def get_inventory(token_data: dict = Depends(require_crew)) -> list[dict]:
    try:
        from backend.database import get_inventory_levels
        return get_inventory_levels()
    except Exception as exc:
        logger.error(f"Error fetching inventory: {exc}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error fetching inventory")

# POST Inventory Restock - Crew Only  
@app.post("/crew/inventory/restock")
def restock_inventory(
    item: str,
    quantity: int = Query(10, ge=1, le=100),
    token_data: dict = Depends(require_crew)
) -> dict:
    try:
        from backend.database import restock_inventory_item
        new_stock = restock_inventory_item(item, quantity)
        if new_stock is None:
            raise HTTPException(status_code=404, detail=f"Item '{item}' not found in inventory")
        return {"status": "success", "item": item, "new_stock": new_stock}
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"Error restocking inventory: {exc}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error restocking inventory")

# Speech to Text transcription endpoint
@app.post("/transcribe")
def transcribe_audio(
    file: UploadFile = File(...),
    _ = Depends(request_limiter)
) -> dict:
    try:
        max_size = 5 * 1024 * 1024  # 5MB
        
        # Read the first chunk to check magic number and size
        first_chunk = file.file.read(8192)
        if not first_chunk:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Empty file uploaded."
            )
            
        # Common audio magic headers validation
        is_audio = False
        if first_chunk.startswith(b"RIFF") and b"WAVE" in first_chunk[:16]:
            is_audio = True
        elif first_chunk.startswith(b"ID3") or (len(first_chunk) >= 2 and first_chunk[0] == 0xFF and (first_chunk[1] & 0xE0) == 0xE0):
            is_audio = True
        elif first_chunk.startswith(b"OggS"):
            is_audio = True
        elif first_chunk.startswith(b"fLaC"):
            is_audio = True
        elif first_chunk.startswith(b"\x1A\x45\xDF\xA3"):
            is_audio = True
        elif file.content_type and file.content_type.startswith("audio/"):
            is_audio = True
            
        if not is_audio:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid file format. Only audio files are allowed."
            )
            
        chunks = [first_chunk]
        size = len(first_chunk)
        
        while True:
            chunk = file.file.read(8192)
            if not chunk:
                break
            size += len(chunk)
            if size > max_size:
                raise HTTPException(
                    status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                    detail="Uploaded file exceeds the 5MB size limit."
                )
            chunks.append(chunk)
            
        content = b"".join(chunks)
        text = transcribe_audio_stub(content)
        return {"status": "success", "text": text}
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"Error transcribing audio: {exc}", exc_info=True)
        raise HTTPException(status_code=500, detail="Audio transcription failed")
