from django.core import mail
from django.test import TestCase, override_settings

from .models import StaffProfile


class RoleAccessTests(TestCase):
    def make_user(self, username, role):
        user = StaffProfile.objects.create_user(username, password="TestPass123!")
        user.role = role
        user.save(update_fields=["role"])
        return user

    def test_read_only_cannot_post(self):
        user = self.make_user("readonly", StaffProfile.Role.READ_ONLY)
        self.client.force_login(user)
        self.assertEqual(self.client.post("/monitoring/records/new/", {}).status_code, 403)

    def test_read_only_cannot_open_write_pages(self):
        user = self.make_user("readonly_pages", StaffProfile.Role.READ_ONLY)
        self.client.force_login(user)
        for path in ("/projects/new/", "/activities/new/", "/attendance/new/", "/monitoring/forms/new/"):
            self.assertEqual(self.client.get(path).status_code, 403, path)

    def test_data_entry_cannot_edit_or_configure(self):
        user = self.make_user("dataentry_pages", StaffProfile.Role.DATA_ENTRY)
        self.client.force_login(user)
        for path in ("/monitoring/records/999/edit/", "/monitoring/forms/new/", "/attendance/999/edit/"):
            self.assertEqual(self.client.get(path).status_code, 403, path)

    def test_data_entry_cannot_delete(self):
        user = self.make_user("dataentry", StaffProfile.Role.DATA_ENTRY)
        self.client.force_login(user)
        self.assertEqual(self.client.post("/monitoring/records/999/delete/", {}).status_code, 403)

    def test_system_admin_can_manage_staff(self):
        user = self.make_user("sysadmin", StaffProfile.Role.SYSTEM_ADMIN)
        self.client.force_login(user)
        self.assertEqual(self.client.get("/accounts/staff/").status_code, 200)

    def test_staff_id_is_generated_and_immutable(self):
        user = self.make_user("generated", StaffProfile.Role.DATA_ENTRY)
        staff_id = user.staff_id
        user.username = "new-username"
        user.save()
        user.refresh_from_db()
        self.assertTrue(staff_id.startswith("APED-"))
        self.assertEqual(user.staff_id, staff_id)

    def test_login_accepts_staff_id_email_and_phone(self):
        user = self.make_user("identifier", StaffProfile.Role.DATA_ENTRY)
        user.email = "identifier@example.com"
        user.phone = "+256700000001"
        user.save(update_fields=["phone"])
        user.set_password("TestPass123!")
        user.save()
        for identifier in (user.username, user.staff_id, user.email, user.phone):
            self.client.logout()
            self.assertTrue(self.client.login(username=identifier, password="TestPass123!"))

    @override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
    def test_staff_creation_sends_onboarding_email(self):
        admin = self.make_user("creator", StaffProfile.Role.SYSTEM_ADMIN)
        self.client.force_login(admin)
        response = self.client.post("/accounts/staff/new/", {
            "first_name": "New", "last_name": "Officer", "email": "officer@example.com",
            "role": StaffProfile.Role.DATA_ENTRY, "job_title": "Officer", "department": "Field",
            "phone": "+256700000002", "location": "Gulu",
        })
        self.assertEqual(response.status_code, 302)
        user = StaffProfile.objects.get(email="officer@example.com")
        self.assertEqual(user.username, user.staff_id)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn(user.staff_id, mail.outbox[0].body)
        self.assertIn("Temporary password:", mail.outbox[0].body)
