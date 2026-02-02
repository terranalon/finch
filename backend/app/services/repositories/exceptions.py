"""Repository-specific exceptions.

These exceptions provide semantic meaning for data access errors,
separating them from general database errors.
"""


class RepositoryError(Exception):
    """Base exception for repository operations."""


class NotFoundError(RepositoryError):
    """Entity not found in database."""

    def __init__(self, entity_type: str, identifier: str | int):
        self.entity_type = entity_type
        self.identifier = identifier
        super().__init__(f"{entity_type} not found: {identifier}")


class DuplicateError(RepositoryError):
    """Entity already exists (unique constraint violation)."""

    def __init__(self, entity_type: str, field: str, value: str):
        self.entity_type = entity_type
        self.field = field
        self.value = value
        super().__init__(f"{entity_type} with {field}={value} already exists")
