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
