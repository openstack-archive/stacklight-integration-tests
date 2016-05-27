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
from proboscis import asserts
import requests


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
    msg = msg or "%s responded with {0}, expected {1}" % url
    r = requests.get(url, **kwargs)
    asserts.assert_equal(
        r.status_code, expected_code, msg.format(r.status_code, expected_code))
    return r


def verify_services(remote, service_name, count):
    """Check that a process is running on a host.

    :param remote: SSHClient
    :type remote: SSHClient object
    :param service_name: the process name to match.
    :type service_name: str
    :param count: the number of processes to match.
    :type count: int
    """
    checkers.verify_service(remote, service_name, count)
