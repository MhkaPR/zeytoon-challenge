"""Signal wiring for the companies module."""

from django.contrib.auth import get_user_model
from django.db.models.signals import post_delete
from django.dispatch import receiver

User = get_user_model()


@receiver(post_delete, sender=User)
def _archive_companies_on_user_delete(sender, instance, **kwargs):
    """Archiving hook for account deletion (FR-038).

    Companies are archived, never hard-deleted; with ``on_delete=PROTECT`` the actual delete
    of the user is blocked while companies exist, so this receiver exists to make the
    archival path explicit and testable rather than to perform the delete.
    """
    from apps.companies.services import archive_companies_for_user

    archive_companies_for_user(instance)
