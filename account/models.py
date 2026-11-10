from django.contrib.auth.models import AbstractUser
from django.contrib.auth.models import Group, Permission
from django.db import models
from django.utils import timezone


class CustomUser(AbstractUser):
    """The single APED authentication and staff profile model."""

    class Role(models.TextChoices):
        SYSTEM_ADMIN = "system_admin", "System Administrator"
        PROGRAMME_MANAGER = "programme_manager", "Programme Manager"
        DATA_ENTRY = "data_entry", "Data Entry Officer"
        READ_ONLY = "read_only", "Read Only"

    staff_id = models.CharField(max_length=20, unique=True, editable=False, blank=True)
    role = models.CharField(max_length=30, choices=Role.choices, default=Role.READ_ONLY)
    job_title = models.CharField(max_length=160, blank=True)
    department = models.CharField(max_length=160, blank=True)
    phone = models.CharField(max_length=40, blank=True)
    location = models.CharField(max_length=160, blank=True)
    groups = models.ManyToManyField(
        Group,
        blank=True,
        through="CustomUserGroup",
        related_name="custom_users",
        related_query_name="custom_user",
        verbose_name="groups",
    )
    user_permissions = models.ManyToManyField(
        Permission,
        blank=True,
        through="CustomUserPermission",
        related_name="custom_users",
        related_query_name="custom_user",
        verbose_name="user permissions",
    )

    class Meta:
        db_table = "auth_user"
        swappable = "AUTH_USER_MODEL"
        ordering = ["last_name", "first_name", "username"]

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if not self.staff_id:
            self.staff_id = f"APED-{timezone.localdate():%y}-{self.pk:04d}"
            type(self).objects.filter(pk=self.pk).update(staff_id=self.staff_id)

    @property
    def is_system_admin(self):
        return self.role == self.Role.SYSTEM_ADMIN or self.is_superuser

    @property
    def role_label(self):
        return self.get_role_display()

    def __str__(self):
        return self.get_full_name() or self.username


class CustomUserGroup(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, db_column="user_id")
    group = models.ForeignKey(Group, on_delete=models.CASCADE, db_column="group_id")

    class Meta:
        managed = False
        db_table = "auth_user_groups"
        unique_together = (("user", "group"),)


class CustomUserPermission(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, db_column="user_id")
    permission = models.ForeignKey(Permission, on_delete=models.CASCADE, db_column="permission_id")

    class Meta:
        managed = False
        db_table = "auth_user_user_permissions"
        unique_together = (("user", "permission"),)
