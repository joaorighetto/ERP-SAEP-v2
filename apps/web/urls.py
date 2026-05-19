from django.urls import path

from apps.web.views import home as home_views

app_name = "web"

urlpatterns = [
    path("", home_views.HomeView.as_view(), name="home"),
]
