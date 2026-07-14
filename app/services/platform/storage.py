"""Bucket genérico da plataforma — não pertence a nenhum app.

**Só do servidor.** Nenhum navegador toca neste bucket: a API lê os bytes e os transmite.
Por isso, ao contrário de `annotation_studio/storage.py` e do oral-collector, aqui não há
URL assinada, nem CORS, nem acesso público — só existir e a service account poder ler e
escrever.

O nome do bucket vem das Settings (`GCS_PLATFORM_BUCKET`), não de uma constante cravada no
módulo como fazem `storage/upload.py` e `annotation_studio/constants.py`.
"""

from __future__ import annotations

import asyncio

from app.core.config import Settings, get_settings
from app.core.exceptions import ValidationError

_gcs_client = None


def _client():  # type: ignore[no-untyped-def]
    from google.cloud import storage

    global _gcs_client
    if _gcs_client is None:
        _gcs_client = storage.Client()
    return _gcs_client


def _blob(key: str, settings: Settings):  # type: ignore[no-untyped-def]
    if not settings.gcs_platform_bucket:
        raise ValidationError("GCS_PLATFORM_BUCKET is not configured")
    return _client().bucket(settings.gcs_platform_bucket).blob(key)


class GcsPlatformStore:
    """Leitura/escrita de objetos opacos no bucket da plataforma."""

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()

    async def get(self, key: str) -> bytes | None:
        """Os bytes do objeto, ou `None` se ele não existe."""
        return await asyncio.to_thread(self._get_sync, key)

    async def put(self, key: str, data: bytes, content_type: str) -> None:
        """Grava o objeto (sobrescreve)."""
        await asyncio.to_thread(self._put_sync, key, data, content_type)

    def _get_sync(self, key: str) -> bytes | None:
        # `exists()` + download custa duas idas ao GCS; pegar `NotFound` custaria uma. Mas
        # `from google.cloud.exceptions import NotFound` importa de um pacote TIPADO
        # (google-cloud-core), o que faz o mypy "acordar" o namespace `google.cloud` — e aí
        # o `ignore_missing_imports` do pyproject deixa de mascarar os cinco
        # `from google.cloud import storage` que já existem no repo, e o build quebra em
        # arquivos que não têm nada a ver com este. Duas idas é o preço de não pisar nessa mina.
        blob = _blob(key, self._settings)
        if not blob.exists():
            return None
        return bytes(blob.download_as_bytes())

    def _put_sync(self, key: str, data: bytes, content_type: str) -> None:
        _blob(key, self._settings).upload_from_string(data, content_type=content_type)
