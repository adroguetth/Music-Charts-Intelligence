"""
Cache and HTTP session management for API clients.

This module provides access to the global in-memory cache and reusable
HTTP sessions. The actual cache and sessions are defined in config.py
to avoid circular imports; this module simply re-exports them.
"""

from ..config import get_cache, get_http_sessions

# Re-export for convenience
__all__ = ["get_cache", "get_http_sessions"]
