# Stacklight tests


This project based on two other projects:

  * Devops: [Devops documentation](http://docs.fuel-infra.org/fuel-dev/devops.html)

  * Fuel-QA: [Fuel-QA documentation](https://docs.fuel-infra.org/fuel-qa/)


## Step-by-step guide:


1. Prepare the environment:

  * `vi openrc`

  * `. openrc`

  * `./utils/fuel-qa-builder/prepare_env.sh`


2. Run the tests:

  `./utils/jenkins/system_tests.sh -k -K -j fuelweb_test -t test -w $(pwd) -o --group=<your_test_group_to_run>`

  You can read more about on https://docs.fuel-infra.org/fuel-qa/ or
  run it next way to view help: `./utils/jenkins/system_tests.sh -h`.



## To contributors:

Please, follow next rules:

* run `tox` or `tox -epep8` before send to review

* try to reuse in dependencies previous deployed environment in
`@test(depends_on=[<dependency>]`
(usually basic env is deployed in smoke bvt tests)

* mark test group following next pattern:

 ```
 @test(groups=["<full_unique_name_of_test>",
               "<test_method_purpose>",
               "<plugin_name>",
               "<test_category>"])
 ```

 For example:

 ```
 @test(groups=["install_influxdb_grafana",
               "install",
               "influxdb_grafana",
               "smoke"])
 ```