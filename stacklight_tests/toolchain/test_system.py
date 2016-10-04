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
from proboscis import asserts
from proboscis import test

from stacklight_tests.toolchain import api


@test(groups=["plugins"])
class TestNodesToolchain(api.ToolchainApi):
    """Class for system tests for the LMA Toolchain plugins."""

    @test(depends_on_groups=["deploy_ha_toolchain"],
          groups=["check_scaling_toolchain", "scaling", "toolchain", "system",
                  "add_remove_controller_toolchain"])
    @log_snapshot_after_test
    def add_remove_controller_toolchain(self):
        """Verify that the number of controllers can scale up and down

        Scenario:
            1. Revert snapshot with 9 deployed nodes in HA configuration
            2. Remove one controller node and update the cluster
            3. Check that plugin is working
            4. Run OSTF
            5. Add one controller node (return previous state) and
               update the cluster
            6. Check that plugins are working
            7. Run OSTF

        Duration 120m
        """
        self.env.revert_snapshot("deploy_ha_toolchain")

        manipulated_node = {'slave-03': ['controller']}

        # Remove controller
        self.helpers.remove_nodes_from_cluster(manipulated_node)

        self.check_plugins_online()

        self.helpers.run_ostf(should_fail=1)

        # Add controller
        self.helpers.add_nodes_to_cluster(manipulated_node)

        self.check_plugins_online()

        self.helpers.run_ostf(should_fail=1)

    @test(depends_on_groups=["deploy_ha_toolchain"],
          groups=["check_scaling_toolchain", "scaling", "toolchain", "system",
                  "add_remove_compute_toolchain"])
    @log_snapshot_after_test
    def add_remove_compute_toolchain(self):
        """Verify that the number of computes can scale up and down

        Scenario:
            1. Revert snapshot with 9 deployed nodes in HA configuration
            2. Remove one compute node and update the cluster
            3. Check that plugin is working
            4. Run OSTF
            5. Add one compute node (return previous state) and
               update the cluster
            6. Check that plugins are working
            7. Run OSTF

        Duration 120m
        """
        self.env.revert_snapshot("deploy_ha_toolchain")

        manipulated_node = {'slave-04': ['compute', 'cinder']}

        # Remove compute
        self.helpers.remove_nodes_from_cluster(manipulated_node)

        self.check_plugins_online()

        self.helpers.run_ostf(should_fail=1)

        # Add compute
        self.helpers.add_nodes_to_cluster(manipulated_node)

        self.check_plugins_online()

        self.helpers.run_ostf(should_fail=1)

    @test(depends_on_groups=["deploy_ha_toolchain"],
          groups=["check_scaling_toolchain", "scaling",
                  "toolchain", "system",
                  "add_remove_toolchain_node"])
    @log_snapshot_after_test
    def add_remove_toolchain_node(self):
        """Verify that the number of StackLight nodes can scale up and down

        Scenario:
            1. Revert snapshot with 9 deployed nodes in HA configuration
            2. Remove one node with StackLight roles and update the cluster
            3. Check that plugin are working
            4. Run OSTF
            5. Add one node with StackLight roles (return previous state) and
               update the cluster
            6. Check that plugins are working
            7. Run OSTF

        Duration 120m
        """
        self.env.revert_snapshot("deploy_ha_toolchain")

        manipulated_node = {'slave-07': self.settings.stacklight_roles}
        manipulated_node_hostname = self.helpers.get_hostname_by_node_name(
            manipulated_node.keys()[0])

        self.check_nodes_count(3, manipulated_node_hostname, True)

        # Remove node with StackLight roles
        self.helpers.remove_nodes_from_cluster(manipulated_node)

        self.check_plugins_online()

        # NOTE(vgusev): Do not check influxdb node count because node is not
        # removed from database and the number 3 is always returned
        self.check_nodes_count(2, manipulated_node_hostname, False,
                               ignored_plugins=[self.INFLUXDB_GRAFANA])

        self.helpers.run_ostf()

        # Add node with StackLight roles
        self.helpers.add_nodes_to_cluster(manipulated_node)

        self.check_plugins_online()

        manipulated_node_hostname = self.helpers.get_hostname_by_node_name(
            manipulated_node.keys()[0])

        self.check_nodes_count(3, manipulated_node_hostname, True)

        self.helpers.run_ostf()

    @test(depends_on_groups=["prepare_slaves_3"],
          groups=["toolchain_createmirror_deploy_plugins", "system",
                  "toolchain", "createmirror"])
    @log_snapshot_after_test
    def toolchain_createmirror_deploy_plugins(self):
        """Run fuel-createmirror and deploy environment

        Scenario:
            1. Copy the LMA Toolchain plugins to the Fuel Master node and
               install the plugins.
            2. Run the following command on the master node:
               fuel-createmirror
            3. Create an environment with enabled plugins in the
               Fuel Web UI and deploy it.
            4. Run OSTF.

        Duration 60m
        """
        self.env.revert_snapshot("ready_with_3_slaves")

        self.prepare_plugins()

        self.helpers.fuel_createmirror()

        self.helpers.create_cluster(name=self.__class__.__name__)

        self.activate_plugins()

        self.helpers.deploy_cluster(self.settings.base_nodes)

        self.check_plugins_online()

        self.helpers.run_ostf()

    @test(depends_on_groups=["deploy_toolchain"],
          groups=["toolchain_createmirror_setup_repos",
                  "system", "toolchain", "createmirror"])
    @log_snapshot_after_test
    def toolchain_createmirror_setup_repos(self):
        """Check work after fuel-createmirror and setup core repositories.

        Scenario:
            1. Revert the snapshot with 3 deployed nodes
            2. Get pid of services which were launched
               on controller/compute/storage/etc nodes by plugin and store them
            3. Run the following commands on the master node:
               `fuel-mirror create -P ubuntu -G mos`
               `fuel-mirror apply --replace -P ubuntu -G mos`
            4. Run the following command on the master node:
               `fuel --env ENV_ID node --node-id Node1 ... NodeN --tasks setup_repositories` # noqa
            5. Check that all nodes are remain in ready status
            6. Get pid of services which were launched
               on controller/compute/storage/etc nodes by plugin
               and check that they wasn't changed from last check
            7. Run OSTF

        Duration 60m
        """
        self.env.revert_snapshot("deploy_toolchain")

        ready_nodes_before = self.helpers.get_all_ready_nodes()

        ready_nodes_hostnames_before = {node["hostname"]
                                        for node in ready_nodes_before}

        pids_before = self.get_pids_of_services()

        # NOTE(rpromyshlennikov): fuel-createmirror cmd is deprecated
        # since fuel-8.0 release
        self.helpers.replace_ubuntu_mirror_with_mos()
        self.helpers.fuel_create_repositories(ready_nodes_before)

        # NOTE(rpromyshlennikov): next check will fail
        # before this bug will be fixed
        # https://bugs.launchpad.net/lma-toolchain/+bug/1570850
        ready_nodes_hostnames_after = {node["hostname"] for node
                                       in self.helpers.get_all_ready_nodes()}
        asserts.assert_equal(
            ready_nodes_hostnames_before, ready_nodes_hostnames_after,
            "List of ready nodes is not equal, "
            "before createmirror: {}, "
            "after createmirror: {}.".format(ready_nodes_hostnames_before,
                                             ready_nodes_hostnames_after)
        )

        pids_after = self.get_pids_of_services()
        asserts.assert_equal(
            pids_after, pids_before,
            "PIDs of services not equal, "
            "before createmirror: {}, "
            "after createmirror: {}.".format(pids_before, pids_after))

        self.check_plugins_online()

        self.helpers.run_ostf()

    @test(depends_on_groups=["deploy_toolchain"],
          groups=["check_toolchain_after_maintenance_update",
                  "system", "toolchain", "maintenance_update"])
    @log_snapshot_after_test
    def check_toolchain_after_maintenance_update(self):
        """Check work after applying maintenance update.

        Scenario:
            1. Revert the snapshot with 3 deployed nodes
            2. Get pid of services which were launched
               on controller/compute/storage/etc nodes by plugin and store them
            3. Apply maintenance update
            4. Get pid of services which were launched
               on controller/compute/storage/etc nodes by plugin
               and verify that they wasn't changed from last check
            5. Run OSTF

        Duration 240m
        """
        self.env.revert_snapshot("deploy_toolchain")

        ready_nodes_before = self.helpers.get_all_ready_nodes()

        ready_nodes_hostnames_before = {node["hostname"]
                                        for node in ready_nodes_before}

        pids_before = self.get_pids_of_services()

        self.helpers.apply_maintenance_update()

        ready_nodes_hostnames_after = {node["hostname"] for node
                                       in self.helpers.get_all_ready_nodes()}

        asserts.assert_equal(
            ready_nodes_hostnames_before, ready_nodes_hostnames_after,
            "List of ready nodes is not equal, "
            "before maintenance update: {}, "
            "after maintenance update: {}.".format(
                ready_nodes_hostnames_before, ready_nodes_hostnames_after)
        )

        pids_after = self.get_pids_of_services()
        asserts.assert_equal(
            pids_after, pids_before,
            "PIDs of services not equal, "
            "before maintenance update: {}, "
            "after maintenance update: {}.".format(pids_before, pids_after))

        self.check_plugins_online()

        self.helpers.run_ostf()

    @test(depends_on_groups=["deploy_ha_toolchain"],
          groups=["shutdown_infrastructure_alerting_node_in_toolchain",
                  "failover", "toolchain", "system", "destructive"])
    @log_snapshot_after_test
    def shutdown_infrastructure_alerting_node_in_toolchain(self):
        """Verify that failover for LMA Infrastructure Alerting cluster
        in plugins toolchain works.

        Scenario:
            1. Shutdown node were vip_infrastructure_alerting_mgmt_vip
               was started.
            2. Check that vip_infrastructure_alerting was started
               on another plugin node.
            3. Check that plugins toolchain is working.
            4. Check that no data lost after shutdown.
            5. Run OSTF.

        Duration 30m
        """
        self.env.revert_snapshot("deploy_ha_toolchain")

        self.LMA_INFRASTRUCTURE_ALERTING.check_plugin_failover()

        self.check_plugins_online()

        self.helpers.run_ostf()

    @test(depends_on_groups=["deploy_ha_toolchain"],
          groups=["shutdown_influxdb_grafana_node_in_toolchain",
                  "failover", "toolchain", "system", "destructive"])
    @log_snapshot_after_test
    def shutdown_influxdb_grafana_node_in_toolchain(self):
        """Verify that failover for InfluxDB cluster
        in plugins toolchain works.

        Scenario:
            1. Shutdown node were vip_influxdb was started.
            2. Check that vip_influxdb was started on another plugin node.
            3. Check that plugins toolchain is working.
            4. Check that no data lost after shutdown.
            5. Run OSTF.

        Duration 30m
        """
        self.env.revert_snapshot("deploy_ha_toolchain")

        self.INFLUXDB_GRAFANA.check_plugin_failover()

        self.check_plugins_online()

        self.helpers.run_ostf()

    @test(depends_on_groups=["deploy_ha_toolchain"],
          groups=["shutdown_elasticsearch_kibana_node_in_toolchain",
                  "failover", "toolchain", "system", "destructive"])
    @log_snapshot_after_test
    def shutdown_elasticsearch_kibana_node_in_toolchain(self):
        """Verify that failover for Elasticsearch cluster
        in plugins toolchain works.

        Scenario:
            1. Shutdown node were es_vip_mgmt was started.
            2. Check that es_vip_mgmt was started on another plugin node.
            3. Check that plugins toolchain is working.
            4. Check that no data lost after shutdown.
            5. Run OSTF.

        Duration 30m
        """
        self.env.revert_snapshot("deploy_ha_toolchain")

        self.ELASTICSEARCH_KIBANA.check_plugin_failover()

        self.check_plugins_online()

        self.helpers.run_ostf()

    @test(depends_on_groups=["prepare_slaves_9"],
          groups=["deploy_toolchain_ha_ceph_backend", "deploy", "deploy_ha",
                  "toolchain", "smoke"])
    @log_snapshot_after_test
    def deploy_toolchain_ha_ceph_backend(self):
        """Deploy plugins in HA mode with Ceph backend

        Scenario:
            1.  Create new environment with plugins and Ceph backend.
            2.  Add 3 controllers, 3 compute+ceph, 3 toolchain nodes
                and deploy the environment.
            3.  Check that plugins work.
            4.  Run OSTF.

        Duration 120m
        """

        self.env.revert_snapshot("ready_with_9_slaves")

        self.prepare_plugins()

        data = {
            'volumes_ceph': True,
            'images_ceph': True,
            'volumes_lvm': False,
        }

        self.helpers.create_cluster(name=self.__class__.__name__,
                                    settings=data)

        self.activate_plugins()

        node_roles = {
            'slave-01': ['controller'],
            'slave-02': ['controller'],
            'slave-03': ['controller'],
            'slave-04': ['compute', 'ceph-osd'],
            'slave-05': ['compute', 'ceph-osd'],
            'slave-06': ['compute', 'ceph-osd'],
            'slave-07': self.settings.stacklight_roles,
            'slave-08': self.settings.stacklight_roles,
            'slave-09': self.settings.stacklight_roles
        }

        self.helpers.deploy_cluster(node_roles)

        self.check_plugins_online()

        self.helpers.run_ostf()

    @test(depends_on_groups=["prepare_slaves_9"],
          groups=["deploy_toolchain_ha_platform_components", "deploy",
                  "deploy_ha", "toolchain", "smoke"])
    @log_snapshot_after_test
    def deploy_toolchain_ha_platform_components(self):
        """Deploy plugins with platform components

        Scenario:
            1.  Create new environment with plugins and enable Ceilometer,
                Sahara and Murano.
            2.  Add 3 controllers+mongo, 3 compute+cinder,
                3 toolchain nodes and deploy the environment.
            3.  Check that plugins work.
            4.  Run OSTF.

        Duration 120m
        """

        self.env.revert_snapshot("ready_with_9_slaves")

        self.prepare_plugins()

        data = {
            'sahara': True,
            'murano': True,
            'ceilometer': True
        }

        self.helpers.create_cluster(name=self.__class__.__name__,
                                    settings=data)

        self.activate_plugins()

        node_roles = {
            'slave-01': ['controller', 'mongo'],
            'slave-02': ['controller', 'mongo'],
            'slave-03': ['controller', 'mongo'],
            'slave-04': ['compute', 'cinder'],
            'slave-05': ['compute', 'cinder'],
            'slave-06': ['compute', 'cinder'],
            'slave-07': self.settings.stacklight_roles,
            'slave-08': self.settings.stacklight_roles,
            'slave-09': self.settings.stacklight_roles
        }

        self.helpers.deploy_cluster(node_roles)

        self.check_plugins_online()

        self.helpers.run_ostf()
