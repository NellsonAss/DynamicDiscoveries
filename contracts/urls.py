from django.urls import path
from . import views

app_name = "contracts"

urlpatterns = [
    path("webhook", views.docusign_webhook, name="webhook"),
    path("return", views.return_view, name="return"),
]



