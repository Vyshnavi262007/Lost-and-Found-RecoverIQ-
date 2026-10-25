"""Glue between the pure matching engine and the database."""
import logging
from datetime import timedelta

from django.db import transaction
from django.db.models import Q

from apps.core.services import notify
from apps.core.site_settings import get_setting

from . import matching, visual
from .models import ItemReport, Match

logger = logging.getLogger(__name__)
WINDOW_DAYS = 90


def features(report):
    loc = report.location
    return {
        "id": report.pk, "type": report.type, "category_id": report.category_id,
        "category_group": report.category.group, "category_name": report.category.name,
        "text": " ".join([report.title, report.description, report.brand, report.color, report.features]),
        "location": {"id": loc.pk, "x": loc.x_m, "y": loc.y_m, "block": loc.block or None},
        "date": report.date, "time": report.time,
    }


def _first_embedding(report):
    img = report.images.all()[0] if report.images.all() else None
    if img is None:
        return None
    if img.embedding is None:
        img.embedding = visual.embed_path(img.image.path)
        if img.embedding is not None:
            img.save(update_fields=["embedding"])
    return img.embedding


def recompute_matches(report):
    """Never raises: matching problems must not break report submission."""
    try:
        with transaction.atomic():
            return _recompute(report)
    except Exception:
        logger.exception("Matching failed for report %s", getattr(report, "pk", None))
        return []


def _recompute(report):
    side = "lost_report" if report.type == "lost" else "found_report"
    if report.moderation != "approved" or report.status != "open":
        Match.objects.filter(**{side: report}).exclude(status="dismissed").delete()
        return []
    weights = get_setting("match_weights")
    threshold = get_setting("match_threshold")
    notify_at = get_setting("match_notify_threshold")
    opposite = "found" if report.type == "lost" else "lost"
    lo, hi = report.date - timedelta(days=WINDOW_DAYS), report.date + timedelta(days=WINDOW_DAYS)
    candidates = list(ItemReport.objects.filter(type=opposite, status="open", moderation="approved",
                                                date__range=(lo, hi)).exclude(pk=report.pk)
                      .select_related("category", "location").prefetch_related("images"))
    me = features(report)
    cand_f = [features(c) for c in candidates]
    sims = matching.text_similarities(me["text"], [c["text"] for c in cand_f])
    use_visual = visual.available()
    my_emb = _first_embedding(report) if use_visual else None
    kept, created_matches = [], []
    for cand, cf, sim in zip(candidates, cand_f, sims):
        vis = None
        if use_visual and my_emb is not None:
            vis = visual.cosine(my_emb, _first_embedding(cand))
        res = matching.compare(me, cf, sim, weights, visual=vis)
        if res is None or res.score < threshold:
            continue
        lost, found = (report, cand) if report.type == "lost" else (cand, report)
        match, created = Match.objects.update_or_create(
            lost_report=lost, found_report=found,
            defaults={"score": res.score, "components": res.components, "explanation": res.explanation})
        kept.append(match.pk)
        if created:
            created_matches.append((match, res.score))
    Match.objects.filter(**{side: report}).exclude(pk__in=kept).exclude(status="dismissed").delete()
    for match, score in created_matches:
        if score >= notify_at:
            _notify_match(match)
    return kept


def _notify_match(match):
    pct = int(round(match.score * 100))
    lost, found = match.lost_report, match.found_report
    notify(lost.reporter, "match", "Possible match for your lost item",
           f"\"{found.title}\" looks like \"{lost.title}\" (similarity estimate {pct}%).",
           f"/reports/{lost.pk}/matches")
    if found.reporter_id != lost.reporter_id:
        notify(found.reporter, "match", "Someone may be looking for an item you found",
               f"\"{lost.title}\" resembles \"{found.title}\" (similarity estimate {pct}%).",
               f"/reports/{found.pk}/matches")


MATCH_FIELDS = {"title", "description", "category", "location", "date", "time", "brand", "color", "features"}
