"""User model for phone-based authentication.

Roles are Django ``Group``s (``regular`` / ``ops`` / ``admin``) managed with
django-guardian; there is no ad-hoc role column. ``ops`` operators work in the ``/ops``
console, while ``admin`` adds Django-admin access. Object-level permissions are handled by
django-guardian.
"""

from django.contrib.auth.models import AbstractUser, Group
from django.contrib.auth.models import UserManager as DjangoUserManager
from django.db import models

from apps.utils.models import DeletedObjectsManager, SoftDeleteManager, TimestampedModel


class UserManager(SoftDeleteManager, DjangoUserManager):
    """Soft-delete aware manager that keeps Django's user creation helpers."""

    def create_user(self, username, email=None, password=None, **extra_fields):
        extra_fields.pop("email", None)
        if not username:
            raise ValueError("The username must be set.")
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        user = self.model(username=username, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, username, email=None, password=None, **extra_fields):
        extra_fields.pop("email", None)
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")
        return self.create_user(username, password=password, **extra_fields)


class User(AbstractUser, TimestampedModel):
    """A person identified by phone number.

    ``username`` is retained (required by ``AbstractUser``) but the phone number is the
    user's unique identifier for login.
    """

    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        BLOCKED = "blocked", "Blocked"

    REGULAR_GROUP = "regular"
    OPS_GROUP = "ops"
    ADMIN_GROUP = "admin"

    phone_number = models.CharField(max_length=32)
    objects = UserManager()
    deleted_objects = DeletedObjectsManager()
    email = None
    status = models.CharField(
        max_length=16, choices=Status.choices, default=Status.ACTIVE
    )

    # AbstractUser already defines is_active; blocked users are refused at login.
    #
    # ``phone_number`` is a required, unique field, so it MUST be listed here: otherwise
    # ``createsuperuser`` would only collect username/password and store an empty phone,
    # which collides with the empty phone of guardian's ``AnonymousUser`` row (and with any
    # second admin). Listing it makes ``createsuperuser`` prompt for ``--phone_number``.
    REQUIRED_FIELDS = ["phone_number"]
    USERNAME_FIELD = "username"

    class Meta:
        db_table = "accounts_user"
        constraints = [
            models.UniqueConstraint(
                fields=("phone_number",),
                condition=models.Q(deleted_at__isnull=True),
                name="uniq_active_user_phone",
            )
        ]

    def __str__(self):
        return self.phone_number

    def save(self, *args, **kwargs):
        """Normalize the phone number and guarantee a non-usable password.

        OTP login never uses a password, so implicitly created users must not keep an
        empty ``password`` column -- Django treats ``""`` as a *usable* password. Calling
        ``set_unusable_password`` stores the ``!``-prefixed marker instead, so
        ``has_usable_password()`` correctly returns ``False`` (spec FR-005).
        """
        from apps.accounts.validation import normalize_phone

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

        ``admin`` wins over ``ops``, which wins over ``regular``. A user in none of the
        groups is treated as ``regular``. A Django superuser (e.g. one made with
        ``createsuperuser``) is always an admin.
        """
        if self.is_superuser:
            return self.ADMIN_GROUP
        group_names = set(self.groups.values_list("name", flat=True))
        if self.ADMIN_GROUP in group_names:
            return self.ADMIN_GROUP
        if self.OPS_GROUP in group_names:
            return self.OPS_GROUP
        return self.REGULAR_GROUP

    def is_admin(self):
        return self.role() == self.ADMIN_GROUP

    def is_operator(self):
        """Operators are the ``ops`` group plus admins (admins are a superset)."""
        return self.role() in (self.ADMIN_GROUP, self.OPS_GROUP)


def ensure_role_groups():
    """Create the ``regular``, ``ops``, and ``admin`` groups if they do not exist."""
    for name in (User.REGULAR_GROUP, User.OPS_GROUP, User.ADMIN_GROUP):
        Group.objects.get_or_create(name=name)
