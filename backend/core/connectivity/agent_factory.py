from core.connectivity.agents import S3StorageAgent, DummyStorageAgent
from core.connectivity.abstract_storage_agent import AbstractStorageAgent

AVAILABLE_FLAVOURS = {
    S3StorageAgent.FLAVOUR: S3StorageAgent,
    DummyStorageAgent.FLAVOUR: DummyStorageAgent  # For testing only
}

# Factory for instantiating the correct AbstractStorageAgent based on configuration
def agent_factory(config: dict) -> AbstractStorageAgent:
    """
    Factory function to create a storage agent based on the provided configuration.

    :param config: Configuration dictionary containing the flavour and agent details.
    :return: An instance of AbstractStorageAgent (S3StorageAgent, DummyStorageAgent, etc.).
    """

    flavour = config.get('flavour')

    return AVAILABLE_FLAVOURS[flavour](**config['agent'])

