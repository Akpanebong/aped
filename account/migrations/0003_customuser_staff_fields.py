from django.db import migrations, models


def copy_staff_profiles(apps, schema_editor):
    StaffProfile = apps.get_model("account", "StaffProfile")
    LegacyStaffProfile = apps.get_model("account", "LegacyStaffProfile")

    profile_fields = ["staff_id", "role", "job_title", "department", "phone", "location"]
    for profile in LegacyStaffProfile.objects.all():
        try:
            user = StaffProfile.objects.get(pk=profile.user_id)
        except StaffProfile.DoesNotExist:
            continue
        for field in profile_fields:
            setattr(user, field, getattr(profile, field))
        user.save(update_fields=profile_fields)

    for user in StaffProfile.objects.filter(staff_id__isnull=True):
        user.staff_id = f"APED-{user.date_joined:%y}-{user.pk:04d}"
        user.save(update_fields=["staff_id"])


class Migration(migrations.Migration):
    dependencies = [("account", "0002_staffprofile_staff_id")]

    operations = [
        migrations.AddField(
            model_name="staffprofile",
            name="staff_id",
            field=models.CharField(blank=True, editable=False, max_length=20, null=True, unique=True),
        ),
        migrations.AddField(
            model_name="staffprofile",
            name="role",
            field=models.CharField(choices=[("system_admin", "System Administrator"), ("programme_manager", "Programme Manager"), ("data_entry", "Data Entry Officer"), ("read_only", "Read Only")], default="read_only", max_length=30),
        ),
        migrations.AddField(model_name="staffprofile", name="job_title", field=models.CharField(blank=True, max_length=160)),
        migrations.AddField(model_name="staffprofile", name="department", field=models.CharField(blank=True, max_length=160)),
        migrations.AddField(model_name="staffprofile", name="phone", field=models.CharField(blank=True, max_length=40)),
        migrations.AddField(model_name="staffprofile", name="location", field=models.CharField(blank=True, max_length=160)),
        migrations.RunPython(copy_staff_profiles, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="staffprofile",
            name="staff_id",
            field=models.CharField(blank=True, editable=False, max_length=20, unique=True),
        ),
        migrations.DeleteModel(name="LegacyStaffProfile"),
    ]
