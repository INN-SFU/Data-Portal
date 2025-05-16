from uuid import UUID

from pydantic import BaseModel

from core.connectivity import AbstractStorageAgent


# todo incorporate model
class Endpoint(BaseModel):
    """
    Endpoint
    Class representing an endpoint.

    Attributes:
    - uuid: UUID
    - name: str
    - agent: AbstractStorageAgent
    """
    uuid: UUID
    name: str
    flavour: str
    agent: AbstractStorageAgent

    class Config:
        arbitrary_types_allowed = True

    def config(self, secrets: bool = False):
        """
        Returns the configuration of the endpoint.
        This is a placeholder for the actual implementation.
        """
        return {
            "uuid": str(self.uuid),
            "name": self.name,
            "flavour": self.agent.FLAVOUR,
            "agent": self.agent.config(secrets) if self.agent else None
        }

    def close(self):
        """
        Perform explicit cleanup of resources held by this endpoint.
        For instance, if the agent holds connections or open files, they
        should be closed here.
        """
        if self.agent:
            # Assuming your AbstractStorageAgent implements a method like close() to free resources.
            self.agent.close()

    def __del__(self):
        """
        Destructor to try to ensure cleanup.
        Note: __del__ is not guaranteed to be called deterministically,
        so you should explicitly call close() when you know the Endpoint is no longer needed.
        """
        self.close()

    def __str__(self):
        """
        String representation of the Endpoint.
        """
        return f"Endpoint(uuid={self.uuid}, name={self.name}, agent={self.agent.__str__()})"

    def __eq__(self, other):
        """
        Equality check based on UUID.
        """
        if isinstance(other, Endpoint):
            return self.uuid == other.uuid
        return False
