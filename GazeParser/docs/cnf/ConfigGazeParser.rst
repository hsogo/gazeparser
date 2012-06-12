.. _config-gazeparser:

Configure GazeParser
=============================================================

Parameters
------------------------------

=============================== =======================================================================================
Parameter                       Description
=============================== =======================================================================================
RECORDED_EYE                    Specify recorded eye(s). 'L' for the left eye only, 'R' for the right eye only, or 'B' 
                                for binocular recording.
SCREEN_ORIGIN                   Specify the origin of the presentation screen. 'Center', 'BottomLeft' or 'TopLeft'.
TRACKER_ORIGIN                  Specify the origin of the tracker origin. Usually, this parameter is coincide with 
                                SCREEN_ORIGIN
SCREEN_WIDTH                    Specify the width of the presentation screen in px. (e.g. 1024 for XGA screen)
SCREEN_HEIGHT                   Specify the height of the presentation screen in px. (e.g. 768 for XGA screen)
DOTS_PER_CENTIMETER_H           Specify how many dots are horizontally arranged in one centimeter on the presentation 
                                screen. (Screen width[cm] / Screen width[px])
DOTS_PER_CENTIMETER_V           Specify how many dots are vertically arranged in one centimeter on the presentation 
                                screen. (Screen height[cm] / Screen height[px])
VIEWING_DISTANCE                Specify the distance between the presentation screen and the participant's eye. 
                                The unit is cm.
SACCADE_VELOCITY_THRESHOLD      Eye movements faster than this value is considered as saccadic eye movement.
SACCADE_ACCELERATION_THRESHOLD  Eye movements accerelating quicker than this value is considered as saccadic eye 
                                movement.
SACCADE_MINIMUM_DURATION        Specify minimum saccade duration in milliseconds. Saccadic eye movements shorter than 
                                this value is marged to neighboring fixations.
FIXATION_MINIMUM_DURATION       Specify minimum fixation duration in milliseconds. Fixational eye movements shorter than
                                this value is marged to neighboring saccades.
BLINK_MINIMUM_DURATION          Specify minimum blink duration in milliseconds. A lack of data longer than this value 
                                is considered as a blink.
FILTER_TYPE                     Specify smoothing filter for noise reduction. 'identity' for no filtering, 'ma' for 
                                moving average, 'butter' for butterworth low-pass filter, or 'butter-filtfilt' for 
                                forward-backward butterworth filter.
FILTER_WN                       If FILTER_TYPE is 'butter' or 'butter-filtfilt', the cutoff frequency is specifiyed by 
                                this parameter. The range of the value is from 0.0 to 1.0.  1.0 means the half of the 
                                sampling frequency.
FILTER_SIZE                     If FILTER_SIZE is 'ma', the range of moving average is specified by this parameer.
FILTER_ORDER                    If FILTER_TYPE is 'butter' or 'butter-filtfilt', the order of the filter is specified 
                                by this parameter.
=============================== =======================================================================================

