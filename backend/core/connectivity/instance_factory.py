from core.management.instances.models import Instance
from core.connectivity.agents import available_flavours


# Factory for instantiating the correct AbstractStorageAgent based on configuration
def instance_factory(config: dict) -> Instance:
    """
    Factory function to create an Instance instance based on the provided configuration.

    :param config: Configuration dictionary containing the details for creating the Instance.
    :return: An instance of Instance.
    """

    flavour = config.get('flavour')

    return available_flavours[flavour](**config['agent'])

