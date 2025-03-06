import os
import logging
import logging.config


def setup_logging(config: dict) -> dict:
    """
    Set up logging configuration based on the provided config.

    :param config: dictionary containing logging configuration
    :type config: dict
    :return: list of created loggers
    :rtype: dict
    """
    logging.config.fileConfig(os.getenv('LOG_CONFIG'), disable_existing_loggers=False)

    # Set loggers levels based on the YAML configuration
    log_levels = config['logging']['level']
    for logger_name, level in log_levels.items():
        logging.getLogger(logger_name).setLevel(level)

    # Create loggers
    app_logger = logging.getLogger('app')
    uvicorn_logger = logging.getLogger('uvicorn')
    casbin_logger = logging.getLogger('casbin')

    return {'app': app_logger, 'uvicorn': uvicorn_logger, 'casbin': casbin_logger}
