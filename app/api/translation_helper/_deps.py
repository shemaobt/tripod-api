from app.core.access_control import require_app_access

TH_APP_KEY = "translation-helper"
th_access = require_app_access(TH_APP_KEY)
