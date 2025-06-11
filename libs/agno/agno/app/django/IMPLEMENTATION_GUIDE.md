# Django-Ninja Integration Implementation Guide

This guide provides step-by-step instructions for implementing a Django-Ninja integration for Agno that allows seamless integration of AI agents and teams into existing Django projects.

## Overview

The Django-Ninja integration enables developers to:
- Add Agno agents and teams to existing Django projects
- Integrate with django-ninja APIs without conflicts
- Leverage Django's authentication, ORM, and middleware systems
- Maintain Django patterns and conventions

## Architecture

The implementation uses a **standalone integration approach** that doesn't inherit from `BaseAPIApp` due to fundamental differences between FastAPI and Django architectures.

```
DjangoNinjaApp
├── Integrates with existing NinjaAPI instances
├── Automatically generates routes for agents/teams
├── Handles Django-specific patterns (auth, sessions, files)
└── Provides Django admin integration
```

## Implementation Steps

### Step 1: Create the Core Integration Class

Create `libs/agno/agno/app/django/app.py`:

```python
from typing import List, Optional, Dict, Any
from uuid import uuid4
import logging

from ninja import NinjaAPI
from ninja.files import UploadedFile
from pydantic import BaseModel

from agno.agent.agent import Agent
from agno.team.team import Team
from agno.workflow.workflow import Workflow
from agno.app.utils import generate_id
from agno.utils.log import log_info

logger = logging.getLogger(__name__)


class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None
    user_id: Optional[str] = None
    stream: bool = False


class ChatResponse(BaseModel):
    content: str
    agent_id: Optional[str] = None
    team_id: Optional[str] = None
    session_id: Optional[str] = None


class DjangoNinjaApp:
    """
    Django-Ninja integration for Agno AI components.

    Provides seamless integration of Agno agents, teams, and workflows into
    Django projects using django-ninja for API routing. Works alongside existing
    django-ninja routes and leverages Django's authentication and middleware systems.

    Features:
    - Automatic route generation for agents, teams, and workflows
    - Django authentication integration
    - File upload handling with Django's file system
    - Session management using Django sessions
    - Admin interface integration
    - Compatible with existing django-ninja APIs

    Example:
        ```python
        # In your Django app
        from ninja import NinjaAPI
        from agno import Agent
        from agno.app.django import DjangoNinjaApp

        # Existing API
        api = NinjaAPI()

        # Add existing routes
        @api.get("/users")
        def list_users(request):
            return {"users": []}

        # Add Agno integration
        agent = Agent(name="assistant", model="gpt-4")
        agno_app = DjangoNinjaApp(
            api=api,
            agents=[agent],
            prefix="/ai"
        )

        # Now available:
        # GET /users (existing)
        # POST /ai/agents/assistant/chat (Agno-generated)
        ```
    """

    def __init__(
        self,
        api: NinjaAPI,
        agents: Optional[List[Agent]] = None,
        teams: Optional[List[Team]] = None,
        workflows: Optional[List[Workflow]] = None,
        prefix: str = "/agno",
        app_id: Optional[str] = None,
        name: Optional[str] = None,
        description: Optional[str] = None,
        require_auth: bool = True,
        monitoring: bool = True,
    ):
        """
        Initialize Django-Ninja integration.

        Args:
            api: Existing NinjaAPI instance to add routes to
            agents: List of Agent instances to expose
            teams: List of Team instances to expose
            workflows: List of Workflow instances to expose
            prefix: URL prefix for all Agno routes (default: "/agno")
            app_id: Unique identifier for the application
            name: Human-readable name for the application
            description: Description of the application
            require_auth: Whether to require Django authentication
            monitoring: Enable platform monitoring and registration
        """
        if not agents and not teams and not workflows:
            raise ValueError("At least one of agents, teams, or workflows must be provided.")

        self.api = api
        self.agents = agents or []
        self.teams = teams or []
        self.workflows = workflows or []
        self.prefix = prefix.rstrip('/')
        self.app_id = app_id or str(uuid4())
        self.name = name
        self.description = description
        self.require_auth = require_auth
        self.monitoring = monitoring

        # Initialize components
        self._initialize_components()

        # Register routes
        self._register_routes()

        # Register with platform if monitoring enabled
        if self.monitoring:
            self._register_on_platform()

    def _initialize_components(self):
        """Initialize all agents, teams, and workflows with proper IDs."""
        for agent in self.agents:
            if not agent.app_id:
                agent.app_id = self.app_id
            agent.initialize_agent()

        for team in self.teams:
            if not team.app_id:
                team.app_id = self.app_id
            team.initialize_team()

            # Initialize team members
            for member in team.members:
                if isinstance(member, Agent):
                    if not member.app_id:
                        member.app_id = self.app_id
                    member.team_id = team.team_id
                    member.initialize_agent()
                elif isinstance(member, Team):
                    member.initialize_team()

        for workflow in self.workflows:
            if not workflow.app_id:
                workflow.app_id = self.app_id
            if not workflow.workflow_id:
                workflow.workflow_id = generate_id(workflow.name)

    def _register_routes(self):
        """Register all routes with the NinjaAPI instance."""
        # Status endpoint
        self._add_status_route()

        # Agent routes
        for agent in self.agents:
            self._add_agent_routes(agent)

        # Team routes
        for team in self.teams:
            self._add_team_routes(team)

        # Workflow routes
        for workflow in self.workflows:
            self._add_workflow_routes(workflow)

    def _add_status_route(self):
        """Add status endpoint."""
        @self.api.get(f"{self.prefix}/status")
        def agno_status(request):
            return {
                "status": "available",
                "app_id": self.app_id,
                "agents": len(self.agents),
                "teams": len(self.teams),
                "workflows": len(self.workflows)
            }

    def _add_agent_routes(self, agent: Agent):
        """Add routes for a specific agent."""
        agent_path = f"{self.prefix}/agents/{agent.agent_id}"

        # Chat endpoint
        @self.api.post(f"{agent_path}/chat", response=ChatResponse)
        def agent_chat(request, data: ChatRequest):
            if self.require_auth and not request.user.is_authenticated:
                return {"error": "Authentication required"}, 401

            # Use Django session for session_id if not provided
            session_id = data.session_id or request.session.session_key
            user_id = data.user_id or (str(request.user.id) if request.user.is_authenticated else None)

            try:
                response = agent.run(
                    data.message,
                    session_id=session_id,
                    user_id=user_id,
                    stream=data.stream
                )

                return ChatResponse(
                    content=response.content,
                    agent_id=agent.agent_id,
                    session_id=session_id
                )
            except Exception as e:
                logger.error(f"Agent chat error: {e}")
                return {"error": str(e)}, 500

        # File upload endpoint
        @self.api.post(f"{agent_path}/upload")
        def agent_upload(request, file: UploadedFile):
            if self.require_auth and not request.user.is_authenticated:
                return {"error": "Authentication required"}, 401

            if not agent.knowledge:
                return {"error": "Agent has no knowledge base configured"}, 400

            try:
                # Process the uploaded file based on content type
                documents = self._process_uploaded_file(file)

                # Add to agent's knowledge base
                agent.knowledge.load_documents(documents)

                return {
                    "message": f"File {file.name} uploaded successfully",
                    "agent_id": agent.agent_id
                }
            except Exception as e:
                logger.error(f"File upload error: {e}")
                return {"error": str(e)}, 500

    def _add_team_routes(self, team: Team):
        """Add routes for a specific team."""
        team_path = f"{self.prefix}/teams/{team.team_id}"

        @self.api.post(f"{team_path}/chat", response=ChatResponse)
        def team_chat(request, data: ChatRequest):
            if self.require_auth and not request.user.is_authenticated:
                return {"error": "Authentication required"}, 401

            session_id = data.session_id or request.session.session_key
            user_id = data.user_id or (str(request.user.id) if request.user.is_authenticated else None)

            try:
                response = team.run(
                    data.message,
                    session_id=session_id,
                    user_id=user_id,
                    stream=data.stream
                )

                return ChatResponse(
                    content=response.content,
                    team_id=team.team_id,
                    session_id=session_id
                )
            except Exception as e:
                logger.error(f"Team chat error: {e}")
                return {"error": str(e)}, 500

    def _add_workflow_routes(self, workflow: Workflow):
        """Add routes for a specific workflow."""
        workflow_path = f"{self.prefix}/workflows/{workflow.workflow_id}"

        @self.api.post(f"{workflow_path}/run")
        def workflow_run(request, data: Dict[str, Any]):
            if self.require_auth and not request.user.is_authenticated:
                return {"error": "Authentication required"}, 401

            try:
                result = workflow.run(data)
                return {
                    "result": result,
                    "workflow_id": workflow.workflow_id
                }
            except Exception as e:
                logger.error(f"Workflow run error: {e}")
                return {"error": str(e)}, 500

    def _process_uploaded_file(self, file: UploadedFile):
        """Process uploaded file based on content type."""
        from io import BytesIO

        if file.content_type == "application/pdf":
            from agno.document.reader.pdf_reader import PDFReader
            return PDFReader().read(BytesIO(file.read()))

        elif file.content_type == "text/csv":
            from agno.document.reader.csv_reader import CSVReader
            return CSVReader().read(BytesIO(file.read()))

        elif file.content_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
            from agno.document.reader.docx_reader import DocxReader
            return DocxReader().read(BytesIO(file.read()))

        elif file.content_type == "text/plain":
            from agno.document.reader.text_reader import TextReader
            return TextReader().read(BytesIO(file.read()))

        elif file.content_type == "application/json":
            from agno.document.reader.json_reader import JSONReader
            return JSONReader().read(BytesIO(file.read()))

        else:
            raise ValueError(f"Unsupported file type: {file.content_type}")

    def _register_on_platform(self):
        """Register the app with Agno platform for monitoring."""
        try:
            from agno.api.app import AppCreate, create_app

            create_app(app=AppCreate(
                name=self.name or "Django Ninja App",
                app_id=self.app_id,
                config=self._to_dict()
            ))

            # Register individual components
            for agent in self.agents:
                agent.register_agent()

            for team in self.teams:
                team.register_team()

            for workflow in self.workflows:
                workflow.register_workflow()

        except Exception as e:
            logger.debug(f"Could not register with platform: {e}")

    def _to_dict(self) -> Dict[str, Any]:
        """Convert app configuration to dictionary for platform registration."""
        return {
            "type": "django-ninja",
            "description": self.description,
            "prefix": self.prefix,
            "agents": [
                {
                    **agent.get_agent_config_dict(),
                    "agent_id": agent.agent_id,
                    "team_id": agent.team_id,
                }
                for agent in self.agents
            ] if self.agents else None,
            "teams": [
                {
                    **team.to_platform_dict(),
                    "team_id": team.team_id,
                }
                for team in self.teams
            ] if self.teams else None,
            "workflows": [
                {
                    "workflow_id": workflow.workflow_id,
                    "name": workflow.name,
                }
                for workflow in self.workflows
            ] if self.workflows else None,
        }
```

