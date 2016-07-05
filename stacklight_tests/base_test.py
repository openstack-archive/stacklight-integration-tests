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

from devops.helpers import helpers as devops_helpers
from fuelweb_test import logger
from fuelweb_test.tests import base_test_case
import requests
import six

# Imports used in check_port() method
from contextlib import closing
import socket

from stacklight_tests.helpers import checkers
from stacklight_tests.helpers import helpers
from stacklight_tests.helpers import remote_ops
from stacklight_tests.helpers import ui_tester


@six.add_metaclass(abc.ABCMeta)
class PluginApi(object):
    """Base class to manage StackLight plugins with Fuel."""

    def __init__(self):
        self.test = base_test_case.TestBasic()
        self.env = self.test.env
        self.settings = self.get_plugin_settings()
        self.helpers = helpers.PluginHelper(self.env)
        self.checkers = checkers
        self.remote_ops = remote_ops
        self.ui_tester = ui_tester
        self._checked_ports = {}

    def __getattr__(self, item):
        return getattr(self.test, item)

    @property
    def base_nodes(self):
        """Return a dict mapping nodes to Fuel roles without HA."""
        return {
            'slave-01': ['controller'],
            'slave-02': ['compute', 'cinder'],
            'slave-03': self.settings.role_name,
        }

    @property
    def full_ha_nodes(self):
        """Return a dict mapping nodes to Fuel roles with HA."""
        return {
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

    @abc.abstractmethod
    def get_plugin_settings(self):
        """Return a dict with the default plugin's settings.
        """
        pass

    @abc.abstractmethod
    def prepare_plugin(self):
        """Upload and install the plugin on the Fuel master node.
        """
        pass

    @abc.abstractmethod
    def activate_plugin(self):
        """Enable and configure the plugin in the environment.
        """
        pass

    @abc.abstractmethod
    def get_plugin_vip(self):
        """Get the VIP address associated to the plugin (if any).
        """
        pass

    @abc.abstractmethod
    def check_plugin_online(self):
        """Check that the plugin works properly.
        """
        pass

    def wait_plugin_online(self, timeout=5 * 60):
        """Wait until the plugin will start working properly.
        """
        def check_availability():
            try:
                self.check_plugin_online()
                return True
            except (AssertionError, requests.ConnectionError):
                return False

        logger.info('Wait a plugin become online')
        msg = "Plugin has not become online after a waiting period"
        devops_helpers.wait(
            check_availability, timeout=timeout, timeout_msg=msg)

    def check_plugin_failover(self):
        """Check that failover for the plugin works.
        """
        vip_name = self.helpers.full_vip_name(self.settings.vip_name)
        target_node = self.helpers.get_node_with_vip(
            self.settings.role_name, vip_name)
        self.helpers.power_off_node(target_node)
        self.helpers.wait_for_vip_migration(
            target_node, self.settings.role_name, vip_name)

    def check_port(self, address, port):
        k = "{}{}".format(address, port)
        if k not in self._checked_ports.keys():
            with closing(socket.socket(
                    socket.AF_INET, socket.SOCK_STREAM)) as sock:
                if sock.connect_ex((address, port)) == 0:
                    self._checked_ports[k] = True
                else:
                    self._checked_ports[k] = False
        return self._checked_ports[k]
