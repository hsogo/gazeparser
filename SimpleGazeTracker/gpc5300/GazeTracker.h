/*!
@file GazeTracker.h
@author Hiroyuki Sogo
@copyright GNU General Public License (GPL) version 3.
@brief Camera-dependent constants are defined.

@date 2012/03/23
- Custom menu is supported.
@date 2012/07/30
- EDITION is defined here.
*/

#define EDITION "GPC5300 Edition"

#ifdef TOSHIBA

#define CAMERA_CONFIG_FILE "CAMERA_TOSHIBA.cfg"

#elif IMPERX

#define CAMERA_CONFIG_FILE "CAMERA.cfg"

#endif


#include "IFCml.h"
#include "../common/GazeTrackerCommon.h"
