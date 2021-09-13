from django.http import HttpResponse
from django.urls import path

from django.conf import settings
from django.utils.http import urlencode

def provider_logout(request):
    logout_url = settings.OIDC_OP_LOGOUT_ENDPOINT
    redirect_uri = request.build_absolute_uri(settings.LOGOUT_REDIRECT_URL)
    return logout_url + '?' + urlencode({'redirect_uri': redirect_uri})