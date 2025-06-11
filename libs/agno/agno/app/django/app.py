from typing import List, Optional, Dict, Any
from uuid import uuid4
import logging

try:
    from ninja import NinjaAPI
    from ninja.files import UploadedFile
except ImportError:
    raise ImportError(
        "`django-ninja` not installed. Please install using `pip install agno[django]`"
    )

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
