from datetime import date, timedelta
from io import BytesIO

from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient, APITestCase

from apps.accounts.models import User
from apps.core.models import Campus, CampusLocation, ItemCategory

PW = "Str0ng-Test-Pass!9"


def png(name="x.png", size=(20, 20)):
    buf = BytesIO()
    Image.new("RGB", size, (200, 30, 30)).save(buf, "PNG")
    return SimpleUploadedFile(name, buf.getvalue(), content_type="image/png")


class Base(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.campus = Campus.objects.create(name="Test Campus", code="test")
        cls.loc1 = CampusLocation.objects.create(campus=cls.campus, name="Library", block="A", x_m=0, y_m=0)
        cls.loc2 = CampusLocation.objects.create(campus=cls.campus, name="Cafe", block="A", x_m=60, y_m=0)
        cls.wallets = ItemCategory.objects.create(name="Wallets", slug="wallets", group="documents")
        cls.phones = ItemCategory.objects.create(name="Phones", slug="phones", group="electronics")
        cls.student = cls.mk("s1@students.campus.example.edu", "Sam One")
        cls.student2 = cls.mk("s2@students.campus.example.edu", "Tia Two")
        cls.student3 = cls.mk("s3@students.campus.example.edu", "Uma Three")
        cls.staff = cls.mk("st@campus.example.edu", "Stan Staff", "staff", can_review_claims=True, can_release_items=True)
        cls.warden = cls.mk("w@campus.example.edu", "Wes Warden", "staff", can_review_claims=True)
        cls.admin = cls.mk("a@campus.example.edu", "Ada Admin", "admin")

    @classmethod
    def mk(cls, email, name, role="student", **kw):
        first, last = name.split(" ", 1)
        u = User(username=email, email=email, first_name=first, last_name=last, role=role, email_verified=True, **kw)
        u.set_password(PW)
        u.save()
        return u

    def as_user(self, user):
        c = APIClient()
        if user:
            c.credentials(HTTP_AUTHORIZATION="Token " + Token.objects.get_or_create(user=user)[0].key)
        return c

    def report_payload(self, type_, title="Black leather wallet", **kw):
        d = {"type": type_, "title": title, "category": self.wallets.pk, "description": "Black leather wallet with cards inside",
             "location": self.loc1.pk, "date": (date.today() - timedelta(days=1)).isoformat(),
             "private_details": "SECRET: tear near the card slot"}
        d.update(kw)
        return d

    def make_report(self, user, type_, **kw):
        r = self.as_user(user).post("/api/reports/", self.report_payload(type_, **kw), format="multipart")
        self.assertEqual(r.status_code, 201, r.content)
        return r.data
