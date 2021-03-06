/*!
@file Camera.cpp
@author Hiroyuki Sogo
@copyright GNU General Public License (GPL) version 3.
@brief Camera-dependent procedures are defined.

@date 2013/02/21
- Created.
*/

#define _CRT_SECURE_NO_DEPRECATE


#include "GazeTracker.h"
#include "FlyCapture2.h"

#include "opencv2/opencv.hpp"
#include "opencv2/core/core.hpp"
#include "opencv2/highgui/highgui.hpp"

#include <fstream>
#include <string>

FlyCapture2::Camera g_FC2Camera;
FlyCapture2::PGRGuid g_FC2CameraGUID;
FlyCapture2::Image g_rawImage;

int g_CameraN = 0;
int g_OffsetX = 0;
int g_OffsetY = 0;
int g_CameraMode = 1;
float g_FrameRate = 200;
float g_Shutter = 4.0;

SDL_Thread *g_pThread;
bool g_runThread;

int g_SleepDuration = 0;
bool g_isThreadMode = true;

bool g_UseBlurFilter = true;
int g_BlurFilterSize = 3;
cv::Mat g_TmpImg;

volatile bool g_NewFrameAvailable = false; /*!< True if new camera frame is grabbed. @note This function is necessary when you customize this file for your camera.*/

#define CUSTOMMENU_SHUTTER		(MENU_GENERAL_NUM+0)
#define CUSTOMMENU_NUM			1

// for debugging
// FlyCapture2::TimeStamp g_timestamp[5000];


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

