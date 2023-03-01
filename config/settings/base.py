"""
Base settings to build other settings files upon.
"""
from pathlib import Path

import environ

ROOT_DIR = Path(__file__).resolve(strict=True).parent.parent.parent
# ryft/
APPS_DIR = ROOT_DIR / "ryft"
env = environ.Env()

READ_DOT_ENV_FILE = env.bool("DJANGO_READ_DOT_ENV_FILE", default=False)
if READ_DOT_ENV_FILE:
    DJANGO_ENV_FILE_LOCATION = env("DJANGO_ENV_FILE_LOCATION", default="")
    # OS environment variables take precedence over variables from .env
    if DJANGO_ENV_FILE_LOCATION:
        env.read_env(str(ROOT_DIR / DJANGO_ENV_FILE_LOCATION))
    else:
        env.read_env(str(ROOT_DIR / ".env"))

# GENERAL
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#debug
DEBUG = env.bool("DJANGO_DEBUG", False)
# Local time zone. Choices are
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# though not all of them may be available with every OS.
# In Windows, this must be set to your system time zone.
TIME_ZONE = "Europe/Budapest"
# https://docs.djangoproject.com/en/dev/ref/settings/#language-code
LANGUAGE_CODE = "en-us"
# https://docs.djangoproject.com/en/dev/ref/settings/#site-id
SITE_ID = 1
# https://docs.djangoproject.com/en/dev/ref/settings/#use-i18n
USE_I18N = True
# https://docs.djangoproject.com/en/dev/ref/settings/#use-l10n
USE_L10N = True
# https://docs.djangoproject.com/en/dev/ref/settings/#use-tz
USE_TZ = True
# https://docs.djangoproject.com/en/dev/ref/settings/#locale-paths
LOCALE_PATHS = [str(ROOT_DIR / "locale")]

# DATABASES
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#databases
DATABASES = {"default": env.db("DATABASE_URL")}
DATABASES["default"]["ATOMIC_REQUESTS"] = True
# https://docs.djangoproject.com/en/stable/ref/settings/#std:setting-DEFAULT_AUTO_FIELD
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# URLS
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#root-urlconf
ROOT_URLCONF = "config.urls"
# https://docs.djangoproject.com/en/dev/ref/settings/#wsgi-application
WSGI_APPLICATION = "config.wsgi.application"

# APPS
# ------------------------------------------------------------------------------
DJANGO_APPS = [
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.sites",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # "django.contrib.humanize", # Handy template tags
    "django.contrib.admin",
    "django.forms",
]
THIRD_PARTY_APPS = [
    "crispy_forms",
    "crispy_bootstrap5",
    # "allauth",
    # "allauth.account",
    # "allauth.socialaccount",
    "django_celery_beat",
    "rest_framework",
    "rest_framework.authtoken",
    # "dj_rest_auth",
    # "dj_rest_auth.registration",
    "corsheaders",
    "drf_spectacular",
    "django_filters",
    "siwe_auth.apps.SiweAuthConfig",
]

LOCAL_APPS = [
    # "ryft.users",
    "ryft.core",
    # Your stuff: custom apps go here
]
# https://docs.djangoproject.com/en/dev/ref/settings/#installed-apps
INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

# MIGRATIONS
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#migration-modules
MIGRATION_MODULES = {"sites": "ryft.contrib.sites.migrations"}

# AUTHENTICATION
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#authentication-backends
AUTHENTICATION_BACKENDS = [
    # "django.contrib.auth.backends.ModelBackend",
    # "allauth.account.auth_backends.AuthenticationBackend",
    "siwe_auth.backend.SiweBackend",
    "ryft.core.backend.SiweBackend",
    "ryft.core.backend.DiscordAuthenticationBackend",
]
# https://docs.djangoproject.com/en/dev/ref/settings/#auth-user-model

AUTH_USER_MODEL = "siwe_auth.Wallet"
SESSION_COOKIE_AGE = 2419200
SESSION_COOKIE_SAMESITE = "none"
SESSION_COOKIE_SECURE = True
CREATE_GROUPS_ON_AUTHN = True
CREATE_ENS_PROFILE_ON_AUTHN = True
RYFT_CONTRACT_ADDRESS = env("RYFT_CONTRACT_ADDRESS")

