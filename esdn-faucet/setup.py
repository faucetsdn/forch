import os
import setuptools
import sys


setuptools.setup(
    name="forch",
    description="Faucet orchestrator",
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: Apache Software License",
        "Operating System :: Debian",
    ],
    python_requires='>=3.6',
    install_requires=[
        'wheel',
        'pbr>=1.9',
        'setuptools>=17.1'
    ],
    setup_requires=['pbr>=1.9', 'setuptools>=17.1'],
    pbr=True
)
