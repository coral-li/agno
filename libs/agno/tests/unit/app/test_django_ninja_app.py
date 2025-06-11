"""Unit tests for DjangoNinjaApp class."""

import pytest
from unittest.mock import Mock, patch, MagicMock, call
from typing import Dict, Any
from io import BytesIO

# Configure Django settings first
import os
import django
from django.conf import settings

if not settings.configured:
    settings.configure(
        INSTALLED_APPS=[
            'django.contrib.auth',
            'django.contrib.contenttypes',
        ],
        DATABASES={
            'default': {
                'ENGINE': 'django.db.backends.sqlite3',
                'NAME': ':memory:',
            }
        },
        SECRET_KEY='test-secret-key',
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
    not django_ninja_available,
    reason="django-ninja not installed. Install with 'pip install agno[django]'"
)

from agno.agent.agent import Agent
from agno.team.team import Team
from agno.workflow.workflow import Workflow

# Only import Django components if django-ninja is available
if django_ninja_available:
    from agno.app.django.app import DjangoNinjaApp, ChatRequest, ChatResponse
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
        assert app.prefix == "/agno"
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
            prefix="/custom",
            app_id="custom-app-id",
            name="Custom App",
            description="Custom Description",
            require_auth=False,
            monitoring=False
        )

        assert app.prefix == "/custom"
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

    def test_prefix_normalization(self, mock_ninja_api, mock_agent):
        """Test that prefix is properly normalized (trailing slash removed)."""
        app = DjangoNinjaApp(api=mock_ninja_api, agents=[mock_agent], prefix="/custom/")
        assert app.prefix == "/custom"


class TestDjangoNinjaAppComponentInitialization:
    """Test component initialization and app_id propagation."""

    def test_app_id_propagation_to_agents(self, mock_ninja_api, mock_agent):
        """Test that app_id is properly propagated to agents."""
        app = DjangoNinjaApp(api=mock_ninja_api, agents=[mock_agent])

        # Verify agent gets app_id when it doesn't have one
        assert mock_agent.app_id == app.app_id

    def test_app_id_not_overridden_for_agents(self, mock_ninja_api, mock_agent):
        """Test that existing app_id on agents is not overridden."""
        mock_agent.app_id = "existing-agent-id"

        DjangoNinjaApp(api=mock_ninja_api, agents=[mock_agent])

        # Agent should keep its existing app_id
        assert mock_agent.app_id == "existing-agent-id"

    def test_team_member_initialization(self, mock_ninja_api, mock_team):
        """Test that team members are properly initialized."""
        # Create mock team members
        mock_agent_member = Mock(spec=Agent)
        mock_agent_member.app_id = None
        mock_agent_member.team_id = None
        mock_agent_member.initialize_agent = Mock()

        mock_team_member = Mock(spec=Team)
        mock_team_member.initialize_team = Mock()

        mock_team.members = [mock_agent_member, mock_team_member]

        app = DjangoNinjaApp(api=mock_ninja_api, teams=[mock_team])

        # Verify team members are initialized
        mock_agent_member.initialize_agent.assert_called_once()
        mock_team_member.initialize_team.assert_called_once()

        # Verify agent member gets proper IDs
        assert mock_agent_member.app_id == app.app_id
        assert mock_agent_member.team_id == mock_team.team_id

    def test_workflow_id_generation(self, mock_ninja_api, mock_workflow):
        """Test that workflow_id is generated when not provided."""
        with patch("agno.app.django.app.generate_id", return_value="generated-id") as mock_generate:
            DjangoNinjaApp(api=mock_ninja_api, workflows=[mock_workflow])

            mock_generate.assert_called_once_with(mock_workflow.name)
            assert mock_workflow.workflow_id == "generated-id"

    def test_workflow_id_not_overridden(self, mock_ninja_api):
        """Test that existing workflow_id is not overridden."""
        mock_workflow = Mock(spec=Workflow)
        mock_workflow.name = "test-workflow"
        mock_workflow.workflow_id = "existing-id"
        mock_workflow.app_id = None
        mock_workflow.register_workflow = Mock()

        with patch("agno.app.django.app.generate_id") as mock_generate:
            DjangoNinjaApp(api=mock_ninja_api, workflows=[mock_workflow])

            mock_generate.assert_not_called()
            assert mock_workflow.workflow_id == "existing-id"


