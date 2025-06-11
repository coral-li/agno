"""Unit tests for DjangoNinjaApp class."""

# Configure Django settings first
from unittest.mock import Mock, patch

import django
import pytest
from django.conf import settings

if not settings.configured:
    settings.configure(
        INSTALLED_APPS=[
            "django.contrib.auth",
            "django.contrib.contenttypes",
        ],
        DATABASES={
            "default": {
                "ENGINE": "django.db.backends.sqlite3",
                "NAME": ":memory:",
            }
        },
        SECRET_KEY="test-secret-key",
        USE_TZ=True,
    )
    django.setup()

# Check if django-ninja is available
try:
    from ninja import NinjaAPI
    from ninja.files import UploadedFile

    django_ninja_available = True
except ImportError:
    django_ninja_available = False

# Skip all tests if django-ninja is not available
pytestmark = pytest.mark.skipif(
    not django_ninja_available, reason="django-ninja not installed. Install with 'pip install agno[django]'"
)

from agno.agent.agent import Agent
from agno.team.team import Team
from agno.workflow.workflow import Workflow

# Only import Django components if django-ninja is available
if django_ninja_available:
    from agno.app.django.app import ChatRequest, ChatResponse, DjangoNinjaApp
else:
    # Create dummy classes to prevent import errors
    DjangoNinjaApp = None
    ChatRequest = None
    ChatResponse = None


@pytest.fixture
def mock_ninja_api():
    """Create a mock NinjaAPI instance."""
    api = Mock(spec=NinjaAPI)
    api.get = Mock()
    api.post = Mock()
    return api


@pytest.fixture
def mock_agent():
    """Create a mock Agent instance."""
    agent = Mock(spec=Agent)
    agent.name = "test-agent"
    agent.agent_id = "test-agent"
    agent.app_id = None
    agent.team_id = None
    agent.knowledge = Mock()
    agent.initialize_agent = Mock()
    agent.register_agent = Mock()
    agent.run = Mock()
    agent.get_agent_config_dict = Mock(return_value={"model": "gpt-4"})
    return agent


@pytest.fixture
def mock_team():
    """Create a mock Team instance."""
    team = Mock(spec=Team)
    team.name = "test-team"
    team.team_id = "test-team"
    team.app_id = None
    team.members = []
    team.initialize_team = Mock()
    team.register_team = Mock()
    team.run = Mock()
    team.to_platform_dict = Mock(return_value={"name": "test-team"})
    return team


@pytest.fixture
def mock_workflow():
    """Create a mock Workflow instance."""
    workflow = Mock(spec=Workflow)
    workflow.name = "test-workflow"
    workflow.workflow_id = None
    workflow.app_id = None
    workflow.run = Mock()
    workflow.deep_copy = Mock(return_value=workflow)
    workflow.register_workflow = Mock()
    return workflow


@pytest.fixture
def mock_django_request():
    """Create a mock Django request."""
    request = Mock()
    request.user = Mock()
    request.user.is_authenticated = True
    request.user.id = 123
    request.session = Mock()
    request.session.session_key = "test-session-key"
    return request


@pytest.fixture
def mock_uploaded_file():
    """Create a mock UploadedFile."""
    file = Mock(spec=UploadedFile)
    file.name = "test.pdf"
    file.content_type = "application/pdf"
    file.read = Mock(return_value=b"fake pdf content")
    return file


