# Generated migration for origin propagation fields

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("scanpipe", "0001_add_origin_determination"),
    ]

    operations = [
        migrations.AddField(
            model_name="codeorigindetermination",
            name="is_propagated",
            field=models.BooleanField(
                default=False,
                help_text="Whether this origin was propagated from another file",
            ),
        ),
        migrations.AddField(
            model_name="codeorigindetermination",
            name="propagation_source",
            field=models.ForeignKey(
                blank=True,
                help_text="The origin determination this was propagated from",
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="propagated_to",
                to="scanpipe.codeorigindetermination",
            ),
        ),
        migrations.AddField(
            model_name="codeorigindetermination",
            name="propagation_method",
            field=models.CharField(
                blank=True,
                help_text="Method used for propagation (e.g., path_pattern, package_membership, license_similarity)",
                max_length=100,
            ),
        ),
        migrations.AddField(
            model_name="codeorigindetermination",
            name="propagation_confidence",
            field=models.FloatField(
                blank=True,
                help_text="Confidence score for the propagation (0.0 to 1.0)",
                null=True,
            ),
        ),
        migrations.AddField(
            model_name="codeorigindetermination",
            name="propagation_metadata",
            field=models.JSONField(
                blank=True,
                default=dict,
                help_text="Additional metadata about the propagation",
            ),
        ),
        migrations.AddIndex(
            model_name="codeorigindetermination",
            index=models.Index(
                fields=["is_propagated"], name="scanpipe_co_is_prop_idx"
            ),
        ),
        migrations.AddIndex(
            model_name="codeorigindetermination",
            index=models.Index(
                fields=["propagation_method"], name="scanpipe_co_propaga_idx"
            ),
        ),
    ]
