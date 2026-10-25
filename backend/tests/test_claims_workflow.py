from datetime import timedelta

from django.utils import timezone

from apps.claims.models import Claim, HandoverRecord, InventoryRecord
from apps.core.models import AuditLog, Notification
from apps.reports.models import ItemReport
from .helpers import Base, png

ANS = [{"question": "Marks?", "answer": "A tear near the card slot"}]


class ClaimTests(Base):
    def claim(self, user, report_id, **kw):
        return self.as_user(user).post("/api/claims/", {"report": report_id, "description": "My black leather wallet",
                                                        "answers": ANS, **kw}, format="json")

    def test_full_acceptance_workflow_peer_return(self):
        # 1-3 student reports lost, another reports found
        lost = self.make_report(self.student, "lost")
        found = self.make_report(self.student2, "found")
        self.assertTrue(Notification.objects.filter(user=self.student, kind="match").exists())  # 4-5
        # 6-7 student opens found report and claims; hidden details stay hidden
        detail = self.as_user(self.student).get(f"/api/reports/{found['id']}/")
        self.assertIsNone(detail.data["private_details"])
        r = self.claim(self.student, found["id"])
        self.assertEqual(r.status_code, 201, r.content)
        cid = r.data["id"]
        self.assertIsNone(r.data["report_private_details"])
        # claimant cannot approve own claim; unrelated student cannot see it
        self.assertEqual(self.as_user(self.student).post(f"/api/claims/{cid}/review/", {"decision": "approve"}, format="json").status_code, 403)
        self.assertEqual(self.as_user(self.student3).get(f"/api/claims/{cid}/").status_code, 404)
        # 8-9 the finder (not held by staff) reviews and approves; sees hidden details
        view = self.as_user(self.student2).get(f"/api/claims/{cid}/")
        self.assertEqual(view.data["report_private_details"], "SECRET: tear near the card slot")
        ok = self.as_user(self.student2).post(f"/api/claims/{cid}/review/", {"decision": "approve", "reason": "Details match"}, format="json")
        self.assertEqual(ok.status_code, 200, ok.content)
        self.assertEqual(ItemReport.objects.get(pk=found["id"]).status, "claim_pending")
        # claimant cannot mark it returned; only the finder can confirm
        self.assertEqual(self.as_user(self.student).post(f"/api/claims/{cid}/confirm-return/").status_code, 403)
        done = self.as_user(self.student2).post(f"/api/claims/{cid}/confirm-return/")
        self.assertEqual(done.status_code, 200, done.content)
        # 11-12 returned and visible in dashboards/analytics
        self.assertEqual(ItemReport.objects.get(pk=found["id"]).status, "returned")
        self.assertEqual(self.as_user(self.student).get("/api/dashboard/student/").data["items_recovered"], 1)
        stats = self.as_user(self.admin).get("/api/admin/analytics/?days=30").data["totals"]
        self.assertEqual(stats["items_returned"], 1)
        self.assertEqual(stats["recovery_rate"], 1.0)
        self.assertEqual(Claim.objects.get(pk=cid).reviewer_id, self.student2.pk)
        self.assertTrue(AuditLog.objects.filter(action="claim.completed").exists())
        self.assertTrue(Notification.objects.filter(user=self.student, kind="handover").exists())

    def test_finder_cannot_claim_own_item_and_no_duplicate_live_claims(self):
        found = self.make_report(self.student2, "found")
        self.assertEqual(self.claim(self.student2, found["id"]).status_code, 400)
        self.assertEqual(self.claim(self.student, found["id"]).status_code, 201)
        self.assertEqual(self.claim(self.student, found["id"]).status_code, 409)
        lost = self.make_report(self.student, "lost")
        self.assertEqual(self.claim(self.student3, lost["id"]).status_code, 404)  # only found items

    def test_conflicting_approvals_prevented(self):
        found = self.make_report(self.student3, "found")
        c1 = self.claim(self.student, found["id"]).data["id"]
        c2 = self.claim(self.student2, found["id"]).data["id"]
        adm = self.as_user(self.admin)
        self.assertEqual(adm.post(f"/api/claims/{c1}/review/", {"decision": "approve"}, format="json").status_code, 200)
        self.assertEqual(adm.post(f"/api/claims/{c2}/review/", {"decision": "approve"}, format="json").status_code, 409)
        self.assertEqual(Claim.objects.filter(status="approved").count(), 1)
        self.assertEqual(self.claim(self.student, found["id"]).status_code, 409)

    def test_reject_requires_reason_and_dispute_flow(self):
        found = self.make_report(self.student3, "found")
        cid = self.claim(self.student, found["id"]).data["id"]
        fin = self.as_user(self.student3)
        self.assertEqual(fin.post(f"/api/claims/{cid}/review/", {"decision": "reject"}, format="json").status_code, 400)
        self.assertEqual(fin.post(f"/api/claims/{cid}/review/", {"decision": "reject", "reason": "Wrong details"}, format="json").status_code, 200)
        c = Claim.objects.get(pk=cid)
        self.assertEqual((c.status, c.reviewer_id), ("rejected", self.student3.pk))
        self.assertTrue(Notification.objects.filter(user=self.student, kind="claim", title__icontains="not approved").exists())
        self.assertEqual(self.as_user(self.student).post(f"/api/claims/{cid}/dispute/", {"note": "I can prove it"}, format="json").status_code, 200)
        self.assertEqual(len(self.as_user(self.admin).get("/api/admin/disputes/").data), 1)
        self.as_user(self.admin).post(f"/api/admin/disputes/{cid}/", {"outcome": "reopen", "note": "Re-check"}, format="json")
        self.assertEqual(Claim.objects.get(pk=cid).status, "under_review")

    def test_evidence_is_private(self):
        found = self.make_report(self.student3, "found")
        cid = self.claim(self.student, found["id"]).data["id"]
        up = self.as_user(self.student).post(f"/api/claims/{cid}/evidence/", {"file": png("receipt.png"), "note": "photo"}, format="multipart")
        self.assertEqual(up.status_code, 201, up.content)
        eid = up.data["id"]
        self.assertEqual(self.as_user(self.student).get(f"/api/claim-evidence/{eid}/download/").status_code, 200)
        self.assertEqual(self.as_user(self.student3).get(f"/api/claim-evidence/{eid}/download/").status_code, 200)  # finder-reviewer
        self.assertEqual(self.as_user(self.student2).get(f"/api/claim-evidence/{eid}/download/").status_code, 404)
        self.assertEqual(self.as_user(None).get(f"/api/claim-evidence/{eid}/download/").status_code, 401)

    def stored_item(self):
        r = self.as_user(self.staff).post("/api/inventory/", {**self.report_payload("found", title="Wallet at desk"),
                                                              "storage_location": "Locker 3"}, format="multipart")
        self.assertEqual(r.status_code, 201, r.content)
        return r.data

    def test_held_item_needs_authorised_release_and_handover(self):
        inv = self.stored_item()
        rid = inv["report_id"]
        self.assertEqual(InventoryRecord.objects.count(), 1)
        self.assertTrue(ItemReport.objects.get(pk=rid).held_by_staff)
        cid = self.claim(self.student, rid).data["id"]
        # the (finder = staff) route: students and unauthorised staff cannot approve
        self.assertEqual(self.as_user(self.student2).post(f"/api/claims/{cid}/review/", {"decision": "approve"}, format="json").status_code, 403)
        self.assertEqual(self.as_user(self.warden).post(f"/api/claims/{cid}/review/", {"decision": "approve"}, format="json").status_code, 403)
        ok = self.as_user(self.staff).post(f"/api/claims/{cid}/review/", {"decision": "approve", "reason": "ID matched"}, format="json")
        self.assertEqual(ok.status_code, 200, ok.content)
        # a claimant "claim" click or peer confirm never marks a held item returned
        self.assertEqual(self.as_user(self.student).post(f"/api/claims/{cid}/confirm-return/").status_code, 403)
        self.assertEqual(self.as_user(self.staff).post(f"/api/claims/{cid}/confirm-return/").status_code, 403)
        when = (timezone.now() + timedelta(days=1)).isoformat()
        self.assertEqual(self.as_user(self.warden).post(f"/api/claims/{cid}/handover/", {"scheduled_for": when, "location": "Desk"}, format="json").status_code, 403)
        sch = self.as_user(self.staff).post(f"/api/claims/{cid}/handover/", {"scheduled_for": when, "location": "Security desk"}, format="json")
        self.assertEqual(sch.status_code, 200, sch.content)
        h = HandoverRecord.objects.get()
        self.assertTrue(h.reference.startswith("HO-"))
        self.assertTrue(Notification.objects.filter(user=self.student, kind="handover").exists())
        self.assertEqual(self.as_user(self.student).post(f"/api/handovers/{h.pk}/confirm/").status_code, 403)
        self.assertEqual(self.as_user(self.warden).post(f"/api/handovers/{h.pk}/confirm/").status_code, 403)
        self.assertEqual(self.as_user(self.staff).post(f"/api/handovers/{h.pk}/confirm/").status_code, 200)
        h.refresh_from_db()
        self.assertEqual((h.status, h.confirmed_by_id), ("completed", self.staff.pk))
        self.assertEqual(ItemReport.objects.get(pk=rid).status, "returned")
        self.assertEqual(InventoryRecord.objects.get().status, "returned")
        self.assertEqual(self.as_user(self.staff).post(f"/api/handovers/{h.pk}/confirm/").status_code, 409)  # not twice
