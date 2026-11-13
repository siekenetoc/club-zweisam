from django.urls import path

from apps.pages import views

app_name = "pages"

urlpatterns = [
    path("<slug:slug>/", views.page_detail, name="detail"),
]