### Step 2: Create Django Models (Optional)

Create `libs/agno/agno/app/django/models.py` for logging and session management:

```python
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
```

### Step 3: Create Django Admin Integration

Create `libs/agno/agno/app/django/admin.py`:

```python
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
```

### Step 4: Create Management Commands

Create `libs/agno/agno/app/django/management/commands/register_agno_agents.py`:

```python
from django.core.management.base import BaseCommand
from django.conf import settings
import importlib


class Command(BaseCommand):
    help = 'Register Agno agents with the platform'

    def add_arguments(self, parser):
        parser.add_argument(
            '--app-module',
            type=str,
            help='Module path to your Django Ninja app with Agno integration',
            default='myapp.api'
        )

    def handle(self, *args, **options):
        try:
            module_path = options['app_module']
            module = importlib.import_module(module_path)

            # Assuming the DjangoNinjaApp instance is named 'agno_app'
            agno_app = getattr(module, 'agno_app', None)

            if not agno_app:
                self.stdout.write(
                    self.style.ERROR(
                        f'No agno_app found in {module_path}. '
                        'Make sure your DjangoNinjaApp instance is named "agno_app"'
                    )
                )
                return

            # Re-register all components
            agno_app._register_on_platform()

            self.stdout.write(
                self.style.SUCCESS(
                    f'Successfully registered {len(agno_app.agents)} agents, '
                    f'{len(agno_app.teams)} teams, and '
                    f'{len(agno_app.workflows)} workflows'
                )
            )

        except ImportError as e:
            self.stdout.write(
                self.style.ERROR(f'Could not import {module_path}: {e}')
            )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error registering agents: {e}')
            )
```