class TestDjangoNinjaAppInitialization:
    """Test DjangoNinjaApp initialization scenarios."""

    def test_init_with_agents_only(self, mock_ninja_api, mock_agent):
        """Test initialization with agents only."""
        app = DjangoNinjaApp(api=mock_ninja_api, agents=[mock_agent])

        assert app.api == mock_ninja_api
        assert app.agents == [mock_agent]
        assert app.teams == []
        assert app.workflows == []
        assert app.require_auth is True
        assert app.monitoring is True
        assert app.app_id is not None
        mock_agent.initialize_agent.assert_called_once()

    def test_init_with_teams_only(self, mock_ninja_api, mock_team):
        """Test initialization with teams only."""
        app = DjangoNinjaApp(api=mock_ninja_api, teams=[mock_team])

        assert app.teams == [mock_team]
        assert app.agents == []
        assert app.workflows == []
        mock_team.initialize_team.assert_called_once()

    def test_init_with_workflows_only(self, mock_ninja_api, mock_workflow):
        """Test initialization with workflows only."""
        with patch("agno.app.django.app.generate_id", return_value="generated-workflow-id"):
            app = DjangoNinjaApp(api=mock_ninja_api, workflows=[mock_workflow])

            assert app.workflows == [mock_workflow]
            assert app.agents == []
            assert app.teams == []
            assert mock_workflow.workflow_id == "generated-workflow-id"

    def test_init_with_custom_settings(self, mock_ninja_api, mock_agent):
        """Test initialization with custom settings."""
        app = DjangoNinjaApp(
            api=mock_ninja_api,
            agents=[mock_agent],
            app_id="custom-app-id",
            name="Custom App",
            description="Custom Description",
            require_auth=False,
            monitoring=False,
        )

        assert app.app_id == "custom-app-id"
        assert app.name == "Custom App"
        assert app.description == "Custom Description"
        assert app.require_auth is False
        assert app.monitoring is False

    def test_init_no_components_raises_error(self, mock_ninja_api):
        """Test that initialization without any components raises ValueError."""
        with pytest.raises(ValueError, match="At least one of agents, teams, or workflows must be provided"):
            DjangoNinjaApp(api=mock_ninja_api)

    def test_init_empty_lists_raises_error(self, mock_ninja_api):
        """Test that initialization with empty lists raises ValueError."""
        with pytest.raises(ValueError, match="At least one of agents, teams, or workflows must be provided"):
            DjangoNinjaApp(api=mock_ninja_api, agents=[], teams=[], workflows=[])


class TestDjangoNinjaAppComponentInitialization:
    """Test component initialization and configuration."""

    def test_app_id_propagation_to_agents(self, mock_ninja_api, mock_agent):
        """Test that app_id is propagated to agents."""
        mock_agent.app_id = None
        app = DjangoNinjaApp(api=mock_ninja_api, agents=[mock_agent], app_id="test-app-id")

        assert mock_agent.app_id == "test-app-id"

    def test_app_id_not_overridden_for_agents(self, mock_ninja_api, mock_agent):
        """Test that existing app_id on agents is not overridden."""
        mock_agent.app_id = "existing-id"
        app = DjangoNinjaApp(api=mock_ninja_api, agents=[mock_agent], app_id="test-app-id")

        assert mock_agent.app_id == "existing-id"

    def test_team_member_initialization(self, mock_ninja_api, mock_team):
        """Test that team members are properly initialized."""
        mock_agent_member = Mock(spec=Agent)
        mock_agent_member.app_id = None
        mock_agent_member.team_id = None
        mock_agent_member.initialize_agent = Mock()

        mock_team_member = Mock(spec=Team)
        mock_team_member.initialize_team = Mock()

        mock_team.members = [mock_agent_member, mock_team_member]
        mock_team.team_id = "test-team-id"

        app = DjangoNinjaApp(api=mock_ninja_api, teams=[mock_team], app_id="test-app-id")

        assert mock_agent_member.app_id == "test-app-id"
        assert mock_agent_member.team_id == "test-team-id"
        mock_agent_member.initialize_agent.assert_called_once()
        mock_team_member.initialize_team.assert_called_once()

    def test_workflow_id_generation(self, mock_ninja_api, mock_workflow):
        """Test that workflow_id is generated when not present."""
        mock_workflow.workflow_id = None
        mock_workflow.name = "test-workflow"

        with patch("agno.app.django.app.generate_id", return_value="generated-workflow-id"):
            app = DjangoNinjaApp(api=mock_ninja_api, workflows=[mock_workflow])

            assert mock_workflow.workflow_id == "generated-workflow-id"

    def test_workflow_id_not_overridden(self, mock_ninja_api):
        """Test that existing workflow_id is not overridden."""
        mock_workflow = Mock(spec=Workflow)
        mock_workflow.name = "test-workflow"
        mock_workflow.workflow_id = "existing-workflow-id"
        mock_workflow.app_id = None

        app = DjangoNinjaApp(api=mock_ninja_api, workflows=[mock_workflow])

        assert mock_workflow.workflow_id == "existing-workflow-id"


