from fuelweb_test.settings import *  # noqa

# StackLight plugins
LMA_COLLECTOR_PLUGIN_PATH = os.environ.get('LMA_COLLECTOR_PLUGIN_PATH')
LMA_INFRA_ALERTING_PLUGIN_PATH = os.environ.get(
    'LMA_INFRA_ALERTING_PLUGIN_PATH')
ELASTICSEARCH_KIBANA_PLUGIN_PATH = os.environ.get(
    'ELASTICSEARCH_KIBANA_PLUGIN_PATH')
INFLUXDB_GRAFANA_PLUGIN_PATH = os.environ.get('INFLUXDB_GRAFANA_PLUGIN_PATH')
KAFKA_PLUGIN_PATH = os.environ.get('KAFKA_PLUGIN_PATH')

# Ceilometer plugins
CEILOMETER_REDIS_PLUGIN_PATH = os.environ.get('CEILOMETER_REDIS_PLUGIN_PATH')

# Openstack telemetery plugin
OPENSTACK_TELEMETRY_PLUGIN_PATH = os.environ.get(
    'OPENSTACK_TELEMETRY_PLUGIN_PATH')

# Detach plugins
DETACH_DATABASE_PLUGIN_PATH = os.environ.get('DETACH_DATABASE_PLUGIN_PATH')
DETACH_RABBITMQ_PLUGIN_PATH = os.environ.get('DETACH_RABBITMQ_PLUGIN_PATH')
