/*!
@file Camera.cpp
@author Hiroyuki Sogo
@copyright GNU General Public License (GPL) version 3.
@brief Camera-dependent procedures are defined.

@date 2012/03/23
- Custom menu is supported.
*/

#define _CRT_SECURE_NO_DEPRECATE

#include "GazeTracker.h"

#include <fstream>
#include <string>

#include <SDL.h>

#include <opencv2/highgui/highgui.hpp>
#include <opencv2/opencv.hpp>
#include <opencv2/core/core.hpp>

cv::VideoCapture g_VideoCapture;
SDL_Thread *g_pThread;
bool g_runThread;

volatile bool g_NewFrameAvailable = false; /*!< True if new camera frame is grabbed. @note This function is necessary when you customize this file for your camera.*/

int captureCameraThread(void *unused)
{
	cv::Mat frame, monoFrame;

	while(g_runThread)
	{
		if(g_VideoCapture.grab())
		{
			g_VideoCapture.retrieve(frame);
			if(frame.channels()==3)
				cv::cvtColor(frame, monoFrame, CV_RGB2GRAY);
			else
				monoFrame = frame;
			for(int idx=0; idx<g_CameraWidth*g_CameraHeight; idx++)
			{
				g_frameBuffer[idx] = monoFrame.data[idx];
			}
			g_NewFrameAvailable = true;
		}
	}

	return 0;
}


/*!
initCamera: Initialize camera.

Read parameters from the configuration file, start camera and set callback function.
@attention If there are custom camera menu items, number of custom menu items must be set to g_CustomMenuNum in this function.

@param[in] ParamPath Path to the camera configuration file.
@return int
@retval S_OK Camera is successfully initialized.
@retval E_FAIL Initialization is failed.
@note This function is necessary when you customize this file for your camera.
@todo check whether number of custom menus are too many.
 */
int initCamera( const char* ParamPath )
{
	g_VideoCapture = cv::VideoCapture(0);
	if(!g_VideoCapture.isOpened())
	{
		g_LogFS << "ERROR: no VideoCapture device is found.\n";
		return E_FAIL;
	}

	g_VideoCapture.set(CV_CAP_PROP_FRAME_WIDTH,g_CameraWidth);
	g_VideoCapture.set(CV_CAP_PROP_FRAME_HEIGHT,g_CameraHeight);

	if((int)g_VideoCapture.get(CV_CAP_PROP_FRAME_WIDTH) != g_CameraWidth)
	{
		g_LogFS << "ERROR: wrong camera size (" << g_CameraWidth << "," << g_CameraHeight << ")\n";
		return E_FAIL;
	}
	if((int)g_VideoCapture.get(CV_CAP_PROP_FRAME_HEIGHT) != g_CameraHeight)
	{
		g_LogFS << "ERROR: wrong camera size (" << g_CameraWidth << "," << g_CameraHeight << ")\n";
		return E_FAIL;
	}

	g_runThread = true;
	g_pThread = SDL_CreateThread(captureCameraThread, NULL);
	if(g_pThread==NULL)
	{
		g_LogFS << "ERROR: failed to start thread\n";
		g_runThread = false;
		return E_FAIL;
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
	if(g_NewFrameAvailable)
	{
		g_NewFrameAvailable = false;
		return S_OK;
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
	g_runThread = false;
	SDL_WaitThread(g_pThread, NULL);
}

/*!
saveCameraParameters: Save current camera parameters to the camera configuration file.

@param[in] ParamPath Path to the camera configuration file.
@return No value is returned.
@note This function is necessary when you customize this file for your camera.
 */
void saveCameraParameters(const char* ParamPath)
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
void updateCustomMenuText( void )
{
	// no custom parameters for this camera
	return;
}
