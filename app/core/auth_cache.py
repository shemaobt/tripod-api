"""In-memory TTL cache for auth lookups (user-by-id, roles-by-user).

Eliminates repeated DB round-trips to remote Neon on every authenticated
request.  Cache entries expire after 5 minutes; mutations (role assign /
revoke) explicitly invalidate the relevant keys.
"""

from cachetools import TTLCache

_user_cache: TTLCache = TTLCache(maxsize=256, ttl=300)
_roles_cache: TTLCache = TTLCache(maxsize=512, ttl=300)


# -- User cache -------------------------------------------------------------


def get_cached_user(user_id: str):
    return _user_cache.get(user_id)


def set_cached_user(user_id: str, user) -> None:
    _user_cache[user_id] = user


def invalidate_user(user_id: str) -> None:
    _user_cache.pop(user_id, None)


# -- Roles cache ------------------------------------------------------------


def _roles_key(user_id: str, app_key: str | None) -> str:
    return f"{user_id}:{app_key or '*'}"


def get_cached_roles(user_id: str, app_key: str | None) -> list | None:
    return _roles_cache.get(_roles_key(user_id, app_key))


def set_cached_roles(user_id: str, app_key: str | None, roles: list) -> None:
    _roles_cache[_roles_key(user_id, app_key)] = roles


def invalidate_roles(user_id: str) -> None:
    keys_to_remove = [k for k in _roles_cache if k.startswith(f"{user_id}:")]
    for k in keys_to_remove:
        _roles_cache.pop(k, None)
