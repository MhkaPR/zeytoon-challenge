from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("pipeline", "0006_link_pipeline_task_state")]

    operations = [
        migrations.AddField(
            model_name="llmcostledger",
            name="links",
            field=models.ManyToManyField(
                blank=True,
                related_name="batch_llm_spend_rows",
                to="pipeline.link",
            ),
        ),
    ]
