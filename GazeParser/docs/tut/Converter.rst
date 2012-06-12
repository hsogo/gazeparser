How to generate GazeParser data file
=======================================

GazeParser.Converter module includes conversion tools to generate GazeParser data file.
Currently, GazeTracker data file (\*.csv) and Eyelink EDF file (\*.edf) are supported.
To generate GazePaser datafile from GazeParser.Tracker data file, use :func:`~GazeParser.Converter.TrackerToGazeParser` method.
In the following example, 'data.csv' is a GazeParser.Tracker data file to be converted. ::

    import GazeParser.Converter
    GazeParser.Converter.TrackerToGazeParser('data.csv')

If this method run successfully, a file named 'data.db' is generated.
This file can be read with GazeParser.load() method.
TrackerToGazeParser accepts following optional parameters.

================= =======================================================================
Name               Description
================= =======================================================================
overwrite         By default, TrackerToGazeParser does not overwrite existing file.
                  If overwrite=True is specified, TrackerToGazeParser overwrites 
                  existing file. Default value is *False*.
config            Specify a GazeParser.Configuration file where conversion parameters
                  are defined.  If no configuration file is specified (i.e. config=None),
                  TrackerToGazeParser uses default configuration file.
                  See :class:`~GazeParser.Configuration` for detail.
                  Default value is *None*
useFileParameters If this parameter is True, conversion parameters are overwritten by 
                  parameters recorded in GazeParser.Tracker data file.
                  See :class:`~GazeParser.TrackingTools` for detail.
                  Default value is *None*
================= =======================================================================

.. note:: Currently, GazeParser.Tracking supports only monolular recording.
          Right eye's data is a copy of left eye's data when 'B' is specified.

If you want to convert an Eyelink EDF file to GazeParser data file, use :func:`~GazeParser.Converter.EyelinkToGazeParser` method. ::

    import GazeParser.Converter
    GazeParser.Converter.EyelinkToGazeParser('data.edf')

EyelinkToGazeParser accepts the same parameters as those of TrackerToGazeParser except useFileParameters.


.. using e002t.db in this example.
