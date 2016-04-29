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
class TestLMAInfraAlertingPluginDestructive(api.InfraAlertingPluginApi):
    """Class for destructive testing the LMA Infrastructure Alerting plugin."""

    @test(depends_on=[smoke.deploy_lma_infra_alerting],
          groups=["simulate_net_failure_lma_infra_alerting"])
    @log_snapshot_after_test
    def simulate_net_failure_lma_infra_alerting(self):
        """Simulate network failure on the analytics node

        Scenario:
            1. Revert snapshot with 3 deployed nodes
            2. Simulate network interruption on plugin node
            3. Wait for at least 30 seconds before recover network availability
            4. Recover network availability
            5. Check that plugin is working
            6. Run OSTF
        Duration 20m
        """
        self.env.revert_snapshot("deploy_lma_alerting_plugin")

        nailgun_nodes = self.fuel_web.get_nailgun_cluster_nodes_by_roles(
            self.helpers.cluster_id, self.settings.role_name)
        devops_nodes = self.fuel_web.get_devops_nodes_by_nailgun_nodes(
            nailgun_nodes)

        with self.fuel_web.get_ssh_for_node(devops_nodes[0].name) as remote:
            self.remote_ops.simulate_network_interrupt_on_node(remote)

        self.check_plugin_online()
        self.helpers.run_ostf()
