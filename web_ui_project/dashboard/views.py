from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from chat.models import Project

@login_required
def home(request):
    return render(request, "dashboard/home.html")

@login_required
def new_project(request):
    if request.method == "POST":
        project_name = request.POST.get("project_name")
        root_path = request.POST.get("root_path")

        project = Project.objects.create(
            user=request.user,
            name=project_name,
            root_path=root_path
        )

        return redirect("chat:chat", project_id=project.id)

    return render(request, "dashboard/new_project.html")

@login_required
def project_list(request):
    projects = Project.objects.filter(user=request.user).order_by("-created_at")
    return render(request, "dashboard/project_list.html", {"projects": projects})