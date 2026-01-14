from django.db import models
from django.contrib.auth.models import User

class Project(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=200)
    root_path = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class ChatMessage(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE)
    sender = models.CharField(max_length=10)  # user / agent
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
