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
from fuelweb_test import logger


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


def ban_resource(remote, resource, wait=None):
    """Ban a resource from the current node.

        :param remote: SSH connection to the node.
        :type remote: SSHClient
        :param resource: resource name.
        :type name: str
        :param wait: number of seconds to wait for the operation to complete.
        :type operation: int
    """
    cmd = "pcs resource ban {}".format(resource)
    if wait is not None:
        cmd = "{} --wait={}".format(cmd, wait)
    remote.check_call(cmd)


def clear_resource(remote, resource, wait=None):
    """Clear a resource.

        :param remote: SSH connection to the node.
        :type remote: SSHClient
        :param resource: resource name.
        :type name: str
        :param wait: number of seconds to wait for the operation to complete.
        :type operation: int
    """
    cmd = "pcs resource clear {}".format(resource)
    if wait is not None:
        cmd = "{} --wait={}".format(cmd, wait)
    remote.check_call(cmd)


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


def manage_service(remote, name, operation="restart", default=False):
    """Operate service on remote node.

        :param remote: SSH connection to the node.
        :type remote: SSHClient
        :param name: service name.
        :type name: str
        :param operation: type of operation, usually start, stop or restart.
        :type operation: str
    """

    # if remote.execute("pcs resource show {}".format(name))['exit_code'] == 0:
    #     service_cmd = 'pcs resource {operation} {service}'
    if remote.execute("service {} status".format(name))['exit_code'] == 0:
        service_cmd = 'service {service} {operation}'
    elif remote.execute("initctl status {}".format(name))['exit_code'] == 0:
        service_cmd = 'initctl {operation} {service}'
    elif default:
        service_cmd = 'service {service} {operation}'
    else:
        raise Exception('no service handler!')

    remote.check_call(service_cmd.format(service=name, operation=operation))


def manage_pcs_service(remote, name, node, operation="ban"):
    """Operate service on remote node.

        :param remote: SSH connection to the node.
        :type remote: SSHClient
        :param name: service name.
        :type name: str
        :param operation: type of operation, usually start, stop or restart.
        :type operation: str
    """

    remote.check_call("pcs resource {} {} {}".format(operation, name, node))


def clear_local_mail(remote):
    """Clean local mail

        :param remote: SSH connection to the node.
        :type remote: SSHClient
    """
    remote.check_call("rm -f $MAIL")


def fill_up_filesystem(remote, fs, percent, file_name):
    """Fill filesystem on node.

        :param remote: SSH connection to the node.
        :type remote: SSHClient
        :param fs: name of the filesystem to fill up
        :type fs: str
        :param percent: amount of space to be filled in percent.
        :type percent: int
        :param file_name: name of the created file
        :type file_name: str

    """
    logger.info("Filling up {} filesystem to {} percent".format(fs, percent))
    cmd = (
        "fallocate -l $(df | grep {} | awk '{{ printf(\"%.0f\\n\", "
        "1024 * ((($3 + $4) * {} / 100) - $3))}}') {}".format(
            fs, percent, file_name))
    remote.check_call(cmd)


def clean_filesystem(remote, filename):
    """Clean space filled by fill_up_filesystem function

        :param remote: SSH connection to the node.
        :type remote: SSHClient
        :param filename: name of the file to delete
        :type filename: str
    """
    logger.info("Removing {} file".format(filename))
    remote.check_call("rm -f {}".format(filename))
