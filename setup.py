import os
import setuptools
import sys


def get_http_files():
    file_list = []
    for file in os.listdir('public'):
        file_list.append(os.path.join('public', file))
    return file_list


data_files = []
data_files.append(('lib/forch/public', get_http_files()))
package_data = {'': ['GVERSION']}

with open("README.md", "r") as fh:
    long_description = fh.read()

version = os.popen('git describe').read().strip()
version_content = f'''"""Forch version file"""

__version__ = '{version}'
'''
with open('forch/__version__.py', 'w+') as version_file:
    version_file.write(version_content)


setuptools.setup(
    name="forch",
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
        'pbr>=1.9',
        'prometheus_client',
        'protobuf',
        'psutil',
        'pyyaml',
        'requests',
        'setuptools>=17.1'
    ],
    setup_requires=['pbr>=1.9', 'setuptools>=17.1'],
    data_files=data_files,
    scripts=['bin/forch'],
    pbr=True
)
