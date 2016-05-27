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
import copy
import multiprocessing
import os
import time
from proboscis import asserts
from proboscis import test

from fuelweb_test.helpers.decorators import log_snapshot_after_test
from fuelweb_test import logger
from fuelweb_test import settings
from fuelweb_test.helpers.rally import RallyBenchmarkTest
from fuelweb_test.tests.base_test_case import TestBasic
import traceback

from stacklight_tests.toolchain import api

from devops.helpers import helpers as devops_helpers
from subprocess import call
from fuelweb_test.tests import base_test_case

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
    # @log_snapshot_after_test
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

#TODO: Doesn't work right! Fix!
        self.helpers.emulate_whole_network_disaster(
            delay_before_recover=7 * 60)

        self.wait_plugin_online()

        self.check_plugin_online()

        self.helpers.run_ostf(should_fail=1)

    @test(depends_on_groups=["prepare_lma_plugins_load_ha"],
        groups=["restart_services_during_workload"])
    # @log_snapshot_after_test
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
        logger.info("Creating close to production load")
        queue = multiprocessing.Queue()
        from django.db import connection
        connection.close()
        process_list = []
        process_list.append(multiprocessing.Process(target=self.create_load, args=(queue,cluster_id)))
        process_list.append(multiprocessing.Process(target=self.restart_services_actions, args=(queue,cluster_id)))

        process_list[0].start()
        if not queue.get(timeout=60 * 5):
            raise AssertionError("Failed to get 'True' from create_load method")
        process_list[1].start()
        while(queue.empty()):
            time.sleep(1)
        for process in process_list:
            process.terminate()


    def restart_services_actions(self, queue, cluster_id):
        test = base_test_case.TestBasic()
        env = test.env
        fuel_web = env.fuel_web
        try:
            logger.info("Moving vip__management service to another node")
            nailgun_controllers = fuel_web.get_nailgun_cluster_nodes_by_roles(
                cluster_id, ['controller'])
            devops_nodes = fuel_web.get_devops_nodes_by_nailgun_nodes(
                nailgun_controllers)
            service_node = fuel_web.get_pacemaker_resource_location(
                devops_nodes[1].name, "vip__management")[0]

            for node in nailgun_controllers:
                if node['name'] == service_node.name + "_controller_ceph-osd":
                    nailgun_controllers.remove(node)

            self.move_resource(fuel_web, nailgun_controllers[0], "vip__management", nailgun_controllers[0])

            self.monitoring_check()

            # time.sleep(3600)

            self.move_resource(fuel_web, nailgun_controllers[1], "vip__management", nailgun_controllers[1])

            self.monitoring_check()

            nailgun_controllers = fuel_web.get_nailgun_cluster_nodes_by_roles(
                 cluster_id, ['controller'])

            pids = self.get_tasks_pids(fuel_web, ['hekad', 'collectd'])

            self.manage_pcs_resource(fuel_web, nailgun_controllers, "lma_collector",
                                     "disable", "Stopped")
            self.get_tasks_pids(fuel_web, ['hekad'], devops_nodes, 1)
            self.manage_pcs_resource(fuel_web, nailgun_controllers, "lma_collector",
                                     "enable", "Started")
            self.monitoring_check()

            nailgun_compute = fuel_web.get_nailgun_cluster_nodes_by_roles(
                cluster_id, ['compute'])
            nailgun_plugins = fuel_web.get_nailgun_cluster_nodes_by_roles(
                cluster_id, self.settings.stacklight_roles)

            self.manage_lma_collector_service(fuel_web, nailgun_compute, "restart")
            self.manage_lma_collector_service(fuel_web, nailgun_plugins, "restart")

            new_pids = self.get_tasks_pids(fuel_web, ['hekad'])

            for node in new_pids:
                asserts.assert_true(new_pids[node]["hekad"] != pids[node]["hekad"],
                                    "hekad on {0} hasn't changed it's pid! Was {1} "
                                    "now {2}".format(node, pids[node]["hekad"],
                                                     new_pids[node]["hekad"]))
            self.monitoring_check()

            self.manage_lma_collector_service(fuel_web, nailgun_compute, "stop")
            self.manage_lma_collector_service(fuel_web, nailgun_plugins, "stop")
            #TODO: SHOULD BE REPLACED WITH NAILGUN NODES!
            devops_computes = fuel_web.get_devops_nodes_by_nailgun_nodes(
                nailgun_compute)
            devops_plugins = fuel_web.get_devops_nodes_by_nailgun_nodes(
                nailgun_plugins)
            self.get_tasks_pids(fuel_web, ['hekad'], devops_computes, 1)
            self.get_tasks_pids(fuel_web, ['hekad'], devops_plugins, 1)
            self.manage_lma_collector_service(fuel_web, nailgun_compute, "start")
            self.manage_lma_collector_service(fuel_web, nailgun_plugins, "start")
            self.monitoring_check()

            msg = "hekad has not been restarted by pacemaker on node {0} after" \
                  " kill -9"
            for node in nailgun_controllers:
                with fuel_web.get_ssh_for_nailgun_node(node) as remote:
                    def wait_for_restart():
                        if remote.execute("pidof hekad")["exit_code"]:
                            return False
                        else:
                            return True
                    exec_res = remote.execute("kill -9 `pidof hekad`")
                    asserts.assert_equal(0, exec_res['exit_code'],
                                         "Failed to kill -9 hekad on"
                                         " {0}".format(node["name"]))
                    devops_helpers.wait(wait_for_restart,
                                        timeout=60 * 5,
                                        timeout_msg=msg.format(node["name"]))
            queue.put(True)
        except Exception as ex:
            logger.error(ex)
            queue.put(False)

