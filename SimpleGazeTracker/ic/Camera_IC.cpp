/*!
@file Camera.cpp
@author Hiroyuki Sogo
@copyright GNU General Public License (GPL) version 3.
@brief Camera-dependent procedures are defined.

@date 2020/02/26
- Created.
*/

#define _CRT_SECURE_NO_DEPRECATE
#define _CRT_SECURE_NO_WARNINGS

#include "GazeTracker.h"
#include <tisudshl.h>
#include "cmdhelper.h"

#include "opencv2/opencv.hpp"
#include "opencv2/core/core.hpp"
#include "opencv2/highgui/highgui.hpp"

#include <fstream>
#include <string>


DShowLib::Grabber g_ICGrabber;
DShowLib::tFrameHandlerSinkPtr g_pSink;
DShowLib::tMemBufferCollectionPtr g_pCollection;

DWORD g_ICFrameCount;

#define CUSTOMMENU_EXPOSURE		(MENU_GENERAL_NUM+0)
#define CUSTOMMENU_NUM			1

int g_OffsetX = 0;
int g_OffsetY = 0;
int g_Binning = 1;
float g_FrameRate = 200;
float g_Exposure = 1000;

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
	while(g_runThread)
	{
		DWORD currentFrame = g_ICGrabber.getFrameCount();
		if(currentFrame>g_ICFrameCount)
		{
			g_NewFrameAvailable = true;
			g_ICFrameCount = currentFrame;
			
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
	
	fs.open(fname.c_str(),std::ios::in);
	if(fs.is_open())
	{
		g_LogFS << "Open camera configuration file (" << fname << ")" << std::endl;
		while(fs.getline(buff,sizeof(buff)-1))
		{
			if(buff[0]=='#') continue;

			//in Section "[SimpleGazeTrackerSpinnaker]"
			if(buff[0]=='['){
				if(strcmp(buff,"[SimpleGazeTrackerIC]")==0){
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
			else if (strcmp(buff, "BINNING_SIZE") == 0)
			{
				g_Binning = (int)param;
			}
			else if(strcmp(buff,"FRAME_RATE")==0)
			{
				g_FrameRate = (float)param;
			}
			else if (strcmp(buff, "EXPOSURE") == 0)
			{
				g_Exposure = (float)param;
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

	if (g_Exposure >= 1000000 / g_FrameRate) {
		g_Exposure = 1000000 / g_FrameRate - 100;
		g_LogFS << "Exposure is too long. Adjusted to " << g_Exposure << std::endl;
	}
	else if (g_Exposure <= 0) {
		g_Exposure = 100;
		g_LogFS << "Exposure is too short. Adjusted to " << g_Exposure << std::endl;
	}


	//Init IC camera
	DShowLib::InitLibrary();
	DShowLib::Grabber::tVidCapDevListPtr pVidCapDevList = g_ICGrabber.getAvailableVideoCaptureDevices();
	if (pVidCapDevList == 0 || pVidCapDevList->empty())
	{
		snprintf(g_errorMessage, sizeof(g_errorMessage), "Failed to find IC camera.");
		g_LogFS << "ERROR: failed to get IC camera" << std::endl;
		return E_FAIL;
	}

	// get first camera
	if (!g_ICGrabber.openDev(pVidCapDevList->at(0)))
	{
		snprintf(g_errorMessage, sizeof(g_errorMessage), "Failed to get the first IC camera.");
		g_LogFS << "ERROR: Could not get the first IC camera" << std::endl;
		return E_FAIL;
	}

	/*
	DShowLib::Grabber::tFPSListPtr pFPSlist = g_ICGrabber.getAvailableFPS();
	for (DShowLib::Grabber::tFPSList::iterator it = pFPSlist->begin(); it != pFPSlist->end(); it++) {
		g_LogFS << *it << std::endl;
	}
	*/

	// get available video format
	DShowLib::Grabber::tVidFmtListPtr pVidFmtList = g_ICGrabber.getAvailableVideoFormats();

	// search best video format
	bool found_y800 = false;
	int index = 0,  best_index = 0, cx, cy, max_cxcy = 0;
	std::string format_string;
	for (DShowLib::Grabber::tVidFmtList::const_iterator it = pVidFmtList->begin(); it != pVidFmtList->end(); it++) {
		format_string = it->toString();
		if (format_string.find("Y800 ") != std::string::npos) {
			found_y800 = true;
			size_t from, to;
			from = format_string.find("(");
			to = format_string.find("x");
			cx = std::stoi(format_string.substr(from + 1, to - from));
			from = format_string.find("x");
			to = format_string.find(")");
			cy = std::stoi(format_string.substr(from + 1, to - from));
			if (cx*cy > max_cxcy) {
				best_index = index;
				max_cxcy = cx * cy;
			}
		}
		index++;
	}
	if (!found_y800) {
		g_LogFS << "Y800 format is not available" << std::endl;
		return E_FAIL;
	}

	// set to best video format
	g_ICGrabber.setVideoFormat(pVidFmtList->at(best_index));
	g_LogFS << "Bset video format: " << (pVidFmtList->at(best_index)).toString() << std::endl;

	// prepare buffer
	g_pSink = DShowLib::FrameHandlerSink::create(DShowLib::eY800, 1);
	g_pSink->setSnapMode(false);
	g_ICGrabber.setSinkType(g_pSink);
	if (!g_ICGrabber.prepareLive(false))
	{
		g_LogFS << "Could not render the VideoFormat into an 8bit-monochrome buffer.";
		return E_FAIL;
	}
	DShowLib::FrameTypeInfo info;
	g_pSink->getOutputFrameType(info);

	if (info.dim.cx != g_CameraWidth || info.dim.cy != g_CameraHeight)
	{
		g_LogFS << "Image size in CONFIG (" << g_CameraWidth << "," << g_CameraHeight << ") is inconsistent with camera setting (" << info.dim.cx << "," << info.dim.cy << ")." << std::endl;
		return E_FAIL;
	}

	BYTE* pBuf[1];
	pBuf[0] = (BYTE*) g_frameBuffer;
	g_pCollection = DShowLib::MemBufferCollection::create(info, 1, pBuf);

	if (g_pCollection == 0 || !g_pSink->setMemBufferCollection(g_pCollection))
	{
		g_LogFS << "Could not set the new MemBufferCollection, because types do not match.";
		return -1;
	}

	if (!g_ICGrabber.startLive(false)) {
		g_LogFS << "Could not start grabbing";
		return -1;
	}
	g_ICFrameCount = 0;

	
	g_LogFS << "Grabber.getFPS:" << g_ICGrabber.getFPS() << std::endl;
	g_LogFS << "Grabber.Format:" << g_ICGrabber.getVideoFormat().toString() << std::endl;
	

	//start thread if necessary
	if (g_isThreadMode)
	{
		g_runThread = true;
		g_pThread = SDL_CreateThread(captureCameraThread, "CaptureThread", NULL);
		if (g_pThread == NULL)
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

	Sleep(5);

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
		DWORD currentFrame = g_pSink->getFrameCount();

		if(currentFrame > g_ICFrameCount)
		{
			g_ICFrameCount = currentFrame;
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
	if(g_isThreadMode && g_runThread){
		g_runThread = false;
		SDL_WaitThread(g_pThread, NULL);
		g_LogFS << "Camera capture thread is stopped." << std::endl;
	}

	g_ICGrabber.stopLive();
	g_ICGrabber.closeDev();

	return;
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
	std::fstream fs;
	std::string fname(g_ParamPath.c_str());

	fname.append(PATH_SEPARATOR);
	fname.append(CAMERA_CONFIG_FILE);

	fs.open(fname.c_str(), std::ios::out);
	if (!fs.is_open())
	{
		return;
	}

	fs << "#If you want to recover original settings, delete this file and start eye tracker program." << std::endl;
	fs << "[SimpleGazeTrackerIC]" << std::endl;
	fs << "OFFSET_X=" << g_OffsetX << std::endl;
	fs << "OFFSET_Y=" << g_OffsetY << std::endl;
	fs << "BINNING_SIZE=" << g_Binning << std::endl;
	fs << "FRAME_RATE=" << g_FrameRate << std::endl;
	fs << "EXPOSURE=" << g_Exposure << std::endl;
	fs << "USE_THREAD=" << g_isThreadMode << std::endl;
	fs << "SLEEP_DURATION=" << g_SleepDuration << std::endl;

	fs.close();

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
			case CUSTOMMENU_EXPOSURE:
				g_Exposure -= 100;
				if (g_Exposure < 0)
					g_Exposure = 100;
				//g_pSpinnakerCam->ExposureTime.SetValue(g_Exposure);
				break;
			default:
				break;
			}
			break;

		case SDLK_RIGHT:
			switch (currentMenuPosition)
			{
			case CUSTOMMENU_EXPOSURE:
				g_Exposure += 100;
				if (g_Exposure >= 1000000 / g_FrameRate)
					g_Exposure = (1000000 / g_FrameRate) - 100;
				//g_pSpinnakerCam->ExposureTime.SetValue(g_Exposure);
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
void updateCustomMenuText( void )
{
	std::stringstream ss;
	ss << "Exposure(" << g_Exposure << ")";
	g_MenuString[CUSTOMMENU_EXPOSURE] = ss.str();

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
