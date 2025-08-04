"""
Custom exceptions for the music app backend.
"""

class MusicAppException(Exception):
    """Base exception class for the music app."""
    
    def __init__(self, message: str, details: str = None):
        self.message = message
        self.details = details
        super().__init__(self.message)


class DatabaseError(MusicAppException):
    """Raised when database operations fail."""
    pass


class FileUploadError(MusicAppException):
    """Raised when file upload operations fail."""
    pass


class AudioAnalysisError(MusicAppException):
    """Raised when audio analysis fails."""
    pass


class ValidationError(MusicAppException):
    """Raised when input validation fails."""
    pass


class ConfigurationError(MusicAppException):
    """Raised when configuration is invalid."""
    pass


class ExternalServiceError(MusicAppException):
    """Raised when external service calls fail."""
    pass
