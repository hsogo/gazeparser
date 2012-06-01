/*!
@file Camera.cpp
@author Hiroyuki Sogo
@copyright GNU General Public License (GPL) version 3.
@brief Camera-dependent procedures are defined.

@date 2012/03/23
- Custom menu is supported.
*/

#define _CRT_SECURE_NO_DEPRECATE


#include <atlbase.h>
#include "GazeTracker.h"

#include <fstream>
#include <iostream>
#include <string>

#include "C:\Program Files\Interface\GPC5300\include\IFCml.h"


HANDLE g_CameraDeviceHandle; /*!< Holds camera device handle */
HANDLE g_CameraMemHandle; /*!< Holds camera buffer handle */

unsigned char* g_TmpFrameBuffer; /*!< Temporary buffer to hold camera image until CallBackProc() is called.*/
volatile bool g_NewFrameAvailable = false; /*!< True if new camera frame is grabbed. @note This function is necessary when you customize this file for your camera.*/


/*!
CallBackProc: Grab camera images.

@param[in] IntFlg Event ID.
@param[in] User User defined data.
@return no value is returned.
 */
void CALLBACK CallBackProc(DWORD IntFlg, DWORD User)
{
	memcpy(g_frameBuffer, g_TmpFrameBuffer, g_CameraWidth*g_CameraHeight*sizeof(unsigned char));
	g_NewFrameAvailable = true;
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
 */
int initCamera( char* ParamPath )
{
	INT				ret;
	DWORD			BufSize;
	IFCMLCAPFMT     CapFmt;
	char            buff[512];

	g_TmpFrameBuffer = (unsigned char*)malloc(g_CameraWidth*g_CameraHeight*sizeof(unsigned char));

	g_CameraDeviceHandle = CmlOpen("IFIMGCML1");
	if(g_CameraDeviceHandle == INVALID_HANDLE_VALUE){
		return E_FAIL;
	}

	strcpy(buff, ParamPath);
	strcat(buff, CAMERA_CONFIG_FILE);
	if(!PathFileExists(buff)){
		char exefile[512];
		char configfile[512];
		char drive[4],dir[512],fname[32],ext[5];
		errno_t r;
		GetModuleFileName(NULL,exefile,sizeof(exefile));
		r = _splitpath_s(exefile,drive,sizeof(drive),dir,sizeof(dir),fname,sizeof(fname),ext,sizeof(ext));
		strcpy(configfile,drive);
		strcat(configfile,dir);
		strcat(configfile,CAMERA_CONFIG_FILE);
		CopyFile(configfile,buff,true);
	}
	
	ret = CmlReadCamConfFile(g_CameraDeviceHandle,buff);
	
	if(ret != IFCML_ERROR_SUCCESS){
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
		CmlClose(g_CameraDeviceHandle);
		return E_FAIL;
	}

	// Allocate the buffer for storing the image data.
	BufSize = CapFmt.FrameSize_Buf;

	ret =  CmlRegistMemInfo(g_CameraDeviceHandle, g_TmpFrameBuffer, BufSize, &g_CameraMemHandle);
	if(ret != IFCML_ERROR_SUCCESS){
		CmlClose(g_CameraDeviceHandle);
		return E_FAIL;
	}

	// Set Capture Configration
	ret = CmlSetCapConfig(g_CameraDeviceHandle,g_CameraMemHandle,&CapFmt);
	if(ret != IFCML_ERROR_SUCCESS){
		CmlClose(g_CameraDeviceHandle);
		return E_FAIL;
	}

	CmlOutputPower(g_CameraDeviceHandle,IFCML_PWR_ON);
	Sleep(1000);

	////interrupt////
	IFCMLEVENTREQ Event;
	Event.WndHandle = NULL;
	Event.MessageCode = 0;
	Event.CallBackProc = CallBackProc;
	Event.User = 0;

	DWORD EventMask = 0x03;
	ret = CmlSetEventMask(g_CameraDeviceHandle,EventMask);
	ret = CmlSetEvent(g_CameraDeviceHandle,&Event);

	ret = CmlStartCapture(g_CameraDeviceHandle, 0 ,IFCML_CAM_DMA | IFCML_CAP_ASYNC);
	////interrupt////

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
	if(g_TmpFrameBuffer!=NULL)
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
 */
void saveCameraParameters(char* ParamPath)
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