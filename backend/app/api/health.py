from fastapi import APIRouter, status

router = APIRouter(tags=["system"])


@router.get("/health", status_code=status.HTTP_200_OK)
def healthcheck() -> dict[str, str]:
    """Liveness endpoint; it intentionally exposes no sensitive configuration."""
    return {"status": "ok"}
