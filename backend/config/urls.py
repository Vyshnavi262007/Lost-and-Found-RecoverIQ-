from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("django-admin/", admin.site.urls),
    path("api/", include("apps.accounts.urls")),
    path("api/", include("apps.core.urls")),
    path("api/", include("apps.reports.urls")),
    path("api/", include("apps.messaging.urls")),
    path("api/", include("apps.claims.urls")),
    path("api/", include("apps.adminapi.urls")),
]
if settings.DEBUG:  # public item photos only; claim evidence is never served this way
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