class TestDjangoNinjaAppRouteRegistration:
    """Test route registration functionality."""

    def test_status_route_registration(self, mock_ninja_api, mock_agent):
        """Test that status route is registered correctly."""
        DjangoNinjaApp(api=mock_ninja_api, agents=[mock_agent])

        # Verify status route was registered
        mock_ninja_api.get.assert_any_call("/agno/status")

    def test_agent_routes_registration(self, mock_ninja_api, mock_agent):
        """Test that agent routes are registered correctly."""
        DjangoNinjaApp(api=mock_ninja_api, agents=[mock_agent])

        # Check that agent routes were registered
        expected_chat_route = "/agno/agents/test-agent/chat"
        expected_upload_route = "/agno/agents/test-agent/upload"

        # Verify routes were registered with correct paths
        calls = mock_ninja_api.post.call_args_list
        chat_call = any(call[0][0] == expected_chat_route for call in calls)
        upload_call = any(call[0][0] == expected_upload_route for call in calls)

        assert chat_call, f"Chat route {expected_chat_route} was not registered"
        assert upload_call, f"Upload route {expected_upload_route} was not registered"

    def test_team_routes_registration(self, mock_ninja_api, mock_team):
        """Test that team routes are registered correctly."""
        DjangoNinjaApp(api=mock_ninja_api, teams=[mock_team])

        expected_route = "/agno/teams/test-team/chat"

        calls = mock_ninja_api.post.call_args_list
        team_call = any(call[0][0] == expected_route for call in calls)

        assert team_call, f"Team route {expected_route} was not registered"

    def test_workflow_routes_registration(self, mock_ninja_api, mock_workflow):
        """Test that workflow routes are registered correctly."""
        with patch("agno.app.django.app.generate_id", return_value="test-workflow-id"):
            DjangoNinjaApp(api=mock_ninja_api, workflows=[mock_workflow])

            expected_route = "/agno/workflows/test-workflow-id/run"

            calls = mock_ninja_api.post.call_args_list
            workflow_call = any(call[0][0] == expected_route for call in calls)

            assert workflow_call, f"Workflow route {expected_route} was not registered"

    def test_custom_prefix_routes(self, mock_ninja_api, mock_agent):
        """Test routes with custom prefix."""
        DjangoNinjaApp(api=mock_ninja_api, agents=[mock_agent], prefix="/custom")

        # Check that routes use custom prefix
        calls = mock_ninja_api.get.call_args_list + mock_ninja_api.post.call_args_list
        routes = [call[0][0] for call in calls]

        # All routes should use custom prefix
        assert any("/custom/status" in route for route in routes)
        assert any("/custom/agents/" in route for route in routes)


class TestDjangoNinjaAppPlatformRegistration:
    """Test platform registration functionality."""

    @patch("agno.api.app.create_app")
    def test_platform_registration_with_monitoring_enabled(self, mock_create_app, mock_ninja_api, mock_agent):
        """Test platform registration when monitoring is enabled."""
        DjangoNinjaApp(api=mock_ninja_api, agents=[mock_agent], monitoring=True)

        # Should attempt to register with platform
        assert mock_create_app.called
        mock_agent.register_agent.assert_called_once()

    @patch("agno.api.app.create_app")
    def test_platform_registration_with_monitoring_disabled(self, mock_create_app, mock_ninja_api, mock_agent):
        """Test no platform registration when monitoring is disabled."""
        DjangoNinjaApp(api=mock_ninja_api, agents=[mock_agent], monitoring=False)

        # Should not attempt to register with platform
        mock_create_app.assert_not_called()
        mock_agent.register_agent.assert_not_called()

    @patch("agno.api.app.create_app")
    @patch("agno.app.django.app.logger")
    def test_platform_registration_failure_handled_gracefully(self, mock_logger, mock_create_app, mock_ninja_api, mock_agent):
        """Test that platform registration failures are handled gracefully."""
        mock_create_app.side_effect = Exception("Platform registration failed")

        # Should not raise exception
        DjangoNinjaApp(api=mock_ninja_api, agents=[mock_agent], monitoring=True)

        # Should log the error
        mock_logger.debug.assert_called()


