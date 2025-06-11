# Django-Ninja Integration for Agno

This directory contains examples and documentation for integrating Agno AI components into Django projects using django-ninja.

## Overview

The Django-Ninja integration provides seamless integration of Agno agents, teams, and workflows into existing Django projects. It automatically generates REST API endpoints while leveraging Django's built-in authentication, session management, and admin interface.

## Features

- ✅ **Seamless Integration**: Works with existing django-ninja APIs
- ✅ **Universal API Endpoint**: Single `/runs` endpoint for all AI components
- ✅ **Django Authentication**: Leverages Django's built-in auth system
- ✅ **File Uploads**: Supports multimodal content (images, audio, video, documents)
- ✅ **Session Management**: Uses Django sessions automatically
- ✅ **Streaming Support**: Real-time streaming responses
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

**Note:** No Django models, migrations, admin interfaces, or INSTALLED_APPS required. Agno uses native PostgreSQL storage.

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
assistant = Agent(
    name="assistant",
    model="gpt-4",
    instructions="You are a helpful assistant."
)

# Add Agno integration
agno_app = DjangoNinjaApp(
    api=api,
    agents=[assistant],
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

## API Endpoints

The integration automatically creates these endpoints:

### Status Endpoint
- `GET /api/status` - Check integration status

### Universal Runs Endpoint
- `POST /api/runs` - Universal endpoint for all AI interactions

## Universal Runs Endpoint

The `/runs` endpoint handles all agent, team, and workflow interactions through query parameters:

### Agent Chat
```bash
curl -X POST "http://localhost:8000/api/runs?agent_id=assistant" \
  -F "message=Hello, how are you?" \
  -F "stream=false"
```

### Team Chat
```bash
curl -X POST "http://localhost:8000/api/runs?team_id=content-team" \
  -F "message=Create an article about AI" \
  -F "stream=true"
```

### Workflow Execution
```bash
curl -X POST "http://localhost:8000/api/runs?workflow_id=data-analysis" \
  -F "workflow_input={\"data\": \"sample\"}"
```

### Parameters

**Query Parameters:**
- `agent_id` (optional): ID of the agent to run
- `team_id` (optional): ID of the team to run
- `workflow_id` (optional): ID of the workflow to run

**Form Data:**
- `message` (string): Message for agent/team chat
- `workflow_input` (object): Input data for workflows
- `stream` (boolean): Enable streaming responses (default: true)
- `monitor` (boolean): Enable monitoring (default: false)
- `session_id` (string, optional): Session identifier
- `user_id` (string, optional): User identifier
- `files` (array, optional): Uploaded files

### Response Format

**Non-streaming Response:**
```json
{
  "content": "Hello! I'm doing well, thank you for asking...",
  "agent_id": "assistant",
  "session_id": "abc123",
  "status": "success"
}
```

**Streaming Response:**
```
data: {"event": "run_response", "content": "Hello! I'm", "status": "running"}

data: {"event": "run_response", "content": " doing well...", "status": "success"}
```

## File Upload Support

The integration supports multimodal content through file uploads:

### Supported File Types

**Images** (for multimodal agents):
- PNG, JPEG, JPG, WebP

**Audio**:
- WAV, MP3, MPEG

**Video**:
- MP4, WebM, WMV, MOV

**Documents** (for knowledge bases):
- PDF, CSV, DOCX, TXT, JSON

### File Upload Example

```bash
curl -X POST "http://localhost:8000/api/runs?agent_id=assistant" \
  -F "message=Analyze this document" \
  -F "files=@document.pdf" \
  -F "files=@image.jpg" \
  -F "stream=false"
```

## Advanced Usage

### Teams Integration

```python
from agno import Agent, Team

researcher = Agent(
    name="researcher",
    model="gpt-4",
    instructions="You research topics thoroughly."
)
writer = Agent(
    name="writer",
    model="gpt-4",
    instructions="You write engaging content."
)

content_team = Team(
    name="content-team",
    members=[researcher, writer],
    instructions="Work together to create high-quality content."
)

agno_app = DjangoNinjaApp(
    api=api,
    agents=[researcher, writer],
    teams=[content_team],
)
```

### Workflows Integration

```python
from agno import Workflow

data_workflow = Workflow(
    name="data-analysis",
    description="Analyze data and generate insights"
)

agno_app = DjangoNinjaApp(
    api=api,
    workflows=[data_workflow],
)
```

### Custom Configuration

```python
agno_app = DjangoNinjaApp(
    api=api,
    agents=[agent],
    name="My AI App",
    description="Custom AI integration",
    app_id="my-custom-app-id",
    require_auth=True,      # Require Django authentication
    monitoring=True,        # Enable platform monitoring
)
```

## Authentication Integration

### Requiring Authentication

```python
agno_app = DjangoNinjaApp(
    api=api,
    agents=[agent],
    require_auth=True,  # Require Django login
)
```

### Using Django User Context

The integration automatically:
- Uses Django's `request.user.id` for `user_id` when authenticated
- Uses Django's session key for `session_id`
- Provides proper 401 responses for unauthenticated requests

## Django Settings

```python
# settings.py

# Agno configuration
AGNO_MONITOR = True
AGNO_API_KEY = "your-api-key"

# Database configuration (uses same DB for native storage)
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'your_db',
        # ... other settings
    }
}
```



## Testing

```python
# tests.py
from agno.app.django.testing import AgnoTestCase
from ninja.testing import TestClient

class MyAgnoTestCase(AgnoTestCase):
    def test_agent_chat(self):
        agno_app = self.create_agno_app()
        client = TestClient(agno_app.api)

        response = client.post(
            "/runs",
            params={"agent_id": "test-agent"},
            data={"message": "Test message", "stream": False}
        )

        self.assertAgentResponse(response)

    def test_streaming_response(self):
        agno_app = self.create_agno_app()
        client = TestClient(agno_app.api)

        response = client.post(
            "/runs",
            params={"agent_id": "test-agent"},
            data={"message": "Test streaming", "stream": True}
        )

        self.assertEqual(response.status_code, 200)

    def test_file_upload(self):
        agno_app = self.create_agno_app()
        client = TestClient(agno_app.api)

        from io import BytesIO
        test_file = BytesIO(b"test content")

        response = client.post(
            "/runs",
            params={"agent_id": "test-agent"},
            data={"message": "Process this file", "stream": False},
            files={"files": ("test.txt", test_file, "text/plain")}
        )

        self.assertIn(response.status_code, [200, 400])
```

## Error Handling

The integration provides proper HTTP error responses:

- `400 Bad Request` - Invalid request parameters or missing required fields
- `401 Unauthorized` - Authentication required (when `require_auth=True`)
- `404 Not Found` - Agent/team/workflow not found
- `500 Internal Server Error` - Processing error

### Example Error Responses

```json
{
  "error": "Only one of agent_id, team_id or workflow_id can be provided"
}
```

```json
{
  "error": "Agent not found"
}
```

## Data Monitoring

Agno uses native PostgreSQL storage for optimal performance. Monitor your agents using:

**Direct Database Queries:**
```sql
-- View recent memories
SELECT user_id, memory::text, created_at FROM agno.agent_memories ORDER BY created_at DESC;

-- View active sessions
SELECT session_id, agent_id, user_id, created_at FROM agno.agent_sessions ORDER BY updated_at DESC;
```

**Python Inspection Scripts:**
```bash
python manage.py shell < scripts/inspect_agent_data.py
```

This provides better performance and more detailed insights than Django admin interfaces.

## Security Considerations

- **Authentication**: Handled by Django's built-in system
- **File Validation**: Content-type validation for uploads
- **Session Security**: Uses Django's session framework
- **CSRF Protection**: Configure as needed for your Django setup
- **Input Sanitization**: Automatic validation of request parameters

## Performance Tips

- **Streaming**: Use `stream=true` for better user experience with long responses
- **Caching**: Enable Django's caching for frequently accessed agents
- **Database**: Native storage automatically optimizes indexes
- **File Handling**: Consider file size limits for uploads
- **Connection Pooling**: Configure database connection pooling

## Troubleshooting

### Common Issues

1. **Import Error**: Ensure `django-ninja` is installed: `pip install agno[django]`
2. **Authentication Required**: Set `require_auth=False` for testing
3. **Agent Not Found**: Verify agent initialization and ID matching
4. **File Upload Error**: Check file type support and agent knowledge base configuration
5. **Streaming Issues**: Ensure proper content-type headers for streaming responses

### Debug Mode

Enable debug logging:

```python
# settings.py
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

### API Testing

Test the status endpoint:
```bash
curl http://localhost:8000/api/status
```

Test agent interaction:
```bash
curl -X POST "http://localhost:8000/api/runs?agent_id=assistant" \
  -F "message=Hello" \
  -F "stream=false"
```

## Migration from Previous Versions

If you're migrating from the previous Django-Ninja integration:

### API Changes
- **Old**: `/agents/{agent_id}/chat` → **New**: `/runs?agent_id=...`
- **Old**: JSON body → **New**: Form data
- **Old**: Separate endpoints → **New**: Universal endpoint

### Code Changes
```python
# Old approach (no longer supported)
# Individual endpoints were auto-generated

# New approach
agno_app = DjangoNinjaApp(
    api=api,
    agents=[agent],
    teams=[team],
    workflows=[workflow]
)
# Single /runs endpoint handles all interactions
```

## Contributing

See the main Agno contributing guidelines for information on how to contribute to this integration.

## License

This integration follows the same license as the main Agno project.