class TestDjangoNinjaAppRouteRegistration:
    """Test route registration with the new unified API structure."""

    def test_status_route_registration(self, mock_ninja_api, mock_agent):
        """Test that status route is registered."""
        app = DjangoNinjaApp(api=mock_ninja_api, agents=[mock_agent])

        # Verify that the get route for /status was registered
        mock_ninja_api.get.assert_called()
        calls = mock_ninja_api.get.call_args_list
        status_call = next((call for call in calls if "/status" in str(call)), None)
        assert status_call is not None

    def test_runs_route_registration(self, mock_ninja_api, mock_agent):
        """Test that unified /runs route is registered."""
        app = DjangoNinjaApp(api=mock_ninja_api, agents=[mock_agent])

        # Verify that the post route for /runs was registered
        mock_ninja_api.post.assert_called()
        calls = mock_ninja_api.post.call_args_list
        runs_call = next((call for call in calls if "/runs" in str(call)), None)
        assert runs_call is not None

    def test_only_unified_routes_registered(self, mock_ninja_api, mock_agent, mock_team, mock_workflow):
        """Test that only the unified routes are registered, not separate component routes."""
        app = DjangoNinjaApp(api=mock_ninja_api, agents=[mock_agent], teams=[mock_team], workflows=[mock_workflow])

        # Should only have 2 routes: /status (GET) and /runs (POST)
        assert mock_ninja_api.get.call_count == 1
        assert mock_ninja_api.post.call_count == 1

        # Verify no separate agent/team/workflow routes
        all_calls = mock_ninja_api.get.call_args_list + mock_ninja_api.post.call_args_list
        for call in all_calls:
            call_str = str(call)
            assert "/agents/" not in call_str
            assert "/teams/" not in call_str
            assert "/workflows/" not in call_str


class TestDjangoNinjaAppPlatformRegistration:
    """Test platform registration functionality."""

    @patch("agno.api.app.create_app")
    def test_platform_registration_with_monitoring_enabled(self, mock_create_app, mock_ninja_api, mock_agent):
        """Test platform registration when monitoring is enabled."""
        app = DjangoNinjaApp(api=mock_ninja_api, agents=[mock_agent], monitoring=True)

        # Platform registration should have been called during initialization
        mock_create_app.assert_called_once()
        mock_agent.register_agent.assert_called_once()

    @patch("agno.api.app.create_app")
    def test_platform_registration_with_monitoring_disabled(self, mock_create_app, mock_ninja_api, mock_agent):
        """Test platform registration when monitoring is disabled."""
        app = DjangoNinjaApp(api=mock_ninja_api, agents=[mock_agent], monitoring=False)

        # Platform registration should not have been called
        mock_create_app.assert_not_called()
        mock_agent.register_agent.assert_not_called()

    @patch("agno.api.app.create_app")
    @patch("agno.app.django.app.logger")
    def test_platform_registration_failure_handled_gracefully(
        self, mock_logger, mock_create_app, mock_ninja_api, mock_agent
    ):
        """Test that platform registration failures are handled gracefully."""
        mock_create_app.side_effect = Exception("Platform unavailable")

        # Should not raise an exception
        app = DjangoNinjaApp(api=mock_ninja_api, agents=[mock_agent], monitoring=True)

        # Should log the error
        mock_logger.debug.assert_called()


