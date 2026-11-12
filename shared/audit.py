"""Append-only trail of management actions."""

import json

from flask import g

from shared.web import client_ip


def record_audit(db, action, entity, entity_id=None, details=None):
    """Write inside the caller's transaction so an action and its trail commit together."""
    user = getattr(g, "user", None) or {}
    db.execute(
        "INSERT INTO audit_log(actor_user_id,actor_username,action,entity,entity_id,details,client_ip) "
        "VALUES (?,?,?,?,?,?,?)",
        (
            user.get("user_id"),
            user.get("username"),
            action,
            entity,
            None if entity_id is None else str(entity_id),
            json.dumps(details or {}, ensure_ascii=False),
            client_ip(),
        ),
    )
