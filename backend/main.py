# Cabin Atlas API composition: service operations and passenger experience.
import json
import asyncio
import logging
import os
import hashlib
import uuid
import time
from contextlib import asynccontextmanager

from fastapi import (
    FastAPI,
    HTTPException,
    Depends,
    Security,
    status,
    File,
    UploadFile,
    Query,
    Request,
    Header,
    Response,
)
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.exceptions import RequestValidationError
from fastapi.security import HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware

from backend.services.event_manager import event_manager
from backend.services.fleet import configured_seat, profile_for_flight, assigned_flights

from backend.security.dependencies import authorized_flight
from backend.security.tokens import revoke_token
from backend.security.body_limit import BodyLimitMiddleware

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
from backend.services.speech_to_text import transcribe_audio as transcribe_audio_bytes

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("cabinops")


# Lifespan context manager
@asynccontextmanager
async def lifespan(app: FastAPI):
    if (
        os.getenv("ENV") == "production"
        and os.getenv("CREW_PASSWORD")
        and len(os.environ["CREW_PASSWORD"]) < 12
    ):
        raise RuntimeError("CREW_PASSWORD must contain at least 12 characters")
    init_db()
    from backend.services.recommendations import integrity_report

    if not integrity_report()["verified"]:
        raise RuntimeError("Media catalogue integrity check failed")
    yield


production = os.getenv("ENV") == "production"
app = FastAPI(
    title="Cabin Atlas API",
    version="3.0.0",
    lifespan=lifespan,
    docs_url=None if production else "/docs",
    redoc_url=None if production else "/redoc",
    openapi_url=None if production else "/openapi.json",
)
app.add_middleware(BodyLimitMiddleware)

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
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Authorization", "Content-Type", "Idempotency-Key"],
)


@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    started = time.monotonic()
    response = await call_next(request)
    response.headers["X-Request-ID"] = str(uuid.uuid4())
    logger.info(
        "request method=%s path=%s status=%s duration_ms=%.1f request_id=%s",
        request.method,
        request.url.path,
        response.status_code,
        (time.monotonic() - started) * 1000,
        response.headers["X-Request-ID"],
    )
    response.headers["Server-Timing"] = f"app;dur={(time.monotonic()-started)*1000:.1f}"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Cache-Control"] = "no-store"
    response.headers["Permissions-Policy"] = "camera=(), geolocation=(), payment=()"
    if request.url.path not in {"/docs", "/redoc"}:
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; frame-ancestors 'none';"
        )
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    if os.getenv("ENV", "production") == "production":
        response.headers["Strict-Transport-Security"] = (
            "max-age=31536000; includeSubDomains"
        )
    return response


@app.exception_handler(RequestValidationError)
async def safe_validation_error(request, error):
    # Never echo submitted booking credentials, passwords or passenger text.
    errors = [
        {"location": list(item["loc"]), "message": item["msg"], "type": item["type"]}
        for item in error.errors()
    ]
    return JSONResponse(
        status_code=422, content={"detail": "Invalid request data", "errors": errors}
    )


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/events")
async def events_endpoint(token_data: dict = Depends(get_current_token_data)):
    flight_id = authorized_flight(token_data)

    async def event_generator():
        queue = event_manager.subscribe(flight_id, token_data["jti"])
        try:
            yield 'data: {"status":"connected"}\n\n'
            while True:
                # Logout and expiry also close idle streams, before a heartbeat.
                from backend.database.connection import get_connection

                with get_connection() as conn:
                    active = conn.execute(
                        "SELECT 1 FROM sessions WHERE token_id = ? AND expires_at > ?",
                        (token_data["jti"], time.time()),
                    ).fetchone()
                if not active:
                    break
                try:
                    message = await asyncio.wait_for(queue.get(), timeout=15)
                except asyncio.TimeoutError:
                    yield ": heartbeat\n\n"
                    continue
                yield f"data: {json.dumps(message)}\n\n"
        except asyncio.CancelledError:
            raise
        finally:
            event_manager.unsubscribe(queue)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-store", "X-Accel-Buffering": "no"},
    )


