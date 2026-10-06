from fastapi import Depends, Security, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from backend.security.tokens import verify_token

security = HTTPBearer(auto_error=False)


def get_current_token_data(
    credentials: HTTPAuthorizationCredentials = Security(security),
) -> dict:
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication credentials are required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = credentials.credentials
    data = verify_token(token)
    if not data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return data


def require_role(allowed_roles: list[str]):
    def dependency(data: dict = Depends(get_current_token_data)) -> dict:
        role = data.get("role")
        if role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Permission denied: insufficient privileges",
            )
        return data

    return dependency


require_crew = require_role(["crew"])


def authorized_flight(data: dict, requested: str | None = None) -> str:
    """Derive object scope from signed claims, never from a caller's query alone."""
    allowed = (
        [data["flight_id"]]
        if data["role"] == "passenger"
        else data.get("permitted_flights", [])
    )
    if not allowed or (requested is not None and requested not in allowed):
        raise HTTPException(status_code=403, detail="Flight access is not permitted")
    selected = requested or (
        data.get("flight_id") if data.get("flight_id") in allowed else allowed[0]
    )
    from backend.database.connection import get_connection

    with get_connection() as conn:
        flight = conn.execute(
            "SELECT state FROM flights WHERE flight_id=?", (selected,)
        ).fetchone()
        if data["role"] == "crew" and data.get("username"):
            assigned = conn.execute(
                "SELECT 1 FROM crew_assignments WHERE username=? AND flight_id=?",
                (data["username"], selected),
            ).fetchone()
            if not assigned:
                raise HTTPException(
                    status_code=403, detail="Crew assignment is no longer active"
                )
    if not flight or flight["state"] != "active":
        raise HTTPException(status_code=403, detail="Flight is not active")
    return selected