# TODO when launch
CUSTOM_GROUPS = [
    # (
    #     "ryft",
    #     ERC721OwnerManager(
    #         config={"contract": RYFT_CONTRACT_ADDRESS}
    #     ),
    # ),
]

# Set environment variable with your provider or use default
INFURA_PROJECT_ID = env("INFURA_PROJECT_ID")
PROVIDER = f"https://mainnet.infura.io/v3/{INFURA_PROJECT_ID}"

# https://docs.djangoproject.com/en/dev/ref/settings/#login-redirect-url
# LOGIN_REDIRECT_URL = "users:redirect"
# https://docs.djangoproject.com/en/dev/ref/settings/#login-url
# LOGIN_URL = "account_login"

# PASSWORDS
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#password-hashers
PASSWORD_HASHERS = [
    # https://docs.djangoproject.com/en/dev/topics/auth/passwords/#using-argon2-with-django
    "django.contrib.auth.hashers.Argon2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2SHA1PasswordHasher",
    "django.contrib.auth.hashers.BCryptSHA256PasswordHasher",
]
# https://docs.djangoproject.com/en/dev/ref/settings/#auth-password-validators
AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"
    },
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# MIDDLEWARE
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#middleware
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "django.middleware.common.CommonMiddleware",
    # "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.common.BrokenLinkEmailsMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "ryft.core.middleware.SaveRequest",
]

# STATIC
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#static-root
STATIC_ROOT = str(ROOT_DIR / "staticfiles")
# https://docs.djangoproject.com/en/dev/ref/settings/#static-url
STATIC_URL = "/static/"
# https://docs.djangoproject.com/en/dev/ref/contrib/staticfiles/#std:setting-STATICFILES_DIRS
STATICFILES_DIRS = [str(APPS_DIR / "static")]
# https://docs.djangoproject.com/en/dev/ref/contrib/staticfiles/#staticfiles-finders
STATICFILES_FINDERS = [
    "django.contrib.staticfiles.finders.FileSystemFinder",
    "django.contrib.staticfiles.finders.AppDirectoriesFinder",
]

# MEDIA
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#media-root
MEDIA_ROOT = str(APPS_DIR / "media")
# https://docs.djangoproject.com/en/dev/ref/settings/#media-url
MEDIA_URL = "/media/"

# TEMPLATES
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#templates
TEMPLATES = [
    {
        # https://docs.djangoproject.com/en/dev/ref/settings/#std:setting-TEMPLATES-BACKEND
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        # https://docs.djangoproject.com/en/dev/ref/settings/#dirs
        "DIRS": [str(APPS_DIR / "templates")],
        # https://docs.djangoproject.com/en/dev/ref/settings/#app-dirs
        "APP_DIRS": True,
        "OPTIONS": {
            # https://docs.djangoproject.com/en/dev/ref/settings/#template-context-processors
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.template.context_processors.i18n",
                "django.template.context_processors.media",
                "django.template.context_processors.static",
                "django.template.context_processors.tz",
                "django.contrib.messages.context_processors.messages",
                "ryft.users.context_processors.allauth_settings",
            ],
        },
    }
]

# https://docs.djangoproject.com/en/dev/ref/settings/#form-renderer
FORM_RENDERER = "django.forms.renderers.TemplatesSetting"

# http://django-crispy-forms.readthedocs.io/en/latest/install.html#template-packs
CRISPY_TEMPLATE_PACK = "bootstrap5"
CRISPY_ALLOWED_TEMPLATE_PACKS = "bootstrap5"

# FIXTURES
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#fixture-dirs
FIXTURE_DIRS = (str(APPS_DIR / "fixtures"),)

# SECURITY
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#session-cookie-httponly
SESSION_COOKIE_HTTPONLY = True
# https://docs.djangoproject.com/en/dev/ref/settings/#csrf-cookie-httponly
CSRF_COOKIE_HTTPONLY = True
# https://docs.djangoproject.com/en/dev/ref/settings/#secure-browser-xss-filter
SECURE_BROWSER_XSS_FILTER = True
# https://docs.djangoproject.com/en/dev/ref/settings/#x-frame-options
X_FRAME_OPTIONS = "DENY"

