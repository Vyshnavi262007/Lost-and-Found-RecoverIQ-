"""Idempotent demo data (fictional). Safe to run repeatedly: existing rows are reused, never duplicated.

Passwords come from DEMO_ADMIN_PASSWORD / DEMO_USER_PASSWORD (see .env.example); the defaults below
are DEVELOPMENT-ONLY values documented in the README.
"""
import os
from datetime import date, time, timedelta

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from apps.accounts.models import User
from apps.claims import services as cs
from apps.claims.models import Claim, InventoryRecord
from apps.core.models import Campus, CampusLocation, ItemCategory, Notification
from apps.reports.matching_service import recompute_matches
from apps.reports.models import Comment, ItemReport

DOMAIN = "students.campus.example.edu"
STAFF_DOMAIN = "campus.example.edu"

LOCATIONS = [  # name, block, x, y (metres on a local campus grid)
    ("Main Library", "Central", 0, 0), ("Student Center", "Central", 120, 40), ("Cafeteria", "Central", 100, -100),
    ("Administration Block", "Central", 60, 120), ("Engineering Block", "North", 300, -80),
    ("Science Block", "North", 250, 150), ("Auditorium", "East", 200, -200), ("Hostel A", "Residence", -200, 300),
    ("Hostel B", "Residence", -260, 260), ("Sports Complex", "South", 500, 300), ("Main Gate", "Gate", -50, -350),
]
CATEGORIES = [("ID Cards", "documents"), ("Wallets & Cards", "documents"), ("Keys", "personal"),
              ("Mobile Phones", "electronics"), ("Chargers & Cables", "electronics"),
              ("Earphones & Headphones", "electronics"), ("Laptops & Tablets", "electronics"),
              ("Books & Stationery", "study"), ("Water Bottles", "personal"), ("Watches & Jewellery", "personal"),
              ("Bags", "personal"), ("Clothing", "personal"), ("Other", "other")]


