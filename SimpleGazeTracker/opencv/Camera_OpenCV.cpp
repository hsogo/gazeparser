/*!
@file Camera.cpp
@author Hiroyuki Sogo
@copyright GNU General Public License (GPL) version 3.
@brief Camera-dependent procedures are defined.

@date 2012/03/23
- Custom menu is supported.
*/

#include "GazeTracker.h"

#include <fstream>
#include <string>

#include <SDL2/SDL.h>

#include <opencv2/highgui/highgui.hpp>
#include <opencv2/opencv.hpp>
#include <opencv2/core/core.hpp>

cv::VideoCapture g_VideoCapture;
SDL_Thread *g_pThread;
bool g_runThread;
double g_prevCaptureTime;

int g_SleepDuration = 0;
double g_FrameRate = 30;
bool g_isThreadMode = false;

int g_cameraID = 0;
double g_Intensity = 1.0;
double g_Exposure = 1.0;
double g_Brightness = 1.0;
double g_Contrast = 1.0;
double g_Gain = 1.0;

#define CAMERA_PARAM_INTENSITY   0
#define CAMERA_PARAM_EXPOSURE    1
#define CAMERA_PARAM_BRIGHTNESS  2
#define CAMERA_PARAM_CONTRAST    3
#define CAMERA_PARAM_GAIN        4
#define CAMERA_PARAM_FRAMERATE   5
#define CAMERA_PARAM_NUM         6

bool g_isParameterSpecified[CAMERA_PARAM_NUM] = {false,false,false,false,false,false};

volatile bool g_NewFrameAvailable = false; /*!< True if new camera frame is grabbed. @note This function is necessary when you customize this file for your camera.*/

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
captureCameraThread: Capture camera image using thread.

