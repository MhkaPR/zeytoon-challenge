import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("admin_console", "0004_site_last_discovered_at")]

    operations = [
        migrations.CreateModel(
            name="PlanExclusion",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("fingerprint", models.CharField(max_length=64)),
                ("plan_type", models.CharField(max_length=64)),
                ("plan_name", models.CharField(max_length=255)),
                ("price_amount", models.CharField(max_length=64)),
                (
                    "link",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="plan_exclusions",
                        to="admin_console.link",
                    ),
                ),
            ],
            options={"db_table": "admin_console_plan_exclusion"},
        ),
        migrations.AddConstraint(
            model_name="planexclusion",
            constraint=models.UniqueConstraint(
                fields=("link", "fingerprint"),
                name="uniq_plan_exclusion_link_fingerprint",
            ),
        ),
    ]
