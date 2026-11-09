from django.db import migrations


def strip_other_values(apps, schema_editor):
    PublishedRecord = apps.get_model("catalog", "PublishedRecord")
    for record in PublishedRecord._base_manager.all().iterator():
        values = record.values or {}
        if "other" not in values:
            continue
        values = {key: value for key, value in values.items() if key != "other"}
        record.values = values
        record.save(update_fields=["values"])


class Migration(migrations.Migration):

    dependencies = [
        ("catalog", "0003_remove_publishedrecord_uniq_published_record_source_site_key_and_more"),
    ]

    operations = [
        migrations.RunPython(strip_other_values, migrations.RunPython.noop),
    ]
