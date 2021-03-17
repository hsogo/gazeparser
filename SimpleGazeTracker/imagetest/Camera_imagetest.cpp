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

int g_CurrentImageFileIndex;
std::string g_imageSourceName;
std::vector<std::string> g_ImageSourceNameList;

#define CUSTOMMENU_IMAGEFILE	(MENU_GENERAL_NUM+0)
#define CUSTOMMENU_NUM			1

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
getDefaultConfigFileName: Get default config file name.

@return default config file name.

@date 2021/03/17 created.
*/
const char* getDefaultConfigFileName(void)
{
	return CAMERA_CONFIG_FILE;
}

/*!
Split stirng (helper function)
*/
std::vector<std::string> split_string(std::string str, char del) {
	size_t first = 0;
	size_t last = str.find_first_of(del);

	std::vector<std::string> result;

	while (first < str.size()) {
		std::string subStr(str, first, last - first);

		result.push_back(subStr);

		first = last + 1;
		last = str.find_first_of(del, first);

		if (last == std::string::npos) {
			last = str.size();
		}
	}

	return result;
}

/*!
Load image file
*/
HRESULT load_image_to_buffer(std::string imageSourceName)
{
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


	if (tmpframe.rows != g_CameraHeight || tmpframe.cols != g_CameraWidth) {
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
initCameraParameters: Initialize camera specific parameters

@param[in] buff Pointer to parameter name
@param[in] parambuff Pointer to parameter value (in char)
@return int
@retval S_OK Parameter is successfully initialized.
@retval E_FAIL Parameter is name unknown or value is wrong.
@note This function is necessary when you customize this file for your camera.
@todo check whether number of custom menus are too many.

@date 2020/03/16
Created.
*/
int initCameraParameters(char* buff, char* parambuff)
{
	char *p, *pp;
	double param;

	p = parambuff;
	param = strtod(p, &pp); //paramete is not int but double

	if (strcmp(buff, "IMAGE_SOURCE") == 0)
	{
		g_imageSourceName = p;
	}
	else {
		// unknown parameter
		return E_FAIL;
	}

	return S_OK;
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
	if (g_imageSourceName.empty())
	{
		snprintf(g_errorMessage, sizeof(g_errorMessage), "Image Source is not specified.");
		g_LogFS << "ERROR: image source is not specified" << std::endl;
		return E_FAIL;
	}

	// load image file

	g_ImageSourceNameList = split_string(g_imageSourceName, ',');
	g_CurrentImageFileIndex = 0;

	load_image_to_buffer(g_ImageSourceNameList.at(g_CurrentImageFileIndex));

	//prepare custom menu
	g_CustomMenuNum = CUSTOMMENU_NUM;

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
void saveCameraParameters( std::fstream* fs )
{
	*fs << "# Camera specific parameters for " << EDITION << std::endl;
	*fs << "IMAGE_SOURCE=" << g_imageSourceName << std::endl;

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
	switch (SDLevent->type) {
	case SDL_KEYDOWN:
		switch (SDLevent->key.keysym.sym)
		{
		case SDLK_LEFT:
			switch (currentMenuPosition)
			{
			case CUSTOMMENU_IMAGEFILE:
				g_CurrentImageFileIndex--;
				if (g_CurrentImageFileIndex < 0)
					g_CurrentImageFileIndex = (int)g_ImageSourceNameList.size()-1;
				if (FAILED(load_image_to_buffer(g_ImageSourceNameList.at(g_CurrentImageFileIndex))))
				{
					//clear buffer
					for (int idx = 0; idx < g_CameraWidth*g_CameraHeight; idx++)
					{
						g_frameBuffer[idx] = 0;
					}
				}
				break;
			default:
				break;
			}
			break;

		case SDLK_RIGHT:
			switch (currentMenuPosition)
			{
			case CUSTOMMENU_IMAGEFILE:
				g_CurrentImageFileIndex++;
				if (g_CurrentImageFileIndex >= g_ImageSourceNameList.size())
					g_CurrentImageFileIndex = 0;
				if (FAILED(load_image_to_buffer(g_ImageSourceNameList.at(g_CurrentImageFileIndex))))
				{
					//clear buffer
					for (int idx = 0; idx < g_CameraWidth*g_CameraHeight; idx++)
					{
						g_frameBuffer[idx] = 0;
					}
				}
				break;
			default:
				break;
			}
			break;

		default:
			break;
		}
	default:
		break;
	}

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
	std::stringstream ss;
	ss << "ImageFile(" << g_CurrentImageFileIndex << ")";
	g_MenuString[CUSTOMMENU_IMAGEFILE] = ss.str();

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

