"""Custom exceptions for Beanclerk"""


class BeanclerkError(Exception):
    """Base class for all beanclerk exceptions"""


class ConfigError(BeanclerkError):
    """Error in configuration file"""

    def __init__(self, message: str) -> None:
        super().__init__(f"Cannot load config file: {message}")
