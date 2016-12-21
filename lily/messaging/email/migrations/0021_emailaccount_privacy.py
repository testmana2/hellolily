# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('email', '0020_truncate_noemailmessageid_table'),
    ]

    operations = [
        migrations.AddField(
            model_name='emailaccount',
            name='privacy',
            field=models.IntegerField(default=1, choices=[(0, 'Public'), (1, 'Read only'), (2, 'Metadata only'), (3, 'Private')]),
            preserve_default=True,
        ),
    ]
