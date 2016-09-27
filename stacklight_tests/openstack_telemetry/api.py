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
import datetime
import os

import ceilometerclient.v2.client
from fuelweb_test.helpers import checkers as fuelweb_checkers
from fuelweb_test import logger
import heatclient.v1.client

from stacklight_tests import base_test
from stacklight_tests.helpers import checkers
from stacklight_tests.helpers import helpers
from stacklight_tests.influxdb_grafana.api import InfluxdbPluginApi
from stacklight_tests.openstack_telemetry import plugin_settings


class OpenstackTelemeteryPluginApi(base_test.PluginApi):
    def __init__(self):
        super(OpenstackTelemeteryPluginApi, self).__init__()
        self._ceilometer = None
        self._heat_cli = None

    @property
    def keystone_access(self):
        return self.helpers.os_conn.keystone_access

    @property
    def nova_cli(self):
        return self.helpers.os_conn.nova

    @property
    def neutron_cli(self):
        return self.helpers.os_conn.neutron

    @property
    def auth_url(self):
        return self.keystone_access.service_catalog.url_for(
            service_type='identity', service_name='keystone',
            interface='internal')

    @property
    def heat_cli(self):
        if self._heat_cli is None:
            endpoint = self.keystone_access.service_catalog.url_for(
                service_type='orchestration', service_name='heat',
                interface='internal')
            if not endpoint:
                raise self.helpers.NotFound(
                    "Cannot find Heat endpoint")
            self._heat_cli = heatclient.v1.client.Client(
                auth_url=self.auth_url,
                endpoint=endpoint,
                token=(lambda: self.keystone_access.auth_token)()
            )
        return self._heat_cli

    @property
    def ceilometer_client(self):
        if self._ceilometer is None:
            endpoint = self.keystone_access.service_catalog.url_for(
                service_type='metering', service_name='ceilometer',
                interface='internal')
            if not endpoint:
                raise self.helpers.NotFound(
                    "Cannot find Ceilometer endpoint")
            aodh_endpoint = self.keystone_access.service_catalog.url_for(
                service_type='alarming', service_name='aodh',
                interface='internal')
            if not aodh_endpoint:
                raise self.helpers.NotFound(
                    "Cannot find AODH (alarm) endpoint")
            self._ceilometer = ceilometerclient.v2.Client(
                aodh_endpoint=aodh_endpoint,
                auth_url=self.auth_url,
                endpoint=endpoint,
                token=lambda: self.keystone_access.auth_token)
        return self._ceilometer

    def get_plugin_settings(self):
        return plugin_settings

    def prepare_plugin(self):
        self.helpers.prepare_plugin(self.settings.plugin_path)

    def activate_plugin(self, options=None):
        if options is None:
            options = self.settings.default_options
        self.helpers.activate_plugin(
            self.settings.name, self.settings.version, options)

    def is_kafka_enabled(self):
        return (
            self.fuel_web.get_nailgun_cluster_nodes_by_roles(
                self.helpers.cluster_id, ["kafka"])
        )

    def check_services_on_nodes(self, services, node_role):
        node_ips = [
            node["ip"] for node in
            self.fuel_web.get_nailgun_cluster_nodes_by_roles(
                self.helpers.cluster_id, [node_role])]
        logger.info("Check {} services on {} nodes".format(
            services, node_role))
        for ip in node_ips:
            for service in services:
                fuelweb_checkers.verify_service(
                    ip, service, ignore_count_of_proccesses=True)

    def check_plugin_online(self):
        non_ha_pcmk_resources = ["p_ceilometer-agent-central",
                                 "p_aodh-evaluator"]
        ha_pcmk_resources = ["telemetry-collector-heka"]
        controller_services = ["ceilometer-agent-notification",
                               "ceilometer-api", "aodh-api"]
        compute_services = ["ceilometer-polling"]
        if self.is_kafka_enabled():
            kafka_services = ["telemetry-collector-hindsight"]
            self.check_services_on_nodes(kafka_services, "kafka")
            ha_pcmk_resources = non_ha_pcmk_resources
        else:
            logger.info("Check {} pacemaker resources".format(
                non_ha_pcmk_resources))
            for resource in non_ha_pcmk_resources:
                self.helpers.check_pacemaker_resource(
                    resource, "controller", is_ha=False)
        logger.info(
            "Check {} pacemaker resources".format(ha_pcmk_resources))
        for resource in ha_pcmk_resources:
            self.helpers.check_pacemaker_resource(resource, "controller")
        self.check_services_on_nodes(controller_services, "controller")
        self.check_services_on_nodes(compute_services, "compute")
        logger.info("Check Ceilometer API")
        keystone_access = self.helpers.os_conn.keystone_access
        endpoint = keystone_access.service_catalog.url_for(
            service_type="metering", service_name="ceilometer",
            interface="internal")
        if not endpoint:
            raise helpers.NotFound("Cannot find Ceilometer endpoint")
        headers = {
            "X-Auth-Token": keystone_access.auth_token,
            "content-type": "application/json"
        }
        checkers.check_http_get_response("{}/v2/capabilities".format(endpoint),
                                         headers=headers)
        logger.info("Check Ceilometer database in InfluxDB")
        InfluxdbPluginApi().do_influxdb_query(
            "show measurements", db="ceilometer")

    def uninstall_plugin(self):
        return self.helpers.uninstall_plugin(self.settings.name,
                                             self.settings.version)

    def check_uninstall_failure(self):
        return self.helpers.check_plugin_cannot_be_uninstalled(
            self.settings.name, self.settings.version)

    def check_ceilometer_sample_functionality(self):
        logger.info("Start checking Ceilometer Samples API")

        fail_msg = "Failed to get sample list."
        msg = "getting samples list"
        self.helpers.verify(60, self.ceilometer_client.new_samples.list, 1,
                            fail_msg, msg, limit=10)

        fail_msg = "Failed to get statistic of metric."
        msg = "getting statistic of metric"
        an_hour_ago = (datetime.datetime.now() -
                       datetime.timedelta(hours=1)).isoformat()
        query = [{"field": "timestamp", "op": "gt", "value": an_hour_ago}]

        self.helpers.verify(600, self.ceilometer_client.statistics.list, 2,
                            fail_msg, msg, meter_name="image", q=query)

    def check_ceilometer_alarm_functionality(self):
        logger.info("Start checking Ceilometer AODH(Alarms) API")

        fail_msg = "Failed to create alarm."
        msg = "creating alarm"
        alarm = self.helpers.verify(60, self.create_alarm, 1, fail_msg, msg,
                                    meter_name="image",
                                    threshold=0.9,
                                    name="ceilometer-fake-alarm",
                                    period=600,
                                    statistic="avg",
                                    comparison_operator="lt")

        fail_msg = "Failed to get alarm."
        msg = "getting alarm"
        self.helpers.verify(60, self.ceilometer_client.alarms.get, 2,
                            fail_msg, msg, alarm_id=alarm.alarm_id)

        fail_msg = "Failed while waiting for alarm state to become 'ok'."
        msg = "waiting for alarm state to become 'ok'"
        self.helpers.verify(1000, self.check_alarm_state, 3,
                            fail_msg, msg, alarm_id=alarm.alarm_id, state="ok")

        fail_msg = "Failed to update alarm."
        msg = "updating alarm"
        self.helpers.verify(60, self.ceilometer_client.alarms.update, 4,
                            fail_msg, msg, alarm_id=alarm.alarm_id,
                            threshold=1.1)

        fail_msg = "Failed while waiting for alarm state to become 'alarm'."
        msg = "waiting for alarm state to become 'alarm'"
        self.helpers.verify(1000, self.check_alarm_state, 5,
                            fail_msg, msg, alarm_id=alarm.alarm_id,
                            state="alarm")

        fail_msg = "Failed to get alarm history."
        msg = "getting alarm history"
        self.helpers.verify(60, self.ceilometer_client.alarms.get_history, 6,
                            fail_msg, msg, alarm_id=alarm.alarm_id)

        fail_msg = "Failed to delete alarm."
        msg = "deleting alarm"
        self.helpers.verify(60, self.ceilometer_client.alarms.delete, 7,
                            fail_msg, msg, alarm_id=alarm.alarm_id)

    def check_ceilometer_event_functionality(self):
        logger.info("Start checking Ceilometer Events API")

        fail_msg = "Failed to get event list."
        msg = "getting event list"
        events_list = self.helpers.verify(
            600, self.ceilometer_client.events.list, 1, fail_msg, msg,
            limit=10
        )
        event_type = events_list[0].event_type
        message_id = events_list[0].message_id
        traits = events_list[0].traits

        fail_msg = ("Failed to find '{event_type}' event type in certain "
                    "'{message_id}' event.".format(event_type=event_type,
                                                   message_id=message_id))
        msg = ("searching '{event_type}' event type in certain "
               "'{message_id}' event.".format(event_type=event_type,
                                              message_id=message_id))
        self.helpers.verify(60, self.ceilometer_client.events.get, 2, fail_msg,
                            msg, message_id=message_id)

        fail_msg = "Failed to get event types list."
        msg = "getting event types list"
        self.helpers.verify(60, self.ceilometer_client.event_types.list, 3,
                            fail_msg, msg)

        fail_msg = "Failed to get trait list."
        msg = "getting trait list"
        self.helpers.verify(60, self.ceilometer_client.traits.list, 4,
                            fail_msg, msg, event_type=event_type,
                            trait_name=traits[0]["name"])

        fail_msg = "Failed to check event traits description."
        msg = "checking event traits description"
        self.helpers.verify(60, self.ceilometer_client.trait_descriptions.list,
                            5, fail_msg, msg, event_type=event_type)

    def check_ceilometer_resource_functionality(self):
        logger.info("Start checking Ceilometer Resource API")

        fail_msg = "Failed to get resource list."
        msg = "getting resources list"
        resources_list = self.helpers.verify(
            600, self.ceilometer_client.resources.list, 1, fail_msg, msg,
            limit=10)
        for resource in resources_list:
            # We need to check that resource_id doesn't contain char '/'
            # because if it is GET resource request fails
            if "/" not in resource.resource_id:
                resource_id = resource.resource_id
                break
        fail_msg = ("Failed to find '{}' resource with certain resource "
                    "ID.".format(resource_id))
        msg = ("searching '{}' resource with certain resource "
               "ID".format(resource_id))
        self.helpers.verify(60, self.ceilometer_client.resources.get, 2,
                            fail_msg, msg, resource_id=resource_id)

        fail_msg = "Failed to get meters list."
        msg = "getting meters list"
        self.helpers.verify(60, self.ceilometer_client.meters.list, 3,
                            fail_msg, msg, limit=10)

        fail_msg = "Failed to get unique meters list."
        msg = "getting unique meters list"
        self.helpers.verify(60, self.ceilometer_client.meters.list, 4,
                            fail_msg, msg, limit=10, unique=True)

    def check_ceilometer_autoscaling(self):
        logger.info("Start checking autoscaling")

        # logger.info("keystone: {}".format(self.keystone_access.tenant_id))

        # check required resources available
        self._check_required_resources(min_required_ram_mb=4000)

        # create test flavor
        fail_msg = "Failed to create test heat flavor"
        # heat_flavor = self.helpers.verify(60, self._create_flavor, 1, fail_msg,
        #                                   "creating test heat flavor")
        heat_flavor = self.helpers.verify(
            60, self.helpers.os_conn.create_flavor, 1, fail_msg,
            "creating test heat flavor",
            name="ostf_test-secgroup-autoscaling", ram=256, vcpus=1, disk=2
        )

        # create keypair
        fail_msg = "Failed to create test keypair"
        keypair = self.helpers.verify(
            60, self.helpers.os_conn.create_key, 2, fail_msg,
            "creating test keypair", key_name="ostf_test-keypair-autoscaling")

        # create security group
        fail_msg = "Failed to create test seurity group"
        msg = "creating test security group"
        sec_group = self.helpers.verify(60, self._create_securtity_group, 3,
                                        fail_msg, msg)
        parameters = {
            'KeyName': keypair.name,
            'InstanceType': heat_flavor.name,
            'ImageId': "TestVM",
            'SecurityGroup': sec_group.name
        }
        net_provider = self.helpers.nailgun_client.get_cluster(
            self.helpers.cluster_id)["net_provider"]

        if "neutron" in net_provider:
            template = self._load_template("heat_autoscaling_neutron.yaml")
            fail_msg = "Failed to create test network resources"
            msg = "creating network resources"
            parameters['Net'] = self.helpers.verify(
                60, self._create_network_resources, 4, fail_msg, msg,
                tenant_id=self.keystone_access.tenant_id)
        else:
            template = self._load_temlate("heat_autoscaling_nova.yaml")

        # create Heat stack
        fail_msg = "Failed to create Heat stack"
        msg = "creating Heat stack"
        stack_name = 'ostf_test-heat-stack'
        stack_id = self.helpers.verify(60, self.heat_cli.stacks.create, 5,
                                       fail_msg, msg,
                                       stack_name=stack_name,
                                       template=template,
                                       parameters=parameters,
                                       disable_rollback=True)['stack']['id']

        # stack_id = "2223d319-2b8f-4d86-8131-6b40d89b24be"

        # get Heat stack
        fail_msg = "Failed to get Heat stack"
        msg = "getting Heat stack"
        stack = self.helpers.verify(60, self.heat_cli.stacks.get, 6, fail_msg,
                                    msg, stack_id=stack_id)

        # check stack creation comleted
        fail_msg = "Stack was not created properly."
        self.helpers.verify(
            600, self._check_stack_status,
            6, fail_msg,
            "stack status becoming 'CREATE_COMPLETE'",
            stack_id=stack_id, status="CREATE_COMPLETE"
        )

        # getting instances list
        reduced_stack_name = "{0}-{1}".format(
            stack.stack_name[:2], stack.stack_name[-4:])

        instances = self.helpers.verify(60, self._get_instances_by_name_mask,
                                        7, "Failed to get instances list",
                                        "getting instances list",
                                        mask_name=reduced_stack_name)

        # assign floating ip to instance
        self.helpers.verify(60, self.helpers.os_conn.assign_floating_ip, 9,
                            "Failed to assign floating ip to instance",
                            "assigning floating ip to instance",
                            srv=instances[0], use_neutron=True)

        # launching the second instance during autoscaling
        fail_msg = "Failed to launch the 2nd instance per autoscaling alarm."
        msg = "launching the new instance per autoscaling alarm"
        self.helpers.verify(
            1500, self._check_instance_scaling, 10, fail_msg, msg,
            exp_length=(len(instances) + 2),
            reduced_stack_name=reduced_stack_name
        )

        # termination of the second instance during autoscaling
        fail_msg = ("Failed to terminate the 2nd instance per autoscaling "
                    "alarm.")
        msg = "terminating the 2nd instance per autoscaling alarm"
        self.helpers.verify(
            1500, self.check_instance_scaling, 11, fail_msg, msg,
            exp_lenght=(len(instances) + 1),
            reduced_stack_name=reduced_stack_name
        )

        # delete Heat stack
        self.helpers.verify(60, self.heat_cli.stacks.delete, 12,
                            "Failed to delete Heat stack",
                            "deleting Heat stack", stack_id=stack_id)
        self.helpers.verify(
            600, self.check_instance_scaling, 13,
            "Not all stack instances was deleted",
            "checking all stack instances was deleted",
            exp_lenght=(len(instances) - 1),
            reduced_stack_name=reduced_stack_name
        )

    def _create_securtity_group(self, name="ostf_test-secgroup-autoscaling"):
        logger.info("Creating test security group for Heat autoscaling...")
        sg_desc = name + " description"
        sec_group = None
        for sgp in self.nova_cli.security_groups.list():
            if name == sgp.name:
                sec_group = sgp
                break
        if not sec_group:
            sec_group = self.nova_cli.security_groups.create(name, sg_desc)
        return sec_group

    def _create_network_resources(self, tenant_id):
        """This method creates network resources.

        It creates a network, an internal subnet on the network, a router and
        links the network to the router. All resources created by this method
        will be automatically deleted.
        """
        logger.info("Creating network resources...")
        net_name = "ostf-autoscaling-test-service-net"
        net_body = {
            "network": {
                "name": net_name,
                "tenant_id": tenant_id
            }
        }
        ext_net = None
        net = None
        for network in self.neutron_cli.list_networks()["networks"]:
            if not net and network["name"] == net_name:
                net = network
            if not ext_net and network["router:external"]:
                ext_net = network
        if not net:
            net = self.neutron_cli.create_network(net_body)["network"]
        subnet = self.helpers.os_conn.create_subnet(
            "sub" + net_name, net["id"], "10.1.7.0/24", tenant_id=tenant_id
        )
        router_name = 'ostf-autoscaling-test-service-router'
        router = self.helpers.os_conn.create_router(
            router_name, self.helpers.os_conn.get_tenant("admin"))
        self.neutron_cli.add_interface_router(
            router["id"], {"subnet_id": subnet["id"]})
        return net["id"]

    @staticmethod
    def _load_template(file_name):
        """Load specified template file from etc directory."""

        filepath = os.path.join(
            os.path.dirname(os.path.realpath(__file__)),
            '../../fixtures/network_templates', file_name)
        with open(filepath) as f:
            return f.read()

    def create_alarm(self, **kwargs):
        for alarm in self.ceilometer_client.alarms.list():
            if alarm.name == kwargs['name']:
                self.ceilometer_client.alarms.delete(alarm.alarm_id)
        return self.ceilometer_client.alarms.create(**kwargs)

    def check_alarm_state(self, alarm_id, state=None):
        try:
            alarm_state = self.ceilometer_client.alarms.get_state(
                alarm_id)
        except Exception:
            alarm_state = None
        if state:
            if alarm_state == state:
                return True
        elif alarm_state == 'alarm' or 'ok':
            return True
        return False

    def _check_instance_scaling(self, exp_length, reduced_stack_name):
        return exp_length == self._get_instances_by_name_mask(
            reduced_stack_name)

    def _check_stack_status(self, stack_id, status):
        try:
            stack_status = self.heat_cli.stacks.get(stack_id).stack_status
        except Exception:
            stack_status = None
        if stack_status and stack_status == status:
            return True
        return False

    def _get_instances_by_name_mask(self, mask_name):
        """This method retuns list of instances with certain names."""

        instances = []

        instance_list = self.nova_cli.servers.list()
        logger.info('Instances list is {0}'.format(instance_list))
        logger.info(
            'Expected instance name should inlude {0}'.format(mask_name))

        for inst in instance_list:
            logger.info('Instance name is {0}'.format(inst.name))
            if inst.name.startswith(mask_name):
                instances.append(inst)
        return instances

    def save_key_to_file(self, key):
        return self._run_ssh_cmd(
            "KEY=`mktemp`; echo '{0}' > $KEY; "
            "chmod 600 $KEY; echo -ne $KEY;".format(key))[0]

    def _get_info_about_available_resources(self, min_ram, min_hdd, min_vcpus):
        """This function allows to get the information about resources.

        We need to collect the information about available RAM, HDD and vCPUs
        on all compute nodes for cases when we will create more than 1 VM.

        This function returns the count of VMs with required parameters which
        we can successfully run on existing cloud.
        """
        vms_count = 0
        for hypervisor in self.nova_cli.hypervisors.list():
            if hypervisor.free_ram_mb >= min_ram:
                if hypervisor.free_disk_gb >= min_hdd:
                    if hypervisor.vcpus - hypervisor.vcpus_used >= min_vcpus:
                        # We need to determine how many VMs we can run
                        # on this hypervisor
                        free_cpu = hypervisor.vcpus - hypervisor.vcpus_used
                        k1 = int(hypervisor.free_ram_mb / min_ram)
                        k2 = int(hypervisor.free_disk_gb / min_hdd)
                        k3 = int(free_cpu / min_vcpus)
                        vms_count += min(k1, k2, k3)
        return vms_count

    def _check_required_resources(self, min_required_ram_mb=4096,
                                  hdd=40, vCpu=2):
        vms_count = self._get_info_about_available_resources(
            min_required_ram_mb, hdd, vCpu)
        if vms_count < 1:
            msg = ('This test requires more hardware resources of your '
                   'OpenStack cluster: your cloud should allow to create '
                   'at least 1 VM with {0} MB of RAM, {1} HDD and {2} vCPUs. '
                   'You need to remove some resources or add compute nodes '
                   'to have an ability to run this OSTF test.'
                   .format(min_required_ram_mb, hdd, vCpu))
            raise helpers.SkipTest(msg)
