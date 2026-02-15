
def init_telemetry ():
    from telemetry import configure, TestConfig, Resource, SERVICE_NAME
    from telemetry import HttpConfig
    import logging
    import os

    if "SAMPLE_GRAFANA" in os.environ.keys():
        config = HttpConfig( "http://otel.polympiads.ch:4318" )
        config.resource = Resource({ SERVICE_NAME: os.environ.get("SERVICE", "<unknown-service>") })
        config.loglevel = logging.DEBUG
        configure(config)
    else:
        config = TestConfig()
        config.resource = Resource({ SERVICE_NAME: "service" })
        config.loglevel = logging.DEBUG
        configure(config)

    if "DEBUG_LOGS" in os.environ.keys():
        logging.getLogger().addHandler( logging.StreamHandler() )
