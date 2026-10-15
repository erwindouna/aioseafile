"""Asynchronous Python client for Seafile."""


class SeafileError(Exception):
    """Generic exception for Seafile errors."""


class SeafileConnectionError(SeafileError):
    """Exception raised for connection errors."""


class SeafileTimeoutError(SeafileError):
    """Exception raised for timeout errors."""


class SeafileAuthenticationError(SeafileError):
    """Exception raised for invalid credentials or an invalid token."""


class SeafileTwoFactorRequiredError(SeafileAuthenticationError):
    """Exception raised when the account requires a two-factor authentication code."""


class SeafilePermissionError(SeafileError):
    """Exception raised when the token lacks permission, for example for admin endpoints."""


class SeafileNotFoundError(SeafileError):
    """Exception raised when a resource is not found."""
