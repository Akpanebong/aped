from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


def create_profiles(apps, schema_editor):
    User = apps.get_model(settings.AUTH_USER_MODEL.split(".")[0], settings.AUTH_USER_MODEL.split(".")[1])
    StaffProfile = apps.get_model("account", "StaffProfile")
    StaffProfile.objects.bulk_create([StaffProfile(user_id=user.pk) for user in User.objects.all()])


class Migration(migrations.Migration):
    initial = True
    dependencies = [("account", "0000_customuser")]
    operations = [
        migrations.CreateModel(
            name="StaffProfile",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("role", models.CharField(choices=[("system_admin", "System Administrator"), ("programme_manager", "Programme Manager"), ("data_entry", "Data Entry Officer"), ("read_only", "Read Only")], default="read_only", max_length=30)),
                ("job_title", models.CharField(blank=True, max_length=160)),
                ("department", models.CharField(blank=True, max_length=160)),
                ("phone", models.CharField(blank=True, max_length=40)),
                ("location", models.CharField(blank=True, max_length=160)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("user", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="staff_profile", to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ["user__last_name", "user__first_name", "user__username"], "verbose_name": "Staff profile", "verbose_name_plural": "Staff profiles"},
        ),
        migrations.RunPython(create_profiles, migrations.RunPython.noop),
    ]
