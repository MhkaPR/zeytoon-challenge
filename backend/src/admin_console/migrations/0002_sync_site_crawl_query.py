from django.db import migrations


def add_crawl_query_column(apps, schema_editor):
    site_model = apps.get_model("admin_console", "Site")
    table_name = site_model._meta.db_table
    with schema_editor.connection.cursor() as cursor:
        existing_columns = {
            column.name
            for column in schema_editor.connection.introspection.get_table_description(
                cursor, table_name
            )
        }

    field = site_model._meta.get_field("crawl_query")
    if field.column not in existing_columns:
        schema_editor.add_field(site_model, field)


class Migration(migrations.Migration):
    dependencies = [
        ("admin_console", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(add_crawl_query_column, migrations.RunPython.noop),
    ]
