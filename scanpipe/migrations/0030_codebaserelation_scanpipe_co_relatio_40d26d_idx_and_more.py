# Generated by Django 4.2 on 2023-04-19 07:26

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("scanpipe", "0029_alter_projecterror_details"),
    ]

    operations = [
        migrations.AddIndex(
            model_name="codebaserelation",
            index=models.Index(
                fields=["relationship"], name="scanpipe_co_relatio_40d26d_idx"
            ),
        ),
        migrations.AddIndex(
            model_name="codebaserelation",
            index=models.Index(
                fields=["match_type"], name="scanpipe_co_match_t_62bd20_idx"
            ),
        ),
    ]