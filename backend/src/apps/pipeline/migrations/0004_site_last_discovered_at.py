from django.db import migrations, models
from django.utils import timezone


def mark_existing_sites_discovered(apps, schema_editor):
    Site = apps.get_model("pipeline", "Site")
    Link = apps.get_model("pipeline", "Link")
    alias = schema_editor.connection.alias
    site_ids = (
        Link.objects.using(alias)
        .filter(source="adaptive_crawl")
        .values_list("site_id", flat=True)
        .distinct()
    )
    for site in Site.objects.using(alias).filter(pk__in=site_ids).iterator():
        site.last_discovered_at = site.onboarded_at or site.created_at or timezone.now()
        site.save(update_fields=["last_discovered_at"], using=alias)


class Migration(migrations.Migration):
    dependencies = [("pipeline", "0003_sync_legacy_link_fields")]

    operations = [
        migrations.AddField(
            model_name="site",
            name="last_discovered_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.RunPython(mark_existing_sites_discovered, migrations.RunPython.noop),
    ]
