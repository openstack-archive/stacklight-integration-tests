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

import ceilometerclient.v2.client

from stacklight_tests import base_test
from stacklight_tests.ceilometer_redis import plugin_settings
from stacklight_tests.helpers import helpers


class CeilometerRedisPluginApi(base_test.PluginApi):
    def __init__(self):
        super(CeilometerRedisPluginApi, self).__init__()
        self._ceilometer = None

    @property
    def ceilometer(self):
        if self._ceilometer is None:
            keystone_access = self.helpers.os_conn.keystone_access
            endpoint = keystone_access.service_catalog.url_for(
                service_type='metering',
                service_name='ceilometer',
                interface='internal')
            if not endpoint:
                raise helpers.NotFound("Cannot find ceilometer endpoint")

            self._ceilometer = ceilometerclient.v2.Client(
                endpoint=endpoint, token=lambda: keystone_access.auth_token)
        return self._ceilometer

    def get_plugin_vip(self):
        pass

    def get_plugin_settings(self):
        return plugin_settings

    def prepare_plugin(self):
        self.helpers.prepare_plugin(self.settings.plugin_path)

    def run_ostf(self):
        self.fuel_web.run_ostf(
            cluster_id=self.helpers.cluster_id,
            test_sets=['smoke', 'sanity'],
            timeout=60 * 15
        )

        test_class_main = ('fuel_health.tests.tests_platform.'
                           'test_ceilometer.'
                           'CeilometerApiPlatformTests')

        tests_names = ['test_check_alarm_state',
                       'test_create_sample',
                       'test_check_volume_events',
                       'test_check_glance_notifications',
                       'test_check_keystone_notifications',
                       'test_check_neutron_notifications',
                       'test_check_events_and_traits']

        test_classes = ['{0}.{1}'.format(test_class_main, test_name)
                        for test_name in tests_names]

        for test_name in test_classes:
            self.helpers.run_single_ostf(
                test_sets=['tests_platform'], test_name=test_name)

    def activate_plugin(self, options=None):
        if options is None:
            options = self.settings.default_options
        self.helpers.activate_plugin(
            self.settings.name, self.settings.version, options)

    def check_plugin_online(self):
        resource_names = ['p_redis-server', 'p_ceilometer-agent-central',
                          'p_aodh-evaluator']
        for resource_name in resource_names:
            self.helpers.check_pacemaker_resource(resource_name, "controller")

    def uninstall_plugin(self):
        return self.helpers.uninstall_plugin(self.settings.name,
                                             self.settings.version)

    def check_uninstall_failure(self):
        return self.helpers.check_plugin_cannot_be_uninstalled(
            self.settings.name, self.settings.version)
