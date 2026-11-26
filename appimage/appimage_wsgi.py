import setuptools
from django.contrib.staticfiles.handlers import StaticFilesHandler
from django.core.wsgi import get_wsgi_application

application = StaticFilesHandler(get_wsgi_application())
