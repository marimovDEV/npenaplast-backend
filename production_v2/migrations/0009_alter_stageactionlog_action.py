from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('production_v2', '0008_bunker_is_occupied_bunker_last_occupied_at_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='stageactionlog',
            name='action',
            field=models.CharField(
                choices=[
                    ('START', 'Boshlash'),
                    ('FINISH', 'Yakunlash'),
                    ('FAIL', 'Xatolik'),
                    ('PAUSE', 'To‘xtatish'),
                    ('RESUME', 'Davom ettirish'),
                    ('RESET', 'Qayta tiklash'),
                ],
                max_length=20,
            ),
        ),
    ]
