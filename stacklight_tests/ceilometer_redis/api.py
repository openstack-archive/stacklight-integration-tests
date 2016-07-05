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
from proboscis.asserts import assert_equal
from stacklight_tests import base_test
from stacklight_tests.ceilometer_redis import plugin_settings
from stacklight_tests.helpers.helpers import NotFound


class CeilometerRedisPluginApi(base_test.PluginApi):
    def __init__(self):
        super(CeilometerRedisPluginApi, self).__init__()
        self._ceilometer = None

    @property
    def ceilometer(self):
        if self._ceilometer is None:
            keystone = self.helpers.os_conn.keystone
            try:
                endpoint = keystone.service_catalog.url_for(
                    service_type='metering',
                    endpoint_type='internalURL')
            except NotFound("Cannot initialize ceilometer client"):
                return None

            self._ceilometer = ceilometerclient.v2.Client(
                endpoint=endpoint, token=lambda: keystone.auth_token)
        return self._ceilometer

    def get_plugin_vip(self):
        pass

    def get_plugin_settings(self):
        return plugin_settings

    def prepare_plugin(self):
        self.helpers.prepare_plugin(self.settings.plugin_path)

    def run_ostf(self, skip_tests=None):
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
                       'test_check_sahara_notifications',
                       'test_check_events_and_traits']

        test_classes = []

        for test_name in tests_names:
            test_classes.append('{0}.{1}'.format(test_class_main,
                                                 test_name))

        all_tests = [test['id'] for test
                     in self.fuel_web.client.get_ostf_tests(self.helpers
                                                            .cluster_id)]

        for test_id in test_classes:
            if test_id in all_tests:
                if skip_tests and test_id.split('.')[-1] in skip_tests:

                    all_status = self.fuel_web.run_single_ostf_test(
                        cluster_id=self.helpers.cluster_id,
                        test_sets=['tests_platform'],
                        test_name=test_id, retries=True, timeout=60 * 20)

                    test_name = next(
                        test['name'] for test
                        in self.fuel_web.client.get_ostf_tests(self.
                                                               helpers.
                                                               cluster_id)
                        if test['id'] == test_id)

                    status = next(test.values()[0]
                                  for test in all_status
                                  if test.keys()[0] == test_name)

                    assert_equal(
                        status, "skipped",
                        'Test: "{}" must be skipped status, '
                        'but his status {}'.format(test_name, status))
                else:
                    self.fuel_web.run_single_ostf_test(
                        cluster_id=self.helpers.cluster_id,
                        test_sets=['tests_platform'],
                        test_name=test_id, timeout=60 * 20)

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
