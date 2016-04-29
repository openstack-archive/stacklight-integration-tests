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

import abc

from fuelweb_test.tests import base_test_case
import six

from stacklight_tests.helpers import checkers
from stacklight_tests.helpers import helpers
from stacklight_tests.helpers import remote_ops
from stacklight_tests.helpers import ui_tester
from stacklight_tests import settings


@six.add_metaclass(abc.ABCMeta)
class PluginApi(object):
    """Common test class to operate with StackLight plugin."""

    def __init__(self):
        self.test = base_test_case.TestBasic()
        self.env = self.test.env
        self.settings = self.get_plugin_settings()
        self.helpers = helpers.PluginHelper(self.env)
        self.checkers = checkers
        self.remote_ops = remote_ops
        self.ui_tester = ui_tester.UITester()

    def __getattr__(self, item):
        return getattr(self.test, item)

    @property
    def base_nodes(self):
        base_nodes = {
            'slave-01': ['controller'],
            'slave-02': ['compute', 'cinder'],
            'slave-03': self.settings.role_name,
        }
        return base_nodes

    @property
    def full_ha_nodes(self):
        full_ha_nodes = {
            'slave-01': ['controller'],
            'slave-02': ['controller'],
            'slave-03': ['controller'],
            'slave-04': ['compute', 'cinder'],
            'slave-05': ['compute', 'cinder'],
            'slave-06': ['compute', 'cinder'],
            'slave-07': self.settings.role_name,
            'slave-08': self.settings.role_name,
            'slave-09': self.settings.role_name,
        }
        return full_ha_nodes

    def create_cluster(self, cluster_settings=None,
                       mode=settings.DEPLOYMENT_MODE):
            return helpers.create_cluster(
                self.env,
                name=self.__class__.__name__,
                cluster_settings=cluster_settings,
                mode=mode,
            )

    @abc.abstractmethod
    def get_plugin_settings(self):
        pass

    @abc.abstractmethod
    def prepare_plugin(self):
        pass

    @abc.abstractmethod
    def activate_plugin(self, cluster_id):
        pass

    @abc.abstractmethod
    def get_plugin_vip(self, cluster_id):
        pass

    @abc.abstractmethod
    def check_plugin_online(self, cluster_id):
        pass
