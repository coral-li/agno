# Django-Ninja Integration for Agno

This directory contains examples and documentation for integrating Agno AI components into Django projects using django-ninja.

## Overview

The Django-Ninja integration provides seamless integration of Agno agents, teams, and workflows into existing Django projects. It automatically generates REST API endpoints while leveraging Django's built-in authentication, session management, and admin interface.

## Features

- ✅ **Seamless Integration**: Works with existing django-ninja APIs
- ✅ **Django Authentication**: Leverages Django's built-in auth system
- ✅ **File Uploads**: Supports document uploads to agent knowledge bases
- ✅ **Session Management**: Uses Django sessions automatically
- ✅ **Admin Interface**: Optional Django admin integration for monitoring
- ✅ **Testing Utilities**: Comprehensive test utilities included
- ✅ **Management Commands**: CLI commands for agent registration
- ✅ **Error Handling**: Proper HTTP error responses
- ✅ **Logging**: Integration with Django's logging system

## Installation

1. Install Agno with Django-Ninja support:
```bash
pip install agno[django]
```

Or install dependencies separately:
```bash
pip install django django-ninja
```

2. In your Django project's `INSTALLED_APPS`, add:
```python
INSTALLED_APPS = [
    # ... your existing apps
    'agno.app.django',  # Optional: for models and admin
]
```

## Quick Start

### Basic Integration

```python
# myapp/api.py
from ninja import NinjaAPI
from agno import Agent
from agno.app.django import DjangoNinjaApp

# Create your ninja API
api = NinjaAPI()

# Add existing routes
@api.get("/users")
def list_users(request):
    return {"users": []}

# Create Agno agents
assistant = Agent(name="assistant", model="gpt-4")

# Add Agno integration
agno_app = DjangoNinjaApp(
    api=api,
    agents=[assistant],
    prefix="/ai"
)
```

### URL Configuration

```python
# myproject/urls.py
from django.contrib import admin
from django.urls import path
from myapp.api import api

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', api.urls),
]
```

## Generated Endpoints

The integration automatically creates these endpoints:

- `GET /api/ai/status` - Check integration status
- `POST /api/ai/agents/{agent_id}/chat` - Chat with specific agent
- `POST /api/ai/agents/{agent_id}/upload` - Upload files to agent knowledge base
- `POST /api/ai/teams/{team_id}/chat` - Chat with team
- `POST /api/ai/workflows/{workflow_id}/run` - Execute workflow

## Examples

### Agent Chat Request

```bash
curl -X POST http://localhost:8000/api/ai/agents/assistant/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello, how are you?"}'
```

Response:
```json
{
  "content": "Hello! I'm doing well, thank you for asking...",
  "agent_id": "assistant",
  "session_id": "abc123"
}
```

### File Upload

```bash
curl -X POST http://localhost:8000/api/ai/agents/assistant/upload \
  -F "file=@document.pdf"
```

## Advanced Usage

### Teams Integration

```python
from agno import Agent, Team

researcher = Agent(name="researcher", model="gpt-4")
writer = Agent(name="writer", model="gpt-4")

content_team = Team(
    name="content-team",
    members=[researcher, writer]
)

agno_app = DjangoNinjaApp(
    api=api,
    agents=[researcher, writer],
    teams=[content_team],
    prefix="/ai"
)
```

### Custom Configuration

```python
agno_app = DjangoNinjaApp(
    api=api,
    agents=[agent],
    prefix="/ai",
    name="My AI App",
    description="Custom AI integration",
    require_auth=True,      # Require Django authentication
    monitoring=True,        # Enable platform monitoring
)
```

## Django Settings

```python
# settings.py

# Agno configuration
AGNO_MONITOR = True
AGNO_API_KEY = "your-api-key"

# Database configuration for logging (optional)
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'your_db',
        # ... other settings
    }
}
```

## Management Commands

Register agents with the platform:

```bash
python manage.py register_agno_agents --app-module myapp.api
```

## Testing

```python
# tests.py
from agno.app.django.testing import AgnoTestCase

class MyAgnoTestCase(AgnoTestCase):
    def test_agent_chat(self):
        agno_app = self.create_agno_app()
        client = TestClient(agno_app.api)

        response = client.post("/agno/agents/test-agent/chat", json={
            "message": "Test message"
        })

        self.assertAgentResponse(response)
```

## Error Handling

The integration provides proper HTTP error responses:

- `401 Unauthorized` - Authentication required
- `400 Bad Request` - Invalid request data
- `404 Not Found` - Agent/team not found
- `500 Internal Server Error` - Processing error

## File Upload Support

Supported file types:
- **Documents**: PDF, CSV, DOCX, TXT, JSON
- **Images**: PNG, JPEG, WebP (for multimodal agents)
- **Audio**: WAV, MP3, MPEG
- **Video**: MP4, WebM, WMV

## Django Admin Integration

The integration includes Django admin interfaces for monitoring:

- Agent runs and responses
- Team interactions
- Performance metrics
- Error tracking

## Security Considerations

- Authentication is handled by Django's built-in system
- File uploads are validated by content type
- Session management uses Django sessions
- CSRF protection can be configured as needed

## Troubleshooting

### Common Issues

1. **Import Error**: Make sure `django-ninja` is installed
2. **Auth Required**: Set `require_auth=False` for testing
3. **Agent Not Found**: Check agent names and initialization
4. **File Upload Error**: Verify file type and agent knowledge base

### Debug Mode

Enable debug logging:

```python
LOGGING = {
    'version': 1,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
    'loggers': {
        'agno.app.django': {
            'handlers': ['console'],
            'level': 'DEBUG',
        },
    },
}
```

## Performance Tips

- Use async agents for better performance
- Configure proper database indexing for models
- Enable Django's caching for frequent requests
- Use connection pooling for database connections

## Contributing

See the main Agno contributing guidelines for information on how to contribute to this integration.

## License

This integration follows the same license as the main Agno project.
