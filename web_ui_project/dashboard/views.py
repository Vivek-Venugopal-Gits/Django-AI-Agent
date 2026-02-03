from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
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


@login_required
@require_POST
def delete_project_chat(request, project_id):
    project = get_object_or_404(Project, id=project_id, user=request.user)

    # Delete all chat messages for this project
    Project.objects.filter(id=project.id).delete()

    return redirect("dashboard:project_list")