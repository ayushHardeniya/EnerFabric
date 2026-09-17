"""Shared Pydantic configuration for domain models.

Not a generic "Entity" base class — domain models do not share behavior
through this class, only a strict-validation config (reject unknown
fields, so typos and drift from the domain contract fail loudly).
"""

from pydantic import BaseModel, ConfigDict


class DomainModel(BaseModel):
    model_config = ConfigDict(extra="forbid")
