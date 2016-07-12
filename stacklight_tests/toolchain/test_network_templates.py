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

import copy

from fuelweb_test.helpers.decorators import log_snapshot_after_test
from fuelweb_test import logger
from fuelweb_test import settings
from proboscis import asserts
from proboscis import test

from stacklight_tests.toolchain import api


@test(groups=["plugins"])
class TestToolchainNetworkTemplates(api.ToolchainApi):
    """Class for testing the LMA Toolchain plugins when using network
    templates.
    """

    @test(depends_on_groups=["prepare_slaves_3"],
          groups=["deploy_toolchain_with_network_template", "deploy",
                  "toolchain", "network_templates"])
    @log_snapshot_after_test
    def deploy_toolchain_with_network_template(self):
        """Deploy a cluster with the LMA Toolchain plugins using network
        templates.

        Scenario:
            1. Upload the LMA Toolchain plugins to the master node
            2. Install the plugins
            3. Create the cluster using VxLAN segmentation
            4. Add 1 node with controller role
            5. Add 1 node with compute and cinder roles
            6. Add 1 node with plugin roles
            7. Upload the custom network template
            8. Modify the L3 configuration
            9. Deploy the cluster
            10. Check that LMA Toolchain plugins are running
            11. Run OSTF

        Duration 60m
        Snapshot deploy_toolchain_with_network_template
        """
        self.check_run("deploy_toolchain_with_network_template")
        self.env.revert_snapshot("ready_with_3_slaves")

        self.prepare_plugins()

        self.helpers.create_cluster(
            name="deploy_toolchain_with_network_template",
            settings={
                "net_provider": "neutron",
                "net_segment_type": settings.NEUTRON_SEGMENT["tun"]
            }
        )

        self.activate_plugins()

        nailgun_client = self.helpers.nailgun_client
        network_template = self.get_network_template("monitoring")
        nailgun_client.upload_network_template(
            cluster_id=self.helpers.cluster_id,
            network_template=network_template)
        logger.info("Network template: {0}".format(network_template))

        networks = nailgun_client.get_network_groups()
        logger.info("Network groups before update: {0}".format(networks))

        # Hijack the management network's address space for the monitoring
        # network
        management_net = None
        for n in networks:
            if n["name"] == "management":
                management_net = n
                break
        asserts.assert_is_not_none(
            management_net, "Couldn't find management network")
        monitoring_net = copy.deepcopy(management_net)
        monitoring_net["name"] = "monitoring"
        monitoring_net.pop("id")
        nailgun_client.add_network_group(monitoring_net)

        networks = nailgun_client.get_network_groups()
        logger.info("Network groups after update: {0}".format(networks))

        network_config = nailgun_client.get_networks(self.helpers.cluster_id)
        for network in network_config["networks"]:
            if network["name"] == "management":
                network["cidr"] = "10.109.5.0/24"
                network["ip_ranges"] = [["10.109.5.2", "10.109.5.254"]]
                network["vlan_start"] = 101
        nailgun_client.update_network(self.helpers.cluster_id,
                                      networks=network_config["networks"])

        # Don't update the interfaces when using network templates
        self.helpers.deploy_cluster(self.settings.base_nodes,
                                    verify_network=True,
                                    update_interfaces=False)

        self.check_plugins_online()

        self.helpers.run_ostf()

        self.env.make_snapshot("deploy_toolchain_with_network_template",
                               is_make=True)