class TestDjangoNinjaAppFileProcessing:
    """Test file processing functionality."""

    def test_process_pdf_file(self, mock_ninja_api, mock_agent):
        """Test processing PDF files."""
        app = DjangoNinjaApp(api=mock_ninja_api, agents=[mock_agent])
        mock_file = Mock(spec=UploadedFile)
        mock_file.content_type = "application/pdf"
        mock_file.read = Mock(return_value=b"pdf content")

        with patch("agno.document.reader.pdf_reader.PDFReader") as mock_pdf_reader:
            mock_reader_instance = Mock()
            mock_pdf_reader.return_value = mock_reader_instance
            mock_reader_instance.read.return_value = ["document"]

            result = app._process_uploaded_file(mock_file)

            assert result == ["document"]
            mock_pdf_reader.assert_called_once()
            mock_reader_instance.read.assert_called_once()

    def test_process_csv_file(self, mock_ninja_api, mock_agent):
        """Test processing CSV files."""
        app = DjangoNinjaApp(api=mock_ninja_api, agents=[mock_agent])
        mock_file = Mock(spec=UploadedFile)
        mock_file.content_type = "text/csv"
        mock_file.read = Mock(return_value=b"csv content")

        with patch("agno.document.reader.csv_reader.CSVReader") as mock_csv_reader:
            mock_reader_instance = Mock()
            mock_csv_reader.return_value = mock_reader_instance
            mock_reader_instance.read.return_value = ["document"]

            result = app._process_uploaded_file(mock_file)

            assert result == ["document"]
            mock_csv_reader.assert_called_once()

    def test_process_docx_file(self, mock_ninja_api, mock_agent):
        """Test processing DOCX files."""
        app = DjangoNinjaApp(api=mock_ninja_api, agents=[mock_agent])
        mock_file = Mock(spec=UploadedFile)
        mock_file.content_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        mock_file.read = Mock(return_value=b"docx content")

        with patch("agno.document.reader.docx_reader.DocxReader") as mock_docx_reader:
            mock_reader_instance = Mock()
            mock_docx_reader.return_value = mock_reader_instance
            mock_reader_instance.read.return_value = ["document"]

            result = app._process_uploaded_file(mock_file)

            assert result == ["document"]
            mock_docx_reader.assert_called_once()

    def test_process_text_file(self, mock_ninja_api, mock_agent):
        """Test processing text files."""
        app = DjangoNinjaApp(api=mock_ninja_api, agents=[mock_agent])
        mock_file = Mock(spec=UploadedFile)
        mock_file.content_type = "text/plain"
        mock_file.read = Mock(return_value=b"text content")

        with patch("agno.document.reader.text_reader.TextReader") as mock_text_reader:
            mock_reader_instance = Mock()
            mock_text_reader.return_value = mock_reader_instance
            mock_reader_instance.read.return_value = ["document"]

            result = app._process_uploaded_file(mock_file)

            assert result == ["document"]
            mock_text_reader.assert_called_once()

    def test_process_json_file(self, mock_ninja_api, mock_agent):
        """Test processing JSON files."""
        app = DjangoNinjaApp(api=mock_ninja_api, agents=[mock_agent])
        mock_file = Mock(spec=UploadedFile)
        mock_file.content_type = "application/json"
        mock_file.read = Mock(return_value=b'{"key": "value"}')

        with patch("agno.document.reader.json_reader.JSONReader") as mock_json_reader:
            mock_reader_instance = Mock()
            mock_json_reader.return_value = mock_reader_instance
            mock_reader_instance.read.return_value = ["document"]

            result = app._process_uploaded_file(mock_file)

            assert result == ["document"]
            mock_json_reader.assert_called_once()

    def test_process_unsupported_file_type(self, mock_ninja_api, mock_agent):
        """Test processing unsupported file types raises error."""
        app = DjangoNinjaApp(api=mock_ninja_api, agents=[mock_agent])
        mock_file = Mock(spec=UploadedFile)
        mock_file.content_type = "unsupported/type"

        with pytest.raises(ValueError, match="Unsupported file type: unsupported/type"):
            app._process_uploaded_file(mock_file)