### Step 5: Create Package Init File

Create `libs/agno/agno/app/django/__init__.py`:

```python
"""
Django-Ninja integration for Agno AI components.

This package provides seamless integration of Agno agents, teams, and workflows
into Django projects using django-ninja for API routing.
"""

from .app import DjangoNinjaApp, ChatRequest, ChatResponse

__all__ = ['DjangoNinjaApp', 'ChatRequest', 'ChatResponse']
```

### Step 6: Create Testing Utilities

Create `libs/agno/agno/app/django/testing.py`:

```python
from django.test import TestCase, Client
from django.contrib.auth.models import User
from ninja.testing import TestClient

from agno import Agent
from .app import DjangoNinjaApp


class AgnoTestCase(TestCase):
    """Base test case for testing Agno Django integrations."""

    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        self.client = Client()

    def create_test_agent(self, name="test-agent"):
        """Create a test agent for testing."""
        return Agent(
            name=name,
            model="gpt-3.5-turbo",
            instructions="You are a helpful test assistant."
        )

    def create_agno_app(self, agent=None, **kwargs):
        """Create a DjangoNinjaApp for testing."""
        from ninja import NinjaAPI

        api = NinjaAPI()
        agent = agent or self.create_test_agent()

        return DjangoNinjaApp(
            api=api,
            agents=[agent],
            require_auth=False,  # Disable auth for tests by default
            monitoring=False,    # Disable monitoring for tests
            **kwargs
        )

    def login(self):
        """Log in the test user."""
        self.client.login(username='testuser', password='testpass123')

    def assertAgentResponse(self, response, expected_status=200):
        """Assert that an agent response has the expected format."""
        self.assertEqual(response.status_code, expected_status)
        if expected_status == 200:
            data = response.json()
            self.assertIn('content', data)
            self.assertIn('agent_id', data)


# Example test
class DjangoNinjaAppTestCase(AgnoTestCase):

    def test_agent_chat_endpoint(self):
        """Test that agent chat endpoint works."""
        agno_app = self.create_agno_app()
        client = TestClient(agno_app.api)

        response = client.post("/agno/agents/test-agent/chat", json={
            "message": "Hello, how are you?"
        })

        self.assertAgentResponse(response)

    def test_status_endpoint(self):
        """Test that status endpoint returns correct information."""
        agno_app = self.create_agno_app()
        client = TestClient(agno_app.api)

        response = client.get("/agno/status")

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['agents'], 1)
        self.assertEqual(data['teams'], 0)
        self.assertEqual(data['workflows'], 0)
```

