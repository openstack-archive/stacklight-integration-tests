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

from stacklight_tests.lma_infrastructure_alerting import api


@test(groups=["plugins"])
class TestDestructiveLMAInfraAlertingPlugin(api.InfraAlertingPluginApi):
    """Class for testing plugin failover after network disaster."""

    @test(depends_on_groups=["deploy_ha_lma_infrastructure_alerting"],
          groups=["check_disaster_lma_infrastructure_alerting",
                  "lma_infrastructure_alerting", "destructive",
                  "check_cluster_outage_lma_infrastructure_alerting"])
    @log_snapshot_after_test
    def check_cluster_outage_lma_infrastructure_alerting(self):
        """Verify that the backends and dashboards recover after a network
        outage of the whole LMA Infrastructure Alerting cluster.

        Scenario:
            1. Revert the snapshot with 9 deployed nodes in HA configuration
            2. Simulate a network outage of the whole
               LMA Infrastructure Alerting cluster
            3. Wait for at least 7 minutes before network recovery
            4. Wait for all services to be back online
            5. Run OSTF
            6. Check that the cluster's state is okay

        Duration 40m
        """
        self.env.revert_snapshot("deploy_ha_lma_infrastructure_alerting")

        self.helpers.emulate_whole_network_disaster(
            delay_before_recover=7 * 60)

        self.wait_plugin_online()

        self.helpers.run_ostf()

    @test(depends_on_groups=["deploy_lma_infrastructure_alerting"],
          groups=["check_disaster_lma_infrastructure_alerting",
                  "lma_infrastructure_alerting", "destructive",
                  "check_node_outage_lma_infrastructure_alerting"])
    @log_snapshot_after_test
    def check_node_outage_lma_infrastructure_alerting(self):
        """Verify that the backends and dashboards recover after
        a network outage on a standalone LMA Infrastructure Alerting node.

        Scenario:
            1. Revert the snapshot with 3 deployed nodes
            2. Simulate network interruption on the LMA Infrastructure Alerting
               node
            3. Wait for at least 30 seconds before recover network availability
            4. Run OSTF
            5. Check that plugin is working

        Duration 20m
        """
        self.env.revert_snapshot("deploy_lma_infrastructure_alerting")

        with self.fuel_web.get_ssh_for_nailgun_node(
                self.helpers.get_master_node_by_role(self.settings.role_name)
        ) as remote:
            self.remote_ops.simulate_network_interrupt_on_node(remote)

        self.wait_plugin_online()

        self.helpers.run_ostf()
