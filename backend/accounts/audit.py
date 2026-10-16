from .models import AuditLog


def record_audit_log(*, user, action, entity, entity_id):
    return AuditLog.objects.create(
        user=user,
        action=action,
        entity=entity,
        entity_id=str(entity_id),
    )