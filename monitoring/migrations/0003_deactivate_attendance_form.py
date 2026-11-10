from django.db import migrations


def deactivate_attendance_form(apps, schema_editor):
    MonitoringForm = apps.get_model('monitoring', 'MonitoringForm')
    MonitoringForm.objects.filter(name__in=['Attendance List', 'Field Visit Attendance Sheet']).update(is_active=False)


class Migration(migrations.Migration):
    dependencies = [('monitoring', '0002_alter_monitoringform_category')]
    operations = [migrations.RunPython(deactivate_attendance_form, migrations.RunPython.noop)]
