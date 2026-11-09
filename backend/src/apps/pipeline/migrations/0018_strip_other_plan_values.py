from django.db import migrations


def strip_other_values(apps, schema_editor):
    PlanRecord = apps.get_model("pipeline", "PlanRecord")
    for record in PlanRecord._base_manager.all().iterator():
        values = record.values or {}
        if "other" not in values:
            continue
        values = {key: value for key, value in values.items() if key != "other"}
        record.values = values
        record.save(update_fields=["values"])


class Migration(migrations.Migration):

    dependencies = [
        ("pipeline", "0017_tableclassification_confidence_and_more"),
    ]

    operations = [
        migrations.RunPython(strip_other_values, migrations.RunPython.noop),
    ]
