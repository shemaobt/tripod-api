from app.core.access_control import require_app_access, require_role

mm_access = require_app_access("meaning-map-generator")
mm_analyst = require_role("meaning-map-generator", "analyst")
