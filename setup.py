from setuptools import setup, find_packages


setup(
    name='compmake',
    author="Andrea Censi",
    author_email="andrea@cds.caltech.edu",
    url='http://compmake.org',
    version="0.9.5",
    packages=find_packages(),
    entry_points={
     'console_scripts': [
       'compmake = compmake.scripts.master:main'
       ]
       },
    install_requires=['termcolor', 'setproctitle', 'readline'],
    extras_require={
    'multiprocessing':  ['redis']
    # TODO: learn how to use this feature
    # TODO: add gvgen
    }
)