## Usage Instructions

### Basic Usage

1. **In your Django project**, add to your `urls.py`:

```python
# myproject/urls.py
from django.contrib import admin
from django.urls import path
from .api import api  # Your ninja API instance

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', api.urls),  # This includes Agno routes
]
```

2. **Create your API with Agno integration**:

```python
# myproject/api.py
from ninja import NinjaAPI
from agno import Agent
from agno.app.django import DjangoNinjaApp

# Create your ninja API
api = NinjaAPI()

# Add your existing routes
@api.get("/users")
def list_users(request):
    return {"users": []}

# Create Agno agents
assistant_agent = Agent(
    name="assistant",
    model="gpt-4",
    instructions="You are a helpful assistant."
)

customer_service_agent = Agent(
    name="customer-service",
    model="gpt-4",
    instructions="You are a customer service representative."
)

# Add Agno integration
agno_app = DjangoNinjaApp(
    api=api,
    agents=[assistant_agent, customer_service_agent],
    prefix="/ai",
    name="My Django AI App",
    require_auth=True,  # Require Django authentication
)

# Now you have:
# GET  /api/users (your existing route)
# GET  /api/ai/status (Agno status)
# POST /api/ai/agents/assistant/chat (Agno agent)
# POST /api/ai/agents/customer-service/chat (Agno agent)
```

### Advanced Usage with Teams

```python
from agno import Agent, Team
from agno.app.django import DjangoNinjaApp

# Create agents
researcher = Agent(name="researcher", model="gpt-4")
writer = Agent(name="writer", model="gpt-4")

# Create team
content_team = Team(
    name="content-team",
    members=[researcher, writer],
    instructions="Work together to create high-quality content."
)

# Add to Django
agno_app = DjangoNinjaApp(
    api=api,
    agents=[researcher, writer],
    teams=[content_team],
    prefix="/ai"
)
```

### Configuration

Add to your Django `settings.py`:

```python
# settings.py

# Agno settings
AGNO_MONITOR = True  # Enable platform monitoring
AGNO_API_KEY = "your-api-key"

# Add to INSTALLED_APPS if using models
INSTALLED_APPS = [
    # ... your apps
    'agno.app.django',
]
```

### Testing

```python
# tests.py
from agno.app.django.testing import AgnoTestCase

class MyAgnoTestCase(AgnoTestCase):

    def test_my_agent(self):
        agent = self.create_test_agent("my-agent")
        agno_app = self.create_agno_app(agent=agent)

        # Test your agent functionality
        client = TestClient(agno_app.api)
        response = client.post("/agno/agents/my-agent/chat", json={
            "message": "Test message"
        })

        self.assertAgentResponse(response)
```

## Key Features

- ✅ **Seamless Integration**: Works with existing django-ninja APIs
- ✅ **Django Authentication**: Leverages Django's built-in auth system
- ✅ **File Uploads**: Supports document uploads to agent knowledge bases
- ✅ **Session Management**: Uses Django sessions automatically
- ✅ **Admin Interface**: Optional Django admin integration for monitoring
- ✅ **Testing Utilities**: Comprehensive test utilities included
- ✅ **Management Commands**: CLI commands for agent registration
- ✅ **Error Handling**: Proper HTTP error responses
- ✅ **Logging**: Integration with Django's logging system

## Benefits

1. **Django-Native**: Follows Django patterns and conventions
2. **Non-Intrusive**: Doesn't interfere with existing django-ninja routes
3. **Flexible**: Configurable authentication, prefixes, and monitoring
4. **Production-Ready**: Includes logging, error handling, and monitoring
5. **Developer-Friendly**: Comprehensive testing utilities and documentation

This implementation provides a complete Django-Ninja integration that feels natural to Django developers while providing all the power of Agno's AI capabilities.
