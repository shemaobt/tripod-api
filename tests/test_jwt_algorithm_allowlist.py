"""Guard: token decoding pins an explicit algorithm allowlist, so a token signed
with any other algorithm is rejected (no algorithm confusion).

This guards the allowlist, not a CVE — the python-jose >= 3.5.0 bump is what
carries the CVE-2024-33663/33664 fixes.
"""

from __future__ import annotations

import pytest
from jose import jwt

from app.core.config import get_settings
from app.core.exceptions import InvalidTokenError
from app.utils.jwt import decode_token


def test_decode_rejects_algorithm_outside_the_allowlist():
    settings = get_settings()
    allowed = settings.jwt_algorithm
    other = "HS512" if allowed != "HS512" else "HS384"
    forged = jwt.encode({"sub": "u", "type": "access"}, settings.jwt_secret_key, algorithm=other)
    with pytest.raises(InvalidTokenError):
        decode_token(forged)
