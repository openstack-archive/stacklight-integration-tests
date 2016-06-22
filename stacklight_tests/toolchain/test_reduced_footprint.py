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
from proboscis import asserts
from proboscis import test

from stacklight_tests.toolchain import api
from stacklight_tests.toolchain import toolchain_settings as settings


@test(groups=["plugins"])
class TestToolchainReducedFootprint(api.ToolchainApi):
    """Class for testing the LMA Toolchain plugins with Reduced Footprint.
    nodes (aka Reduced Footprint).
    """

    @test(depends_on_groups=["prepare_slaves_3"],
          groups=["deploy_toolchain_with_reduced_footprint", "deploy",
                  "toolchain", "reduced_footprint"])
    @log_snapshot_after_test
    def deploy_toolchain_with_reduced_footprint(self):
        """Deploy a cluster with the LMA Toolchain plugins using the Reduced
        Footprint feature (aka virt nodes).

        Scenario:
            1. Enable the advanced features.
            2. Upload the LMA Toolchain plugins to the master node
            3. Install the plugins
            4. Create the cluster
            5. Add 1 node with virt role
            6. Spawn 1 virtual machine on the virt node
            7. Add 1 node with controller role
            8. Add 1 node with compute and cinder roles
            9. Assign the StackLight roles to the virtual machine
            10. Deploy the cluster
            11. Check that LMA Toolchain plugins are running
            12. Run OSTF

        Duration 60m
        Snapshot deploy_toolchain_with_reduced_footprint
        """
        self.check_run("deploy_toolchain_with_reduced_footprint")

        self.env.revert_snapshot("ready_with_3_slaves")

        fuel_web = self.helpers.fuel_web
        nailgun_client = self.helpers.nailgun_client
        checkers.enable_feature_group(self.env, "advanced")

        self.prepare_plugins()

        self.helpers.create_cluster(
            name="deploy_toolchain_with_reduced_footprint",
            settings={
                "net_provider": "neutron",
                "net_segment_type": fuelweb_settings.NEUTRON_SEGMENT["tun"]
            }
        )

        self.activate_plugins()

        self.helpers.add_nodes_to_cluster({
            "slave-03": ["virt"],
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

        logger.info("Waiting for the virtual manchine to be up...")
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
            "Assigning StackLight roles to node {}".format(vm_node["id"]))
        nailgun_client.update_nodes([{
            "cluster_id": self.helpers.cluster_id,
            "id": vm_node["id"],
            "pending_roles": settings.stacklight_roles,
            "pending_addition": True
        }])
        # The mapping between the hypervisor's NICs and the virtual machine's
        # NICs is defined on the Fuel node in
        # /etc/puppet/modules/osnailyfacter/templates/vm_libvirt.erb. In
        # practice, only the management and storage interfaces need to be
        # swapped. Note that the interface names on the virtual machines are
        # the legacy ones (ethX instead of enpXsY)
        fuel_web.update_node_networks(
            vm_node["id"],
            {
                "eth0": ["fuelweb_admin", "private"],
                "eth1": ["public"],
                "eth2": ["storage"],
                "eth3": ["management"],
                "eth4": []
            })
        self.helpers.deploy_cluster({
            "slave-01": ["controller"],
            "slave-02": ["compute", "cinder"],
        })
        # The 'hiera' and post-deployment tasks have to be re-executed
        # "manually" for the virt node
        self.helpers.run_tasks([virt_node], tasks=['hiera'],
                               start="post_deployment_start", timeout=20 * 60)

        self.check_plugins_online()
        self.helpers.run_ostf()

        self.env.make_snapshot("deploy_toolchain_with_reduced_footprint",
                               is_make=True)
