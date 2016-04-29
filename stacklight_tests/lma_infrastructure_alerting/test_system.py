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
import time
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
class TestLMAInfraAlertingPluginSystem(api.InfraAlertingPluginApi):
    """Class for system testing the LMA Infrastructure Alerting plugin."""

    @test(depends_on=[smoke.deploy_lma_infra_alerting_plugin_in_ha_mode],
          groups=["add_remove_infrastructure_alerting"])
    @log_snapshot_after_test
    def add_remove_infrastructure_alerting(self):
        """Add/remove infrastructure alerting nodes in existing environment

        Scenario:
            1.  Remove 1 node with the infrastructure_alerting role.
            2.  Re-deploy the cluster.
            3.  Check the plugin services using the CLI
            4.  Check that Nagios UI works correctly.
            5.  Run the health checks (OSTF).
            6.  Add 1 new node with the infrastructure_alerting role.
            7.  Re-deploy the cluster.
            8.  Check the plugin services using the CLI.
            9.  Check that Nagios UI works correctly.
            10. Run the health checks (OSTF).

        Duration 60m
        """
        self.env.revert_snapshot("deploy_lma_alerting_plugin_ha")

        role_name = self.settings.role_name[:].append('influxdb_grafana')
        target_node = self.helpers.get_fuel_node_name('slave-05')
        self.helpers.remove_node_from_cluster({'slave-05': role_name})
        self.run_ostf(should_fail=1)
        self.check_plugin_online()
        self.check_node_in_nagios(target_node, False)

        self.helpers.add_node_to_cluster({'slave-05': role_name})
        self.run_ostf(should_fail=1)
        self.check_plugin_online()
        target_node = self.helpers.get_fuel_node_name('slave-05')
        self.check_node_in_nagios(target_node, True)

    @test(depends_on=[smoke.deploy_lma_infra_alerting_plugin_in_ha_mode],
          groups=["shutdown_infrastructure_alerting"])
    @log_snapshot_after_test
    def shutdown_infrastructure_alerting(self):
        """Shutdown infrastructure alerting node

        Scenario:
            1.  Connect to any infrastructure_alerting node and run
             command ‘crm status’.
            2.  Shutdown node were vip_infrastructure_alerting_mgmt_vip
             was started.
            3.  Check that vip_infrastructure_alerting was started
             on another infrastructure_alerting node.
            4.  Check the plugin services using CLI.
            5.  Check that Nagios UI works correctly.
            6.  Check that no data lost after shutdown.
            7.  Run OSTF.

        Duration 60m
        """
        self.env.revert_snapshot("deploy_lma_alerting_plugin_ha")

        target_node = self.get_primary_lma_node()
        self.fuel_web.warm_shutdown_nodes([target_node])
        new_node = self.get_primary_lma_node()
        asserts.assert_not_equal(target_node, new_node)

        nailgun_nodes = self.fuel_web.get_nailgun_cluster_nodes_by_roles(
            self.helpers.cluster_id, self.settings.role_name)
        devops_nodes = self.fuel_web.get_devops_nodes_by_nailgun_nodes(
            nailgun_nodes)
        self.helpers.check_influxdb_status(devops_nodes)

        self.check_plugin_online()
        self.helpers.run_ostf()
