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

#include <SDL/SDL.h>

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
				cv::cvtColor(frame, monoFrame, CV_RGB2GRAY);
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
initCamera: Initialize camera.

Read parameters from the configuration file, start camera and set callback function.
@attention If there are custom camera menu items, number of custom menu items must be set to g_CustomMenuNum in this function.

@param[in] ParamPath Path to the camera configuration file.
@return int
@retval S_OK Camera is successfully initialized.
@retval E_FAIL Initialization is failed.
@note This function is necessary when you customize this file for your camera.
@todo check whether number of custom menus are too many.

@date 2012/11/05
- Section header [SimpleGazeTrackerOpenCV] is supported.
- spaces and tabs around '=' are removed.
 */
int initCamera( const char* ParamPath )
{
	std::fstream fs;
	std::string str;
	char *p,*pp;
	char buff[1024];
	double param;
	bool isInSection = true; //default is True to support old config file
	
	int cameraID = 0;

	str = ParamPath;
	str.append(PATH_SEPARATOR);
	str.append(CAMERA_CONFIG_FILE);

	checkAndCopyFile(g_ParamPath,CAMERA_CONFIG_FILE,g_AppDirPath);

	fs.open(str.c_str(),std::ios::in);
	if(fs.is_open())
	{
		g_LogFS << "Open camera configuration file (" << str << ")" << std::endl;
		while(fs.getline(buff,sizeof(buff)-1))
		{
			if(buff[0]=='#') continue;

			//in Section "[SimpleGazeTrackerOpenCV]"
			if(buff[0]=='['){
				if(strcmp(buff,"[SimpleGazeTrackerOpenCV]")==0){
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

			if(strcmp(buff,"SLEEP_DURATION")==0)
			{
				g_SleepDuration = (int)param;
			}
			else if(strcmp(buff,"USE_THREAD")==0)
			{
				if((int)param!=0)
				{
					g_isThreadMode = true;
				}
			}
			else if(strcmp(buff,"CAMERA_ID")==0)
			{
				cameraID = (int)param;
			}
			else if(strcmp(buff,"FRAME_RATE")==0)
			{
				g_FrameRate = param;
				g_isParameterSpecified[CAMERA_PARAM_FRAMERATE]=true;
			}
			else if(strcmp(buff,"EXPOSURE")==0)
			{
				g_Exposure = param;
				g_isParameterSpecified[CAMERA_PARAM_EXPOSURE]=true;
			}
			else if(strcmp(buff,"BRIGHTNESS")==0)
			{
				g_Brightness = param;
				g_isParameterSpecified[CAMERA_PARAM_BRIGHTNESS]=true;
			}
			else if(strcmp(buff,"CONTRAST")==0)
			{
				g_Contrast = param;
				g_isParameterSpecified[CAMERA_PARAM_CONTRAST]=true;
			}
			else if(strcmp(buff,"GAIN")==0)
			{
				g_Gain = param;
				g_isParameterSpecified[CAMERA_PARAM_GAIN]=true;
			}
		}
		fs.close();
	}else{
		g_LogFS << "ERROR: failed to open camera configuration file (" << str << ")" << std::endl;
		return E_FAIL;
	}

	g_VideoCapture = cv::VideoCapture(cameraID);
	if(!g_VideoCapture.isOpened())
	{
		g_LogFS << "ERROR: no VideoCapture device is found." << std::endl;
		return E_FAIL;
	}

	g_VideoCapture.set(CV_CAP_PROP_FRAME_WIDTH,g_CameraWidth);
	g_VideoCapture.set(CV_CAP_PROP_FRAME_HEIGHT,g_CameraHeight);

	if((int)g_VideoCapture.get(CV_CAP_PROP_FRAME_WIDTH) != g_CameraWidth)
	{
		g_LogFS << "ERROR: wrong camera size (" << g_CameraWidth << "," << g_CameraHeight << ")" << std::endl;
		return E_FAIL;
	}
	if((int)g_VideoCapture.get(CV_CAP_PROP_FRAME_HEIGHT) != g_CameraHeight)
	{
		g_LogFS << "ERROR: wrong camera size (" << g_CameraWidth << "," << g_CameraHeight << ")" << std::endl;
		return E_FAIL;
	}

	if(g_isParameterSpecified[CAMERA_PARAM_FRAMERATE])
	{
		g_VideoCapture.set(CV_CAP_PROP_FPS,g_FrameRate);
		param = g_VideoCapture.get(CV_CAP_PROP_FPS);
		if(param != g_FrameRate)
			g_LogFS << "WARINING: tried to set FRAMERATE " << g_FrameRate << ", but returned value was " << param << std::endl;
	}
	if(g_isParameterSpecified[CAMERA_PARAM_BRIGHTNESS])
	{
		g_VideoCapture.set(CV_CAP_PROP_BRIGHTNESS,g_Brightness);
		param = g_VideoCapture.get(CV_CAP_PROP_BRIGHTNESS);
		if(param != g_Brightness)
			g_LogFS << "WARINING: tried to set BRIGHTNESS " << g_Brightness << ", but returned value was " << param << std::endl;
	}
	if(g_isParameterSpecified[CAMERA_PARAM_CONTRAST])
	{
		g_VideoCapture.set(CV_CAP_PROP_CONTRAST,g_Contrast);
		param = g_VideoCapture.get(CV_CAP_PROP_CONTRAST);
		if(param != g_Contrast)
			g_LogFS << "WARINING: tried to set CONTRAST " << g_Contrast << ", but returned value was " << param << std::endl;
	}
	if(g_isParameterSpecified[CAMERA_PARAM_GAIN])
	{
		g_VideoCapture.set(CV_CAP_PROP_GAIN,g_Gain);
		param = g_VideoCapture.get(CV_CAP_PROP_GAIN);
		if(param != g_Gain)
			g_LogFS << "WARINING: tried to set GAIN " << g_Gain << ", but returned value was " << param << std::endl;
	}
	if(g_isParameterSpecified[CAMERA_PARAM_EXPOSURE])
	{
		g_VideoCapture.set(CV_CAP_PROP_EXPOSURE,g_Exposure);
		param = g_VideoCapture.get(CV_CAP_PROP_EXPOSURE);
		if(param != g_Exposure)
			g_LogFS << "WARINING: tried to set EXPOSURE " << g_Exposure << ", but returned value was " << param << std::endl;
	}

	if(g_isThreadMode)
	{
		g_runThread = true;
		g_pThread = SDL_CreateThread(captureCameraThread, NULL);
		if(g_pThread==NULL)
		{
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
					cv::cvtColor(frame, monoFrame, CV_RGB2GRAY);
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
	if(g_isThreadMode){
		g_runThread = false;
		SDL_WaitThread(g_pThread, NULL);
	}
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
