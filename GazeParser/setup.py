#!/usr/bin/env python

from setuptools import setup, find_packages
import sys
import os

version = '0.11.1'

setup(name='GazeParser',
      version=version,
      description='Gaze tracking, parsing and visualization tools',
      long_description="""
The GazeParser is a package for eye movement research. 
For recording, this package provides a module to control SimpleGazeTracker, 
an open-source video-based eye-tracking application, from VisionEgg and PsychoPy.
For data analysis, this package provides various  functions such as detecting
saccades and fixations, plotting and comparing scan paths, calculating saccade
trajectory curvature and so on.

See http://sourceforge.net/p/gazeparser/ for detail.
""",
      classifiers=[
          # http://pypi.python.org/pypi?%3Aaction=list_classifiers
          'Development Status :: 4 - Beta',
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
      author_email='hsogo12600@gmail.com',
      url='http://sourceforge.net/p/gazeparser/',
      license='GNU GPL',
      install_requires=['scipy', 'numpy', 'matplotlib'],
      packages=['GazeParser', 'GazeParser.app'],
      package_data={'GazeParser': ['LICENSE.txt', '*.cfg',
                                   'GazeParserComponents/*.*',
                                   'GazeParserComponents/GazeParserComponents/*.*'],
                    'GazeParser.app': ['img/*.png', 'img/*.ico',
                                       'img/*.gif', '*.cfg']},
      scripts=['GazeParser_post_install.py', 'setup_for_psychopy.py']
      )
