#define _CRT_SECURE_NO_WARNINGS


#include "../common/SGTConfigDlg.h"
extern std::vector<SGTParam*> g_pCameraParamsVector;

#include "GazeTracker.h"

#include <atlbase.h>
#include <cameralibrary.h>

#include <fstream>
#include <sstream>
#include <string>

CameraLibrary::Camera *g_camera;
CameraLibrary::Frame *g_frame;

int g_FrameRate = 100;
int g_Intensity = 7;
int g_Exposure = 399;

bool g_AcquisitionStarted = false;

#define CUSTOMMENU_INTENSITY	(MENU_GENERAL_NUM+0)
#define CUSTOMMENU_EXPOSURE		(MENU_GENERAL_NUM+1)
#define CUSTOMMENU_NUM			2
int g_CustomMenuNum = CUSTOMMENU_NUM;

std::string g_CustomMenuString[] = {
	"Intensity",
	"Exposure"
};

const char* getDefaultConfigString(void)
{
	return CAMERA_CONFIG_FILE;
}

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
int initCameraParameters(char* buff, char* p)
{
	if (strcmp(buff, "FRAME_RATE") == 0) g_pCameraParamsVector.push_back(new SGTParamInt("FRAME_RATE", &g_FrameRate, p,
		"Set frame rate in frames-per-second.\n(Value: integer)"));
	else if (strcmp(buff, "EXPOSURE") == 0) g_pCameraParamsVector.push_back(new SGTParamInt("EXPOSURE", &g_Exposure, p,
		"Set exposure.\n(Value: integer)"));
	else if (strcmp(buff, "INTENSITY") == 0)g_pCameraParamsVector.push_back(new SGTParamInt("INTENSITY", &g_Intensity, p,
		"Set intensity of built-in IR-LED.\n(Value: integer)"));
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

@date 2012/05/24
- Both width and height are checked (640x480 or 320x240).
@date 2012/07/30
- Configuration file name in the log file is corrected.
@date 2012/11/05
- Section header [SimpleGazeTrackerOptiTrack] is supported.
- spaces and tabs around '=' are removed.
@date 2013/03/15
- Argument "ParamPath" was removed. Use g_ParamPath instead.
@date 2013/10/23
- Camera configuration file is customizable.
@date 2013/11/15
- Library is changed (OptiTrack 2D SDK -> OptiTrack CameraSDK)
*/
int initCamera( void )
{
	CameraLibrary::CameraManager::X().WaitForInitialization();
	if(!CameraLibrary::CameraManager::X().AreCamerasInitialized()){
		g_LogFS << "ERROR: failed to initialize camera(s)" << std::endl;
		return E_FAIL;
	}

	g_camera = CameraLibrary::CameraManager::X().GetCamera();

	if(g_camera==NULL)
	{
		g_LogFS << "ERROR: no camera is found" << std::endl;
		return E_FAIL;
	}
	
	//== Set Some Camera Options ====================----
	//g_camera->SetVideoType(Core::eVideoMode::GrayscaleMode);
	g_camera->SetVideoType(Core::MJPEGMode);
	g_camera->SetNumeric(false,0);
	g_camera->SetTextOverlay(false);
	g_camera->SetIRFilter(true);

	g_camera->SetIntensity(g_Intensity);
	g_camera->SetExposure(g_Exposure);

	if(g_CameraWidth == 640 && g_CameraHeight == 480)
		g_camera->SetGrayscaleDecimation(0);
	else if(g_CameraWidth == 320 && g_CameraHeight == 240)
		g_camera->SetGrayscaleDecimation(2);
	else
	{
		g_LogFS << "ERROR: wrong camera size (" << g_CameraWidth << "," << g_CameraHeight << ")" << std::endl;
		return E_FAIL;
	}
	g_camera->SetFrameRate(g_FrameRate);
	g_camera->SetThreshold(254);
	
	g_camera->Start();

	Sleep(10);
	g_AcquisitionStarted = true;

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
	if (!g_AcquisitionStarted)
		return E_FAIL;

	g_frame = g_camera->GetLatestFrame();

	if(g_frame)
	{
		//== New Frame Has Arrived ==========================------
		g_frame->Rasterize(g_CameraWidth, g_CameraHeight, g_CameraWidth, 8, (byte *) g_frameBuffer);
		g_frame->Release();

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
	g_AcquisitionStarted = false;

	if(g_camera != NULL){
		g_camera->Stop();

		CameraLibrary::CameraManager::X().Shutdown();
	}
}

/*!
saveCameraParameters: Save current camera parameters to the camera configuration file.

@param[in] ParamPath Path to the camera configuration file.
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
	*fs << "FRAME_RATE=" << g_FrameRate << std::endl;
	*fs << "EXPOSURE=" << g_Exposure << std::endl;
	*fs << "INTENSITY=" << g_Intensity << std::endl;

	return;
}

/*!
customCameraMenu: Process camera-dependent custom menu items. If there is no custom menu items, this function do nothing.

Your camera may have some parameters which you want to adjust with previewing camera image.
In such cases, write nesessary codes to adjust these parameters in this function.
This function is when left or right cursor key is pressed.

@param[in] SDLevent Event object.
@param[in] currentMenuPosition Current menu position.
@return int
@retval S_OK 
@retval E_FAIL 
@note This function is necessary when you customize this file for your camera.
*/
int customCameraMenu(int code, int currentMenuPosition)
{
	switch( code )
	{
	case MENU_LEFT_KEY:
		switch(currentMenuPosition)
		{
		case CUSTOMMENU_INTENSITY:
			g_Intensity--;
			if(g_Intensity<0)
				g_Intensity = 0;
			g_camera->SetIntensity(g_Intensity);
			break;
		case CUSTOMMENU_EXPOSURE:
			g_Exposure--;
			if(g_Exposure<0)
				g_Exposure = 0;
			g_camera->SetExposure(g_Exposure);
			break;
		default:
			break;
		}
		break;

	case MENU_RIGHT_KEY:
		switch(currentMenuPosition)
		{
		case CUSTOMMENU_INTENSITY:
			g_Intensity++;
			if(g_Intensity>=12)
				g_Intensity = 12;
			g_camera->SetIntensity(g_Intensity);
			break;
		case CUSTOMMENU_EXPOSURE:
			g_Exposure++;
			if(g_Exposure>=479)
				g_Exposure = 479;
			g_camera->SetExposure(g_Exposure);
			break;
		default:
			break;
		}
		break;

	default:
		break;
	}

	return S_OK;

}

void updateCustomCameraParameterFromMenu(int id, std::string val)
{
	char* p;
	if (id == CUSTOMMENU_EXPOSURE) {
		g_Exposure = std::strtol(val.c_str(), &p, 10);
	}
	else if (id == CUSTOMMENU_INTENSITY) {
		g_Intensity = std::strtol(val.c_str(), &p, 10);
	}
}


/*!
updateCustomMenuText: update menu text of custom camera menu items.

Your camera may have some parameters which you want to adjust with previewing camera image.
If your custom menu need to update its text, write nessesary codes to update text in this function.
This function is called from initD3D() at first, and from MsgProc() when left or right cursor key is pressed.

@return No value is returned.
@note This function is necessary when you customize this file for your camera.
*/
std::string updateCustomMenuText( int id )
{
	char buff[256];

	if (id == CUSTOMMENU_EXPOSURE) {
		snprintf(buff, sizeof(buff), "%d", g_Exposure);
		return std::string(buff);
	}
	else if (id == CUSTOMMENU_INTENSITY) {
		snprintf(buff, sizeof(buff), "%d", g_Intensity);
		return std::string(buff);
	}

	return std::string("");
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