@app.post("/auth/logout")
def logout_session(
    response: Response, token_data: dict = Depends(get_current_token_data)
):
    revoke_token(token_data)
    response.delete_cookie("atlas_media", path="/")
    return {"status": "signed_out"}


@app.post("/auth/crew")
def auth_crew(payload: CrewAuth, _=Depends(auth_limiter)) -> dict:
    username = payload.username
    password = payload.password

    from backend.database import get_user_by_username
    from backend.security import verify_password

    user = get_user_by_username(username)
    from backend.security.hashing import DUMMY_PASSWORD_HASH

    valid_password = verify_password(
        user["password_hash"] if user else DUMMY_PASSWORD_HASH, password
    )
    if not user or not valid_password:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid crew credentials"
        )

    role = user["role"]
    permitted_flights = assigned_flights(username)
    if not permitted_flights:
        raise HTTPException(
            status_code=403, detail="No active flights are assigned to this account"
        )
    flight_id = permitted_flights[0]
    token = generate_token(
        {
            "role": role,
            "username": username,
            "flight_id": flight_id,
            "permitted_flights": permitted_flights,
        }
    )
    return {
        "status": "success",
        "token": token,
        "role": role,
        "flight_id": flight_id,
        "flights": permitted_flights,
    }


@app.post("/auth/passenger")
def auth_passenger(payload: PassengerAuth, _=Depends(auth_limiter)) -> dict:
    seat = payload.seat
    booking_ref = payload.booking_reference

    flight_id = None
    from backend.database.connection import get_connection
    from backend.database.operations import verify_booking

    with get_connection() as conn:
        rows = conn.execute(
            "SELECT flight_id FROM bookings WHERE seat = ?", (seat,)
        ).fetchall()
    for row in rows:
        if verify_booking(seat, booking_ref, row["flight_id"]):
            flight_id = row["flight_id"]
            break

    if not flight_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid seat or booking reference.",
        )

    configured_seat(flight_id, seat)
    token = generate_token(
        {"role": "passenger", "seat": seat.upper(), "flight_id": flight_id}
    )
    return {
        "status": "success",
        "token": token,
        "role": "passenger",
        "flight_id": flight_id,
    }


# Flight Context Endpoints
@app.get("/flight-context", response_model=FlightContext)
def get_flight_context(
    flight_id: str | None = None, token_data: dict = Depends(get_current_token_data)
) -> dict:
    flight_id = authorized_flight(token_data, flight_id)
    try:
        return get_db_flight_context(flight_id)
    except Exception as exc:
        logger.error(f"Error getting flight context: {exc}", exc_info=True)
        raise HTTPException(
            status_code=500, detail="Internal server error retrieving flight context"
        )


@app.post("/flight-context")
async def update_flight_context(
    payload: FlightContext, token_data: dict = Depends(require_crew)
) -> dict:
    try:
        flight_id = authorized_flight(token_data)
        ctx_dict = payload.model_dump()
        update_db_flight_context(
            ctx_dict, flight_id, actor=token_data.get("username", "crew")
        )
        await event_manager.broadcast(
            {"flight_id": flight_id, "topic": "flight_context", "action": "update"}
        )
        return {"status": "success", "flight_context": ctx_dict}
    except Exception as exc:
        logger.error(f"Error updating flight context: {exc}", exc_info=True)
        raise HTTPException(
            status_code=500, detail="Internal server error updating flight context"
        )


