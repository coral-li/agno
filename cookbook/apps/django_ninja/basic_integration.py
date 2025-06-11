"""
Basic Django-Ninja integration example for Agno.

This example demonstrates how to integrate Agno agents into a Django project
using django-ninja for API routing with the new universal /runs endpoint.

To use this example:
1. Install django and django-ninja: pip install agno[django]
2. Create a Django project and app
3. Add the integration to your Django app
4. Run the server and test the endpoints

Key endpoints created:
- GET /api/status - Check integration status
- POST /api/runs - Universal endpoint for all AI interactions

Usage examples:
- POST /api/runs?agent_id=assistant (chat with agent)
- POST /api/runs?team_id=content-team (chat with team)
- POST /api/runs?workflow_id=analysis (run workflow)
"""

from agno import Agent, Team
from agno.app.django import DjangoNinjaApp
from ninja import NinjaAPI

# Create your ninja API (this would be in your Django app)
api = NinjaAPI()


# Add your existing Django routes
@api.get("/users")
def list_users(request):
    """Example existing endpoint."""
    return {"users": ["user1", "user2"]}


@api.get("/health")
def health_check(request):
    """Health check endpoint."""
    return {"status": "healthy"}


# Create Agno agents
assistant_agent = Agent(
    name="assistant",
    model="gpt-4",
    instructions="You are a helpful assistant that can answer questions and help with tasks.",
)

customer_service_agent = Agent(
    name="customer-service",
    model="gpt-4",
    instructions="You are a customer service representative. Be polite, helpful, and professional.",
)

# Create a team (optional)
support_team = Team(
    name="support-team",
    members=[assistant_agent, customer_service_agent],
    instructions="Work together to provide excellent customer support.",
)

# Add Agno integration to your existing API
agno_app = DjangoNinjaApp(
    api=api,
    agents=[assistant_agent, customer_service_agent],
    teams=[support_team],
    name="My Django AI App",
    description="Django-Ninja integration with Agno AI agents and teams",
    require_auth=False,  # Set to True to require Django authentication
    monitoring=True,     # Enable platform monitoring
)

# Now you have these endpoints available:
# GET  /api/users (your existing route)
# GET  /api/health (your existing route)
# GET  /api/status (Agno status check)
# POST /api/runs (Universal AI endpoint)

# Usage examples for the /runs endpoint:

# 1. Chat with assistant agent
# curl -X POST "http://localhost:8000/api/runs?agent_id=assistant" \
#   -F "message=Hello, how can you help me?" \
#   -F "stream=false"

# 2. Chat with customer service agent
# curl -X POST "http://localhost:8000/api/runs?agent_id=customer-service" \
#   -F "message=I need help with my order" \
#   -F "stream=true"

# 3. Chat with support team
# curl -X POST "http://localhost:8000/api/runs?team_id=support-team" \
#   -F "message=I have a technical issue" \
#   -F "stream=true"

# 4. Upload files with message
# curl -X POST "http://localhost:8000/api/runs?agent_id=assistant" \
#   -F "message=Analyze this document" \
#   -F "files=@document.pdf" \
#   -F "stream=false"


# In your Django urls.py, you would include:
# from django.urls import path
# from .api import api
#
# urlpatterns = [
#     path('admin/', admin.site.urls),
#     path('api/', api.urls),
# ]


# Example usage in your Django views or other code:
def example_programmatic_usage():
    """Example of how to interact with agents programmatically."""
    # Direct agent interaction (not through API)
    response = assistant_agent.run("What is the weather like today?")
    print(f"Assistant: {response.content}")

    # Direct customer service agent interaction
    response = customer_service_agent.run("I need help with my order")
    print(f"Customer Service: {response.content}")

    # Direct team interaction
    response = support_team.run("Can you help me troubleshoot a technical issue?")
    print(f"Support Team: {response.content}")


