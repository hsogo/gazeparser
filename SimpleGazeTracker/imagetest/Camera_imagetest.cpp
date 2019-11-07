/*!
@file Camera.cpp
@author Hiroyuki Sogo
@copyright GNU General Public License (GPL) version 3.
@brief Camera-dependent procedures are defined.

*/

#define _CRT_SECURE_NO_DEPRECATE

#include <atlbase.h>
#include "GazeTracker.h"

#include <fstream>
#include <string>

#include "opencv2/opencv.hpp"


unsigned char* g_TmpFrameBuffer; /*!< Temporary buffer to hold camera image until CallBackProc() is called.*/
volatile bool g_NewFrameAvailable = false; /*!< True if new camera frame is grabbed. @note This function is necessary when you customize this file for your camera.*/
DWORD g_DigitalInput = 0;

/*!
getEditionString: Get edition string.

@return edition string.

@date 2012/07/30 created.
*/
const char* getEditionString(void)
{
	return EDITION;
}

/*!
initCamera: Initialize camera.

Read parameters from the configuration file, start camera and set callback function.
@attention If there are custom camera menu items, number of custom menu items must be set to g_CustomMenuNum in this function.

@return int
@retval S_OK Camera is successfully initialized.
@retval E_FAIL Initialization is failed.
@note This function is necessary when you customize this file for your camera.
@todo check whether number of custom menus are too many.

@date 2013/03/15
- Argument "ParamPath" was removed. Use g_ParamPath instead.
@date 2013/05/27 a new option, "OUTPUT_DIGITAL_INPUT", was appended.
@date 2013/07/25 support for Wow64 environment.
@date 2013/10/23
- Camera configuration file is customizable.
 */
int initCamera(void)
{
	std::fstream fs;
	std::string fname;
	std::string imageSourceName;
	char *p, *pp;
	char buff[1024];
	double param;
	bool isInSection = true; //default is True to support old config file

	fname = g_ParamPath.c_str();
	fname.append(PATH_SEPARATOR);
	if (g_CameraConfigFileName == "") {
		g_CameraConfigFileName = CAMERA_CONFIG_FILE;
		checkAndCopyFile(g_ParamPath, CAMERA_CONFIG_FILE, g_AppDirPath);
	}
	fname.append(g_CameraConfigFileName.c_str());

	fs.open(fname.c_str(), std::ios::in);
	if (fs.is_open())
	{
		g_LogFS << "Open camera configuration file (" << fname << ")" << std::endl;
		while (fs.getline(buff, sizeof(buff) - 1))
		{
			if (buff[0] == '#') continue;

			//in Section "[SimpleGazeTrackerImageTest]"
			if (buff[0] == '[') {
				if (strcmp(buff, "[SimpleGazeTrackerImageTest]") == 0) {
					isInSection = true;
				}
				else
				{
					isInSection = false;
				}
				continue;
			}

			if (!isInSection) continue; //not in section


			//Check options.
			//If "=" is not included, this line is not option.
			if ((p = strchr(buff, '=')) == NULL) continue;

			//remove space/tab
			*p = '\0';
			while (*(p - 1) == 0x09 || *(p - 1) == 0x20)
			{
				p--;
				*p = '\0';
			}
			while (*(p + 1) == 0x09 || *(p + 1) == 0x20) p++;
			param = strtod(p + 1, &pp); //parameter is not int but double

			if (strcmp(buff, "IMAGE_SOURCE") == 0)
			{
				imageSourceName = p + 1;
			}
		}
		fs.close();
	}
	else {
		snprintf(g_errorMessage, sizeof(g_errorMessage), "Failed to open camera configuration file (%s)", fname.c_str());
		g_LogFS << "ERROR: failed to open camera configuration file (" << fname << ")" << std::endl;
		return E_FAIL;
	}

	if (g_isOutputCameraSpecificData == USE_CAMERASPECIFIC_DATA)
	{
		g_LogFS << "Output digital input of GPC5300" << std::endl;
	}
	if (imageSourceName.empty())
	{
		snprintf(g_errorMessage, sizeof(g_errorMessage), "Image Source is not specified.");
		g_LogFS << "ERROR: image source is not specified" << std::endl;
		return E_FAIL;
	}

	// load image file
	cv::Mat frame, tmpframe;
    // 0=read as monochrome
	tmpframe = cv::imread(imageSourceName.c_str(), 0);

	if (tmpframe.empty()) {
		// try data directory
		tmpframe = cv::imread(joinPath(g_DataPath.c_str(), imageSourceName.c_str()), 0);

		if (tmpframe.empty()) {
			snprintf(g_errorMessage, sizeof(g_errorMessage), "Failed to load image %s.", imageSourceName.c_str());
			g_LogFS << "ERROR: failed to load image " << imageSourceName << std::endl;
			return E_FAIL;
		}
	}

	g_LogFS << "Load image " << imageSourceName << std::endl;


	if(tmpframe.rows != g_CameraHeight || tmpframe.cols != g_CameraWidth){
		cv::resize(tmpframe, frame, cv::Size(g_CameraWidth, g_CameraHeight));
	}
	else {
		frame = tmpframe;
	}

	for (int idx = 0; idx < g_CameraWidth*g_CameraHeight; idx++)
	{
		g_frameBuffer[idx] = (unsigned char)frame.data[idx];
	}

	return S_OK;
}

/*!
getCameraImage: Get new camera image.

@return int
@retval S_OK New frame is available.
@retval E_FAIL There is no new frame.
@note This function is necessary when you customize this file for your camera.
*/
int getCameraImage(void)
{
	return S_OK;
}

/*!
cleanupCamera: release camera resources.

@return No value is returned.

@note This function is necessary when you customize this file for your camera.
*/
void cleanupCamera()
{
	// nothing to do
	return;
}

/*!
saveCameraParameters: Save current camera parameters to the camera configuration file.

@param[in] ParamPath Path to the camera configuration file.
@return No value is returned.
@note This function is necessary when you customize this file for your camera.

@date 2013/03/15
- Argument "ParamPath" was removed. Use g_ParamPath instead.
 */
void saveCameraParameters(void)
{
	// no custom parameters for this camera
	return;
}

/*!
customCameraMenu: Process camera-dependent custom menu items. If there is no custom menu items, this function do nothing.

Your camera may have some parameters which you want to adjust with previewing camera image.
In such cases, write nesessary codes to adjust these parameters in this function.
This function is called when left or right cursor key is pressed.

@param[in] SDLevent Event object.
@param[in] currentMenuPosition Current menu position.
@return int
@retval S_OK
@retval E_FAIL
@note This function is necessary when you customize this file for your camera.
*/
int customCameraMenu(SDL_Event* SDLevent, int currentMenuPosition)
{
	// no custom menu for this camera
	return S_OK;
}


/*!
updateCustomMenuText: update menu text of custom camera menu items.

Your camera may have some parameters which you want to adjust with previewing camera image.
If your custom menu need to update its text, write nessesary codes to update text in this function.
This function is called from initD3D() at first, and from MsgProc() when left or right cursor key is pressed.

@return No value is returned.
@note This function is necessary when you customize this file for your camera.
*/
void updateCustomMenuText(void)
{
	// no custom parameters for this camera
	return;
}

/*!
getCameraSpecificData: return Camera specific data.

If your camera has input port, you can insert its value to the SimpleGazeTracker data file
using this function. Currently, only single value (unsigned int) can be returned.
@date 2013/05/27 created.
*/
unsigned int getCameraSpecificData(void)
{
	return 0;
}

