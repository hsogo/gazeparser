.. _config-tracker:

Configure GazeParse.Tracker
=============================================================

============================== ============================================================================ =============
parameter                      description                                                                  method
============================== ============================================================================ =============
IP address                     IP address of the recorder PC.                                               :func:`GazeParser.TrackingTools.BaseController.connect`
Image size                     Size of the image captured by the camera.                                    :func:`GazeParser.TrackingTools.BaseController.setReceiveImageSize`
Preview size                   Size of the preview image on the presentation PC.                            :func:`GazeParser.TrackingTools.BaseController.setPreviewImageSize`
Validation shift               Shift of the target position in the Validation.                              :func:`GazeParser.TrackingTools.BaseController.setPreviewImageSize`
                               If this parameter is 10, target position in the Validation is
                               10 pixel distant from target position in the Calibration
Display of Calibration results If this parameter is true, preview image is shown at the presentation PC.
                               Set this parameter false if you want to hide preview image from participant.
============================== ============================================================================ =============

