from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from django.views import defaults as default_views
from django.views.generic import TemplateView
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from siwe_auth.views import login as siwe_login

from ryft.core.api.views import (
    IsBetaUserView,
    UserWhitelistView,
    wallet_activity_webhook,
)
from ryft.core.views import (
    discord_callback,
    discord_connect_view,
    discord_login,
    discord_login_view,
    get_authenticated_user,
    index,
    login,
    logout,
    nonce,
    siwe_message,
)

urlpatterns = [
    path("", include("django_prometheus.urls")),
    path("", TemplateView.as_view(template_name="pages/home.html"), name="home"),
    path("app/", index),
    path(
        "about/", TemplateView.as_view(template_name="pages/about.html"), name="about"
    ),
    # Django Admin, use {% url 'admin:index' %}
    path(settings.ADMIN_URL, admin.site.urls),
    # User management
    path("users/", include("ryft.users.urls", namespace="users")),
    # path("accounts/", include("allauth.urls")),
    path("webhooks/alchemy/wallet-activity/", wallet_activity_webhook),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

# API URLS
urlpatterns += [
    # API auth
    path("api/auth/custom-login/", login),
    path("api/auth/logout/", logout),
    path("api/auth/message/", siwe_message),
    path("api/auth/nonce/", nonce),
    path("api/auth/login", siwe_login),
    # path("api/auth/", include("siwe_auth.urls")),
    # Discord auth
    path("auth/user", get_authenticated_user, name="get_authenticated_user"),
    path("api/oauth2/login/", discord_login, name="oauth_login"),
    path(
        "api/oauth2/callback/discord/login/",
        discord_callback,
        name="discord_login_redirect",
    ),
    path(
        "api/oauth2/callback/discord/connect/",
        discord_connect_view,
        name="discord_connect_redirect",
    ),
    path("api/oauth2/app/discord/login/", discord_login_view),
    # check beta user
    path("api/v1/check-beta-user/", IsBetaUserView.as_view(), name="check-beta"),
    path(
        "api/user/collections/whitelisted/",
        UserWhitelistView.as_view(),
    ),
    # API base url
    path("api/", include("config.api_router")),
    # DRF auth token
    # path("auth-token/", obtain_auth_token),
    path("api/schema/", SpectacularAPIView.as_view(), name="api-schema"),
    path(
        "api/docs/",
        SpectacularSwaggerView.as_view(url_name="api-schema"),
        name="api-docs",
    ),
]

if settings.DEBUG:
    # This allows the error pages to be debugged during development, just visit
    # these url in browser to see how these error pages look like.
    urlpatterns += [
        path(
            "400/",
            default_views.bad_request,
            kwargs={"exception": Exception("Bad Request!")},
        ),
        path(
            "403/",
            default_views.permission_denied,
            kwargs={"exception": Exception("Permission Denied")},
        ),
        path(
            "404/",
            default_views.page_not_found,
            kwargs={"exception": Exception("Page not Found")},
        ),
        path("500/", default_views.server_error),
    ]
    if "debug_toolbar" in settings.INSTALLED_APPS:
        import debug_toolbar

        urlpatterns = [path("__debug__/", include(debug_toolbar.urls))] + urlpatterns
