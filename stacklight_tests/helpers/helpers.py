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

import os

from fuelweb_test import logger
from proboscis import asserts

from stacklight_tests import settings


def create_cluster(
        env, name, cluster_settings=None, mode=settings.DEPLOYMENT_MODE):
    return env.fuel_web.create_cluster(
        name=name, settings=cluster_settings, mode=mode)


class PluginHelper(object):

    def __init__(self, env):
        self.env = env
        self.fuel_web = self.env.fuel_web

    def prepare_plugin(self, plugin_path):
        self.env.admin_actions.upload_plugin(plugin=plugin_path)
        self.env.admin_actions.install_plugin(
            plugin_file_name=os.path.basename(plugin_path))

    def activate_plugin(self, cluster_id, name, version, options):
        msg = "Plugin couldn't be enabled. Check plugin version. Test aborted"
        asserts.assert_true(
            self.fuel_web.check_plugin_exists(cluster_id, name),
            msg)
        self.fuel_web.update_plugin_settings(
            cluster_id, name, version, options)

    def get_plugin_vip(self, cluster_id, vip_name):
        networks = self.fuel_web.client.get_networks(cluster_id)
        vip = networks.get('vips').get(vip_name, {}).get('ipaddr', None)
        asserts.assert_is_not_none(
            vip, "Failed to get the IP of {} server".format(vip_name))

        logger.debug("Check that {} is ready".format(vip_name))

    def get_all_ready_nodes(self, cluster_id):
        return [node for node in
                self.fuel_web.client.list_cluster_nodes(cluster_id)
                if node["status"] == "ready"]
