from django.db import migrations, models
from django.utils import timezone


def populate_staff_ids(apps, schema_editor):
    StaffProfile = apps.get_model("account", "StaffProfile")
    year = timezone.localdate().strftime("%y")
    for profile in StaffProfile.objects.select_related("user").all():
        profile.staff_id = f"APED-{year}-{profile.user_id:04d}"
        profile.save(update_fields=["staff_id"])


class Migration(migrations.Migration):
    dependencies = [("account", "0001_initial")]
    operations = [
        migrations.AddField(
            model_name="staffprofile",
            name="staff_id",
            field=models.CharField(blank=True, editable=False, max_length=20, unique=True),
        ),
        migrations.RunPython(populate_staff_ids, migrations.RunPython.noop),
    ]
