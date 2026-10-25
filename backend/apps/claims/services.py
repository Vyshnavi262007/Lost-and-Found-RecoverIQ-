"""Claim, inventory and handover business rules. Every state change happens here, in a transaction."""
import secrets

from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.accounts.permissions import can_release
from apps.core.services import audit, notify
from apps.reports.models import ItemReport

from .models import Claim, ClaimEvent, HandoverRecord, InventoryRecord

LIVE = ("pending", "under_review", "approved")


class ClaimError(Exception):
    def __init__(self, message, status=400):
        super().__init__(message)
        self.message, self.status = message, status


def can_review_claim(user, claim):
    """Who may decide a claim. The claimant never can; the finder can only for items NOT held by staff."""
    if not user.is_authenticated or not user.is_active or claim.claimant_id == user.id:
        return False
    report = claim.report
    if user.role == "admin":
        return True
    if user.role == "staff":
        if not user.can_review_claims:
            return False
        return not report.held_by_staff or user.can_release_items
    return user.id == report.reporter_id and not report.held_by_staff


def can_view_claim(user, claim):
    return user.id == claim.claimant_id or can_review_claim(user, claim)


def record_event(claim, actor, note=""):
    ClaimEvent.objects.create(claim=claim, status=claim.status, actor=actor, note=note[:500])
    audit(actor, f"claim.{claim.status}", claim, {"report": claim.report_id, "note": note[:200]})


def clean_answers(raw):
    if not isinstance(raw, list):
        raise ClaimError("Answers must be a list.")
    out = []
    for item in raw[:6]:
        if isinstance(item, dict):
            q, a = str(item.get("question", ""))[:200], str(item.get("answer", "")).strip()[:500]
            if a:
                out.append({"question": q, "answer": a})
    if not out:
        raise ClaimError("Please answer at least one ownership-verification question.")
    return out


@transaction.atomic
def submit_claim(user, report_id, description, answers, preferred_handover=""):
    report = ItemReport.objects.select_for_update().filter(pk=report_id, moderation="approved").first()
    if not report or report.type != "found":
        raise ClaimError("Only found-item reports can be claimed.", 404)
    if report.status != "open":
        raise ClaimError("This item is no longer open for claims.", 409)
    if report.reporter_id == user.id:
        raise ClaimError("You cannot claim an item you reported as found.")
    description = (description or "").strip()
    if len(description) < 10:
        raise ClaimError("Describe the item in at least 10 characters.")
    if report.claims.filter(status__in=("approved", "completed")).exists():
        raise ClaimError("Another claim has already been approved for this item.", 409)
    answers = clean_answers(answers)
    try:
        claim = Claim.objects.create(report=report, claimant=user, description=description[:2000], answers=answers,
                                     preferred_handover=(preferred_handover or "")[:300])
    except IntegrityError:
        raise ClaimError("You already have an active claim for this item.", 409)
    record_event(claim, user, "Claim submitted")
    link = f"/claims/{claim.pk}"
    notify(report.reporter, "claim", "New ownership claim", f"A claim was submitted for \"{report.title}\".", link)
    return claim


