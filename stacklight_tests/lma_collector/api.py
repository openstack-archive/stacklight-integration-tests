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

from fuelweb_test import logger

from stacklight_tests import base_test
from stacklight_tests.lma_collector import plugin_settings


class LMACollectorPluginApi(base_test.PluginApi):
    def get_plugin_settings(self):
        return plugin_settings

    def prepare_plugin(self):
        self.helpers.prepare_plugin(self.settings.plugin_path)

    def activate_plugin(self, options=None):
        if options is None:
            options = self.settings.default_options
        self.helpers.activate_plugin(
            self.settings.name, self.settings.version, options)

    def verify_services(self):
        """Check that the correct amount of collector processes are running.

        :returns: list of process IDs indexed by node and process
        :rtype: dict
        """
        services = ["metric_collector", "log_collector"]
        service_version_9 = ["lma_collector"]
        pgrep = {}
        processes_count = {
            "collectd ": 1,
            "collectdmon ": 1
        }

        if self.settings.version.startswith("0.9"):
            processes_count[
                "hekad -config[= ]/etc/{}".format(service_version_9)] = 1
        else:
            # Starting with 0.10, there are one collector for logs and one for
            # metrics
            for service in services:
                processes_count["hekad -config[= ]/etc/{}".format(service)] = 1
        online_nodes = [node for node in self.helpers.get_all_ready_nodes()
                        if node["online"]]
        for node in online_nodes:
            pgrep[node["name"]] = {}
            with self.env.d_env.get_ssh_to_remote(node["ip"]) as remote:
                for process, count in processes_count.items():
                    logger.info("Checking process {0} on node {1}".format(
                        process, node["name"]
                    ))
                    pgrep[node["name"]][process] = (
                        self.checkers.check_process_count(
                            remote, process, count))
        return pgrep

    def check_plugin_online(self):
        # Run the OSTF tests to check the Pacemaker status except when no
        # controller are being deployed (dedicated environment case)
        controllers = self.fuel_web.get_nailgun_cluster_nodes_by_roles(
            self.helpers.cluster_id, ["controller"])
        if len(controllers) > 0:
            self.helpers.run_single_ostf(
                test_sets=['ha'],
                test_name='fuel_health.tests.ha.test_pacemaker_status.'
                          'TestPacemakerStatus.test_check_pacemaker_resources')

        self.verify_services()

    def uninstall_plugin(self):
        return self.helpers.uninstall_plugin(self.settings.name,
                                             self.settings.version)

    def check_uninstall_failure(self):
        return self.helpers.check_plugin_cannot_be_uninstalled(
            self.settings.name, self.settings.version)