*/
int captureCameraThread(void *unused)
{
	cv::Mat frame, monoFrame;
	
	while(g_runThread)
	{
		if(g_VideoCapture.grab())
		{
			g_VideoCapture.retrieve(frame);
			if(frame.channels()==3)
				cv::cvtColor(frame, monoFrame, cv::COLOR_RGB2GRAY);
			else
				monoFrame = frame;
			for(int idx=0; idx<g_CameraWidth*g_CameraHeight; idx++)
			{
				g_frameBuffer[idx] = (unsigned char)monoFrame.data[idx];
			}
			g_NewFrameAvailable = true;
			
			if(g_SleepDuration>0.0)
			{
				sleepMilliseconds(g_SleepDuration);
			}
		}
	}
	
	return 0;
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

	if (strcmp(buff, "SLEEP_DURATION") == 0)
	{
		g_SleepDuration = (int)param;
	}
	else if (strcmp(buff, "USE_THREAD") == 0)
	{
		g_isThreadMode = ((int)param != 0) ? true : false;
	}
	else if (strcmp(buff, "CAMERA_ID") == 0)
	{
		g_cameraID = (int)param;
	}
	else if (strcmp(buff, "FRAME_RATE") == 0)
	{
		g_FrameRate = param;
		g_isParameterSpecified[CAMERA_PARAM_FRAMERATE] = true;
	}
	else if (strcmp(buff, "EXPOSURE") == 0)
	{
		g_Exposure = param;
		g_isParameterSpecified[CAMERA_PARAM_EXPOSURE] = true;
	}
	else if (strcmp(buff, "BRIGHTNESS") == 0)
	{
		g_Brightness = param;
		g_isParameterSpecified[CAMERA_PARAM_BRIGHTNESS] = true;
	}
	else if (strcmp(buff, "CONTRAST") == 0)
	{
		g_Contrast = param;
		g_isParameterSpecified[CAMERA_PARAM_CONTRAST] = true;
	}
	else if (strcmp(buff, "GAIN") == 0)
	{
		g_Gain = param;
		g_isParameterSpecified[CAMERA_PARAM_GAIN] = true;
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

@date 2012/11/05
- Section header [SimpleGazeTrackerOpenCV] is supported.
- spaces and tabs around '=' are removed.
@date 2013/03/15
- Argument "ParamPath" was removed. Use g_ParamPath instead.
@date 2013/10/23
- Camera configuration file is customizable.
 */
int initCamera( void )
{
	double param;

	g_VideoCapture = cv::VideoCapture(g_cameraID);
	if(!g_VideoCapture.isOpened())
	{
		snprintf(g_errorMessage, sizeof(g_errorMessage), "No VideoCapture device was found.");
		g_LogFS << "ERROR: no VideoCapture device was found." << std::endl;
		return E_FAIL;
	}

	g_VideoCapture.set(cv::CAP_PROP_FRAME_WIDTH,g_CameraWidth);
	g_VideoCapture.set(cv::CAP_PROP_FRAME_HEIGHT,g_CameraHeight);

	if((int)g_VideoCapture.get(cv::CAP_PROP_FRAME_WIDTH) != g_CameraWidth)
	{
		snprintf(g_errorMessage, sizeof(g_errorMessage), "Image size (%d, %d) is not supported.", g_CameraWidth, g_CameraHeight);
		return E_FAIL;
	}
	if((int)g_VideoCapture.get(cv::CAP_PROP_FRAME_HEIGHT) != g_CameraHeight)
	{
		snprintf(g_errorMessage, sizeof(g_errorMessage), "Image size (%d, %d) is not supported.", g_CameraWidth, g_CameraHeight);
		return E_FAIL;
	}

	if(g_isParameterSpecified[CAMERA_PARAM_FRAMERATE])
	{
		g_VideoCapture.set(cv::CAP_PROP_FPS,g_FrameRate);
		param = g_VideoCapture.get(cv::CAP_PROP_FPS);
		if(param != g_FrameRate)
			g_LogFS << "WARINING: tried to set FRAMERATE " << g_FrameRate << ", but returned value was " << param << std::endl;
	}
	if(g_isParameterSpecified[CAMERA_PARAM_BRIGHTNESS])
	{
		g_VideoCapture.set(cv::CAP_PROP_BRIGHTNESS,g_Brightness);
		param = g_VideoCapture.get(cv::CAP_PROP_BRIGHTNESS);
		if(param != g_Brightness)
			g_LogFS << "WARINING: tried to set BRIGHTNESS " << g_Brightness << ", but returned value was " << param << std::endl;
	}
	if(g_isParameterSpecified[CAMERA_PARAM_CONTRAST])
	{
		g_VideoCapture.set(cv::CAP_PROP_CONTRAST,g_Contrast);
		param = g_VideoCapture.get(cv::CAP_PROP_CONTRAST);
		if(param != g_Contrast)
			g_LogFS << "WARINING: tried to set CONTRAST " << g_Contrast << ", but returned value was " << param << std::endl;
	}
	if(g_isParameterSpecified[CAMERA_PARAM_GAIN])
	{
		g_VideoCapture.set(cv::CAP_PROP_GAIN,g_Gain);
		param = g_VideoCapture.get(cv::CAP_PROP_GAIN);
		if(param != g_Gain)
			g_LogFS << "WARINING: tried to set GAIN " << g_Gain << ", but returned value was " << param << std::endl;
	}
	if(g_isParameterSpecified[CAMERA_PARAM_EXPOSURE])
	{
		g_VideoCapture.set(cv::CAP_PROP_EXPOSURE,g_Exposure);
		param = g_VideoCapture.get(cv::CAP_PROP_EXPOSURE);
		if(param != g_Exposure)
			g_LogFS << "WARINING: tried to set EXPOSURE " << g_Exposure << ", but returned value was " << param << std::endl;
	}

	if(g_isThreadMode)
	{
		g_runThread = true;
		g_pThread = SDL_CreateThread(captureCameraThread, "CaptureThread", NULL);
		if(g_pThread==NULL)
		{
			snprintf(g_errorMessage, sizeof(g_errorMessage), "Failed to start a new thread for asynchronous capturing.");
			g_LogFS << "ERROR: failed to start thread" << std::endl;
			g_runThread = false;
			return E_FAIL;
		}
		else
		{
			g_LogFS << "Start CameraThread" << std::endl;
		}
	}
	else
	{
		g_prevCaptureTime = getCurrentTime();
		g_LogFS << "Start without threading" << std::endl;
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
int getCameraImage( void )
{
	if(g_isThreadMode)
	{
		if(g_NewFrameAvailable)
		{
			g_NewFrameAvailable = false;
			return S_OK;
		}
	}
	else // non-threading mode
	{
		double t;
		t = getCurrentTime();
		if(t-g_prevCaptureTime > g_SleepDuration)
		{
			
			cv::Mat frame, monoFrame;
			
			if(g_VideoCapture.grab())
			{
				g_VideoCapture.retrieve(frame);
				if(frame.channels()==3)
					cv::cvtColor(frame, monoFrame, cv::COLOR_RGB2GRAY);
				else
					monoFrame = frame;
				for(int idx=0; idx<g_CameraWidth*g_CameraHeight; idx++)
				{
					g_frameBuffer[idx] = (unsigned char)monoFrame.data[idx];
				}
				g_prevCaptureTime = getCurrentTime();
				return S_OK;
			}
		}
	}

	return E_FAIL;
}

/*!
cleanupCamera: release camera resources.

@return No value is returned.

@note This function is necessary when you customize this file for your camera.
*/
void cleanupCamera()
{
	if(g_isThreadMode && g_runThread){
		g_runThread = false;
		SDL_WaitThread(g_pThread, NULL);
		g_LogFS << "Camera capture thread is stopped." << std::endl;
	}
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
	*fs << "SLEEP_DURATION=" << g_SleepDuration << std::endl;
	*fs << "CAMERA_ID=" << g_cameraID << std::endl;
	*fs << "USE_THREAD=" << ((g_isThreadMode) ? 1: 0) << std::endl;

	if (g_isParameterSpecified[CAMERA_PARAM_FRAMERATE])
		*fs << "FRAME_RATE=" << g_FrameRate << std::endl;
	else
		*fs << "#FRAME_RATE=" << std::endl;

	if (g_isParameterSpecified[CAMERA_PARAM_EXPOSURE])
		*fs << "EXPOSURE=" << g_Exposure << std::endl;
	else
		*fs << "#EXPOSURE=" << std::endl;

	if (g_isParameterSpecified[CAMERA_PARAM_BRIGHTNESS])
		*fs << "BRIGHTNESS=" << g_Brightness << std::endl;
	else
		*fs << "#BRIGHTNESS=" << std::endl;

	if (g_isParameterSpecified[CAMERA_PARAM_CONTRAST])
		*fs << "CONTRAST=" << g_Contrast << std::endl;
	else
		*fs << "#CONTRAST=" << std::endl;

	if (g_isParameterSpecified[CAMERA_PARAM_GAIN])
		*fs << "GAIN=" << g_Gain << std::endl;
	else
		*fs << "#GAIN=" << std::endl;

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
void updateCustomMenuText( void )
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
unsigned int getCameraSpecificData( void )
{
	//no custom input
	return 0;
}
