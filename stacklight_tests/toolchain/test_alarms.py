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

from stacklight_tests.toolchain import api

OKAY_STATUS = 0
WARNING_STATUS = 1
CRITICAL_STATUS = 3


@test(groups=["plugins"])
class TestToolchainAlarms(api.ToolchainApi):
    """Class for testing built-in StackLight Collector alarms.
    """

    @test(depends_on_groups=["deploy_toolchain"],
          groups=["check_mysql_fs_warning_alarm", "toolchain", "alarms"])
    @log_snapshot_after_test
    def check_mysql_fs_warning_alarm(self):
        """Check that mysql-fs-warning alarm works as expected.
        Scenario:
            1. Fill up /var/lib/mysql filesystem to 91 percent.
            2. Check the last value of the alarm in InfluxDB.

        Duration 10m
        """
        self.env.revert_snapshot("deploy_toolchain")
        controller = self.fuel_web.get_nailgun_cluster_nodes_by_roles(
            self.helpers.cluster_id, ["controller"])[0]
        self.check_alarms(
            "node", "mysql-fs", controller["hostname"], OKAY_STATUS)
        with self.fuel_web.get_ssh_for_nailgun_node(controller) as remote:
            self.remote_ops.fill_up_filesystem(
                remote, "/dev/mapper/mysql-root", 91,
                "/var/lib/mysql/test/bigfile")
        self.check_alarms(
            "node", "mysql-fs", controller["hostname"], WARNING_STATUS)
        with self.fuel_web.get_ssh_for_nailgun_node(controller) as remote:
            self.remote_ops.clean_filesystem(
                remote, "/var/lib/mysql/test/bigfile")

    @test(depends_on_groups=["deploy_toolchain"],
          groups=["check_mysql_fs_critical_alarm", "toolchain", "alarms"])
    @log_snapshot_after_test
    def check_mysql_fs_critical_alarm(self):
        """Check that mysql-fs-critical alarm works as expected.
        Scenario:
            1. Fill up /var/lib/mysql filesystem to 96 percent.
            2. Check the last value of the alarm in InfluxDB.

        Duration 10m
        """
        self.env.revert_snapshot("deploy_toolchain")
        controller = self.fuel_web.get_nailgun_cluster_nodes_by_roles(
            self.helpers.cluster_id, ["controller"])[0]
        self.check_alarms(
            "node", "mysql-fs", controller["hostname"], OKAY_STATUS)
        with self.fuel_web.get_ssh_for_nailgun_node(controller) as remote:
            self.remote_ops.fill_up_filesystem(
                remote, "/dev/mapper/mysql-root", 96,
                "/var/lib/mysql/test/bigfile")
        self.check_alarms(
            "node", "mysql-fs", controller["hostname"], CRITICAL_STATUS)
        with self.fuel_web.get_ssh_for_nailgun_node(controller) as remote:
            self.remote_ops.clean_filesystem(
                remote, "/var/lib/mysql/test/bigfile")
