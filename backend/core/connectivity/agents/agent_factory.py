from .posix_agent import PosixStorageAgent
from .s3_agent import S3StorageAgent
from .dummy_agent import DummyStorageAgent
from .. import AbstractStorageAgent

available_flavours = {
    PosixStorageAgent.FLAVOUR: PosixStorageAgent,
    S3StorageAgent.FLAVOUR: S3StorageAgent,
    DummyStorageAgent.FLAVOUR: DummyStorageAgent  # For testing only
}


def agent_factory(config: dict, flavour: str) -> AbstractStorageAgent:
    """
    Factory function to create an AbstractStorageAgent instance based on the provided configuration.

    :param flavour: The flavour of the agent to create (e.g., 's3', 'dummy').
    :param config: The configuration dictionary containing the details for creating the agent.
    :return:
    """
    try:
        return available_flavours[flavour](**config)
    except KeyError:
        raise ValueError(f"Unsupported agent flavour: {flavour}")

