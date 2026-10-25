from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APIClient

from apps.core.models import Notification
from apps.reports.models import ItemReport, Match
from .helpers import Base, png


class ReportTests(Base):
    def test_create_report_with_image_and_private_field_protection(self):
        c = self.as_user(self.student)
        r = c.post("/api/reports/", {**self.report_payload("lost"), "images": png()}, format="multipart")
        self.assertEqual(r.status_code, 201, r.content)
        self.assertEqual(len(r.data["images"]), 1)
        self.assertIn("SECRET", r.data["private_details"])  # owner sees own
        rid = r.data["id"]
        other = self.as_user(self.student2).get(f"/api/reports/{rid}/")
        self.assertIsNone(other.data["private_details"])
        self.assertNotIn("SECRET", other.content.decode())
        feed = self.as_user(self.student2).get("/api/reports/")
        self.assertNotIn("SECRET", feed.content.decode())
        self.assertNotIn("s1@students", feed.content.decode())
        pub = APIClient().get("/api/public/recent/")
        self.assertEqual(pub.status_code, 200)
        self.assertNotIn("SECRET", pub.content.decode())
        self.assertIsNone(self.as_user(self.student2).get(f"/api/reports/{rid}/").data["private_details"])
        self.assertEqual(self.as_user(self.staff).get(f"/api/reports/{rid}/").data["private_details"], "SECRET: tear near the card slot")

    def test_image_validation(self):
        c = self.as_user(self.student)
        fake = SimpleUploadedFile("evil.png", b"not an image at all", content_type="image/png")
        r = c.post("/api/reports/", {**self.report_payload("lost"), "images": fake}, format="multipart")
        self.assertEqual(r.status_code, 400)
        self.assertIn("images", r.data)
        self.assertEqual(ItemReport.objects.count(), 0)

    def test_server_side_validation(self):
        c = self.as_user(self.student)
        r = c.post("/api/reports/", self.report_payload("lost", title="x", date="2999-01-01"), format="multipart")
        self.assertEqual(r.status_code, 400)
        self.assertIn("title", r.data)
        self.assertIn("date", r.data)

    def test_only_owner_can_edit_or_close(self):
        rid = self.make_report(self.student, "lost")["id"]
        self.assertEqual(self.as_user(self.student2).patch(f"/api/reports/{rid}/", {"title": "Hacked"}, format="json").status_code, 403)
        self.assertEqual(self.as_user(self.student2).post(f"/api/reports/{rid}/close/").status_code, 403)
        self.assertEqual(self.as_user(self.student).patch(f"/api/reports/{rid}/", {"title": "New title"}, format="json").status_code, 200)
        self.assertEqual(self.as_user(self.student).post(f"/api/reports/{rid}/close/").status_code, 200)

    def test_search_filters_and_pagination(self):
        self.make_report(self.student, "lost", title="Black wallet")
        self.make_report(self.student2, "found", title="Phone", category=self.phones.pk, description="Blue phone with cracked screen")
        c = self.as_user(self.student3)
        self.assertEqual(c.get("/api/reports/?type=found").data["count"], 1)
        self.assertEqual(c.get("/api/reports/?q=wallet").data["count"], 1)
        self.assertEqual(c.get(f"/api/reports/?category={self.phones.pk}").data["count"], 1)
        self.assertEqual(c.get(f"/api/reports/?location={self.loc2.pk}").data["count"], 0)
        self.assertEqual(c.get("/api/reports/?q=wallet&ordering=relevance").status_code, 200)
        self.assertIn("results", c.get("/api/reports/?page_size=1").data)

    def test_comments_permissions(self):
        rid = self.make_report(self.student, "lost")["id"]
        c2 = self.as_user(self.student2)
        r = c2.post(f"/api/reports/{rid}/comments/", {"body": "I saw it"}, format="json")
        self.assertEqual(r.status_code, 201)
        self.assertEqual(c2.post(f"/api/reports/{rid}/comments/", {"body": "x" * 1001}, format="json").status_code, 400)
        cid = r.data["id"]
        self.assertEqual(self.as_user(self.student3).delete(f"/api/comments/{cid}/").status_code, 403)
        self.assertEqual(self.as_user(self.student3).patch(f"/api/comments/{cid}/", {"body": "edit"}, format="json").status_code, 403)
        self.assertTrue(Notification.objects.filter(user=self.student, kind="comment").exists())
        self.assertEqual(self.as_user(self.admin).delete(f"/api/comments/{cid}/").status_code, 204)

    def test_messaging_is_private(self):
        rid = self.make_report(self.student, "found")["id"]
        r = self.as_user(self.student2).post("/api/conversations/", {"report": rid, "body": "Is this mine?"}, format="json")
        self.assertEqual(r.status_code, 201)
        cid = r.data["id"]
        self.assertEqual(self.as_user(self.student3).get(f"/api/conversations/{cid}/").status_code, 404)
        self.assertEqual(self.as_user(self.student3).post(f"/api/conversations/{cid}/messages/", {"body": "hi"}, format="json").status_code, 404)
        self.assertEqual(self.as_user(self.student).get(f"/api/conversations/{cid}/").status_code, 200)
        self.assertEqual(self.as_user(self.student).post("/api/conversations/", {"report": rid, "body": "me"}, format="json").status_code, 400)
        self.assertTrue(Notification.objects.filter(user=self.student, kind="message").exists())
        self.assertNotIn("Is this mine", self.as_user(self.student2).get(f"/api/reports/{rid}/").content.decode())
        self.assertEqual(self.as_user(self.admin).get(f"/api/conversations/{cid}/").status_code, 200)

    def test_bookmarks_and_abuse(self):
        rid = self.make_report(self.student, "lost")["id"]
        c = self.as_user(self.student2)
        self.assertEqual(c.post(f"/api/reports/{rid}/bookmark/").status_code, 201)
        self.assertEqual(c.post(f"/api/reports/{rid}/bookmark/").status_code, 201)  # idempotent
        self.assertEqual(c.get("/api/bookmarks/").data["count"], 1)
        self.assertEqual(c.post(f"/api/reports/{rid}/abuse/", {"reason": "spam"}, format="json").status_code, 201)
        self.assertEqual(len(self.as_user(self.admin).get("/api/admin/abuse/").data), 1)


