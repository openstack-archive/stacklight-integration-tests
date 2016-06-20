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

from stacklight_tests.ceilometer_redis import api


@test(groups=["plugins"])
class TestNodesCeilometerRedisPlugin(api.CeilometerRedisPluginApi):
    """Class for system tests for Ceilometer-Redis plugin."""

    @test(depends_on_groups=["deploy_ceilometer_redis"],
          groups=["check_scaling_ceilometer_redis", "scaling",
                  "ceilometer_redis", "system",
                  "add_remove_controller_ceilometer_redis"])
    @log_snapshot_after_test
    def add_remove_controller_ceilometer_redis(self):
        """Verify that the number of controllers can scale up and down

        Scenario:
            1. Revert snapshot with 5 deployed nodes in HA configuration
            2. Remove one controller node and redeploy the cluster
            3. Check that Ceilometer-Redis are running
            4. Run OSTF
            5. Add one controller node (return previous state) and
               redeploy the cluster
            6. Check that Ceilometer-Redis are running
            7. Run OSTF

        Duration 120m
        """
        self.env.revert_snapshot("deploy_ceilometer_redis")

        target_node = {'slave-02': ['controller', 'mongo']}

        # Remove a controller
        self.helpers.remove_node_from_cluster(target_node)

        self.check_plugin_online()

        # After removing a controller, one OSTF test should fail
        self.helpers.run_ostf(should_fail=1)

        # Add a controller
        self.helpers.add_nodes_to_cluster(target_node)

        self.check_plugin_online()

        self.helpers.run_ostf(should_fail=1)

    @test(depends_on_groups=["deploy_ceilometer_redis"],
          groups=["check_scaling_ceilometer_redis", "scaling",
                  "ceilometer_redis", "system",
                  "add_remove_compute_ceilometer_redis"])
    @log_snapshot_after_test
    def add_remove_compute_ceilometer_redis(self):
        """Verify that the number of computes can scale up and down

        Scenario:
            1. Revert snapshot with 5 deployed nodes in HA configuration
            2. Remove one controller node and redeploy the cluster
            3. Check that Ceilometer-Redis are running
            4. Run OSTF
            5. Add one compute node (return previous state) and
               redeploy the cluster
            6. Check that Ceilometer-Redis are running
            7. Run OSTF

        Duration 120m
        """
        self.env.revert_snapshot("deploy_ceilometer_redis")

        target_node = {'slave-05': ['compute', 'cinder']}

        # Remove a compute
        self.helpers.remove_node_from_cluster(target_node)

        self.check_plugin_online()

        # After removing a compute, one OSTF test should fail
        self.helpers.run_ostf(should_fail=1)

        # Add a compute
        self.helpers.add_nodes_to_cluster(target_node)

        self.check_plugin_online()

        self.helpers.run_ostf(should_fail=1)

    @test(depends_on_groups=["prepare_slaves_5"],
          groups=["ceilometer_redis_createmirror_deploy_plugin",
                  "system", "ceilometer_redis", "createmirror"])
    @log_snapshot_after_test
    def ceilometer_redis_createmirror_deploy_plugin(self):
        """Run fuel-createmirror and deploy environment

        Scenario:
            1. Copy the Ceilometer-Redis plugin to the Fuel Master node and
               install the plugin.
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

        self.helpers.deploy_cluster(self.base_nodes)

        self.check_plugin_online()

        self.helpers.run_ostf()
