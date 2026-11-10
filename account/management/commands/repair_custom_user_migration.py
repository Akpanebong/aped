from django.core.management.base import BaseCommand, CommandError
from django.db import connection
from django.utils import timezone


class Command(BaseCommand):
    help = "Mark the compatibility CustomUser migration applied on databases migrated before CustomUser was introduced."

    def handle(self, *args, **options):
        with connection.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) FROM django_migrations WHERE app = %s AND name = %s", ["account", "0001_initial"])
            old_account_migration = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM django_migrations WHERE app = %s AND name = %s", ["account", "0000_customuser"])
            compatibility_migration = cursor.fetchone()[0]
            if not old_account_migration or compatibility_migration:
                self.stdout.write("No migration repair required.")
                return
            try:
                cursor.execute("SELECT COUNT(*) FROM auth_user")
            except Exception as exc:
                raise CommandError("The auth_user table does not exist; run normal migrations instead.") from exc
            cursor.execute(
                "INSERT INTO django_migrations (app, name, applied) VALUES (%s, %s, %s)",
                ["account", "0000_customuser", timezone.now()],
            )
        self.stdout.write(self.style.SUCCESS("Marked account.0000_customuser as applied."))
