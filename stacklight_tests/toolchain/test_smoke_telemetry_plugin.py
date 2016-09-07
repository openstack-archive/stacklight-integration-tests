#    Copyright 2016 Mirantis, Inc.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

from fuelweb_test.helpers.decorators import log_snapshot_after_test
from proboscis import test
from stacklight_tests.elasticsearch_kibana import (
    plugin_settings as elasticsearch_settings)
from stacklight_tests.helpers import helpers
from stacklight_tests.influxdb_grafana import (
    plugin_settings as influxdb_settings)
from stacklight_tests.openstack_telemetry import api
from stacklight_tests import settings


@test(groups=["plugins"])
class TestOpenstackTelemetry(api.OpenstackTelemeteryPluginApi):
    """Class for smoke testing the Openstack Telemetry Plugin."""

    @test(depends_on_groups=['prepare_slaves_3'],
          groups=["deploy_openstack_telemetry", "install",
                  "ceilometer_redis", "smoke"])
    @log_snapshot_after_test
    def deploy_openstack_telemetry(self):
        """Install Openstack-Telemetry plugin and check it exists

        Scenario:
            1. Upload the Openstack-Telemetry plugin to the master node
            2. Install the plugin
            3. Create a cluster
            4. Check that the plugin can be enabled

        Duration 90m
        """
        self.check_run("deploy_openstack_telemetry")
        self.env.revert_snapshot("ready_with_3_slaves")
        self.prepare_plugin()
        self.helpers.prepare_plugin(settings.INFLUXDB_GRAFANA_PLUGIN_PATH)
        self.helpers.prepare_plugin(settings.ELASTICSEARCH_KIBANA_PLUGIN_PATH)
        self.helpers.create_cluster(name=self.__class__.__name__)
        self.activate_plugin()
        self.helpers.activate_plugin(
            helpers.get_plugin_name(settings.INFLUXDB_GRAFANA_PLUGIN_PATH),
            helpers.get_plugin_version(settings.INFLUXDB_GRAFANA_PLUGIN_PATH))
        self.helpers.activate_plugin(
            helpers.get_plugin_name(settings.ELASTICSEARCH_KIBANA_PLUGIN_PATH),
            helpers.get_plugin_version(
                settings.ELASTICSEARCH_KIBANA_PLUGIN_PATH))
        stacklight_roles = (
            elasticsearch_settings.role_name + influxdb_settings.role_name)
        self.helpers.deploy_cluster(
            {'slave-01': ['controller'],
             'slave-02': ['compute'],
             'slave-03': stacklight_roles})
        self.check_plugin_online()
        self.helpers.run_ostf()
        self.env.make_snapshot("deploy_openstack_telemetry", is_make=True)
