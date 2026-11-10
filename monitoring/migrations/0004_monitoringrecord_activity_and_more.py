from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [('core', '0001_initial'), ('monitoring', '0003_deactivate_attendance_form')]
    operations = [
        migrations.AddField(
            model_name='monitoringrecord',
            name='activity',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='monitoring_records', to='core.activity'),
        ),
        migrations.AddField(
            model_name='monitoringrecord',
            name='project',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='monitoring_records', to='core.project'),
        ),
    ]
