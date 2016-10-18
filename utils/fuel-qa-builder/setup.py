#!/usr/bin/env python

import os
from setuptools import setup


def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()


def get_requirements_list(requirements):
    all_requirements = read(requirements)
    all_requirements = [req for req in all_requirements.splitlines()
                        if 'devops' not in req and 'launchpadlib' not in req]
    return all_requirements

all_pkgs = ['fuelweb_test', 'gates_tests', 'core']
pkgs = []
for d in all_pkgs:
    print d
    if os.path.isdir(d):
        pkgs += [d]

setup(
    name='fuelweb_test',
    version=1.0,
    description='Fuel-qa fuelweb package',

    url='http://www.openstack.org/',
    author='OpenStack',
    author_email='openstack-dev@lists.openstack.org',
    packages=pkgs,
    include_package_data=True,
    classifiers=[
        'Environment :: Linux',
        'Intended Audience :: Developers',
        'Intended Audience :: Information Technology',
        'License :: OSI Approved :: Apache Software License',
        'Operating System :: POSIX :: Linux',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.4',
    ],
    install_requires=get_requirements_list('./fuelweb_test/requirements.txt'),
)
