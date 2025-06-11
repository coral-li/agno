from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone


class AgentRun(models.Model):
    """Model to log agent interactions."""

    agent_id = models.CharField(max_length=255)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    session_id = models.CharField(max_length=255, null=True, blank=True)
    message = models.TextField()
    response = models.TextField()
    created_at = models.DateTimeField(default=timezone.now)
    response_time = models.FloatField(null=True, blank=True)  # in seconds

    class Meta:
        db_table = 'agno_agent_runs'
        ordering = ['-created_at']

    def __str__(self):
        return f"Agent {self.agent_id} - {self.created_at}"


class TeamRun(models.Model):
    """Model to log team interactions."""

    team_id = models.CharField(max_length=255)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    session_id = models.CharField(max_length=255, null=True, blank=True)
    message = models.TextField()
    response = models.TextField()
    created_at = models.DateTimeField(default=timezone.now)
    response_time = models.FloatField(null=True, blank=True)

    class Meta:
        db_table = 'agno_team_runs'
        ordering = ['-created_at']

    def __str__(self):
        return f"Team {self.team_id} - {self.created_at}"
