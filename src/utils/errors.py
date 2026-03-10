"""Custom exception classes for GitHub AI Agent."""


class AgentError(Exception):
    """Base exception for all agent errors."""
    pass


class ConfigurationError(AgentError):
    """Configuration loading or validation error."""
    pass


class GitHubAPIError(AgentError):
    """GitHub API operation error."""
    pass


class GeminiAPIError(AgentError):
    """Gemini API operation error."""
    pass


class JSONParseError(AgentError):
    """JSON parsing error."""
    pass


class GitError(AgentError):
    """Git operation error."""
    pass


class FileWriteError(AgentError):
    """File write operation error."""
    pass
