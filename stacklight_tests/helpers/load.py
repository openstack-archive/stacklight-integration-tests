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

import os

from fuelweb_test import logger
from fuelweb_test import settings
from fuelweb_test.helpers.rally import RallyBenchmarkTest
from fuelweb_test.tests import base_test_case

from proboscis import asserts

class CreateLoad(object):
    """Class for load creation functions."""

    def create_load(self, queue, cluster_id):
        logger.info("Creating close to production load")
        send_flag = True
        workspace = ""
        if "WORKSPACE" in os.environ.keys():
            workspace = os.environ["WORKSPACE"]
        base_path = base_test_case.__file__.split("site-packages")[0]
        os.environ["WORKSPACE"] = base_path + "/site-packages"

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
            queue.put(os.getpid())
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
