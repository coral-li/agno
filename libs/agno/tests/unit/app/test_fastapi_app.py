"""Unit tests for FastAPIApp class."""

import pytest
from unittest.mock import Mock, patch

from fastapi import FastAPI
from fastapi.routing import APIRouter

from agno.agent.agent import Agent
from agno.app.fastapi.app import FastAPIApp
from agno.app.settings import APIAppSettings
from agno.team.team import Team
from agno.workflow.workflow import Workflow


@pytest.fixture
def mock_agent():
    """Create a mock Agent instance."""
    agent = Mock(spec=Agent)
    agent.name = "test-agent"
    agent.app_id = None
    agent.team_id = None
    agent.initialize_agent = Mock()
    agent.register_agent = Mock()
    return agent


@pytest.fixture
def mock_team():
    """Create a mock Team instance."""
    team = Mock(spec=Team)
    team.name = "test-team"
    team.app_id = None
    team.members = []
    team.initialize_team = Mock()
    team.register_team = Mock()
    return team


@pytest.fixture
def mock_workflow():
    """Create a mock Workflow instance."""
    workflow = Mock(spec=Workflow)
    workflow.name = "test-workflow"
    workflow.app_id = None
    workflow.workflow_id = "test-workflow"  # Default to the name, like BaseAgno.set_id() does
    workflow.register_workflow = Mock()
    return workflow


@pytest.fixture
def mock_settings():
    """Create mock APIAppSettings."""
    return Mock(spec=APIAppSettings)


@pytest.fixture
def mock_fastapi():
    """Create a mock FastAPI instance."""
    return Mock(spec=FastAPI)


@pytest.fixture
def mock_router():
    """Create a mock APIRouter instance."""
    return Mock(spec=APIRouter)


class TestFastAPIAppInitialization:
    """Test FastAPIApp initialization scenarios."""

    def test_init_with_agents_only(self, mock_agent):
        """Test initialization with agents only."""
        app = FastAPIApp(agents=[mock_agent])

        assert app.agents == [mock_agent]
        assert app.teams is None
        assert app.workflows is None
        assert isinstance(app.settings, APIAppSettings)
        assert app.monitoring is True
        mock_agent.initialize_agent.assert_called_once()

    def test_init_with_teams_only(self, mock_team):
        """Test initialization with teams only."""
        app = FastAPIApp(teams=[mock_team])

        assert app.agents is None
        assert app.teams == [mock_team]
        assert app.workflows is None
        mock_team.initialize_team.assert_called_once()

    def test_init_with_workflows_only(self, mock_workflow):
        """Test initialization with workflows only."""
        # Create a new mock to avoid state issues
        test_workflow = Mock()
        test_workflow.name = "test-workflow"
        test_workflow.app_id = None
        test_workflow.workflow_id = None
        test_workflow.register_workflow = Mock()

        with patch("agno.app.fastapi.app.generate_id", return_value="generated-workflow-id") as mock_generate_id:
            app = FastAPIApp(workflows=[test_workflow])

            assert app.agents is None
            assert app.teams is None
            assert app.workflows == [test_workflow]
            # Verify that generate_id was called and workflow_id was set
            mock_generate_id.assert_called_once_with("test-workflow")
            assert test_workflow.workflow_id == "generated-workflow-id"

    def test_init_with_all_components(self, mock_agent, mock_team, mock_workflow):
        """Test initialization with all component types."""
        with patch("agno.app.fastapi.app.generate_id", return_value="generated-workflow-id"):
            app = FastAPIApp(
                agents=[mock_agent],
                teams=[mock_team],
                workflows=[mock_workflow]
            )

            assert app.agents == [mock_agent]
            assert app.teams == [mock_team]
            assert app.workflows == [mock_workflow]
            mock_agent.initialize_agent.assert_called_once()
            mock_team.initialize_team.assert_called_once()

    def test_init_with_custom_settings(self, mock_agent, mock_settings):
        """Test initialization with custom settings."""
        app = FastAPIApp(agents=[mock_agent], settings=mock_settings)

        assert app.settings == mock_settings

    def test_init_with_custom_components(self, mock_agent, mock_fastapi, mock_router):
        """Test initialization with custom FastAPI and router instances."""
        app = FastAPIApp(
            agents=[mock_agent],
            api_app=mock_fastapi,
            router=mock_router
        )

        assert app.api_app == mock_fastapi
        assert app.router == mock_router

    def test_init_with_app_metadata(self, mock_agent):
        """Test initialization with app metadata."""
        app = FastAPIApp(
            agents=[mock_agent],
            app_id="custom-app-id",
            name="Test App",
            description="Test Description",
            monitoring=False
        )

        assert app.app_id == "custom-app-id"
        assert app.name == "Test App"
        assert app.description == "Test Description"
        assert app.monitoring is False

    def test_init_no_components_raises_error(self):
        """Test that initialization without any components raises ValueError."""
        with pytest.raises(ValueError, match="Either agents, teams or workflows must be provided"):
            FastAPIApp()

    def test_init_empty_lists_raises_error(self):
        """Test that initialization with empty lists raises ValueError."""
        with pytest.raises(ValueError, match="Either agents, teams or workflows must be provided"):
            FastAPIApp(agents=[], teams=[], workflows=[])


