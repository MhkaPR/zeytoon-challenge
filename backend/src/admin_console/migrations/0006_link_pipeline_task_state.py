from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("admin_console", "0005_planexclusion")]

    operations = [
        migrations.AddField(
            model_name="link",
            name="pipeline_task_state",
            field=models.CharField(db_index=True, default="idle", max_length=16),
        ),
    ]
