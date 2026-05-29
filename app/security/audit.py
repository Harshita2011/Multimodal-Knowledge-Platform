import logging
from typing import Any

logger = logging.getLogger("security_audit")


def audit(event: str, **attrs: Any) -> None:
    safe = {k: v for k, v in attrs.items() if k not in {"password", "token", "client_secret", "refresh_token"}}
    logger.info("audit", extra={"event": event, "audit": safe})
