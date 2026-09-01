"""Pure authorization policy for already validated requests."""

from .models import Action, AuthorizationRequest, Decision, Role


def authorize(request: AuthorizationRequest) -> Decision:
    """Return the deterministic decision for one validated request."""

    principal = request.principal
    resource = request.resource

    if principal.tenant_id != resource.tenant_id:
        return Decision(False, "deny_cross_tenant")

    if principal.role is Role.ADMIN:
        return Decision(True, "allow_admin")

    if principal.role is Role.AUDITOR:
        if request.action is Action.READ:
            return Decision(True, "allow_auditor_read")
        return Decision(False, "deny_insufficient_privilege")

    if principal.role is Role.MEMBER:
        is_owner = principal.subject_id == resource.owner_id
        if is_owner and request.action in (Action.READ, Action.WRITE):
            return Decision(True, "allow_owner")

    return Decision(False, "deny_insufficient_privilege")