class TestFastAPIAppComponentInitialization:
    """Test component initialization and app_id propagation."""

    def test_app_id_propagation_to_agents(self, mock_agent):
        """Test that app_id is properly propagated to agents."""
        app = FastAPIApp(agents=[mock_agent])

        # Verify agent gets app_id when it doesn't have one
        assert mock_agent.app_id == app.app_id

    def test_app_id_not_overridden_for_agents(self, mock_agent):
        """Test that existing app_id on agents is not overridden."""
        mock_agent.app_id = "existing-agent-id"

        FastAPIApp(agents=[mock_agent])

        # Agent should keep its existing app_id
        assert mock_agent.app_id == "existing-agent-id"

    def test_team_member_initialization(self, mock_team):
        """Test that team members are properly initialized."""
        # Create mock team members
        mock_agent_member = Mock(spec=Agent)
        mock_agent_member.app_id = None
        mock_agent_member.team_id = "existing-team-id"
        mock_agent_member.initialize_agent = Mock()

        mock_team_member = Mock(spec=Team)
        mock_team_member.initialize_team = Mock()

        mock_team.members = [mock_agent_member, mock_team_member]

        app = FastAPIApp(teams=[mock_team])

        # Verify agent member initialization
        mock_agent_member.initialize_agent.assert_called_once()
        assert mock_agent_member.app_id == app.app_id
        assert mock_agent_member.team_id is None  # Should be reset

        # Verify team member initialization
        mock_team_member.initialize_team.assert_called_once()

    def test_workflow_id_generation(self, mock_workflow):
        """Test that workflow_id is generated when not provided."""
        # Create a fresh mock to ensure clean state - don't use spec to avoid state issues
        test_workflow = Mock()
        test_workflow.name = "test-workflow"
        test_workflow.app_id = None
        test_workflow.workflow_id = None
        test_workflow.register_workflow = Mock()

        with patch("agno.app.fastapi.app.generate_id", return_value="generated-id") as mock_generate_id:
            FastAPIApp(workflows=[test_workflow])

            mock_generate_id.assert_called_once_with("test-workflow")
            assert test_workflow.workflow_id == "generated-id"

    def test_workflow_id_not_overridden(self):
        """Test that existing workflow_id is not overridden."""
        # Create a fresh mock with existing workflow_id
        test_workflow = Mock()
        test_workflow.name = "test-workflow"
        test_workflow.app_id = None
        test_workflow.workflow_id = "existing-workflow-id"
        test_workflow.register_workflow = Mock()

        with patch("agno.app.fastapi.app.generate_id") as mock_generate_id:
            FastAPIApp(workflows=[test_workflow])

            mock_generate_id.assert_not_called()
            assert test_workflow.workflow_id == "existing-workflow-id"


