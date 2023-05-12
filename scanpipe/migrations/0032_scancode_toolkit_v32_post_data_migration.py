# Generated by Django 4.2 on 2023-05-08 09:08

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("scanpipe", "0031_scancode_toolkit_v32_data_updates"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="discoveredpackage",
            name="contains_source_code",
        ),
        migrations.RemoveField(
            model_name="discoveredpackage",
            name="manifest_path",
        ),
        migrations.RemoveField(
            model_name="codebaseresource",
            name="license_expressions",
        ),
        migrations.RemoveField(
            model_name="codebaseresource",
            name="licenses",
        ),
        migrations.AddIndex(
            model_name="discoveredpackage",
            index=models.Index(
                fields=["declared_license_expression"],
                name="scanpipe_di_declare_4b8499_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="discoveredpackage",
            index=models.Index(
                fields=["other_license_expression"],
                name="scanpipe_di_other_l_1f1616_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="codebaseresource",
            index=models.Index(
                fields=["detected_license_expression"],
                name="scanpipe_co_detecte_f3f97d_idx",
            ),
        ),
    ]