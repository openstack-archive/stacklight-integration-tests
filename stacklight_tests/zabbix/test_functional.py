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
from proboscis import asserts
from proboscis import test

from stacklight_tests.zabbix import api


@test(groups=["plugins"])
class TestFunctionalZabbix(api.ZabbixApi):
    """Class for functional testing of Zabbix plugin."""

    @test(depends_on_groups=["deploy_zabbix_monitoring_ha"],
          groups=["test_zabbix_deployment", "zabbix", "functional"])
    @log_snapshot_after_test
    def test_zabbix_deployment(self):
        """Verify that zabbix packages are installed on all controllers
        and zabbix service is started.

        Scenario:
            1. Revert snapshot with zabbix ha configuration
            2. Connect to controller node.
            3. Check that zabbix packages installed.
            4. Check that zabbix service is started.
            5. Repeat steps 2-4 for all controllers.

        Duration 20m
        """
        self.env.revert_snapshot("deploy_zabbix_monitoring_ha")

        controllers = self.fuel_web.get_nailgun_cluster_nodes_by_roles(
            self.helpers.cluster_id, ['controller'])

        for controller in controllers:
            with self.fuel_web.get_ssh_for_nailgun_node(controller) as remote:
                remote.check_call("dpkg --get-selections | grep zabbix")

        self.get_node_with_zabbix_vip_fqdn()

    @test(depends_on_groups=["deploy_zabbix_monitoring_ha"],
          groups=["check_zabbix_api", "zabbix", "functional"])
    @log_snapshot_after_test
    def check_zabbix_api(self):
        """Verify that zabbix login works correctly.

        Scenario:
            1. Revert snapshot with zabbix ha configuration
            2. Check that it is possible to login with valid
             credentials
            3. Check that it is impossible to login with invalid
             credentials
            4. Check that it is possible to login with over https

        Duration 20m
        """

        self.env.revert_snapshot("deploy_zabbix_monitoring_ha")

        self.get_zabbix_web(
            username='invalid_username',
            password='invalid_password').zabbix_web_login(expected_code=400)
        self.get_zabbix_web(protocol='http').zabbix_web_login()
        self.get_zabbix_web(protocol='https').zabbix_web_login()

    @test(depends_on_groups=["deploy_zabbix_monitoring_ha"],
          groups=["check_zabbix_dashboard_configuration", "zabbix",
                  "functional"])
    @log_snapshot_after_test
    def check_zabbix_dashboard_configuration(self):
        """Verify that zabbix dashboard is preconfigured

        Scenario:
            1. Revert snapshot with zabbix ha configuration
            2. Login to zabbix web
            2. Get zabbix/screens.php
            3. Check preconfigured graphs:
                - screen 'OpenStack Cluster'
                - screen 'Ceph' if Ceph is deployed

        Duration 10m
        """
        self.env.revert_snapshot("deploy_zabbix_monitoring_ha")

        zabbix_web = self.get_zabbix_web()
        zabbix_web.zabbix_web_login()

        screens_html = zabbix_web.get_zabbix_web_screen()

        found = False
        for tag in screens_html.find_all('td'):
            if 'Openstack Cluster' == tag.text:
                found = True

        asserts.assert_true(found, "'Openstack cluster' screen was not found"
                                   " on screens.php")

        ceph_nodes = self.fuel_web.get_nailgun_cluster_nodes_by_roles(
            self.helpers.cluster_id, ['ceph-osd'])
        if ceph_nodes:
            found = False
            for tag in screens_html.find_all('td'):
                if 'Openstack Cluster' == tag.text:
                    found = True
            asserts.assert_true(found, "'Ceph' screen was not found"
                                       " on screens.php")

    @test(depends_on_groups=["deploy_zabbix_monitoring_ha"],
          groups=["test_triggers", "zabbix", "functional"])
    @log_snapshot_after_test
    def test_triggers(self):
        """Verify that zabbix login works correctly.

        Scenario:
            1. Revert snapshot with zabbix ha configuration
            2. Check that all services have '0' status

        Duration 10m
        """

        self.env.revert_snapshot("deploy_zabbix_monitoring_ha")

        result = self.get_zabbix_api().do_request('trigger.get', {
            "output": ["triggerid"], "filter": {"value": 1},
            "sortfield": "priority"})
        asserts.assert_true(len(result['result']) == 0,
                            "Some triggers have '1' status: {0}".format(
                                result['result']))

    @test(depends_on_groups=["deploy_zabbix_monitoring_ha"],
          groups=["test_trigger_api", "zabbix", "functional"])
    @log_snapshot_after_test
    def test_trigger_api(self):
        """Verify that the API is detected as down.

        Scenario:
            1. Revert snapshot with zabbix ha configuration.
            2. Log into on controller node.
            3. Stop neutron-server.
            4. On dashboard verify that alerts are present.

        Duration 10m
        """

        self.env.revert_snapshot("deploy_zabbix_monitoring_ha")

        controller = self.fuel_web.get_nailgun_cluster_nodes_by_roles(
            self.helpers.cluster_id, ['controller'])[0]
        with self.fuel_web.get_ssh_for_nailgun_node(controller) as remote:
            remote.check_call("stop neutron-server",
                              "Cannot stop neutron-server on {0}!".format(
                                  controller['name']))

        alerts = [
            {'priority': '4',
             'description': 'Neutron API test failed on {HOST.NAME}'},
            {'priority': '4',
             'description': 'Neutron Server service is down on {HOST.NAME}'},
            {'priority': '4', 'description': 'Neutron Server process '
                                             'is not running on {HOST.NAME}'},
            {'priority': '3',
             'description': '{} backend of neutron proxy down'.format(
                 controller["hostname"])}
        ]

        self.wait_for_trigger(alerts)