# Passenger Request Ingress
@app.post("/request", response_model=ParsedRequest)
async def create_request(
    payload: PassengerRequest,
    idempotency_key: str | None = Header(None, max_length=128, min_length=8),
    _=Depends(request_limiter),
    token_data: dict = Depends(require_role(["passenger"])),
) -> dict:
    if token_data.get("seat", "").upper() != payload.seat.upper():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Seat mismatch: token is for seat {token_data.get('seat')}, but request is for {payload.seat}",
        )
    flight_id = authorized_flight(token_data)
    seat_info = configured_seat(flight_id, payload.seat)
    parsed = parse_request(payload.text, payload.seat, seat_info["zone"])
    parsed["assigned_zone"] = seat_info["zone"] if parsed["crew_required"] else None
    if payload.item and parsed["urgency"] != "high":
        from backend.database.operations import get_inventory_levels

        chosen = next(
            (
                row
                for row in get_inventory_levels(flight_id)
                if row["item"] == payload.item
            ),
            None,
        )
        if not chosen:
            raise HTTPException(
                status_code=422, detail="Item is not in this flight's loading manifest"
            )
        intent = {
            "food": "meal_request",
            "beverage": "water_request",
            "comfort": "blanket_request",
            "equipment": "general_assistance",
        }[chosen["category"]]
        parsed.update(
            intent=intent,
            urgency="low",
            crew_required=True,
            assigned_zone=seat_info["zone"],
            status="pending",
            slots={"item": chosen["item"]},
            confidence=1.0,
            action=f"Crew delivery requested: {payload.quantity} × {chosen['name']}.",
        )

    try:
        flight_context = get_db_flight_context(flight_id)
        if not flight_context:
            raise ValueError("Flight context not found")
    except Exception as exc:
        logger.error(f"Failed to fetch flight context: {exc}")
        if parsed["intent"] in {"medical_assistance", "emergency"}:
            flight_context = {
                "flight_phase": "cruise",
                "seatbelt_sign": False,
                "meal_service_active": True,
                "minutes_to_landing": 90,
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Flight operations database is temporarily unavailable. Non-emergency service requests cannot be processed.",
            )

    parsed = apply_flight_rules(parsed, flight_context)

    from backend.database.connection import get_connection

    # A reservation and its request record commit together, or roll back together.
    with get_connection() as connection:
        connection.execute("BEGIN IMMEDIATE")
        payload_hash = hashlib.sha256(payload.model_dump_json().encode()).hexdigest()
        if idempotency_key:
            receipt = connection.execute(
                "SELECT payload_hash, response FROM request_receipts WHERE flight_id = ? AND seat = ? AND request_key = ?",
                (flight_id, payload.seat, idempotency_key),
            ).fetchone()
            if receipt:
                if receipt["payload_hash"] != payload_hash:
                    raise HTTPException(
                        status_code=409,
                        detail="Request key was already used for different content",
                    )
                return json.loads(receipt["response"])
        # Wire inventory checking and reservation
        item = parsed.get("slots", {}).get("item")
        inventory_reserved = False
        if item and parsed["crew_required"]:
            if not reserve_item(
                item,
                quantity=payload.quantity,
                connection=connection,
                flight_id=flight_id,
            ):
                parsed["crew_required"] = False
                parsed["assigned_zone"] = None
                parsed["status"] = "rejected"
                alt = suggest_alternative(item, flight_id)
                if alt:
                    parsed["action"] = (
                        f"Requested item '{item.replace('_', ' ').capitalize()}' is currently unavailable. Recommended alternative: '{alt.replace('_', ' ').capitalize()}'."
                    )
                else:
                    parsed["action"] = (
                        f"Requested item '{item.replace('_', ' ').capitalize()}' is currently unavailable."
                    )
            else:
                inventory_reserved = True
                parsed["action"] = (
                    f"Confirmed: {payload.quantity}x '{item.replace('_', ' ').capitalize()}' allocated from galley inventory. {parsed['action']}"
                )

        # Wire announcement history lookup
        if parsed["intent"] == "missed_announcement":
            try:
                from backend.database import list_announcements

                speaker_filter = (
                    "Captain" if "captain" in payload.text.lower() else None
                )
                matched = list_announcements(
                    speaker=speaker_filter, limit=1, flight_id=flight_id
                )
                if matched:
                    latest = matched[0]
                    parsed["action"] = (
                        f"{latest['speaker']} ({latest['timestamp']}): \"{latest['text']}\""
                    )
                else:
                    parsed["action"] = (
                        "No recent announcements matching your query were found."
                    )
            except Exception as e:
                logger.error(f"Unable to retrieve announcements: {e}", exc_info=True)
                parsed["action"] = (
                    "Unable to retrieve announcements due to a server error."
                )

        zone = parsed["assigned_zone"]
        if not zone:
            zone = seat_info["zone"]

        task_id = insert_task(
            seat=parsed["seat"],
            zone=zone,
            intent=parsed["intent"],
            urgency=parsed["urgency"],
            status=parsed["status"],
            action=parsed["action"],
            flight_id=flight_id,
            inventory_item=item,
            inventory_reserved=inventory_reserved,
            connection=connection,
            request_text=payload.text,
            input_modality=payload.input_modality,
            inventory_quantity=payload.quantity,
        )

        parsed["task_id"] = task_id
        from backend.services.operations import append_audit

        append_audit(
            connection,
            flight_id,
            "passenger:" + payload.seat,
            "request.created",
            parsed["intent"] + " · " + parsed["status"],
            task_id,
        )
        if idempotency_key:
            connection.execute(
                "INSERT INTO request_receipts (flight_id, seat, request_key, payload_hash, response, task_id) VALUES (?, ?, ?, ?, ?, ?)",
                (
                    flight_id,
                    payload.seat,
                    idempotency_key,
                    payload_hash,
                    json.dumps(parsed),
                    task_id,
                ),
            )

    await event_manager.broadcast(
        {"flight_id": flight_id, "topic": "tasks", "action": "update"}
    )
    if item:
        await event_manager.broadcast(
            {"flight_id": flight_id, "topic": "inventory", "action": "update"}
        )
    return parsed


