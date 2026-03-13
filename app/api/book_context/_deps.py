from app.core.access_control import require_app_access

MM_APP_KEY = "meaning-map-generator"
mm_access = require_app_access(MM_APP_KEY)
