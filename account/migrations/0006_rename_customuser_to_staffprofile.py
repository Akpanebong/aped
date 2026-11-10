from django.db import migrations, models


def repair_auth_join_tables(apps, schema_editor):
    """Keep existing auth group/permission memberships during the model rename."""
    connection = schema_editor.connection
    quote = connection.ops.quote_name

    for table, old_columns in (
        ("auth_user_groups", ("user_id", "customuser_id")),
        ("auth_user_user_permissions", ("user_id", "customuser_id")),
    ):
        tables = connection.introspection.table_names()
        if table not in tables:
            from account.models import StaffProfile

            field_name = "groups" if table.endswith("groups") else "user_permissions"
            through = StaffProfile._meta.get_field(field_name).remote_field.through
            schema_editor.create_model(through)
            continue

        columns = {field.name for field in connection.introspection.get_table_description(connection.cursor(), table)}
        if "staffprofile_id" not in columns:
            for old_column in old_columns:
                if old_column in columns:
                    schema_editor.execute(
                        f"ALTER TABLE {quote(table)} RENAME COLUMN {quote(old_column)} TO {quote('staffprofile_id')}"
                    )
                    break


class Migration(migrations.Migration):
    dependencies = [("account", "0005_customusergroup_customuserpermission_and_more")]

    operations = [
        migrations.RunPython(repair_auth_join_tables, migrations.RunPython.noop),
        migrations.SeparateDatabaseAndState(
            database_operations=[],
            state_operations=[
                migrations.AlterField(
                    model_name="staffprofile",
                    name="groups",
                    field=models.ManyToManyField(
                        blank=True,
                        help_text="The groups this user belongs to. A user will get all permissions granted to each of their groups.",
                        related_name="user_set",
                        related_query_name="user",
                        to="auth.group",
                        verbose_name="groups",
                    ),
                ),
                migrations.AlterField(
                    model_name="staffprofile",
                    name="user_permissions",
                    field=models.ManyToManyField(
                        blank=True,
                        help_text="Specific permissions for this user.",
                        related_name="user_set",
                        related_query_name="user",
                        to="auth.permission",
                        verbose_name="user permissions",
                    ),
                ),
                migrations.DeleteModel(name="CustomUserGroup"),
                migrations.DeleteModel(name="CustomUserPermission"),
            ],
        ),
    ]
