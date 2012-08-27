
Install GazeParser (Linux)
==================================

Dependencies
-------------------------

**Python 2.5, 2.6 or 2.7** is necessary to use GazePaser.
The author mainly uses Python 2.7.
GazeParser depends on following Python modules.

- **numpy**
- **scipy**
- **matplotlib**
- **PIL (Python Imaging Library)**
- **Tkinter (Python-TK)**
- **VisionEgg** and/or **PsychoPy** (experimental control library)

Following libraries are necessary to record gaze position.

- libsdl
- libsdl-net
- libsdl-ttf
- opencv

Download
---------------------------

GazeParser installer can be downloaded from following page.

`<http://sourceforge.net/projects/gazeparser/files/>`_

Install either of these files to computers which you plan to use stimulus presentation and data analysis.

- `GazeParser-0.5.2-py2.7.egg <http://sourceforge.net/projects/gazeparser/files/0.5.2/GazeParser-0.5.2-py2.7.egg>`_ : python egg file
- `GazeParser-0.5.2.zip <http://sourceforge.net/projects/gazeparser/files/0.5.2/GazeParser-0.5.2.zip>`_ : zipped file

If you plan to record gaze data, download following source code and build SimpleGazeTracker.
**Currently, SimpleGazeTracker for Linux is distributed only in source code**.

- `SimpleGazeTracker-0.5.1.tar.gz <http://sourceforge.net/projects/gazeparser/files/0.5.1/SimpleGazeTracker-0.5.1.tar.gz>`_

Build SimpleGazeTracker (Ubuntu 12.04 desktop)
-----------------------------------------------

OpenCV and SDL are necessary to build SimpleGazeTracker.
Install following packages in advance.
Other packages may be necessary depending on your environment.

- libopencv-dev
- libsdl1.2-dev
- libsdl-net1.2-dev
- libsdl-ttf2.0-dev

.. code-block:: bash

    ~$ sudo apt-get install libopencv-dev

Expand gzipped tarball and change working directory to the created directory.

.. code-block:: bash

    ~$ tar zxvf SimpleGazeTracker-x.x.x.tar.gz
    ~$ cd SimpleGazeTracker-x.x.x

Execute 'configure' script.  If error message is displayed, check missing files and install corresponding packages.
Ubuntu package search (`<http://packages.ubuntu.com/>`) is useful to search contents of packages.

.. code-block:: bash

    ~/SimpleGazeTracker-x.x.x$ ./configure

If 'configure' script finish successfully, build and install SimpleGazeTracker.

.. code-block:: bash

    ~/SimpleGazeTracker-x.x.x$ make
    ~/SimpleGazeTracker-x.x.x$ sudo make install

By default, simplegazetracker is installed at /usr/local/simplegazetracker.
Type as following to comfirm SimpleGazeTracker has been correctly installed.
If it works correctly, ~/SimpleGazeTracker directory is created at the home directory.
SimpleGazeTracker will show error message and terminate automatically if you have not connected camera unit in advance.

.. code-block:: bash

    ~/SimpleGazeTracker-x.x.x$ /usr/local/simplegazetracker/simplegazetracker


