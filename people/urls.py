from django.urls import path
from . import views

app_name = "people"

urlpatterns = [
    path("contractor/onboarding/", views.contractor_onboarding, name="contractor_onboarding"),
    path("contractor/nda/send/", views.send_nda, name="send_nda"),
    path("contractor/nda/sign/", views.nda_sign, name="nda_sign"),
    path("contractor/nda/sign/submit/", views.sign_nda, name="sign_nda"),
    path("contractor/w9/upload/", views.upload_w9, name="upload_w9"),
    path("onboarding/w9/docusign/start/", views.start_w9_docusign, name="start_w9_docusign"),
]



