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

from fuelweb_test.helpers import checkers
from fuelweb_test import logger
from stacklight_tests import base_test
from stacklight_tests.openstack_telemetry import plugin_settings


class OpenstackTelemeteryPluginApi(base_test.PluginApi):
    def __init__(self):
        super(OpenstackTelemeteryPluginApi, self).__init__()

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
        non_ha_resources = ['p_ceilometer-agent-central', 'p_aodh-evaluator']
        ha_resources = ['telemetry-collector']
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
        logger.info("Check {} pacemaker resources".format(non_ha_resources))
        for resource in non_ha_resources:
            self.helpers.check_pacemaker_resource(
                resource, "controller", is_ha=False)
        logger.info("Check {} pacemaker resources".format(ha_resources))
        for resource in ha_resources:
            self.helpers.check_pacemaker_resource(resource, "controller")
        logger.info("Check {} services on {}".format(
            controller_services, controller_ips))
        for ip in controller_ips:
            for service in controller_services:
                checkers.verify_service(
                    ip, service, ignore_count_of_proccesses=True)
        logger.info(
            "Check {} services on {}".format(compute_services, compute_ips))
        for ip in compute_ips:
            for service in compute_services:
                checkers.verify_service(ip, service,
                                        ignore_count_of_proccesses=True)

    def uninstall_plugin(self):
        return self.helpers.uninstall_plugin(self.settings.name,
                                             self.settings.version)

    def check_uninstall_failure(self):
        return self.helpers.check_plugin_cannot_be_uninstalled(
            self.settings.name, self.settings.version)