# Passenger Specific Requests Retrieval
@app.get("/passenger/requests")
def get_passenger_requests(
    seat: str,
    flight_id: str | None = None,
    token_data: dict = Depends(require_role(["passenger"])),
) -> list[dict]:
    if token_data.get("seat", "").upper() != seat.upper():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Seat mismatch: token is for seat {token_data.get('seat')}, but requested seat is {seat}",
        )
    actual_flight_id = authorized_flight(token_data, flight_id)
    try:
        return list_tasks(seat=seat, flight_id=actual_flight_id)
    except Exception as exc:
        logger.error(f"Error fetching passenger requests: {exc}", exc_info=True)
        raise HTTPException(
            status_code=500, detail="Internal server error fetching your requests"
        )


# Announcements Endpoint
@app.get("/announcements", response_model=list[Announcement])
def get_announcements(
    flight_id: str | None = None, token_data: dict = Depends(get_current_token_data)
) -> list[dict]:
    flight_id = authorized_flight(token_data, flight_id)
    try:
        from backend.database import list_announcements

        return list_announcements(flight_id=flight_id)
    except Exception as exc:
        logger.error(f"Error loading announcements: {exc}", exc_info=True)
        raise HTTPException(
            status_code=500, detail="Internal server error loading announcements"
        )


# Crew Bookings Endpoint
@app.get("/crew/bookings/{seat}")
def get_booking_details(seat: str, token_data: dict = Depends(require_crew)) -> dict:
    try:
        from backend.database import get_booking_by_seat

        booking = get_booking_by_seat(seat, flight_id=authorized_flight(token_data))
        if not booking:
            raise HTTPException(
                status_code=404, detail=f"No booking found for seat {seat}"
            )
        return {"seat": booking["seat"], "passenger_name": booking["passenger_name"]}
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(
            f"Error retrieving booking details for seat {seat}: {exc}", exc_info=True
        )
        raise HTTPException(
            status_code=500, detail="Internal server error retrieving booking details"
        )


