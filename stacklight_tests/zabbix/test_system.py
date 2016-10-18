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

from devops.helpers.helpers import wait
from fuelweb_test.helpers import checkers
from fuelweb_test.helpers.decorators import log_snapshot_after_test
from fuelweb_test import logger
from fuelweb_test import settings as fuelweb_settings
from netaddr import IPNetwork
from proboscis import asserts
from proboscis import test

from stacklight_tests.zabbix import api


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
            }
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

    @test(depends_on_groups=["deploy_zabbix_monitoring_ha"],
          groups=["check_scaling_zabbix", "scaling", "zabbix", "system",
                  "add_remove_controller_toolchain"])
    @log_snapshot_after_test
    def add_remove_controller_toolchain(self):
        """Verify that the number of controllers can scale up and down

        Scenario:
            1. Revert snapshot with zabbix plugin deployed in HA configuration
            2. Remove one controller node and update the cluster
            3. Check that plugin is working
            4. Run OSTF
            5. Add one controller node (return previous state) and
               update the cluster
            6. Check that plugin is working
            7. Run OSTF

        Duration 120m
        """
        self.env.revert_snapshot("deploy_zabbix_monitoring_ha")

        manipulated_node = {'slave-03': ['controller']}

        # Remove controller
        self.helpers.remove_nodes_from_cluster(manipulated_node)

        self.check_plugin_online()

        self.helpers.run_ostf(should_fail=1)

        # Add controller
        self.helpers.add_nodes_to_cluster(manipulated_node)

        self.check_plugin_online()

        self.helpers.run_ostf(should_fail=1)

    @test(depends_on_groups=["deploy_zabbix_monitoring_ha"],
          groups=["check_scaling_toolchain", "scaling", "toolchain", "system",
                  "add_remove_compute_toolchain"])
    @log_snapshot_after_test
    def add_remove_compute_toolchain(self):
        """Verify that the number of computes can scale up and down

        Scenario:
            1. Revert snapshot with 9 deployed nodes in HA configuration
            2. Add one compute node and update the cluster
            3. Check that plugin is working
            4. Run OSTF
            5. Remove one compute node (return previous state) and
               update the cluster
            6. Check that plugin is working
            7. Run OSTF

        Duration 120m
        """
        self.env.revert_snapshot("deploy_zabbix_monitoring_ha")

        manipulated_node = {'slave-06': ['compute']}

        self.env.bootstrap_nodes(
            self.env.d_env.nodes().slaves[5:6])

        # Add compute
        self.helpers.add_nodes_to_cluster(manipulated_node)

        self.check_plugin_online()

        self.helpers.run_ostf()

        # Remove compute
        self.helpers.remove_nodes_from_cluster(manipulated_node)

        self.check_plugin_online()

        self.helpers.run_ostf(should_fail=1)

    @test(depends_on_groups=["prepare_slaves_3"],
          groups=["deploy_zabbix_with_reduced_footprint", "deploy",
                  "zabbix", "reduced_footprint"])
    @log_snapshot_after_test
    def deploy_zabbix_with_reduced_footprint(self):
        """Deploy a cluster with Zabbix plugin using the Reduced Footprint
        feature (aka virt nodes).

        Scenario:
            1. Enable the advanced features.
            2. Upload Zabbix plugin to the master node
            3. Install the plugin
            4. Create the cluster
            5. Add 1 node with virt role
            6. Spawn 1 virtual machine on the virt node
            7. Add 1 node with controller role
            8. Assign compute role to the virtual machine
            9. Deploy the cluster
            10. Check that Zabbix plugin is running
            11. Check that compute host is present in Zabbix hosts

        Duration 60m
        Snapshot deploy_zabbix_with_reduced_footprint
        """
        self.check_run("deploy_zabbix_with_reduced_footprint")

        self.env.revert_snapshot("ready_with_3_slaves")

        fuel_web = self.helpers.fuel_web
        nailgun_client = self.helpers.nailgun_client
        checkers.enable_feature_group(self.env, "advanced")

        self.prepare_plugin()

        self.helpers.create_cluster(
            name="deploy_zabbix_with_reduced_footprint",
            settings={
                "net_provider": "neutron",
                "net_segment_type": fuelweb_settings.NEUTRON_SEGMENT["tun"]
            }
        )

        self.activate_plugin()

        self.helpers.add_nodes_to_cluster({
            "slave-02": ["virt"],
        }, redeploy=False)

        initial_nodes = nailgun_client.list_nodes()
        virt_node = None
        for node in initial_nodes:
            if "virt" in node["pending_roles"]:
                virt_node = node
                break

        asserts.assert_is_not_none(virt_node,
                                   "Couldn't find any node with the virt role")
        vm_ram = 2
        asserts.assert_true(
            virt_node["meta"]["memory"]["total"] > vm_ram * (1024 ** 3),
            "Not enough RAM on node {0}, at least {1} GB required".format(
                virt_node["name"], vm_ram))

        nailgun_client.create_vm_nodes(
            virt_node["id"],
            [{"id": 1, "mem": vm_ram, "cpu": 1, "vda_size": "120G"}])

        logger.info(
            "Spawning 1 virtual machine on node {}".format(virt_node["id"]))
        fuel_web.spawn_vms_wait(self.helpers.cluster_id)

        logger.info("Waiting for the virtual machine to be up...")
        wait(lambda: len(nailgun_client.list_nodes()) == 4,
             timeout=10 * 60,
             timeout_msg=("Timeout waiting for 4 nodes to be ready, "
                          "current nodes:{0}\n".format('\n'.join(
                              ['id: {0}, name: {1}, online: {2}'.
                               format(i["id"], i['name'], i['online'])
                               for i in nailgun_client.list_nodes()]))))
        vm_node = None
        for node in nailgun_client.list_nodes():
            if node["id"] not in [x["id"] for x in initial_nodes]:
                vm_node = node
                break
        asserts.assert_is_not_none(vm_node,
                                   "Couldn't find the virtual machine node")

        logger.info(
            "Assigning controller role to node {}".format(vm_node["id"]))
        nailgun_client.update_nodes([{
            "cluster_id": self.helpers.cluster_id,
            "id": vm_node["id"],
            "pending_roles": ["compute"],
            "pending_addition": True
        }])

        self.helpers.deploy_cluster({
            "slave-01": ["controller"],
        })
        # The 'hiera' and post-deployment tasks have to be re-executed
        # "manually" for the virt node
        self.helpers.run_tasks([virt_node], tasks=['hiera'],
                               start="post_deployment_start", timeout=20 * 60)

        self.check_plugin_online()

        zabbix_api = self.get_zabbix_api()
        hosts = [host["name"] for host in zabbix_api.host.get(status=1)]
        compute = self.fuel_web.get_nailgun_cluster_nodes_by_roles(
            self.helpers.cluster_id, ["compute"])[0]
        asserts.assert_true(compute["fqdn"] in hosts,
                            "Compute host not found in list of Zabbix hosts")

        self.env.make_snapshot("deploy_zabbix_with_reduced_footprint",
                               is_make=True)
