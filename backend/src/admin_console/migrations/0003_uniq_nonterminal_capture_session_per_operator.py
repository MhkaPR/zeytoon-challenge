"""One active capture per operator at a time.

An operator cannot record two links concurrently: the second capture would open a second
Chrome window and both trace files would be hard to attribute. The constraint makes the
rule race-free; the API maps the violation to ``409 capture_in_progress``.
"""

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        (
            "admin_console",
            "0002_capturesession_uniq_nonterminal_capture_session_per_link",
        ),
    ]

    operations = [
        migrations.AddConstraint(
            model_name="capturesession",
            constraint=models.UniqueConstraint(
                condition=models.Q(
                    state__in=("pending", "recording", "awaiting_upload")
                ),
                fields=("operator",),
                name="uniq_nonterminal_capture_session_per_operator",
            ),
        ),
    ]
