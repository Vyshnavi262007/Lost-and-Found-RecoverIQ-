from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.core.site_settings import get_setting


class Command(BaseCommand):
    help = "Mark open reports older than the configured expiry (admin setting) as expired."

    def handle(self, *args, **options):
        from apps.reports.models import ItemReport
        days = get_setting("report_expiry_days")
        cutoff = timezone.now() - timedelta(days=days)
        n = ItemReport.objects.filter(status="open", held_by_staff=False, created_at__lt=cutoff).update(status="expired")
        self.stdout.write(f"Expired {n} reports older than {days} days.")
