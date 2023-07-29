"""Custom exceptions."""
# Usually, subclasses of Exception should describe what the exception
# represents, and not the context in which it might occur.
# https://github.com/google/styleguide/blob/gh-pages/pyguide.md#384-classes


class BeanclerkError(Exception):
    """Base class for all Beanclerk exceptions."""


class ConfigError(BeanclerkError):
    """Beanclerk configuration is invalid."""

    def __init__(self, message: str) -> None:
        """Initialize the exception.

        Args:
            message (str): an error message
        """
        super().__init__(f"Cannot load config file: {message}")


class ClerkError(BeanclerkError):
    """Clerk cannot operate."""

    def __init__(self, message: str) -> None:
        """Initialize the exception.

        Args:
            message (str): an error message
        """
        super().__init__(f"Clerk error: {message}")
