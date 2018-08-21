/*!
@file Camera.cpp
@author Hiroyuki Sogo
@copyright GNU General Public License (GPL) version 3.
@brief Camera-dependent procedures are defined.

@date 2012/03/23
- Custom menu is supported.
@date 2013/03/15
- Filename is renamed. (Camera_interface.cpp -> Camera_gpc5300.cpp)
*/

#define _CRT_SECURE_NO_DEPRECATE


#include <atlbase.h>
#include "GazeTracker.h"

#include <fstream>
#include <string>


HANDLE g_CameraDeviceHandle; /*!< Holds camera device handle */
HANDLE g_CameraMemHandle; /*!< Holds camera buffer handle */
BOOL g_isWow64; /*!< Process is running on WOW64? */

unsigned char* g_TmpFrameBuffer; /*!< Temporary buffer to hold camera image until CallBackProc() is called.*/
volatile bool g_NewFrameAvailable = false; /*!< True if new camera frame is grabbed. @note This function is necessary when you customize this file for your camera.*/
DWORD g_DigitalInput = 0;

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
CallBackProc: Grab camera images.

@param[in] IntFlg Event ID.
@param[in] User User defined data.
@return no value is returned.

@date 2018/07/27 Change type of the second parameter to migrate to x64
 */
void CALLBACK CallBackProc(DWORD IntFlg, PVOID User)
{
	//error check
	/*
	IFCMLCAPSTS CapSts;
	INT ret;
	ret = CmlGetCaptureStatus(g_CameraDeviceHandle, &CapSts);
	if(ret != IFCML_ERROR_SUCCESS){
		return;
	}*/

	//copy to buffer
	memcpy(g_frameBuffer, g_TmpFrameBuffer, g_CameraWidth*g_CameraHeight*sizeof(unsigned char));
	if(IFCML_ERROR_SUCCESS != CmlInputDI(g_CameraDeviceHandle, &g_DigitalInput)){
		g_LogFS << "WARNING:DI Error" << std::endl;
	};
	g_NewFrameAvailable = true;
}

/*!
initCamera: Initialize camera.

Read parameters from the configuration file, start camera and set callback function.
@attention If there are custom camera menu items, number of custom menu items must be set to g_CustomMenuNum in this function.

@return int
@retval S_OK Camera is successfully initialized.
@retval E_FAIL Initialization is failed.
@note This function is necessary when you customize this file for your camera.
@todo check whether number of custom menus are too many.

@date 2013/03/15
- Argument "ParamPath" was removed. Use g_ParamPath instead.
@date 2013/05/27 a new option, "OUTPUT_DIGITAL_INPUT", was appended.
@date 2013/07/25 support for Wow64 environment.
@date 2013/10/23
- Camera configuration file is customizable.
 */
