import os
import setuptools
import sys


def get_http_files():
    file_list = []
    for file in os.listdir('public'):
        file_list.append(os.path.join('public', file))
    return file_list


data_files = []
data_files.append(('forch/public', get_http_files()))
package_data = {'': ['GVERSION']}

with open("README.md", "r") as fh:
    long_description = fh.read()

version = os.popen('git describe').read().strip()

setuptools.setup(
    name="forch",
    version=version,
    description="Faucet orchestrator",
    long_description=long_description,
    long_description_content_type="text/markdown",
    packages=setuptools.find_packages(),
    package_data=package_data,
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: Apache Software License",
        "Operating System :: Debian",
    ],
    python_requires='>=3.6',
    install_requires=[
        'wheel',
        'prometheus_client',
        'protobuf',
        'psutil',
        'pyyaml',
        'requests'
    ],
    data_files=data_files,
    scripts=['bin/forch']
)
