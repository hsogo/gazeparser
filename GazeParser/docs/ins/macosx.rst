
Install GazeParser (Mac OS X)
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

- **GazeParser-x.x.x-pyx.x.egg**: python egg file
- **GazeParser-x.x.x.zip**: zipped file

If you plan to record gaze data, download following source code and build SimpleGazeTracker.
**Currently, SimpleGazeTracker for Mac OS X is distributed only in source code**.

- **simplegazetracker-x.x.x.tar.gz**

Build SimpleGazeTracker (Mac OS X Lion)
-----------------------------------------------

Install Xcode and command line tools in advance.
Following tools and libraries are necessary to build SimpleGazeracker.

- pkg-config
- cmake
- ffmpeg
- OpenCV
- SDL
- SDL_net
- SDL_ttf

In a testing environment, pkg-config was installed via macports.
Binary distribution of cmake was used.
Other libraries were built from source in the following order.

1. SDL
2. SDL_net
3. SDL_ttf
4. ffmpeg
5. OpenCV

.. warning::
    By default, current version of SDL_net is built without TCP_NODELAY option in Mac OS X.
    This **severely spoil performance of SimpleGazeTraqcker**.
    To build SDL_net with TCP_NODELAY option, edit SDLnetsys.h to force to include netinet/tcp.h.
    
    As to SDL_net-1.2.8, delete following highlighted lines in SDLnetsys.h to include netinet/tcp.h in Mac OS X.
    
    .. code-block:: c
        :emphasize-lines: 4,6
    
        #ifndef __BEOS__
        #include <arpa/inet.h>
        #endif
        #ifdef linux /* FIXME: what other platforms have this? */
        #include <netinet/tcp.h>
        #endif
        #include <sys/socket.h>
        #include <net/if.h>
    
    Don't forget enable **ffmpeg** when configuring OpenCV.
    If you want to use IEEE1394 camera, enable **dc1394**.

Now you are ready to build SimpleGazeTracker.
Expand gzipped tarball and change working directory to the created directory.

.. code-block:: bash

    ~$ tar zxvf simplegazetracker-x.x.x.tar.gz
    ~$ cd simplegazetracker-x.x.x

Execute 'configure' script.  If error message is displayed, check missing files and install corresponding packages.
Ubuntu package search (`<http://packages.ubuntu.com/>`) is useful to search contents of packages.

.. code-block:: bash

    ~/simplegazetracker-x.x.x$ ./configure

If 'configure' script finish successfully, build and install SimpleGazeTracker.

.. code-block:: bash

    ~/simplegazetracker-x.x.x$ make
    ~/simplegazetracker-x.x.x$ sudo make install

By default, simplegazetracker is installed at /usr/local/simplegazetracker.
Type as following to comfirm SimpleGazeTracker has been correctly installed.
If it works correctly, ~/SimpleGazeTracker directory is created at the home directory.
SimpleGazeTracker will show error message and terminate automatically if you have not connected camera unit in advance.

.. code-block:: bash

    ~/simplegazetracker-x.x.x$ /usr/local/simplegazetracker/simplegazetracker


