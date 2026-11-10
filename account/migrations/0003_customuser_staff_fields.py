from django.db import migrations, models


def copy_staff_profiles(apps, schema_editor):
    CustomUser = apps.get_model("account", "CustomUser")
    StaffProfile = apps.get_model("account", "StaffProfile")

    profile_fields = ["staff_id", "role", "job_title", "department", "phone", "location"]
    for profile in StaffProfile.objects.all():
        try:
            user = CustomUser.objects.get(pk=profile.user_id)
        except CustomUser.DoesNotExist:
            continue
        for field in profile_fields:
            setattr(user, field, getattr(profile, field))
        user.save(update_fields=profile_fields)

    for user in CustomUser.objects.filter(staff_id__isnull=True):
        user.staff_id = f"APED-{user.date_joined:%y}-{user.pk:04d}"
        user.save(update_fields=["staff_id"])


class Migration(migrations.Migration):
    dependencies = [("account", "0002_staffprofile_staff_id")]

    operations = [
        migrations.AddField(
            model_name="customuser",
            name="staff_id",
            field=models.CharField(blank=True, editable=False, max_length=20, null=True, unique=True),
        ),
        migrations.AddField(
            model_name="customuser",
            name="role",
            field=models.CharField(choices=[("system_admin", "System Administrator"), ("programme_manager", "Programme Manager"), ("data_entry", "Data Entry Officer"), ("read_only", "Read Only")], default="read_only", max_length=30),
        ),
        migrations.AddField(model_name="customuser", name="job_title", field=models.CharField(blank=True, max_length=160)),
        migrations.AddField(model_name="customuser", name="department", field=models.CharField(blank=True, max_length=160)),
        migrations.AddField(model_name="customuser", name="phone", field=models.CharField(blank=True, max_length=40)),
        migrations.AddField(model_name="customuser", name="location", field=models.CharField(blank=True, max_length=160)),
        migrations.RunPython(copy_staff_profiles, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="customuser",
            name="staff_id",
            field=models.CharField(blank=True, editable=False, max_length=20, unique=True),
        ),
        migrations.DeleteModel(name="StaffProfile"),
    ]
