#!/usr/bin/env python
from setuptools import setup, find_packages
import sys
import os

from GazeParser import __version__

version = __version__

setup(name='GazeParser',
      version=version,
      description='Gaze tracking, parsing and visualization tools',
      long_description="""
The GazeParser is a package for people who want to research human eye movements 
such as psychologists.  For recording, this package is designed to synchronize
a video-based eye-tracking Windows application with the VisionEgg or Psychopy 
stimulus-presentation packages. For analyzing, this package provides various 
functions such as detecting saccades and fixations, plotting and comparing scan 
paths, calculating saccade trajectory curvature and so on.
""",
      classifiers=[
          # http://pypi.python.org/pypi?%3Aaction=list_classifiers
          'Development Status :: 3 - Alpha',
          'Environment :: Console',
          'Intended Audience :: Science/Research',
          'License :: OSI Approved :: GNU General Public License (GPL)',
          'Operating System :: MacOS',
          'Operating System :: Microsoft :: Windows',
          'Operating System :: POSIX :: Linux',
          'Programming Language :: Python',
          'Topic :: Scientific/Engineering',
      ],
      keywords='gaze tracking, eye tracking, eye movement',
      author='Hiroyuki Sogo',
      author_email='hsogo@ehime-u.ac.jp',
      url='http://sourceforge.net/p/gazeparser/',
      license='GNU GPL',
      install_requires=['scipy', 'numpy', 'matplotlib'],
      packages=['GazeParser', 'GazeParser.app'],
      package_data={'GazeParser': ['LICENSE.txt', '*.cfg',
                                   'PsychoPyComponents/*.*'],
                    'GazeParser.app': ['img/*.png', 'img/*.ico',
                                       'img/*.gif', '*.cfg']},
      scripts=['GazeParser_post_install.py', 'setup_for_psychopy.py']
      )
