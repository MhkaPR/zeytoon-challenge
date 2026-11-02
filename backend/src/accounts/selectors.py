"""Read-side helpers, including the guest/role resolver."""

from django.contrib.auth import get_user_model
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import AccessToken

User = get_user_model()

GUEST = "guest"


def user_from_request(request):
    """Return the authenticated user, or ``None`` for a guest/blocked/revoked session."""
    header = request.META.get("HTTP_AUTHORIZATION", "")
    if not header.lower().startswith("bearer "):
        return None
    raw = header.split(" ", 1)[1].strip()
    try:
        token = AccessToken(raw)
    except TokenError:
        return None
    user_id = token.get("user_id")
    if not user_id:
        return None
    user = User.objects.filter(pk=user_id).first()
    if user is None or user.is_blocked or not user.is_active:
        return None
    return user


def resolve_current_user(request):
    """Return a small identity dict for the current request (guest or authenticated)."""
    from utils.logging import mask_phone

    user = user_from_request(request)
    if user is None:
        return {"authenticated": False, "role": GUEST}
    return {
        "authenticated": True,
        "role": user.role(),
        "user": {"phone": mask_phone(user.phone_number), "role": user.role()},
    }


def get_user_role(user):
    """Return the role string for a user, or ``guest`` when there is no user."""
    if user is None or not getattr(user, "is_authenticated", False):
        return GUEST
    return user.role()


def is_authenticated(request):
    return user_from_request(request) is not None