class TestDjangoNinjaAppFileProcessing:
    """Test file processing functionality."""

    def test_agent_process_pdf_file(self, mock_ninja_api, mock_agent):
        """Test processing PDF file for agents."""
        app = DjangoNinjaApp(api=mock_ninja_api, agents=[mock_agent])

        mock_file = Mock()
        mock_file.content_type = "application/pdf"
        mock_file.name = "test.pdf"
        mock_file.read = Mock(return_value=b"fake pdf content")

        with patch("agno.document.reader.pdf_reader.PDFReader") as mock_pdf_reader:
            mock_reader_instance = Mock()
            mock_reader_instance.read = Mock(return_value=[])
            mock_pdf_reader.return_value = mock_reader_instance

            images, audios, videos = app._agent_process_file([mock_file], mock_agent)

            assert images == []
            assert audios == []
            assert videos == []
            mock_agent.knowledge.load_documents.assert_called_once()

    def test_agent_process_image_file(self, mock_ninja_api, mock_agent):
        """Test processing image file for agents."""
        app = DjangoNinjaApp(api=mock_ninja_api, agents=[mock_agent])

        mock_file = Mock()
        mock_file.content_type = "image/png"
        mock_file.name = "test.png"

        with patch("agno.app.django.app.process_image") as mock_process_image:
            mock_image = Mock()
            mock_process_image.return_value = mock_image

            images, audios, videos = app._agent_process_file([mock_file], mock_agent)

            assert images == [mock_image]
            assert audios == []
            assert videos == []

    def test_team_process_file(self, mock_ninja_api, mock_team):
        """Test processing files for teams."""
        app = DjangoNinjaApp(api=mock_ninja_api, teams=[mock_team])

        mock_file = Mock()
        mock_file.content_type = "application/pdf"
        mock_file.name = "test.pdf"

        with patch("agno.app.django.app.process_document") as mock_process_document:
            mock_document = Mock()
            mock_process_document.return_value = mock_document

            images, audios, videos, documents = app._team_process_file([mock_file])

            assert images == []
            assert audios == []
            assert videos == []
            assert documents == [mock_document]

    def test_process_unsupported_file_type(self, mock_ninja_api, mock_agent):
        """Test processing unsupported file type raises appropriate error."""
        app = DjangoNinjaApp(api=mock_ninja_api, agents=[mock_agent])

        mock_file = Mock()
        mock_file.content_type = "application/unsupported"
        mock_file.name = "test.unsupported"

        with pytest.raises(ValueError, match="Unsupported file type"):
            app._agent_process_file([mock_file], mock_agent)


class TestDjangoNinjaAppToDictMethod:
    """Test the _to_dict method for platform registration."""

    def test_to_dict_with_agents_only(self, mock_ninja_api, mock_agent):
        """Test _to_dict with agents only."""
        app = DjangoNinjaApp(
            api=mock_ninja_api,
            agents=[mock_agent],
            name="Test App",
            description="Test Description"
        )

        result = app._to_dict()

        assert result["type"] == "django-ninja"
        assert result["description"] == "Test Description"
        assert result["agents"] is not None
        assert len(result["agents"]) == 1
        assert result["teams"] is None
        assert result["workflows"] is None

    def test_to_dict_with_teams_only(self, mock_ninja_api, mock_team):
        """Test _to_dict with teams only."""
        app = DjangoNinjaApp(api=mock_ninja_api, teams=[mock_team])

        result = app._to_dict()

        assert result["agents"] is None
        assert result["teams"] is not None
        assert len(result["teams"]) == 1
        assert result["workflows"] is None

    def test_to_dict_with_workflows_only(self, mock_ninja_api, mock_workflow):
        """Test _to_dict with workflows only."""
        mock_workflow.workflow_id = "test-workflow-id"
        mock_workflow.name = "Test Workflow"

        app = DjangoNinjaApp(api=mock_ninja_api, workflows=[mock_workflow])

        result = app._to_dict()

        assert result["agents"] is None
        assert result["teams"] is None
        assert result["workflows"] is not None
        assert len(result["workflows"]) == 1
        assert result["workflows"][0]["workflow_id"] == "test-workflow-id"
        assert result["workflows"][0]["name"] == "Test Workflow"

    def test_to_dict_with_all_components(self, mock_ninja_api, mock_agent, mock_team, mock_workflow):
        """Test _to_dict with all component types."""
        mock_workflow.workflow_id = "test-workflow-id"
        mock_workflow.name = "Test Workflow"

        app = DjangoNinjaApp(
            api=mock_ninja_api,
            agents=[mock_agent],
            teams=[mock_team],
            workflows=[mock_workflow]
        )

        result = app._to_dict()

        assert result["agents"] is not None
        assert result["teams"] is not None
        assert result["workflows"] is not None
        assert len(result["agents"]) == 1
        assert len(result["teams"]) == 1
        assert len(result["workflows"]) == 1


