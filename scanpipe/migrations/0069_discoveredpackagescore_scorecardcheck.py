# Generated by Django 5.1.1 on 2024-11-01 22:58

import django.db.models.deletion
import uuid
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('scanpipe', '0068_rename_discovered_dependencies_attribute'),
    ]

    operations = [
        migrations.CreateModel(
            name='DiscoveredPackageScore',
            fields=[
                ('scoring_tool', models.CharField(blank=True, choices=[('ossf-scorecard', 'Ossf'), ('others', 'Others')], help_text='Defines the source of a score or any other scoring metricsFor example: ossf-scorecard for scorecard data', max_length=100)),
                ('scoring_tool_version', models.CharField(blank=True, help_text='Defines the version of the scoring tool used for scanning thepackageFor Eg : 4.6 current version of OSSF - scorecard', max_length=50)),
                ('score', models.CharField(blank=True, help_text='Score of the package which is scanned', max_length=50)),
                ('scoring_tool_documentation_url', models.CharField(blank=True, help_text='Documentation URL of the scoring tool used', max_length=100)),
                ('score_date', models.DateTimeField(blank=True, editable=False, help_text='Date when the scoring was calculated on the package', null=True)),
                ('uuid', models.UUIDField(db_index=True, default=uuid.uuid4, editable=False, primary_key=True, serialize=False, verbose_name='UUID')),
                ('discovered_package', models.ForeignKey(blank=True, editable=False, help_text='The package for which the score is given', null=True, on_delete=django.db.models.deletion.CASCADE, related_name='discovered_packages_score', to='scanpipe.discoveredpackage')),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='ScorecardCheck',
            fields=[
                ('check_name', models.CharField(blank=True, help_text='Defines the name of check corresponding to the OSSF scoreFor example: Code-Review or CII-Best-PracticesThese are the some of the checks which are performed on a scanned package', max_length=100)),
                ('check_score', models.CharField(blank=True, help_text='Defines the score of the check for the package scannedFor Eg : 9 is a score given for Code-Review', max_length=50)),
                ('reason', models.CharField(blank=True, help_text='Gives a reason why a score was given for a specific checkFor eg, : Found 9/10 approved changesets -- score normalized to 9', max_length=300)),
                ('details', models.JSONField(blank=True, default=list, help_text='A list of details/errors regarding the score')),
                ('uuid', models.UUIDField(db_index=True, default=uuid.uuid4, editable=False, primary_key=True, serialize=False, verbose_name='UUID')),
                ('for_package_score', models.ForeignKey(blank=True, editable=False, help_text='The checks for which the score is given', null=True, on_delete=django.db.models.deletion.CASCADE, related_name='discovered_packages_score_checks', to='scanpipe.discoveredpackagescore')),
            ],
            options={
                'abstract': False,
            },
        ),
    ]