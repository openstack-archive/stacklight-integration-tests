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

from stacklight_tests.kafka import api


@test(groups=["plugins"])
class TestNodesKafkaPlugin(api.KafkaPluginApi):
    """Class for system tests for Ceilometer-Redis plugin."""

    @test(depends_on_groups=["deploy_kafka"],
          groups=["check_scaling_kafka", "scaling",
                  "kafka", "system",
                  "add_remove_controller_kafka"])
    @log_snapshot_after_test
    def add_remove_controller_kafka(self):
        """Verify that the number of controllers can scale up and down

        Scenario:
            1. Revert snapshot with 5 deployed nodes in HA configuration
            2. Remove one controller node and redeploy the cluster
            3. Check that Kafka is running
            4. Run OSTF
            5. Add one controller node (return previous state) and
               redeploy the cluster
            6. Check that Kafka is running
            7. Run OSTF

        Duration 120m
        """
        self.env.revert_snapshot("deploy_kafka")

        target_node = {'slave-02': ['controller', self.settings.role_name]}

        # Remove a controller
        self.helpers.remove_nodes_from_cluster(target_node)

        self.check_plugin_online()

        # After removing a controller, one OSTF test should fail
        self.helpers.run_ostf()

        # Add a controller
        self.helpers.add_nodes_to_cluster(target_node)

        self.check_plugin_online()

        self.helpers.run_ostf()

    @test(depends_on_groups=["deploy_kafka"],
          groups=["check_scaling_kafka", "scaling",
                  "kafka", "system",
                  "add_remove_compute_kafka"])
    @log_snapshot_after_test
    def add_remove_compute_kafka(self):
        """Verify that the number of computes can scale up and down

        Scenario:
            1. Revert snapshot with 5 deployed nodes in HA configuration
            2. Remove one controller node and redeploy the cluster
            3. Check that Kafka is running
            4. Run OSTF
            5. Add one compute node (return previous state) and
               redeploy the cluster
            6. Check that Kafka is running
            7. Run OSTF

        Duration 120m
        """
        self.env.revert_snapshot("deploy_kafka")

        target_node = {'slave-05': ['compute', 'cinder']}

        # Remove a compute
        self.helpers.remove_nodes_from_cluster(target_node)

        self.check_plugin_online()

        # After removing a compute, one OSTF test should fail
        self.helpers.run_ostf()

        # Add a compute
        self.helpers.add_nodes_to_cluster(target_node)

        self.check_plugin_online()

        self.helpers.run_ostf()
