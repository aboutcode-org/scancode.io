# Generated manually for origin curation feature

import django.db.models.deletion
import uuid
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('scanpipe', '0076_discoveredpackagescore_scorecardcheck_and_more'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        # Add curation fields to CodebaseRelation
        migrations.AddField(
            model_name='codebaserelation',
            name='curation_status',
            field=models.CharField(
                blank=True,
                choices=[
                    ('pending', 'Pending'),
                    ('approved', 'Approved'),
                    ('rejected', 'Rejected'),
                ],
                help_text='Curation status for this relation.',
                max_length=20,
                null=True,
            ),
        ),
        migrations.AddField(
            model_name='codebaserelation',
            name='curated_by',
            field=models.ForeignKey(
                blank=True,
                help_text='User who curated this relation.',
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='curated_relations',
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddField(
            model_name='codebaserelation',
            name='curated_at',
            field=models.DateTimeField(
                blank=True,
                help_text='Timestamp when this relation was curated.',
                null=True,
            ),
        ),
        migrations.AddField(
            model_name='codebaserelation',
            name='curation_notes',
            field=models.TextField(
                blank=True,
                help_text='Notes or comments about the curation.',
            ),
        ),
        migrations.AddField(
            model_name='codebaserelation',
            name='confidence_level',
            field=models.CharField(
                blank=True,
                choices=[
                    ('low', 'Low'),
                    ('medium', 'Medium'),
                    ('high', 'High'),
                    ('verified', 'Verified'),
                ],
                help_text='Confidence level for this origin determination.',
                max_length=20,
            ),
        ),
        # Create OriginCuration model
        migrations.CreateModel(
            name='OriginCuration',
            fields=[
                (
                    'uuid',
                    models.UUIDField(
                        db_index=True,
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                        verbose_name='UUID',
                    ),
                ),
                (
                    'created_date',
                    models.DateTimeField(
                        auto_now_add=True,
                        help_text='When this curation was created.',
                    ),
                ),
                (
                    'notes',
                    models.TextField(
                        blank=True,
                        help_text='Notes or comments about this curation action.',
                    ),
                ),
                (
                    'curation_status',
                    models.CharField(
                        choices=[
                            ('pending', 'Pending'),
                            ('approved', 'Approved'),
                            ('rejected', 'Rejected'),
                        ],
                        help_text='Curation status set by this action.',
                        max_length=20,
                    ),
                ),
                (
                    'confidence_level',
                    models.CharField(
                        blank=True,
                        choices=[
                            ('low', 'Low'),
                            ('medium', 'Medium'),
                            ('high', 'High'),
                            ('verified', 'Verified'),
                        ],
                        help_text='Confidence level set by this action.',
                        max_length=20,
                    ),
                ),
                (
                    'previous_map_type',
                    models.CharField(
                        blank=True,
                        help_text='Previous map_type value (for tracking changes).',
                        max_length=30,
                    ),
                ),
                (
                    'curator',
                    models.ForeignKey(
                        help_text='User who performed this curation.',
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name='origin_curations',
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    'previous_from_resource',
                    models.ForeignKey(
                        blank=True,
                        help_text='Previous from_resource value (for tracking changes).',
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name='previous_from_curations',
                        to='scanpipe.codebaseresource',
                    ),
                ),
                (
                    'previous_to_resource',
                    models.ForeignKey(
                        blank=True,
                        help_text='Previous to_resource value (for tracking changes).',
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name='previous_to_curations',
                        to='scanpipe.codebaseresource',
                    ),
                ),
                (
                    'project',
                    models.ForeignKey(
                        editable=False,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='origincurations',
                        to='scanpipe.project',
                    ),
                ),
                (
                    'relation',
                    models.ForeignKey(
                        help_text='The relation being curated.',
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='curations',
                        to='scanpipe.codebaserelation',
                    ),
                ),
            ],
            options={
                'ordering': ['-created_date'],
            },
        ),
        # Add indexes
        migrations.AddIndex(
            model_name='origincuration',
            index=models.Index(
                fields=['relation', '-created_date'],
                name='scanpipe_or_relation_created_idx',
            ),
        ),
        migrations.AddIndex(
            model_name='origincuration',
            index=models.Index(
                fields=['curator', '-created_date'],
                name='scanpipe_or_curator_created_idx',
            ),
        ),
        # Create PropagationBatch model
        migrations.CreateModel(
            name='PropagationBatch',
            fields=[
                (
                    'uuid',
                    models.UUIDField(
                        db_index=True,
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                        verbose_name='UUID',
                    ),
                ),
                (
                    'strategy',
                    models.CharField(
                        help_text='Propagation strategy used (similar, directory, package, pattern).',
                        max_length=50,
                    ),
                ),
                (
                    'created_date',
                    models.DateTimeField(
                        auto_now_add=True,
                        help_text='When this propagation was created.',
                    ),
                ),
                (
                    'relation_count',
                    models.IntegerField(
                        default=0,
                        help_text='Number of relations created in this batch.',
                    ),
                ),
                (
                    'extra_data',
                    models.JSONField(
                        blank=True,
                        default=dict,
                        help_text='Additional data about the propagation (pattern, threshold, etc.).',
                    ),
                ),
                (
                    'created_by',
                    models.ForeignKey(
                        help_text='User who performed this propagation.',
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name='propagation_batches',
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    'project',
                    models.ForeignKey(
                        editable=False,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='propagationbatches',
                        to='scanpipe.project',
                    ),
                ),
                (
                    'source_relation',
                    models.ForeignKey(
                        help_text='The source relation that was propagated.',
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='propagation_batches',
                        to='scanpipe.codebaserelation',
                    ),
                ),
            ],
            options={
                'ordering': ['-created_date'],
            },
        ),
        migrations.AddIndex(
            model_name='propagationbatch',
            index=models.Index(
                fields=['source_relation', '-created_date'],
                name='scanpipe_pr_source_r_created_idx',
            ),
        ),
        migrations.AddIndex(
            model_name='propagationbatch',
            index=models.Index(
                fields=['created_by', '-created_date'],
                name='scanpipe_pr_created__created_idx',
            ),
        ),
    ]

