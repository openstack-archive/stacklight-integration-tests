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

from proboscis import asserts
import requests
from requests.packages.urllib3.poolmanager import PoolManager

from stacklight_tests.helpers import helpers
from stacklight_tests.helpers import remote_ops


class TestHTTPAdapter(requests.adapters.HTTPAdapter):
    """Custom transport adapter disables host checking in https requests."""

    def init_poolmanager(self, connections, maxsize, block=False):
        self.poolmanager = PoolManager(assert_hostname=False)


def check_http_get_response(url, expected_code=200, msg=None, **kwargs):
    """Perform a HTTP GET request and assert that the HTTP server replies with
    the expected code.

    :param url: the requested URL
    :type url: str
    :param expected_code: the expected HTTP response code. Defaults to 200
    :type expected_code: int
    :param msg: the assertion message. Defaults to None
    :type msg: str
    :returns: HTTP response object
    :rtype: requests.Response
    """
    s = requests.Session()
    s.mount("https:/", TestHTTPAdapter())
    cert = helpers.get_fixture("https/rootCA.pem")
    msg = msg or "%s responded with {0}, expected {1}" % url
    r = s.get(url, verify=cert, **kwargs)
    asserts.assert_equal(
        r.status_code, expected_code, msg.format(r.status_code, expected_code))
    return r


def check_process_count(remote, process, count):
    """Check that the expected number of processes is running on a host.

    :param remote: SSH connection to the node.
    :type remote: SSHClient
    :param process: the process name to match.
    :type process: str
    :param count: the number of processes to match.
    :type count: int
    :returns: list of PIDs.
    :rtype: list
    """
    msg = "Got {got} instances instead of {count} for process {process}."
    pids = remote_ops.get_pids_of_process(remote, process)
    asserts.assert_equal(
        len(pids), count,
        msg.format(process=process, count=count, got=len(pids)))
    return pids
