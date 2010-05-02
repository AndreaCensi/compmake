from setuptools import setup

import compmake

setup(name='compmake',
      version=compmake.version,
      py_modules=['compmake'],
      entry_points={
         'console_scripts': [
           'compmake = master:main'
        ]
      },
      install_requires=['termcolor', 'setproctitle', 'readline'],
      extras_require={
        'multiprocessing':  ['redis']
    }
)

