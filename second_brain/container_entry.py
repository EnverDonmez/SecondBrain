"""Container network namespace entry point; host exposure is loopback-only in Compose."""

import uvicorn

from .api import create_app

uvicorn.run(create_app("/app/data"), host="0.0.0.0", port=8765, access_log=False)  # noqa: S104 -- container namespace; Compose restricts host exposure
