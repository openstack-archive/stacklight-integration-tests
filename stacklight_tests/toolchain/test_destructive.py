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
from fuelweb_test.helpers.decorators import log_snapshot_after_test
from fuelweb_test import logger
import multiprocessing
from proboscis import test
from stacklight_tests.toolchain import api
import time


@test(groups=["plugins"])
class TestLMAInfraAlertingPluginDestructive(api.ToolchainApi):
    """Class for destructive testing the LMA Infrastructure Alerting plugin."""

    @test(depends_on_groups=["prepare_slaves_9"],
          groups=["prepare_lma_plugins_load_ha"])
    @log_snapshot_after_test
    def prepare_lma_plugins_load_ha(self):
        """Prepare env for load tests with LMA plugins.

        Scenario:
            1. Upload plugins to the master node
            2. Install plugins
            3. Create cluster
            4. Add 3 nodes with controller and ceph roles
            5. Add 2 nodes with compute role
            6. Add 3 nodes with elasticsearch, lma infrastructure alerting and
               influxdb roles
            7. Deploy the cluster
            8. Check that plugins are working
            9. Run OSTF

        Duration 60m
        """

        self.check_run('prepare_lma_plugins_load_ha')

        self.env.revert_snapshot("ready_with_9_slaves")

        self.prepare_plugin()

        self.create_cluster(
            {
                'volumes_ceph': True,
                'images_ceph': True,
                'volumes_lvm': False,
                'osd_pool_size': "3"
            }
        )

        self.activate_plugin()

        self.helpers.deploy_cluster(
            {
                'slave-01': ['controller', 'ceph-osd'],
                'slave-02': ['controller', 'ceph-osd'],
                'slave-03': ['controller', 'ceph-osd'],
                'slave-04': ['compute'],
                'slave-05': ['compute'],
                'slave-06': self.settings.stacklight_roles,
                'slave-07': self.settings.stacklight_roles,
                'slave-08': self.settings.stacklight_roles,
            }
        )

        self.check_plugin_online()

        self.helpers.run_ostf()

        logger.info('Making environment snapshot '
                    'prepare_lma_plugins_load_ha')
        self.env.make_snapshot("prepare_lma_plugins_load_ha", is_make=True)

    @test(depends_on_groups=["prepare_lma_plugins_load_ha"],
          groups=["simulate_network_failure"])
    @log_snapshot_after_test
    def simulate_network_failure(self):
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
        self.env.revert_snapshot("prepare_lma_plugins_load_ha")

        nailgun_nodes = self.fuel_web.get_nailgun_cluster_nodes_by_roles(
            self.helpers.cluster_id, self.settings.stacklight_roles)
        devops_nodes = self.fuel_web.get_devops_nodes_by_nailgun_nodes(
            nailgun_nodes)

        with self.fuel_web.get_ssh_for_node(devops_nodes[0].name) as remote:
            self.remote_ops.simulate_network_interrupt_on_node(remote)

        self.wait_plugin_online()
        self.helpers.run_ostf()

    @test(depends_on_groups=["prepare_lma_plugins_load_ha"],
          groups=["simulate_network_interruption"])
    @log_snapshot_after_test
    def simulate_network_interruption(self):
        """Verify that all services work correctly with workload.

        Scenario:
            1. Revert snapshot with 9 deployed nodes in HA configuration
            2. Simulate network interruption in the whole cluster
            3. Wait for at least 7 minutes before recover network availability
            4. Recover network availability
            5. Wait while all services are started
            6. Run OSTF
            7. Check that plugin is working
            8. Check that data continues to be pushed by the various nodes
               once the network interruption has ended

        Duration 40m
        """

        self.env.revert_snapshot("prepare_lma_plugins_load_ha")

        self.helpers.emulate_whole_network_disaster(
            delay_before_recover=7 * 60)

        self.wait_plugin_online()

        self.check_plugin_online()

        self.helpers.run_ostf(should_fail=1)

    @test(depends_on_groups=["prepare_lma_plugins_load_ha"],
          groups=["restart_services_during_workload"])
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
            7. Stop lma_collector (heka) via “pcs resource disable
               lma_collector”.
            8. Wait while pcs report that lma_collector (heka) stopped on
               all controllers.
            9. Check PID of hekad on all controllers. If hekad PID
               exist - test failed.
            10. Start lma_collector (heka) via “pcs resource enable
                lma_collector”.
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
            20. Kill heka process with “kill -9” command on controller node.
            21. Wait while pacemaker starts heka process on this controller.
            22. Repeat previous 2 steps for all controller nodes.

        Duration 90m
        """

        self.env.revert_snapshot("prepare_lma_plugins_load_ha")

        cluster_id = self.helpers.cluster_id
        queue = multiprocessing.Queue()
        from django.db import connection
        connection.close()
        process_list = []
        process_list.append(multiprocessing.Process(
            target=self.create_load, args=(queue, cluster_id)))
        process_list.append(multiprocessing.Process(
            target=self.restart_services_actions, args=(queue, cluster_id)))

        process_list[0].start()
        if not queue.get(timeout=60 * 5):
            raise AssertionError(
                "Failed to get 'True' from create_load method")
        process_list[1].start()
        while(queue.empty()):
            time.sleep(1)
        for process in process_list:
            process.terminate()
        if not queue.get():
            raise AssertionError("Test returned false. Process {0}"
                                 " had crashed!".format(queue.get()))
