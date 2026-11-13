from django.urls import path

from apps.playbook import views

app_name = "playbook"

urlpatterns = [
    path("", views.index, name="index"),
    path("start/<int:challenge_id>/", views.start, name="start"),
    path("lauf/<int:pk>/", views.run_detail, name="run"),
    path("lauf/<int:pk>/bestaetigen/", views.confirm, name="confirm"),
    path("lauf/<int:pk>/abbrechen/", views.abort, name="abort"),
    path("opt-in/", views.opt_in, name="opt_in"),
    path("opt-out/", views.opt_out, name="opt_out"),
]
