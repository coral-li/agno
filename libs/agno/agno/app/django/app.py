import json
import logging
from dataclasses import asdict
from io import BytesIO
from typing import Any, Dict, List, Optional, cast
from uuid import uuid4

try:
    from django.http import StreamingHttpResponse, JsonResponse
    from ninja import NinjaAPI, File, Form, Query
    from ninja.files import UploadedFile
except ImportError:
    raise ImportError("`django-ninja` not installed. Please install using `pip install agno[django]`")

from pydantic import BaseModel

from agno.agent.agent import Agent, RunResponse
from agno.app.playground.utils import process_audio, process_document, process_image, process_video
from agno.app.utils import generate_id
from agno.media import Audio, Image, Video
from agno.media import File as FileMedia
from agno.run.base import RunStatus
from agno.run.response import RunResponseEvent
from agno.run.team import RunResponseErrorEvent as TeamRunResponseErrorEvent
from agno.run.team import TeamRunResponseEvent
from agno.team.team import Team
from agno.workflow.workflow import Workflow

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


def agent_chat_response_streamer(
    agent: Agent,
    message: str,
    session_id: Optional[str] = None,
    user_id: Optional[str] = None,
    images: Optional[List[Image]] = None,
    audio: Optional[List[Audio]] = None,
    videos: Optional[List[Video]] = None,
):
    """Generator for streaming agent responses."""
    try:
        run_response = agent.run(
            message,
            session_id=session_id,
            user_id=user_id,
            images=images,
            audio=audio,
            videos=videos,
            stream=True,
            stream_intermediate_steps=True,
        )
        for run_response_chunk in run_response:
            run_response_chunk = cast(RunResponseEvent, run_response_chunk)
            yield f"{run_response_chunk.to_json()}"
    except Exception as e:
        error_response = RunResponse(content=str(e), status=RunStatus.error)
        yield f"{error_response.to_json()}"
        return


def team_chat_response_streamer(
    team: Team,
    message: str,
    session_id: Optional[str] = None,
    user_id: Optional[str] = None,
    images: Optional[List[Image]] = None,
    audio: Optional[List[Audio]] = None,
    videos: Optional[List[Video]] = None,
    files: Optional[List[FileMedia]] = None,
):
    """Generator for streaming team responses."""
    try:
        run_response = team.run(
            message,
            session_id=session_id,
            user_id=user_id,
            images=images,
            audio=audio,
            videos=videos,
            files=files,
            stream=True,
            stream_intermediate_steps=True,
        )
        for run_response_chunk in run_response:
            run_response_chunk = cast(TeamRunResponseEvent, run_response_chunk)
            yield f"{run_response_chunk.to_json()}"
    except Exception as e:
        error_response = TeamRunResponseErrorEvent(
            content=str(e),
        )
        yield f"{error_response.to_json()}"
        return


