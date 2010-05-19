from setuptools import setup


setup(name='compmake',
      version="1.0",
      py_modules=['compmake'],
      entry_points={
         'console_scripts': [
           'compmake = master:main'
        ]
      },
      install_requires=['termcolor', 'setproctitle', 'readline'],
      extras_require={
        'multiprocessing':  ['redis']
        # TODO: learn how to use this feature
        # TODO: add gvgen
    }
)

