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
import bs4
import requests
import urllib
import urlparse

from devops.helpers import helpers as devops_helpers
from fuelweb_test import logger
from proboscis import asserts
from pyzabbix import ZabbixAPI

from stacklight_tests.helpers import checkers
from stacklight_tests.helpers import helpers
from stacklight_tests.helpers import remote_ops

from stacklight_tests import base_test
from stacklight_tests.zabbix import plugin_settings as zabbix_plugin_settings


class ZabbixWeb(object):
    def __init__(self, zabbix_url, username, password, protocol, verify=False):
        self.session = requests.Session()
        adapter = requests.adapters.HTTPAdapter(max_retries=3)
        self.session.mount('{}://'.format(protocol), adapter)
        self.base_url = zabbix_url
        self.username = username
        self.password = password
        self.verify = verify

    def zabbix_web_login(self, autologin=1, expected_code=200):
        login_params = urllib.urlencode({'request': '',
                                         'name': self.username,
                                         'password': self.password,
                                         'autologin': autologin,
                                         'enter': 'Sign in'})
        url = urlparse.urljoin(self.base_url,
                               '?{0}'.format(login_params))
        response = self.session.post(url, verify=self.verify)

        asserts.assert_equal(
            response.status_code, expected_code,
            "Login to Zabbix failed: {0}".format(response.content))

    def get_zabbix_web_screen(self, page='screens.php',
                              expected_code=200):
        url = urlparse.urljoin(self.base_url, page)
        response = self.session.get(url, verify=self.verify)

        asserts.assert_equal(response.status_code, expected_code,
                             "Getting Zabbix screens failed: {0}".format(
                                 response.content))

        return bs4.BeautifulSoup(response.content)


class ZabbixApi(base_test.PluginApi):
    def __init__(self):
        super(ZabbixApi, self).__init__()
        self.settings = zabbix_plugin_settings
        self.helpers = helpers.PluginHelper(self.env)
        self.checkers = checkers
        self.remote_ops = remote_ops

    def get_plugin_settings(self):
        return zabbix_plugin_settings

    def prepare_plugin(self, dependat_plugins=False):
        self.helpers.prepare_plugin(self.settings.plugin_path)
        if dependat_plugins:
            for plugin in self.settings.dependant_plugins:
                self.helpers.prepare_plugin(
                    self.settings.dependant_plugins[plugin]["plugin_path"])

    def activate_plugin(self, options=None):
        if options is None:
            options = self.settings.default_options
        self.helpers.activate_plugin(
            self.settings.name, self.settings.version, options)

    def activate_dependant_plugin(self, plugin, options=None):
        if options is None:
            options = self.settings.default_options
        self.helpers.activate_plugin(
            plugin["name"], plugin["version"], options)

    def get_zabbix_url(self, protocol='http'):
        return "{0}://{1}/zabbix/".format(protocol, self.get_zabbix_vip())

    def get_zabbix_vip(self):
        return self.helpers.fuel_web.get_public_vip(self.helpers.cluster_id)

    def check_plugin_online(self):
        controller = self.fuel_web.get_nailgun_cluster_nodes_by_roles(
            self.helpers.cluster_id, ['controller'])[0]
        with self.fuel_web.get_ssh_for_nailgun_node(controller) as remote:
            remote.check_call("dpkg --get-selections | grep zabbix")
            response = remote.execute("crm resource status "
                                      "p_zabbix-server")["stdout"][0]
        asserts.assert_true("p_zabbix-server is running" in response,
                            "p_zabbix-server resource wasn't found"
                            " in pacemaker:\n{0}".format(response))

        zabbix_web = self.get_zabbix_web()
        zabbix_web.zabbix_web_login()
        screens_html = zabbix_web.get_zabbix_web_screen()
        screens_links = screens_html.find_all('a')
        asserts.assert_true(any('charts.php?graphid=' in link.get('href')
                                for link in screens_links),
                            "Zabbix screen page does not contain "
                            "graphs:\n{0}".format(screens_links))

    def uninstall_plugin(self):
        return self.helpers.uninstall_plugin(self.settings.name,
                                             self.settings.version)

    def check_uninstall_failure(self):
        return self.helpers.check_plugin_cannot_be_uninstalled(
            self.settings.name, self.settings.version)

    def get_zabbix_web(self, username='', password='', protocol='http'):
        username = username or self.settings.zabbix_username
        password = password or self.settings.zabbix_password

        return ZabbixWeb(
            self.helpers.fuel_web.get_public_vip(self.helpers.cluster_id),
            username, password, protocol)
