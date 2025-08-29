from django.urls import re_path

from . import views

urlpatterns = [
    re_path(r"^_pretix_pix_openpix/webhook/", views.webhook, name="webhook"),
]
