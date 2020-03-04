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

#include "opencv2/opencv.hpp"
#include "opencv2/core/core.hpp"
#include "opencv2/highgui/highgui.hpp"

#include <fstream>
#include <string>


DShowLib::Grabber g_ICGrabber;
DShowLib::tFrameHandlerSinkPtr g_pSink;
DShowLib::tMemBufferCollectionPtr g_pCollection;

DWORD g_ICFrameCount;

float g_FrameRate = 200;
std::string g_ImageFormat = "auto";

SDL_Thread *g_pThread;
bool g_runThread;

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

			if (strcmp(buff, "IMAGE_FORMAT") == 0)
			{
				g_ImageFormat = p + 1;  // string
			}
			else if(strcmp(buff,"FRAME_RATE")==0)
			{
				g_FrameRate = (float)param;
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

	// get available video format
	DShowLib::Grabber::tVidFmtListPtr pVidFmtList = g_ICGrabber.getAvailableVideoFormats();

	if (g_ImageFormat == "auto")
	{
		// search best video format
		bool found_y800 = false;
		int index = 0, best_index = 0, cx, cy, max_cxcy = 0;
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
		g_LogFS << "Selected video format: " << (pVidFmtList->at(best_index)).toString() << std::endl;
		g_ICGrabber.setVideoFormat(pVidFmtList->at(best_index));
	}
	else
	{
		int index = 0;
		bool found = false;
		std::string format_string;
		for (DShowLib::Grabber::tVidFmtList::const_iterator it = pVidFmtList->begin(); it != pVidFmtList->end(); it++) {
			format_string = it->toString();
			if (format_string == g_ImageFormat) {
				found = true;
				break;
			}
			index++;
		}

		if (found) {
			g_LogFS << "Set video format: " << (pVidFmtList->at(index)).toString() << std::endl;
			g_ICGrabber.setVideoFormat(pVidFmtList->at(index));
		}
		else{
			g_LogFS << "Video format (" << g_ImageFormat << ") is not available. Check format string. Use \"auto\" to select format automatically (note: \"auto\" is case sensitive)." << std::endl;
			return E_FAIL;
		}
	}

	/*
	DShowLib::Grabber::tFPSListPtr pFPSlist = g_ICGrabber.getAvailableFPS();
	for (DShowLib::Grabber::tFPSList::iterator it = pFPSlist->begin(); it != pFPSlist->end(); it++) {
		g_LogFS << *it << std::endl;
	}
	*/

	// set fps
	if (!g_ICGrabber.setFPS(g_FrameRate)) {
		g_LogFS << "Could not set frame rate to " << g_FrameRate << " fps.";
		return E_FAIL;
	}

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

	/*
	g_LogFS << "Grabber.getFPS:" << g_ICGrabber.getFPS() << std::endl;
	g_LogFS << "Grabber.Format:" << g_ICGrabber.getVideoFormat().toString() << std::endl;
	*/
	

	g_LogFS << "Camera is started." << std::endl;

	Sleep(5);

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
	DWORD currentFrame = g_pSink->getFrameCount();

	if(currentFrame > g_ICFrameCount)
	{
		g_ICFrameCount = currentFrame;
		return S_OK;
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
	g_ICGrabber.stopLive();
	g_ICGrabber.closeDev();

	g_LogFS << "Camera is stopped." << std::endl;

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
