from django.urls import path

from . import views

urlpatterns = [
    path("", views.homepage, name="homepage"),
    path("sample_result_page", views.result_page, name="sample_result_page"),
    path("form_example_page", views.form_example_get_name, name="form_example_page")
]