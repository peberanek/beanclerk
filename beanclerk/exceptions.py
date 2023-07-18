"""Custom exceptions for Beanclerk"""


class BeanclerkError(Exception):
    """Base class for all Beanclerk exceptions"""


class ConfigError(BeanclerkError):
    """Error in the Beanclerk configuration file"""

    def __init__(self, message: str) -> None:
        super().__init__(f"Cannot load config file: {message}")


class ClerkError(BeanclerkError):
    """An Error during clerk operations"""

    def __init__(self, message: str) -> None:
        super().__init__(f"Clerk error: {message}")
