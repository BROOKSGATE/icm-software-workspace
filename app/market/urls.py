from django.urls import path

from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("signup/", views.signup, name="signup"),
    path("requests/new/", views.request_new, name="request_new"),
    path("requests/<int:pk>/", views.request_detail, name="request_detail"),
    path("requests/<int:pk>/quote/", views.quote_create, name="quote_create"),
    path("requests/<int:pk>/quotes/<int:quote_id>/accept/", views.quote_accept, name="quote_accept"),
    path("requests/<int:pk>/pay/", views.pay, name="pay"),
    path("requests/<int:pk>/pay/done/", views.pay_done, name="pay_done"),
    path("requests/<int:pk>/chat/", views.chat, name="chat"),
    path("requests/<int:pk>/proof/", views.proof_upload, name="proof_upload"),
    path("requests/<int:pk>/proof/<str:step>/", views.proof_file, name="proof_file"),
    path("requests/<int:pk>/release/<str:step>/", views.step_confirm, name="step_confirm"),
    path("requests/<int:pk>/cancel/", views.cancel, name="cancel"),
]
