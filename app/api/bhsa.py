from fastapi import APIRouter, BackgroundTasks, HTTPException, Response

from app.models.bhsa import BHSALoadResponse, BHSAStatusResponse, ClauseData, PassageResponse
from app.services.bhsa import loader

router = APIRouter()


@router.get("/status", response_model=BHSAStatusResponse)
async def get_bhsa_status() -> BHSAStatusResponse | Response:
    bhsa_status = loader.get_status()

    if bhsa_status.is_loaded:
        return BHSAStatusResponse(status="loaded", bhsa_loaded=True, message=bhsa_status.message)

    if bhsa_status.is_loading:
        return Response(
            content=BHSAStatusResponse(
                status="loading", bhsa_loaded=False, message=bhsa_status.message
            ).model_dump_json(),
            status_code=202,
            media_type="application/json",
        )

    return Response(
        content=BHSAStatusResponse(
            status="not_loaded", bhsa_loaded=False, message=bhsa_status.message
        ).model_dump_json(),
        status_code=503,
        media_type="application/json",
    )


@router.post("/load", response_model=BHSALoadResponse)
async def load_bhsa_data(background_tasks: BackgroundTasks) -> BHSALoadResponse:
    bhsa_status = loader.get_status()
    if bhsa_status.is_loaded:
        return BHSALoadResponse(status="already_loaded", message="BHSA data is already loaded")
    if bhsa_status.is_loading:
        return BHSALoadResponse(status="loading", message="BHSA data is already loading")

    background_tasks.add_task(loader.load)
    return BHSALoadResponse(
        status="loading_started",
        message="BHSA data loading started in background",
    )


@router.get("/passage", response_model=PassageResponse)
async def fetch_passage(ref: str) -> PassageResponse:
    bhsa_status = loader.get_status()
    if bhsa_status.is_loading:
        raise HTTPException(
            status_code=202,
            detail="BHSA data is still loading. Please try again shortly.",
        )
    if not bhsa_status.is_loaded:
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


@router.get("/books/{book_name}/verse-counts")
async def get_verse_counts(book_name: str) -> dict[str, int]:

    bhsa_status = loader.get_status()
    if not bhsa_status.is_loaded:
        raise HTTPException(status_code=503, detail="BHSA not loaded")
    try:
        counts = loader.get_verse_counts(book_name)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return {str(k): v for k, v in counts.items()}
