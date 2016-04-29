# coding=utf-8
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
from proboscis import asserts
from proboscis import test

from fuelweb_test.helpers.decorators import log_snapshot_after_test
from fuelweb_test import logger
from fuelweb_test import settings
from fuelweb_test.tests import base_test_case

from stacklight_tests.lma_infrastructure_alerting import api
from stacklight_tests.lma_infrastructure_alerting.test_smoke_bvt \
    import TestLMAInfraAlertingPlugin as smoke


@test(groups=["plugins"])
class TestLMAInfraAlertingPluginFunc(api.InfraAlertingPluginApi):
    """Class for functional testing the LMA Infrastructure Alerting plugin."""

    @test(depends_on=[smoke.deploy_lma_infra_alerting_plugin_in_ha_mode],
          groups=["warning_alert_service_infra_alerting"])
    @log_snapshot_after_test
    def warning_alert_service_infra_alerting(self):
        """Verify that the warning alerts for services show up in the
         Grafana and Nagios UI.

        Scenario:
            1.  Open the Nagios URL
            2.  Connect to one of the controller nodes using ssh and
             stop the nova-api service.
            3.  Wait for at least 1 minute.
            4.  On Nagios, check the following items:
                    - the ‘nova’ service is in ‘WARNING’ state,
                    - the local user root on the lma node has received
                     an email about the service
                     being in warning state.
            5.  Restart the nova-api service.
            6.  Wait for at least 1 minute.
            7.  On Nagios, check the following items:
                    - the ‘nova’ service is in ‘OK’ state,
                    - the local user root on the lma node has received
                    an email about the recovery
                     of the service.
            8.  Stop the nova-scheduler service.
            9.  Wait for at least 3 minutes.
            10. On Nagios, check the following items:
                    - the ‘nova’ service is in ‘WARNING’ state,
                    - the local user root on the lma node has received
                    an email about the service
                     being in warning state.
            11. Restart the nova-scheduler service.
            12. Wait for at least 1 minute.
            13. On Nagios, check the following items:
                    - the ‘nova’ service is in ‘OK’ state,
                    - the local user root on the lma node has received
                    an email about the recovery
                     of the service.
            14. Repeat steps 1 to 13 for the following services:
                    - Cinder (stopping and starting the cinder-api and
                    cinder-api services
                     respectively).
                    - Neutron (stopping and starting the neutron-server
                    and neutron-openvswitch-agent
                     services respectively).
            15. Repeat steps 1 to 7 for the following services:
                    - Glance (stopping and starting the glance-api service).
                    - Heat (stopping and starting the heat-api service).
                    - Keystone (stopping and starting the Apache service).

        Duration 15m
        """
        self.env.revert_snapshot("deploy_lma_alerting_plugin_ha")

        driver = self.get_nagios_main_page()

        services = {
            'nova': ['nova-api', 'nova-scheduler'],
            'cinder': ['cinder-api', 'cinder-scheduler'],
            'neutron': ['neutron-server'],
            'glance': ['glance-api'],
            'heat': ['heat-api'],
            'keystone': ['apache2']
        }

        lma_node = self.get_primary_lma_node()

        try:
            for key in services:
                for service in services[key]:
                    nailgun_nodes = (
                        self.fuel_web.get_nailgun_cluster_nodes_by_roles(
                            self.helpers.cluster_id, ['controller']))
                    service_node = (
                        self.fuel_web.get_devops_nodes_by_nailgun_nodes(
                            nailgun_nodes)[0])
                    self.change_verify_service_state(
                        [service, key], 'stop', 'WARNING', lma_node,
                        [service_node], driver)
                    self.change_verify_service_state(
                        [service, key], 'start', 'OK', lma_node,
                        [service_node], driver)
        finally:
            driver.close()

    @test(depends_on=[smoke.deploy_lma_infra_alerting_plugin_in_ha_mode],
          groups=["critical_alert_service_infra_alerting"])
    @log_snapshot_after_test
    def critical_alert_service_infra_alerting(self):
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
                    - the ‘nova’ service is in ‘WARNING’ state,
                    - the local user root on the lma node has received
                     an email about the service
                     being in warning state.
            6.  Restart the nova-api service on both nodes.
            7.  Wait for at least 1 minute.
            8.  On Nagios, check the following items:
                    - the ‘nova’ service is in ‘OK’ state,
                    - the local user root on the lma node has received
                    an email about the recovery
                     of the service.
            9.  Connect to one of the controller nodes using ssh and stop
             the nova-scheduler service.
            10. Connect to a second controller node using ssh and stop the
            nova-scheduler service.
            11. Wait for at least 3 minutes.
            12. On Nagios, check the following items:
                    - the ‘nova’ service is in ‘WARNING’ state,
                    - the local user root on the lma node has received an
                    email about the service
                     being in warning state.
            13. Restart the nova-scheduler service on both nodes.
            14. Wait for at least 1 minute.
            15. On Nagios, check the following items:
                    - the ‘nova’ service is in ‘OK’ state,
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
        self.env.revert_snapshot("deploy_lma_alerting_plugin_ha")

        driver = self.get_nagios_main_page()

        services = {
            'nova': ['nova-api', 'nova-scheduler'],
            'cinder': ['cinder-api', 'cinder-scheduler'],
            'neutron': ['neutron-server'],
            'glance': ['glance-api'],
            'heat': ['heat-api'],
            'keystone': ['apache2']
        }

        lma_node = self.get_primary_lma_node()

        try:
            for key in services:
                for service in services[key]:
                    logger.info("Checking service {0}".format(service))
                    nailgun_nodes = (
                        self.fuel_web.get_nailgun_cluster_nodes_by_roles(
                            self.helpers.cluster_id, ['controller']))
                    service_nodes = (
                        self.fuel_web.get_devops_nodes_by_nailgun_nodes(
                            nailgun_nodes))
                    self.change_verify_service_state(
                        [service, key], 'stop', 'CRITICAL', lma_node,
                        [service_nodes[0], service_nodes[1]], driver)
                    self.change_verify_service_state(
                        [service, key], 'start', 'OK', lma_node,
                        [service_nodes[0], service_nodes[1]], driver)
        finally:
            driver.close()

    @test(depends_on=[smoke.deploy_lma_infra_alerting_plugin_in_ha_mode],
          groups=["warning_alert_node_infra_alerting"])
    @log_snapshot_after_test
    def warning_alert_node_infra_alerting(self):
        """Verify that the warning alerts for nodes show up in the
         Grafana and Nagios UI.

        Scenario:
            1.  Open the Nagios URL
            2.  Connect to one of the controller nodes using ssh and
             run:
                    fallocate -l $(df | grep /dev/mapper/mysql-root
                    | awk '{ printf("%.0f\n", 1024 * ((($3 + $4) * 96
                    / 100) - $3))}') /var/lib/mysql/test
            3.  Wait for at least 1 minute.
            4.  On Nagios, check the following items:
                    - the ‘mysql’ service is in ‘OK’ state,
                    - the ‘mysql-nodes.mysql-fs’ service is in ‘WARNING’
                     state for the node.
            5.  Connect to a second controller node using ssh and run:
                    fallocate -l $(df | grep /dev/mapper/mysql-root
                    | awk '{ printf("%.0f\n", 1024 * ((($3 + $4) * 96
                     / 100) - $3))}') /var/lib/mysql/test
            6.  Wait for at least 1 minute.
            7.  On Nagios, check the following items:
                    - the ‘mysql’ service is in ‘WARNING’ state,
                    - the ‘mysql-nodes.mysql-fs’ service is in ‘WARNING’
                     state for the 2 nodes,
                    - the local user root on the lma node has received an
                     email about the service
                    being in warning state.
            8.  Run the following command on both controller nodes:
                    rm /var/lib/mysql/test
            9. Wait for at least 1 minutes.
            10. On Nagios, check the following items:
                    - the ‘mysql’ service is in ‘OK’ state,
                    - the ‘mysql-nodes.mysql-fs’ service is in ‘OKAY’ state
                     for the 2 nodes,
                    - the local user root on the lma node has received an
                     email about the recovery of the service.

        Duration 15m
        """
        self.env.revert_snapshot("deploy_lma_alerting_plugin_ha")

        driver = self.get_nagios_main_page()

        lma_node = self.get_primary_lma_node()
        nailgun_nodes = self.fuel_web.get_nailgun_cluster_nodes_by_roles(
                        self.helpers.cluster_id, ['controller'])
        service_nodes = self.fuel_web.get_devops_nodes_by_nailgun_nodes(
            nailgun_nodes)
        try:
            self.change_verify_node_service_state(
                ['mysql', 'mysql-nodes.mysql-fs'], 'WARNING', '96', lma_node,
                [service_nodes[0].name, service_nodes[1].name], driver)
        finally:
            driver.close()

    @test(depends_on=[smoke.deploy_lma_infra_alerting_plugin_in_ha_mode],
          groups=["critical_alert_node_infra_alerting"])
    @log_snapshot_after_test
    def critical_alert_node_infra_alerting(self):
        """Verify that the critical alerts for nodes show up in the
         Grafana and Nagios UI.

        Scenario:
            1.  Open the Nagios URL
            2.  Connect to one of the controller nodes using ssh and run:
                    fallocate -l $(df | grep /dev/mapper/mysql-root
                    | awk '{ printf("%.0f\n", 1024 * ((($3 + $4) *
                    98 / 100) - $3))}') /var/lib/mysql/test
            3.  Wait for at least 1 minute.
            4.  On Nagios, check the following items:
                    - the ‘mysql’ service is in ‘OK’ state,
                    - the ‘mysql-nodes.mysql-fs’ service is in ‘CRITICAL’
                     state for the node.
            5.  Connect to a second controller node using ssh and run:
                    fallocate -l $(df | grep /dev/mapper/mysql-root
                    | awk '{ printf("%.0f\n", 1024 * ((($3 + $4) *
                    98 / 100) - $3))}') /var/lib/mysql/test
            6.  Wait for at least 1 minute.
            7.  On Nagios, check the following items:
                    - the ‘mysql’ service is in ‘CRITICAL’ state,
                    - the ‘mysql-nodes.mysql-fs’ service is in ‘CRITICAL’
                     state for the 2 nodes,
                    - the local user root on the lma node has received an
                    email about the service
                    being in warning state.
            8.  Run the following command on both controller nodes:
                    rm /var/lib/mysql/test
            9. Wait for at least 1 minutes.
            10. On Nagios, check the following items:
                    - the ‘mysql’ service is in ‘OK’ state,
                    - the ‘mysql-nodes.mysql-fs’ service is in ‘OKAY’ state
                     for the 2 nodes,
                    - the local user root on the lma node has received an
                    email about the recovery of the service.

        Duration 15m
        """
        self.env.revert_snapshot("deploy_lma_alerting_plugin_ha")

        driver = self.get_nagios_main_page()

        lma_node = self.get_primary_lma_node()
        nailgun_nodes = self.fuel_web.get_nailgun_cluster_nodes_by_roles(
                        self.helpers.cluster_id, ['controller'])
        service_nodes = self.fuel_web.get_devops_nodes_by_nailgun_nodes(
            nailgun_nodes)
        # TODO: All services except SSH management network will fall in
        # UNKNOWN state. Test will fail on status check.
        try:
            self.change_verify_node_service_state(
                ['mysql', 'mysql-nodes.mysql-fs'], 'CRITICAL', '98',
                lma_node, [service_nodes[0].name, service_nodes[1].name],
                driver)
        finally:
            driver.close()