@date 2013/03/29 created.
*/
int captureCameraThread(void *unused)
{
	FlyCapture2::Error error;
	FlyCapture2::ImageMetadata metadata;

	// for debugging
	//int i = 0;

	while(g_runThread)
	{
		error = g_FC2Camera.RetrieveBuffer( &g_rawImage );
		if(error == FlyCapture2::PGRERROR_OK)
		{
			metadata = g_rawImage.GetMetadata();
			// for debugging
			//g_timestamp[i] = g_rawImage.GetTimeStamp();
			//i = (i+1)%5000;
			memcpy(g_frameBuffer, g_rawImage.GetData(), g_CameraWidth*g_CameraHeight*sizeof(unsigned char));
			if(g_UseBlurFilter){
				//cv::GaussianBlur takes approx 1.9ms while cv::blur takes only approx 0.9ms in i7-2600k machine.
				//cv::GaussianBlur(g_TmpImg, g_TmpImg, cv::Size(g_BlurFilterSize,g_BlurFilterSize),0,0);
				cv::blur(g_TmpImg, g_TmpImg, cv::Size(g_BlurFilterSize,g_BlurFilterSize));
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

	if (strcmp(buff, "CAMERA_N") == 0)
	{
		g_CameraN = (int)param;
	}
	else if (strcmp(buff, "OFFSET_X") == 0)
	{
		g_OffsetX = (int)param;
	}
	else if (strcmp(buff, "OFFSET_Y") == 0)
	{
		g_OffsetY = (int)param;
	}
	else if (strcmp(buff, "FRAME_RATE") == 0)
	{
		g_FrameRate = (float)param;
	}
	else if (strcmp(buff, "SHUTTER") == 0)
	{
		g_Shutter = (float)param;
	}
	else if (strcmp(buff, "CAMERA_MODE") == 0)
	{
		g_CameraMode = (int)param;
	}
	else if (strcmp(buff, "SLEEP_DURATION") == 0)
	{
		g_SleepDuration = (int)param;
	}
	else if (strcmp(buff, "USE_THREAD") == 0)
	{
		if ((int)param != 0)
		{
			g_isThreadMode = true;
		}
		else
		{
			g_isThreadMode = false;
		}
	}
	else if (strcmp(buff, "BLUR_FILTER_SIZE") == 0)
	{
		g_BlurFilterSize = (int)param;
		if (g_BlurFilterSize > 1) g_UseBlurFilter = true;
		else g_UseBlurFilter = false;
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

@param[in] ParamPath Path to the camera configuration file.
@return int
@retval S_OK Camera is successfully initialized.
@retval E_FAIL Initialization is failed.
@note This function is necessary when you customize this file for your camera.
@todo check whether number of custom menus are too many.

@date 2013/03/15
- Argument "ParamPath" was removed. Use g_ParamPath instead.
@date 2013/03/29
- Threading mode is added.
- USE_THREAD and SLEEP_DURATION options are supported.
@date 2013/10/23
- Camera configuration file is customizable.
 */
int initCamera( void )
{
	FlyCapture2::Error error;
	FlyCapture2::Mode mode;

	// create cv::Mat for blurring
	if(g_UseBlurFilter){
		g_LogFS << "BlurFilter: use blur filter (size=" << g_BlurFilterSize << ")." << std::endl;
		g_TmpImg = cv::Mat(g_CameraHeight,g_CameraWidth,CV_8UC1,g_frameBuffer);
	}else{
		g_LogFS << "BlurFilter: use raw image." << std::endl;
	}

	// get camera mode
	switch(g_CameraMode)
	{
	case 0:
		mode = FlyCapture2::MODE_0;
		break;

	case 1:
		mode = FlyCapture2::MODE_1;
		break;

	default:
		snprintf(g_errorMessage, sizeof(g_errorMessage), "Only MODE_0 and MODE_1 are supported. \nCheck vaule of CAMERA_MODE parameter");
		g_LogFS << "ERROR: only MODE_0 and MODE_1 are supported." << std::endl;
		return E_FAIL;
	}

	//Init FlyCapture2 camera

	FlyCapture2::BusManager busMgr;
	unsigned int numCameras;
	error = busMgr.GetNumOfCameras(&numCameras);
	if(error != FlyCapture2::PGRERROR_OK)
	{
		snprintf(g_errorMessage, sizeof(g_errorMessage), "Failed to find FlyCapture2 camera.");
		g_LogFS << "ERROR: failed to get FlyCapture2 camera" << std::endl;
		return E_FAIL;
	}

	if(numCameras<=0){
		snprintf(g_errorMessage, sizeof(g_errorMessage), "Failed to find FlyCapture2 camera.");
		g_LogFS << "ERROR: no FlyCapture2 camera was found" << std::endl;
		return E_FAIL;
	}

	error = busMgr.GetCameraFromIndex(g_CameraN, &g_FC2CameraGUID);
	if(error != FlyCapture2::PGRERROR_OK)
	{
		snprintf(g_errorMessage, sizeof(g_errorMessage), "Failed to get the first Flycapture2 camera.");
		g_LogFS << "ERROR: Could not get FlyCapture2 camera from index" << std::endl;
		return E_FAIL;
	}

	// Connect to a camera
	error = g_FC2Camera.Connect(&g_FC2CameraGUID);
	if (error != FlyCapture2::PGRERROR_OK)
	{
		snprintf(g_errorMessage, sizeof(g_errorMessage), "Failed to connect to Flycapture2 camera.");
		g_LogFS << "ERROR: failed to connect to FlyCapture2 camera" << std::endl;
		return E_FAIL;
	}

	FlyCapture2::FC2Config Config;
	FlyCapture2::Format7ImageSettings imageSettings;
	FlyCapture2::Format7PacketInfo packetInfo;
	FlyCapture2::Property prop;
	FlyCapture2::PropertyInfo propInfo;
	FlyCapture2::EmbeddedImageInfo eInfo;
	unsigned int packetSize;
	float percentage;
	bool settingsAreValid;

	//set Format7 configuration
	g_FC2Camera.GetFormat7Configuration(&imageSettings, &packetSize, &percentage);
	if (error != FlyCapture2::PGRERROR_OK)
	{
		snprintf(g_errorMessage, sizeof(g_errorMessage), "Failed to get \"Format7\" cofiguration of the Flycapture2 camera.");
		g_LogFS << "ERROR: failed to get \"Format7\" camera configuration." << std::endl;
		return E_FAIL;
	}
	imageSettings.mode = mode;
	imageSettings.width=g_CameraWidth;
	imageSettings.height=g_CameraHeight;
	imageSettings.offsetX = g_OffsetX;
	imageSettings.offsetY = g_OffsetY;
	imageSettings.pixelFormat = FlyCapture2::PIXEL_FORMAT_RAW8;
	error = g_FC2Camera.ValidateFormat7Settings(&imageSettings, &settingsAreValid, &packetInfo);
	if (error != FlyCapture2::PGRERROR_OK)
	{
		snprintf(g_errorMessage, sizeof(g_errorMessage), "Failed to validate camera format.\nCheck CAMERA_WIDTH, CAMERA_HEIGHT, OFFSET_X, OFFSET_Y and CAMERA_MODE.");
		g_LogFS << "ERROR: could not validate \"Format7\" camera format.  Check CAMERA_WIDTH, CAMERA_HEIGHT, OFFSET_X, OFFSET_Y and CAMERA_MODE." << std::endl;
		return E_FAIL;
	}
	if(!settingsAreValid)
	{
		snprintf(g_errorMessage, sizeof(g_errorMessage), "Camera format is invalid.\nCheck CAMERA_WIDTH, CAMERA_HEIGHT, OFFSET_X, OFFSET_Y and CAMERA_MODE.");
		g_LogFS << "ERROR: invalid \"Format7\" camera format. Check CAMERA_WIDTH, CAMERA_HEIGHT, OFFSET_X, OFFSET_Y and CAMERA_MODE." << std::endl;
		return E_FAIL;
	}
	error = g_FC2Camera.SetFormat7Configuration(&imageSettings, packetInfo.recommendedBytesPerPacket);
	if (error != FlyCapture2::PGRERROR_OK)
	{
		snprintf(g_errorMessage, sizeof(g_errorMessage), "Failed to configure camera format.");
		g_LogFS << "ERROR: failed to configure \"Format7\" camera format." << std::endl;
		return E_FAIL;
	}
	//error = g_FC2Camera.GetFormat7Configuration(&imageSettings, &packetSize, &percentage);

	//set frame rate (manual mode, absolute value)
	prop.type = FlyCapture2::FRAME_RATE;
	prop.autoManualMode = false;
	prop.onOff = true;
	prop.absControl = true;
	prop.absValue = g_FrameRate;
	error = g_FC2Camera.SetProperty(&prop);
	if (error != FlyCapture2::PGRERROR_OK)
	{
		snprintf(g_errorMessage, sizeof(g_errorMessage), "Failed to set frame rate.\nCheck FRAME_RATE.");
		g_LogFS << "ERROR: failed to set frame rate." << std::endl;
		return E_FAIL;
	}
	error = g_FC2Camera.GetProperty(&prop);
	if (error != FlyCapture2::PGRERROR_OK)
	{
		snprintf(g_errorMessage, sizeof(g_errorMessage), "Failed to validate frame rate.");
		g_LogFS << "ERROR: failed to get frame rate." << std::endl;
		return E_FAIL;
	}
	else
	{
		g_LogFS << "Frame rate is set to " << prop.absValue << " fps." << std::endl;
	}

	//set shutter speed
	prop.type = FlyCapture2::SHUTTER;
	prop.autoManualMode = false;
	prop.onOff = true;
	prop.absControl = true;
	prop.absValue = g_Shutter;
	error = g_FC2Camera.SetProperty(&prop);
	if (error != FlyCapture2::PGRERROR_OK)
	{
		g_LogFS << "ERROR: failed to set shutter speed." << std::endl;
		return E_FAIL;
	}
	error = g_FC2Camera.GetProperty(&prop);
	if (error != FlyCapture2::PGRERROR_OK)
	{
		g_LogFS << "ERROR: failed to get shutter speed." << std::endl;
		return E_FAIL;
	}
	else
	{
		g_LogFS << "Shutter is set to " << prop.absValue << " ms." << std::endl;
	}

	/*
	// disable auto exposure
	prop.type = FlyCapture2::AUTO_EXPOSURE;
	prop.autoManualMode = false;
	prop.onOff = true;
	prop.absControl = true;
	prop.absValue = 1.3;
	error = g_FC2Camera.SetProperty(&prop);
	if (error != FlyCapture2::PGRERROR_OK)
	{
		g_LogFS << "ERROR: failed to disable AUTO_EXPOSURE." << std::endl;
		return E_FAIL;
	}

	// disable auto gain
	prop.type = FlyCapture2::GAIN;
	prop.autoManualMode = false;
	prop.onOff = true;
	prop.absControl = true;
	prop.absValue = 10.0;
	error = g_FC2Camera.SetProperty(&prop);
	if (error != FlyCapture2::PGRERROR_OK)
	{
		g_LogFS << "ERROR: failed to disable AUTO_GAIN." << std::endl;
		return E_FAIL;
	}*/

	//set grabTimeout = 0 (immediate) 
	error = g_FC2Camera.GetConfiguration(&Config);
	if (error != FlyCapture2::PGRERROR_OK)
	{
		snprintf(g_errorMessage, sizeof(g_errorMessage), "Failed to get camera configuration to set grab-timeout.");
		g_LogFS << "ERROR: failed to get camera configuration." << std::endl;
		return E_FAIL;
	}
	Config.grabTimeout = 0;
	error = g_FC2Camera.SetConfiguration(&Config);
	if (error != FlyCapture2::PGRERROR_OK)
	{
		snprintf(g_errorMessage, sizeof(g_errorMessage), "Failed to set grab-timeout.");
		g_LogFS << "ERROR: failed to set grab-timeout." << std::endl;
		return E_FAIL;
	}

	//start camera
	error = g_FC2Camera.StartCapture();
	if (error != FlyCapture2::PGRERROR_OK)
	{
		snprintf(g_errorMessage, sizeof(g_errorMessage), "Failed to start capturing by FlyCapture2 camera.");
		g_LogFS << "ERROR: failed to start capturing by FlyCapture2 camera" << std::endl;
		return E_FAIL;
	}

	//enable embedded GPIO pin state
	eInfo.GPIOPinState.onOff = true;
	error = g_FC2Camera.SetEmbeddedImageInfo(&eInfo);
	if(error != FlyCapture2::PGRERROR_OK)
	{
		snprintf(g_errorMessage, sizeof(g_errorMessage), "Failed to set embedded GPIO pin state.");
		g_LogFS << "ERROR: failed to set embedded GPIO pin state." << std::endl;
		return E_FAIL;
	}

	//start thread if necessary
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
        g_LogFS << "Start without threading" << std::endl;
    }

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

@date 2013/03/29
- Threading mode is added.
*/
int getCameraImage( void )
{
	FlyCapture2::Error error;

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
		error = g_FC2Camera.RetrieveBuffer( &g_rawImage );
		if(error == FlyCapture2::PGRERROR_OK)
		{
			memcpy(g_frameBuffer, g_rawImage.GetData(), g_CameraWidth*g_CameraHeight*sizeof(unsigned char));
			if(g_UseBlurFilter){
				//cv::GaussianBlur takes approx 1.9ms while cv::blur takes only approx 0.9ms in i7-2600k machine.
				//cv::GaussianBlur(g_TmpImg, g_TmpImg, cv::Size(g_BlurFilterSize,g_BlurFilterSize),0,0);
				cv::blur(g_TmpImg, g_TmpImg, cv::Size(g_BlurFilterSize,g_BlurFilterSize));
			}
			return S_OK;
		}
	}

	return E_FAIL;
}

/*!
cleanupCamera: release camera resources.

@return No value is returned.

@note This function is necessary when you customize this file for your camera.

@date 2013/03/29
- Threading mode is added.
*/
void cleanupCamera()
{
	FlyCapture2::Error error;
	
	if(g_isThreadMode && g_runThread){
		g_runThread = false;
		SDL_WaitThread(g_pThread, NULL);
		g_LogFS << "Camera capture thread is stopped." << std::endl;
	}
	
	error = g_FC2Camera.StopCapture();
	if (error != FlyCapture2::PGRERROR_OK)
	{
		g_LogFS << "ERROR: failed to stop FlyCapture2 camera" << std::endl;
		return;
	}

	error = g_FC2Camera.Disconnect();
	if (error != FlyCapture2::PGRERROR_OK)
	{
		g_LogFS << "ERROR: failed to disconnect FlyCapture2 camera" << std::endl;
		return;
	}

	// for debugging
	//for(int i=0; i<4999; i++){
	//	g_LogFS << g_timestamp[i+1].microSeconds - g_timestamp[i].microSeconds << std::endl;
	//}

	//need to shutdown BusManager?
}

/*!
saveCameraParameters: Save current camera parameters to the camera configuration file.

@return No value is returned.
@note This function is necessary when you customize this file for your camera.

@date 2013/03/15
- Argument "ParamPath" was removed. Use g_ParamPath instead.
 */
void saveCameraParameters( std::fstream* fs )
{
	*fs << "# Camera specific parameters for " << EDITION << std::endl;
	*fs << "CAMERA_N=" << g_CameraN << std::endl;
	*fs << "OFFSET_X=" << g_OffsetX << std::endl;
	*fs << "OFFSET_Y=" << g_OffsetY << std::endl;
	*fs << "FRAME_RATE=" << g_FrameRate << std::endl;
	*fs << "SHUTTER=" << g_Shutter << std::endl;
	*fs << "CAMERA_MODE=" << g_CameraMode << std::endl;
	*fs << "USE_THREAD=" << g_isThreadMode << std::endl;
	*fs << "SLEEP_DURATION=" << g_SleepDuration << std::endl;
	*fs << "BLUR_FILTER_SIZE=" << g_BlurFilterSize << std::endl;

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
	bool updateShutterValue = false;

	switch (SDLevent->type) {
	case SDL_KEYDOWN:
		switch (SDLevent->key.keysym.sym)
		{
		case SDLK_LEFT:
			switch (currentMenuPosition)
			{
			case CUSTOMMENU_SHUTTER:
				g_Shutter -= 0.1;
				if (g_Shutter < 1.0)
					g_Shutter = 1.0;
				updateShutterValue = true;
				break;
			default:
				break;
			}
			break;

		case SDLK_RIGHT:
			switch (currentMenuPosition)
			{
			case CUSTOMMENU_SHUTTER:
				g_Shutter += 0.1;
				if (g_Shutter >= 1000 / g_FrameRate)
					g_Shutter = (1000 / g_FrameRate) - 0.1;
				updateShutterValue = true;
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

	if (updateShutterValue)
	{
		FlyCapture2::Property prop;
		FlyCapture2::Error error;

		prop.type = FlyCapture2::SHUTTER;
		prop.autoManualMode = false;
		prop.onOff = true;
		prop.absControl = true;
		prop.absValue = g_Shutter;
		error = g_FC2Camera.SetProperty(&prop);
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
void updateCustomMenuText( void )
{
	std::stringstream ss;
	ss << "Shutter(" << g_Shutter << ")";
	g_MenuString[CUSTOMMENU_SHUTTER] = ss.str();
	return;	return;
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
