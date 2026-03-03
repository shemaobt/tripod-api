from fastapi import APIRouter, BackgroundTasks, HTTPException, Response

from app.models.bhsa import BHSAStatusResponse, ClauseData, PassageResponse
from app.services.bhsa import loader

router = APIRouter()


@router.get("/status", response_model=BHSAStatusResponse)
async def get_bhsa_status() -> BHSAStatusResponse | Response:
    status = loader.get_status()

    if status["is_loaded"]:
        return BHSAStatusResponse(
            status="loaded", bhsa_loaded=True, message=status["message"]
        )

    if status["is_loading"]:
        return Response(
            content=BHSAStatusResponse(
                status="loading", bhsa_loaded=False, message=status["message"]
            ).model_dump_json(),
            status_code=202,
            media_type="application/json",
        )

    return Response(
        content=BHSAStatusResponse(
            status="not_loaded", bhsa_loaded=False, message=status["message"]
        ).model_dump_json(),
        status_code=503,
        media_type="application/json",
    )


@router.post("/load")
async def load_bhsa_data(background_tasks: BackgroundTasks) -> dict[str, str]:
    status = loader.get_status()
    if status["is_loaded"]:
        return {"status": "already_loaded", "message": "BHSA data is already loaded"}
    if status["is_loading"]:
        return {"status": "loading", "message": "BHSA data is already loading"}

    background_tasks.add_task(loader.load)
    return {
        "status": "loading_started",
        "message": "BHSA data loading started in background",
    }


@router.get("/passage", response_model=PassageResponse)
async def fetch_passage(ref: str) -> PassageResponse:
    status = loader.get_status()
    if status["is_loading"]:
        raise HTTPException(
            status_code=202,
            detail="BHSA data is still loading. Please try again shortly.",
        )
    if not status["is_loaded"]:
        raise HTTPException(
            status_code=503,
            detail="BHSA not loaded. Call POST /api/bhsa/load first",
        )

    try:
        data = loader.fetch_passage(ref)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    return PassageResponse(
        reference=data["reference"],
        source_lang=data["source_lang"],
        clauses=[ClauseData(**c) for c in data["clauses"]],
    )
