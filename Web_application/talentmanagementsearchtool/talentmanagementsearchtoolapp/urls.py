from django.urls import path

from . import views

urlpatterns = [
    path("", views.home_page, name="home_page"),
    path("result_page", views.result_page, name="result_page"),
    path("check_processing_status", views.check_processing_status, name="check_processing_status"),
    path("loading_page", views.loading_page, name="loading_page"),
    path("email_confirmation_page", views.email_confirmation_page, name="email_confirmation_page"),
]