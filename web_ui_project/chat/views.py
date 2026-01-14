# from django.shortcuts import render, get_object_or_404
# from django.contrib.auth.decorators import login_required
# from .models import Project, ChatMessage
# from agent.agent_core import AgentCore

# @login_required
# def chat_view(request, project_id):
#     project = get_object_or_404(Project, id=project_id, user=request.user)
#     messages = ChatMessage.objects.filter(project=project).order_by("created_at")

#     agent = AgentCore()

#     if request.method == "POST":
#         user_input = request.POST.get("message")

#         # Save user message
#         ChatMessage.objects.create(
#             project=project,
#             sender="user",
#             message=user_input
#         )

#         # Call existing AgentCore (unchanged)
#         response = agent.run(user_input)

#         # Save agent response (FULL response = code + explanation)
#         ChatMessage.objects.create(
#             project=project,
#             sender="agent",
#             message=response
#         )

#     return render(request, "chat/chat.html", {
#         "project": project,
#         "messages": messages
#     })

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from .models import Project, ChatMessage
from agent.agent_core import AgentCore

@login_required
def chat_view(request, project_id):
    project = get_object_or_404(Project, id=project_id, user=request.user)
    messages = ChatMessage.objects.filter(project=project).order_by("created_at")

    if request.method == "POST":
        user_input = request.POST.get("message")

        # Validate input
        if not user_input or not user_input.strip():
            return redirect("chat:chat", project_id=project_id)

        # Save user message
        ChatMessage.objects.create(
            project=project,
            sender="user",
            message=user_input
        )

        # Initialize agent with project's root path (DYNAMIC WORKSPACE)
        agent = AgentCore(workspace_root=project.root_path)

        # Call agent with user input
        response = agent.run(user_input)

        # Save agent response (FULL response = code + explanation)
        ChatMessage.objects.create(
            project=project,
            sender="agent",
            message=response
        )

        # Redirect to prevent form resubmission
        return redirect("chat:chat", project_id=project_id)

    return render(request, "chat/chat.html", {
        "project": project,
        "messages": messages
    })