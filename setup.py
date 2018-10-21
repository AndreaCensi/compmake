from setuptools import setup, find_packages


def get_version(filename):
    import ast
    version_ = None
    with open(filename) as f:
        for line in f:
            if line.startswith('__version__'):
                version_ = ast.parse(line).body[0].value.s
                break
        else:
            raise ValueError('No version found in %r.' % filename)
    if version_ is None:
        raise ValueError(filename)
    return version_


version = get_version(filename='src/compmake/__init__.py')

setup(
        name='compmake',
        author="Andrea Censi",
        url='http://compmake.org',
        version=version,

        description="Compmake is a non-obtrusive module that provides "
                    "'make'-like facilities to your Python applications,"
                    "including caching of results, robustness to jobs failure, "
                    "and multiprocessing/multihost parallel processing.",

        long_description="""
        Compmake is a non-obtrusive module that provides 
        'make'-like facilities to your Python applications,
        including caching of results, robustness to jobs failure,
        and multiprocessing/multihost parallel processing.

        Please see for docs: http://compmake.org 
        and get the manual PDF at: http://purl.org/censi/compmake-manual
    """,

        keywords="parallel processing, make, cmake, manager, recovery",
        license="LGPL",

        classifiers=[
            'Development Status :: 5 - Production/Stable',
            'Intended Audience :: Developers',
            'Intended Audience :: Science/Research',
            'Topic :: Scientific/Engineering',
            'Topic :: System :: Clustering',
            'Topic :: System :: Distributed Computing',
            'Topic :: System :: Hardware :: Symmetric Multi-processing',
            'License :: OSI Approved :: GNU Library or '
            'Lesser General Public License (LGPL)',
        ],

        package_dir={'': 'src'},
        packages=find_packages('src'),
        entry_points={
            'console_scripts': [
                'compmake = compmake.scripts.master:main',
                # 'compmake_slave = compmake.jobs.manager_ssh_cluster:compmake_slave'
            ]
        },
        install_requires=[
            'PyContracts',
            'termcolor',
            'setproctitle',
            'PyYaml',
            'psutil',
            'decorator',
            'SystemCmd',
            'future',
            'networkx>=1,<2',
            'six',
            # 'pyreadline',
        ],

        tests_require=['nose'],
)
