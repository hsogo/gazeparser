/*!
@file GazeTracker.h
@author Hiroyuki Sogo
@copyright GNU General Public License (GPL) version 3.
@brief Camera-dependent constants are defined.

@date 2012/03/23
- Custom menu is supported.
*/
#ifdef _WIN32
#pragma comment(lib,"C:\\Program Files\\Interface\\GPC5300\\lib\\IfCml.lib")
#endif

#ifdef TOSHIBA

#define CAMERA_CONFIG_FILE "CAMERA_TOSHIBA.cfg"

#elif IMPERX

#define CAMERA_CONFIG_FILE "CAMERA.cfg"

#endif

#include "GazeTrackerCommon.h"