class TestChatRequestModel:
    """Test ChatRequest model validation."""

    def test_chat_request_required_fields(self):
        """Test ChatRequest with required fields only."""
        request = ChatRequest(message="Hello")
        assert request.message == "Hello"
        assert request.session_id is None
        assert request.user_id is None
        assert request.stream is False

    def test_chat_request_all_fields(self):
        """Test ChatRequest with all fields."""
        request = ChatRequest(
            message="Hello",
            session_id="session-123",
            user_id="user-456",
            stream=True
        )
        assert request.message == "Hello"
        assert request.session_id == "session-123"
        assert request.user_id == "user-456"
        assert request.stream is True

    def test_chat_request_validation(self):
        """Test ChatRequest validation."""
        with pytest.raises(ValueError):
            ChatRequest()  # Missing required message field


class TestChatResponseModel:
    """Test ChatResponse model validation."""

    def test_chat_response_required_fields(self):
        """Test ChatResponse with required fields only."""
        response = ChatResponse(content="Hello back")
        assert response.content == "Hello back"
        assert response.agent_id is None
        assert response.team_id is None
        assert response.session_id is None

    def test_chat_response_all_fields(self):
        """Test ChatResponse with all fields."""
        response = ChatResponse(
            content="Hello back",
            agent_id="agent-123",
            team_id="team-456",
            session_id="session-789"
        )
        assert response.content == "Hello back"
        assert response.agent_id == "agent-123"
        assert response.team_id == "team-456"
        assert response.session_id == "session-789"


class TestDjangoNinjaAppErrorHandling:
    """Test error handling scenarios."""

    def test_agent_initialization_failure(self, mock_ninja_api, mock_agent):
        """Test handling of agent initialization failure."""
        mock_agent.initialize_agent.side_effect = Exception("Initialization failed")

        with pytest.raises(Exception, match="Initialization failed"):
            DjangoNinjaApp(api=mock_ninja_api, agents=[mock_agent])

    def test_team_initialization_failure(self, mock_ninja_api, mock_team):
        """Test handling of team initialization failure."""
        mock_team.initialize_team.side_effect = Exception("Team initialization failed")

        with pytest.raises(Exception, match="Team initialization failed"):
            DjangoNinjaApp(api=mock_ninja_api, teams=[mock_team])

    def test_invalid_api_parameter(self, mock_agent):
        """Test that invalid API parameter raises appropriate error."""
        with pytest.raises(TypeError):
            DjangoNinjaApp(api="not-an-api", agents=[mock_agent])