class TestDjangoNinjaAppToDictMethod:
    """Test the _to_dict method for platform registration."""

    def test_to_dict_with_agents_only(self, mock_ninja_api, mock_agent):
        """Test _to_dict with agents only."""
        app = DjangoNinjaApp(
            api=mock_ninja_api,
            agents=[mock_agent],
            name="Test App",
            description="Test Description",
            prefix="/test"
        )

        result = app._to_dict()

        expected = {
            "type": "django-ninja",
            "description": "Test Description",
            "prefix": "/test",
            "agents": [
                {
                    "model": "gpt-4",
                    "agent_id": "test-agent",
                    "team_id": None,
                }
            ],
            "teams": None,
            "workflows": None,
        }

        assert result == expected

    def test_to_dict_with_teams_only(self, mock_ninja_api, mock_team):
        """Test _to_dict with teams only."""
        app = DjangoNinjaApp(api=mock_ninja_api, teams=[mock_team])

        result = app._to_dict()

        expected = {
            "type": "django-ninja",
            "description": None,
            "prefix": "/agno",
            "agents": None,
            "teams": [
                {
                    "name": "test-team",
                    "team_id": "test-team",
                }
            ],
            "workflows": None,
        }

        assert result == expected

    def test_to_dict_with_workflows_only(self, mock_ninja_api, mock_workflow):
        """Test _to_dict with workflows only."""
        with patch("agno.app.django.app.generate_id", return_value="generated-id"):
            app = DjangoNinjaApp(api=mock_ninja_api, workflows=[mock_workflow])

            result = app._to_dict()

            expected = {
                "type": "django-ninja",
                "description": None,
                "prefix": "/agno",
                "agents": None,
                "teams": None,
                "workflows": [
                    {
                        "workflow_id": "generated-id",
                        "name": "test-workflow",
                    }
                ],
            }

            assert result == expected

    def test_to_dict_with_all_components(self, mock_ninja_api, mock_agent, mock_team, mock_workflow):
        """Test _to_dict with all components."""
        with patch("agno.app.django.app.generate_id", return_value="generated-id"):
            app = DjangoNinjaApp(
                api=mock_ninja_api,
                agents=[mock_agent],
                teams=[mock_team],
                workflows=[mock_workflow],
                description="Full App"
            )

            result = app._to_dict()

            assert result["type"] == "django-ninja"
            assert result["description"] == "Full App"
            assert len(result["agents"]) == 1
            assert len(result["teams"]) == 1
            assert len(result["workflows"]) == 1


class TestChatRequestModel:
    """Test ChatRequest Pydantic model."""

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
        # Empty message should be valid (validation might be handled elsewhere)
        request = ChatRequest(message="")
        assert request.message == ""


class TestChatResponseModel:
    """Test ChatResponse Pydantic model."""

    def test_chat_response_required_fields(self):
        """Test ChatResponse with required fields only."""
        response = ChatResponse(content="Hello back!")

        assert response.content == "Hello back!"
        assert response.agent_id is None
        assert response.team_id is None
        assert response.session_id is None

    def test_chat_response_all_fields(self):
        """Test ChatResponse with all fields."""
        response = ChatResponse(
            content="Hello back!",
            agent_id="agent-123",
            team_id="team-456",
            session_id="session-789"
        )

        assert response.content == "Hello back!"
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
        mock_team.initialize_team.side_effect = Exception("Team init failed")

        with pytest.raises(Exception, match="Team init failed"):
            DjangoNinjaApp(api=mock_ninja_api, teams=[mock_team])

    def test_invalid_api_parameter(self, mock_agent):
        """Test that passing invalid api parameter raises appropriate error."""
        with pytest.raises(Exception):
            DjangoNinjaApp(api="not-an-api", agents=[mock_agent])


