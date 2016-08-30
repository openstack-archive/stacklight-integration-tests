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
DOWN_STATUS = 3

WARNING_PERCENT = 91
CRITICAL_PERCENT = 96


@test(groups=["plugins"])
class TestToolchainAlarms(api.ToolchainApi):
    """Class for testing built-in StackLight Collector alarms.
    """

    def _check_filesystem_alarms(self, nailgun_node, filesystem, entity,
                                 source, filename):
        self.check_alarms('node', entity, source, nailgun_node["hostname"],
                          OKAY_STATUS)
        with self.fuel_web.get_ssh_for_nailgun_node(nailgun_node) as remote:
            self.remote_ops.fill_up_filesystem(
                remote, filesystem, WARNING_PERCENT, filename)
            logger.info("Checking {}-warning alarm".format(source))
            self.check_alarms('node', entity, source,
                              nailgun_node["hostname"], WARNING_STATUS)
            self.remote_ops.clean_filesystem(remote, filename)
            self.check_alarms('node', entity, source,
                              nailgun_node["hostname"], OKAY_STATUS)
            self.remote_ops.fill_up_filesystem(
                remote, filesystem, CRITICAL_PERCENT, filename)
            logger.info("Checking {}-critical alarm".format(source))
            self.check_alarms('node', entity, source,
                              nailgun_node["hostname"], CRITICAL_STATUS)
            self.remote_ops.clean_filesystem(remote, filename)
            self.check_alarms('node', entity, source,
                              nailgun_node["hostname"], OKAY_STATUS)

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

    @test(depends_on_groups=["deploy_ha_toolchain"],
          groups=["check_rabbitmq_pacemaker_alarms", "toolchain", "alarms"])
    @log_snapshot_after_test
    def check_rabbitmq_pacemaker_alarms(self):
        """Check that rabbitmq-pacemaker-* alarms work as expected.

        Scenario:
            1. Stop one RabbitMQ instance.
            2. Check that the status of the RabbitMQ cluster is warning.
            3. Stop a second RabbitMQ instance.
            4. Check that the status of the RabbitMQ cluster is critical.
            5. Stop a third RabbitMQ instance.
            6. Check that the status of the RabbitMQ cluster is down.
            7. Restart all RabbitMQ instances.
            8. Check that the status of the RabbitMQ cluster is okay.

        Duration 10m
        """
        def ban_and_check_status(node, status):
            with self.fuel_web.get_ssh_for_nailgun_node(node) as remote:
                self.remote_ops.ban_resource(remote,
                                             'master_p_rabbitmq-server',
                                             wait=120)
            self.check_alarms('service', 'rabbitmq-cluster', 'pacemaker',
                              None, status)

        self.env.revert_snapshot("deploy_ha_toolchain")

        self.check_alarms('service', 'rabbitmq-cluster', 'pacemaker',
                          None, OKAY_STATUS)

        controllers = self.fuel_web.get_nailgun_cluster_nodes_by_roles(
            self.helpers.cluster_id, ["controller"])

        ban_and_check_status(controllers[0], WARNING_STATUS)
        ban_and_check_status(controllers[1], CRITICAL_STATUS)
        ban_and_check_status(controllers[2], DOWN_STATUS)

        self.remote_ops.clear_resource(controllers[0],
                                       'master_p_rabbitmq-server',
                                       wait=240)
        self.check_alarms('service', 'rabbitmq-cluster', 'pacemaker',
                          None, OKAY_STATUS)
