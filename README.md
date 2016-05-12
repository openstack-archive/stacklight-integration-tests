# StackLight tests

This project contains the functional tests for the [StackLight](https://launchpad.net/lma-toolchain) plugins.

It is based on two other projects:

  * Fuel-Devops ([documentation](http://docs.fuel-infra.org/fuel-dev/devops.html)).

  * Fuel-QA ([documentation](https://docs.fuel-infra.org/fuel-qa/)).

## Getting started

1. Provision the SQL database for fuel-qa (see the [official
   documentation](https://docs.fuel-infra.org/fuel-dev/devops.html#configuring-database)
for the detailed procedure).
2. Prepare the environment:

        cp openrc.default openrc
        # Edit the openrc file as needed
        . openrc
        ./utils/fuel-qa-builder/prepare_env.sh

3. Activate the Python virtual environment:

        . $VENV_PATH/bin/activate

4. Run the tests:

        ./utils/jenkins/system_tests.sh -k -K -j fuelweb_test -t test -w $(pwd) -o --group=<your_test_group_to_run>

## Contributing

If you would like to contribute to the development of this plugin,
you must follow the [OpenStack development workflow](
http://docs.openstack.org/infra/manual/developers.html#development-workflow)
instructions.

Patch reviews take place on the [OpenStack Gerrit](
https://review.openstack.org/#/q/status:open+project:openstack/fuel-plugin-lma-collector,n,z)
system.

Guidelines:

* Run `tox` before submitting a review.

* Declare test groups using the @test decorator (see the [Proboscis](https://pythonhosted.org/proboscis) documentation for details)

```
@test(groups=["<full_unique_name_of_test>",
              "<test_method_purpose>",
              "<plugin_name>",
              "<test_category>"])
```

 For example

```
@test(groups=["install_influxdb_grafana",
              "install",
              "influxdb_grafana",
              "smoke"])
def install_influxdb_grafana():
    ....
```

## Communication

The *OpenStack Development Mailing List* is the preferred way to communicate
with the members of the project.
Emails should be sent to `openstack-dev@lists.openstack.org` with the subject
prefixed by `[fuel][plugins][lma]`.
