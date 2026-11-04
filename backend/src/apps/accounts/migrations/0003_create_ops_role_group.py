"""Create the operational role groups (regular, ops, admin).

Groups previously only existed after calling ``ensure_role_groups`` from tests or a shell.
Creating them in a migration makes ``ops`` assignable in every environment, including the
existing development database.
"""

from django.db import migrations

GROUPS = ("regular", "ops", "admin")


def create_groups(apps, schema_editor):
    Group = apps.get_model("auth", "Group")
    for name in GROUPS:
        Group.objects.get_or_create(name=name)


def noop(apps, schema_editor):
    """Keep existing groups on rollback; deleting them would drop user assignments."""


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0002_unusable_password_for_otp_users"),
        ("auth", "0012_alter_user_first_name_max_length"),
    ]

    operations = [migrations.RunPython(create_groups, noop)]
