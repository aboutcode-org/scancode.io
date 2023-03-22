# SPDX-License-Identifier: Apache-2.0
#
# http://nexb.com and https://github.com/nexB/scancode.io
# The ScanCode.io software is licensed under the Apache License version 2.0.
# Data generated with ScanCode.io is provided as-is without warranties.
# ScanCode is a trademark of nexB Inc.
#
# You may not use this software except in compliance with the License.
# You may obtain a copy of the License at: http://apache.org/licenses/LICENSE-2.0
# Unless required by applicable law or agreed to in writing, software distributed
# under the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR
# CONDITIONS OF ANY KIND, either express or implied. See the License for the
# specific language governing permissions and limitations under the License.
#
# Data Generated with ScanCode.io is provided on an "AS IS" BASIS, WITHOUT WARRANTIES
# OR CONDITIONS OF ANY KIND, either express or implied. No content created from
# ScanCode.io should be considered or used as legal advice. Consult an Attorney
# for any legal advice.
#
# ScanCode.io is a free software code scanning tool from nexB Inc. and others.
# Visit https://github.com/nexB/scancode.io for support and download.

import sys
import tempfile
from pathlib import Path

import environ

PROJECT_DIR = environ.Path(__file__) - 1
ROOT_DIR = PROJECT_DIR - 1

# Environment

ENV_FILE = "/etc/scancodeio/.env"
if not Path(ENV_FILE).exists():
    ENV_FILE = ROOT_DIR(".env")

env = environ.Env()
environ.Env.read_env(ENV_FILE)

# Security

SECRET_KEY = env.str("SECRET_KEY")

ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", default=[".localhost", "127.0.0.1", "[::1]"])

CSRF_TRUSTED_ORIGINS = env.list("CSRF_TRUSTED_ORIGINS", default=[])

# SECURITY WARNING: don't run with debug turned on in production
DEBUG = env.bool("SCANCODEIO_DEBUG", default=False)

SCANCODEIO_REQUIRE_AUTHENTICATION = env.bool(
    "SCANCODEIO_REQUIRE_AUTHENTICATION", default=False
)

# ScanCode.io

SCANCODEIO_WORKSPACE_LOCATION = env.str("SCANCODEIO_WORKSPACE_LOCATION", default="var")

SCANCODE_TOOLKIT_CLI_OPTIONS = env.list("SCANCODE_TOOLKIT_CLI_OPTIONS", default=[])

SCANCODEIO_LOG_LEVEL = env.str("SCANCODEIO_LOG_LEVEL", "INFO")

# Set the number of parallel processes to use for ScanCode related scan execution.
# If the SCANCODEIO_PROCESSES argument is not set, defaults to an optimal number of CPUs
# available on the machine.
SCANCODEIO_PROCESSES = env.int("SCANCODEIO_PROCESSES", default=None)

SCANCODEIO_POLICIES_FILE = env.str("SCANCODEIO_POLICIES_FILE", default="policies.yml")

# This setting defines the additional locations ScanCode.io will search for pipelines.
# This should be set to a list of strings that contain full paths to your additional
# pipelines directories.
SCANCODEIO_PIPELINES_DIRS = env.list("SCANCODEIO_PIPELINES_DIRS", default=[])

# Maximum time allowed for a pipeline to complete.
SCANCODEIO_TASK_TIMEOUT = env.str("SCANCODEIO_TASK_TIMEOUT", default="24h")

# Default to 2 minutes.
SCANCODEIO_SCAN_FILE_TIMEOUT = env.int("SCANCODEIO_SCAN_FILE_TIMEOUT", default=120)

# List views pagination, controls the number of items displayed per page.
# Syntax in .env: SCANCODEIO_PAGINATE_BY=project=10,project_error=10
SCANCODEIO_PAGINATE_BY = env.dict(
    "SCANCODEIO_PAGINATE_BY",
    default={
        "project": 20,
        "error": 50,
        "resource": 100,
        "package": 100,
        "dependency": 100,
    },
)

# Default limit for "most common" entries in QuerySets.
SCANCODEIO_MOST_COMMON_LIMIT = env.int("SCANCODEIO_MOST_COMMON_LIMIT", default=7)

# Application definition

INSTALLED_APPS = (
    # Local apps
    # Must come before Third-party apps for proper templates override
    "scanpipe",
    # Django built-in
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.admin",
    "django.contrib.humanize",
    # Third-party apps
    "crispy_forms",
    "crispy_bootstrap3",  # required for the djangorestframework browsable API
    "django_filters",
    "rest_framework",
    "rest_framework.authtoken",
    "django_rq",
    "django_probes",
)

MIDDLEWARE = (
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
)

ROOT_URLCONF = "scancodeio.urls"

WSGI_APPLICATION = "scancodeio.wsgi.application"

SECURE_PROXY_SSL_HEADER = env.tuple(
    "SECURE_PROXY_SSL_HEADER", default=("HTTP_X_FORWARDED_PROTO", "https")
)

# Database