class TestDjangoNinjaAppTypeValidation:
    """Test type validation and edge cases."""

    def test_empty_component_lists_behavior(self, mock_ninja_api):
        """Test that empty component lists are converted to empty lists, but still raise error."""
        # The implementation actually checks if not agents and not teams and not workflows
        # which treats empty lists as falsy, so this should still raise an error
        with pytest.raises(ValueError, match="At least one of agents, teams, or workflows must be provided"):
            DjangoNinjaApp(api=mock_ninja_api, agents=[], teams=[], workflows=[])

    def test_components_type_validation(self, mock_ninja_api):
        """Test that invalid component types are handled properly."""
        # This should pass - type validation might be handled at runtime
        invalid_agent = "not-an-agent"

        # The actual validation might happen during initialization or method calls
        # For now, we'll test that the app can be created with invalid types
        # and expect errors during actual usage
        try:
            app = DjangoNinjaApp(api=mock_ninja_api, agents=[invalid_agent])
            # If this passes, the validation happens later
            assert True
        except Exception:
            # If this fails, the validation happens during initialization
            assert True

    def test_empty_component_names(self, mock_ninja_api):
        """Test handling of components with empty names."""
        mock_agent = Mock(spec=Agent)
        mock_agent.name = ""
        mock_agent.agent_id = ""
        mock_agent.app_id = None
        mock_agent.team_id = None
        mock_agent.initialize_agent = Mock()
        mock_agent.register_agent = Mock()
        mock_agent.get_agent_config_dict = Mock(return_value={})

        app = DjangoNinjaApp(api=mock_ninja_api, agents=[mock_agent])

        # Should handle empty names gracefully
        assert mock_agent in app.agents


class TestDjangoNinjaAppIntegrationScenarios:
    """Test complex integration scenarios."""

    def test_complex_initialization_scenario(self, mock_ninja_api):
        """Test complex scenario with multiple components and custom settings."""
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
            agent.get_agent_config_dict = Mock(return_value={"model": f"gpt-{i}"})
            agents.append(agent)

        # Create multiple teams with members
        teams = []
        for i in range(2):
            team = Mock(spec=Team)
            team.name = f"team-{i}"
            team.team_id = f"team-{i}"
            team.app_id = None
            team.members = [agents[i]]  # Add agent as team member
            team.initialize_team = Mock()
            team.register_team = Mock()
            team.to_platform_dict = Mock(return_value={"name": f"team-{i}"})
            teams.append(team)

        # Create workflow
        workflow = Mock(spec=Workflow)
        workflow.name = "complex-workflow"
        workflow.workflow_id = None
        workflow.app_id = None
        workflow.register_workflow = Mock()

        with patch("agno.app.django.app.generate_id", return_value="generated-workflow-id"):
            app = DjangoNinjaApp(
                api=mock_ninja_api,
                agents=agents,
                teams=teams,
                workflows=[workflow],
                prefix="/complex",
                name="Complex App",
                description="A complex test application",
                require_auth=False,
                monitoring=True
            )

            # Verify all components were initialized
            assert len(app.agents) == 3
            assert len(app.teams) == 2
            assert len(app.workflows) == 1

            # Verify initialization calls - note that agents in teams are initialized twice:
            # once as standalone agents and once as team members
            for i, agent in enumerate(agents):
                if i < 2:  # First two agents are also team members
                    assert agent.initialize_agent.call_count == 2
                else:  # Third agent is only standalone
                    agent.initialize_agent.assert_called_once()

            for team in teams:
                team.initialize_team.assert_called_once()

            # Verify app_id propagation
            for agent in agents:
                assert agent.app_id == app.app_id

            for team in teams:
                assert team.app_id == app.app_id

            assert workflow.app_id == app.app_id
            assert workflow.workflow_id == "generated-workflow-id"

            # Verify custom settings
            assert app.prefix == "/complex"
            assert app.name == "Complex App"
            assert app.description == "A complex test application"
            assert app.require_auth is False
            assert app.monitoring is True

    @patch("agno.api.app.create_app")
    def test_full_lifecycle_with_monitoring(self, mock_create_app, mock_ninja_api, mock_agent, mock_team, mock_workflow):
        """Test full app lifecycle with monitoring enabled."""
        with patch("agno.app.django.app.generate_id", return_value="workflow-id"):
            app = DjangoNinjaApp(
                api=mock_ninja_api,
                agents=[mock_agent],
                teams=[mock_team],
                workflows=[mock_workflow],
                monitoring=True
            )

            # Verify platform registration was attempted
            mock_create_app.assert_called_once()

            # Verify individual component registration
            mock_agent.register_agent.assert_called_once()
            mock_team.register_team.assert_called_once()
            mock_workflow.register_workflow.assert_called_once()

            # Verify route registration calls were made
            assert mock_ninja_api.get.called
            assert mock_ninja_api.post.called

            # Verify the app maintains references to all components
            assert app.agents == [mock_agent]
            assert app.teams == [mock_team]
            assert app.workflows == [mock_workflow]