# EMAIL
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#email-backend
EMAIL_BACKEND = env(
    "DJANGO_EMAIL_BACKEND",
    default="django.core.mail.backends.smtp.EmailBackend",
)
# https://docs.djangoproject.com/en/dev/ref/settings/#email-timeout
EMAIL_TIMEOUT = 5

# ADMIN
# ------------------------------------------------------------------------------
# Django Admin URL.
ADMIN_URL = "admin/"
# https://docs.djangoproject.com/en/dev/ref/settings/#admins
ADMINS = [("""Ryft""", "ryft@example.com")]
# https://docs.djangoproject.com/en/dev/ref/settings/#managers
MANAGERS = ADMINS

# LOGGING
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#logging
# See https://docs.djangoproject.com/en/dev/topics/logging for
# more details on how to customize your logging configuration.
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "%(levelname)s %(asctime)s %(module)s "
            "%(process)d %(thread)d %(message)s"
        }
    },
    "handlers": {
        "console": {
            "level": "DEBUG",
            "class": "logging.StreamHandler",
            "formatter": "verbose",
        }
    },
    "root": {"level": "INFO", "handlers": ["console"]},
}

# Celery
# ------------------------------------------------------------------------------
if USE_TZ:
    # https://docs.celeryq.dev/en/stable/userguide/configuration.html#std:setting-timezone
    CELERY_TIMEZONE = TIME_ZONE
# https://docs.celeryq.dev/en/stable/userguide/configuration.html#std:setting-broker_url
CELERY_BROKER_URL = env("CELERY_BROKER_URL")
# https://docs.celeryq.dev/en/stable/userguide/configuration.html#std:setting-result_backend
CELERY_RESULT_BACKEND = CELERY_BROKER_URL
# https://docs.celeryq.dev/en/stable/userguide/configuration.html#std:setting-accept_content
CELERY_ACCEPT_CONTENT = ["json"]
# https://docs.celeryq.dev/en/stable/userguide/configuration.html#std:setting-task_serializer
CELERY_TASK_SERIALIZER = "json"
# https://docs.celeryq.dev/en/stable/userguide/configuration.html#std:setting-result_serializer
CELERY_RESULT_SERIALIZER = "json"
# https://docs.celeryq.dev/en/stable/userguide/configuration.html#task-time-limit
# TODO: set to whatever value is adequate in your circumstances
CELERY_TASK_TIME_LIMIT = 20000 * 60
# https://docs.celeryq.dev/en/stable/userguide/configuration.html#task-soft-time-limit
# TODO: set to whatever value is adequate in your circumstances
CELERY_TASK_SOFT_TIME_LIMIT = 10000 * 60
# https://docs.celeryq.dev/en/stable/userguide/configuration.html#beat-scheduler
CELERY_BEAT_SCHEDULER = "django_celery_beat.schedulers:DatabaseScheduler"

# https://github.com/danihodovic/celery-exporter
CELERY_WORKER_SEND_TASK_EVENTS = True
CELERY_TASK_SEND_SENT_EVENT = True