class TestFastAPIAppRouterMethods:
    """Test router method functionality."""

    @patch("agno.app.fastapi.app.get_sync_router")
    def test_get_router(self, mock_get_sync_router, mock_agent, mock_team, mock_workflow):
        """Test get_router method."""
        mock_router = Mock(spec=APIRouter)
        mock_get_sync_router.return_value = mock_router

        app = FastAPIApp(agents=[mock_agent], teams=[mock_team], workflows=[mock_workflow])
        result = app.get_router()

        assert result == mock_router
        mock_get_sync_router.assert_called_once_with(
            agents=[mock_agent],
            teams=[mock_team],
            workflows=[mock_workflow]
        )

    @patch("agno.app.fastapi.app.get_async_router")
    def test_get_async_router(self, mock_get_async_router, mock_agent, mock_team, mock_workflow):
        """Test get_async_router method."""
        mock_router = Mock(spec=APIRouter)
        mock_get_async_router.return_value = mock_router

        app = FastAPIApp(agents=[mock_agent], teams=[mock_team], workflows=[mock_workflow])
        result = app.get_async_router()

        assert result == mock_router
        mock_get_async_router.assert_called_once_with(
            agents=[mock_agent],
            teams=[mock_team],
            workflows=[mock_workflow]
        )


class TestFastAPIAppServeMethod:
    """Test serve method functionality."""

    @patch("agno.app.fastapi.app.uvicorn.run")
    @patch("agno.app.fastapi.app.log_info")
    def test_serve_with_agents(self, mock_log_info, mock_uvicorn_run, mock_agent):
        """Test serve method with agents."""
        app = FastAPIApp(agents=[mock_agent])
        app.set_app_id = Mock()
        app.register_app_on_platform = Mock()

        app.serve("test:app", host="0.0.0.0", port=8000, reload=True)

        # Verify setup calls
        app.set_app_id.assert_called_once()
        app.register_app_on_platform.assert_called_once()
        mock_agent.register_agent.assert_called_once()

        # Verify uvicorn call
        mock_uvicorn_run.assert_called_once_with(
            app="test:app",
            host="0.0.0.0",
            port=8000,
            reload=True
        )

        # Verify logging
        mock_log_info.assert_called_once_with("Starting API on 0.0.0.0:8000")

    @patch("agno.app.fastapi.app.uvicorn.run")
    @patch("agno.app.fastapi.app.log_info")
    def test_serve_with_teams(self, mock_log_info, mock_uvicorn_run, mock_team):
        """Test serve method with teams."""
        app = FastAPIApp(teams=[mock_team])
        app.set_app_id = Mock()
        app.register_app_on_platform = Mock()

        app.serve("test:app")

        # Verify setup calls
        app.set_app_id.assert_called_once()
        app.register_app_on_platform.assert_called_once()
        mock_team.register_team.assert_called_once()

        # Verify uvicorn call with defaults
        mock_uvicorn_run.assert_called_once_with(
            app="test:app",
            host="localhost",
            port=7777,
            reload=False
        )

    @patch("agno.app.fastapi.app.uvicorn.run")
    @patch("agno.app.fastapi.app.log_info")
    def test_serve_with_workflows(self, mock_log_info, mock_uvicorn_run, mock_workflow):
        """Test serve method with workflows."""
        app = FastAPIApp(workflows=[mock_workflow])
        app.set_app_id = Mock()
        app.register_app_on_platform = Mock()

        app.serve("test:app")

        # Verify setup calls
        app.set_app_id.assert_called_once()
        app.register_app_on_platform.assert_called_once()
        mock_workflow.register_workflow.assert_called_once()

    @patch("agno.app.fastapi.app.uvicorn.run")
    @patch("agno.app.fastapi.app.log_info")
    def test_serve_with_all_components(self, mock_log_info, mock_uvicorn_run, mock_agent, mock_team, mock_workflow):
        """Test serve method with all component types."""
        app = FastAPIApp(agents=[mock_agent], teams=[mock_team], workflows=[mock_workflow])
        app.set_app_id = Mock()
        app.register_app_on_platform = Mock()

        app.serve("test:app")

        # Verify all components are registered
        mock_agent.register_agent.assert_called_once()
        mock_team.register_team.assert_called_once()
        mock_workflow.register_workflow.assert_called_once()

    @patch("agno.app.fastapi.app.uvicorn.run")
    @patch("agno.app.fastapi.app.log_info")
    def test_serve_with_fastapi_instance(self, mock_log_info, mock_uvicorn_run, mock_agent, mock_fastapi):
        """Test serve method with FastAPI instance instead of string."""
        app = FastAPIApp(agents=[mock_agent])
        app.set_app_id = Mock()
        app.register_app_on_platform = Mock()

        app.serve(mock_fastapi, host="127.0.0.1", port=9000)

        mock_uvicorn_run.assert_called_once_with(
            app=mock_fastapi,
            host="127.0.0.1",
            port=9000,
            reload=False
        )

    @patch("agno.app.fastapi.app.uvicorn.run")
    @patch("agno.app.fastapi.app.log_info")
    def test_serve_with_extra_kwargs(self, mock_log_info, mock_uvicorn_run, mock_agent):
        """Test serve method with additional uvicorn kwargs."""
        app = FastAPIApp(agents=[mock_agent])
        app.set_app_id = Mock()
        app.register_app_on_platform = Mock()

        app.serve("test:app", workers=4, log_level="debug", access_log=False)

        mock_uvicorn_run.assert_called_once_with(
            app="test:app",
            host="localhost",
            port=7777,
            reload=False,
            workers=4,
            log_level="debug",
            access_log=False
        )


