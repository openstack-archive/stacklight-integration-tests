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

from stacklight_tests.toolchain import api


@test(groups=["openstack_telemetry"])
class TestOpenstackTelemetry(api.ToolchainApi):
    """Class for testing the Openstack Telemetry Plugin."""

    def _deploy_telemetry_plugin(self, caller, snapshot="ready_with_5_slaves",
                                 advanced_options=None, additional_tests=None,
                                 additional_plugins=None, roles=None):
        self.check_run(caller)
        self.env.revert_snapshot(snapshot)
        self.add_plugin(self.OPENSTACK_TELEMETRY)
        self.disable_plugin(self.LMA_COLLECTOR)
        self.disable_plugin(self.LMA_INFRASTRUCTURE_ALERTING)
        for plugin in additional_plugins:
            self.add_plugin(plugin)
        self.prepare_plugins()
        self.helpers.create_cluster(name=self.__class__.__name__)
        self.activate_plugins()
        if advanced_options:
            self.OPENSTACK_TELEMETRY.activate_plugin(options=advanced_options)
        node_roles = {
            "slave-01": ["controller"],
            "slave-02": ["controller"],
            "slave-03": ["controller"],
            "slave-04": ["compute", "cinder"],
            "slave-05": ["elasticsearch_kibana", "influxdb_grafana"]} \
            if not roles else roles
        self.helpers.deploy_cluster(nodes_roles=node_roles)
        self.check_plugins_online()
        self.helpers.run_ostf()
        if additional_tests:
            for ostf_test in additional_tests:
                ostf_test()
        self.env.make_snapshot(caller, is_make=True)

    @test(depends_on_groups=["prepare_slaves_5"],
          groups=["deploy_openstack_telemetry", "deploy", "smoke",
                  "openstack_telemetry"])
    @log_snapshot_after_test
    def deploy_openstack_telemetry(self):
        """Deploy an environment with Openstack-Telemetry plugin
        with Elasticsearch and InfluxDB backends.

            1. Upload the Openstack-Telemetry, Elasticsearch-Kibana and
            InfluxDB-Grafana plugins to the master node
            2. Install the plugins
            3. Create the cluster
            4. Add 3 nodes with controller roles
            5. Add 1 node with compute and cinder roles
            6. Add 1 node with elasticsearch_kibana and influxdb_grafana roles
            7. Deploy the cluster
            8. Check that plugins are running
            9. Run OSTF

        Duration 90m
        """
        self._deploy_telemetry_plugin("deploy_openstack_telemetry")

    @test(depends_on_groups=["deploy_openstack_telemetry"],
          groups=["openstack_telemetry_default_functional", "functional"])
    def openstack_telemetry_default_functional(self):
        """Deploy an environment with Openstack-Telemetry plugin with
        Elasticsearch and InfluxDB backends and check default functionality

            1. Revert deploy_openstack_telemetry with Openstack-Telemetry,
            Elasticsearch-Kibana and InfluxDB-Grafana plugins installed
            2. Check Ceilometer Sample API
            3. Check Ceilometer Alarm API

        Duration 90m
        """
        additional_tests = (
            self.OPENSTACK_TELEMETRY.check_ceilometer_sample_functionality,
            self.OPENSTACK_TELEMETRY.check_ceilometer_alarm_functionality
        )

        self._deploy_telemetry_plugin("openstack_telemetry_default_functional",
                                      snapshot="deploy_openstack_telemetry",
                                      additional_tests=additional_tests
                                      )

    @test(depends_on_groups=["prepare_slaves_5"],
          groups=["openstack_telemetry_event_functional", "functional"])
    @log_snapshot_after_test
    def openstack_telemetry_event_functional(self):
        """Deploy an environment with Openstack-Telemetry plugin with
        enabled Ceilometer Event API and check its functionality

            1. Upload the Openstack-Telemetry, Elasticsearch-Kibana and
            InfluxDB-Grafana plugins to the master node
            2. Install the plugins
            3. Create the cluster
            4. Add 3 nodes with controller role
            5. Add 1 nodes with compute and cinder roles
            6. Add 1 nodes with elasticsearch_kibana and influxdb_grafana roles
            7. Enable Ceilometer Event API
            8. Deploy the cluster
            9. Check that plugins are running
            10. Run OSTF
            11. Check Ceilometer Sample API
            12. Check Ceilometer Alarm API
            13. Check Ceilometer Events API

        Duration 90m
        """
        additional_tests = (
            self.OPENSTACK_TELEMETRY.check_ceilometer_sample_functionality,
            self.OPENSTACK_TELEMETRY.check_ceilometer_alarm_functionality,
            self.OPENSTACK_TELEMETRY.check_ceilometer_event_functionality,
        )

        options = {
            "advanced_settings/value": True,
            "event_api/value": True,
        }

        self._deploy_telemetry_plugin("openstack_telemetry_event_functional",
                                      additional_tests=additional_tests,
                                      advanced_options=options
                                      )

    @test(depends_on_groups=["prepare_slaves_5"],
          groups=["openstack_telemetry_resource_functional", "functional"])
    @log_snapshot_after_test
    def openstack_telemetry_resource_functional(self):
        """Deploy an environment with Openstack-Telemetry plugin with
        enabled Ceilometer Resource API and check its functionality

            1. Upload the Openstack-Telemetry, Elasticsearch-Kibana and
            InfluxDB-Grafana plugins to the master node
            2. Install the plugins
            3. Create the cluster
            4. Add 3 nodes with controller role
            5. Add 1 nodes with compute and cinder roles
            6. Add 1 nodes with elasticsearch_kibana and influxdb_grafana roles
            9. Enable Ceilometer Resource API
            10. Deploy the cluster
            11. Check that plugins are running
            12. Run OSTF
            13. Check Ceilometer Sample API
            14. Check Ceilometer Alarm API
            15. Check Ceilometer Resource API

        Duration 90m
        """
        additional_tests = (
            self.OPENSTACK_TELEMETRY.check_ceilometer_sample_functionality,
            self.OPENSTACK_TELEMETRY.check_ceilometer_alarm_functionality,
            self.OPENSTACK_TELEMETRY.check_ceilometer_resource_functionality,
        )

        options = {
            "advanced_settings/value": True,
            "resource_api/value": True,
        }

        self._deploy_telemetry_plugin(
            "openstack_telemetry_resource_functional",
            additional_tests=additional_tests,
            advanced_options=options
        )

    @test(depends_on_groups=["prepare_slaves_5"],
          groups=["openstack_telemetry_all_functional", "functional"])
    @log_snapshot_after_test
    def openstack_telemetry_full_functional(self):
        """Deploy an environment with Openstack-Telemetry plugin with
        enabled Ceilometer Event and Resource API and check its functionality

            1. Upload the Openstack-Telemetry, Elasticsearch-Kibana and
            InfluxDB-Grafana plugins to the master node
            2. Install the plugins
            3. Create the cluster
            4. Add 3 nodes with controller role
            5. Add 1 nodes with compute and cinder roles
            6. Add 1 nodes with elasticsearch_kibana and influxdb_grafana roles
            9. Enable Ceilometer Event and Resource API
            10. Deploy the cluster
            11. Check that plugins are running
            12. Run OSTF
            13. Check Ceilometer Sample API
            14. Check Ceilometer Alarm API
            15. Check Ceilometer Event API
            16. Check Ceilometer Resource API

        Duration 90m
        """
        additional_tests = (
            self.OPENSTACK_TELEMETRY.check_ceilometer_sample_functionality,
            self.OPENSTACK_TELEMETRY.check_ceilometer_alarm_functionality,
            self.OPENSTACK_TELEMETRY.check_ceilometer_event_functionality,
            self.OPENSTACK_TELEMETRY.check_ceilometer_resource_functionality,
        )

        options = {
            "advanced_settings/value": True,
            "event_api/value": True,
            "resource_api/value": True,
        }

        self._deploy_telemetry_plugin(
            "openstack_telemetry_full_functional",
            additional_tests=additional_tests,
            advanced_options=options
        )

    @test(depends_on_groups=['prepare_slaves_5'],
          groups=["deploy_openstack_telemetry_kafka", "deploy", "smoke"])
    @log_snapshot_after_test
    def deploy_openstack_telemetry_kafka(self):
        """Deploy an environment with Openstack-Telemetry plugin
        with Elasticsearch and InfluxDB backends and Kafka plugin.

            1. Upload the Openstack-Telemetry, Elasticsearch-Kibana, Kafka and
            InfluxDB-Grafana plugins to the master node
            2. Install the plugins
            3. Create the cluster
            4. Add 3 nodes with controller and kafka roles
            5. Add 1 node with compute and cinder roles
            6. Add 1 node with elasticsearch_kibana and influxdb_grafana roles
            7. Deploy the cluster
            8. Check that plugins are running
            9. Run OSTF

        Duration 90m
        """
        additional_tests = (
            self.OPENSTACK_TELEMETRY.check_ceilometer_sample_functionality,
            self.OPENSTACK_TELEMETRY.check_ceilometer_alarm_functionality
        )

        roles = {
            "slave-01": ["controller", "kafka"],
            "slave-02": ["controller", "kafka"],
            "slave-03": ["controller", "kafka"],
            "slave-04": ["compute", "cinder"],
            "slave-05": ["elasticsearch_kibana", "influxdb_grafana"]}

        self._deploy_telemetry_plugin(
            "deploy_openstack_telemetry_kafka",
            additional_tests=additional_tests,
            additional_plugins=self.KAFKA,
            roles=roles
        )
