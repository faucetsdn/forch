import os
import setuptools


def get_http_files():
    file_list = []
    for file in os.listdir('public'):
        file_list.append(os.path.join('public', file))
    return file_list


data_files = []
data_files.append(('forch/public', get_http_files()))

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="forch",
    version="1.0",
    description="Faucet orchestrator",
    long_description=long_description,
    long_description_content_type="text/markdown",
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: Apache Software License",
        "Operating System :: Debian",
    ],
    python_requires='>=3.6',
    install_requires=['requests', 'prometheus_client', 'psutil', 'pyyaml'],
    data_files=data_files,
    scripts=['bin/forch']
)
