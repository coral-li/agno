from django.contrib import admin
from .models import AgentRun, TeamRun


@admin.register(AgentRun)
class AgentRunAdmin(admin.ModelAdmin):
    list_display = ['agent_id', 'user', 'created_at', 'response_time']
    list_filter = ['agent_id', 'created_at', 'user']
    search_fields = ['agent_id', 'message', 'user__username']
    readonly_fields = ['created_at']
    date_hierarchy = 'created_at'

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user')


@admin.register(TeamRun)
class TeamRunAdmin(admin.ModelAdmin):
    list_display = ['team_id', 'user', 'created_at', 'response_time']
    list_filter = ['team_id', 'created_at', 'user']
    search_fields = ['team_id', 'message', 'user__username']
    readonly_fields = ['created_at']
    date_hierarchy = 'created_at'

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user')
