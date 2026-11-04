from django.db import migrations


def add_missing_link_fields(apps, schema_editor):
    link_model = apps.get_model("pipeline", "Link")
    table_name = link_model._meta.db_table
    with schema_editor.connection.cursor() as cursor:
        existing_columns = {
            column.name
            for column in schema_editor.connection.introspection.get_table_description(
                cursor, table_name
            )
        }

    for field_name in (
        "refilter_plan_type",
        "refilter_confidence",
        "refilter_flag",
        "retry_count",
        "last_error",
    ):
        field = link_model._meta.get_field(field_name)
        if field.column not in existing_columns:
            schema_editor.add_field(link_model, field)


class Migration(migrations.Migration):
    dependencies = [
        ("pipeline", "0002_sync_site_crawl_query"),
    ]

    operations = [
        migrations.RunPython(add_missing_link_fields, migrations.RunPython.noop),
    ]
