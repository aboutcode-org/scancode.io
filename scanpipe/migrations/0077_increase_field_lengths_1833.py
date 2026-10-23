# Generated manually for issue #1833
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('scanpipe', '0076_discoveredpackagescore_scorecardcheck_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='projectmessage',
            name='traceback',
            field=models.TextField(blank=True),
        ),
        migrations.AlterField(
            model_name='codebaseresource',
            name='path',
            field=models.TextField(help_text='The full path value of a resource.'),
        ),
    ]
