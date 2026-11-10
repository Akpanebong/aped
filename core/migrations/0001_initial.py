from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True
    dependencies = [migrations.swappable_dependency(settings.AUTH_USER_MODEL)]
    operations = [
        migrations.CreateModel(
            name='Project',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('code', models.CharField(max_length=40, unique=True)),
                ('name', models.CharField(max_length=180)),
                ('description', models.TextField(blank=True)),
                ('location', models.CharField(blank=True, max_length=180)),
                ('start_date', models.DateField(blank=True, null=True)),
                ('end_date', models.DateField(blank=True, null=True)),
                ('is_active', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={'ordering': ['name']},
        ),
        migrations.CreateModel(
            name='Activity',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('activity_name', models.CharField(max_length=180)),
                ('village', models.CharField(max_length=180)),
                ('activity_date', models.DateField()),
                ('facilitator', models.CharField(blank=True, max_length=180)),
                ('notes', models.TextField(blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='core_activities', to=settings.AUTH_USER_MODEL)),
                ('project', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='activities', to='core.project')),
            ],
            options={'ordering': ['-activity_date', '-created_at']},
        ),
        migrations.CreateModel(
            name='Attendance',
            fields=[
                ('activity_ptr', models.OneToOneField(auto_created=True, on_delete=django.db.models.deletion.CASCADE, parent_link=True, primary_key=True, serialize=False, to='core.activity')),
                ('name', models.CharField(max_length=180)),
                ('gender', models.CharField(choices=[('male', 'Male'), ('female', 'Female'), ('other', 'Other')], max_length=10)),
                ('age_group', models.CharField(choices=[('18-35', '18-35'), ('35+', '35+')], max_length=10)),
                ('disability_status', models.CharField(choices=[('yes', 'Yes'), ('no', 'No')], default='no', max_length=5)),
                ('disability_type', models.CharField(blank=True, max_length=120)),
                ('contact', models.CharField(blank=True, max_length=80)),
                ('signature', models.CharField(blank=True, help_text='Signature, consent or attendance confirmation', max_length=180)),
                ('attendance_notes', models.TextField(blank=True)),
            ],
            options={'ordering': ['-activity_date', 'name']},
            bases=('core.activity',),
        ),
    ]
