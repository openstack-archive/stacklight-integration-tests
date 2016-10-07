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


# Use a virtual display server for running the tests headless or not
headless_mode = os.environ.get('SELENIUM_HEADLESS', False)

# The browser session will be started with given proxy,
# can be useful if you try to start UI tests on developer machine,
# but environment is on remote server
proxy_address = os.environ.get('DRIVER_PROXY', None)

# Maximize the current window that webdriver is using or not
maximize_window = os.environ.get('SELENIUM_MAXIMIZE', True)

# Sets a sticky timeout to implicitly wait for an element to be found,
# or a command to complete.
implicit_wait = os.environ.get('IMPLICIT_WAIT', 5)

# Set the amount of time to wait for a page load to complete
# before throwing an error.
page_timeout = os.environ.get('PAGE_TIMEOUT', 15)