@transaction.atomic
def review_claim(user, claim_id, decision, reason=""):
    claim = Claim.objects.select_for_update().select_related("report").filter(pk=claim_id).first()
    if not claim:
        raise ClaimError("Claim not found.", 404)
    if not can_review_claim(user, claim):
        raise ClaimError("You are not authorised to review this claim.", 403)
    reason = (reason or "").strip()[:500]
    report = ItemReport.objects.select_for_update().get(pk=claim.report_id)
    now = timezone.now()
    if decision == "start":
        if claim.status != "pending":
            raise ClaimError("Only pending claims can be taken for review.", 409)
        claim.status, claim.reviewer = "under_review", user
        claim.save(update_fields=["status", "reviewer", "updated_at"])
        record_event(claim, user, "Review started")
        notify(claim.claimant, "claim", "Your claim is under review", report.title, f"/claims/{claim.pk}")
    elif decision == "approve":
        if claim.status not in ("pending", "under_review"):
            raise ClaimError("This claim can no longer be approved.", 409)
        if report.status != "open" or report.claims.filter(status__in=("approved", "completed")).exists():
            raise ClaimError("Another claim is already approved for this item.", 409)
        claim.status, claim.reviewer, claim.reviewed_at, claim.decision_reason = "approved", user, now, reason
        try:
            with transaction.atomic():
                claim.save()
        except IntegrityError:
            raise ClaimError("Another claim is already approved for this item.", 409)
        report.status = "claim_pending"
        report.save(update_fields=["status", "updated_at"])
        record_event(claim, user, reason or "Ownership verified")
        step = ("Campus staff will schedule a handover." if report.held_by_staff
                else "The finder will arrange the return with you.")
        notify(claim.claimant, "claim", "Your claim was approved", f"{report.title}. {step}", f"/claims/{claim.pk}")
        notify(report.reporter, "status", "A claim was approved for your found item", report.title, f"/reports/{report.pk}")
    elif decision == "reject":
        if claim.status not in ("pending", "under_review"):
            raise ClaimError("This claim can no longer be rejected.", 409)
        if not reason:
            raise ClaimError("Please give a reason for rejecting the claim.")
        claim.status, claim.reviewer, claim.reviewed_at, claim.decision_reason = "rejected", user, now, reason
        claim.save()
        record_event(claim, user, reason)
        notify(claim.claimant, "claim", "Your claim was not approved", reason, f"/claims/{claim.pk}")
    else:
        raise ClaimError("decision must be start, approve or reject.")
    return claim


@transaction.atomic
def withdraw_claim(user, claim_id):
    claim = Claim.objects.select_for_update().select_related("report").filter(pk=claim_id, claimant=user).first()
    if not claim:
        raise ClaimError("Claim not found.", 404)
    if claim.status not in LIVE:
        raise ClaimError("This claim can no longer be withdrawn.", 409)
    was_approved = claim.status == "approved"
    claim.status = "withdrawn"
    claim.save(update_fields=["status", "updated_at"])
    claim.handovers.filter(status="scheduled").update(status="cancelled")
    if was_approved:
        ItemReport.objects.filter(pk=claim.report_id, status="claim_pending").update(status="open")
    record_event(claim, user, "Withdrawn by claimant")
    return claim


@transaction.atomic
def open_dispute(user, claim_id, note):
    claim = Claim.objects.select_for_update().filter(pk=claim_id, claimant=user).first()
    if not claim:
        raise ClaimError("Claim not found.", 404)
    if claim.status != "rejected" or claim.dispute_status != "none":
        raise ClaimError("Only a rejected claim can be disputed, once.", 409)
    if not (note or "").strip():
        raise ClaimError("Explain why you are disputing the decision.")
    claim.dispute_status, claim.dispute_note = "open", note.strip()[:500]
    claim.save(update_fields=["dispute_status", "dispute_note", "updated_at"])
    audit(user, "claim.disputed", claim)
    from apps.accounts.models import User
    for admin in User.objects.filter(role="admin", is_active=True):
        notify(admin, "claim", "A claim decision was disputed", f"Claim #{claim.pk}", "/admin/disputes")
    return claim


@transaction.atomic
def resolve_dispute(admin, claim_id, outcome, note):
    claim = Claim.objects.select_for_update().select_related("report").filter(pk=claim_id, dispute_status="open").first()
    if not claim:
        raise ClaimError("Open dispute not found.", 404)
    note = (note or "").strip()[:500]
    if outcome == "uphold":
        claim.dispute_status = "upheld"
    elif outcome == "reopen":
        if claim.report.status != "open":
            raise ClaimError("The item is no longer open, so the claim cannot be reopened.", 409)
        claim.dispute_status, claim.status = "reopened", "under_review"
        claim.reviewer = admin
    else:
        raise ClaimError("outcome must be uphold or reopen.")
    claim.dispute_resolution = note
    try:
        with transaction.atomic():
            claim.save()
    except IntegrityError:
        raise ClaimError("The claimant already has another active claim for this item.", 409)
    ClaimEvent.objects.create(claim=claim, status=claim.status, actor=admin, note=f"Dispute {claim.dispute_status}: {note}")
    audit(admin, f"claim.dispute_{claim.dispute_status}", claim, {"note": note})
    notify(claim.claimant, "claim", f"Your dispute was resolved: {claim.get_dispute_status_display()}", note,
           f"/claims/{claim.pk}")
    return claim