# Crew Dashboard Tasks Retrieval
@app.get("/crew/tasks")
def crew_tasks(
    status: str | None = None,
    seat: str | None = None,
    zone: str | None = None,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    token_data: dict = Depends(require_crew),
) -> list[dict]:
    try:
        flight_id = authorized_flight(token_data)
        return list_tasks(
            status=status,
            seat=seat,
            zone=zone,
            limit=limit,
            offset=offset,
            flight_id=flight_id,
            prioritize=True,
        )
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"Error fetching crew tasks: {exc}", exc_info=True)
        raise HTTPException(
            status_code=500, detail="Internal server error fetching tasks"
        )


# Crew Dashboard Analytics
@app.get("/analytics/summary")
def analytics_summary(token_data: dict = Depends(require_crew)) -> dict:
    try:
        flight_id = authorized_flight(token_data)
        return get_analytics(flight_id=flight_id)
    except Exception as exc:
        logger.error(f"Error aggregating analytics: {exc}", exc_info=True)
        raise HTTPException(
            status_code=500, detail="Internal server error calculating analytics"
        )


@app.post("/crew/tasks/clear")
async def clear_tasks(token_data: dict = Depends(require_crew)) -> dict:
    if os.getenv("ENV") == "production":
        raise HTTPException(
            status_code=403, detail="Request history cannot be cleared in production"
        )
    try:
        from backend.database import clear_all_tasks

        flight_id = authorized_flight(token_data)
        clear_all_tasks(flight_id=flight_id)
        await event_manager.broadcast(
            {"flight_id": flight_id, "topic": "tasks", "action": "update"}
        )
        return {
            "status": "success",
            "message": "Passenger request history cleared for this flight.",
        }
    except Exception as exc:
        logger.error(f"Error clearing tasks: {exc}", exc_info=True)
        raise HTTPException(
            status_code=500, detail="Internal server error clearing tasks"
        )


# Task State Transitions
@app.post("/crew/tasks/{task_id}/accept")
async def accept_task(task_id: int, token_data: dict = Depends(require_crew)) -> dict:
    flight_id = authorized_flight(token_data)
    try:
        permitted = [authorized_flight(token_data)]
        success = update_task_status(
            task_id,
            "accepted",
            permitted_flights=permitted,
            actor=token_data.get("username", "crew"),
        )
        if not success:
            raise HTTPException(
                status_code=404, detail="Task not found or unable to accept"
            )
        await event_manager.broadcast(
            {"flight_id": flight_id, "topic": "tasks", "action": "update"}
        )
        await event_manager.broadcast(
            {"flight_id": flight_id, "topic": "inventory", "action": "update"}
        )
        return {"status": "success", "message": f"Task {task_id} accepted"}
    except HTTPException:
        raise
    except ValueError as val_err:
        if "Permission denied" in str(val_err):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail=str(val_err)
            )
        raise HTTPException(status_code=400, detail=str(val_err))
    except Exception as exc:
        logger.error(f"Error accepting task: {exc}", exc_info=True)
        raise HTTPException(
            status_code=500, detail="Internal server error updating task status"
        )


@app.post("/crew/tasks/{task_id}/complete")
async def complete_task(task_id: int, token_data: dict = Depends(require_crew)) -> dict:
    flight_id = authorized_flight(token_data)
    try:
        permitted = [authorized_flight(token_data)]
        success = update_task_status(
            task_id,
            "completed",
            permitted_flights=permitted,
            actor=token_data.get("username", "crew"),
        )
        if not success:
            raise HTTPException(
                status_code=404, detail="Task not found or unable to complete"
            )
        await event_manager.broadcast(
            {"flight_id": flight_id, "topic": "tasks", "action": "update"}
        )
        await event_manager.broadcast(
            {"flight_id": flight_id, "topic": "inventory", "action": "update"}
        )
        return {"status": "success", "message": f"Task {task_id} completed"}
    except HTTPException:
        raise
    except ValueError as val_err:
        if "Permission denied" in str(val_err):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail=str(val_err)
            )
        raise HTTPException(status_code=400, detail=str(val_err))
    except Exception as exc:
        logger.error(f"Error completing task: {exc}", exc_info=True)
        raise HTTPException(
            status_code=500, detail="Internal server error updating task status"
        )


