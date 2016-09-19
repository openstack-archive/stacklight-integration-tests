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

import ceilometerclient.v2.client
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

    def check_plugin_online(self):
        non_ha_pcmk_resources = ['p_ceilometer-agent-central',
                                 'p_aodh-evaluator']
        ha_pcmk_resources = ['telemetry-collector-heka']
        controller_services = ['ceilometer-agent-notification',
                               'ceilometer-api', 'aodh-api']
        compute_services = ['ceilometer-polling']
        controller_ips = [
            controller['ip'] for controller in
            self.fuel_web.get_nailgun_cluster_nodes_by_roles(
                self.helpers.cluster_id, ['controller'])]
        compute_ips = [
            compute['ip'] for compute in
            self.fuel_web.get_nailgun_cluster_nodes_by_roles(
                self.helpers.cluster_id, ['compute'])]
        logger.info("Check {} pacemaker resources".format(
            non_ha_pcmk_resources))
        for resource in non_ha_pcmk_resources:
            self.helpers.check_pacemaker_resource(
                resource, "controller", is_ha=False)
        logger.info("Check {} pacemaker resources".format(ha_pcmk_resources))
        for resource in ha_pcmk_resources:
            self.helpers.check_pacemaker_resource(resource, "controller")
        logger.info("Check {} services on {}".format(
            controller_services, controller_ips))
        for ip in controller_ips:
            for service in controller_services:
                fuelweb_checkers.verify_service(
                    ip, service, ignore_count_of_proccesses=True)
        logger.info(
            "Check {} services on {}".format(compute_services, compute_ips))
        for ip in compute_ips:
            for service in compute_services:
                fuelweb_checkers.verify_service(
                    ip, service, ignore_count_of_proccesses=True)
        logger.info("Check Ceilometer API")
        keystone_access = self.helpers.os_conn.keystone_access
        endpoint = keystone_access.service_catalog.url_for(
            service_type='metering', service_name='ceilometer',
            interface='internal')
        if not endpoint:
            raise helpers.NotFound("Cannot find ceilometer endpoint")
        headers = {
            'X-Auth-Token': keystone_access.auth_token,
            'content-type': 'application/json'
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
        events_list = self.verify(600, self.ceilometer_client.events.list, 1,
                                  fail_msg, msg, limit=10)
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
                            trait_name=traits[0].name)

        fail_msg = "Failed to check event traits description."
        msg = "checking event traits description"
        self.helpers.verify(60, self.ceilometer_client.trait_descriptions, 5,
                            fail_msg, msg, event_type=event_type)

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
