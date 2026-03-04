# SPDX-License-Identifier: Apache-2.0
#
# Migration for adding origin determination support

from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ('scanpipe', '0001_initial'),  # Replace with the latest migration
    ]

    operations = [
        migrations.CreateModel(
            name='CodeOriginDetermination',
            fields=[
                ('uuid', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False, verbose_name='UUID')),
                ('created_date', models.DateTimeField(auto_now_add=True)),
                ('updated_date', models.DateTimeField(auto_now=True)),
                ('detected_origin_type', models.CharField(blank=True, choices=[('package', 'Package'), ('repository', 'Repository'), ('url', 'URL'), ('unknown', 'Unknown')], help_text='Automatically detected origin type', max_length=50)),
                ('detected_origin_identifier', models.CharField(blank=True, help_text='Detected origin identifier (e.g., package URL, repository URL)', max_length=2048)),
                ('detected_origin_confidence', models.FloatField(blank=True, help_text='Confidence score (0.0 to 1.0) for the detected origin', null=True)),
                ('detected_origin_method', models.CharField(blank=True, help_text='Method used to detect origin (e.g., scancode, matchcode)', max_length=100)),
                ('detected_origin_metadata', models.JSONField(blank=True, default=dict, help_text='Additional metadata about the detected origin')),
                ('amended_origin_type', models.CharField(blank=True, choices=[('package', 'Package'), ('repository', 'Repository'), ('url', 'URL'), ('unknown', 'Unknown')], help_text='User-amended origin type', max_length=50)),
                ('amended_origin_identifier', models.CharField(blank=True, help_text='User-amended origin identifier', max_length=2048)),
                ('amended_origin_notes', models.TextField(blank=True, help_text='Notes about the amendment')),
                ('amended_by', models.CharField(blank=True, help_text='User who amended the origin', max_length=255)),
                ('is_verified', models.BooleanField(default=False, help_text='Whether the origin determination has been verified')),
                ('codebase_resource', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='origin_determination', to='scanpipe.codebaseresource')),
            ],
            options={
                'verbose_name': 'Code Origin Determination',
                'verbose_name_plural': 'Code Origin Determinations',
                'ordering': ['-updated_date'],
                'indexes': [
                    models.Index(fields=['detected_origin_type']),
                    models.Index(fields=['detected_origin_confidence']),
                    models.Index(fields=['is_verified']),
                    models.Index(fields=['amended_origin_type']),
                ],
            },
        ),
    ]
