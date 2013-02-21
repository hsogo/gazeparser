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
#include <string>

FlyCapture2::Camera g_FC2Camera;
FlyCapture2::PGRGuid g_FC2CameraGUID;
FlyCapture2::Image g_rawImage;

HANDLE g_CameraDeviceHandle; /*!< Holds camera device handle */
HANDLE g_CameraMemHandle; /*!< Holds camera buffer handle */

unsigned char* g_TmpFrameBuffer; /*!< Temporary buffer to hold camera image until CallBackProc() is called.*/
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
CallBackProc: Grab camera images.

@param[in] IntFlg Event ID.
@param[in] User User defined data.
@return no value is returned.
 
void CALLBACK CallBackProc(DWORD IntFlg, DWORD User)
{
	memcpy(g_frameBuffer, g_TmpFrameBuffer, g_CameraWidth*g_CameraHeight*sizeof(unsigned char));
	g_NewFrameAvailable = true;
}
*/

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
int initCamera( const char* ParamPath )
{
	FlyCapture2::Error error;

	FlyCapture2::BusManager busMgr;
	unsigned int numCameras;
	error = busMgr.GetNumOfCameras(&numCameras);
	if(error != FlyCapture2::PGRERROR_OK)
	{
		g_LogFS << "ERROR: failed to get FlyCapture2 camera" << std::endl;
		return E_FAIL;
	}

	if(numCameras<=0){
		g_LogFS << "ERROR: no FlyCapture2 camera was found" << std::endl;
		return E_FAIL;
	}

	error = busMgr.GetCameraFromIndex(0, &g_FC2CameraGUID);
	if(error != FlyCapture2::PGRERROR_OK)
	{
		g_LogFS << "ERROR: Could not get FlyCapture2 camera from index" << std::endl;
		return E_FAIL;
	}

	// Connect to a camera
	error = g_FC2Camera.Connect(&g_FC2CameraGUID);
	if (error != FlyCapture2::PGRERROR_OK)
	{
		g_LogFS << "ERROR: failed to connect to FlyCapture2 camera" << std::endl;
		return E_FAIL;
	}

	FlyCapture2::FC2Config Config;
	FlyCapture2::Format7ImageSettings imageSettings;
	FlyCapture2::Format7PacketInfo packetInfo;
	FlyCapture2::Property prop;
	FlyCapture2::PropertyInfo propInfo;
	unsigned int packetSize;
	float percentage;
	bool settingsAreValid;

	//set Format7 configuration
	g_FC2Camera.GetFormat7Configuration(&imageSettings, &packetSize, &percentage);
	imageSettings.mode = FlyCapture2::MODE_1;
	imageSettings.width=g_CameraWidth;
	imageSettings.height=g_CameraHeight;
	imageSettings.offsetX = (640-g_CameraWidth)/2;  //TODO: read from configuration file
	imageSettings.offsetY = (512-g_CameraHeight)/2; //TODO: read from configuration file
	imageSettings.pixelFormat = FlyCapture2::PIXEL_FORMAT_RAW8;
	g_FC2Camera.ValidateFormat7Settings(&imageSettings, &settingsAreValid, &packetInfo);
	error = g_FC2Camera.SetFormat7Configuration(&imageSettings, packetInfo.recommendedBytesPerPacket);
	error = g_FC2Camera.GetFormat7Configuration(&imageSettings, &packetSize, &percentage);

	//set frame rate (manual)
	prop.type = FlyCapture2::FRAME_RATE;
	prop.autoManualMode = false;
	prop.onOff = true;
	prop.absControl = true;
	prop.absValue = 250.0; //TODO: read from configuration file
	error = g_FC2Camera.SetProperty(&prop);
	error = g_FC2Camera.GetProperty(&prop);

	//set grabTimeout = 0 (immediate) 
	g_FC2Camera.GetConfiguration(&Config);
	Config.grabTimeout = 0;
	error = g_FC2Camera.SetConfiguration(&Config);


	error = g_FC2Camera.StartCapture();
	if (error != FlyCapture2::PGRERROR_OK)
	{
		g_LogFS << "ERROR: failed to start capture by FlyCapture2 camera" << std::endl;
		return E_FAIL;
	}

	//checkAndCopyFile(g_ParamPath,CAMERA_CONFIG_FILE,g_AppDirPath);


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
	FlyCapture2::Error error;

	error = g_FC2Camera.RetrieveBuffer( &g_rawImage );
	if(error == FlyCapture2::PGRERROR_OK)
	{
		memcpy(g_frameBuffer, g_rawImage.GetData(), g_CameraWidth*g_CameraHeight*sizeof(unsigned char));
		g_NewFrameAvailable = true;
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
	FlyCapture2::Error error;

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

	//need to shutdown BusManager?
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
