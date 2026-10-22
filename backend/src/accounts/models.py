"""User model for phone-based authentication.

Roles are Django ``Group``s (``regular`` / ``admin``) managed with django-guardian; there is
no ad-hoc role column. Object-level permissions are handled by django-guardian.
"""

from django.contrib.auth.models import AbstractUser, Group
from django.db import models

from utils.models import TimestampedModel


class User(AbstractUser, TimestampedModel):
    """A person identified by phone number.

    ``username`` is retained (required by ``AbstractUser``) but the phone number is the
    user's unique identifier for login.
    """

    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        BLOCKED = "blocked", "Blocked"

    REGULAR_GROUP = "regular"
    ADMIN_GROUP = "admin"

    phone_number = models.CharField(max_length=32, unique=True)
    status = models.CharField(
        max_length=16, choices=Status.choices, default=Status.ACTIVE
    )

    # AbstractUser already defines is_active; blocked users are refused at login.
    REQUIRED_FIELDS = []
    USERNAME_FIELD = "username"

    class Meta:
        db_table = "accounts_user"

    def __str__(self):
        from utils.logging import mask_phone

        return mask_phone(self.phone_number)

    def save(self, *args, **kwargs):
        """Normalize the phone number and guarantee a non-usable password.

        OTP login never uses a password, so implicitly created users must not keep an
        empty ``password`` column -- Django treats ``""`` as a *usable* password. Calling
        ``set_unusable_password`` stores the ``!``-prefixed marker instead, so
        ``has_usable_password()`` correctly returns ``False`` (spec FR-005).
        """
        from accounts.validation import normalize_phone

        if not self.password:
            self.set_unusable_password()

        normalized = normalize_phone(self.phone_number)
        if normalized:
            self.phone_number = normalized
            if not self.username:
                self.username = normalized
        super().save(*args, **kwargs)

    @property
    def is_blocked(self):
        return self.status == self.Status.BLOCKED

    def role(self):
        """Return the user's role based on group membership.

        ``admin`` wins over ``regular``; a user in neither group is treated as ``regular``.
        """
        group_names = set(self.groups.values_list("name", flat=True))
        if self.ADMIN_GROUP in group_names:
            return self.ADMIN_GROUP
        return self.REGULAR_GROUP

    def is_admin(self):
        return self.role() == self.ADMIN_GROUP


def ensure_role_groups():
    """Create the ``regular`` and ``admin`` groups if they do not exist."""
    Group.objects.get_or_create(name=User.REGULAR_GROUP)
    Group.objects.get_or_create(name=User.ADMIN_GROUP)
