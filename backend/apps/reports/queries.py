import operator
from functools import reduce

from django.db.models import Case, Count, Exists, IntegerField, OuterRef, Q, Value, When

from .models import Bookmark, ItemReport


def annotated(qs, user):
    qs = qs.select_related("category", "location", "reporter").prefetch_related("images").annotate(
        comment_count=Count("comments", filter=Q(comments__is_removed=False), distinct=True))
    if user is not None and user.is_authenticated:
        qs = qs.annotate(is_bookmarked=Exists(Bookmark.objects.filter(user=user, report=OuterRef("pk"))))
    return qs


def visible_reports(user):
    """Reports the user may open. Approved ones are public to signed-in users; owners see their own."""
    if user.is_authenticated and user.role == "admin":
        return ItemReport.objects.all()
    if user.is_authenticated:
        return ItemReport.objects.filter(Q(moderation="approved") | Q(reporter=user))
    return ItemReport.objects.filter(moderation="approved")


def apply_filters(qs, params):
    q = (params.get("q") or "").strip()
    relevance = None
    if q:
        terms = [t for t in q.split()[:6] if t]
        qs = qs.filter(reduce(operator.or_, [
            Q(title__icontains=t) | Q(description__icontains=t) | Q(brand__icontains=t) | Q(color__icontains=t)
            for t in terms]))
        parts = [Case(When(title__icontains=t, then=Value(3)), When(description__icontains=t, then=Value(1)),
                      default=Value(0), output_field=IntegerField()) for t in terms]
        relevance = reduce(operator.add, parts)
    if params.get("type") in ("lost", "found"):
        qs = qs.filter(type=params["type"])
    if params.get("category"):
        qs = qs.filter(category_id=params["category"])
    if params.get("location"):
        qs = qs.filter(location_id=params["location"])
    if params.get("status"):
        qs = qs.filter(status=params["status"])
    if params.get("date_from"):
        qs = qs.filter(date__gte=params["date_from"])
    if params.get("date_to"):
        qs = qs.filter(date__lte=params["date_to"])
    if params.get("ordering") == "relevance" and relevance is not None:
        qs = qs.annotate(relevance=relevance).order_by("-relevance", "-created_at")
    else:
        qs = qs.order_by("-created_at", "-id")
    return qs
