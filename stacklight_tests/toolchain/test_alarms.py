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
from proboscis import test

from stacklight_tests.toolchain import api

OKAY_STATUS = 0
WARNING_STATUS = 1
CRITICAL_STATUS = 3
WARNING_PERCENT = 91
CRITICAL_PERCENT = 96
DISK_WARNING_PERCENT = 99.99
DISK_CRITICAL_PERCENT = 100
MEMORY_WARNING_VALUE = 1.01
MEMORY_CRITICAL_VALUE = 1.0001


@test(groups=["plugins"])
class TestToolchainAlarms(api.ToolchainApi):
    """Class for testing built-in StackLight Collector alarms.
    """

    def _check_filesystem_alarms(self, nailgun_node, filesystem, source,
                                 filename, alarm_type="node"):
        self.check_alarms(
            alarm_type, source, nailgun_node["hostname"], OKAY_STATUS)
        with self.fuel_web.get_ssh_for_nailgun_node(nailgun_node) as remote:
            self.remote_ops.fill_up_filesystem(
                remote, filesystem, WARNING_PERCENT, filename)
            logger.info("Checking {}-warning alarm".format(source))
            self.check_alarms(
                alarm_type, source, nailgun_node["hostname"], WARNING_STATUS)
            self.remote_ops.clean_filesystem(remote, filename)
            self.check_alarms(
                alarm_type, source, nailgun_node["hostname"], OKAY_STATUS)
            self.remote_ops.fill_up_filesystem(
                remote, filesystem, CRITICAL_PERCENT, filename)
            logger.info("Checking {}-critical alarm".format(source))
            self.check_alarms(
                alarm_type, source, nailgun_node["hostname"], CRITICAL_STATUS)
            self.remote_ops.clean_filesystem(remote, filename)
            self.check_alarms(
                alarm_type, source, nailgun_node["hostname"], OKAY_STATUS)
            
    def _check_rabbit_mq_alarms(self, controller, alarm_type, source):
        cmd = ("rabbitmqctl set_disk_free_limit $(df | grep /dev/dm-4 | "
               "awk '{{ printf(\"%.0f\\n\", 1024 * ((($3 + $4) * "
               "{percent} / 100) - $3))}}')")
        self.check_alarms(alarm_type, source, controller["hostname"],
                          OKAY_STATUS)
        with self.fuel_web.get_ssh_for_nailgun_node(controller) as remote:
            default_value = remote.check_call(
                "rabbitmqctl environment | grep disk_free_limit | "
                "sed -r 's/}.+//' | sed 's|.*,||'")['stdout'][0].rstrip()
            remote.check_call(cmd.format(percent=DISK_WARNING_PERCENT))
            self.check_alarms(alarm_type, source, controller["hostname"],
                              WARNING_STATUS)
            remote.check_call(cmd.format(percent=DISK_CRITICAL_PERCENT))
            self.check_alarms(alarm_type, source, controller["hostname"],
                              CRITICAL_STATUS)
            remote.check_call("rabbitmqctl set_disk_free_limit {}".format(
                default_value))
            self.check_alarms(alarm_type, source, controller["hostname"],
                              OKAY_STATUS)

    def _check_rabbit_mq_memory_alarms(self, controller, alarm_type, source):
        cmd = "rabbitmqctl set_vm_memory_high_watermark absolute \"{memory}\""
        self.check_alarms(alarm_type, source, controller["hostname"],
                          OKAY_STATUS)
        with self.fuel_web.get_ssh_for_nailgun_node(controller) as remote:
            default_value = remote.check_call(
                "rabbitmqctl environment | grep disk_free_limit | "
                "sed -r 's/}.+//' | sed 's|.*,||'")['stdout'][0].rstrip()
            mem_usage = self.get_rabbitmq_memory_usage()
            remote.check_call(cmd.format(memory=int(mem_usage * 1.01)))
            self.check_alarms(alarm_type, source, controller["hostname"],
                              WARNING_STATUS)
            mem_usage = self.get_rabbitmq_memory_usage()
            remote.check_call(cmd.format(memory=int(mem_usage * 1.0001)))
            self.check_alarms(alarm_type, source, controller["hostname"],
                              CRITICAL_STATUS)
            self.try_set_memory_limit(controller, default_value)
            self.check_alarms(alarm_type, source, controller["hostname"],
                              OKAY_STATUS)
            
    @test(depends_on_groups=["deploy_toolchain"],
          groups=["check_mysql_fs_alarms", "toolchain", "alarms"])
    @log_snapshot_after_test
    def check_mysql_fs_alarms(self):
        """Check that mysql-fs-warning and mysql-fs-critical alarms work as
        expected.

        Scenario:
            1. Fill up /var/lib/mysql filesystem to 91 percent.
            2. Check the last value of the warning alarm in InfluxDB.
            3. Clean the filesystem.
            4. Fill up /var/lib/mysql filesystem to 96 percent.
            5. Check the last value of the critical alarm in InfluxDB.
            6. Clean the filesystem.

        Duration 10m
        """
        self.env.revert_snapshot("deploy_toolchain")
        controller = self.fuel_web.get_nailgun_cluster_nodes_by_roles(
            self.helpers.cluster_id, ["controller"])[0]
        self._check_filesystem_alarms(
            controller, "/dev/mapper/mysql-root", "mysql-fs",
            "/var/lib/mysql/test/bigfile")

    @test(depends_on_groups=["deploy_toolchain"],
          groups=["check_rabbitmq_disk_limit_alarm", "toolchain", "alarms"])
    @log_snapshot_after_test
    def check_rabbitmq_disk_limit_alarm(self):
        """Check that rabbitmq-disk-limit-warning and
        rabbitmq-disk-limit-critical alarms work as expected.

        Scenario:
            1. Check the last value of the okay alarm in InfluxDB.
            2. Set RabbitMQ disk limit to 99.99 percent of available space.
            3. Check the last value of the warning alarm in InfluxDB.
            4. Set RabbitMQ disk limit to 100 percent of available space.
            5. Check the last value of the critical alarm in InfluxDB.
            6. Set RabbitMQ disk limit to the default value.
            7. Check the last value of the okay alarm in InfluxDB.

        Duration 10m
        """
        self.env.revert_snapshot("deploy_toolchain")
        controller = self.fuel_web.get_nailgun_cluster_nodes_by_roles(
            self.helpers.cluster_id, ["controller"])[0]
        self._check_rabbit_mq_alarms(controller, "service", "disk")

    @test(depends_on_groups=["deploy_toolchain"],
          groups=["check_rabbitmq_memory_watermark_alarm", "toolchain",
                  "alarms"])
    @log_snapshot_after_test
    def check_rabbitmq_memory_watermark_alarm(self):
        """Check that rabbitmq-memory-limit-warning and
        rabbitmq-memory-limit-critical alarms work as expected.

        Scenario:
            1. Check the last value of the okay alarm in InfluxDB.
            2. Set RabbitMQ memory limit to 101 percent of currently
            used memory.
            3. Check the last value of the warning alarm in InfluxDB.
            4. Set RabbitMQ memory limit to 100.01 percent of currently
            used memory.
            5. Check the last value of the critical alarm in InfluxDB.
            6. Set RabbitMQ memory limit to the default value.
            7. Check the last value of the okay alarm in InfluxDB.

        Duration 10m
        """
        self.env.revert_snapshot("deploy_toolchain")
        controller = self.fuel_web.get_nailgun_cluster_nodes_by_roles(
            self.helpers.cluster_id, ["controller"])[0]

        self._check_rabbit_mq_memory_alarms(controller, "service", "memory")