class MatchingTests(Base):
    def test_lost_and_found_produce_one_match_and_notification(self):
        lost = self.make_report(self.student, "lost")
        found = self.make_report(self.student2, "found", location=self.loc2.pk)
        self.assertEqual(Match.objects.count(), 1)
        m = Match.objects.get()
        self.assertEqual((m.lost_report_id, m.found_report_id), (lost["id"], found["id"]))
        self.assertTrue(m.explanation)
        self.assertEqual(set(m.components), {"category", "text", "location", "date", "visual"})
        self.assertTrue(Notification.objects.filter(user=self.student, kind="match").exists())
        resp = self.as_user(self.student).get(f"/api/reports/{lost['id']}/matches/")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.data), 1)
        self.assertIn("similarity_estimate", resp.data[0])
        self.assertNotIn("SECRET", resp.content.decode().replace(lost["private_details"], ""))
        self.assertEqual(self.as_user(self.student3).get(f"/api/reports/{lost['id']}/matches/").status_code, 403)

    def test_same_type_never_matches_and_no_duplicates(self):
        self.make_report(self.student, "lost")
        self.make_report(self.student2, "lost")
        self.assertEqual(Match.objects.count(), 0)
        found = self.make_report(self.student3, "found")
        from apps.reports.matching_service import recompute_matches
        recompute_matches(ItemReport.objects.get(pk=found["id"]))
        recompute_matches(ItemReport.objects.get(pk=found["id"]))
        self.assertEqual(Match.objects.count(), 2)  # one per lost report, no duplicates

    def test_incompatible_category_not_matched(self):
        self.make_report(self.student, "lost")
        self.make_report(self.student2, "found", title="Phone", category=self.phones.pk, description="Black leather wallet with cards inside")
        self.assertEqual(Match.objects.count(), 0)

    def test_dismiss_and_recalculate_on_edit(self):
        lost = self.make_report(self.student, "lost")
        self.make_report(self.student2, "found")
        m = Match.objects.get()
        self.assertEqual(self.as_user(self.student).post(f"/api/matches/{m.pk}/dismiss/").status_code, 200)
        self.assertEqual(self.as_user(self.student).get(f"/api/reports/{lost['id']}/matches/").data, [])
        self.assertEqual(self.as_user(self.student3).post(f"/api/matches/{m.pk}/dismiss/").status_code, 404)
        # editing the report to an unrelated category removes non-dismissed matches
        self.as_user(self.student).patch(f"/api/reports/{lost['id']}/", {"category": self.phones.pk}, format="json")
        self.assertEqual(Match.objects.exclude(status="dismissed").count(), 0)
