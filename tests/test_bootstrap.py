"""Smoke tests for Django bootstrap and basic configuration."""

from django.apps import apps
from django.conf import settings
from django.urls import reverse


class TestSettingsLoading:
    """Test that Django settings load correctly without domain apps."""

    def test_settings_module_is_test(self):
        """Verify settings module is config.settings.test."""
        assert settings.SETTINGS_MODULE == "config.settings.test"

    def test_secret_key_is_set(self):
        """Verify SECRET_KEY is loaded from environment."""
        assert settings.SECRET_KEY is not None
        assert len(settings.SECRET_KEY) > 0

    def test_database_is_configured(self):
        """Verify PostgreSQL database is configured."""
        assert "default" in settings.DATABASES
        assert settings.DATABASES["default"]["ENGINE"] == "django.db.backends.postgresql"

    def test_installed_apps_contains_core_apps(self):
        """Verify core Django apps are installed."""
        installed = [app.name for app in apps.get_app_configs()]
        assert "django.contrib.admin" in installed or "admin" in installed
        assert "django.contrib.auth" in installed or "auth" in installed
        assert "rest_framework" in installed or "rest_framework" in installed

    def test_no_domain_apps_installed(self):
        """Verify no unauthorized domain apps are installed."""
        installed = [app.name for app in apps.get_app_configs()]
        # users is expected after PIL-BE-ACE-001; organizational added after PIL-BE-ACE-002, etc.
        domain_apps = [
            "organizational",
            "materials",
            "stock",
            "requisitions",
            "approvals",
            "warehouse",
            "notifications",
            "imports",
            "audit",
            "reports",
        ]
        for app in domain_apps:
            assert not any(app in name for name in installed), (
                f"Domain app '{app}' should not be installed yet"
            )

    def test_drf_is_configured(self):
        """Verify Django REST Framework is configured."""
        assert "rest_framework" in settings.INSTALLED_APPS or any(
            "rest_framework" in str(app) for app in settings.INSTALLED_APPS
        )
        assert settings.REST_FRAMEWORK is not None


class TestURLLoading:
    """Test that URL configuration loads correctly."""

    def test_admin_url_is_accessible(self):
        """Verify admin URL is accessible."""
        admin_url = reverse("admin:index")
        assert admin_url == "/admin/"

    def test_root_urls_load(self):
        """Verify root URLconf loads without errors."""
        from config import urls

        assert urls.urlpatterns is not None
        assert len(urls.urlpatterns) > 0


class TestDjangoCheck:
    """Test that Django check command passes."""

    def test_django_setup_succeeds(self):
        """Verify Django setup completes without errors."""
        from django.core.management import call_command

        call_command("check", verbosity=0)
