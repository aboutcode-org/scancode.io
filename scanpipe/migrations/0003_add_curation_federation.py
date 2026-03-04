# Generated migration for FederatedCode curation integration

from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ('scanpipe', '0002_add_origin_propagation'),
    ]

    operations = [
        migrations.CreateModel(
            name='CurationSource',
            fields=[
                ('uuid', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False, verbose_name='UUID')),
                ('name', models.CharField(help_text='Human-readable name for this curation source', max_length=255, unique=True)),
                ('source_type', models.CharField(choices=[('federatedcode_git', 'FederatedCode Git Repository'), ('scancodeio_api', 'ScanCode.io API'), ('community_service', 'Community Curation Service'), ('manual_import', 'Manual Import'), ('local', 'Local (This Instance)')], help_text='Type of curation source', max_length=50)),
                ('url', models.URLField(blank=True, help_text='URL to the curation source (Git repo, API endpoint, etc.)', max_length=1024)),
                ('api_key', models.CharField(blank=True, help_text='API key or authentication token for accessing this source', max_length=512)),
                ('priority', models.IntegerField(default=50, help_text='Priority for conflict resolution (higher = preferred). Range: 0-100. Local/manual sources typically have higher priority.')),
                ('is_active', models.BooleanField(default=True, help_text='Whether this source is currently active for imports')),
                ('auto_sync', models.BooleanField(default=False, help_text='Automatically sync curations from this source periodically')),
                ('sync_frequency_hours', models.IntegerField(default=24, help_text='How often to sync curations (in hours) if auto_sync is enabled')),
                ('last_sync_date', models.DateTimeField(blank=True, help_text='Last time curations were synced from this source', null=True)),
                ('sync_statistics', models.JSONField(blank=True, default=dict, help_text='Statistics from the last sync (imported, conflicts, errors)')),
                ('metadata', models.JSONField(blank=True, default=dict, help_text='Additional metadata about this source (maintainer, license, etc.)')),
                ('created_date', models.DateTimeField(auto_now_add=True)),
                ('updated_date', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name': 'Curation Source',
                'verbose_name_plural': 'Curation Sources',
                'ordering': ['-priority', 'name'],
            },
        ),
        migrations.CreateModel(
            name='CurationProvenance',
            fields=[
                ('uuid', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False, verbose_name='UUID')),
                ('action_type', models.CharField(choices=[('created', 'Created'), ('amended', 'Amended'), ('verified', 'Verified'), ('imported', 'Imported'), ('merged', 'Merged'), ('propagated', 'Propagated'), ('rejected', 'Rejected')], help_text='Type of action that created this provenance record', max_length=50)),
                ('actor_name', models.CharField(blank=True, help_text='Name of the person/system that performed the action', max_length=255)),
                ('actor_email', models.EmailField(blank=True, help_text='Email of the person who performed the action', max_length=254)),
                ('action_date', models.DateTimeField(default=django.utils.timezone.now, help_text='When this action was performed')),
                ('previous_value', models.JSONField(blank=True, default=dict, help_text='Previous values before this action (for amendments/merges)')),
                ('new_value', models.JSONField(blank=True, default=dict, help_text='New values after this action')),
                ('notes', models.TextField(blank=True, help_text='Additional notes about this provenance record')),
                ('metadata', models.JSONField(blank=True, default=dict, help_text='Additional metadata (tool version, confidence, etc.)')),
                ('created_date', models.DateTimeField(auto_now_add=True)),
                ('curation_source', models.ForeignKey(blank=True, help_text='The source where this curation came from (if imported)', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='curation_provenances', to='scanpipe.curationsource')),
                ('origin_determination', models.ForeignKey(help_text='The origin determination this provenance is for', on_delete=django.db.models.deletion.CASCADE, related_name='provenance_records', to='scanpipe.codeorigindetermination')),
            ],
            options={
                'verbose_name': 'Curation Provenance',
                'verbose_name_plural': 'Curation Provenances',
                'ordering': ['-action_date'],
            },
        ),
        migrations.CreateModel(
            name='CurationConflict',
            fields=[
                ('uuid', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False, verbose_name='UUID')),
                ('resource_path', models.CharField(help_text='Path to the resource with conflicting curations', max_length=2048)),
                ('conflict_type', models.CharField(choices=[('origin_type_mismatch', 'Origin Type Mismatch'), ('origin_identifier_mismatch', 'Origin Identifier Mismatch'), ('confidence_difference', 'Significant Confidence Difference'), ('multiple_sources', 'Multiple Source Conflict'), ('manual_vs_automated', 'Manual vs Automated Conflict')], help_text='Type of conflict', max_length=50)),
                ('imported_origin_data', models.JSONField(default=dict, help_text='The imported/conflicting origin data')),
                ('resolution_status', models.CharField(choices=[('pending', 'Pending Resolution'), ('auto_resolved', 'Automatically Resolved'), ('manual_resolved', 'Manually Resolved'), ('deferred', 'Deferred for Later'), ('ignored', 'Ignored')], default='pending', help_text='Current status of conflict resolution', max_length=50)),
                ('resolution_strategy', models.CharField(blank=True, choices=[('keep_existing', 'Keep Existing'), ('use_imported', 'Use Imported'), ('merge_both', 'Merge Both'), ('highest_priority', 'Highest Priority Source'), ('highest_confidence', 'Highest Confidence'), ('manual_decision', 'Manual Decision')], help_text='Strategy used or to be used for resolution', max_length=50)),
                ('resolved_by', models.CharField(blank=True, help_text='Name of the person/system that resolved the conflict', max_length=255)),
                ('resolved_date', models.DateTimeField(blank=True, help_text='When the conflict was resolved', null=True)),
                ('resolution_notes', models.TextField(blank=True, help_text='Notes about the conflict resolution')),
                ('metadata', models.JSONField(blank=True, default=dict, help_text='Additional conflict metadata')),
                ('created_date', models.DateTimeField(auto_now_add=True)),
                ('updated_date', models.DateTimeField(auto_now=True)),
                ('existing_origin', models.ForeignKey(blank=True, help_text='The existing origin determination', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='conflicts_as_existing', to='scanpipe.codeorigindetermination')),
                ('imported_source', models.ForeignKey(blank=True, help_text='The source of the imported curation', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='conflicts', to='scanpipe.curationsource')),
                ('project', models.ForeignKey(help_text='The project this conflict belongs to', on_delete=django.db.models.deletion.CASCADE, related_name='curation_conflicts', to='scanpipe.project')),
                ('resolved_origin', models.ForeignKey(blank=True, help_text='The origin determination after conflict resolution', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='conflicts_resolved_to', to='scanpipe.codeorigindetermination')),
            ],
            options={
                'verbose_name': 'Curation Conflict',
                'verbose_name_plural': 'Curation Conflicts',
                'ordering': ['-created_date'],
            },
        ),
        migrations.CreateModel(
            name='CurationExport',
            fields=[
                ('uuid', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False, verbose_name='UUID')),
                ('destination_url', models.URLField(blank=True, help_text='URL where the exported curations can be found', max_length=1024)),
                ('export_format', models.CharField(default='json', help_text='Format of the exported curations (json, yaml, etc.)', max_length=50)),
                ('origin_count', models.IntegerField(default=0, help_text='Number of origin determinations exported')),
                ('verified_only', models.BooleanField(default=True, help_text='Whether only verified curations were exported')),
                ('include_propagated', models.BooleanField(default=False, help_text='Whether propagated origins were included in export')),
                ('status', models.CharField(choices=[('pending', 'Pending'), ('in_progress', 'In Progress'), ('completed', 'Completed'), ('failed', 'Failed')], default='pending', help_text='Status of the export operation', max_length=50)),
                ('export_file_path', models.CharField(blank=True, help_text='Path to the exported file (if applicable)', max_length=1024)),
                ('git_commit_sha', models.CharField(blank=True, help_text='Git commit SHA if exported to a Git repository', max_length=64)),
                ('error_message', models.TextField(blank=True, help_text='Error message if export failed')),
                ('metadata', models.JSONField(blank=True, default=dict, help_text='Additional export metadata')),
                ('created_by', models.CharField(blank=True, help_text='User who initiated the export', max_length=255)),
                ('created_date', models.DateTimeField(auto_now_add=True)),
                ('completed_date', models.DateTimeField(blank=True, help_text='When the export completed', null=True)),
                ('destination_source', models.ForeignKey(blank=True, help_text='The destination source where curations were exported', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='exports', to='scanpipe.curationsource')),
                ('project', models.ForeignKey(help_text='The project whose curations were exported', on_delete=django.db.models.deletion.CASCADE, related_name='curation_exports', to='scanpipe.project')),
            ],
            options={
                'verbose_name': 'Curation Export',
                'verbose_name_plural': 'Curation Exports',
                'ordering': ['-created_date'],
            },
        ),
        migrations.AddIndex(
            model_name='curationsource',
            index=models.Index(fields=['source_type'], name='scanpipe_cu_source__9e8ea9_idx'),
        ),
        migrations.AddIndex(
            model_name='curationsource',
            index=models.Index(fields=['is_active'], name='scanpipe_cu_is_acti_4d7c0e_idx'),
        ),
        migrations.AddIndex(
            model_name='curationsource',
            index=models.Index(fields=['priority'], name='scanpipe_cu_priorit_f9ba82_idx'),
        ),
        migrations.AddIndex(
            model_name='curationprovenance',
            index=models.Index(fields=['origin_determination', '-action_date'], name='scanpipe_cu_origin__5f8d2a_idx'),
        ),
        migrations.AddIndex(
            model_name='curationprovenance',
            index=models.Index(fields=['action_type'], name='scanpipe_cu_action__15e7b4_idx'),
        ),
        migrations.AddIndex(
            model_name='curationprovenance',
            index=models.Index(fields=['curation_source'], name='scanpipe_cu_curatio_f7de21_idx'),
        ),
        migrations.AddIndex(
            model_name='curationexport',
            index=models.Index(fields=['project', '-created_date'], name='scanpipe_cu_project_e45d90_idx'),
        ),
        migrations.AddIndex(
            model_name='curationexport',
            index=models.Index(fields=['status'], name='scanpipe_cu_status_b84cf8_idx'),
        ),
        migrations.AddIndex(
            model_name='curationconflict',
            index=models.Index(fields=['project', 'resolution_status'], name='scanpipe_cu_project_f4d8b2_idx'),
        ),
        migrations.AddIndex(
            model_name='curationconflict',
            index=models.Index(fields=['conflict_type'], name='scanpipe_cu_conflic_ba3c91_idx'),
        ),
        migrations.AddIndex(
            model_name='curationconflict',
            index=models.Index(fields=['resolution_status'], name='scanpipe_cu_resolut_5e8c72_idx'),
        ),
    ]
