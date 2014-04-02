#!/usr/bin/env python

from distutils.core import setup
dist = setup(
    name='rcore',
    version='1.0.3',
    description = "Core for rion's python daemons",
    long_description = """jsut a packages which includes all often
    necessary tools like xmlrpc, schedulers, config handing, db and etc""",
    author="rion",
    author_email="rion4ik@gmail.com",
    url="https://github.com/Ri0n/rcore",
    license="GPL-3",

    packages=['rcore'],
    requires=["watchdog", "twisted"]
)