CELERY_ROUTES = {
    "ryft.core.portfolio.tasks.create_wallet_webhook": {"queue": "long"},
    "ryft.core.portfolio.tasks.get_wallet_nfts": {"queue": "long"},
    "ryft.core.portfolio.tasks.calculate_portfolio_total": {"queue": "long"},
    "ryft.core.portfolio.tasks.create_wallet_nfts": {"queue": "long"},
    "ryft.core.portfolio.tasks.fetch_individual_wallet_transactions": {"queue": "long"},
    "ryft.core.portfolio.tasks.check_wallet_access": {"queue": "long"},
    "ryft.core.portfolio.tasks.save_final_wallet_details": {"queue": "long"},
    "ryft.core.portfolio.tasks.save_tracked_wallet_thumbnail": {"queue": "long"},
    "ryft.core.tasks.fetch_nfts": {"queue": "default"},
    "ryft.core.tasks.create_nft_attributes": {"queue": "default"},
    "ryft.core.tasks.rank_nfts": {"queue": "default"},
    "ryft.core.tasks.link_nfts_to_transactions": {"queue": "default"},
    "ryft.core.tasks.link_nfts_to_wallets": {"queue": "default"},
    "ryft.core.portfolio.tasks.fetch_collection_metrics": {"queue": "default"},
    "ryft.core.portfolio.tasks.fetch_collection_owners_history": {"queue": "default"},
    "ryft.core.portfolio.tasks.fetch_collection_price_history": {"queue": "default"},
    "ryft.core.portfolio.tasks.fetch_collections_transfers": {"queue": "default"},
    "ryft.core.portfolio.tasks.fetch_eth_price": {"queue": "default"},
    "ryft.core.portfolio.tasks.fetch_trending_collections": {"queue": "default"},
}
CELERY_TASK_DEFAULT_QUEUE = "default"

CELERY_BEAT_SCHEDULE = {
    # "fetch-collection-metrics-every-day": {
    #     "task": "fetch_collection_metrics",
    #     "schedule": crontab(hour="0"),
    #     "args": (),
    #     "options": {
    #         "expires": 15.0,
    #     },
    # },
    # "daily-wallet-task": {
    #     "task": "daily_wallet_task",
    #     "schedule": crontab(hour="2"),
    #     "args": (),
    #     "options": {
    #         "expires": 15.0,
    #     },
    # },
    # "daily-collection-owners": {
    #     "task": "fetch_collection_owners_history",
    #     "schedule": crontab(minute=0, hour="0"),
    #     "args": (),
    #     "options": {
    #         "expires": 15.0,
    #     },
    # },
    # "daily-collection-prices": {
    #     "task": "fetch_collection_price_history",
    #     "schedule": crontab(minute=0, hour="1"),
    #     "args": (),
    #     "options": {
    #         "expires": 15.0,
    #     },
    # },
    # "collection-email": {
    #     "task": "send_daily_collection_email",
    #     "schedule": crontab(minute=0, hour="0"),
    #     "args": (),
    #     "options": {
    #         "expires": 15.0,
    #     },
    # },
    # "collection-last-block-transfers": {
    #     "task": "fetch_collections_transfers",
    #     "schedule": crontab(minute=0, hour="*/1"),
    #     "args": (),
    #     "options": {
    #         "expires": 15.0,
    #     },
    # },
    # "trending-collections": {
    #     "task": "fetch_trending_collections",
    #     "schedule": crontab(minute=0, hour="*/2"),
    #     "args": (),
    #     "options": {
    #         "expires": 15.0,
    #     },
    # },
    # TODO launch when live
    # "hourly-check-ryft-owners": {
    #     "task": "fetch_ryft_owners_task",
    #     "schedule": crontab(minute=0, hour="*/1"),
    #     "args": (),
    #     "options": {
    #         "expires": 15.0,
    #     },
    # },
}

# django-allauth
# ------------------------------------------------------------------------------
# ACCOUNT_USER_MODEL_USERNAME_FIELD = None
ACCOUNT_ALLOW_REGISTRATION = env.bool("DJANGO_ACCOUNT_ALLOW_REGISTRATION", True)
# # https://django-allauth.readthedocs.io/en/latest/configuration.html
# ACCOUNT_AUTHENTICATION_METHOD = "email"
# # https://django-allauth.readthedocs.io/en/latest/configuration.html
# ACCOUNT_EMAIL_REQUIRED = True
# ACCOUNT_UNIQUE_EMAIL = True
# ACCOUNT_USERNAME_REQUIRED = False
# # https://django-allauth.readthedocs.io/en/latest/configuration.html
# ACCOUNT_EMAIL_VERIFICATION = "mandatory"
# # https://django-allauth.readthedocs.io/en/latest/configuration.html
# ACCOUNT_ADAPTER = "ryft.users.adapters.AccountAdapter"
# # https://django-allauth.readthedocs.io/en/latest/forms.html
# ACCOUNT_FORMS = {"signup": "ryft.users.forms.UserSignupForm"}
# # https://django-allauth.readthedocs.io/en/latest/configuration.html
# SOCIALACCOUNT_ADAPTER = "ryft.users.adapters.SocialAccountAdapter"
# # https://django-allauth.readthedocs.io/en/latest/forms.html
# SOCIALACCOUNT_FORMS = {"signup": "ryft.users.forms.UserSocialSignupForm"}

