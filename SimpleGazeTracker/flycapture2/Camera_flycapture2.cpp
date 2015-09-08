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

int g_OffsetX = 0;
int g_OffsetY = 0;
int g_CameraMode = 1;
float g_FrameRate = 200;

SDL_Thread *g_pThread;
bool g_runThread;

int g_SleepDuration = 0;
bool g_isThreadMode = true;

bool g_UseBlurFilter = true;
int g_BlurFilterSize = 3;
cv::Mat g_TmpImg;


volatile bool g_NewFrameAvailable = false; /*!< True if new camera frame is grabbed. @note This function is necessary when you customize this file for your camera.*/

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
	std::fstream fs;
	std::string fname;
	char *p,*pp;
	char buff[1024];
	double param;
	bool isInSection = true; //default is True to support old config file
	
	fname = g_ParamPath.c_str();
	fname.append(PATH_SEPARATOR);
	if(g_CameraConfigFileName==""){
		g_CameraConfigFileName = CAMERA_CONFIG_FILE;
		checkAndCopyFile(g_ParamPath,CAMERA_CONFIG_FILE,g_AppDirPath);
	}
	fname.append(g_CameraConfigFileName.c_str());
	
	FlyCapture2::Error error;
	FlyCapture2::Mode mode;

	fs.open(fname.c_str(),std::ios::in);
	if(fs.is_open())
	{
		g_LogFS << "Open camera configuration file (" << fname << ")" << std::endl;
		while(fs.getline(buff,sizeof(buff)-1))
		{
			if(buff[0]=='#') continue;

			//in Section "[SimpleGazeTrackerFlyCapture2]"
			if(buff[0]=='['){
				if(strcmp(buff,"[SimpleGazeTrackerFlyCapture2]")==0){
					isInSection = true;
				}
				else
				{
					isInSection = false;
				}
				continue;
			}
		
			if(!isInSection) continue; //not in section
		

			//Check options.
			//If "=" is not included, this line is not option.
			if((p=strchr(buff,'='))==NULL) continue;

			//remove space/tab
			*p = '\0';
			while(*(p-1)==0x09 || *(p-1)==0x20)
			{
				p--;
				*p= '\0';
			}
			while(*(p+1)==0x09 || *(p+1)==0x20) p++;
			param = strtod(p+1,&pp); //paramete is not int but double

			if(strcmp(buff,"OFFSET_X")==0)
			{
				g_OffsetX = (int)param;
			}
			else if(strcmp(buff,"OFFSET_Y")==0)
			{
				g_OffsetY = (int)param;
			}
			else if(strcmp(buff,"FRAME_RATE")==0)
			{
				g_FrameRate = (float)param;
			}
			else if(strcmp(buff,"CAMERA_MODE")==0)
			{
				g_CameraMode = (int)param;
			}
			else if(strcmp(buff,"SLEEP_DURATION")==0)
			{
				g_SleepDuration = (int)param;
			}
			else if(strcmp(buff,"USE_THREAD")==0)
			{
				if((int)param!=0)
				{
					g_isThreadMode = true;
				}
				else
				{
					g_isThreadMode = false;
				}
			}
			else if(strcmp(buff,"BLUR_FILTER_SIZE")==0)
			{
				g_BlurFilterSize = (int)param;
				if(g_BlurFilterSize>1) g_UseBlurFilter = true;
				else g_UseBlurFilter = false;
			}
		}
		fs.close();
	}else{
		snprintf(g_errorMessage, sizeof(g_errorMessage), "Failed to open camera configuration file (%s)", fname.c_str());
		g_LogFS << "ERROR: failed to open camera configuration file (" << fname << ")" << std::endl;
		return E_FAIL;
	}

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
		snprintf(g_errorMessage, sizeof(g_errorMessage), "Only MODE_0 and MODE_1 are supported. \nCheck vaule of CAMERA_MODE parameter in %s", buff, fname.c_str());
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

	error = busMgr.GetCameraFromIndex(0, &g_FC2CameraGUID);
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
		snprintf(g_errorMessage, sizeof(g_errorMessage), "Failed to validate camera format.\nCheck CAMERA_WIDTH, CAMERA_HEIGHT, OFFSET_X, OFFSET_Y and CAMERA_MODE in %s.", fname.c_str());
		g_LogFS << "ERROR: could not validate \"Format7\" camera format.  Check CAMERA_WIDTH, CAMERA_HEIGHT, OFFSET_X, OFFSET_Y and CAMERA_MODE." << std::endl;
		return E_FAIL;
	}
	if(!settingsAreValid)
	{
		snprintf(g_errorMessage, sizeof(g_errorMessage), "Camera format is invalid.\nCheck CAMERA_WIDTH, CAMERA_HEIGHT, OFFSET_X, OFFSET_Y and CAMERA_MODE in %s.", fname.c_str());
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
		snprintf(g_errorMessage, sizeof(g_errorMessage), "Failed to set frame rate.\nCheck FRAME_RATE in %s.", fname.c_str());
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
void saveCameraParameters( void )
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
