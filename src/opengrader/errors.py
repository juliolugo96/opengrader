"""Domain exceptions displayed as concise CLI errors."""


class OpenGraderError(Exception):
    """Base class for expected, user-facing failures."""


class ConfigError(OpenGraderError):
    """The assignment configuration could not be loaded."""


class SubmissionError(OpenGraderError):
    """The submissions directory is invalid or empty."""


class DockerUnavailableError(OpenGraderError):
    """Docker is required but unavailable."""

