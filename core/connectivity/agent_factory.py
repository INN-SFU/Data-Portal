from core.connectivity.agent import Agent
from core.connectivity.agents import S3Agent


# Factory for instantiating the correct Agent based on configuration
def new_endpoint(config: dict) -> Agent:
    flavor = config.get("flavour")
    if flavor == "s3":
        return S3Agent(
            access_point_slug=config.get("slug"),
            endpoint_url=config.get("endpoint"),
            aws_access_key_id=config.get("aws_access_key_id"),
            aws_secret_access_key=config.get("aws_secret_access_key")
        )
    else:
        raise ValueError(f"Unsupported storage flavor: {flavor}")