class TestFastAPIAppErrorHandling:
    """Test error handling scenarios."""

    def test_init_with_none_values(self):
        """Test initialization with None values for lists."""
        with pytest.raises(ValueError, match="Either agents, teams or workflows must be provided"):
            FastAPIApp(agents=None, teams=None, workflows=None)

    def test_agent_initialization_failure(self, mock_agent):
        """Test handling of agent initialization failure."""
        mock_agent.initialize_agent.side_effect = Exception("Agent init failed")

        # Should not raise exception during FastAPIApp init
        # The exception should be handled gracefully or propagated appropriately
        with pytest.raises(Exception, match="Agent init failed"):
            FastAPIApp(agents=[mock_agent])

    def test_team_initialization_failure(self, mock_team):
        """Test handling of team initialization failure."""
        mock_team.initialize_team.side_effect = Exception("Team init failed")

        with pytest.raises(Exception, match="Team init failed"):
            FastAPIApp(teams=[mock_team])

    @patch("agno.app.fastapi.app.uvicorn.run")
    def test_serve_registration_failure(self, mock_uvicorn_run, mock_agent):
        """Test handling of registration failure during serve."""
        app = FastAPIApp(agents=[mock_agent])
        app.set_app_id = Mock()
        app.register_app_on_platform = Mock()
        mock_agent.register_agent.side_effect = Exception("Registration failed")

        with pytest.raises(Exception, match="Registration failed"):
            app.serve("test:app")