class DjangoNinjaApp:
    """
    Django-Ninja integration for Agno AI components.

    Provides seamless integration of Agno agents, teams, and workflows into
    Django projects using django-ninja for API routing. Exposes the same API
    structure as the FastAPI integration.

    API Endpoints:
    - GET /status: API health check
    - POST /runs: Universal endpoint for agent/team/workflow communication

    Features:
    - Unified API endpoint matching FastAPI structure
    - Django authentication integration
    - File upload handling with Django's file system
    - Session management using Django sessions
    - Streaming response support
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
        )

        # Now available:
        # GET /users (existing)
        # GET /status (Agno status)
        # POST /runs?agent_id=assistant (Agno universal endpoint)
        ```
    """

    def __init__(
        self,
        api: NinjaAPI,
        agents: Optional[List[Agent]] = None,
        teams: Optional[List[Team]] = None,
        workflows: Optional[List[Workflow]] = None,
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
        @self.api.get("/status")
        def status(request):
            return {"status": "available"}

        # Universal runs endpoint
        @self.api.post("/runs")
        def run_agent_or_team_or_workflow(
            request,
            agent_id: Optional[str] = Query(None),
            team_id: Optional[str] = Query(None),
            workflow_id: Optional[str] = Query(None),
            message: Optional[str] = Form(None),
            stream: bool = Form(True),
            monitor: bool = Form(False),
            workflow_input: Optional[Dict[str, Any]] = Form(None),
            session_id: Optional[str] = Form(None),
            user_id: Optional[str] = Form(None),
            files: Optional[List[UploadedFile]] = File(None),
        ):
            # Authentication check
            if self.require_auth and not request.user.is_authenticated:
                return JsonResponse({"error": "Authentication required"}, status=401)

            # Session management
            if session_id is not None and session_id != "":
                logger.debug(f"Continuing session: {session_id}")
            else:
                logger.debug("Creating new session")
                session_id = str(uuid4())

            # Use Django session for session_id if not provided
            if not session_id:
                session_id = request.session.session_key

            # Use Django user for user_id if not provided
            if not user_id and request.user.is_authenticated:
                user_id = str(request.user.id)

            # Validation: Only one of agent_id, team_id or workflow_id can be provided
            if (agent_id and team_id) or (agent_id and workflow_id) or (team_id and workflow_id):
                return JsonResponse({"error": "Only one of agent_id, team_id or workflow_id can be provided"}, status=400)

            if not agent_id and not team_id and not workflow_id:
                return JsonResponse({"error": "One of agent_id, team_id or workflow_id must be provided"}, status=400)

            # Find the component
            agent = None
            team = None
            workflow = None

            if agent_id and self.agents:
                agent = next((a for a in self.agents if a.agent_id == agent_id), None)
                if agent is None:
                    return JsonResponse({"error": "Agent not found"}, status=404)
                if not message:
                    return JsonResponse({"error": "Message is required"}, status=400)

            if team_id and self.teams:
                team = next((t for t in self.teams if t.team_id == team_id), None)
                if team is None:
                    return JsonResponse({"error": "Team not found"}, status=404)
                if not message:
                    return JsonResponse({"error": "Message is required"}, status=400)

            if workflow_id and self.workflows:
                workflow = next((w for w in self.workflows if w.workflow_id == workflow_id), None)
                if workflow is None:
                    return JsonResponse({"error": "Workflow not found"}, status=404)
                if not workflow_input:
                    return JsonResponse({"error": "Workflow input is required"}, status=400)

            # Set monitoring
            if agent:
                agent.monitoring = bool(monitor)
            elif team:
                team.monitoring = bool(monitor)
            elif workflow:
                workflow.monitoring = bool(monitor)

            # Process files
            base64_images: List[Image] = []
            base64_audios: List[Audio] = []
            base64_videos: List[Video] = []
            document_files: List[FileMedia] = []

            if files:
                if agent:
                    base64_images, base64_audios, base64_videos = self._agent_process_file(files, agent)
                elif team:
                    base64_images, base64_audios, base64_videos, document_files = self._team_process_file(files)

            # Execute the component
            if stream:
                if agent:
                    response = StreamingHttpResponse(
                        agent_chat_response_streamer(
                            agent,
                            message,
                            session_id=session_id,
                            user_id=user_id,
                            images=base64_images if base64_images else None,
                            audio=base64_audios if base64_audios else None,
                            videos=base64_videos if base64_videos else None,
                        ),
                        content_type="application/json",
                    )
                    response['Cache-Control'] = 'no-cache'
                    return response
                elif team:
                    response = StreamingHttpResponse(
                        team_chat_response_streamer(
                            team,
                            message,
                            session_id=session_id,
                            user_id=user_id,
                            images=base64_images if base64_images else None,
                            audio=base64_audios if base64_audios else None,
                            videos=base64_videos if base64_videos else None,
                            files=document_files if document_files else None,
                        ),
                        content_type="application/json",
                    )
                    response['Cache-Control'] = 'no-cache'
                    return response
                elif workflow:
                    workflow_instance = workflow.deep_copy(update={"workflow_id": workflow_id})
                    workflow_instance.user_id = user_id
                    workflow_instance.session_name = None

                    def workflow_streamer():
                        for result in workflow_instance.run(**(workflow_input or {})):
                            yield f"data: {json.dumps(asdict(result))}\n\n"

                    response = StreamingHttpResponse(
                        workflow_streamer(),
                        content_type="application/json",
                    )
                    response['Cache-Control'] = 'no-cache'
                    return response
            else:
                if agent:
                    run_response = cast(
                        RunResponse,
                        agent.run(
                            message=message,
                            session_id=session_id,
                            user_id=user_id,
                            images=base64_images if base64_images else None,
                            audio=base64_audios if base64_audios else None,
                            videos=base64_videos if base64_videos else None,
                            stream=False,
                        ),
                    )
                    return run_response.to_dict()
                elif team:
                    team_run_response = team.run(
                        message=message,
                        session_id=session_id,
                        user_id=user_id,
                        images=base64_images if base64_images else None,
                        audio=base64_audios if base64_audios else None,
                        videos=base64_videos if base64_videos else None,
                        files=document_files if document_files else None,
                        stream=False,
                    )
                    return team_run_response.to_dict()
                elif workflow:
                    workflow_instance = workflow.deep_copy(update={"workflow_id": workflow_id})
                    workflow_instance.user_id = user_id
                    workflow_instance.session_name = None
                    return workflow_instance.run(**(workflow_input or {})).to_dict()

    def _agent_process_file(self, files: List[UploadedFile], agent: Agent):
        """Process uploaded files for agents."""
        base64_images: List[Image] = []
        base64_audios: List[Audio] = []
        base64_videos: List[Video] = []

        for file in files:
            logger.info(f"Processing file: {file.content_type}")
            if file.content_type in ["image/png", "image/jpeg", "image/jpg", "image/webp"]:
                try:
                    base64_image = process_image(file)
                    base64_images.append(base64_image)
                except Exception as e:
                    logger.error(f"Error processing image {file.name}: {e}")
                    continue
            elif file.content_type in ["audio/wav", "audio/mp3", "audio/mpeg"]:
                try:
                    base64_audio = process_audio(file)
                    base64_audios.append(base64_audio)
                except Exception as e:
                    logger.error(f"Error processing audio {file.name}: {e}")
                    continue
            elif file.content_type in [
                "video/x-flv",
                "video/quicktime",
                "video/mpeg",
                "video/mpegs",
                "video/mpgs",
                "video/mpg",
                "video/mp4",
                "video/webm",
                "video/wmv",
                "video/3gpp",
            ]:
                try:
                    base64_video = process_video(file)
                    base64_videos.append(base64_video)
                except Exception as e:
                    logger.error(f"Error processing video {file.name}: {e}")
                    continue
            else:
                # Process documents for knowledge base
                if agent.knowledge is None:
                    raise ValueError("KnowledgeBase not found")

                try:
                    if file.content_type == "application/pdf":
                        from agno.document.reader.pdf_reader import PDFReader
                        contents = file.read()
                        pdf_file = BytesIO(contents)
                        pdf_file.name = file.name
                        file_content = PDFReader().read(pdf_file)
                        agent.knowledge.load_documents(file_content)
                    elif file.content_type == "text/csv":
                        from agno.document.reader.csv_reader import CSVReader
                        contents = file.read()
                        csv_file = BytesIO(contents)
                        csv_file.name = file.name
                        file_content = CSVReader().read(csv_file)
                        agent.knowledge.load_documents(file_content)
                    elif file.content_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
                        from agno.document.reader.docx_reader import DocxReader
                        contents = file.read()
                        docx_file = BytesIO(contents)
                        docx_file.name = file.name
                        file_content = DocxReader().read(docx_file)
                        agent.knowledge.load_documents(file_content)
                    elif file.content_type == "text/plain":
                        from agno.document.reader.text_reader import TextReader
                        contents = file.read()
                        text_file = BytesIO(contents)
                        text_file.name = file.name
                        file_content = TextReader().read(text_file)
                        agent.knowledge.load_documents(file_content)
                    elif file.content_type == "application/json":
                        from agno.document.reader.json_reader import JSONReader
                        contents = file.read()
                        json_file = BytesIO(contents)
                        json_file.name = file.name
                        file_content = JSONReader().read(json_file)
                        agent.knowledge.load_documents(file_content)
                    else:
                        raise ValueError(f"Unsupported file type: {file.content_type}")
                except Exception as e:
                    logger.error(f"Error processing document {file.name}: {e}")
                    continue

        return base64_images, base64_audios, base64_videos

    def _team_process_file(self, files: List[UploadedFile]):
        """Process uploaded files for teams."""
        base64_images: List[Image] = []
        base64_audios: List[Audio] = []
        base64_videos: List[Video] = []
        document_files: List[FileMedia] = []

        for file in files:
            if file.content_type in ["image/png", "image/jpeg", "image/jpg", "image/webp"]:
                try:
                    base64_image = process_image(file)
                    base64_images.append(base64_image)
                except Exception as e:
                    logger.error(f"Error processing image {file.name}: {e}")
                    continue
            elif file.content_type in ["audio/wav", "audio/mp3", "audio/mpeg"]:
                try:
                    base64_audio = process_audio(file)
                    base64_audios.append(base64_audio)
                except Exception as e:
                    logger.error(f"Error processing audio {file.name}: {e}")
                    continue
            elif file.content_type in [
                "video/x-flv",
                "video/quicktime",
                "video/mpeg",
                "video/mpegs",
                "video/mpgs",
                "video/mpg",
                "video/mp4",
                "video/webm",
                "video/wmv",
                "video/3gpp",
            ]:
                try:
                    base64_video = process_video(file)
                    base64_videos.append(base64_video)
                except Exception as e:
                    logger.error(f"Error processing video {file.name}: {e}")
                    continue
            elif file.content_type in [
                "application/pdf",
                "text/csv",
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                "text/plain",
                "application/json",
            ]:
                document_file = process_document(file)
                if document_file is not None:
                    document_files.append(document_file)
            else:
                raise ValueError(f"Unsupported file type: {file.content_type}")

        return base64_images, base64_audios, base64_videos, document_files

    def _register_on_platform(self):
        """Register the app with Agno platform for monitoring."""
        try:
            from agno.api.app import AppCreate, create_app

            create_app(app=AppCreate(name=self.name or "Django Ninja App", app_id=self.app_id, config=self._to_dict()))

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
            "agents": [
                {
                    **agent.get_agent_config_dict(),
                    "agent_id": agent.agent_id,
                    "team_id": agent.team_id,
                }
                for agent in self.agents
            ]
            if self.agents
            else None,
            "teams": [
                {
                    **team.to_platform_dict(),
                    "team_id": team.team_id,
                }
                for team in self.teams
            ]
            if self.teams
            else None,
            "workflows": [
                {
                    "workflow_id": workflow.workflow_id,
                    "name": workflow.name,
                }
                for workflow in self.workflows
            ]
            if self.workflows
            else None,
        }
