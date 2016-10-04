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
from fuelweb_test import logger
from proboscis import test

from stacklight_tests.toolchain import api


@test(groups=["plugins"])
class TestFunctionalToolchain(api.ToolchainApi):
    """Class for functional testing of plugins toolchain."""

    @test(depends_on_groups=["deploy_toolchain"],
          groups=["check_display_grafana_dashboards_toolchain",
                  "toolchain", "functional"])
    @log_snapshot_after_test
    def check_display_grafana_dashboards_toolchain(self):
        """Verify that the dashboards show up in the Grafana UI.

        Scenario:
            1. Revert snapshot with 3 deployed nodes
            2. Open the Grafana URL (
                open the "Dashboard" tab and click the "Grafana" link)
            3. Sign-in using the credentials provided
                during the configuration of the environment
            4. Go to the Main dashboard and verify that everything is ok
            5. Repeat the previous step for the following dashboards:
                * Apache
                * Cinder
                * Elasticsearch
                * Glance
                * HAProxy
                * Heat
                * Hypervisor
                * InfluxDB
                * Keystone
                * LMA self-monitoring
                * Memcached
                * MySQL
                * Neutron
                * Nova
                * RabbitMQ
                * System

        Duration 20m
        """

        self.env.revert_snapshot("deploy_toolchain")

        self.check_plugins_online()

        self.INFLUXDB_GRAFANA.check_grafana_dashboards()

    @test(depends_on_groups=["deploy_toolchain"],
          groups=["check_nova_metrics_toolchain",
                  "toolchain", "functional"])
    @log_snapshot_after_test
    def check_nova_metrics_toolchain(self):
        """Verify that the Nova metrics are collecting.

        Scenario:
            1. Revert snapshot with 3 deployed nodes
            2. Check that plugins are online
            3. Check Nova metrics in InfluxDB during OSTF tests

        Duration 20m
        """

        self.env.revert_snapshot("deploy_toolchain")

        self.check_plugins_online()

        self.check_nova_metrics()

    @test(depends_on_groups=["deploy_ha_toolchain"],
          groups=["check_nova_logs_in_elasticsearch", "toolchain",
                  "functional", "query_elasticsearch"])
    @log_snapshot_after_test
    def check_nova_logs_in_elasticsearch(self):
        """Check that Nova logs are present in Elasticsearch

        Scenario:
            1. Revert snapshot with 9 deployed nodes in HA configuration
            2. Query Nova logs are present in current Elasticsearch index
            3. Check that Nova logs are collected from all controller and
               compute nodes

        Duration 10m
        """
        self.env.revert_snapshot("deploy_ha_toolchain")

        self.check_plugins_online()

        self.check_nova_logs()

    @test(depends_on_groups=["deploy_toolchain"],
          groups=["check_nova_notifications_toolchain", "toolchain",
                  "functional", "query_elasticsearch"])
    @log_snapshot_after_test
    def check_nova_notifications_toolchain(self):
        """Check that Nova notifications are present in Elasticsearch

        Scenario:
            1. Revert snapshot with 3 deployed nodes
            2. Launch, update, rebuild, resize, power-off, power-on, snapshot,
               suspend, shutdown, and delete an instance
            3. Check that Nova notifications are present in current
               Elasticsearch index

        Duration 25m
        """
        self.env.revert_snapshot("deploy_toolchain")

        self.check_plugins_online()

        self.check_nova_notifications()

    @test(depends_on_groups=["deploy_toolchain"],
          groups=["check_glance_notifications_toolchain", "toolchain",
                  "functional", "query_elasticsearch"])
    @log_snapshot_after_test
    def check_glance_notifications_toolchain(self):
        """Check that Glance notifications are present in Elasticsearch

        Scenario:
            1. Revert snapshot with 3 deployed nodes
            2. Run the OSTF platform test "Check create, update and delete
               image actions using Glance v2"
            3. Check that Glance notifications are present in current
               Elasticsearch index

        Duration 25m
        """
        self.env.revert_snapshot("deploy_toolchain")

        self.check_plugins_online()

        self.check_glance_notifications()

    @test(depends_on_groups=["deploy_toolchain"],
          groups=["check_keystone_notifications_toolchain", "toolchain",
                  "functional", "query_elasticsearch"])
    @log_snapshot_after_test
    def check_keystone_notifications_toolchain(self):
        """Check that Keystone notifications are present in Elasticsearch

        Scenario:
            1. Revert snapshot with 3 deployed nodes
            2. Run OSTF functional test "Create user and authenticate with it
               to Horizon"
            3. Check that Keystone notifications are present in current
               Elasticsearch index

        Duration 25m
        """
        self.env.revert_snapshot("deploy_toolchain")

        self.check_plugins_online()

        self.check_keystone_notifications()

    @test(depends_on_groups=["deploy_toolchain"],
          groups=["check_heat_notifications_toolchain", "toolchain",
                  "functional", "query_elasticsearch"])
    @log_snapshot_after_test
    def check_heat_notifications_toolchain(self):
        """Check that Heat notifications are present in Elasticsearch

        Scenario:
            1. Revert snapshot with 3 deployed nodes
            2. Run OSTF Heat platform tests
            3. Check that Heat notifications are present in current
               Elasticsearch index

        Duration 25m
        """
        self.env.revert_snapshot("deploy_toolchain")

        self.check_plugins_online()

        self.check_heat_notifications()

    @test(depends_on_groups=["deploy_toolchain"],
          groups=["check_neutron_notifications_toolchain", "toolchain",
                  "functional", "query_elasticsearch"])
    @log_snapshot_after_test
    def check_neutron_notifications_toolchain(self):
        """Check that Neutron notifications are present in Elasticsearch

        Scenario:
            1. Revert snapshot with 3 deployed nodes
            2. Run OSTF functional test "Check network connectivity from
               instance via floating IP"
            3. Check that Neutron notifications are present in current
               Elasticsearch index

        Duration 25m
        """
        self.env.revert_snapshot("deploy_toolchain")

        self.check_plugins_online()

        self.check_neutron_notifications()

    @test(depends_on_groups=["deploy_toolchain"],
          groups=["check_cinder_notifications_toolchain", "toolchain",
                  "functional", "query_elasticsearch"])
    @log_snapshot_after_test
    def check_cinder_notifications_toolchain(self):
        """Check that Cinder notifications are present in Elasticsearch

        Scenario:
            1. Revert snapshot with 3 deployed nodes
            2. Create a volume and update it
            3. Check that Cinder notifications are present in current
               Elasticsearch index

        Duration 25m
        """
        self.env.revert_snapshot("deploy_toolchain")

        self.check_plugins_online()

        self.check_cinder_notifications()

    def _check_services_alerts(self, controllers_count, nagios_status,
                               influx_status, down_haproxy_count):
        components = {
            "nova": [("nova-api", "nova-api"), ("nova-scheduler", None)],
            "cinder": [("cinder-api", "cinder-api"),
                       ("cinder-scheduler", None)],
            "neutron": [
                ("neutron-server", "neutron-api"),
                # TODO(rpromyshlennikov): temporary fix,
                # because openvswitch-agent is managed by pacemaker
                # ("neutron-openvswitch-agent", None)
            ],
            "glance": [("glance-api", "glance-api")],
            "heat": [("heat-api", "heat-api")],
            "keystone": [("apache2", "keystone-public-api")]
        }

        alerting_plugin = self.LMA_INFRASTRUCTURE_ALERTING
        services_names_in_nagios = {}
        for service in components:
            nagios_service_name = (
                service
                if alerting_plugin.settings.version.startswith("0.")
                else "global-{}".format(service)
            )
            services_names_in_nagios[service] = nagios_service_name

        lma_devops_node = self.helpers.get_node_with_vip(
            self.settings.stacklight_roles,
            self.helpers.get_vip_resource_name(
                alerting_plugin.settings.failover_vip))
        toolchain_node = self.fuel_web.get_nailgun_node_by_devops_node(
            lma_devops_node)

        url = alerting_plugin.get_authenticated_nagios_url()
        with self.ui_tester.ui_driver(url, "Nagios Core",
                                      "//frame[2]") as driver:
            alerting_plugin.open_nagios_page(
                driver, "Services", "//table[@class='headertable']")
            controller_nodes = (
                self.fuel_web.get_nailgun_cluster_nodes_by_roles(
                    self.helpers.cluster_id,
                    ["controller"])[:controllers_count]
            )
            for component in components:
                for (service, haproxy_backend) in components[component]:
                    logger.info("Checking service {0}".format(service))
                    self.change_verify_service_state(
                        service_name=[
                            service, component,
                            services_names_in_nagios[component],
                            haproxy_backend],
                        action="stop",
                        new_state=nagios_status,
                        service_state_in_influx=influx_status,
                        down_backends_in_haproxy=down_haproxy_count,
                        toolchain_node=toolchain_node,
                        controller_nodes=controller_nodes,
                        nagios_driver=driver)
                    self.change_verify_service_state(
                        service_name=[
                            service, component,
                            services_names_in_nagios[component],
                            haproxy_backend],
                        action="start",
                        new_state="OK",
                        service_state_in_influx=self.settings.OKAY,
                        down_backends_in_haproxy=0,
                        toolchain_node=toolchain_node,
                        controller_nodes=controller_nodes,
                        nagios_driver=driver)

    @test(depends_on_groups=["deploy_ha_toolchain"],
          groups=["toolchain_warning_alert_service", "service_restart",
                  "toolchain", "functional"])
    @log_snapshot_after_test
    def toolchain_warning_alert_service(self):
        """Verify that the warning alerts for services show up in the
         Grafana and Nagios UI.

        Scenario:
            1. Connect to one of the controller nodes using ssh and
             stop the nova-api service.
            2. Wait for at least 1 minute.
            3. On Grafana, check the following items:
                    - the box in the upper left corner of the dashboard
                     displays 'WARN' with an orange background,
                    - the API panels report 1 entity as down.
            4. On Nagios, check the following items:
                    - the 'nova' service is in 'WARNING' state,
                    - the local user root on the lma node has received
                     an email about the service
                     being in warning state.
            5. Restart the nova-api service.
            6. Wait for at least 1 minute.
            7. On Grafana, check the following items:
                    - the box in the upper left corner of the dashboard
                     displays 'OKAY' with an green background,
                    - the API panels report 0 entity as down.
            8. On Nagios, check the following items:
                    - the 'nova' service is in 'OK' state,
                    - the local user root on the lma node has received
                    an email about the recovery
                     of the service.
            9. Repeat steps 2 to 8 for the following services:
                    - Nova (stopping and starting the nova-api and
                     nova-scheduler)
                    - Cinder (stopping and starting the cinder-api and
                    cinder-scheduler services respectively).
                    - Neutron (stopping and starting the neutron-server
                    and neutron-openvswitch-agent services respectively).
                    - Glance (stopping and starting the glance-api service).
                    - Heat (stopping and starting the heat-api service).
                    - Keystone (stopping and starting the Apache service).

        Duration 45m
        """
        self.env.revert_snapshot("deploy_ha_toolchain")
        params = {"controllers_count": 1,
                  "nagios_status": "WARNING",
                  "influx_status": self.settings.WARN,
                  "down_haproxy_count": 1}

        self._check_services_alerts(**params)

    @test(depends_on_groups=["deploy_ha_toolchain"],
          groups=["toolchain_critical_alert_service", "service_restart",
                  "toolchain", "functional"])
    @log_snapshot_after_test
    def toolchain_critical_alert_service(self):
        """Verify that the critical alerts for services show up in
        the Grafana and Nagios UI.

        Scenario:
            1. Open the Nagios URL
            2. Connect to one of the controller nodes using ssh and
            stop the nova-api service.
            3. Connect to a second controller node using ssh and stop
            the nova-api service.
            4. Wait for at least 1 minute.
            5. On Nagios, check the following items:
                    - the 'nova' service is in 'WARNING' state,
                    - the local user root on the lma node has received
                     an email about the service
                     being in warning state.
            6. Restart the nova-api service on both nodes.
            7. Wait for at least 1 minute.
            8. On Nagios, check the following items:
                    - the 'nova' service is in 'OK' state,
                    - the local user root on the lma node has received
                    an email about the recovery
                     of the service.
            9. Repeat steps 2 to 8 for the following services:
                    - Nova (stopping and starting the nova-api and
                     nova-scheduler)
                    - Cinder (stopping and starting the cinder-api and
                    cinder-scheduler services respectively).
                    - Neutron (stopping and starting the neutron-server
                    and neutron-openvswitch-agent services respectively).
                    - Glance (stopping and starting the glance-api service).
                    - Heat (stopping and starting the heat-api service).
                    - Keystone (stopping and starting the Apache service).

        Duration 45m
        """
        self.env.revert_snapshot("deploy_ha_toolchain")
        params = {"controllers_count": 2,
                  "nagios_status": "CRITICAL",
                  "influx_status": self.settings.CRIT,
                  "down_haproxy_count": 2}

        self._check_services_alerts(**params)

    def _check_mysql_alerts_node(
            self, nagios_status, influx_status, disk_usage_percent):
        lma_devops_node = self.helpers.get_node_with_vip(
            self.settings.stacklight_roles,
            self.helpers.get_vip_resource_name(
                "infrastructure_alerting_mgmt_vip"))
        toolchain_node = self.fuel_web.get_nailgun_node_by_devops_node(
            lma_devops_node)
        nailgun_nodes = self.fuel_web.get_nailgun_cluster_nodes_by_roles(
            self.helpers.cluster_id, ["controller"])

        alerting_plugin = self.LMA_INFRASTRUCTURE_ALERTING
        url = alerting_plugin.get_authenticated_nagios_url()
        with self.ui_tester.ui_driver(url, "Nagios Core",
                                      "//frame[2]") as driver:
            alerting_plugin.open_nagios_page(
                driver, "Services", "//table[@class='headertable']")
            nagios_service_name = (
                "mysql"
                if alerting_plugin.settings.version.startswith("0.")
                else "global-mysql")
            self.change_verify_node_service_state(
                [nagios_service_name, "mysql-nodes.mysql-fs", "mysql"],
                nagios_status,
                influx_status, disk_usage_percent, toolchain_node,
                nailgun_nodes[:2], driver)

    @test(depends_on_groups=["deploy_ha_toolchain"],
          groups=["toolchain_warning_alert_node", "node_alert_warning",
                  "toolchain", "functional"])
    @log_snapshot_after_test
    def toolchain_warning_alert_node(self):
        """Verify that the warning alerts for nodes show up in the
         Grafana and Nagios UI.

        Scenario:
            1. Open the Nagios URL
            2. Open the Grafana URl
            3. Connect to one of the controller nodes using ssh and
               run:
                    fallocate -l $(df | grep /dev/mapper/mysql-root
                    | awk '{ printf("%.0f\n", 1024 * ((($3 + $4) * 96
                     / 100) - $3))}') /var/lib/mysql/test
            4. Wait for at least 1 minute.
            5. On Grafana, check the following items:
                    - the box in the upper left corner of the dashboard
                     displays 'OKAY' with an green background,
            6. On Nagios, check the following items:
                    - the 'mysql' service is in 'OK' state,
                    - the 'mysql-nodes.mysql-fs' service is in 'WARNING'
                     state for the node.
            7. Connect to a second controller node using ssh and run:
                    fallocate -l $(df | grep /dev/mapper/mysql-root
                    | awk '{ printf("%.0f\n", 1024 * ((($3 + $4) * 96
                     / 100) - $3))}') /var/lib/mysql/test
            8. Wait for at least 1 minute.
            9. On Grafana, check the following items:
                    - the box in the upper left corner of the dashboard
                     displays 'WARN' with an orange background,
                    - an annotation telling that the service went from 'OKAY'
                     to 'WARN' is displayed.
            10. On Nagios, check the following items:
                    - the 'mysql' service is in 'WARNING' state,
                    - the 'mysql-nodes.mysql-fs' service is in 'WARNING'
                     state for the 2 nodes,
                    - the local user root on the lma node has received an
                     email about the service
                    being in warning state.
            11. Run the following command on both controller nodes:
                    rm /var/lib/mysql/test
            12. Wait for at least 1 minutes.
            13. On Grafana, check the following items:
                    - the box in the upper left corner of the dashboard
                     displays 'OKAY' with an green background,
                    - an annotation telling that the service went from 'WARN'
                     to 'OKAY' is displayed.
            14. On Nagios, check the following items:
                    - the 'mysql' service is in 'OK' state,
                    - the 'mysql-nodes.mysql-fs' service is in 'OKAY' state
                     for the 2 nodes,
                    - the local user root on the lma node has received an
                     email about the recovery of the service.

        Duration 15m
        """
        self.env.revert_snapshot("deploy_ha_toolchain")
        params = {
            "nagios_status": "WARNING",
            "influx_status": self.settings.WARN,
            "disk_usage_percent": 91}
        self._check_mysql_alerts_node(**params)

    @test(depends_on_groups=["deploy_ha_toolchain"],
          groups=["toolchain_critical_alert_node", "node_alert_critical",
                  "toolchain", "functional"])
    @log_snapshot_after_test
    def toolchain_critical_alert_node(self):
        """Verify that the critical alerts for nodes show up in the
         Grafana and Nagios UI.

        Scenario:
            1. Open the Nagios URL
            2. Open the Grafana URl
            3. Connect to one of the controller nodes using ssh and run:
                    fallocate -l $(df | grep /dev/mapper/mysql-root
                    | awk '{ printf("%.0f\n", 1024 * ((($3 + $4) *
                    98 / 100) - $3))}') /var/lib/mysql/test
            4. Wait for at least 1 minute.
            5. On Grafana, check the following items:
                    - the box in the upper left corner of the dashboard
                     displays 'OKAY' with an green background,
            6. On Nagios, check the following items:
                    - the 'mysql' service is in 'OK' state,
                    - the 'mysql-nodes.mysql-fs' service is in 'CRITICAL'
                     state for the node.
            7. Connect to a second controller node using ssh and run:
                    fallocate -l $(df | grep /dev/mapper/mysql-root
                    | awk '{ printf("%.0f\n", 1024 * ((($3 + $4) *
                    98 / 100) - $3))}') /var/lib/mysql/test
            8. Wait for at least 1 minute.
            9. On Grafana, check the following items:
                    - the box in the upper left corner of the dashboard
                     displays 'CRIT' with an orange background,
                    - an annotation telling that the service went from 'OKAY'
                     to 'WARN' is displayed.
            10. On Nagios, check the following items:
                    - the 'mysql' service is in 'CRITICAL' state,
                    - the 'mysql-nodes.mysql-fs' service is in 'CRITICAL'
                     state for the 2 nodes,
                    - the local user root on the lma node has received an
                    email about the service
                    being in warning state.
            11. Run the following command on both controller nodes:
                    rm /var/lib/mysql/test
            12. Wait for at least 1 minutes.
            13. On Grafana, check the following items:
                    - the box in the upper left corner of the dashboard
                     displays 'OKAY' with an green background,
                    - an annotation telling that the service went from 'CRIT'
                     to 'OKAY' is displayed.
            14. On Nagios, check the following items:
                    - the 'mysql' service is in OK' state,
                    - the 'mysql-nodes.mysql-fs' service is in 'OKAY' state
                     for the 2 nodes,
                    - the local user root on the lma node has received an
                    email about the recovery of the service.

        Duration 15m
        """
        self.env.revert_snapshot("deploy_ha_toolchain")
        params = {
            "nagios_status": "CRITICAL",
            "influx_status": self.settings.CRIT,
            "disk_usage_percent": 96}
        self._check_mysql_alerts_node(**params)
