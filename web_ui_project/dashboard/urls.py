from django.urls import path
from . import views

app_name = "dashboard"

urlpatterns = [
    path("", views.home, name="home"),
    path("new-project/", views.new_project, name="new_project"),
    path("projects/", views.project_list, name="project_list"),
]