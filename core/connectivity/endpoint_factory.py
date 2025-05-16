from core.management.endpoints.models import Endpoint
from core.connectivity.agents import available_flavours


# Factory for instantiating the correct AbstractStorageAgent based on configuration
def endpoint_factory(config: dict) -> Endpoint:
    """
    Factory function to create an Endpoint instance based on the provided configuration.

    :param config: Configuration dictionary containing the details for creating the Endpoint.
    :return: An instance of Endpoint.
    """

    flavour = config.get('flavour')

    return available_flavours[flavour](**config['agent'])

