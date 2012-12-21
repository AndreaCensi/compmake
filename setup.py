import os
from setuptools import setup, find_packages


def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()

version = "2.2.0"


setup(
    name='compmake',
    author="Andrea Censi",
    author_email="andrea@cds.caltech.edu",
    url='http://compmake.org',
    version=version,

    description="Compmake is a non-obtrusive module that provides "
        "'make'-like facilities to your Python computations,"
        "including caching of results, robustness to exceptions, "
        "and multiprocessing/multihost parallel processing. ",

    long_description=read('README.rst'),
    keywords="parallel processing, make, cmake, manager, recovery",
    license="LGPL",

    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'Intended Audience :: Science/Research',
        'Topic :: Scientific/Engineering',
        'Topic :: System :: Clustering',
        'Topic :: System :: Distributed Computing',
        'Topic :: System :: Hardware :: Symmetric Multi-processing',
        'License :: OSI Approved :: GNU Library or '
        'Lesser General Public License (LGPL)',
    ],

    package_dir={'':'src'},
    packages=find_packages('src'),
    entry_points={
     'console_scripts': [
       'compmake = compmake.scripts.master:main',
       'compmake_slave = compmake.jobs.manager_ssh_cluster:compmake_slave'
      ]
    },
    install_requires=['termcolor', 'setproctitle', 'readline', 'PyYaml', 'psutil'],

    tests_require=['nose']
    # extras_require={
    # 'multiprocessing':  ['redis']
    # # TODO: learn how to use this feature
    # # TODO: add gvgen
    # }
)

