import logging

audit_logger = logging.getLogger("audit")

WARNING_EVENT_TYPES = frozenset({
    "auth.login.failure",
    "auth.login.locked",
    "authz.access.denied",
})


def emit_audit_event(request, event_type: str, detail: dict | None = None) -> None:
    """
    Emit a structured NIS2 audit log entry.

    Extracts user, IP, session_id, path, and method from request.
    Logs at WARNING for failure/denial events, INFO for everything else.
    """
    level = logging.WARNING if event_type in WARNING_EVENT_TYPES else logging.INFO

    if request is not None:
        user = request.user.username if request.user.is_authenticated else "anonymous"
        x_fwd = request.META.get("HTTP_X_FORWARDED_FOR", "")
        ip = x_fwd.split(",")[0].strip() if x_fwd else request.META.get("REMOTE_ADDR", "")
        session_id = getattr(request.session, "session_key", None)
        path = request.path
        method = request.method
    else:
        user = "system"
        ip = None
        session_id = None
        path = None
        method = None

    audit_logger.log(
        level,
        event_type,
        extra={
            "event_type": event_type,
            "user": user,
            "ip": ip,
            "session_id": session_id,
            "path": path,
            "method": method,
            "detail": detail or {},
        },
    )
