from django.contrib.auth.hashers import make_password
from django.db import migrations


def backfill_unusable_passwords(apps, schema_editor):
    """Replace blank passwords with Django's unusable-password marker.

    Users created through OTP login were saved with an empty ``password`` value, which
    Django considers a *usable* password. OTP accounts have no password, so every such
    row is rewritten with the ``!``-prefixed marker.
    """
    User = apps.get_model("accounts", "User")
    User.objects.filter(password="").update(password=make_password(None))


def noop(apps, schema_editor):
    """Reversing restores nothing: a blank password is an unsafe prior state."""


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(backfill_unusable_passwords, noop),
    ]
