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

    @test(depends_on_groups=['prepare_slaves_5'],
          groups=["deploy_openstack_telemetry", "deploy",
                  "openstack_telemetry", "smoke"])
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
        self.check_run("deploy_openstack_telemetry")
        self.env.revert_snapshot("ready_with_5_slaves")
        self.add_plugin(self.OPENSTACK_TELEMETRY)
        self.disable_plugin(self.LMA_COLLECTOR)
        self.disable_plugin(self.LMA_INFRASTRUCTURE_ALERTING)
        self.prepare_plugins()
        self.helpers.create_cluster(name=self.__class__.__name__)
        self.activate_plugins()
        roles = ["elasticsearch_kibana", "influxdb_grafana"]
        self.helpers.deploy_cluster(
            {'slave-01': ['controller'],
             'slave-02': ['controller'],
             'slave-03': ['controller'],
             'slave-04': ['compute', 'cinder'],
             'slave-05': roles})
        self.check_plugins_online()
        self.helpers.run_ostf()
        self.env.make_snapshot("deploy_openstack_telemetry", is_make=True)


@test(groups=["openstack_telemetry"])
class TestOpenstackTelemetryFunctional(api.ToolchainApi):
    """Class for functional testing the Openstack Telemetry Plugin."""

    @test(depends_on_groups=['deploy_openstack_telemetry'],
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
        self.check_run("openstack_telemetry_default_functional")
        self.env.revert_snapshot("deploy_openstack_telemetry")
        self.OPENSTACK_TELEMETRY.check_ceilometer_sample_functionality()
        self.OPENSTACK_TELEMETRY.check_ceilometer_alarm_functionality()

    @test(depends_on_groups=['prepare_slaves_5'],
          groups=["openstack_telemetry_event_functional",
                  "deploy_openstack_telemetry", "functional"])
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
        self.check_run("openstack_telemetry_event_functional")
        self.env.revert_snapshot("ready_with_5_slaves")
        self.add_plugin(self.OPENSTACK_TELEMETRY)
        self.disable_plugin(self.LMA_COLLECTOR)
        self.disable_plugin(self.LMA_INFRASTRUCTURE_ALERTING)
        self.prepare_plugins()
        self.helpers.create_cluster(name=self.__class__.__name__)
        self.activate_plugins()

        options = {
            "advanced_settings/value": True,
            "event_api/value": True,
        }

        self.OPENSTACK_TELEMETRY.activate_plugin(options=options)

        roles = ["elasticsearch_kibana", "influxdb_grafana"]
        self.helpers.deploy_cluster(
            {'slave-01': ['controller'],
             'slave-02': ['controller'],
             'slave-03': ['controller'],
             'slave-04': ['compute', 'cinder'],
             'slave-05': roles})
        self.check_plugins_online()
        self.helpers.run_ostf()
        self.OPENSTACK_TELEMETRY.check_ceilometer_sample_functionality()
        self.OPENSTACK_TELEMETRY.check_ceilometer_alarm_functionality()
        self.OPENSTACK_TELEMETRY.check_ceilometer_event_functionality()
        self.env.make_snapshot("openstack_telemetry_event_functional",
                               is_make=True)

    @test(depends_on_groups=['prepare_slaves_5'],
          groups=["openstack_telemetry_resource_functional",
                  "deploy_openstack_telemetry", "functional"])
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
        self.check_run("openstack_telemetry_default_functional")
        self.env.revert_snapshot("ready_with_5_slaves")
        self.add_plugin(self.OPENSTACK_TELEMETRY)
        self.disable_plugin(self.LMA_COLLECTOR)
        self.disable_plugin(self.LMA_INFRASTRUCTURE_ALERTING)
        self.prepare_plugins()
        self.helpers.create_cluster(name=self.__class__.__name__)
        self.activate_plugins()

        options = {
            "advanced_settings/value": True,
            "resource_api/value": True,
        }

        self.OPENSTACK_TELEMETRY.activate_plugin(options=options)

        roles = ["elasticsearch_kibana", "influxdb_grafana"]
        self.helpers.deploy_cluster(
            {'slave-01': ['controller'],
             'slave-02': ['controller'],
             'slave-03': ['controller'],
             'slave-04': ['compute', 'cinder'],
             'slave-05': roles})
        self.check_plugins_online()
        self.helpers.run_ostf()
        self.OPENSTACK_TELEMETRY.check_ceilometer_sample_functionality()
        self.OPENSTACK_TELEMETRY.check_ceilometer_alarm_functionality()
        self.OPENSTACK_TELEMETRY.check_ceilometer_resource_functionality()
        self.env.make_snapshot("openstack_telemetry_event_functional",
                               is_make=True)

    @test(depends_on_groups=['prepare_slaves_5'],
          groups=["openstack_telemetry_all_functional",
                  "deploy_openstack_telemetry", "functional"])
    @log_snapshot_after_test
    def openstack_telemetry_all_functional(self):
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
        self.check_run("openstack_telemetry_all_functional")
        self.env.revert_snapshot("ready_with_5_slaves")
        self.add_plugin(self.OPENSTACK_TELEMETRY)
        self.disable_plugin(self.LMA_COLLECTOR)
        self.disable_plugin(self.LMA_INFRASTRUCTURE_ALERTING)
        self.prepare_plugins()
        self.helpers.create_cluster(name=self.__class__.__name__)
        self.activate_plugins()

        options = {
            "advanced_settings/value": True,
            "event_api/value": True,
            "resource_api/value": True,
        }

        self.OPENSTACK_TELEMETRY.activate_plugin(options=options)

        roles = ["elasticsearch_kibana", "influxdb_grafana"]
        self.helpers.deploy_cluster(
            {'slave-01': ['controller'],
             'slave-02': ['controller'],
             'slave-03': ['controller'],
             'slave-04': ['compute', 'cinder'],
             'slave-05': roles})
        self.check_plugins_online()
        self.helpers.run_ostf()
        self.OPENSTACK_TELEMETRY.check_ceilometer_sample_functionality()
        self.OPENSTACK_TELEMETRY.check_ceilometer_alarm_functionality()
        self.OPENSTACK_TELEMETRY.check_ceilometer_event_functionality()
        self.OPENSTACK_TELEMETRY.check_ceilometer_resource_functionality()
        self.env.make_snapshot("openstack_telemetry_all_functional",
                               is_make=True)
