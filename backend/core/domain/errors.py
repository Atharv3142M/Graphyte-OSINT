"""Domain layer exceptions."""


class DomainError(Exception):
    """Base domain exception."""
    
    def __init__(self, message: str, error_code: str = "UNKNOWN_ERROR"):
        self.message = message
        self.error_code = error_code
        super().__init__(message)


class InvalidTargetError(DomainError):
    """Invalid investigation target."""
    
    def __init__(self, message: str):
        super().__init__(message, "INVALID_TARGET")


class ModuleNotFoundError(DomainError):
    """Module not found in registry."""
    
    def __init__(self, module_name: str):
        super().__init__(f"Module '{module_name}' not found", "MODULE_NOT_FOUND")


class PlaybookNotFoundError(DomainError):
    """Playbook definition not found."""
    
    def __init__(self, playbook_id: str):
        super().__init__(f"Playbook '{playbook_id}' not found", "PLAYBOOK_NOT_FOUND")


class TaskQueueError(DomainError):
    """Task queue operation failed."""
    
    def __init__(self, message: str):
        super().__init__(message, "TASK_QUEUE_ERROR")


class StixIngestionError(DomainError):
    """Failed to ingest results to STIX graph."""
    
    def __init__(self, message: str):
        super().__init__(message, "STIX_INGESTION_ERROR")


class ConfigurationError(DomainError):
    """Configuration validation failed."""
    
    def __init__(self, message: str):
        super().__init__(message, "CONFIGURATION_ERROR")