# POST Announcement - Crew Only
@app.post("/announcements")
async def post_announcement(
    payload: Announcement, token_data: dict = Depends(require_crew)
) -> dict:
    try:
        from backend.database import add_announcement
        from datetime import datetime, timezone

        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        flight_id = authorized_flight(token_data)
        ann_id = add_announcement(
            speaker=payload.speaker,
            text=payload.text,
            timestamp=timestamp,
            actor=token_data.get("username", "crew"),
            flight_id=flight_id,
        )
        await event_manager.broadcast(
            {"flight_id": flight_id, "topic": "announcements", "action": "update"}
        )
        return {"status": "success", "id": ann_id, "timestamp": timestamp}
    except Exception as exc:
        logger.error(f"Error posting announcement: {exc}", exc_info=True)
        raise HTTPException(
            status_code=500, detail="Internal server error posting announcement"
        )


# GET Inventory - Crew Only
@app.get("/crew/inventory")
def get_inventory(token_data: dict = Depends(require_crew)) -> list[dict]:
    try:
        from backend.database import get_inventory_levels

        return get_inventory_levels(authorized_flight(token_data))
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"Error fetching inventory: {exc}", exc_info=True)
        raise HTTPException(
            status_code=500, detail="Internal server error fetching inventory"
        )


# POST Inventory Restock - Crew Only
@app.post("/crew/inventory/restock")
async def restock_inventory(
    item: str,
    quantity: int = Query(10, ge=1, le=100),
    token_data: dict = Depends(require_crew),
) -> dict:
    flight_id = authorized_flight(token_data)
    try:
        from backend.database import restock_inventory_item

        new_stock = restock_inventory_item(
            item,
            quantity,
            flight_id=authorized_flight(token_data),
            actor=token_data.get("username", "crew"),
        )
        if new_stock is None:
            raise HTTPException(
                status_code=404, detail=f"Item '{item}' not found in inventory"
            )
        await event_manager.broadcast(
            {"flight_id": flight_id, "topic": "inventory", "action": "update"}
        )
        return {"status": "success", "item": item, "new_stock": new_stock}
    except HTTPException:
        raise
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except Exception as exc:
        logger.error(f"Error restocking inventory: {exc}", exc_info=True)
        raise HTTPException(
            status_code=500, detail="Internal server error restocking inventory"
        )


# Speech to Text transcription endpoint
@app.post("/transcribe")
def transcribe_audio(
    file: UploadFile = File(...),
    _=Depends(request_limiter),
    token_data: dict = Depends(require_role(["passenger"])),
) -> dict:
    try:
        max_size = 5 * 1024 * 1024  # 5MB

        # Read the first chunk to check magic number and size
        first_chunk = file.file.read(8192)
        if not first_chunk:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Empty file uploaded."
            )

        # Common audio magic headers validation
        is_audio = False
        if first_chunk.startswith(b"RIFF") and b"WAVE" in first_chunk[:16]:
            is_audio = True
        elif first_chunk.startswith(b"ID3") or (
            len(first_chunk) >= 2
            and first_chunk[0] == 0xFF
            and (first_chunk[1] & 0xE0) == 0xE0
        ):
            is_audio = True
        elif first_chunk.startswith(b"OggS"):
            is_audio = True
        elif first_chunk.startswith(b"fLaC"):
            is_audio = True
        elif first_chunk.startswith(b"\x1a\x45\xdf\xa3"):
            is_audio = True

        if not is_audio:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid file format. Only audio files are allowed.",
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
                    detail="Uploaded file exceeds the 5MB size limit.",
                )
            chunks.append(chunk)

        content = b"".join(chunks)
        text = transcribe_audio_bytes(content)
        return {"status": "success", "text": text}
    except HTTPException:
        raise
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        logger.error(f"Error transcribing audio: {exc}", exc_info=True)
        raise HTTPException(status_code=500, detail="Audio transcription failed")