# Example test for the integration
def example_test():
    """Example test using the testing utilities."""
    from agno.app.django.testing import AgnoTestCase
    from ninja.testing import TestClient

    class TestDjangoNinjaIntegration(AgnoTestCase):
        def test_agent_chat(self):
            """Test agent chat through API."""
            client = TestClient(api)

            response = client.post(
                "/runs",
                params={"agent_id": "assistant"},
                data={"message": "Hello", "stream": False}
            )

            assert response.status_code == 200
            data = response.json()
            assert "content" in data
            assert data.get("agent_id") == "assistant"

        def test_team_chat(self):
            """Test team chat through API."""
            client = TestClient(api)

            response = client.post(
                "/runs",
                params={"team_id": "support-team"},
                data={"message": "I need help", "stream": False}
            )

            assert response.status_code == 200

        def test_file_upload(self):
            """Test file upload functionality."""
            client = TestClient(api)

            from io import BytesIO
            test_file = BytesIO(b"Test document content")

            response = client.post(
                "/runs",
                params={"agent_id": "assistant"},
                data={"message": "Analyze this", "stream": False},
                files={"files": ("test.txt", test_file, "text/plain")}
            )

            # Response should be successful (200) or agent may need knowledge base (400)
            assert response.status_code in [200, 400]

        def test_streaming_response(self):
            """Test streaming response."""
            client = TestClient(api)

            response = client.post(
                "/runs",
                params={"agent_id": "assistant"},
                data={"message": "Tell me a story", "stream": True}
            )

            assert response.status_code == 200
            # For streaming, content-type should be text/event-stream
            # Note: TestClient might not preserve streaming headers exactly

        def test_validation_errors(self):
            """Test API validation."""
            client = TestClient(api)

            # Test missing component ID
            response = client.post("/runs", data={"message": "Hello"})
            assert response.status_code == 400

            # Test multiple component IDs
            response = client.post(
                "/runs",
                params={"agent_id": "assistant", "team_id": "support-team"},
                data={"message": "Hello"}
            )
            assert response.status_code == 400

            # Test nonexistent agent
            response = client.post(
                "/runs",
                params={"agent_id": "nonexistent"},
                data={"message": "Hello"}
            )
            assert response.status_code == 404

    # Run the test
    test_case = TestDjangoNinjaIntegration()
    test_case.test_agent_chat()
    print("✅ Tests passed!")


if __name__ == "__main__":
    print("Django-Ninja + Agno Integration Example")
    print("=====================================")
    print()
    print("This example shows how to integrate Agno with Django-Ninja.")
    print("Key features:")
    print("- Universal /runs endpoint for all AI interactions")
    print("- Support for agents, teams, and workflows")
    print("- File upload support (images, audio, video, documents)")
    print("- Streaming responses")
    print("- Django authentication integration")
    print("- Comprehensive testing utilities")
    print()
    print("API Endpoints:")
    print("- GET  /api/status")
    print("- POST /api/runs?agent_id=<id>")
    print("- POST /api/runs?team_id=<id>")
    print("- POST /api/runs?workflow_id=<id>")
    print()
    print("To use this in a Django project:")
    print("1. Install: pip install agno[django]")
    print("2. Add to INSTALLED_APPS: 'agno.app.django'")
    print("3. Include in urls.py: path('api/', api.urls)")
    print("4. Run migrations: python manage.py migrate")
    print("5. Start server: python manage.py runserver")
    print()
    print("Example API calls:")
    print('curl -X POST "http://localhost:8000/api/runs?agent_id=assistant" \\')
    print('  -F "message=Hello" \\')
    print('  -F "stream=false"')
    print()

    # Demonstrate programmatic usage
    print("Running programmatic examples...")
    try:
        example_programmatic_usage()
        example_test()
        print("✅ All examples completed successfully!")
    except Exception as e:
        print(f"⚠️  Examples require API keys to be configured: {e}")
        print("Set your API keys in environment variables to run the agents.")