class Command(BaseCommand):
    help = "Create fictional demo users, locations, categories, reports, matches, comments, claims and inventory."

    def make_user(self, email, name, role="student", pw=None, **extra):
        u = User.objects.filter(email=email).first()
        if u:
            return u
        first, last = name.split(" ", 1)
        u = User(username=email, email=email, first_name=first, last_name=last, role=role, email_verified=True, **extra)
        u.set_password(pw)
        u.save()
        return u

    @transaction.atomic
    def handle(self, *args, **opts):
        admin_pw = os.environ.get("DEMO_ADMIN_PASSWORD", "RecoverIQ-Admin-2026!")
        user_pw = os.environ.get("DEMO_USER_PASSWORD", "RecoverIQ-Demo-2026!")
        campus, _ = Campus.objects.get_or_create(code="riverside", defaults={"name": "Riverside University"})
        locs = {}
        for name, block, x, y in LOCATIONS:
            locs[name], _ = CampusLocation.objects.get_or_create(
                campus=campus, name=name, defaults={"block": block, "x_m": x, "y_m": y})
        cats = {}
        for name, group in CATEGORIES:
            cats[name], _ = ItemCategory.objects.get_or_create(
                slug=name.lower().replace(" & ", "-").replace(" ", "-"), defaults={"name": name, "group": group})

        admin = self.make_user(f"admin@{STAFF_DOMAIN}", "Priya Admin", "admin", admin_pw, campus=campus)
        if not admin.is_superuser:
            admin.is_staff = admin.is_superuser = True
            admin.save()
        security = self.make_user(f"security@{STAFF_DOMAIN}", "Dev Security", "staff", user_pw, campus=campus,
                                  staff_title="Security desk", can_review_claims=True, can_release_items=True)
        warden = self.make_user(f"warden@{STAFF_DOMAIN}", "Lata Warden", "staff", user_pw, campus=campus,
                                staff_title="Hostel warden", can_review_claims=True, can_release_items=False)
        asha = self.make_user(f"asha@{DOMAIN}", "Asha Menon", pw=user_pw, student_id="DEMO-1001", department="Computer Science", year=2, campus=campus)
        ravi = self.make_user(f"ravi@{DOMAIN}", "Ravi Nair", pw=user_pw, student_id="DEMO-1002", department="Mechanical", year=3, campus=campus)
        meera = self.make_user(f"meera@{DOMAIN}", "Meera Shah", pw=user_pw, student_id="DEMO-1003", department="Biotech", year=1, campus=campus)
        kiran = self.make_user(f"kiran@{DOMAIN}", "Kiran Rao", pw=user_pw, student_id="DEMO-1004", department="Electronics", year=4, campus=campus)
        self.make_user(f"prof.iyer@{STAFF_DOMAIN}", "Anand Iyer", "faculty", user_pw, department="Physics", campus=campus)
        # a pending staff-access request to demonstrate the approval queue
        self.make_user(f"hk.request@{STAFF_DOMAIN}", "Hari Housekeeping", pw=user_pw, staff_requested=True, requested_role="staff")

        today = date.today()

        def report(user, type_, title, cat, desc, loc, days_ago, private="", **kw):
            r = ItemReport.objects.filter(reporter=user, title=title).first()
            if r:
                return r, False
            r = ItemReport.objects.create(
                reporter=user, type=type_, title=title, category=cats[cat], description=desc, location=locs[loc],
                date=today - timedelta(days=days_ago), private_details=private, **kw)
            return r, True

        new = []
        new.append(report(asha, "lost", "Black leather wallet", "Wallets & Cards",
                          "Black leather bifold wallet, Fossil brand, with my student ID and a metro card inside.",
                          "Main Library", 3, "Has a small tear near the left card slot; a 2019 photo of my dog inside.",
                          brand="Fossil", color="Black", time=time(16, 30)))
        new.append(report(ravi, "lost", "Blue steel water bottle", "Water Bottles",
                          "Navy blue insulated steel bottle, 750 ml, with a sticker of a mountain on the side.",
                          "Sports Complex", 4, "Dent on the base. Initials RN scratched under the cap.", brand="Milton", color="Blue"))
        new.append(report(meera, "lost", "White wireless earbuds with case", "Earphones & Headphones",
                          "White wireless earbuds in a white charging case with a green silicone cover.",
                          "Engineering Block", 2, "Left earbud has a scratch.", color="White"))
        new.append(report(asha, "lost", "Hostel room key with red tag", "Keys",
                          "Single brass key on a red plastic tag marked B-214.", "Hostel B", 6, "Tag number B-214."))
        new.append(report(security, "found", "Black wallet found near reading hall", "Wallets & Cards",
                          "Black leather wallet found on a reading table on the second floor. Contains cards.",
                          "Main Library", 2, "Contains an ID card and a photo of a dog. Small tear on card slot.",
                          held_by_staff=True, color="Black"))
        new.append(report(kiran, "found", "Blue water bottle left in cafeteria", "Water Bottles",
                          "Dark blue steel bottle with a mountain sticker, left on a table in the cafeteria.",
                          "Cafeteria", 3, "Initials scratched under the lid.", color="Blue"))
        new.append(report(security, "found", "White earbuds case", "Earphones & Headphones",
                          "White earbuds charging case with green cover handed in at the gate desk.",
                          "Main Gate", 1, "One scratched earbud inside.", held_by_staff=True, color="White"))
        new.append(report(warden, "found", "Grey hoodie", "Clothing", "Grey zip-up hoodie, size M, found in the hostel common room.",
                          "Hostel A", 5, "Name tag sewn inside the collar.", color="Grey"))
        for r, created in new:
            if created:
                recompute_matches(r)

        for r, _ in new:
            if r.held_by_staff and not InventoryRecord.objects.filter(report=r).exists():
                InventoryRecord.objects.create(report=r, name=r.title, category=r.category, received_at=timezone.now(),
                                               received_by=security, storage_location="Security desk locker 3",
                                               condition_notes="Good condition")
        wallet_found = next(r for r, _ in new if r.title.startswith("Black wallet"))
        bottle_found = next(r for r, _ in new if r.title.startswith("Blue water bottle left"))
        if not Comment.objects.filter(report=bottle_found).exists():
            Comment.objects.create(report=bottle_found, author=ravi, body="This looks like mine! I lost it near the sports complex.")
            Comment.objects.create(report=bottle_found, author=kiran, body="Happy to hand it over once you can describe it.")
        if not Claim.objects.filter(report=bottle_found).exists():
            try:
                cs.submit_claim(ravi, bottle_found.pk, "My navy Milton 750 ml bottle with a mountain sticker.",
                                [{"question": "Any unique marks?", "answer": "Dent on the base and my initials under the cap."}],
                                "Meet at the library")
            except cs.ClaimError as e:
                self.stdout.write(f"Skipped demo claim: {e.message}")
        if not Claim.objects.filter(report=wallet_found).exists():
            try:
                c = cs.submit_claim(asha, wallet_found.pk, "Black Fossil wallet with my student ID.",
                                    [{"question": "Any unique marks?", "answer": "Small tear by the left card slot and a photo of my dog."}])
                cs.review_claim(security, c.pk, "start")
            except cs.ClaimError as e:
                self.stdout.write(f"Skipped demo claim: {e.message}")
        self.stdout.write(self.style.SUCCESS(
            f"Demo data ready. Matches: {sum(1 for _ in __import__('apps.reports.models', fromlist=['Match']).Match.objects.all())}, "
            f"notifications: {Notification.objects.count()}."))
