from django.conf import settings
from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from rest_framework.permissions import AllowAny

schema_view_kwargs = {}
if settings.DEBUG:
    schema_view_kwargs["permission_classes"] = [AllowAny]

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/v1/", include("apps.users.urls")),
    path("api/v1/", include("apps.materials.urls")),
    path("api/v1/", include("apps.requisitions.urls")),
    path(
        "api/v1/schema/",
        SpectacularAPIView.as_view(**schema_view_kwargs),
        name="schema",
    ),
    path(
        "api/v1/docs/",
        SpectacularSwaggerView.as_view(url_name="schema", **schema_view_kwargs),
        name="swagger-ui",
    ),
]