DATABASES = {
    "default": {
        "ENGINE": env.str("SCANCODEIO_DB_ENGINE", "django.db.backends.postgresql"),
        "HOST": env.str("SCANCODEIO_DB_HOST", "localhost"),
        "NAME": env.str("SCANCODEIO_DB_NAME", "scancodeio"),
        "USER": env.str("SCANCODEIO_DB_USER", "scancodeio"),
        "PASSWORD": env.str("SCANCODEIO_DB_PASSWORD", "scancodeio"),
        "PORT": env.str("SCANCODEIO_DB_PORT", "5432"),
        "ATOMIC_REQUESTS": True,
    }
}

DEFAULT_AUTO_FIELD = "django.db.models.AutoField"

# Templates

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "APP_DIRS": True,
        "OPTIONS": {
            "debug": DEBUG,
            "context_processors": [
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "django.template.context_processors.request",
                "scancodeio.context_processors.versions",
            ],
        },
    },
]

# Login

LOGIN_REDIRECT_URL = "project_list"

# Passwords

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
        "OPTIONS": {
            "min_length": env.int("SCANCODEIO_PASSWORD_MIN_LENGTH", default=12),
        },
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]

# Testing

# True if running tests through `./manage test`
IS_TESTS = "test" in sys.argv

if IS_TESTS:
    # Do not pollute the workspace while running the tests
    SCANCODEIO_WORKSPACE_LOCATION = tempfile.mkdtemp()
    SCANCODEIO_REQUIRE_AUTHENTICATION = True
    SCANCODEIO_SCAN_FILE_TIMEOUT = 120

# Cache

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "default",
    },
    "scan_results": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "scan",
        "TIMEOUT": 86_400,  # 1 day
        "OPTIONS": {
            # Maximum entries allowed in the cache before old values are deleted
            "MAX_ENTRIES": 1_000_000,
        },
    },
}

# Logging

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "simple": {
            "format": "{levelname} {message}",
            "style": "{",
        },
    },
    "handlers": {
        "null": {
            "class": "logging.NullHandler",
        },
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "simple",
        },
    },
    "loggers": {
        "scanpipe": {
            "handlers": ["null"] if IS_TESTS else ["console"],
            "level": SCANCODEIO_LOG_LEVEL,
            "propagate": False,
        },
        "django": {
            "handlers": ["null"] if IS_TESTS else ["console"],
            "propagate": False,
        },
        # Set SCANCODEIO_LOG_LEVEL=DEBUG to display all SQL queries in the console.
        "django.db.backends": {
            "level": SCANCODEIO_LOG_LEVEL,
        },
    },
}

# Instead of sending out real emails the console backend just writes the emails
# that would be sent to the standard output.
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

# Internationalization

LANGUAGE_CODE = "en-us"

TIME_ZONE = env.str("TIME_ZONE", default="UTC")

USE_I18N = True

USE_TZ = True

# Static files (CSS, JavaScript, Images)

STATIC_URL = "/static/"

STATIC_ROOT = "/var/scancodeio/static/"

STATICFILES_DIRS = [
    PROJECT_DIR("static"),
]

# Third-party apps

CRISPY_TEMPLATE_PACK = "bootstrap3"

# Job Queue

RQ_QUEUES = {
    "default": {
        "HOST": env.str("SCANCODEIO_REDIS_HOST", default="localhost"),
        "PORT": env.str("SCANCODEIO_REDIS_PORT", default="6379"),
        "PASSWORD": env.str("SCANCODEIO_REDIS_PASSWORD", default=""),
        "DEFAULT_TIMEOUT": env.int("SCANCODEIO_REDIS_DEFAULT_TIMEOUT", default=360),
    },
}

SCANCODEIO_ASYNC = env.bool("SCANCODEIO_ASYNC", default=False)
if not SCANCODEIO_ASYNC:
    for queue_config in RQ_QUEUES.values():
        queue_config["ASYNC"] = False

# Django restframework

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework.authentication.TokenAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": ("rest_framework.permissions.IsAuthenticated",),
    "DEFAULT_RENDERER_CLASSES": (
        "rest_framework.renderers.JSONRenderer",
        "rest_framework.renderers.BrowsableAPIRenderer",
        "rest_framework.renderers.AdminRenderer",
    ),
    "DEFAULT_FILTER_BACKENDS": (
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.SearchFilter",
    ),
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": env.int("SCANCODEIO_REST_API_PAGE_SIZE", default=50),
    "UPLOADED_FILES_USE_URL": False,
}

if not SCANCODEIO_REQUIRE_AUTHENTICATION:
    REST_FRAMEWORK["DEFAULT_PERMISSION_CLASSES"] = (
        "rest_framework.permissions.AllowAny",
    )

# VulnerableCode integration

VULNERABLECODE_URL = env.str("VULNERABLECODE_URL", default="")
VULNERABLECODE_USER = env.str("VULNERABLECODE_USER", default="")
VULNERABLECODE_PASSWORD = env.str("VULNERABLECODE_PASSWORD", default="")
VULNERABLECODE_API_KEY = env.str("VULNERABLECODE_API_KEY", default="")
