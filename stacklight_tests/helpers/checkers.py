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


def check_http_get_response(url, expected_code=200, msg=None, **kwargs):
    msg = msg or "%s responded with {0}, expected {1}" % url
    r = requests.get(url, **kwargs)
    asserts.assert_equal(
        r.status_code, expected_code, msg.format(r.status_code, expected_code))
    return r
