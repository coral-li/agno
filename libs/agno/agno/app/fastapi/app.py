import logging
from typing import List, Optional, Union

import uvicorn
from fastapi import FastAPI
from fastapi.routing import APIRouter

from agno.agent.agent import Agent
from agno.app.base import BaseAPIApp
from agno.app.fastapi.async_router import get_async_router
from agno.app.fastapi.sync_router import get_sync_router
from agno.app.settings import APIAppSettings
from agno.app.utils import generate_id
from agno.team.team import Team
from agno.utils.log import log_info
from agno.workflow.workflow import Workflow

logger = logging.getLogger(__name__)


class FastAPIApp(BaseAPIApp):
    """
    FastAPI wrapper for Agno AI components that automatically generates REST API endpoints.

    This class provides a production-ready REST API interface for Agno agents, teams, and workflows
    using the FastAPI framework. It automatically generates endpoints for communication, handles
    multimodal inputs, supports streaming responses, and manages sessions.

    Key Features:
    - **Automatic Endpoint Generation**: Creates REST API endpoints without manual configuration
    - **Multi-Component Support**: Works with agents, teams, and workflows
    - **Multimodal Input**: Handles text, images, audio, video, and document uploads
    - **Streaming Responses**: Real-time response streaming for chat-like interactions
    - **Session Management**: Built-in session and user tracking
    - **File Processing**: Automatic processing of various file types (PDF, CSV, DOCX, images, etc.)
    - **Knowledge Base Integration**: Automatically loads documents into agent knowledge bases
    - **Async/Sync Support**: Both synchronous and asynchronous endpoint variants

    Generated Endpoints:
    - `GET /status`: API health check
    - `POST /runs`: Universal endpoint for agent/team/workflow communication
      - Supports file uploads, streaming, session management
      - Routes to appropriate component based on agent_id/team_id/workflow_id

    Args:
        agents: List of Agent instances to expose via API
        teams: List of Team instances to expose via API
        workflows: List of Workflow instances to expose via API
        settings: API configuration settings
        api_app: Custom FastAPI instance (optional)
        router: Custom APIRouter instance (optional)
        app_id: Unique identifier for the application
        name: Human-readable name for the application
        description: Description of the application
        monitoring: Enable platform monitoring and registration

    Raises:
        ValueError: If none of agents, teams, or workflows are provided

    Example:
        ```python
        from agno import Agent
        from agno.app.fastapi import FastAPIApp

        # Create an agent
        agent = Agent(name="assistant", model="gpt-4")

        # Create FastAPI app with automatic endpoints
        app = FastAPIApp(agents=[agent])

        # Serve the API
        app.serve("app:api", host="0.0.0.0", port=8000)

        # Now available:
        # GET  http://localhost:8000/status
        # POST http://localhost:8000/runs?agent_id=assistant
        ```

    Usage with Multiple Components:
        ```python
        from agno import Agent, Team
        from agno.app.fastapi import FastAPIApp

        agent1 = Agent(name="researcher")
        agent2 = Agent(name="writer")
        team = Team(name="content-team", members=[agent1, agent2])

        app = FastAPIApp(agents=[agent1, agent2], teams=[team])
        app.serve("app:api")

        # Access via:
        # POST /runs?agent_id=researcher
        # POST /runs?team_id=content-team
        ```

    File Upload Support:
        The `/runs` endpoint automatically handles:
        - Images: PNG, JPEG, WebP (converted to base64 for AI processing)
        - Audio: WAV, MP3, MPEG (converted to base64)
        - Video: MP4, WebM, WMV, etc. (converted to base64)
        - Documents: PDF, CSV, DOCX, TXT, JSON (loaded into knowledge base)

    Note:
        At least one of agents, teams, or workflows must be provided during initialization.
        All components are automatically initialized and registered with the platform when served.
    """
    type = "fastapi"

    def __init__(
        self,
        agents: Optional[List[Agent]] = None,
        teams: Optional[List[Team]] = None,
        workflows: Optional[List[Workflow]] = None,
        settings: Optional[APIAppSettings] = None,
        api_app: Optional[FastAPI] = None,
        router: Optional[APIRouter] = None,
        app_id: Optional[str] = None,
        name: Optional[str] = None,
        description: Optional[str] = None,
        monitoring: bool = True,
    ):
        if not agents and not teams and not workflows:
            raise ValueError("Either agents, teams or workflows must be provided.")

        self.agents: Optional[List[Agent]] = agents
        self.teams: Optional[List[Team]] = teams
        self.workflows: Optional[List[Workflow]] = workflows

        self.settings: APIAppSettings = settings or APIAppSettings()
        self.api_app: Optional[FastAPI] = api_app
        self.router: Optional[APIRouter] = router

        self.app_id: Optional[str] = app_id
        self.name: Optional[str] = name
        self.monitoring = monitoring
        self.description = description
        self.set_app_id()

        if self.agents:
            for agent in self.agents:
                if not agent.app_id:
                    agent.app_id = self.app_id
                agent.initialize_agent()

        if self.teams:
            for team in self.teams:
                if not team.app_id:
                    team.app_id = self.app_id
                team.initialize_team()
                for member in team.members:
                    if isinstance(member, Agent):
                        if not member.app_id:
                            member.app_id = self.app_id

                        member.team_id = None
                        member.initialize_agent()
                    elif isinstance(member, Team):
                        member.initialize_team()

        if self.workflows:
            for workflow in self.workflows:
                if not workflow.app_id:
                    workflow.app_id = self.app_id
                if not workflow.workflow_id:
                    workflow.workflow_id = generate_id(workflow.name)

    def get_router(self) -> APIRouter:
        return get_sync_router(agents=self.agents, teams=self.teams, workflows=self.workflows)

    def get_async_router(self) -> APIRouter:
        return get_async_router(agents=self.agents, teams=self.teams, workflows=self.workflows)

    def serve(
        self,
        app: Union[str, FastAPI],
        *,
        host: str = "localhost",
        port: int = 7777,
        reload: bool = False,
        **kwargs,
    ):
        self.set_app_id()
        self.register_app_on_platform()

        if self.agents:
            for agent in self.agents:
                agent.register_agent()

        if self.teams:
            for team in self.teams:
                team.register_team()

        if self.workflows:
            for workflow in self.workflows:
                workflow.register_workflow()
        log_info(f"Starting API on {host}:{port}")

        uvicorn.run(app=app, host=host, port=port, reload=reload, **kwargs)