#TODO: Move these methods into the 'api' class!

    def manage_lma_collector_service(self, fuel_web, nodes, action):
        for node in nodes:
            with fuel_web.get_ssh_for_nailgun_node(node) as remote:
                exec_res = remote.execute("{0} lma_collector".format(action))
                asserts.assert_equal(0, exec_res['exit_code'],
                                     "Failed to {0} lma_collector on"
                                     " {1}".format(action, node["name"]))

    def manage_pcs_resource(self, fuel_web, nodes, resource, action, check):
        def check_state():
            grep = "grep {0} | grep {1} | grep {2}".format(
                nodes[0]["hostname"], nodes[1]["hostname"],
                nodes[2]["hostname"])
            with fuel_web.get_ssh_for_nailgun_node(nodes[0]) as remote:
                result = remote.execute(
                    "pcs status | grep {0} | {1}".format(check, grep))
                if not result['exit_code']:
                    return True
                else:
                    return False
        with fuel_web.get_ssh_for_nailgun_node(nodes[0]) as remote:
            exec_res = remote.execute("pcs resource {0} {1}".format(
                action, resource))
            asserts.assert_equal(0, exec_res['exit_code'],
                                 "Failed to {0} resource {1} on {2}".format(
                                     action, resource, nodes[0]["name"]))

        msg = "Failed to stop {0} on all nodes!".format(resource)
        devops_helpers.wait(check_state, timeout=5*60, timeout_msg=msg)

    def get_tasks_pids(self, fuel_web, processes, nodes=None, exit_code=0):
        nodes = nodes or [node for node in self.env.d_env.get_nodes()
                 if node.name != "admin"]
        pids = {}
        for node in nodes:
            with fuel_web.get_ssh_for_node(node.name) as remote:
                pids[node.name] = {}
                for process in processes:
                    result = remote.execute("pidof {0} ".format(process))
                    if exit_code:
                        asserts.assert_equal(exit_code, result['exit_code'],
                                             "process {0} is running on "
                                             "{1}".format(process, node.name))
                    else:
                        pids[node.name][process] = result['stdout'][0].rstrip()

        return pids

    def move_resource(self, fuel_web, node, resource_name, move_to):
        with fuel_web.get_ssh_for_nailgun_node(node) as remote:
            exec_res = remote.execute("pcs resource move {0} {1}".format(
                resource_name, move_to["fqdn"]))
            asserts.assert_equal(0, exec_res['exit_code'],
                                 "Failed to move resource {0} to {1}".format(
                                     resource_name, move_to["fqdn"]))

    def monitoring_check(self):
        logger.info("Checking that lma_collector (heka) sending data to"
                    " Elasticsearch, InfluxDB, Nagios.")
        try:
            self.elasticsearch_monitoring_check()
            self.influxdb_monitoring_check()
            self.lma_infrastructure_alerting_monitoring_check()
        except Exception as ex:
            logger.error(ex)
            logger.error(traceback.print_exc())


    def create_load(self, queue, cluster_id):
        send_flag = True
        workspace = ""
        if "WORKSPACE" in os.environ.keys():
            workspace = os.environ["WORKSPACE"]
        os.environ["WORKSPACE"] = "/home/vushakov/stacklight-integration-tests/utils/fuel-qa-builder/venv-stacklight-tests/lib/python2.7/site-packages"

        test = base_test_case.TestBasic()
        env = test.env
        fuel_web = env.fuel_web
        try:
            while(True):
                files = self.fill_ceph(fuel_web, cluster_id)
                fuel_web.check_ceph_status(1)
                if send_flag:
                    queue.put(True)
                    send_flag = False
                self.run_rally_benchmark(env, cluster_id)
                self.clean_ceph(fuel_web, files, cluster_id)
        except Exception as ex:
            logger.error(ex)
            queue.put(False)
        finally:
            os.environ["WORKSPACE"] = workspace

    def fill_ceph(self, fuel_web, cluster_id):
        ceph_nodes = fuel_web.get_nailgun_cluster_nodes_by_roles(
            cluster_id, ['ceph-osd'])
        files = {}
        for node in ceph_nodes:
            with fuel_web.get_ssh_for_nailgun_node(node) as remote:
                file_name = "test_data"
                file_dir = remote.execute(
                    'mount | grep -m 1 ceph')['stdout'][0].split()[2]
                file_path = os.path.join(file_dir, file_name)
                files[node["name"]] = file_path
                result = remote.execute(
                    'fallocate -l 30G {0}'.format(file_path))['exit_code']
                asserts.assert_equal(result, 0, "The file {0} was not "
                                     "allocated".format(file_name))
        return files

    def clean_ceph(self, fuel_web, files, cluster_id):
        ceph_nodes = fuel_web.get_nailgun_cluster_nodes_by_roles(
            cluster_id, ['ceph-osd'])
        for node in ceph_nodes:
            with fuel_web.get_ssh_for_nailgun_node(node) as remote:
                result = remote.execute(
                    'rm -f {0}'.format(files[node["name"]]))['exit_code']
                asserts.assert_equal(result, 0, "The file {0} was not "
                                     "removed".format(files[node["name"]]))

    def run_rally_benchmark(self, env, cluster_id):
        settings.PATCHING_RUN_RALLY = True
        asserts.assert_true(settings.PATCHING_RUN_RALLY,
                    'PATCHING_RUN_RALLY was not set in true')
        rally_benchmarks = {}
        benchmark_results = {}
        for tag in set(settings.RALLY_TAGS):
            rally_benchmarks[tag] = RallyBenchmarkTest(
                container_repo=settings.RALLY_DOCKER_REPO,
                environment=env,
                cluster_id=cluster_id,
                test_type=tag
            )
            benchmark_results[tag] = rally_benchmarks[tag].run()
            logger.debug(benchmark_results[tag].show())