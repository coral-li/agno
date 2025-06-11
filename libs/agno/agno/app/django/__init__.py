"""
Django-Ninja integration for Agno AI components.

This package provides seamless integration of Agno agents, teams, and workflows
into Django projects using django-ninja for API routing.
"""

try:
    from .app import ChatRequest, ChatResponse, DjangoNinjaApp

    __all__ = ["DjangoNinjaApp", "ChatRequest", "ChatResponse"]
except ImportError:
    raise ImportError("`django` and `django-ninja` not installed. Please install using `pip install agno[django]`")
