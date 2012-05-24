#include <windows.h>
#include <atlbase.h>
#include "GazeTracker.h"
#include "C:/Program Files/NaturalPoint/Optitrack/inc/optitrack.h"
#import  "C:/Program Files/NaturalPoint/Optitrack/inc/optitrack.tlb"

#include <fstream>
#include <iostream>
#include <string>

HRESULT InitCamera( void );
HRESULT getCameraImage( void );
void CleanupCamera( void );

CComPtr<INPCameraCollection> g_cameraCollection;
CComPtr<INPCamera>           g_camera;
CComPtr<INPCameraFrame>		 g_frame;

int g_FrameRate = 100;
int g_Intensity = 7;
int g_Exposure = 399;

#define CUSTOMMENU_INTENSITY	(MENU_GENERAL_NUM+0)
#define CUSTOMMENU_EXPOSURE		(MENU_GENERAL_NUM+1)
#define CUSTOMMENU_NUM			2

/*!
initCamera: Initialize camera.

Read parameters from the configuration file, start camera and set callback function.
@attention If there are custom camera menu items, number of custom menu items must be set to g_CustomMenuNum in this function.

@param[in] ParamPath Path to the camera configuration file.
@return HRESULT
@retval S_OK Camera is successfully initialized.
@retval E_FAIL Initialization is failed.
@note This function is necessary when you customize this file for your camera.
@todo check whether number of custom menus are too many.

@date 2012/05/24
- Both width and height are checked (640x480 or 320x240).
*/
HRESULT initCamera( char* ParamPath )
{
	FILE* fp;
	char buff[512];
	char *p,*pp;
	int param;

	strcpy_s(buff, sizeof(buff), ParamPath);
	strcat_s(buff, sizeof(buff), CAMERA_CONFIG_FILE);
	if(!PathFileExists(buff)){
		char exefile[512];
		char configfile[512];
		char drive[4],dir[512],fname[32],ext[5];
		errno_t r;
		GetModuleFileName(NULL,exefile,sizeof(exefile));
		r = _splitpath_s(exefile,drive,sizeof(drive),dir,sizeof(dir),fname,sizeof(fname),ext,sizeof(ext));
		strcpy_s(configfile,sizeof(configfile),drive);
		strcat_s(configfile,sizeof(configfile),dir);
		strcat_s(configfile,sizeof(configfile),CAMERA_CONFIG_FILE);
		CopyFile(configfile,buff,true);
	}

	if(fopen_s(&fp,buff,"r")==NULL)
	{
		while(fgets(buff,sizeof(buff),fp)!=NULL)
		{
			if(buff[0]=='#') continue;
			if((p=strchr(buff,'='))==NULL) continue;

			param = strtol(p+1,&pp,10);
			*p = NULL;

			if(strcmp(buff,"FRAME_RATE")==0) g_FrameRate = param;
			else if(strcmp(buff,"EXPOSURE")==0) g_Exposure = param;
			else if(strcmp(buff,"INTENSITY")==0) g_Intensity = param;
		}
		fclose(fp);
	}else{
		return E_FAIL;
	}

	CoInitialize(NULL);
    g_cameraCollection.CoCreateInstance(CLSID_NPCameraCollection);
	g_cameraCollection->Enum();

	long cameraCount  = 0;

	g_cameraCollection->get_Count(&cameraCount);
	
	if(cameraCount<1)
		return E_FAIL;

	g_cameraCollection->Item(0, &g_camera);

	long serial,width,height,model,revision,rate;

	g_camera->get_SerialNumber(&serial);
	g_camera->get_Width       (&width);
	g_camera->get_Height      (&height);
	g_camera->get_Model       (&model);
	g_camera->get_Revision    (&revision);
	g_camera->get_FrameRate   (&rate);

	//== Set Some Camera Options ====================----
	g_camera->SetOption(NP_OPTION_VIDEO_TYPE        , (CComVariant) 1 );
	g_camera->SetOption(NP_OPTION_FRAME_DECIMATION  , (CComVariant) 0 );
	g_camera->SetOption(NP_OPTION_NUMERIC_DISPLAY_OFF,(CComVariant) 0 );
	g_camera->SetOption(NP_OPTION_TEXT_OVERLAY_OPTION,(CComVariant) 0 );

	g_camera->SetOption(NP_OPTION_INTENSITY,(CComVariant) g_Intensity);
	g_camera->SetOption(NP_OPTION_EXPOSURE,(CComVariant) g_Exposure);

	if(g_CameraWidth == 640 && g_CameraHeight == 480)
		g_camera->SetOption(NP_OPTION_GRAYSCALE_DECIMATION,(CComVariant)0);
	else if(g_CameraWidth == 320 && g_CameraHeight == 240)
		g_camera->SetOption(NP_OPTION_GRAYSCALE_DECIMATION,(CComVariant)2);
	else
		return E_FAIL;

	g_camera->SetOption(NP_OPTION_FRAME_RATE,(CComVariant) g_FrameRate );
	g_camera->SetOption(NP_OPTION_THRESHOLD,(CComVariant) 254);
	g_camera->SetOption(NP_OPTION_MAXIMUM_SEGMENT_LENGTH,(CComVariant) 1023);
	g_camera->SetOption(NP_OPTION_MINIMUM_SEGMENT_LENGTH,(CComVariant) 1024);
	g_camera->SetOption(NP_OPTION_DRAW_SCALE,(CComVariant)1.0);

	g_camera->Open();
	g_camera->Start();

	Sleep(10);

	//prepare custom menu
	g_CustomMenuNum = CUSTOMMENU_NUM;

	return S_OK;
}

