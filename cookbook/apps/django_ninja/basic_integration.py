"""
Basic Django-Ninja integration example for Agno.

This example demonstrates how to integrate Agno agents into a Django project
using django-ninja for API routing.

To use this example:
1. Install django and django-ninja: pip install django django-ninja
2. Create a Django project and app
3. Add the integration to your Django app
4. Run the server and test the endpoints

Key endpoints created:
- GET /api/ai/status - Check integration status
- POST /api/ai/agents/{agent_id}/chat - Chat with specific agent
- POST /api/ai/agents/{agent_id}/upload - Upload files to agent knowledge base
"""

from ninja import NinjaAPI
from agno import Agent
from agno.app.django import DjangoNinjaApp


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
    instructions="You are a helpful assistant that can answer questions and help with tasks."
)

customer_service_agent = Agent(
    name="customer-service",
    model="gpt-4",
    instructions="You are a customer service representative. Be polite, helpful, and professional."
)

# Add Agno integration to your existing API
agno_app = DjangoNinjaApp(
    api=api,
    agents=[assistant_agent, customer_service_agent],
    prefix="/ai",
    name="My Django AI App",
    description="Django-Ninja integration with Agno AI agents",
    require_auth=True,  # Require Django authentication
    monitoring=True,    # Enable platform monitoring
)

# Now you have these endpoints available:
# GET  /api/users (your existing route)
# GET  /api/health (your existing route)
# GET  /api/ai/status (Agno status)
# POST /api/ai/agents/assistant/chat (Agno agent chat)
# POST /api/ai/agents/customer-service/chat (Agno agent chat)
# POST /api/ai/agents/assistant/upload (File upload)
# POST /api/ai/agents/customer-service/upload (File upload)


# In your Django urls.py, you would include:
# from django.urls import path
# from .api import api
#
# urlpatterns = [
#     path('api/', api.urls),
# ]


# Example usage in your Django views or other code:
def example_usage():
    """Example of how to interact with agents programmatically."""
    # Chat with assistant
    response = assistant_agent.run("What is the weather like today?")
    print(f"Assistant: {response.content}")

    # Chat with customer service agent
    response = customer_service_agent.run("I need help with my order")
    print(f"Customer Service: {response.content}")


if __name__ == "__main__":
    # This would be handled by Django's manage.py runserver
    print("This example is meant to be integrated into a Django project.")
    print("See the docstring for integration instructions.")
