from django.test import override_settings
from rest_framework.test import APIClient

from apps.accounts.models import User
from .helpers import PW, Base


class AuthTests(Base):
    reg = {"full_name": "New Student", "email": "new@students.campus.example.edu", "password": PW}

    def test_academic_domains_accepted_and_staff_admin_need_approval(self):
        c = APIClient()
        for i, (email, kind) in enumerate([("a@mit.edu", "student"), ("b@iitb.ac.in", "faculty"), ("c@ox.ac.uk", "staff"), ("d@uni.edu.au", "admin")]):
            r = c.post("/api/auth/register/", {**self.reg, "email": email, "account_type": kind}, format="json")
            self.assertEqual(r.status_code, 201, r.data)
        self.assertEqual(User.objects.get(email="a@mit.edu").role, "student")
        self.assertEqual(User.objects.get(email="b@iitb.ac.in").role, "faculty")
        for email, kind in (("c@ox.ac.uk", "staff"), ("d@uni.edu.au", "admin")):
            u = User.objects.get(email=email)
            self.assertEqual((u.role, u.staff_requested, u.requested_role), ("student", True, kind))  # no power until approved
        self.as_user(self.admin).post(f"/api/admin/staff-requests/{User.objects.get(email='d@uni.edu.au').pk}/", {"decision": "approve"}, format="json")
        self.assertEqual(User.objects.get(email="d@uni.edu.au").role, "admin")

    def test_register_requires_allowed_domain(self):
        r = APIClient().post("/api/auth/register/", {**self.reg, "email": "x@gmail.com"}, format="json")
        self.assertEqual(r.status_code, 400)
        self.assertIn("email", r.data)

    @override_settings(DEV_EXPOSE_VERIFICATION_LINK=True)
    def test_register_verify_login_flow_and_hashing(self):
        c = APIClient()
        r = c.post("/api/auth/register/", self.reg, format="json")
        self.assertEqual(r.status_code, 201)
        u = User.objects.get(email=self.reg["email"])
        self.assertNotEqual(u.password, PW)
        self.assertTrue(u.password.startswith(("pbkdf2_", "argon2", "bcrypt")))
        self.assertEqual(u.role, "student")  # role is never taken from the client
        # unverified accounts cannot log in
        r = c.post("/api/auth/login/", {"email": self.reg["email"], "password": PW}, format="json")
        self.assertEqual(r.status_code, 403)
        token = r.data and u.verification_token
        self.assertEqual(c.post("/api/auth/verify-email/", {"token": token}, format="json").status_code, 200)
        r = c.post("/api/auth/login/", {"email": self.reg["email"], "password": PW}, format="json")
        self.assertEqual(r.status_code, 200)
        self.assertNotIn("password", r.data["user"])

    def test_cannot_register_as_admin(self):
        APIClient().post("/api/auth/register/", {**self.reg, "role": "admin"}, format="json")
        self.assertEqual(User.objects.get(email=self.reg["email"]).role, "student")

    def test_wrong_password_and_weak_password(self):
        r = APIClient().post("/api/auth/login/", {"email": self.student.email, "password": "nope"}, format="json")
        self.assertEqual(r.status_code, 400)
        r = APIClient().post("/api/auth/register/", {**self.reg, "password": "12345678"}, format="json")
        self.assertEqual(r.status_code, 400)

    def test_deactivated_user_cannot_login(self):
        self.student.is_active = False
        self.student.save()
        r = APIClient().post("/api/auth/login/", {"email": self.student.email, "password": PW}, format="json")
        self.assertEqual(r.status_code, 403)

    def test_change_password(self):
        c = self.as_user(self.student)
        bad = c.post("/api/auth/change-password/", {"old_password": "wrong", "new_password": "An0ther-Pass-77!"}, format="json")
        self.assertEqual(bad.status_code, 400)
        ok = c.post("/api/auth/change-password/", {"old_password": PW, "new_password": "An0ther-Pass-77!"}, format="json")
        self.assertEqual(ok.status_code, 200)
        self.student.refresh_from_db()
        self.assertTrue(self.student.check_password("An0ther-Pass-77!"))

    def test_protected_routes_need_auth(self):
        self.assertEqual(APIClient().get("/api/reports/").status_code, 401)
        self.assertEqual(APIClient().get("/api/auth/me/").status_code, 401)


class RoleAccessTests(Base):
    def test_admin_endpoints_forbidden_for_non_admins(self):
        for path in ["/api/admin/users/", "/api/admin/analytics/", "/api/admin/audit-logs/", "/api/admin/settings/",
                     "/api/admin/abuse/", "/api/admin/categories/"]:
            self.assertEqual(self.as_user(self.student).get(path).status_code, 403, path)
            self.assertEqual(self.as_user(self.staff).get(path).status_code, 403, path)
            self.assertEqual(self.as_user(self.admin).get(path).status_code, 200, path)

    def test_staff_endpoints_forbidden_for_students(self):
        self.assertEqual(self.as_user(self.student).get("/api/inventory/").status_code, 403)
        self.assertEqual(self.as_user(self.staff).get("/api/inventory/").status_code, 200)

    def test_admin_cannot_demote_self_and_audit_logged(self):
        c = self.as_user(self.admin)
        self.assertEqual(c.patch(f"/api/admin/users/{self.admin.pk}/", {"role": "student"}, format="json").status_code, 400)
        r = c.patch(f"/api/admin/users/{self.student.pk}/", {"is_active": False}, format="json")
        self.assertEqual(r.status_code, 200)
        self.assertIn("admin.user_updated", [e["action"] for e in c.get("/api/admin/audit-logs/").data["results"]])

    def test_staff_request_needs_admin_approval(self):
        self.student.staff_requested = True
        self.student.save()
        self.as_user(self.admin).post(f"/api/admin/staff-requests/{self.student.pk}/", {"decision": "approve"}, format="json")
        self.student.refresh_from_db()
        self.assertEqual(self.student.role, "staff")
