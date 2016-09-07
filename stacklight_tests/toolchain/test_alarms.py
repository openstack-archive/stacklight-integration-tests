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
UNKNOWN_STATUS = 2
CRITICAL_STATUS = 3
DOWN_STATUS = 4

WARNING_PERCENT = 91
CRITICAL_PERCENT = 96

RABBITMQ_DISK_WARNING_PERCENT = 99.99
RABBITMQ_DISK_CRITICAL_PERCENT = 100
RABBITMQ_MEMORY_WARNING_VALUE = 1.01
RABBITMQ_MEMORY_CRITICAL_VALUE = 1.0001


@test(groups=["plugins"])
class TestToolchainAlarms(api.ToolchainApi):
    """Class for testing built-in StackLight Collector alarms.
    """

    def _check_filesystem_alarms(self, nailgun_node, filesystem, source,
                                 filename, node_role, alarm_type="node"):
        self.check_alarms(alarm_type, node_role, source,
                          nailgun_node["hostname"], OKAY_STATUS)
        with self.fuel_web.get_ssh_for_nailgun_node(nailgun_node) as remote:
            self.remote_ops.fill_up_filesystem(
                remote, filesystem, WARNING_PERCENT, filename)
            logger.info("Checking {}-warning alarm".format(source))
            self.check_alarms(alarm_type, node_role, source,
                              nailgun_node["hostname"], WARNING_STATUS)
            self.remote_ops.clean_filesystem(remote, filename)
            self.check_alarms(alarm_type, node_role,
                              source, nailgun_node["hostname"], OKAY_STATUS)
            self.remote_ops.fill_up_filesystem(
                remote, filesystem, CRITICAL_PERCENT, filename)
            logger.info("Checking {}-critical alarm".format(source))
            self.check_alarms(alarm_type, node_role, source,
                              nailgun_node["hostname"], CRITICAL_STATUS)
            self.remote_ops.clean_filesystem(remote, filename)
            self.check_alarms(alarm_type, node_role, source,
                              nailgun_node["hostname"], OKAY_STATUS)

    def _check_rabbit_mq_disk_alarms(self, controller, status, percent):
        cmd = ("rabbitmqctl set_disk_free_limit $(df | grep /dev/dm-4 | "
               "awk '{{ printf(\"%.0f\\n\", 1024 * ((($3 + $4) * "
               "{percent} / 100) - $3))}}')")
        self.check_alarms("service", "rabbitmq", "disk",
                          controller["hostname"], OKAY_STATUS)
        with self.fuel_web.get_ssh_for_nailgun_node(controller) as remote:
            default_value = remote.check_call(
                "rabbitmqctl environment | grep disk_free_limit | "
                "sed -r 's/}.+//' | sed 's|.*,||'")['stdout'][0].rstrip()
            remote.check_call(cmd.format(percent=percent))
            self.check_alarms("service", "rabbitmq", "disk",
                              controller["hostname"], status)
            remote.check_call("rabbitmqctl set_disk_free_limit {}".format(
                default_value))
            self.check_alarms("service", "rabbitmq", "disk",
                              controller["hostname"], OKAY_STATUS)

    def _check_rabbit_mq_memory_alarms(self, controller, status, value):
        cmd = "rabbitmqctl set_vm_memory_high_watermark absolute \"{memory}\""
        self.check_alarms("service", "rabbitmq", "memory",
                          controller["hostname"], OKAY_STATUS)
        with self.fuel_web.get_ssh_for_nailgun_node(controller) as remote:
            default_value = remote.check_call(
                "rabbitmqctl environment | grep disk_free_limit | "
                "sed -r 's/}.+//' | sed 's|.*,||'")['stdout'][0].rstrip()
            mem_usage = self.get_rabbitmq_memory_usage()
            remote.check_call(cmd.format(memory=int(mem_usage * value)))
            self.check_alarms("service", "rabbitmq", "memory",
                              controller["hostname"], status)
            self.set_rabbitmq_memory_watermark(controller, default_value)
            self.check_alarms("service", "rabbitmq", "memory",
                              controller["hostname"], OKAY_STATUS)

    def _check_http_logs_errors_alarms(self, provocation_fn, provocation_count,
                                       metrics, status=WARNING_STATUS):
        for _ in range(provocation_count):
            provocation_fn()
        for service, source in metrics.items():
            self.check_alarms("service", service, source, None, status)

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
            "/var/lib/mysql/test/bigfile", "mysql-nodes")

    @test(depends_on_groups=["deploy_toolchain"],
          groups=["check_rabbitmq_disk_alarm", "toolchain", "alarms"])
    @log_snapshot_after_test
    def check_rabbitmq_disk_alarm(self):
        """Check that rabbitmq-disk-limit-warning and
        rabbitmq-disk-limit-critical alarms work as expected.

        Scenario:
            1. Check the last value of the okay alarm in InfluxDB.
            2. Set RabbitMQ disk limit to 99.99 percent of available space.
            3. Check the last value of the warning alarm in InfluxDB.
            4. Set RabbitMQ disk limit to the default value.
            5. Check the last value of the okay alarm in InfluxDB.
            6. Set RabbitMQ disk limit to 100 percent of available space.
            7. Check the last value of the critical alarm in InfluxDB.
            8. Set RabbitMQ disk limit to the default value.
            9. Check the last value of the okay alarm in InfluxDB.

        Duration 10m
        """
        self.env.revert_snapshot("deploy_toolchain")
        controller = self.fuel_web.get_nailgun_cluster_nodes_by_roles(
            self.helpers.cluster_id, ["controller"])[0]
        self._check_rabbit_mq_disk_alarms(controller, WARNING_STATUS,
                                          RABBITMQ_DISK_WARNING_PERCENT)
        self._check_rabbit_mq_disk_alarms(controller, CRITICAL_STATUS,
                                          RABBITMQ_DISK_CRITICAL_PERCENT)

    @test(depends_on_groups=["deploy_toolchain"],
          groups=["check_rabbitmq_memory_alarm", "toolchain",
                  "alarms"])
    @log_snapshot_after_test
    def check_rabbitmq_memory_alarm(self):
        """Check that rabbitmq-memory-limit-warning and
        rabbitmq-memory-limit-critical alarms work as expected.

        Scenario:
            1. Check the last value of the okay alarm in InfluxDB.
            2. Set RabbitMQ memory limit to 101 percent of currently
            used memory.
            3. Check the last value of the warning alarm in InfluxDB.
            4. Set RabbitMQ memory limit to the default value.
            5. Check the last value of the okay alarm in InfluxDB.
            6. Set RabbitMQ memory limit to 100.01 percent of currently
            used memory.
            7. Check the last value of the critical alarm in InfluxDB.
            8. Set RabbitMQ memory limit to the default value.
            9. Check the last value of the okay alarm in InfluxDB.

        Duration 10m
        """
        self.env.revert_snapshot("deploy_toolchain")
        controller = self.fuel_web.get_nailgun_cluster_nodes_by_roles(
            self.helpers.cluster_id, ["controller"])[0]
        self._check_rabbit_mq_memory_alarms(controller, WARNING_STATUS,
                                            RABBITMQ_MEMORY_WARNING_VALUE)
        self._check_rabbit_mq_memory_alarms(controller, CRITICAL_STATUS,
                                            RABBITMQ_MEMORY_CRITICAL_VALUE)

    @test(depends_on_groups=["deploy_ha_toolchain"],
          groups=["check_rabbitmq_pacemaker_alarms", "toolchain", "alarms"])
    @log_snapshot_after_test
    def check_rabbitmq_pacemaker_alarms(self):
        """Check that rabbitmq-pacemaker-* alarms work as expected.

        Scenario:
            1. Stop one slave RabbitMQ instance.
            2. Check that the status of the RabbitMQ cluster is warning.
            3. Stop the second slave RabbitMQ instance.
            4. Check that the status of the RabbitMQ cluster is critical.
            5. Stop the master RabbitMQ instance.
            6. Check that the status of the RabbitMQ cluster is down.
            7. Clear the RabbitMQ resource.
            8. Check that the status of the RabbitMQ cluster is okay.

        Duration 10m
        """
        def ban_and_check_status(node, status, wait=None):
            with self.fuel_web.get_ssh_for_node(node.name) as remote:
                logger.info("Ban rabbitmq resource on {}".format(node.name))
                self.remote_ops.ban_resource(remote,
                                             'master_p_rabbitmq-server',
                                             wait=wait)
            self.check_alarms('service', 'rabbitmq-cluster', 'pacemaker',
                              None, status)

        self.env.revert_snapshot("deploy_ha_toolchain")

        self.check_alarms('service', 'rabbitmq-cluster', 'pacemaker',
                          None, OKAY_STATUS)

        controllers = self.fuel_web.get_nailgun_cluster_nodes_by_roles(
            self.helpers.cluster_id, ["controller"])

        controller = controllers[0]
        controller_node = self.fuel_web.get_devops_node_by_nailgun_node(
            controller)
        rabbitmq_master = self.fuel_web.get_rabbit_master_node(
            controller_node.name)
        rabbitmq_slaves = self.fuel_web.get_rabbit_slaves_node(
            controller_node.name)
        ban_and_check_status(rabbitmq_slaves[0], WARNING_STATUS, 120)
        ban_and_check_status(rabbitmq_slaves[1], CRITICAL_STATUS, 120)
        # Don't wait for the pcs operation to complete as it will fail since
        # the resource isn't running anywhere
        ban_and_check_status(rabbitmq_master, DOWN_STATUS)

        logger.info("Clear rabbitmq resource")
        with self.fuel_web.get_ssh_for_node(rabbitmq_master.name) as remote:
            self.remote_ops.clear_resource(remote,
                                           'master_p_rabbitmq-server',
                                           wait=240)
        self.check_alarms('service', 'rabbitmq-cluster', 'pacemaker',
                          None, OKAY_STATUS)

    @test(depends_on_groups=["deploy_toolchain"],
          groups=["check_root_fs_alarms", "toolchain", "alarms"])
    @log_snapshot_after_test
    def check_root_fs_alarms(self):
        """Check that root-fs-warning and root-fs-critical alarms work as
        expected.

        Scenario:
            1. Fill up root filesystem to 91 percent.
            2. Check the last value of the warning alarm in InfluxDB.
            3. Clean the filesystem.
            4. Fill up root filesystem to 96 percent.
            5. Check the last value of the critical alarm in InfluxDB.
            6. Clean the filesystem.

        Duration 10m
        """
        self.env.revert_snapshot("deploy_toolchain")
        controller = self.fuel_web.get_nailgun_cluster_nodes_by_roles(
            self.helpers.cluster_id, ["controller"])[0]
        self._check_filesystem_alarms(
            controller, "/$", "root-fs", "/bigfile", "controller")

    @test(depends_on_groups=["deploy_toolchain"],
          groups=["check_log_fs_alarms", "toolchain", "alarms"])
    @log_snapshot_after_test
    def check_log_fs_alarms(self):
        """Check that log-fs-warning and log-fs-critical alarms work as
        expected.

        Scenario:
            1. Fill up /var/log filesystem to 91 percent.
            2. Check the last value of the warning alarm in InfluxDB.
            3. Clean the filesystem.
            4. Fill up /var/log filesystem to 96 percent.
            5. Check the last value of the critical alarm in InfluxDB.
            6. Clean the filesystem.

        Duration 10m
        """
        self.env.revert_snapshot("deploy_toolchain")
        controller = self.fuel_web.get_nailgun_cluster_nodes_by_roles(
            self.helpers.cluster_id, ["controller"])[0]
        self._check_filesystem_alarms(
            controller, "/var/log", "log-fs", "/var/log/bigfile", "controller")

    @test(depends_on_groups=["deploy_toolchain"],
          groups=["check_nova_fs_alarms", "toolchain", "alarms"])
    @log_snapshot_after_test
    def check_nova_fs_alarms(self):
        """Check that nova-fs-warning and nova-fs-critical alarms work as
        expected.

        Scenario:
            1. Fill up /var/lib/nova filesystem to 91 percent.
            2. Check the last value of the warning alarm in InfluxDB.
            3. Clean the filesystem.
            4. Fill up /var/lib/nova filesystem to 96 percent.
            5. Check the last value of the critical alarm in InfluxDB.
            6. Clean the filesystem.

        Duration 10m
        """
        self.env.revert_snapshot("deploy_toolchain")
        compute = self.fuel_web.get_nailgun_cluster_nodes_by_roles(
            self.helpers.cluster_id, ["compute"])[0]
        self._check_filesystem_alarms(compute, "/var/lib/nova", "nova-fs",
                                      "/var/lib/nova/bigfile", "compute")

    @test(depends_on_groups=["deploy_toolchain"],
          groups=["check_nova_api_logs_errors_alarms",
                  "http_logs_errors_alarms", "toolchain", "alarms"])
    @log_snapshot_after_test
    def check_nova_api_logs_errors_alarms(self):
        """Check that nova-logs-error and nova-api-http-errors alarms work as
        expected.

        Scenario:
            1. Rename all nova tables to UPPERCASE.
            2. Run some nova-network list command repeatedly.
            3. Check the last value of the nova-logs-error alarm in InfluxDB.
            4. Check the last value of the nova-api-http-errors alarm
               in InfluxDB.
            5. Revert all nova tables names to lowercase.

        Duration 10m
        """
        def get_servers_list():
            try:
                self.helpers.os_conn.get_servers()
            except Exception:
                pass
        self.env.revert_snapshot("deploy_toolchain")

        controllers = self.fuel_web.get_nailgun_cluster_nodes_by_roles(
            self.helpers.cluster_id, ["controller"])

        with self.helpers.make_logical_db_unavailable("nova", controllers):
            metrics = {"nova-logs": "error",
                       "nova-api": "http_errors"}
            self._check_http_logs_errors_alarms(get_servers_list, 100, metrics)

    @test(depends_on_groups=["deploy_toolchain"],
          groups=["check_neutron_api_logs_errors_alarms",
                  "http_logs_errors_alarms", "toolchain", "alarms"])
    @log_snapshot_after_test
    def check_neutron_api_logs_errors_alarms(self):
        """Check that neutron-logs-error and neutron-api-http-errors
        alarms work as expected.

        Scenario:
            1. Rename all neutron tables to UPPERCASE.
            2. Run some neutron agents list command repeatedly.
            3. Check the last value of the neutron-logs-error alarm
               in InfluxDB.
            4. Check the last value of the neutron-api-http-errors alarm
               in InfluxDB.
            5. Revert all neutron tables names to lowercase.

        Duration 10m
        """
        def get_agents_list():
            try:
                self.helpers.os_conn.list_agents()
            except Exception:
                pass

        self.env.revert_snapshot("deploy_toolchain")

        controllers = self.fuel_web.get_nailgun_cluster_nodes_by_roles(
            self.helpers.cluster_id, ["controller"])

        with self.helpers.make_logical_db_unavailable("neutron", controllers):
            metrics = {"neutron-logs": "error",
                       "neutron-api": "http_errors"}
            self._check_http_logs_errors_alarms(get_agents_list, 100, metrics)

    @test(depends_on_groups=["deploy_toolchain"],
          groups=["check_glance_api_logs_errors_alarms",
                  "http_logs_errors_alarms", "toolchain", "alarms"])
    @log_snapshot_after_test
    def check_glance_api_logs_errors_alarms(self):
        """Check that glance-logs-error and glance-api-http-errors alarms work as
        expected.

        Scenario:
            1. Rename all glance tables to UPPERCASE.
            2. Run some glance image list command repeatedly.
            3. Check the last value of the glance-logs-error alarm in InfluxDB.
            4. Check the last value of the glance-api-http-errors alarm
               in InfluxDB.
            5. Revert all glance tables names to lowercase.

        Duration 10m
        """
        def get_images_list():
            try:
                # NOTE(rpromyshlennikov): List is needed here
                # because glance image list is lazy method
                return list(self.helpers.os_conn.get_image_list())
            except Exception:
                pass

        self.env.revert_snapshot("deploy_toolchain")

        controllers = self.fuel_web.get_nailgun_cluster_nodes_by_roles(
            self.helpers.cluster_id, ["controller"])

        with self.helpers.make_logical_db_unavailable("glance", controllers):
            metrics = {"glance-logs": "error",
                       "glance-api": "http_errors"}
            self._check_http_logs_errors_alarms(get_images_list, 100, metrics)

    @test(depends_on_groups=["deploy_toolchain"],
          groups=["check_heat_api_logs_errors_alarms",
                  "http_logs_errors_alarms", "toolchain", "alarms"])
    @log_snapshot_after_test
    def check_heat_api_logs_errors_alarms(self):
        """Check that heat-logs-error and heat-api-http-errors alarms work as
        expected.

        Scenario:
            1. Rename all heat tables to UPPERCASE.
            2. Run some heat stack list command repeatedly.
            3. Check the last value of the heat-logs-error alarm in InfluxDB.
            4. Check the last value of the heat-api-http-errors alarm
               in InfluxDB.
            5. Revert all heat tables names to lowercase.

        Duration 10m
        """
        def get_stacks_list():
            try:
                with self.fuel_web.get_ssh_for_nailgun_node(
                        controllers[0]) as remote:
                    return remote.execute(
                        ". openrc && heat stack-list > /dev/null 2>&1")
            except Exception:
                pass

        self.env.revert_snapshot("deploy_toolchain")

        controllers = self.fuel_web.get_nailgun_cluster_nodes_by_roles(
            self.helpers.cluster_id, ["controller"])

        with self.helpers.make_logical_db_unavailable("heat", controllers):
            metrics = {"heat-logs": "error",
                       "heat-api": "http_errors"}
            self._check_http_logs_errors_alarms(get_stacks_list, 100, metrics)

    @test(depends_on_groups=["deploy_toolchain"],
          groups=["check_cinder_api_logs_errors_alarms",
                  "http_logs_errors_alarms", "toolchain", "alarms"])
    @log_snapshot_after_test
    def check_cinder_api_logs_errors_alarms(self):
        """Check that cinder-logs-error and cinder-api-http-errors alarms work as
        expected.

        Scenario:
            1. Rename all cinder tables to UPPERCASE.
            2. Run some cinder stack list command repeatedly.
            3. Check the last value of the cinder-logs-error alarm in InfluxDB.
            4. Check the last value of the cinder-api-http-errors alarm
               in InfluxDB.
            5. Revert all cinder tables names to lowercase.

        Duration 10m
        """

        def get_volumes_list():
            try:
                self.helpers.os_conn.cinder.volumes.list()
            except Exception:
                pass

        self.env.revert_snapshot("deploy_toolchain")

        controllers = self.fuel_web.get_nailgun_cluster_nodes_by_roles(
            self.helpers.cluster_id, ["controller"])

        with self.helpers.make_logical_db_unavailable("cinder", controllers):
            metrics = {"cinder-logs": "error",
                       "cinder-api": "http_errors"}
            self._check_http_logs_errors_alarms(get_volumes_list, 100, metrics)
