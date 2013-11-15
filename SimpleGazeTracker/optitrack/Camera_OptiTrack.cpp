#include <SDL/SDL.h>
#include "GazeTracker.h"
#include <cameralibrary.h>
#include <atlbase.h>

#include <fstream>
#include <sstream>
#include <string>

int getCameraImage( void );
void CleanupCamera( void );


CameraLibrary::Camera *g_camera;
CameraLibrary::Frame *g_frame;

int g_FrameRate = 100;
int g_Intensity = 7;
int g_Exposure = 399;

#define CUSTOMMENU_INTENSITY	(MENU_GENERAL_NUM+0)
#define CUSTOMMENU_EXPOSURE		(MENU_GENERAL_NUM+1)
#define CUSTOMMENU_NUM			2

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
*/
int initCamera( void )
{
	std::fstream fs;
	std::string fname;
	char buff[512];
	char *p,*pp;
	int param;
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

			//in Section "[SimpleGazeTrackerOptiTrack]"
			if(buff[0]=='['){
				if(strcmp(buff,"[SimpleGazeTrackerOptiTrack]")==0){
					isInSection = true;
				}
				else
				{
					isInSection = false;
				}
				continue;
			}

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
			param = strtol(p+1,&pp,10);

			if(strcmp(buff,"FRAME_RATE")==0) g_FrameRate = param;
			else if(strcmp(buff,"EXPOSURE")==0) g_Exposure = param;
			else if(strcmp(buff,"INTENSITY")==0) g_Intensity = param;
		}
		fs.close();
	}else{
		g_LogFS << "ERROR: failed to open camera configuration file (" << fname << ")" << std::endl;
		return E_FAIL;
	}

	CameraLibrary::CameraManager::X().WaitForInitialization();
	if(!CameraLibrary::CameraManager::X().AreCamerasInitialized()){
		g_LogFS << "ERROR: failed to initialize camera(s)" << std::endl;
		return E_FAIL;
	}

	g_camera = CameraLibrary::CameraManager::X().GetCamera();

	if(g_camera==NULL )
	{
		g_LogFS << "ERROR: no camera is found" << std::endl;
		return E_FAIL;
	}
	
	//== Set Some Camera Options ====================----
	g_camera->SetVideoType(CameraLibrary::GrayscaleMode);
	g_camera->SetNumeric(false,0);
	g_camera->SetTextOverlay(false);

	g_camera->SetIntensity(g_Intensity);
	g_camera->SetExposure(g_Exposure);

	if(g_CameraWidth == 640 && g_CameraHeight == 480)
		g_camera->SetFrameDecimation(0);
	else if(g_CameraWidth == 320 && g_CameraHeight == 240)
		g_camera->SetFrameDecimation(2);
	else
	{
		g_LogFS << "ERROR: wrong camera size (" << g_CameraWidth << "," << g_CameraHeight << ")" << std::endl;
		return E_FAIL;
	}

	g_camera->SetFrameRate(g_FrameRate);
	g_camera->SetThreshold(254);

	g_camera->Start();

	Sleep(10);

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
int getCameraImage( void )
{
	g_frame = g_camera->GetLatestFrame();

	if(g_frame)
	{
		//== New Frame Has Arrived ==========================------
		//frameCounter++;
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
*/
void saveCameraParameters( void )
{
	std::fstream fs;
	std::string fname(g_ParamPath.c_str());

	fname.append(PATH_SEPARATOR);
	fname.append(CAMERA_CONFIG_FILE);

	fs.open(fname.c_str(),std::ios::out);
	if(!fs.is_open())
	{
		return;
	}

	fs << "#If you want to recover original settings, delete this file and start eye tracker program." << std::endl;
	fs << "[SimpleGazeTrackerOptiTrack]" << std::endl;
	fs << "FRAME_RATE=" << g_FrameRate << std::endl;
	fs << "EXPOSURE=" << g_Exposure << std::endl;
	fs << "INTENSITY=" << g_Intensity << std::endl;

	fs.close();

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
int customCameraMenu(SDL_Event* SDLevent, int currentMenuPosition)
{
	switch(SDLevent->type){
	case SDL_KEYDOWN:
		switch(SDLevent->key.keysym.sym)
		{
		case SDLK_LEFT:
			switch(currentMenuPosition)
			{
			case CUSTOMMENU_INTENSITY:
				g_Intensity--;
				if(g_Intensity<1)
					g_Intensity = 1;
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

		case SDLK_RIGHT:
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
	ss << "LightIntensity(" << g_Intensity << ")";
	g_MenuString[CUSTOMMENU_INTENSITY] = ss.str();
	ss.str("");
	ss << "CameraExposure(" << g_Exposure << ")";
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
