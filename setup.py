#!/usr/bin/env python3

from setuptools import setup
from setuptools import find_packages

setup(
    name="analyzer",
    description="PCIe Analyzer modules",
    author="Franck Jullien",
    author_email="franck.jullien@gmail.com",
    license="BSD",
    python_requires="~=3.6",
    packages=find_packages(),
    include_package_data=True,
)
