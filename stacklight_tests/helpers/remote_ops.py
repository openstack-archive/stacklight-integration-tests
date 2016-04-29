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


def get_all_bridged_interfaces_for_node(remote, excluded_criteria=None):
    # TODO(rpromyshlennikov): do filtration on python side
    excluded_criteria_cmd = (
        " | grep -v '%s'" % excluded_criteria
        if excluded_criteria else "")
    cmd = "brctl show | awk '/br-/{{print $1}}'{excluded}".format(
        excluded=excluded_criteria_cmd)
    interfaces = remote.check_call(cmd)["stdout"]
    return [iface.strip() for iface in interfaces]


def switch_interface(remote, interface, method="up"):
    cmd = "if{method} {interface}".format(method=method,
                                          interface=interface)
    remote.check_call(cmd)


def simulate_network_interrupt_on_node(remote):
    cmd = (
        "(/sbin/iptables -I INPUT -j DROP "
        "&& sleep 30 "
        "&& /sbin/iptables -D INPUT -j DROP) 2>&1>/dev/null &")
    remote.execute(cmd)
