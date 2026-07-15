"""The acousteme HTTP surface is retired (ENG-290).

It served the recorded voices of indigenous storytellers — LGPD-sensitive personal data,
exactly what PRD §12 calls sensitive — to **any authenticated Tripod user**: no app
role, no project scoping, nothing but `Depends(get_current_user)`. The collection
listing beside it handed over every audio id, so there was not even a slug to guess.

Nothing consumed it. The routes were twenty hours old when this landed, and the one
client they were built for (`shemaobt/beads`) predates them by four months and reads a
checked-in static `acoustemes.json`, never the API.

The *service* survives. The corpus importer writes through it, and the Sound Necklace
signs through it. What is gone is the ungated door standing in front of it.
"""

from __future__ import annotations

RETIRED_PREFIX = "/api/oc/acoustemes"


def test_no_acousteme_route_is_served_at_this_prefix():
    """Not gated, not deprecated — gone.

    A route that mints a signed URL for a private recording behind nothing but "is
    logged in" has no safe configuration, so there is nothing here to tighten.
    """
    from app.main import app

    leaking = [path for path in app.openapi()["paths"] if path.startswith(RETIRED_PREFIX)]

    assert not leaking, f"the acousteme HTTP surface is back: {leaking}"


def test_no_route_anywhere_serves_an_acousteme_dto():
    """The prefix test names the obvious regression; this one catches the disguised one.

    FastAPI emits a component schema only when a route references it, so an acousteme
    response model in the schema means a route serves it — under *any* prefix, by any
    method. Re-mounting the surface at, say, ``/api/oc/audio-tokens`` would slip past a
    prefix check and be caught here.
    """
    from app.main import app

    schemas = app.openapi()["components"]["schemas"]
    serving = [name for name in schemas if name.startswith("Acousteme")]

    assert not serving, f"a route is serving an acousteme DTO again: {serving}"


async def test_the_service_beneath_it_still_resolves_an_artifact(db_session):
    """Retiring the door must not take the room with it.

    The importer writes acoustemes and the Sound Necklace reads them, both through this
    service — which the deletion leaves untouched. A behaviour check, not a hasattr:
    seed a row and resolve it the way the read path does (newest-READY), so a change
    that breaks resolution fails here rather than passing a name-only assertion.
    """
    from app.db.models.oc_acousteme import OC_AcoustemeArtifact
    from app.services.oral_collector import acousteme_service

    db_session.add(
        OC_AcoustemeArtifact(
            audio_id="ruth-retirement-probe",
            codebook_version="terena-xlsr53-k100-v1",
            collection="terena-ruth",
            status="ready",
            gcs_bucket="terena-pilot",
            gcs_object="acoustemes/ruth-retirement-probe.json.gz",
            audio_bucket="terena-pilot",
            audio_object="ruth/probe.mp3",
        )
    )
    await db_session.commit()

    stored = await acousteme_service.get_artifact(db_session, "ruth-retirement-probe")
    assert stored.audio_object == "ruth/probe.mp3"
