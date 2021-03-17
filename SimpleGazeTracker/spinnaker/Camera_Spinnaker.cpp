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
#include "Spinnaker.h"
//#include "SpinGenApi/SpinnakerGenApi.h"

#include "opencv2/opencv.hpp"
#include "opencv2/core/core.hpp"
#include "opencv2/highgui/highgui.hpp"

#include <fstream>
#include <string>

Spinnaker::SystemPtr g_pSpinnakerSystem = nullptr;
Spinnaker::CameraList g_CameraList;
Spinnaker::CameraPtr g_pSpinnakerCam = nullptr;

#define CUSTOMMENU_EXPOSURE		(MENU_GENERAL_NUM+0)
#define CUSTOMMENU_NUM			1

int g_CameraN = 0;
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
	Spinnaker::ImagePtr pResultImage;

	while(g_runThread)
	{
		pResultImage = g_pSpinnakerCam->GetNextImage();
		if(!pResultImage->IsIncomplete())
		{
			memcpy(g_frameBuffer, pResultImage->GetData(), g_CameraWidth*g_CameraHeight * sizeof(unsigned char));
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
		pResultImage->Release();
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
	else if (strcmp(buff, "BINNING_SIZE") == 0)
	{
		g_Binning = (int)param;
	}
	else if (strcmp(buff, "FRAME_RATE") == 0)
	{
		g_FrameRate = (float)param;
	}
	else if (strcmp(buff, "EXPOSURE") == 0)
	{
		g_Exposure = (float)param;
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
@date 2020/03/16
- reading parameters from configuration file is moved to initCameraParameters().
*/
int initCamera( void )
{
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

	try {
		//Init Spinnaker camera
		g_pSpinnakerSystem = Spinnaker::System::GetInstance();
		g_CameraList = g_pSpinnakerSystem->GetCameras();
		const unsigned int numCameras = g_CameraList.GetSize();

		if (numCameras <= 0)
		{
			g_CameraList.Clear();
			g_pSpinnakerSystem->ReleaseInstance();

			snprintf(g_errorMessage, sizeof(g_errorMessage), "Failed to find Spinnaker camera.");
			g_LogFS << "ERROR: failed to get Spinnaker camera" << std::endl;
			return E_FAIL;
		}

		// get first camera
		g_pSpinnakerCam = g_CameraList.GetByIndex(g_CameraN);

		if (g_pSpinnakerCam == nullptr)
		{
			g_CameraList.Clear();
			g_pSpinnakerSystem->ReleaseInstance();

			snprintf(g_errorMessage, sizeof(g_errorMessage), "Failed to get the first Spinnaker camera.");
			g_LogFS << "ERROR: Could not get the first Spinakker camera" << std::endl;
			return E_FAIL;
		}

		// init first camera
		g_pSpinnakerCam->Init();

		// Acquisition may be stopped if application was failed in the previous run.
		// So acquisition must be stopped
		g_pSpinnakerCam->AcquisitionStop();

		// Buffer only the newest frame.
		g_pSpinnakerCam->TLStream.StreamBufferHandlingMode.SetValue(Spinnaker::StreamBufferHandlingMode_NewestOnly);

		// set to ADC8bit if available
		try {
			g_pSpinnakerCam->AdcBitDepth.SetValue(Spinnaker::AdcBitDepth_Bit8);
		}
		catch (Spinnaker::Exception& e) {
			g_LogFS << e.what() << std::endl;
			g_LogFS << "Warning: Spinnaker camera cannot be set to ADC8bit." << std::endl;
		}

		// set to Mono8 mode if available
		try {
			g_pSpinnakerCam->PixelFormat.SetValue(Spinnaker::PixelFormat_Mono8);
		}
		catch (Spinnaker::Exception& e) {
			g_LogFS << e.what() << std::endl;
			g_LogFS << "Warning: Spinnaker camera cannot be set to Mono8." << std::endl;
		}

		// binning
		g_pSpinnakerCam->BinningSelector.SetValue(Spinnaker::BinningSelector_All);
		//g_pSpinnakerCam->BinningHorizontalMode.SetValue(Spinnaker::BinningHorizontalMode_Average);
		//g_pSpinnakerCam->BinningVerticalMode.SetValue(Spinnaker::BinningVerticalMode_Average);
		g_pSpinnakerCam->BinningHorizontal.SetValue(g_Binning);
		g_pSpinnakerCam->BinningVertical.SetValue(g_Binning);

		// set cropping
		g_pSpinnakerCam->Width.SetValue(g_CameraWidth);
		g_pSpinnakerCam->Height.SetValue(g_CameraHeight);
		g_pSpinnakerCam->OffsetX.SetValue(g_OffsetX);
		g_pSpinnakerCam->OffsetY.SetValue(g_OffsetY);

		// disable GainAuto
		g_pSpinnakerCam->GainAuto.SetIntValue(Spinnaker::GainAuto_Off);

		// continuous acquisition mode
		g_pSpinnakerCam->AcquisitionMode.SetValue(Spinnaker::AcquisitionMode_Continuous);

		// manual exposure 
		g_pSpinnakerCam->ExposureAuto.SetValue(Spinnaker::ExposureAuto_Off);
		g_pSpinnakerCam->ExposureTime.SetValue(g_Exposure);

		// manual frame rate
		g_pSpinnakerCam->AcquisitionFrameRateEnable.SetValue(true);
		g_pSpinnakerCam->AcquisitionFrameRate.SetValue(g_FrameRate);
	}
	catch (Spinnaker::Exception &e) {
		g_LogFS << "Error: " << e.what() << std::endl;
		cleanupCamera();
		return E_FAIL;
	}


	try{
		// start recording
		g_pSpinnakerCam->BeginAcquisition();
	}
	catch (Spinnaker::Exception &e) {
		g_LogFS << "Error: " << e.what() << std::endl;
		g_LogFS << "Couldn't start cameara.  On Linux, make sure that enough USB-FS memory is allocated." << std::endl;
		cleanupCamera();
		return E_FAIL;
	}

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
		Spinnaker::ImagePtr pResultImage = g_pSpinnakerCam->GetNextImage();

		if(!pResultImage->IsIncomplete())
		{
			memcpy(g_frameBuffer, pResultImage->GetData(), g_CameraWidth*g_CameraHeight*sizeof(unsigned char));
			if(g_UseBlurFilter){
				//cv::GaussianBlur takes approx 1.9ms while cv::blur takes only approx 0.9ms in i7-2600k machine.
				//cv::GaussianBlur(g_TmpImg, g_TmpImg, cv::Size(g_BlurFilterSize,g_BlurFilterSize),0,0);
				cv::blur(g_TmpImg, g_TmpImg, cv::Size(g_BlurFilterSize,g_BlurFilterSize));
			}
			pResultImage->Release();
			return S_OK;
		}
		pResultImage->Release();
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

	try{
		if (g_pSpinnakerCam != nullptr) {
			g_pSpinnakerCam->EndAcquisition();
			g_pSpinnakerCam->DeInit();
			g_pSpinnakerCam = nullptr;
		}

		g_CameraList.Clear();
		g_pSpinnakerSystem->ReleaseInstance();
	}
	catch (Spinnaker::Exception &e) {
		g_LogFS << "Error: " << e.what() << std::endl;
		return;
	}

	// for debugging
	//for(int i=0; i<4999; i++){
	//	g_LogFS << g_timestamp[i+1].microSeconds - g_timestamp[i].microSeconds << std::endl;
	//}
}

/*!
saveCameraParameters: Save current camera parameters to the configuration file.

@param[in] fs file stream

@return No value is returned.
@note This function is necessary when you customize this file for your camera.

@date 2013/03/15
- Argument "ParamPath" was removed. Use g_ParamPath instead.
@date 2020/03/16
- camera specific parameters are output to common CONFIG file.
 */
void saveCameraParameters( std::fstream* fs )
{
	*fs << "# Camera specific parameters for " << EDITION << std::endl;
	*fs << "CAMERA_N=" << g_CameraN << std::endl;
	*fs << "OFFSET_X=" << g_OffsetX << std::endl;
	*fs << "OFFSET_Y=" << g_OffsetY << std::endl;
	*fs << "BINNING_SIZE=" << g_Binning << std::endl;
	*fs << "FRAME_RATE=" << g_FrameRate << std::endl;
	*fs << "EXPOSURE=" << g_Exposure << std::endl;
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
				g_pSpinnakerCam->ExposureTime.SetValue(g_Exposure);
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
				g_pSpinnakerCam->ExposureTime.SetValue(g_Exposure);
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