def _complete(claim, actor, now, note):
    claim.status = "completed"
    claim.save(update_fields=["status", "updated_at"])
    report = claim.report
    report.status, report.returned_at = "returned", now
    report.save(update_fields=["status", "returned_at", "updated_at"])
    record_event(claim, actor, note)
    notify(claim.claimant, "handover", "Item return confirmed", report.title, f"/claims/{claim.pk}")
    notify(report.reporter, "status", "Your found item was returned to its owner", report.title, f"/reports/{report.pk}")
    report.lost_matches.all().delete()
    report.found_matches.all().delete()


@transaction.atomic
def confirm_peer_return(user, claim_id):
    """Item NOT in campus custody: the finder (never the claimant) confirms they handed it over."""
    claim = Claim.objects.select_for_update().select_related("report").filter(pk=claim_id).first()
    if not claim:
        raise ClaimError("Claim not found.", 404)
    report = claim.report
    if report.held_by_staff:
        raise ClaimError("This item is in campus custody; staff must confirm the handover.", 403)
    if user.id != report.reporter_id or user.id == claim.claimant_id:
        raise ClaimError("Only the finder can confirm the return.", 403)
    if claim.status != "approved":
        raise ClaimError("The claim must be approved first.", 409)
    _complete(claim, user, timezone.now(), "Finder confirmed the item was handed over")
    return claim


@transaction.atomic
def schedule_handover(user, claim_id, scheduled_for, location, notes=""):
    if not can_release(user):
        raise ClaimError("Only staff authorised to release items can schedule handovers.", 403)
    claim = Claim.objects.select_for_update().select_related("report").filter(pk=claim_id).first()
    if not claim:
        raise ClaimError("Claim not found.", 404)
    if claim.status != "approved":
        raise ClaimError("Only approved claims can have a handover.", 409)
    if not claim.report.held_by_staff:
        raise ClaimError("This item is not in campus custody.", 400)
    if not (location or "").strip():
        raise ClaimError("Give the handover location.")
    inventory = InventoryRecord.objects.filter(report=claim.report).first()
    claim.handovers.filter(status="scheduled").update(status="cancelled")
    h = HandoverRecord.objects.create(reference="HO-" + secrets.token_hex(4).upper(), inventory=inventory, claim=claim,
                                      scheduled_for=scheduled_for, location=location.strip()[:160],
                                      notes=(notes or "")[:300], scheduled_by=user)
    audit(user, "handover.scheduled", h, {"claim": claim.pk})
    notify(claim.claimant, "handover", "Handover scheduled",
           f"Collect \"{claim.report.title}\" at {h.location}. Reference {h.reference}.", f"/claims/{claim.pk}")
    return h


@transaction.atomic
def confirm_handover(user, handover_id):
    if not can_release(user):
        raise ClaimError("Only staff authorised to release items can confirm a handover.", 403)
    h = HandoverRecord.objects.select_for_update().filter(pk=handover_id).first()
    if not h:
        raise ClaimError("Handover not found.", 404)
    claim = Claim.objects.select_for_update().select_related("report").get(pk=h.claim_id)
    if h.status != "scheduled" or claim.status != "approved":
        raise ClaimError("This handover cannot be confirmed (it is not scheduled, or the claim is not approved).", 409)
    now = timezone.now()
    h.status, h.confirmed_by, h.confirmed_at = "completed", user, now
    h.save()
    if h.inventory_id:
        InventoryRecord.objects.filter(pk=h.inventory_id).update(status="returned")
    _complete(claim, user, now, f"Handover {h.reference} confirmed by {user.display_name}")
    audit(user, "handover.confirmed", h, {"claim": claim.pk})
    return h


@transaction.atomic
def cancel_handover(user, handover_id):
    if not can_release(user):
        raise ClaimError("Not authorised.", 403)
    h = HandoverRecord.objects.select_for_update().filter(pk=handover_id, status="scheduled").first()
    if not h:
        raise ClaimError("Scheduled handover not found.", 404)
    h.status = "cancelled"
    h.save(update_fields=["status"])
    audit(user, "handover.cancelled", h)
    return h
