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

from stacklight_tests.openstack_telemetry import api as telemetry_api
from stacklight_tests.toolchain import api


@test(groups=["plugins"])
class TestOpenstackTelemetry(api.ToolchainApi):
    """Class for smoke testing the Openstack Telemetry Plugin."""

    @test(depends_on_groups=['prepare_slaves_3'],
          groups=["deploy_openstack_telemetry", "install",
                  "ceilometer_redis", "smoke"])
    @log_snapshot_after_test
    def deploy_openstack_telemetry(self):
        """Deploy an environment with Openstack-Telemetry plugin
        with Elasticsearch and InfluxDB backends.

            1. Upload the Openstack-Telemetry, Elasticsearch-Kibana and
            InfluxDB-Grafana plugins to the master node
            2. Install the plugins
            3. Create the cluster
            4. Add 1 nodes with controller role
            5. Add 1 nodes with compute and cinder roles
            6. Add 1 nodes with elasticsearch_kibana and influxdb_grafana roles
            7. Deploy the cluster
            8. Check that plugins are running
            9. Run OSTF

        Duration 90m
        """
        self.check_run("deploy_openstack_telemetry")
        self.env.revert_snapshot("ready_with_3_slaves")
        self.add_plugin(telemetry_api.OpenstackTelemeteryPluginApi())
        self.disable_plugin(self.LMA_COLLECTOR)
        self.disable_plugin(self.LMA_INFRASTRUCTURE_ALERTING)
        self.prepare_plugins()
        self.helpers.create_cluster(name=self.__class__.__name__)
        self.activate_plugins()
        roles = ["elasticsearch_kibana", "influxdb_grafana"]
        self.helpers.deploy_cluster(
            {'slave-01': ['controller'],
             'slave-02': ['compute', 'cinder'],
             'slave-03': roles})
        self.check_plugins_online()
        self.helpers.run_ostf()
        self.env.make_snapshot("deploy_openstack_telemetry", is_make=True)