# django-rest-framework
# -------------------------------------------------------------------------------
# django-rest-framework - https://www.django-rest-framework.org/api-guide/settings/
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework.authentication.SessionAuthentication",
        "rest_framework.authentication.TokenAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": ("rest_framework.permissions.IsAuthenticated",),
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_FILTER_BACKENDS": ["django_filters.rest_framework.DjangoFilterBackend"],
}

# REST_AUTH_SERIALIZERS = {
#     "LOGIN_SERIALIZER": "ryft.users.api.serializers.CustomLoginSerializer",
#     "TOKEN_SERIALIZER": "ryft.users.api.serializers.CustomTokenSerializer",
# }
#
# REST_AUTH_REGISTER_SERIALIZERS = {
#     "REGISTER_SERIALIZER": "ryft.users.api.serializers.CustomRegisterSerializer",
# }


# django-cors-headers - https://github.com/adamchainz/django-cors-headers#setup
# CORS_URLS_REGEX = r"^/api/.*$"
CORS_ORIGIN_ALLOW_ALL = True
CORS_ALLOW_CREDENTIALS = True

# By Default swagger ui is available only to admin user(s). You can change permission classes to change that
# See more configuration options at https://drf-spectacular.readthedocs.io/en/latest/settings.html#settings
SPECTACULAR_SETTINGS = {
    "TITLE": "Ryft API",
    "DESCRIPTION": "Documentation of API endpoints of Ryft",
    "VERSION": "1.0.0",
    "SERVE_PERMISSIONS": ["rest_framework.permissions.IsAdminUser"],
    "SERVERS": [
        {"url": "http://127.0.0.1:8000", "description": "Local Development server"},
        {"url": "https://api.ryftpass.io", "description": "Production server"},
    ],
}
# Your stuff...
# ------------------------------------------------------------------------------

# Alchemy
# --
ALCHEMY_API_KEY = env("ALCHEMY_API_KEY")
ALCHEMY_AUTH_TOKEN = env("ALCHEMY_AUTH_TOKEN")
ALCHEMY_WEBHOOK_KEY = env("ALCHEMY_WEBHOOK_KEY")
ALCHEMY_WEBHOOK_WALLET_ACTIVITY_ID = env("ALCHEMY_WEBHOOK_WALLET_ACTIVITY_ID")

# NFTPort
# --
NFTPORT_API_KEY = env("NFTPORT_API_KEY")

# Email
# --
SUPPORT_EMAIL = env("SUPPORT_EMAIL", default="ryftpass@gmail.com")

# Frontend (Not being used anymore)
# ---
FRONTEND_URL = env("FRONTEND_URL", default="http://127.0.0.1:8000")

# Mnemonic
# --
MNEMONIC_API_KEY = env("MNEMONIC_API_KEY")

# Graph Json
# --
GRAPH_JSON_API_KEY = env("GRAPH_JSON_API_KEY")

# Admin wallets
# --
ADMIN_WALLETS = env.list("ADMIN_WALLETS", default=[])

# Request logging
# --
REQUEST_LOG_FILTERED_PATHS = env.list("REQUEST_LOG_FILTERED_PATHS", default=[])

# Discord OAuth2
# --
DISCORD_APP_CLIENT_ID = env("DISCORD_APP_CLIENT_ID")
DISCORD_APP_CLIENT_SECRET = env("DISCORD_APP_CLIENT_SECRET")
DISCORD_BOT_TOKEN = env("DISCORD_BOT_TOKEN")

# Discord Server
# --
RYFT_DISCORD_SERVER_ID = env("RYFT_DISCORD_SERVER_ID")
RYFT_DISCORD_BETA_USER_ROLE_ID = env("RYFT_DISCORD_BETA_USER_ROLE_ID")