class TestFastAPIAppTypeValidation:
    """Test type validation and class properties."""

    def test_app_type_property(self, mock_agent):
        """Test that the app type is correctly set."""
        app = FastAPIApp(agents=[mock_agent])
        assert app.type == "fastapi"

    def test_isinstance_validation(self, mock_agent):
        """Test that the app is an instance of BaseAPIApp."""
        from agno.app.base import BaseAPIApp

        app = FastAPIApp(agents=[mock_agent])
        assert isinstance(app, BaseAPIApp)

    def test_components_type_validation(self):
        """Test type validation for component lists."""
        # Test with non-list types - the actual implementation will try to iterate
        # over the string and access .app_id on each character, causing AttributeError
        with pytest.raises(AttributeError, match="'str' object has no attribute 'app_id'"):
            FastAPIApp(agents="not-a-list")  # type: ignore


class TestFastAPIAppIntegration:
    """Test integration scenarios with multiple components."""

    def test_complex_initialization_scenario(self):
        """Test complex initialization with multiple components and configurations."""
        # Create multiple mock components
        agents = [Mock(spec=Agent) for _ in range(3)]
        teams = [Mock(spec=Team) for _ in range(2)]
        workflows = [Mock(spec=Workflow) for _ in range(2)]

        # Set up mocks
        for i, agent in enumerate(agents):
            agent.name = f"agent-{i}"
            agent.app_id = None
            agent.team_id = None
            agent.initialize_agent = Mock()
            agent.register_agent = Mock()

        for i, team in enumerate(teams):
            team.name = f"team-{i}"
            team.app_id = None
            team.members = []
            team.initialize_team = Mock()
            team.register_team = Mock()

        for i, workflow in enumerate(workflows):
            workflow.name = f"workflow-{i}"
            workflow.app_id = None
            workflow.workflow_id = None
            workflow.register_workflow = Mock()

        with patch("agno.app.utils.generate_id", side_effect=lambda name: f"generated-{name}"):
            app = FastAPIApp(
                agents=agents,
                teams=teams,
                workflows=workflows,
                name="Complex App",
                description="Complex test scenario"
            )

            # Verify all components are properly initialized
            assert len(app.agents) == 3
            assert len(app.teams) == 2
            assert len(app.workflows) == 2

            # Verify initialization was called for all components
            for agent in agents:
                agent.initialize_agent.assert_called_once()
            for team in teams:
                team.initialize_team.assert_called_once()

    @patch("agno.app.fastapi.app.uvicorn.run")
    @patch("agno.app.fastapi.app.log_info")
    def test_full_serve_lifecycle(self, mock_log_info, mock_uvicorn_run):
        """Test complete serve lifecycle with all component types."""
        # Create mock components
        mock_agent = Mock(spec=Agent)
        mock_agent.name = "test-agent"
        mock_agent.app_id = None
        mock_agent.team_id = None
        mock_agent.initialize_agent = Mock()
        mock_agent.register_agent = Mock()

        mock_team = Mock(spec=Team)
        mock_team.name = "test-team"
        mock_team.app_id = None
        mock_team.members = []
        mock_team.initialize_team = Mock()
        mock_team.register_team = Mock()

        mock_workflow = Mock(spec=Workflow)
        mock_workflow.name = "test-workflow"
        mock_workflow.app_id = None
        mock_workflow.workflow_id = "existing-id"
        mock_workflow.register_workflow = Mock()

        app = FastAPIApp(
            agents=[mock_agent],
            teams=[mock_team],
            workflows=[mock_workflow]
        )
        app.set_app_id = Mock()
        app.register_app_on_platform = Mock()

        # Serve the app
        app.serve("test:app", host="0.0.0.0", port=8080)

        # Verify complete lifecycle
        app.set_app_id.assert_called_once()
        app.register_app_on_platform.assert_called_once()
        mock_agent.register_agent.assert_called_once()
        mock_team.register_team.assert_called_once()
        mock_workflow.register_workflow.assert_called_once()

        mock_uvicorn_run.assert_called_once_with(
            app="test:app",
            host="0.0.0.0",
            port=8080,
            reload=False
        )

        mock_log_info.assert_called_once_with("Starting API on 0.0.0.0:8080")
