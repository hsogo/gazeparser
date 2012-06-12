.. _config-directory:

GazeParser Configuration file
=============================

GazeParser reads a configuration file named 'GazeParser.cfg' when it is imported.
GazeParser assumes that the configuration file exists in following directory.

========== ================================
Platform   Directory
========== ================================
Win32      %HOMEDRIVE%%HOMEPATH%\GazeParser
Linux      $HOME/GazeParser
========== ================================

If this directory is not found, GazeParser shows following warning message and reads GazeParser.cfg from the application directory.

.. sourcecode:: ipython

    In [1]: import GazeParser
    GazeParser: Warning: configDir (D:\Users\user\GazeParser) does not exist.
    Call GazeParser.Utility.CreateConfigDir() to create configDir.

GazeParser.Utility.createConfigDir() creates the configuration directory and copies configuration files from the application directory.

.. sourcecode:: ipython

    In [3]: import GazeParser.Utility
    In [4]: GazeParser.Utility.createConfigDir()
    GazeParser: ConfigDir is successfully created.
    C:\Python27\lib\site-packages\GazeParser\GazeParser.cfg -> D:\Users\user\GazeParser\GazeParser.cfg
    C:\Python27\lib\site-packages\GazeParser\Tracker.cfg -> D:\Users\user\GazeParser\Tracker.cfg

GazeParser.Utility.createConfigDir() does not overwrite existing files. If you have already have the configuration directory and want to initialize configuration files, call GazeParser.Utility.createConfigDir() with overwrite=True.

.. sourcecode:: ipython

    In [5]: GazeParser.Utility.createConfigDir()
    GazeParser: ConfigDir is exsiting.
    D:\Users\user\GazeParser\GazeParser.cfg is existing.
    D:\Users\user\GazeParser\Tracker.cfg is existing.
    In [6]: GazeParser.Utility.createConfigDir(overwrite=True)
    GazeParser: ConfigDir is exsiting.
    C:\Python27\lib\site-packages\GazeParser\GazeParser.cfg -> D:\Users\user\GazeParser\GazeParser.cfg
    C:\Python27\lib\site-packages\GazeParser\Tracker.cfg -> D:\Users\user\GazeParser\Tracker.cfg
    GazeParser: ConfigDir is successfully created.


