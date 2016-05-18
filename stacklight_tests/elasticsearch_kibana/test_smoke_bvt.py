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

from fuelweb_test.helpers.decorators import log_snapshot_after_test
from proboscis import test

from stacklight_tests.elasticsearch_kibana import api


@test(groups=["plugins"])
class TestElasticsearchPlugin(api.ElasticsearchPluginApi):
    """Class for smoke testing the Elasticsearch-Kibana plugin."""

    @test(depends_on_groups=['prepare_slaves_3'],
          groups=["install_elasticsearch_kibana", "install",
                  "elasticsearch_kibana", "smoke"])
    @log_snapshot_after_test
    def install_elasticsearch_kibana(self):
        """Install Elasticsearch-Kibana plugin and check it exists

        Scenario:
            1. Upload the Elasticsearch/Kibana plugin to the master node
            2. Install the plugin
            3. Create a cluster
            4. Check that the plugin can be enabled

        Duration 20m
        """
        self.env.revert_snapshot("ready_with_3_slaves")

        self.prepare_plugin()

        self.helpers.create_cluster()

        self.activate_plugin()

    @test(depends_on_groups=['prepare_slaves_3'],
          groups=["deploy_elasticsearch_kibana", "deploy",
                  "elasticsearch_kibana", "smoke"])
    @log_snapshot_after_test
    def deploy_elasticsearch_kibana(self):
        """Deploy a cluster with the Elasticsearch-Kibana plugin

        Scenario:
            1. Upload the Elasticsearch/Kibana plugin to the master node
            2. Install the plugin
            3. Create the cluster
            4. Add 1 node with controller role
            5. Add 1 node with compute and cinder roles
            6. Add 1 node with elasticsearch_kibana role
            7. Deploy the cluster
            8. Check that Elasticsearch/Kibana are running
            9. Run OSTF

        Duration 60m
        Snapshot deploy_elasticsearch_kibana
        """
        self.check_run("deploy_elasticsearch_kibana")
        self.env.revert_snapshot("ready_with_3_slaves")

        self.prepare_plugin()

        self.helpers.create_cluster()

        self.activate_plugin()

        self.helpers.deploy_cluster(self.base_nodes)

        self.check_plugin_online()

        self.helpers.run_ostf()

        self.env.make_snapshot("deploy_elasticsearch_kibana", is_make=True)

    @test(depends_on_groups=['prepare_slaves_9'],
          groups=["deploy_ha_elasticsearch_kibana", "deploy", "deploy_ha"
                  "elasticsearch_kibana", "smoke"])
    @log_snapshot_after_test
    def deploy_ha_elasticsearch_kibana(self):
        """Deploy a cluster with the Elasticsearch-Kibana plugin in HA mode

        Scenario:
            1. Upload the Elasticsearch/Kibana plugin to the master node
            2. Install the plugin
            3. Create the cluster
            4. Add 3 nodes with controller role
            5. Add 3 nodes with compute and cinder roles
            6. Add 3 nodes with elasticsearch_kibana role
            7. Deploy the cluster
            8. Check that Elasticsearch/Kibana are running
            9. Run OSTF

        Duration 120m
        Snapshot deploy_ha_elasticsearch_kibana
        """
        self.check_run("deploy_ha_elasticsearch_kibana")
        self.env.revert_snapshot("ready_with_9_slaves")

        self.prepare_plugin()

        self.helpers.create_cluster()

        self.activate_plugin()

        self.helpers.deploy_cluster(self.full_ha_nodes)

        self.check_plugin_online()

        self.helpers.run_ostf()

        self.env.make_snapshot("deploy_ha_elasticsearch_kibana", is_make=True)
