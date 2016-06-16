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

    @test(depends_on_groups=["deploy_ha_toolchain"],
          groups=["check_nova_notifications_toolchain", "toolchain",
                  "functional", "query_elasticsearch"])
    @log_snapshot_after_test
    def check_nova_notifications_toolchain(self):
        """Check that Nova notifications are present in Elasticsearch

        Scenario:
            1. Revert snapshot with 9 deployed nodes in HA configuration
            2. Launch, update, rebuild, resize, power-off, power-on, snapshot,
               suspend, shutdown, and delete an instance
            3. Check that Nova notifications are present in current
               Elasticsearch index

        Duration 25m
        """
        self.env.revert_snapshot("deploy_ha_toolchain")

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

    @test(depends_on_groups=["deploy_ha_toolchain"],
          groups=["toolchain_warning_alert_service", "service_restart",
                  "toolchain", "functional"])
    @log_snapshot_after_test
    def toolchain_warning_alert_service(self):
        """Verify that the warning alerts for services show up in the
         Grafana and Nagios UI.

        Scenario:
            1.  Connect to one of the controller nodes using ssh and
             stop the nova-api service.
            2.  Wait for at least 1 minute.
            3. On Grafana, check the following items:
                    - the box in the upper left corner of the dashboard
                     displays 'WARN' with an orange background,
                    - the API panels report 1 entity as down.
            4.  On Nagios, check the following items:
                    - the 'nova' service is in 'WARNING' state,
                    - the local user root on the lma node has received
                     an email about the service
                     being in warning state.
            5.  Restart the nova-api service.
            6.  Wait for at least 1 minute.
            7.  On Grafana, check the following items:
                    - the box in the upper left corner of the dashboard
                     displays 'OKAY' with an green background,
                    - the API panels report 0 entity as down.
            8.  On Nagios, check the following items:
                    - the 'nova' service is in 'OK' state,
                    - the local user root on the lma node has received
                    an email about the recovery
                     of the service.
            9.  Stop the nova-scheduler service.
            10.  Wait for at least 3 minutes.
            11. On Grafana, check the following items:
                    - the box in the upper left corner of the dashboard
                     displays 'WARN' with an orange background,
                    - the API panels report 1 entity as down.
            12. On Nagios, check the following items:
                    - the 'nova' service is in 'WARNING' state,
                    - the local user root on the lma node has received
                    an email about the service
                     being in warning state.
            13. Restart the nova-scheduler service.
            14. Wait for at least 1 minute.
            15.  On Grafana, check the following items:
                    - the box in the upper left corner of the dashboard
                     displays 'OKAY' with an green background,
                    - the API panels report 0 entity as down.
            16. On Nagios, check the following items:
                    - the 'nova' service is in 'OK' state,
                    - the local user root on the lma node has received
                    an email about the recovery
                     of the service.
            17. Repeat steps 1 to 16 for the following services:
                    - Cinder (stopping and starting the cinder-api and
                    cinder-api services
                     respectively).
                    - Neutron (stopping and starting the neutron-server
                    and neutron-openvswitch-agent
                     services respectively).
            18. Repeat steps 1 to 8 for the following services:
                    - Glance (stopping and starting the glance-api service).
                    - Heat (stopping and starting the heat-api service).
                    - Keystone (stopping and starting the Apache service).

        Duration 15m
        """
        self.env.revert_snapshot("deploy_ha_toolchain")

        services = {
            'nova': ['nova-api', 'nova-scheduler'],
            'cinder': ['cinder-api', 'cinder-scheduler'],
            'neutron': ['neutron-server'],
            'glance': ['glance-api'],
            'heat': ['heat-api'],
            'keystone': ['apache2']
        }

        lma_devops_node = self.helpers.get_node_with_vip(
            self.settings.stacklight_roles,
            self.helpers.full_vip_name(
                self.LMA_INFRASTRUCTURE_ALERTING.settings.vip_name))
        lma_node = self.fuel_web.get_nailgun_node_by_devops_node(
            lma_devops_node)

        url = self.LMA_INFRASTRUCTURE_ALERTING.get_authenticated_nagios_url()
        with self.ui_tester.ui_driver(url, "//frame[2]",
                                      "Nagios Core") as driver:
            self.LMA_INFRASTRUCTURE_ALERTING.open_nagios_page(
                driver, 'Services', "//table[@class='headertable']")
            for key in services:
                for service in services[key]:
                    controller_node = (
                        self.fuel_web.get_nailgun_cluster_nodes_by_roles(
                            self.helpers.cluster_id, ['controller'])[0])
                    self.change_verify_service_state(
                        [service, key], 'stop', ['WARNING', 'WARN'], [1, 1],
                        lma_node, [controller_node], driver)
                    self.change_verify_service_state(
                        [service, key], 'start', ['OK', 'OKAY'], [0, 0],
                        lma_node, [controller_node], driver)

    @test(depends_on_groups=["deploy_ha_toolchain"],
          groups=["toolchain_critical_alert_service", "service_restart",
                  "toolchain", "functional"])
    @log_snapshot_after_test
    def toolchain_critical_alert_service(self):
        """Verify that the critical alerts for services show up in
        the Grafana and Nagios UI.

        Scenario:
            1.  Open the Nagios URL
            2.  Connect to one of the controller nodes using ssh and
            stop the nova-api service.
            3.  Connect to a second controller node using ssh and stop
            the nova-api service.
            4.  Wait for at least 1 minute.
            5.  On Nagios, check the following items:
                    - the 'nova' service is in 'WARNING' state,
                    - the local user root on the lma node has received
                     an email about the service
                     being in warning state.
            6.  Restart the nova-api service on both nodes.
            7.  Wait for at least 1 minute.
            8.  On Nagios, check the following items:
                    - the 'nova' service is in 'OK' state,
                    - the local user root on the lma node has received
                    an email about the recovery
                     of the service.
            9.  Connect to one of the controller nodes using ssh and stop
             the nova-scheduler service.
            10. Connect to a second controller node using ssh and stop the
            nova-scheduler service.
            11. Wait for at least 3 minutes.
            12. On Nagios, check the following items:
                    - the 'nova' service is in 'WARNING' state,
                    - the local user root on the lma node has received an
                    email about the service
                     being in warning state.
            13. Restart the nova-scheduler service on both nodes.
            14. Wait for at least 1 minute.
            15. On Nagios, check the following items:
                    - the 'nova' service is in 'OK' state,
                    - the local user root on the lma node has received an
                    email about the recovery
                     of the service.
            16. Repeat steps 1 to 15 for the following services:
                    - Cinder (stopping and starting the cinder-api and
                    cinder-api services
                     respectively).
                    - Neutron (stopping and starting the neutron-server
                    and neutron-openvswitch-agent
                     services respectively).
            17. Repeat steps 1 to 8 for the following services:
                    - Glance (stopping and starting the glance-api service).
                    - Heat (stopping and starting the heat-api service).
                    - Keystone (stopping and starting the Apache service).

        Duration 15m
        """
        self.env.revert_snapshot("deploy_ha_toolchain")

        services = {
            'nova': ['nova-api', 'nova-scheduler'],
            'cinder': ['cinder-api', 'cinder-scheduler'],
            'neutron': ['neutron-server'],
            'glance': ['glance-api'],
            'heat': ['heat-api'],
            'keystone': ['apache2']
        }

        lma_devops_node = self.helpers.get_node_with_vip(
            self.settings.stacklight_roles,
            self.helpers.full_vip_name(
                self.LMA_INFRASTRUCTURE_ALERTING.settings.vip_name))
        lma_node = self.fuel_web.get_nailgun_node_by_devops_node(
            lma_devops_node)

        url = self.LMA_INFRASTRUCTURE_ALERTING.get_authenticated_nagios_url()
        with self.ui_tester.ui_driver(url, "//frame[2]",
                                      "Nagios Core") as driver:
            self.LMA_INFRASTRUCTURE_ALERTING.open_nagios_page(
                driver, 'Services', "//table[@class='headertable']")
            for key in services:
                for service in services[key]:
                    logger.info("Checking service {0}".format(service))
                    controller_nodes = (
                        self.fuel_web.get_nailgun_cluster_nodes_by_roles(
                            self.helpers.cluster_id, ['controller']))
                    self.change_verify_service_state(
                        [service, key], 'stop', ['CRITICAL', 'CRIT'], [3, 2],
                        lma_node, [controller_nodes[0], controller_nodes[1]],
                        driver)
                    self.change_verify_service_state(
                        [service, key], 'start', ['OK', 'OKAY'], [0, 0],
                        lma_node, [controller_nodes[0], controller_nodes[1]],
                        driver)

    @test(depends_on_groups=["deploy_ha_toolchain"],
          groups=["toolchain_warning_alert_node", "node_alert_warning",
                  "toolchain", "functional"])
    @log_snapshot_after_test
    def toolchain_warning_alert_node(self):
        """Verify that the warning alerts for nodes show up in the
         Grafana and Nagios UI.

        Scenario:
            1.  Open the Nagios URL
            2.  Open the Grafana URl
            3.  Connect to one of the controller nodes using ssh and
                run:
                    fallocate -l $(df | grep /dev/mapper/mysql-root
                    | awk '{ printf("%.0f\n", 1024 * ((($3 + $4) * 96
                     / 100) - $3))}') /var/lib/mysql/test
            4.  Wait for at least 1 minute.
            5.  On Grafana, check the following items:
                    - the box in the upper left corner of the dashboard
                     displays 'OKAY' with an green background,
            6.  On Nagios, check the following items:
                    - the 'mysql' service is in 'OK' state,
                    - the 'mysql-nodes.mysql-fs' service is in 'WARNING'
                     state for the node.
            7.  Connect to a second controller node using ssh and run:
                    fallocate -l $(df | grep /dev/mapper/mysql-root
                    | awk '{ printf("%.0f\n", 1024 * ((($3 + $4) * 96
                     / 100) - $3))}') /var/lib/mysql/test
            8.  Wait for at least 1 minute.
            9.  On Grafana, check the following items:
                    - the box in the upper left corner of the dashboard
                     displays 'WARN' with an orange background,
                    - an annotation telling that the service went from 'OKAY'
                     to 'WARN' is displayed.
            10.  On Nagios, check the following items:
                    - the 'mysql' service is in 'WARNING' state,
                    - the 'mysql-nodes.mysql-fs' service is in 'WARNING'
                     state for the 2 nodes,
                    - the local user root on the lma node has received an
                     email about the service
                    being in warning state.
            11.  Run the following command on both controller nodes:
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

        lma_devops_node = self.helpers.get_node_with_vip(
            self.settings.stacklight_roles,
            self.helpers.full_vip_name("infrastructure_alerting_mgmt_vip"))
        lma_node = self.fuel_web.get_nailgun_node_by_devops_node(
            lma_devops_node)
        nailgun_nodes = self.fuel_web.get_nailgun_cluster_nodes_by_roles(
            self.helpers.cluster_id, ['controller'])

        url = self.LMA_INFRASTRUCTURE_ALERTING.get_authenticated_nagios_url()
        with self.ui_tester.ui_driver(url, "//frame[2]",
                                      "Nagios Core") as driver:
            self.LMA_INFRASTRUCTURE_ALERTING.open_nagios_page(
                driver, 'Services', "//table[@class='headertable']")
            self.change_verify_node_service_state(
                ['mysql', 'mysql-nodes.mysql-fs'], 'WARNING', 1, '96',
                lma_node, [nailgun_nodes[0], nailgun_nodes[1]], driver)

    @test(depends_on_groups=["deploy_ha_toolchain"],
          groups=["toolchain_critical_alert_node", "node_alert_critical",
                  "toolchain", "functional"])
    @log_snapshot_after_test
    def toolchain_critical_alert_node(self):
        """Verify that the critical alerts for nodes show up in the
         Grafana and Nagios UI.

        Scenario:
            1.  Open the Nagios URL
            2.  Open the Grafana URl
            3.  Connect to one of the controller nodes using ssh and run:
                    fallocate -l $(df | grep /dev/mapper/mysql-root
                    | awk '{ printf("%.0f\n", 1024 * ((($3 + $4) *
                    98 / 100) - $3))}') /var/lib/mysql/test
            4.  Wait for at least 1 minute.
            5.  On Grafana, check the following items:
                    - the box in the upper left corner of the dashboard
                     displays 'OKAY' with an green background,
            6.  On Nagios, check the following items:
                    - the 'mysql' service is in 'OK' state,
                    - the 'mysql-nodes.mysql-fs' service is in 'CRITICAL'
                     state for the node.
            7.  Connect to a second controller node using ssh and run:
                    fallocate -l $(df | grep /dev/mapper/mysql-root
                    | awk '{ printf("%.0f\n", 1024 * ((($3 + $4) *
                    98 / 100) - $3))}') /var/lib/mysql/test
            8.  Wait for at least 1 minute.
            9.  On Grafana, check the following items:
                    - the box in the upper left corner of the dashboard
                     displays 'CRIT' with an orange background,
                    - an annotation telling that the service went from 'OKAY'
                     to 'WARN' is displayed.
            10.  On Nagios, check the following items:
                    - the 'mysql' service is in 'CRITICAL' state,
                    - the 'mysql-nodes.mysql-fs' service is in 'CRITICAL'
                     state for the 2 nodes,
                    - the local user root on the lma node has received an
                    email about the service
                    being in warning state.
            11.  Run the following command on both controller nodes:
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

        lma_devops_node = self.helpers.get_node_with_vip(
            self.settings.stacklight_roles,
            self.helpers.full_vip_name("infrastructure_alerting_mgmt_vip"))
        lma_node = self.fuel_web.get_nailgun_node_by_devops_node(
            lma_devops_node)
        nailgun_nodes = self.fuel_web.get_nailgun_cluster_nodes_by_roles(
            self.helpers.cluster_id, ['controller'])

        url = self.LMA_INFRASTRUCTURE_ALERTING.get_authenticated_nagios_url()
        with self.ui_tester.ui_driver(url, "//frame[2]",
                                      "Nagios Core") as driver:
            self.LMA_INFRASTRUCTURE_ALERTING.open_nagios_page(
                driver, 'Services', "//table[@class='headertable']")
            self.change_verify_node_service_state(
                ['mysql', 'mysql-nodes.mysql-fs'], 'CRITICAL', 2, '98',
                lma_node, [nailgun_nodes[0], nailgun_nodes[1]], driver)
