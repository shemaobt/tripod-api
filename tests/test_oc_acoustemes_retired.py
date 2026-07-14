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


def test_no_acousteme_route_is_served_at_all():
    """Not gated, not deprecated — gone.

    A route that mints a signed URL for a private recording behind nothing but "is
    logged in" has no safe configuration, so there is nothing here to tighten. The
    project-scoped path in the sound-necklace module replaces it.
    """
    from app.main import app

    leaking = [path for path in app.openapi()["paths"] if path.startswith(RETIRED_PREFIX)]

    assert not leaking, f"the acousteme HTTP surface is back: {leaking}"


def test_the_service_beneath_it_survives():
    """Retiring the door must not take the room with it.

    ``store_artifact`` is how the corpus is ingested (``scripts/import_ruth_acoustemes``)
    and ``get_audio_url`` / ``list_by_collection`` are how the Sound Necklace reaches the
    same bytes through a gate. Deleting them would break both.
    """
    from app.services.oral_collector import acousteme_service

    for survivor in ("store_artifact", "get_artifact", "get_audio_url", "list_by_collection"):
        assert hasattr(acousteme_service, survivor), f"{survivor} was taken down with the routes"
