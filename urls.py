# laptop_guide/urls.py
from django.urls import path
from .views import guide_page, guide_laptop_query

app_name = "laptop_guide"

urlpatterns = [
    path("", guide_page, name="guide_page"),
    path("ask/", guide_laptop_query, name="guide_ask"),
]
