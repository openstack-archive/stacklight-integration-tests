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

from contextlib import closing
import socket

from devops.error import DevopsCalledProcessError
from devops.helpers import helpers as devops_helpers
from proboscis import asserts
import requests
from requests.packages.urllib3 import poolmanager

from stacklight_tests.helpers import helpers
from stacklight_tests.helpers import remote_ops


class TestHTTPAdapter(requests.adapters.HTTPAdapter):
    """Custom transport adapter to disable host checking in https requests."""

    def init_poolmanager(self, connections, maxsize, block=False):
        self.poolmanager = poolmanager.PoolManager(assert_hostname=False)


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
    s.mount("https://", TestHTTPAdapter())
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


def check_port(address, port):
    """Check whether or not a TCP port is open.

    :param address: server address
    :type address: str
    :param port: server port
    :type port: str
    """
    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as sock:
        return sock.connect_ex((address, port)) == 0


def check_local_mail(remote, node_name, service, state, timeout=10 * 60):
    """Check that email from LMA Infrastructure Alerting plugin about service
    changing it's state is presented on a host.

    :param remote: SSH connection to the node.
    :type remote: SSHClient
    :param node_name: name of the node to check for email on.
    :type node_name: str
    :param service: service to look for.
    :type service: str
    :param state: status of service to check.
    :type state: str
    :param timeout: timeout to wait for email to arrive.
    :rtype timeout: int
    """
    def check_mail():
        try:
            response = remote.check_call("cat $MAIL")
            if not response:
                return False
            if ("Service: {}\n".format(service) in response['stdout'] and
                    "State: {}\n".format(state) in response['stdout']):
                return True
        except DevopsCalledProcessError:
            return False
    msg = ("Email about service {0} in {1} state was not "
           "found on {2} after {3} seconds").format(
        service, state, node_name, timeout)
    devops_helpers.wait(check_mail, timeout=timeout, timeout_msg=msg)