int initCamera( void )
{
	std::fstream fs;
	std::string fname;
	std::string customCameraCFGname;
	char *p,*pp;
	char buff[1024];
	double param;
	bool isInSection = true; //default is True to support old config file
	bool isCustomCameraCFG = false;
	
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

			//in Section "[SimpleGazeTrackerFlyCapture2]"
			if(buff[0]=='['){
				if(strcmp(buff,"[SimpleGazeTrackerGPC5300]")==0){
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
			param = strtod(p+1,&pp); //parameter is not int but double

			if(strcmp(buff,"OUTPUT_DIGITAL_INPUT")==0)
			{
				if((int)param==1){
					g_isOutputCameraSpecificData = USE_CAMERASPECIFIC_DATA;
				}else if((int)param==0){
					g_isOutputCameraSpecificData = NO_CAMERASPECIFIC_DATA;
				}else{
					g_LogFS << "ERROR: OUTPUT_DIGITAL_INPUT must be 0 or 1." << std::endl;
					fs.close();
					return E_FAIL;
				}
			}
			else if(strcmp(buff,"CUSTOM_CAMERA_CFG_FILE")==0)
			{
				//parameter is str
				customCameraCFGname = p+1;
				isCustomCameraCFG = true;
			}
		}
		fs.close();
	}else{
		snprintf(g_errorMessage, sizeof(g_errorMessage), "Failed to open camera configuration file (%s)", fname.c_str());
		g_LogFS << "ERROR: failed to open camera configuration file (" << fname << ")" << std::endl;
		return E_FAIL;
	}

	if(g_isOutputCameraSpecificData==USE_CAMERASPECIFIC_DATA)
	{
		g_LogFS << "Output digital input of GPC5300" << std::endl;
	}
	if(isCustomCameraCFG)
	{
		g_LogFS << "Use custom camera CFG file(" << customCameraCFGname.c_str() << ")" << std::endl;
	}

	// init camera unit
	INT ret;
	DWORD BufSize;
	IFCMLCAPFMT CapFmt;
	std::string cfgfname;

	HANDLE hProc;
	hProc = GetCurrentProcess();
	IsWow64Process(hProc, &g_isWow64);

	g_CameraDeviceHandle = CmlOpen("IFIMGCML1");
	if(g_CameraDeviceHandle == INVALID_HANDLE_VALUE){
		snprintf(g_errorMessage, sizeof(g_errorMessage), "Failed to open camera device handle (IFIMGCML1).\nCheck IFIMGCML1 is available.");
		g_LogFS << "ERROR: could not get camera device handle" << std::endl;
		return E_FAIL;
	}

	if(!isCustomCameraCFG){
		checkAndCopyFile(g_ParamPath, GPC5300_CONFIG_FILE, g_AppDirPath);

		cfgfname.assign(g_ParamPath);
		cfgfname.append(PATH_SEPARATOR);
		cfgfname.append(GPC5300_CONFIG_FILE);

	}else{
		std::string::size_type index = customCameraCFGname.find(PATH_SEPARATOR);
		if(index == std::string::npos){
			cfgfname.assign(g_ParamPath);
			cfgfname.append(PATH_SEPARATOR);
			cfgfname.append(customCameraCFGname);
		}
		else //full path?
		{
			cfgfname = customCameraCFGname;
		}
	}
	
	ret = CmlReadCamConfFile(g_CameraDeviceHandle,cfgfname.c_str());
	
	if(ret != IFCML_ERROR_SUCCESS){
		snprintf(g_errorMessage, sizeof(g_errorMessage), "Failed to open camera configuration file (%s)", cfgfname.c_str());
		g_LogFS << "ERROR: could not read camera configuration file(" << cfgfname << ")" << std::endl;
		CmlClose(g_CameraDeviceHandle);
		return E_FAIL;
	}
	
	// Configure the dataformat and the information of buffer.
	CapFmt.Rect.XStart = 0;
	CapFmt.Rect.YStart = 0;
	CapFmt.Rect.XLength = g_CameraWidth;
	CapFmt.Rect.YLength = g_CameraHeight;		
	CapFmt.Scale.PixelCnt = 0;
	CapFmt.Scale.LineCnt = 0;
	CapFmt.CapFormat = IFCML_CAPFMT_CAM;
	CapFmt.OptionFormat = IFCML_OPTFMT_NON;

	ret = CmlSetCaptureFormatInfo(g_CameraDeviceHandle, &CapFmt);
	if(ret != IFCML_ERROR_SUCCESS){
		snprintf(g_errorMessage, sizeof(g_errorMessage), "Failed to set camera image format.");
		g_LogFS << "ERROR: could not set camera image format" << std::endl;
		CmlClose(g_CameraDeviceHandle);
		return E_FAIL;
	}

	if(g_isWow64){
		g_LogFS << "Running on WOW64... Yes" << std::endl;
		PVOID MemoryAddress;
		// Allocate the buffer for storing the image data.
		BufSize = CapFmt.FrameSize_Buf;

		ret =  CmlRegistMemInfo(g_CameraDeviceHandle, (PVOID)-1, BufSize, &g_CameraMemHandle);
		if(ret != IFCML_ERROR_SUCCESS){
			snprintf(g_errorMessage, sizeof(g_errorMessage), "Failed to register meminfo.");
			g_LogFS << "ERROR: could not register meminfo" << std::endl;
			CmlClose(g_CameraDeviceHandle);
			return E_FAIL;
		}
		CmlGetMemPtrValue(g_CameraDeviceHandle, g_CameraMemHandle, &MemoryAddress);
		if(ret != IFCML_ERROR_SUCCESS){
			snprintf(g_errorMessage, sizeof(g_errorMessage), "Failed to get memory pointer.");
			g_LogFS << "ERROR: could not get memory pointer" << std::endl;
			CmlClose(g_CameraDeviceHandle);
			return E_FAIL;
		}
		g_TmpFrameBuffer = (unsigned char*)MemoryAddress;

	}else{
		g_LogFS << "Running on WOW64... No" << std::endl;
		g_TmpFrameBuffer = (unsigned char*)malloc(g_CameraWidth*g_CameraHeight*sizeof(unsigned char));
		if(g_TmpFrameBuffer==NULL)
		{
			snprintf(g_errorMessage, sizeof(g_errorMessage), "Failed to allocate working buffer.");
			g_LogFS << "ERROR: failed to allocate working buffer" << std::endl;
			CmlClose(g_CameraDeviceHandle);
			return E_FAIL;
		}

		// Allocate the buffer for storing the image data.
		BufSize = CapFmt.FrameSize_Buf;

		ret =  CmlRegistMemInfo(g_CameraDeviceHandle, g_TmpFrameBuffer, BufSize, &g_CameraMemHandle);
		if(ret != IFCML_ERROR_SUCCESS){
			snprintf(g_errorMessage, sizeof(g_errorMessage), "Failed to register meminfo.");
			g_LogFS << "ERROR: could not register meminfo.)" << std::endl;
			CmlClose(g_CameraDeviceHandle);
			return E_FAIL;
		}
	}


	// Set Capture Configration
	ret = CmlSetCapConfig(g_CameraDeviceHandle, g_CameraMemHandle, &CapFmt);
	if(ret != IFCML_ERROR_SUCCESS){
		snprintf(g_errorMessage, sizeof(g_errorMessage), "Failed to set camera configuration.");
		g_LogFS << "ERROR: could not set camera configuration)" << std::endl;
		CmlClose(g_CameraDeviceHandle);
		return E_FAIL;
	}

	CmlOutputPower(g_CameraDeviceHandle,IFCML_PWR_ON);
	if(ret != IFCML_ERROR_SUCCESS){
		snprintf(g_errorMessage, sizeof(g_errorMessage), "Failed to turn the camera on.");
		g_LogFS << "ERROR: could not turn the camera on)" << std::endl;
		CmlClose(g_CameraDeviceHandle);
		return E_FAIL;
	}
	Sleep(1000);

	////interrupt////
	IFCMLEVENTREQ Event;
	Event.WndHandle = NULL;
	Event.MessageCode = 0;
	Event.CallBackProc = CallBackProc;
	Event.User = 0;

	ret = CmlSetEventMask(g_CameraDeviceHandle, 0x03);
	if(ret != IFCML_ERROR_SUCCESS){
		snprintf(g_errorMessage, sizeof(g_errorMessage), "Failed to set event mask.");
		g_LogFS << "ERROR: could not set event mask)" << std::endl;
		CmlClose(g_CameraDeviceHandle);
		return E_FAIL;
	}
	ret = CmlSetEvent(g_CameraDeviceHandle,&Event);
	if(ret != IFCML_ERROR_SUCCESS){
		snprintf(g_errorMessage, sizeof(g_errorMessage), "Failed to set event mask.");
		g_LogFS << "ERROR: could not set event)" << std::endl;
		CmlClose(g_CameraDeviceHandle);
		return E_FAIL;
	}

	ret = CmlStartCapture(g_CameraDeviceHandle, 0 ,IFCML_CAM_DMA | IFCML_CAP_ASYNC);
	if(ret != IFCML_ERROR_SUCCESS){
		snprintf(g_errorMessage, sizeof(g_errorMessage), "Failed to start capturing.");
		g_LogFS << "ERROR: could not start capture)" << std::endl;
		CmlClose(g_CameraDeviceHandle);
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
	int ret;
	ret = CmlStopCapture(g_CameraDeviceHandle,IFCML_DMA_STOP);
	ret = CmlFreeMemInfo(g_CameraDeviceHandle,g_CameraMemHandle);
	ret = CmlClose(g_CameraDeviceHandle);
	CmlOutputPower(g_CameraDeviceHandle,IFCML_PWR_OFF);
	if(g_TmpFrameBuffer!=NULL && !g_isWow64)
	{
		free(g_TmpFrameBuffer);
		g_TmpFrameBuffer = NULL;
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
	return (unsigned int)g_DigitalInput;
}