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

from stacklight_tests.elasticsearch_kibana import api


@test(groups=["plugins"])
class TestNodesElasticsearchPlugin(api.ElasticsearchPluginApi):
    """Class for system tests for Elasticsearch-Kibana plugin."""

    @test(depends_on_groups=['deploy_ha_elasticsearch_kibana'],
          groups=["check_scaling_elasticsearch_kibana", "scaling",
                  "elasticsearch_kibana", "system",
                  "add_remove_controller_elasticsearch_kibana"])
    @log_snapshot_after_test
    def add_remove_controller_elasticsearch_kibana(self):
        """Verify that the number of controllers can scale up and down

        Scenario:
            1. Revert snapshot with 9 deployed nodes in HA configuration
            2. Remove one controller node and redeploy the cluster
            3. Check that Elasticsearch/Kibana are running
            4. Run OSTF
            5. Add one controller node (return previous state) and
               redeploy the cluster
            6. Check that Elasticsearch/Kibana are running
            7. Run OSTF

        Duration 120m
        """
        self.env.revert_snapshot("deploy_ha_elasticsearch_kibana")

        target_node = {'slave-03': ['controller']}

        # Remove a controller
        self.helpers.remove_node_from_cluster(target_node)

        self.check_plugin_online()

        # After removing a controller, one OSTF test should fail
        self.helpers.run_ostf(should_fail=1)

        # Add a controller
        self.helpers.add_node_to_cluster(target_node)

        self.check_plugin_online()

        self.helpers.run_ostf(should_fail=1)

    @test(depends_on_groups=['deploy_ha_elasticsearch_kibana'],
          groups=["check_scaling_elasticsearch_kibana", "scaling",
                  "elasticsearch_kibana", "system",
                  "add_remove_compute_elasticsearch_kibana"])
    @log_snapshot_after_test
    def add_remove_compute_elasticsearch_kibana(self):
        """Verify that the number of computes can scale up and down

        Scenario:
            1. Revert snapshot with 9 deployed nodes in HA configuration
            2. Remove one compute node and redeploy the cluster
            3. Check that Elasticsearch/Kibana are running
            4. Run OSTF
            5. Add one compute node (return previous state) and
               redeploy the cluster
            6. Check that Elasticsearch/Kibana are running
            7. Run OSTF

        Duration 120m
        """
        self.env.revert_snapshot("deploy_ha_elasticsearch_kibana")

        target_node = {'slave-04': ['compute', 'cinder']}

        # Remove a compute node
        self.helpers.remove_node_from_cluster(target_node)

        self.check_plugin_online()

        # After removing a controller, one OSTF test should fail
        self.helpers.run_ostf(should_fail=1)

        # Add a compute node
        self.helpers.add_node_to_cluster(target_node)

        self.check_plugin_online()

        self.helpers.run_ostf(should_fail=1)

    @test(depends_on_groups=['deploy_ha_elasticsearch_kibana'],
          groups=["check_scaling_elasticsearch_kibana", "scaling",
                  "elasticsearch_kibana", "system",
                  "add_remove_elasticsearch_kibana_node"])
    @log_snapshot_after_test
    def add_remove_elasticsearch_kibana_node(self):
        """Verify that the number of Elasticsearch-Kibana nodes
        can scale up and down

        Scenario:
            1. Revert the snapshot with 9 deployed nodes in HA configuration
            2. Remove one Elasticsearch/Kibana node and redeploy the cluster
            3. Check that Elasticsearch/Kibana are running
            4. Run OSTF
            5. Add one Elasticsearch-Kibana node (return previous state) and
               redeploy the cluster
            6. Check that Elasticsearch/Kibana are running
            7. Run OSTF

        Duration 120m
        """
        self.env.revert_snapshot("deploy_ha_elasticsearch_kibana")

        self.check_elasticsearch_nodes_count(3)

        target_node = {'slave-07': self.settings.role_name}

        # Remove an Elasticsearch-Kibana node
        self.helpers.remove_node_from_cluster(target_node)

        self.check_plugin_online()

        self.check_elasticsearch_nodes_count(2)

        self.fuel_web.run_ostf()

        # Add an Elasticsearch-Kibana node
        self.helpers.add_node_to_cluster(target_node)

        self.check_plugin_online()

        self.check_elasticsearch_nodes_count(3)

        self.helpers.run_ostf()

    @test(depends_on_groups=["deploy_ha_elasticsearch_kibana"],
          groups=["check_failover_elasticsearch_kibana" "failover",
                  "elasticsearch_kibana", "system", "destructive",
                  "shutdown_elasticsearch_kibana_node"])
    @log_snapshot_after_test
    def shutdown_elasticsearch_kibana_node(self):
        """Verify that failover for Elasticsearch cluster works.

        Scenario:
            1. Shutdown node were es_vip_mgmt was started.
            2. Check that es_vip_mgmt was started on another
               elasticsearch_kibana node.
            3. Check that plugin is working.
            4. Check that no data lost after shutdown.
            5. Run OSTF.

        Duration 30m
        """
        self.env.revert_snapshot("deploy_ha_elasticsearch_kibana")

        vip_name = self.helpers.full_vip_name(self.settings.vip_name)

        target_node = self.helpers.get_node_with_vip(
            self.settings.role_name, vip_name)

        self.helpers.power_off_node(target_node)

        self.helpers.wait_for_vip_migration(
            target_node, self.settings.role_name, vip_name)

        self.check_plugin_online()

        self.helpers.run_ostf()

    @test(depends_on_groups=['prepare_slaves_3'],
          groups=["elasticsearch_kibana_createmirror_deploy_plugin",
                  "system", "elasticsearch_kibana", "createmirror"])
    @log_snapshot_after_test
    def elasticsearch_kibana_createmirror_deploy_plugin(self):
        """Run fuel-createmirror and deploy environment

        Scenario:
            1. Copy the Elasticsearch/Kibana plugin to the Fuel Master node and
               install the plugin.
            2. Run the following command on the master node:
               fuel-createmirror
            3. Create an environment with enabled plugins in the
               Fuel Web UI and deploy it.
            4. Run OSTF.

        Duration 60m
        """
        self.env.revert_snapshot("ready_with_3_slaves")

        self.prepare_plugin()

        self.helpers.fuel_createmirror()

        self.helpers.create_cluster(name=self.__class__.__name__)

        self.activate_plugin()

        self.helpers.deploy_cluster(self.base_nodes)

        self.check_plugin_online()

        self.helpers.run_ostf()
