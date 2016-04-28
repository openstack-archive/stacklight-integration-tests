Stacklight tests
----------------

Project based on two other projects:
  * Devops
  * Fuel-QA

  [Devops documentation](http://docs.fuel-infra.org/fuel-dev/devops.html)
  [Fuel-QA documentation](https://docs.fuel-infra.org/fuel-qa/)


Step-by-step guide:
-------------------

#. Prepare env:
  * vi openrc
  * . openrc
  * ./utils/fuel-qa-builder/prepare_env.sh

#. Run tests:
  Use fuel-qa technique, you can read more about it on https://docs.fuel-infra.org/fuel-qa/
  Basic method to run for developers is:
  ./utils/jenkins/system_tests.sh -k -K -j fuelweb_test -t test -w $(pwd) -o --group=<your_test_group_to_run>