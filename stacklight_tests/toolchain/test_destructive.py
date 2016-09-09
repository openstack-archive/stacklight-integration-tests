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
import multiprocessing
from proboscis import test
import time

from stacklight_tests.toolchain import api


@test(groups=["plugins"])
class TestDestructiveToolchainPlugin(api.ToolchainApi):
    """Class for testing plugin failover after network disaster."""

    @test(depends_on_groups=["deploy_ha_toolchain"],
          groups=["check_disaster_toolchain", "toolchain",
                  "destructive", "check_cluster_outage_toolchain"])
    @log_snapshot_after_test
    def check_cluster_outage_toolchain(self):
        """Verify that the backends and dashboards recover
        after a network outage of the whole cluster with plugins toolchain.

        Scenario:
            1. Revert the snapshot with 9 deployed nodes in HA configuration
            2. Simulate a network outage of the whole cluster
               with plugins toolchain
            3. Wait for at least 7 minutes before network recovery
            4. Wait for all services to be back online
            5. Run OSTF
            6. Check that the cluster's state is okay

        Duration 40m
        """
        self.env.revert_snapshot("deploy_ha_toolchain")

        self.helpers.emulate_whole_network_disaster(
            delay_before_recover=7 * 60)

        self.INFLUXDB_GRAFANA.wait_plugin_online()
        self.ELASTICSEARCH_KIBANA.wait_plugin_online()
        self.LMA_INFRASTRUCTURE_ALERTING.wait_plugin_online()

        # NOTE(rpromyshlennikov): OpenStack cluster can't recover after it,
        # but plugins toolchain is working properly
        self.helpers.run_ostf()

    @test(depends_on_groups=["deploy_toolchain"],
          groups=["check_disaster_toolchain", "toolchain",
                  "destructive", "check_node_outage_toolchain"])
    @log_snapshot_after_test
    def check_node_outage_toolchain(self):
        """Verify that the backends and dashboards recover after
        a network outage on a standalone plugins toolchain node.

        Scenario:
            1. Revert the snapshot with 3 deployed nodes
            2. Simulate network interruption on the Toolchain node
            3. Wait for at least 30 seconds before recover network availability
            4. Run OSTF
            5. Check that plugins toolchain is working

        Duration 20m
        """
        self.env.revert_snapshot("deploy_toolchain")

        with self.fuel_web.get_ssh_for_nailgun_node(
                self.helpers.get_master_node_by_role(
                    self.settings.stacklight_roles)
        ) as remote:
            self.remote_ops.simulate_network_interrupt_on_node(remote)

        self.INFLUXDB_GRAFANA.wait_plugin_online()
        self.ELASTICSEARCH_KIBANA.wait_plugin_online()
        self.LMA_INFRASTRUCTURE_ALERTING.wait_plugin_online()

        self.helpers.run_ostf()

    @test(depends_on_groups=["deploy_toolchain_load_ha"],
          groups=["restart_services_during_workload", "restart_services",
                  "toolchain", "destructive"])
    @log_snapshot_after_test
    def restart_services_during_workload(self):
        """Verify that all services work correctly with workload.

        Scenario:
            1. Create close to production load. Environment should generate
               a lot of logs during test. The load should be periodical.
            2. Move vip__management service into pacemaker to another
               controller node
            3. Ensure that lma_collector (heka) sending data to Elasticsearch,
               InfluxDB, Nagios.
            4. In 1 hour move vip__management service into pacemaker to
               another controller node.
            5. Ensure that lma_collector (heka) sending data to Elasticsearch,
               InfluxDB, Nagios.
            6. Check PID of hekad and collectd on all nodes and save this
               data.
            7. Stop lma_collector (heka) via "pcs resource disable
               lma_collector".
            8. Wait while pcs report that lma_collector (heka) stopped on
               all controllers.
            9. Check PID of hekad on all controllers. If hekad PID
               exist - test failed.
            10. Start lma_collector (heka) via "pcs resource enable
                lma_collector".
            11. Wait while pcs report that lma_collector (heka) started on
                all controllers.
            12. Check that data was correctly sent to Elasticsearch,
                InfluxDB, Nagios.
            13. From fuel master nodes restart lma_collector on all nodes
                except controllers.
            14. Check lma_collector (heka) PID and compare it with PID from
                step 6. If you see even 1 the same PID - test failed.
            15. Check that data was correctly sent to Elasticsearch,
                InfluxDB, Nagios.
            16. From fuel master nodes stop lma_collector on all nodes
                except controllers.
            17. Check lma_collector (heka) PID, if exist - test failed.
            18. From fuel master nodes start lma_collector on all nodes
                except controllers.
            19. Check that data was correctly sent to Elasticsearch,
                InfluxDB, Nagios.
            20. Kill heka process with 'kill -9' command on controller node.
            21. Wait while pacemaker starts heka process on this controller.
            22. Repeat previous 2 steps for all controller nodes.

        Duration 90m
        """
        self.env.revert_snapshot("error_deploy_toolchain_load_ha")

        cluster_id = self.helpers.cluster_id
        queue = multiprocessing.Queue()

        from django.db import connection
        connection.close()
        process_list = []

        process_list.append(multiprocessing.Process(
            target=self.load_generator.create_load, args=(queue, cluster_id)))
        process_list.append(multiprocessing.Process(
            target=self.restart_services_actions, args=(queue, cluster_id)))

        process_list[0].start()
        if not queue.get(timeout=60 * 5):
            raise AssertionError(
                "Failed to get 'True' from create_load method")
        process_list[1].start()
        while queue.empty():
            time.sleep(1)
        for process in process_list:
            process.terminate()
        if not queue.get():
            raise AssertionError("Test returned false. Process {0}"
                                 " had crashed!".format(queue.get()))
