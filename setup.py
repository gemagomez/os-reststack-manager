#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
from setuptools import setup, find_packages


dependencies = ["flask_sqlalchemy", ]


def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()


setup(
    name="os-reststack-manager",
    version="0.0.1",
    author="Gema Gomez",
    author_email="gema@ggomez.me",
    description="",
    install_requires=dependencies,
    packages=find_packages(),
    long_description=read('README.md'),
    entry_points={
        'console_scripts': [
            'app = os_reststack_manager.app:main',
            ]
        }
)