/*!
getCameraImage: Get new camera image.

@return HRESULT
@retval S_OK New frame is available.
@retval E_FAIL There is no new frame.
@note This function is necessary when you customize this file for your camera.
*/
HRESULT getCameraImage( void )
{
	g_camera->GetFrame(0, &g_frame);

	if(g_frame!=0)
	{
		//== New Frame Has Arrived ==========================------
		//frameCounter++;
		g_camera->GetFrameImage(g_frame, g_CameraWidth, g_CameraHeight, g_CameraWidth, 8, (byte *) g_frameBuffer);
		
		g_frame->Free();
		g_frame.Release();

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
		g_camera->Close();
		g_camera.Release();

		g_cameraCollection.Release();
		CoUninitialize();
	}
}

/*!
saveCameraParameters: Save current camera parameters to the camera configuration file.

@param[in] ParamPath Path to the camera configuration file.
@return No value is returned.
@note This function is necessary when you customize this file for your camera.
 */
void saveCameraParameters(char* ParamPath)
{
	FILE* fp;
	char buff[512];

	strcpy_s(buff,sizeof(buff),ParamPath);
	strcat_s(buff,sizeof(buff),CAMERA_CONFIG_FILE);

	if(fopen_s(&fp,buff,"w")!=NULL)
	{
		return;
	}

	fprintf_s(fp,"#If you want to recover original settings, delete this file and start eye tracker program.\n");
	fprintf_s(fp,"FRAME_RATE=%d\n",g_FrameRate);
	fprintf_s(fp,"EXPOSURE=%d\n",g_Exposure);
	fprintf_s(fp,"INTENSITY=%d\n",g_Intensity);

	fclose(fp);

	return;
}

/*!
customCameraMenu: Process camera-dependent custom menu items. If there is no custom menu items, this function do nothing.

Your camera may have some parameters which you want to adjust with previewing camera image.
In such cases, write nesessary codes to adjust these parameters in this function.
This function is called from initD3D() at first, and from MsgProc() when left or right cursor key is pressed.

@param[in] hWnd passed from MsgProc.
@param[in] msg passed from MsgProc.
@param[in] wParam passed from MsgProc.
@param[in] lParam passed from MsgProc.
@param[in] currentMenuPosition Current menu position.
@return HRESULT
@retval S_OK 
@retval E_FAIL 
@note This function is necessary when you customize this file for your camera.
*/
HRESULT customCameraMenu(HWND hWnd, UINT msg, WPARAM wParam, LPARAM lParam, int currentMenuPosition)
{
	switch( msg )
	{
	case WM_KEYDOWN:
		switch(wParam)
		{
		case VK_LEFT:
			switch(currentMenuPosition)
			{
			case CUSTOMMENU_INTENSITY:
				g_Intensity--;
				if(g_Intensity<1)
					g_Intensity = 1;
				g_camera->SetOption(NP_OPTION_INTENSITY,(CComVariant) g_Intensity);
				break;
			case CUSTOMMENU_EXPOSURE:
				g_Exposure--;
				if(g_Exposure<0)
					g_Exposure = 0;
				g_camera->SetOption(NP_OPTION_EXPOSURE,(CComVariant) g_Exposure);
				break;
			default:
				break;
			}
			break;

		case VK_RIGHT:
			switch(currentMenuPosition)
			{
			case CUSTOMMENU_INTENSITY:
				g_Intensity++;
				if(g_Intensity>=12)
					g_Intensity = 12;
				g_camera->SetOption(NP_OPTION_INTENSITY,(CComVariant) g_Intensity);
				break;
			case CUSTOMMENU_EXPOSURE:
				g_Exposure++;
				if(g_Exposure>=479)
					g_Exposure = 479;
				g_camera->SetOption(NP_OPTION_EXPOSURE,(CComVariant) g_Exposure);
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
	_stprintf_s(g_MenuString[CUSTOMMENU_INTENSITY], MENU_STRING_MAX, _T("LightIntensity(%d)"), g_Intensity);
	_stprintf_s(g_MenuString[CUSTOMMENU_EXPOSURE],  MENU_STRING_MAX, _T("CameraExposure(%d)"), g_Exposure);

	return;
}