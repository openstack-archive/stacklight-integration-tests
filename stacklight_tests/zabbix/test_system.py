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
from netaddr import IPNetwork

from proboscis import test

from stacklight_tests.zabbix import api

from fuelweb_test.helpers.decorators import log_snapshot_after_test


@test(groups=["plugins"])
class TestZabbixPluginSystem(api.ZabbixApi):
    """Class for system testing the Zabbix plugin."""

    @test(depends_on_groups=["prepare_slaves_5"],
          groups=["deploy_zabbix_ha_offline", "system", "zabbix",
                  "createmirror"])
    @log_snapshot_after_test
    def deploy_zabbix_ha_offline(self):
        """Run fuel-createmirror and deploy environment

        Scenario:
            1. Copy Zabbix plugin to the Fuel Master
               node and install the plugin.
            2. Run the following command on the master node:
               fuel-createmirror
            3. Create an environment with enabled plugin in the
               Fuel Web UI and deploy it.
            4. Run OSTF.

        Duration 60m
        """
        self.env.revert_snapshot("ready_with_5_slaves")

        self.prepare_plugin()

        self.helpers.fuel_createmirror()

        self.helpers.create_cluster(name=self.__class__.__name__)

        self.activate_plugin()

        self.helpers.deploy_cluster(
            {
                'slave-01': ['controller'],
                'slave-02': ['controller'],
                'slave-03': ['controller'],
                'slave-04': ['compute'],
                'slave-05': ['cinder']
            }, timeout=10800
        )

        self.check_plugin_online()

        self.helpers.run_ostf()

    @test(depends_on_groups=["prepare_slaves_5"],
          groups=["test_dependant_plugins", "system", "zabbix"])
    @log_snapshot_after_test
    def test_dependant_plugins(self):
        """Check Zabbix dependant plugins

        Scenario:
            1. Upload and install Zabbix plugins.
            2. Configure EMC plugin with a fake Name/IP pair:
                MyEMCHost:10.109.0.100
            3. Configure Extreme Networks plugin with a fake Name/IP pair:
                MyXNHost:10.109.0.101
            4. Add 3 nodes with controller role.
            5. Add 1 node with compute role.
            6. Add 1 node with cinder role.
            7. Deploy cluster.
            8. Check plugin health.
            9. Run OSTF.
            10. Send and verify that traps have been received by Zabbix.

        Duration 60m
        """
        self.env.revert_snapshot("ready_with_5_slaves")

        self.prepare_plugin(dependat_plugins=True)

        self.helpers.create_cluster(name=self.__class__.__name__)

        networks = self.helpers.fuel_web.client.get_networks(
            self.helpers.cluster_id)['networks']
        public_cidr = filter(
            lambda x: x['name'] == "public", networks)[0]['cidr']
        extreme_host_ip = str(IPNetwork(public_cidr)[100])
        emc_host_ip = str(IPNetwork(public_cidr)[101])

        self.activate_plugin()
        self.activate_dependant_plugin(
            self.settings.dependant_plugins["ZABBIX_SNMPTRAPD"])
        self.activate_dependant_plugin(
            self.settings.dependant_plugins[
                "ZABBIX_MONITORING_EXTREME_NETWORKS"],
            options={'metadata/enabled': True,
                     'hosts/value': 'MyXNHost:{}'.format(extreme_host_ip)})
        self.activate_dependant_plugin(
            self.settings.dependant_plugins["ZABBIX_MONITORING_EMC"],
            options={'metadata/enabled': True,
                     'hosts/value': 'MyEMCHost:{}'.format(emc_host_ip)})

        self.helpers.deploy_cluster(
            {
                'slave-01': ['controller'],
                'slave-02': ['controller'],
                'slave-03': ['controller'],
                'slave-04': ['compute'],
                'slave-05': ['cinder']
            }, timeout=10800
        )

        self.check_plugin_online()

        self.helpers.run_ostf()

        zabbix_api = self.get_zabbix_api()
        myxnhost_id = zabbix_api.do_request(
            'host.get', {"output": ["hostid"], "filter": {"host": [
                "MyXNHost"]}})['result'][0]['hostid']
        myemchost_id = zabbix_api.do_request(
            'host.get', {"output": ["hostid"], "filter": {"host": [
                "MyEMCHost"]}})['result'][0]['hostid']

        controller = self.fuel_web.get_nailgun_cluster_nodes_by_roles(
            self.helpers.cluster_id, ['controller'])[0]

        with self.fuel_web.get_ssh_for_nailgun_node(controller) as remote:
            remote.check_call("apt-get install snmp -y")
            self.send_extreme_snmptraps(remote, extreme_host_ip)
            self.send_emc_snmptraps(remote, emc_host_ip)

        triggers = [
            {'priority': '4', 'description': 'Power Supply Failed:'
                                             ' {ITEM.VALUE1}'},
            {'priority': '1', 'description': 'Power Supply OK: {ITEM.VALUE1}'},
            {'priority': '4', 'description': 'Fan Failed: {ITEM.VALUE1}'},
            {'priority': '1', 'description': 'Fan OK: {ITEM.VALUE1}'},
            {'priority': '4', 'description': 'Link Down: {ITEM.VALUE1}'},
            {'priority': '1', 'description': 'Link Up: {ITEM.LASTVALUE1}'},
            {'priority': '1', 'description': 'SNMPtrigger Information:'
                                             ' {ITEM.VALUE1}'},
            {'priority': '2', 'description': 'SNMPtrigger Warning:'
                                             ' {ITEM.VALUE1}'},
            {'priority': '3', 'description': 'SNMPtrigger Error:'
                                             ' {ITEM.VALUE1}'},
            {'priority': '4', 'description': 'SNMPtrigger Critical:'
                                             ' {ITEM.VALUE1}'}
        ]

        self.wait_for_trigger(triggers, {"output": [
            "triggerid", "description", "priority"], "filter": {"value": 1},
            "hostids": [str(myxnhost_id), str(myemchost_id)]
        })
