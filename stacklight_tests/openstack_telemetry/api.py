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
import heatclient.v1.client
from fuelweb_test.helpers import checkers as fuelweb_checkers
from fuelweb_test import logger

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
    def nova_cli(self):
        return self.helpers.os_conn.nova

    @property
    def heat_cli(self):
        if self._heat_cli is None:
            keystone_access = self.helpers.os_conn.keystone_access
            endpoint = keystone_access.service_catalog.url_for(
                service_type='orchestration', service_name='heat',
                interface='internal')
            if not endpoint:
                raise self.helpers.NotFound(
                    "Cannot find Heat endpoint")
            auth_url = keystone_access.service_catalog.url_for(
                service_type='identity', service_name='keystone',
                interface='internal')

            self._heat_cli = heatclient.v1.client.Client(
                auth_url=auth_url,
                endpoint=endpoint,
                token=(lambda: keystone_access.auth_token)()
            )
        return self._heat_cli

    @property
    def ceilometer_client(self):
        if self._ceilometer is None:
            keystone_access = self.helpers.os_conn.keystone_access
            endpoint = keystone_access.service_catalog.url_for(
                service_type='metering', service_name='ceilometer',
                interface='internal')
            if not endpoint:
                raise self.helpers.NotFound(
                    "Cannot find Ceilometer endpoint")
            aodh_endpoint = keystone_access.service_catalog.url_for(
                service_type='alarming', service_name='aodh',
                interface='internal')
            if not aodh_endpoint:
                raise self.helpers.NotFound(
                    "Cannot find AODH (alarm) endpoint")
            auth_url = keystone_access.service_catalog.url_for(
                service_type='identity', service_name='keystone',
                interface='internal')
            if not auth_url:
                raise self.helpers.NotFound(
                    "Cannot find Keystone endpoint")

            self._ceilometer = ceilometerclient.v2.Client(
                aodh_endpoint=aodh_endpoint,
                auth_url=auth_url,
                endpoint=endpoint,
                token=lambda: keystone_access.auth_token)
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

    def create_flavor(self, ram=256, vcpus=1, disk=2):
        """This method creates a flavor for Heat tests."""

        logger.info("Creation of Heat tests flavor...")
        name = "ostf_test-heat-flavor"
        for flavor in self.nova_cli.flavors.list():
            if name == flavor.name:
                return flavor
        flavor = self.helpers.os_conn.nova.flavors.create(name, ram, vcpus,
                                                          disk)
        # TODO(idegtiarov): remove test flavor after test passes or fails
        logger.info("Flavor for Heat tests has been created.")
        return flavor

    def create_keypair(self, name="ostf_test-keypair-autoscaling"):
        keypair = None
        for keypairs in self.nova_cli.keypairs.list():
            if name == keypairs.name:
                keypair = keypairs
                break
        if not keypair:
            keypair = self.nova_cli.keypairs.create(name)
        return keypair

    def create_securtity_group(self, name="ostf_test-secgroup-autoscaling"):
        sg_desc = name + " description"
        sec_group = None
        for sgp in self.nova_cli.security_groups.list():
            if name == sgp.name:
                sec_group = sgp
                break
        if not sec_group:
            sec_group = self.nova_cli.security_groups.create(name, sg_desc)
        return sec_group

    def check_ceilometer_autoscaling(self):

        fuel_web = self.helpers.fuel_web

        keystone_access = self.helpers.os_conn.keystone_access
        # need to be checked
        tenant_id = keystone_access.tenant_id
        heat_flavor = self.create_flavor()
        keypair = self.create_keypair()

        controller = fuel_web.get_nailgun_cluster_nodes_by_roles(
            self.helpers.cluster_id, roles=["controller", ])[0]

        with fuel_web.get_ssh_for_nailgun_node(controller) as remote:
            path_to_key = remote.check_call(
                "KEY=`mktemp`; echo '{0}' > $KEY; "
                "chmod 600 $KEY; echo -ne $KEY;".format(keypair.private_key)
            )['stdout'][0]

        sec_group = self.create_securtity_group()
        parameters = {
            'KeyName': keypair.name,
            'InstanceType': heat_flavor.name,
            'ImageId': "TestVM",
            'SecurityGroup': sec_group.name
        }
        net_provider = self.helpers.nailgun_client.get_cluster(
            self.helpers.cluster_id)["net_provider"]
        if "neutron" in net_provider:
            template = self.load_template("heat_autoscaling_neutron.yaml")
            parameters['Net'] = self.create_network_resources(tenant_id)
        else:
            template = self.load_temlate("heat_autoscaling_nova.yaml")
        stack_name = 'ostf_test-heat-stack'
        stack_id = self.heat_cli.stacks.create(
            stack_name=stack_name,
            template=template,
            parameters=parameters,
            disable_rollback=True
        )['stack']['id']

        stack = self.heat_cli.stacks.get(stack_id)

        fail_msg = 'Stack was not created properly.'
        self.helpers.verify(
            600, self.check_stack_status,
            6, fail_msg,
            'stack status becoming "CREATE_COMPLETE"',
            stack_id=stack_id, status='CREATE_COMPLETE'
        )

        reduced_stack_name = '{0}-{1}'.format(
            stack.stack_name[:2], stack.stack_name[-4:])

        logger.info("reduced_name: {}".format(reduced_stack_name))
        instances = self.get_instances_by_name_mask(reduced_stack_name)
        logger.info("list of instances is {}".format(instances[0].id))
        floating_ip = self._create_floating_ip()
        logger.info("Floating Ip is creating")
        assign_floating_ip = self._assign_floating_ip_to_instance(instances[0],
                                                                  floating_ip)
        # launching the second instance during autoscaling
        logger.info("Floating Ip is assigned to instance")
        fail_msg = ("Failed to terminate the 2nd instance per autoscaling "
                    "alarm.")
        msg = "terminating the 2nd instance per autoscaling alarm"
        self.helpers.verify(
            1500, self.check_instance_scaling, 3, fail_msg, msg,
            exp_length=(len(instances)+2),
            reduced_stack_name=reduced_stack_name
        )

        # termination of the second instance during autoscaling
        fail_msg = "Failed to terminate the 2nd instance per autoscaling alarm."
        msg = "terminating the 2nd instance per autoscaling alarm"
        self.verify(
            1500, self.check_instance_scaling, 4, fail_msg, msg,
            exp_lenght=(len(instances) + 1),
            reduced_stack_name=reduced_stack_name
        )

    @staticmethod
    def load_template(file_name):
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

    def check_instance_scaling(self, exp_length, reduced_stack_name):
        return exp_length == self.get_instances_by_name_mask(
            reduced_stack_name)


    def check_stack_status(self, stack_id, status):
        try:
            stack_status = self.heat_cli.stacks.get(stack_id).stack_status
        except Exception:
            stack_status = None
        if stack_status and stack_status == status:
            return True
        return False

    def get_instances_by_name_mask(self, mask_name):
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

    def _create_floating_ip(self):
        floating_ips_pool = self.nova_cli.floating_ip_pools.list()
        logger.info("floating ips pool: {}".format(floating_ips_pool))
        if floating_ips_pool:
            floating_ip = self.nova_cli.floating_ips.create(
                pool=floating_ips_pool[0].name)
            logger.info("floating ip: {}".format(floating_ip))
            return floating_ip
        else:
            logger.warning('No available floating IP found')

    def _assign_floating_ip_to_instance(self, server, floating_ip):
        try:
            self.nova_cli.servers.add_floating_ip(server, floating_ip)
        except Exception:
            logger.exception('Can not assign floating ip to instance')

    def save_key_to_file(self, key):
        return self._run_ssh_cmd(
            "KEY=`mktemp`; echo '{0}' > $KEY; "
            "chmod 600 $KEY; echo -ne $KEY;".format(key))[0]
