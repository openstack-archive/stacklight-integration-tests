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
    """Return all network bridges for a node.

    :param remote: SSH connection to the node.
    :type remote: SSHClient
    :param excluded_criteria: regular expression to filter out items
    :type excluded_criteria: str
    :returns: list of interfaces
    :rtype: list
    """
    # TODO(rpromyshlennikov): do filtration on python side
    excluded_criteria_cmd = (
        " | grep -v '%s'" % excluded_criteria
        if excluded_criteria else "")
    cmd = "brctl show | awk '/br-/{{print $1}}'{excluded}".format(
        excluded=excluded_criteria_cmd)
    interfaces = remote.check_call(cmd)["stdout"]
    return [iface.strip() for iface in interfaces]


def switch_interface(remote, interface, up=True):
    """Turn a network interface up or down.

    :param remote: SSH connection to the node.
    :type remote: SSHClient
    :param interface: interface name.
    :type interface: str
    :param up: whether the interface should be turned up (default: True).
    :type up: boolean
    """
    method = 'up' if up else 'down'
    cmd = "if{method} {interface}".format(method=method,
                                          interface=interface)
    remote.check_call(cmd)


def simulate_network_interrupt_on_node(remote, interval=30):
    """Simulate a network outage on a node.

    :param remote: SSH connection to the node.
    :type remote: SSHClient
    :param interval: outage duration in seconds (default: 30).
    :type interval: int
    """
    cmd = (
        "(/sbin/iptables -I INPUT -j DROP && "
        "sleep {interval} && "
        "/sbin/iptables -D INPUT -j DROP) 2>&1>/dev/null &".format(
            interval=interval))
    remote.execute(cmd)


def get_pids_of_process(remote, name):
    """Get PIDs of process by its name.

        :param remote: SSH connection to the node.
        :type remote: SSHClient
        :param name: process name.
        :type name: str
        :returns: list of PIDs.
        :rtype: list
        """
    cmd = "pidof {}".format(name)
    result = remote.execute(cmd)
    if result['exit_code'] != 0:
        return []
    return result['stdout'][0].strip().split()


def manage_pacemaker_service(remote, name, operation="restart"):
    """Operate HA service on remote node.

        :param remote: SSH connection to the node.
        :type remote: SSHClient
        :param name: service name.
        :type name: str
        :param operation: type of operation, usually start, stop or restart.
        :type operation: str
    """
    remote.check_call("crm resource {operation} {service}".format(
        operation=operation, service=name))


def manage_initctl_service(remote, name, operation="restart"):
    """Operate service on remote node.

        :param remote: SSH connection to the node.
        :type remote: SSHClient
        :param name: service name.
        :type name: str
        :param operation: type of operation, usually start, stop or restart.
        :type operation: str
    """
    remote.check_call("initctl {operation} {service}".format(
        operation=operation, service=name))


def manage_service(remote, name, operation="restart"):
    """Operate service on remote node.

        :param remote: SSH connection to the node.
        :type remote: SSHClient
        :param name: service name.
        :type name: str
        :param operation: type of operation, usually start, stop or restart.
        :type operation: str
    """
    remote.check_call("service {service} {operation}".format(
        service=name, operation=operation))


def clear_local_mail(remote):
    """Clean local mail

        :param remote: SSH connection to the node.
        :type remote: SSHClient
    """
    remote.check_call("rm -f $MAIL")


def fill_mysql_space(remote, parameter):
    """Fill space on node.

        :param remote: SSH connection to the node.
        :type remote: SSHClient
        :param parameter: amount of space to be filled in percentages.
        :type name: int
    """
    cmd = ("fallocate -l $(df | grep /dev/mapper/mysql-root |"
           " awk '{{ printf(\"%.0f\\n\", "
           "1024 * ((($3 + $4) * {0} / 100) - $3))}}') "
           "/var/lib/mysql/test/bigfile".format(parameter))
    remote.check_call(cmd)


def clean_mysql_space(remote):
    """Clean space filled by fill_mysql_space function

        :param remote: SSH connection to the node.
        :type remote: SSHClient
    """
    remote.check_call("rm /var/lib/mysql/test/bigfile")