@app.get("/ready")
def readiness():
    from backend.database.connection import get_connection

    try:
        with get_connection() as conn:
            conn.execute("SELECT COUNT(*) FROM tasks").fetchone()
        return {"status": "ready", "database": "reachable"}
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Database is unavailable") from exc


@app.get("/crew/operations")
def crew_operations(token_data: dict = Depends(require_crew)):
    from backend.services.operations import operational_summary

    return operational_summary(authorized_flight(token_data))


@app.get("/crew/audit")
def crew_audit(
    task_id: int | None = None,
    limit: int = Query(200, ge=1, le=1000),
    token_data: dict = Depends(require_crew),
):
    from backend.services.operations import audit_history

    return audit_history(authorized_flight(token_data), task_id, limit)


from backend.routes.experience import router as experience_router

app.include_router(experience_router)


@app.get("/flight-profile")
def flight_profile(token_data: dict = Depends(get_current_token_data)):
    return profile_for_flight(authorized_flight(token_data))


@app.post("/crew/flight/{flight_id}/select")
def select_flight(flight_id: str, token_data: dict = Depends(require_crew)):
    permitted = assigned_flights(token_data.get("username", ""))
    if flight_id not in permitted:
        raise HTTPException(
            status_code=403, detail="Flight is not assigned to this crew account"
        )
    profile_for_flight(flight_id)
    next_token = generate_token(
        {
            "role": "crew",
            "username": token_data["username"],
            "flight_id": flight_id,
            "permitted_flights": permitted,
        }
    )
    revoke_token(token_data)
    return {
        "token": next_token,
        "flight_id": flight_id,
        "flights": permitted,
        "role": "crew",
    }


@app.post("/passenger/requests/{task_id}/cancel")
async def cancel_request(
    task_id: int, token_data: dict = Depends(require_role(["passenger"]))
):
    from backend.database.connection import get_connection
    from backend.services.operations import append_audit

    flight_id = authorized_flight(token_data)
    with get_connection() as conn:
        conn.execute("BEGIN IMMEDIATE")
        row = conn.execute(
            "SELECT * FROM tasks WHERE id=? AND flight_id=? AND seat=?",
            (task_id, flight_id, token_data["seat"]),
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Request not found")
        if row["status"] == "ignored":
            return {"status": "cancelled"}
        if row["status"] not in {"pending", "delayed"} or row["urgency"] == "high":
            raise HTTPException(
                status_code=409,
                detail="This request is already being handled; please speak to the crew",
            )
        if row["inventory_reserved"]:
            conn.execute(
                "UPDATE flight_inventory SET stock=stock+? WHERE flight_id=? AND item=?",
                (row["inventory_quantity"], flight_id, row["inventory_item"]),
            )
        conn.execute(
            "UPDATE tasks SET status='ignored',inventory_reserved=0,action='Cancelled by passenger' WHERE id=?",
            (task_id,),
        )
        append_audit(
            conn,
            flight_id,
            "passenger:" + token_data["seat"],
            "request.cancelled",
            "Released unfulfilled reservation",
            task_id,
        )
    await event_manager.broadcast(
        {"flight_id": flight_id, "topic": "tasks", "action": "update"}
    )
    await event_manager.broadcast(
        {"flight_id": flight_id, "topic": "inventory", "action": "update"}
    )
    return {"status": "cancelled"}