class TestDjangoNinjaAppTypeValidation:
    """Test type validation and edge cases."""

    def test_empty_component_lists_behavior(self, mock_ninja_api):
        """Test behavior with empty component lists."""
        with pytest.raises(ValueError):
            DjangoNinjaApp(api=mock_ninja_api, agents=[], teams=[], workflows=[])

    def test_components_type_validation(self, mock_ninja_api):
        """Test that component type validation works correctly."""
        # Should work with proper types
        mock_agent = Mock(spec=Agent)
        mock_agent.initialize_agent = Mock()
        DjangoNinjaApp(api=mock_ninja_api, agents=[mock_agent])

        # Should handle mixed valid types
        mock_team = Mock(spec=Team)
        mock_team.initialize_team = Mock()
        mock_team.members = []
        DjangoNinjaApp(api=mock_ninja_api, teams=[mock_team])

    def test_component_names_handling(self, mock_ninja_api):
        """Test handling of components with various name configurations."""
        mock_agent = Mock(spec=Agent)
        mock_agent.name = ""  # Empty name
        mock_agent.agent_id = "empty-name-agent"
        mock_agent.app_id = None
        mock_agent.team_id = None
        mock_agent.initialize_agent = Mock()
        mock_agent.get_agent_config_dict = Mock(return_value={})

        # Should not raise an error
        app = DjangoNinjaApp(api=mock_ninja_api, agents=[mock_agent])
        assert app.agents == [mock_agent]


class TestDjangoNinjaAppIntegrationScenarios:
    """Test complex integration scenarios."""

    def test_complex_initialization_scenario(self, mock_ninja_api):
        """Test complex initialization with multiple components and configurations."""
        # Create multiple agents
        agents = []
        for i in range(3):
            agent = Mock(spec=Agent)
            agent.name = f"agent-{i}"
            agent.agent_id = f"agent-{i}"
            agent.app_id = None
            agent.team_id = None
            agent.initialize_agent = Mock()
            agent.register_agent = Mock()
            agent.get_agent_config_dict = Mock(return_value={"model": f"model-{i}"})
            agents.append(agent)

        # Create teams with agent members
        team_agent = Mock(spec=Agent)
        team_agent.name = "team-agent"
        team_agent.agent_id = "team-agent"
        team_agent.app_id = None
        team_agent.team_id = None
        team_agent.initialize_agent = Mock()

        team = Mock(spec=Team)
        team.name = "test-team"
        team.team_id = "test-team"
        team.app_id = None
        team.members = [team_agent]
        team.initialize_team = Mock()
        team.register_team = Mock()
        team.to_platform_dict = Mock(return_value={"name": "test-team"})

        # Create workflows
        workflow = Mock(spec=Workflow)
        workflow.name = "test-workflow"
        workflow.workflow_id = None
        workflow.app_id = None
        workflow.register_workflow = Mock()

        with patch("agno.app.django.app.generate_id", return_value="generated-workflow-id"):
            app = DjangoNinjaApp(
                api=mock_ninja_api,
                agents=agents,
                teams=[team],
                workflows=[workflow],
                app_id="complex-app-id",
                name="Complex App",
                description="A complex test app",
                require_auth=False,
                monitoring=True,
            )

        # Verify all components were initialized
        assert len(app.agents) == 3
        assert len(app.teams) == 1
        assert len(app.workflows) == 1

        # Verify app IDs were propagated
        for agent in agents:
            assert agent.app_id == "complex-app-id"
        assert team.app_id == "complex-app-id"
        assert team_agent.app_id == "complex-app-id"
        assert team_agent.team_id == "test-team"
        assert workflow.app_id == "complex-app-id"
        assert workflow.workflow_id == "generated-workflow-id"

    @patch("agno.api.app.create_app")
    def test_full_lifecycle_with_monitoring(
        self, mock_create_app, mock_ninja_api, mock_agent, mock_team, mock_workflow
    ):
        """Test full lifecycle including platform registration."""
        mock_workflow.workflow_id = "test-workflow-id"

        app = DjangoNinjaApp(
            api=mock_ninja_api,
            agents=[mock_agent],
            teams=[mock_team],
            workflows=[mock_workflow],
            monitoring=True,
        )

        # Verify platform registration was called
        mock_create_app.assert_called_once()
        mock_agent.register_agent.assert_called_once()
        mock_team.register_team.assert_called_once()
        mock_workflow.register_workflow.assert_called_once()

        # Verify route registration
        assert mock_ninja_api.get.call_count == 1  # /status
        assert mock_ninja_api.post.call_count == 1  # /runs
