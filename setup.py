# -*- coding: utf-8 -*-
import os
from setuptools import setup

def read(fname):
    try:
        return open(os.path.join(os.path.dirname(__file__), fname)).read()
    except:
        return ''

setup(
    name='todoist-flask',
    version='1.00.00',
    packages=['todoist', 'todoist.managers'],
    author='Ben Matheja',
    author_email='post@benmatheja.de',
    license='BSD',
    description='todoist-flask - Todoist Webhook Consumer for Creation of Tasks based on Events',
    long_description = read('README.md'),
    install_requires=[
        'requests',
        'flask',
        'gunicorn',
    ],
    # see here for complete list of classifiers
    # http://pypi.python.org/pypi?%3Aaction=list_classifiers
    classifiers=(
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Programming Language :: Python',
    ),
)
