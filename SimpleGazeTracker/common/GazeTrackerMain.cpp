/*!
@file GazeTrackerMain.cpp
@author Hiroyuki Sogo
@copyright GNU General Public License (GPL) version 3.

@brief Main part of SimpleGazeTracker application.

@date 2012/03/23
- Custom menu is supported.
@date 2012/07/30
- EOG-SimpleGazeTracker concurrent recording mode is appended.  To use this mode, define __DEBUG_WITH_GPC3100.
@date 2015/09/08
- __DEBUG_WITH_GPC3100 is removed. Use USB IO units for debug.
*/

#define _CRT_SECURE_NO_WARNINGS

#include <SDL2/SDL.h>
#include <SDL2/SDL_ttf.h>

#include <fstream>
#include <iostream>

#include <opencv2/opencv.hpp>
#include <opencv2/core/core.hpp>

#include "GazeTrackerCommon.h"

#ifdef _WIN32
#include "resource.h"
#include <windows.h>
#include <atlbase.h>
#include <time.h>
#include <process.h>
#endif

#define MENU_ITEM_HEIGHT 22
#define MENU_FONT_SIZE 18

#define PANEL_WIDTH  256
#define PANEL_HEIGHT 512
#define	PANEL_OFFSET_X 25
#define	PANEL_OFFSET_Y 20
#define CURSOR_SIZE 12
#define CURSOR_OFFSET 5

/*! Holds menu texts. 
@attention Number of menu items (sum of original items and custom items) and 
length of custom menu texts must be smaller than MENU_MAX_ITEMS and MENU_STRING_MAX, respectively.
*/
std::string g_MenuString[MENU_MAX_ITEMS];

//SDL_Surface* g_pSDLscreen;
SDL_Window* g_pSDLwindow;
SDL_Renderer* g_pSDLrenderer;
SDL_Texture* g_pSDLtexture;
SDL_Surface* g_pSDLscreen;
SDL_Surface* g_pCameraTextureSurface;
SDL_Surface* g_pCalResultTextureSurface;
SDL_Surface* g_pPanelSurface;
TTF_Font* g_Font;

unsigned char* g_frameBuffer;
int* g_pCameraTextureBuffer;
int* g_pCalResultTextureBuffer;
int g_CameraWidth;
int g_CameraHeight;
int g_PreviewWidth;
int g_PreviewHeight;
int g_ROIWidth;
int g_ROIHeight;
int g_MorphologicalTrans;

int g_Threshold = 55;  /*!< Pupil candidates are sought from image areas darker than this value. */
int g_MaxPupilWidth = 30; /*!< Dark areas wider than this value is removed from pupil candidates. */
int g_MinPupilWidth = 10; /*!< Dark areas narrower than this value is removed from pupil candidates. */
int g_PurkinjeThreshold = 240;  /*!<  */
int g_PurkinjeSearchArea = 60;  /*!<  */
int g_PurkinjeExcludeArea = 20; /*!<  */

bool g_isShowingCameraImage = true; /*!< If true, camera image is rendered. This must be false while recording.*/


std::string g_ParamPath; /*!< Holds path to the parameter file directory*/
std::string g_DataPath;  /*!< Holds path to the data file directory*/
std::string g_AppDirPath;   /*!< Holds path to the executable file directory*/

int g_CurrentMenuPosition = 0;  /*!< Holds current menu position.*/
int g_CustomMenuNum = 0; /*!< Holds how many custom menu items are defined.*/

double g_EyeData[MAXDATA][4]; /*!< Holds the center of purkinje image relative to the center of pupil. Only two columns are used when recording mode is monocular.*/
double g_PupilSizeData[MAXDATA][2]; /*!< Holds pupil size*/
double g_TickData[MAXDATA]; /*!< Holids tickcount when data was obtained. */
double g_CalPointData[MAXCALDATA][2]; /*!< Holds where the calibration item is presented when calibration data is sampled.*/
bool g_CalPointDelList[MAXCALDATA];
double g_ParamX[6]; /*!< Holds calibration parameters for X coordinate. Only three elements are used when recording mode is monocular.*/
double g_ParamY[6]; /*!< Holds calibration parameters for Y coordinate. Only three elements are used when recording mode is monocular.*/
double g_CalibrationArea[4]; /*!< Holds calibration area. These values are used when calibration results are rendered.*/
unsigned int g_CameraSpecificData[MAXDATA]; /*!< Holds camera-specific data*/

double g_CurrentEyeData[4]; /*!< Holds latest data. Only two elements are used when recording mode is monocular.*/
double g_CurrentPupilSize[2]; /*!< Holds latest data. Only one element is used when recording mode is monocular.*/
double g_CurrentCalPoint[2]; /*!< Holds current position of the calibration target. */
int g_NumCalPoint; /*!< Sum of the number of sampled calibration data.*/
int g_CalSamplesAtCurrentPoint; /*!< Number of calibdation data to be sampled at the current target position.*/

double g_CalGoodness[4]; /*!< Holds goodness of calibration results, defined as a ratio of linear regression coefficients to screen size. Only two elements are used when recording mode is monocular.*/
double g_CalMaxError[2]; /*!< Holds maximum calibration error. Only one element is used when recording mode is monocular.*/
double g_CalMeanError[2]; /*!< Holds mean calibration error. Only one element is used when recording mode is monocular.*/

int g_RecordingMode = RECORDING_BINOCULAR; /*!< Holds recording mode. @note This value is modified only when application is being initialized (i.e. in initParameters()).*/
int g_isShowDetectionErrorMsg = 0; /*!< Holds DetectionError message visibility.*/
int g_isOutputPupilSize = 1; /*!< Holds whether pupil size is output to datafile.*/
int g_isOutputCameraSpecificData = NO_CAMERASPECIFIC_DATA;/*!< Holds whether camera-specific data is output to datafile.*/

int g_DataCounter = 0;
int g_LastSentDataCounter = 0;
bool g_isRecording = false;
bool g_isCalibrating = false;
bool g_isValidating = false;
bool g_isCalibrated = false;
bool g_isShowingCalResult = false;
int g_lastCalValType = TYPE_CALIBRATION;

double g_RecStartTime;

double g_CalPointList[MAXCALPOINT][2];
double g_CalPointPrecision[MAXCALPOINT][4];
double g_CalPointAccuracy[MAXCALPOINT][4];

double g_LastCalPointList[MAXCALPOINT][2];
int g_LastNumCalPoint;

FILE* g_DataFP;
std::fstream g_LogFS;

std::string g_ConfigFileName;

char g_MessageBuffer[MAXMESSAGE];
int g_MessageEnd;

int g_PortRecv = PORT_RECV;
int g_PortSend = PORT_SEND;
int g_DelayCorrection = 0;

bool g_isInhibitRendering = false;
bool g_openSetupGuide = true;

double g_MeanInterFrameInterval;
double g_StdInterFrameInterval;

std::string g_USBIOBoard;
std::string g_USBIOParamAD;
std::string g_USBIOParamDI;

char g_recordingMessage[256];

int g_captureNum = 0;

char g_errorMessage[1024];


/*!
initParameters: Read parameters from the configuration file to initialize application.

Data directory is set to %HOMEDRIVE%%HOMEPATH%\GazeTracker.
Configuration file directory is set to %APPDATA%\GazeTracker.

Following parameters are read from a configuration file (specified by g_ConfigFileName).

-THRESHOLD  (g_Threshold)
-MAX_PUPIL_WIDTH  (g_MaxPupilWidth)
-MIN_PUPIL_WIDTH  (g_MinPupilWidth)
-PURKINJE_THRESHOLD  (g_PurkinjeThreshold)
-PURKINJE_SEARCHAREA  (g_PurkinjeSearchArea)
-PURKINJE_EXCLUDEAREA  (g_PurkinjeExcludeArea)
-BINOCULAR  (g_RecordingMode)
-CAMERA_WIDTH  (g_CameraWidth)
-CAMERA_HEIGHT  (g_CameraHeight)
-PREVIEW_WIDTH  (g_PreviewWidth)
-PREVIEW_HEIGHT  (g_PreviewHeight)
-SHOW_DETECTIONERROR_MSG  (g_isShowDetectionErrorMsg)
-PORT_RECV  (g_PortRecv)
-PORT_SEND  (g_PortSend)
-DELAY_CORRECTION  (g_DelayCorrection)
-OUTPUT_PUPILSIZE (g_isOuputPupilArea)
-USBIO_BOARD (g_USBIOBoard)
-USBIO_AD (g_USBIOParamAD)
-USBIO_DI (g_USBIOParamDI)
-USB_USE_THREAD (g_useUSBThread)
-OPEN_SETUP_GUIDE (g_openSetupGuide)
-MORPH_TRANS (g_MorphologicalTrans)

@return int
@retval S_OK Camera is successfully initialized.
@retval E_FAIL Initialization is failed.

@date 2012/04/06 CAMERA_WIDTH, CAMERA_HEIGHT, PREVIEW_WIDTH and PREVIEW_HEIGHT are supported.
@date 2012/07/17 ROI_WIDTH, ROI_HEIGHT and SHOW_DETECTIONERROR_MSG are supported.
@date 2012/07/26 DELAY_CORRECTION, PORT_SEND and PORT_RECV are supported.
@date 2012/11/05
- Section header [SimpleGazeTrackerCommon] is supported.
- spaces and tabs around '=' are removed.
@date 2012/12/05 checkDirectory is renamed to checkAndCreateDirectory.
@date 2013/10/22 configuration file name can be specified by g_ConfigFileName.
@date 2013/12/12 USBIO_BOARD, USBIO_AD and USBIO_DI is supported.
@date 2013/12/24 USB_USE_THREAD is supported.
@date 2015/03/12 MAXPOINTS and MINPOINTS are changed to MAXWIDTH and MINWIDTH.
@date 2015/06/15 RENDER_DURING_REC is supported.
@date 2015/09/02 RENDER_DURING_REC is removed.
@date 2015/09/08 set g_errorMessage when failed.
@date 2018/08/09 OPEN_SETUP_GUIDE is supported.
@date 2019/11/27 MORPH_TRANS is supported.
@date 2020/03/16 
 */
int initParameters( void )
{
	std::fstream fs;
	std::string fname;
	char buff[1024];
	char *p,*pp;
	int param;
	bool inCommonSection = false;
	bool inCameraSection = false;

	fname.assign(g_ParamPath);
	fname.append(PATH_SEPARATOR);
	fname.append(g_ConfigFileName.c_str());
	fs.open(fname.c_str(), std::ios::in);
	if(!fs.is_open())
	{
		snprintf(g_errorMessage, sizeof(g_errorMessage), "Failed to open  %s", fname.c_str());
		g_LogFS << "Failed to open " << fname << "." << std::endl;
		return E_FAIL;
	}
	g_LogFS << "Configuration file is " << fname << "." << std::endl;

	while(fs.getline(buff,sizeof(buff)))
	{
		if(buff[0]=='#') continue; //comments
		
		//in Section "[SimpleGazeTrackerCommon]"
		if(buff[0]=='['){
			if(strcmp(buff,"[SimpleGazeTrackerCommon]")==0){
				inCommonSection = true;
				inCameraSection = false;
			}
			else if (strcmp(buff, "[SimpleGazeTrackerCamera]") == 0)
			{
				inCommonSection = false;
				inCameraSection = true;

			}else
			{
				inCommonSection = false;
				inCameraSection = false;
			}
			continue;
		}
		
		if(!(inCommonSection || inCameraSection)) continue; //not in section
		
		//Check options.
		//If "=" is not included, this line is not option.
		if((p=strchr(buff,'='))==NULL) continue;

		//remove space/tab
		*p = '\0';
		while (*(p - 1) == 0x09 || *(p - 1) == 0x20)
		{
			p--;
			*p = '\0';
		}
		while (*(p + 1) == 0x09 || *(p + 1) == 0x20) p++;

		// get first character of the parameter value
		p += 1;

		if (inCommonSection) {
			//interpret as integer
			param = strtol(p, &pp, 10);

			if (strcmp(buff, "THRESHOLD") == 0) g_Threshold = param;
			else if (strcmp(buff, "MAX_PUPIL_WIDTH") == 0) g_MaxPupilWidth = param;
			else if (strcmp(buff, "MIN_PUPIL_WIDTH") == 0) g_MinPupilWidth = param;
			else if (strcmp(buff, "PURKINJE_THRESHOLD") == 0) g_PurkinjeThreshold = param;
			else if (strcmp(buff, "PURKINJE_SEARCHAREA") == 0) g_PurkinjeSearchArea = param;
			else if (strcmp(buff, "PURKINJE_EXCLUDEAREA") == 0) g_PurkinjeExcludeArea = param;
			else if (strcmp(buff, "BINOCULAR") == 0) g_RecordingMode = param;
			else if (strcmp(buff, "CAMERA_WIDTH") == 0) g_CameraWidth = param;
			else if (strcmp(buff, "CAMERA_HEIGHT") == 0) g_CameraHeight = param;
			else if (strcmp(buff, "PREVIEW_WIDTH") == 0) g_PreviewWidth = param;
			else if (strcmp(buff, "PREVIEW_HEIGHT") == 0) g_PreviewHeight = param;
			else if (strcmp(buff, "ROI_WIDTH") == 0) g_ROIWidth = param;
			else if (strcmp(buff, "ROI_HEIGHT") == 0) g_ROIHeight = param;
			else if (strcmp(buff, "SHOW_DETECTIONERROR_MSG") == 0) g_isShowDetectionErrorMsg = param;
			else if (strcmp(buff, "PORT_SEND") == 0) g_PortSend = param;
			else if (strcmp(buff, "PORT_RECV") == 0) g_PortRecv = param;
			else if (strcmp(buff, "DELAY_CORRECTION") == 0) g_DelayCorrection = param;
			else if (strcmp(buff, "OUTPUT_PUPILSIZE") == 0) g_isOutputPupilSize = param;
			else if (strcmp(buff, "USBIO_BOARD") == 0) g_USBIOBoard = p;
			else if (strcmp(buff, "USBIO_AD") == 0) g_USBIOParamAD = p;
			else if (strcmp(buff, "USBIO_DI") == 0) g_USBIOParamDI = p;
			else if (strcmp(buff, "USB_USE_THREAD") == 0) g_useUSBThread = (param != 0) ? true : false;
			else if (strcmp(buff, "OPEN_SETUP_GUIDE") == 0) g_openSetupGuide = (param != 0) ? true : false;
			else if (strcmp(buff, "MORPH_TRANS") == 0) g_MorphologicalTrans = param;
			//obsolete parameters
			else if (strcmp(buff, "MAXPOINTS") == 0) {
				printf("Warning: MAXPINTS is obsolete in this version. Use MAX_PUPIL_WIDTH instead.");
				g_LogFS << "Warning: MAXPINTS is obsolete in this version. Use MAX_PUPIL_WIDTH instead." << std::endl;
			}
			else if (strcmp(buff, "MINPOINTS") == 0) {
				printf("Warning: MINPINTS is obsolete in this version. Use MIN_PUPIL_WIDTH instead.");
				g_LogFS << "Warning: MINPINTS is obsolete in this version. Use MIN_PUPIL_WIDTH instead." << std::endl;
			}
			//unknown option
			else {
				snprintf(g_errorMessage, sizeof(g_errorMessage), "Unknown option (\"%s\")\nPlease check %s", buff, joinPath(g_ParamPath, g_ConfigFileName).c_str());
				g_LogFS << "Error: Unknown option in configuration file (" << buff << ")" << std::endl;
				return E_FAIL;
			}
		}
		else if(inCameraSection){
			if (FAILED(initCameraParameters(buff, p))) {
				g_LogFS << "Warning: Unknown camera specific option in configuration file (" << buff << ")" << std::endl;
				// return E_FAIL;
			}
		}
	}
	
	if(g_CameraWidth*g_CameraHeight==0)
	{
		snprintf(g_errorMessage, sizeof(g_errorMessage), "Value of CAMERA_WIDTH and/or CAMERA_HEIGHT is zero.\nCheck  %s", joinPath(g_ParamPath, g_ConfigFileName).c_str());
		g_LogFS << "Error: Value of CAMERA_WIDTH and/or CAMERA_HEIGHT is zero. Please check configration file." << std::endl;
		return E_FAIL;
	}

	if(g_ROIWidth==0) g_ROIWidth = g_CameraWidth;
	if(g_ROIHeight==0) g_ROIHeight = g_CameraHeight;
	
	fs.close();

	return S_OK;
}

/*!
saveParameters: Save current parameters to the configuration file.

Following parameters are wrote to the configuration file.

-THRESHOLD  (g_Threshold)
-MAX_PUPIL_WIDTH  (g_MaxPupilWidht)
-MIN_PUPIL_WIDTH  (g_MinPupilWidth)
-PURKINJE_THRESHOLD  (g_PurkinjeThreshold)
-PURKINJE_SEARCHAREA  (g_PurkinjeSearchArea)
-PURKINJE_EXCLUDEAREA  (g_PurkinjeExcludeArea)
-BINOCULAR  (g_RecordingMode)
-CAMERA_WIDTH  (g_CameraWidth)
-CAMERA_HEIGHT  (g_CameraHeight)
-PREVIEW_WIDTH  (g_PreviewWidth)
-PREVIEW_HEIGHT  (g_PreviewHeight)
-ROI_WIDTH  (g_ROIWidth)
-ROI_HEIGHT  (g_ROIHeight)
-SHOW_DETECTIONERROR_MSG  (g_isShowDetectionErrorMsg)
-PORT_RECV  (g_PortRecv)
-PORT_SEND  (g_PortSend)
-DELAY_CORRECTION  (g_DelayCorrection)
-OUTPUT_PUPILSIZE  (g_isOutputPupilSize)
-USBIO_BOARD (g_USBIOBoard)
-USBIO_AD (g_USBIOParamAD)
-USBIO_DI (g_USBIOParamDI)
-USB_USE_THREAD (g_useUSBThread)
-OPEN_SETUP_GUIDE (g_openSetupGuide)
-MORPH_TRANS (g_MorphologicalTrans)

@return int
@retval S_OK Camera is successfully initialized.
@retval E_FAIL Initialization is failed.

@date 2012/04/06 CAMERA_WIDTH, CAMERA_HEIGHT, PREVIEW_WIDTH and PREVIEW_HEIGHT are supported.
@date 2012/07/17 ROI_WIDTH, ROI_Height, SHOW_DETECTIONERROR_MSG are supported.
@date 2012/07/26 DELAY_CORRECTION, PORT_SEND and PORT_RECV are supported.
@date 2012/09/28 OUTPUT_PUPILSIZE is supported.
@date 2012/11/05 section name [SimpleGazeTrackerCommon] is output.
@date 2013/03/26 Output log message.
@date 2013/12/13 USBIO_BOARD, USBIO_AD and USBIO_DI is supported.
@date 2013/12/24 USB_USE_THREAD is supported.
@date 2015/03/12 MAXPOINTS and MINPOINTS are changed to MAXWIDTH and MINWIDTH.
@date 2015/06/15 RENDER_DURING_REC is supported.
@date 2015/09/02 RENDER_DURING_REC is removed.
@date 2015/09/08 return 
@date 2018/08/10 OPEN_SETUP_GUIDE is supported.
@date 2019/11/27 MORPH_TRANS is supported.

*/
int saveParameters( void )
{
	std::fstream fs;
	std::string fname(g_ParamPath);

	fname.append(PATH_SEPARATOR);
	fname.append(g_ConfigFileName);

	g_LogFS << "Saving parameters to "<< fname << " ... ";

	fs.open(fname.c_str(),std::ios::out);
	if(!fs.is_open())
	{
		snprintf(g_errorMessage, sizeof(g_errorMessage), "Failed to save parameters to %s.\nThe file may be write protected or opened by another program.", fname.c_str());
		g_LogFS  << std::endl << "Error: can't open " << fname << "." << std::endl;
		return E_FAIL;
	}

	fs << "#If you want to recover original settings, delete this file and start eye tracker program." << std::endl;
	fs << "[SimpleGazeTrackerCommon]" << std::endl;
	fs << "THRESHOLD=" << g_Threshold << std::endl;
	fs << "MAX_PUPIL_WIDTH=" << g_MaxPupilWidth << std::endl;
	fs << "MIN_PUPIL_WIDTH=" << g_MinPupilWidth << std::endl;
	fs << "PURKINJE_THRESHOLD=" << g_PurkinjeThreshold << std::endl;
	fs << "PURKINJE_SEARCHAREA=" << g_PurkinjeSearchArea << std::endl;
	fs << "PURKINJE_EXCLUDEAREA=" << g_PurkinjeExcludeArea << std::endl;
	fs << "BINOCULAR=" << g_RecordingMode << std::endl;
	fs << "CAMERA_WIDTH=" <<  g_CameraWidth << std::endl;
	fs << "CAMERA_HEIGHT=" <<  g_CameraHeight << std::endl;
	fs << "PREVIEW_WIDTH=" <<  g_PreviewWidth << std::endl;
	fs << "PREVIEW_HEIGHT=" <<  g_PreviewHeight << std::endl;
	if(g_ROIWidth==g_CameraWidth)
	{
		fs << "ROI_WIDTH=0" << std::endl;	
	}
	else{
		fs << "ROI_WIDTH=" <<  g_ROIWidth << std::endl;
	}
	if(g_ROIHeight==g_CameraHeight)
	{
		fs << "ROI_HEIGHT=0" << std::endl;	
	}
	else
	{
		fs << "ROI_HEIGHT=" <<  g_ROIHeight << std::endl;
	}
	fs << "SHOW_DETECTIONERROR_MSG=" << g_isShowDetectionErrorMsg << std::endl;
	fs << "PORT_SEND=" <<  g_PortSend << std::endl;
	fs << "PORT_RECV=" <<  g_PortRecv << std::endl;
	fs << "DELAY_CORRECTION=" << g_DelayCorrection << std::endl;
	fs << "OUTPUT_PUPILSIZE=" << g_isOutputPupilSize << std::endl;
	fs << "USBIO_BOARD=" << g_USBIOBoard << std::endl;
	fs << "USBIO_AD=" << g_USBIOParamAD << std::endl;
	fs << "USBIO_DI=" << g_USBIOParamDI << std::endl;
	fs << "USB_USE_THREAD=" << (g_useUSBThread? "1" : "0") << std::endl;
	fs << "OPEN_SETUP_GUIDE=" << (g_openSetupGuide ? "1" : "0") << std::endl;
	fs << "MORPH_TRANS=" << g_MorphologicalTrans << std::endl;

	fs << std::endl << "[SimpleGazeTrackerCamera]" <<std::endl;
	saveCameraParameters( &fs );

	fs.close();

	g_LogFS << "OK." << std::endl;
	return S_OK;
}


/*
openHTMLdoc: open HTML help document

@param[in] doc Name of document file

@return E_FAIL if document is not found.
@date 2018/08/21 Created.
*/
int openHTMLdoc(std::string doc)
{
	std::string path;
	path.assign(g_AppDirPath);
	path.append(PATH_SEPARATOR);
	path.append("doc");

	if (checkFile(path, doc.c_str())==E_FAIL) {
		const size_t last_slash_idx = g_AppDirPath.rfind(PATH_SEPARATOR);
		if (std::string::npos == last_slash_idx)
			return E_FAIL;

		path = g_AppDirPath.substr(0, last_slash_idx);
		path.append(PATH_SEPARATOR);
		path.append("doc");

		if (checkFile(path, doc.c_str())==E_FAIL)
			return E_FAIL;
	}

	path.insert(0, "file://");
	path.append(PATH_SEPARATOR);
	path.append(doc);

	openLocation(path);

	return S_OK;
}

/*!
updateMenuText: update menu text.

@return No value is returned.
@date 2015/03/12
- Support MaxPupilWidth and MinPupilWidth
*/
void updateMenuText( void )
{
	std::stringstream ss;
	ss << "PupilThreshold(" << g_Threshold << ")";
	g_MenuString[MENU_THRESH_PUPIL] = ss.str();
	ss.str("");
	ss << "PurkinjeThreshold(" << g_PurkinjeThreshold << ")";
	g_MenuString[MENU_THRESH_PURKINJE] = ss.str();
	ss.str("");
	ss << "MinPupilWidth(" << g_MinPupilWidth << ")";
	g_MenuString[MENU_MIN_PUPILWIDTH] = ss.str();
	ss.str("");
	ss << "MaxPupilWidth(" << g_MaxPupilWidth << ")";
	g_MenuString[MENU_MAX_PUPILWIDTH] = ss.str();
	ss.str("");
	ss  << "PurkinjeSearchArea(" << g_PurkinjeSearchArea << ")";
	g_MenuString[MENU_SEARCHAREA] = ss.str();
	ss.str("");
	ss  << "PurkinjeExcludeArea(" << g_PurkinjeExcludeArea << ")";
	g_MenuString[MENU_EXCLUDEAREA] = ss.str();
	ss.str("");
	ss << "MorphologicalTrans(" << g_MorphologicalTrans << ")";
	g_MenuString[MENU_MORPHTRANS] = ss.str();

	return;
}

/*
*/
void printStringToTexture(int StartX, int StartY, std::string *strings, int numItems, int fontsize, SDL_Surface* pSurface)
{
	int SX = StartX;
	int SY = StartY;
	SDL_Surface* textSurface;
	SDL_Rect dstRect;
	SDL_Color color={255,255,255};

	SDL_FillRect(pSurface, NULL, 0);

	for(int l=0; l<numItems; l++)
	{
		textSurface = TTF_RenderUTF8_Blended(g_Font, strings[l].c_str(), color);
		dstRect.x = SX;
		dstRect.y = SY;
		SDL_BlitSurface(textSurface, NULL, pSurface, &dstRect);

		SY += MENU_ITEM_HEIGHT;
		SX = StartX;
	}
}

int initSDLTTF(void)
{
	std::string fontFilePath(g_AppDirPath);

	if(TTF_Init()==-1){
		return E_FAIL;
	};
	
	fontFilePath.append(PATH_SEPARATOR);
	fontFilePath.append("FreeSans.ttf");
	if((g_Font=TTF_OpenFont(fontFilePath.c_str(), MENU_FONT_SIZE))==NULL)
	{
		// try debian font directory
		fontFilePath.assign("/usr/share/fonts/truetype/freefont/FreeSans.ttf");
		if((g_Font=TTF_OpenFont(fontFilePath.c_str(), MENU_FONT_SIZE))==NULL)
		{
			// try current directory
			fontFilePath.assign("FreeSans.ttf");
			if((g_Font=TTF_OpenFont(fontFilePath.c_str(), MENU_FONT_SIZE))==NULL)
			{
				// try parent directory
				fontFilePath.assign("..");
				fontFilePath.append(PATH_SEPARATOR);
				fontFilePath.append("FreeSans.ttf");
				if ((g_Font = TTF_OpenFont(fontFilePath.c_str(), MENU_FONT_SIZE)) == NULL){
					return E_FAIL;
				}
			}
		}
	}

	return S_OK;
}

int initSDLSurfaces(void)
{
	g_pCameraTextureSurface =  SDL_CreateRGBSurfaceFrom((void*)g_pCameraTextureBuffer, 
					g_CameraWidth, g_CameraHeight, 32, g_CameraWidth*4,
					0xff0000, 0x00ff00, 0x0000ff, 0 );
	g_pCalResultTextureSurface = SDL_CreateRGBSurfaceFrom((void*)g_pCalResultTextureBuffer, 
					g_PreviewWidth, g_PreviewHeight, 32, g_PreviewWidth*4,
					0xff0000, 0x00ff00, 0x0000ff, 0 );

	g_pPanelSurface = SDL_CreateRGBSurface(SDL_SWSURFACE, PANEL_WIDTH, PANEL_HEIGHT,
					32, 0xff0000, 0x00ff00, 0x0000ff, 0 );

	updateMenuText();
	updateCustomMenuText();
	printStringToTexture(0,0,g_MenuString,MENU_GENERAL_NUM+g_CustomMenuNum,MENU_FONT_SIZE,g_pPanelSurface);

	return S_OK;
}


/*!
cleanup: release malloced buffers.

@return No value is returned.

@date 2012/04/06 release buffers.
@date 2013/03/26 output log message.
@date 2013/12/16 release buffers for USB-IO.
*/
void cleanup( void )
{
	g_LogFS << "Release buffers ... ";
	
	if( g_frameBuffer != NULL )
	{
		free(g_frameBuffer);
		g_frameBuffer = NULL;
	}

	if( g_pCameraTextureBuffer != NULL )
	{
		free(g_pCameraTextureBuffer);
		g_pCameraTextureBuffer = NULL;
	}

	if( g_pCalResultTextureBuffer != NULL )
	{
		free(g_pCalResultTextureBuffer);
		g_pCalResultTextureBuffer = NULL;
	}

	if( g_SendImageBuffer != NULL )
	{
		free(g_SendImageBuffer);
		g_SendImageBuffer = NULL;
	}
	
	//USB
	cleanupUSBIO();

	g_LogFS << "OK." << std::endl;
}

/*!
flushGazeData: write data to the datafile.

This function is called either when recording is stopped or g_DataCounter reached to MAXDATA.

@return No value is returned.

@date 2012/07/30
- EOG-SimpleGazeTracker concurrent recording mode is appended
@date 2012/09/28
- Support for pupil size output
@date 2013/05/27
- Support camera custom data.
*/
void flushGazeData(void)
{
	double xy[4];
	char buff[255];
	int len=0;
	if(g_RecordingMode==RECORDING_MONOCULAR){
		for(int i=0; i<g_DataCounter; i++){
			fprintf(g_DataFP,"%.3f,",g_TickData[i]);

			if(g_EyeData[i][0]<E_PUPIL_PURKINJE_DETECTION_FAIL){
				if(g_EyeData[i][0] == E_MULTIPLE_PUPIL_CANDIDATES)
					fprintf(g_DataFP,"MULTIPUPIL,MULTIPUPIL");
				else if(g_EyeData[i][0] == E_NO_PUPIL_CANDIDATE)
					fprintf(g_DataFP,"NOPUPIL,NOPUPIL");
				else if(g_EyeData[i][0] == E_NO_PURKINJE_CANDIDATE)
					fprintf(g_DataFP,"NOPURKINJE,NOPURKINJE");
				else if(g_EyeData[i][0] == E_MULTIPLE_PURKINJE_CANDIDATES)
					fprintf(g_DataFP,"MULTIPURKINJE,MULTIPURKINJE");
				else if(g_EyeData[i][0] == E_NO_FINE_PUPIL_CANDIDATE)
					fprintf(g_DataFP,"NOFINEPUPIL,NOFINEPUPIL");
				else
					fprintf(g_DataFP,"FAIL,FAIL");
				
				if(g_isOutputPupilSize)
					fprintf(g_DataFP,",FAIL");

			}else{
				getGazePositionMono(g_EyeData[i], xy);
				if(g_isOutputPupilSize)
					fprintf(g_DataFP,"%.1f,%.1f,%.1f" ,xy[MONO_X],xy[MONO_Y],g_PupilSizeData[i][MONO_P]);
				else
					fprintf(g_DataFP,"%.1f,%.1f" ,xy[MONO_X],xy[MONO_Y]);
			}

			//USBIO
			if(g_useUSBIO){
				getUSBIODataString(i, buff, sizeof(buff));
				fprintf(g_DataFP,",%s", buff);
			}

			//Camera custom data
			if(g_isOutputCameraSpecificData==USE_CAMERASPECIFIC_DATA)
				fprintf(g_DataFP,",%d",g_CameraSpecificData[i]);

			//End of line
			fprintf(g_DataFP,"\n");
		}
	}else{ //binocular
		for(int i=0; i<g_DataCounter; i++){
			fprintf(g_DataFP,"%.3f,",g_TickData[i]);
			getGazePositionBin(g_EyeData[i], xy);
			//left eye
			if(g_EyeData[i][BIN_LX]<E_PUPIL_PURKINJE_DETECTION_FAIL){
				if(g_EyeData[i][BIN_LX] == E_MULTIPLE_PUPIL_CANDIDATES)
					fprintf(g_DataFP,"MULTIPUPIL,MULTIPUPIL,");
				else if(g_EyeData[i][BIN_LX] == E_NO_PUPIL_CANDIDATE)
					fprintf(g_DataFP,"NOPUPIL,NOPUPIL,");
				else if(g_EyeData[i][BIN_LX] == E_NO_PURKINJE_CANDIDATE)
					fprintf(g_DataFP,"NOPURKINJE,NOPURKINJE,");
				else if(g_EyeData[i][BIN_LX] == E_MULTIPLE_PURKINJE_CANDIDATES)
					fprintf(g_DataFP,"MULTIPURKINJE,MULTIPURKINJE,");
				else if(g_EyeData[i][BIN_LX] == E_NO_FINE_PUPIL_CANDIDATE)
					fprintf(g_DataFP,"NOFINEPUPIL,NOFINEPUPIL,");
				else
					fprintf(g_DataFP,"FAIL,FAIL,");		
			}else{
				fprintf(g_DataFP,"%.1f,%.1f," ,xy[BIN_LX],xy[BIN_LY]);
			}
			//right eye
			if(g_EyeData[i][BIN_RX]<E_PUPIL_PURKINJE_DETECTION_FAIL){
				if(g_EyeData[i][BIN_RX] == E_MULTIPLE_PUPIL_CANDIDATES)
					fprintf(g_DataFP,"MULTIPUPIL,MULTIPUPIL");
				else if(g_EyeData[i][BIN_RX] == E_NO_PUPIL_CANDIDATE)
					fprintf(g_DataFP,"NOPUPIL,NOPUPIL");
				else if(g_EyeData[i][BIN_RX] == E_NO_PURKINJE_CANDIDATE)
					fprintf(g_DataFP,"NOPURKINJE,NOPURKINJE");
				else if(g_EyeData[i][BIN_LX] == E_MULTIPLE_PURKINJE_CANDIDATES)
					fprintf(g_DataFP,"MULTIPURKINJE,MULTIPURKINJE");
				else if(g_EyeData[i][BIN_RX] == E_NO_FINE_PUPIL_CANDIDATE)
					fprintf(g_DataFP,"NOFINEPUPIL,NOFINEPUPIL");
				else
					fprintf(g_DataFP,"FAIL,FAIL");
			}else{
				fprintf(g_DataFP,"%.1f,%.1f" ,xy[BIN_RX],xy[BIN_RY]);
			}
			
			//pupil
			if(g_isOutputPupilSize){
				//left
				if(g_EyeData[i][BIN_LX]<E_PUPIL_PURKINJE_DETECTION_FAIL)
					fprintf(g_DataFP,",FAIL");
				else
					fprintf(g_DataFP,",%.1f",g_PupilSizeData[i][BIN_LP]);
				
				//right
				if(g_EyeData[i][BIN_RX]<E_PUPIL_PURKINJE_DETECTION_FAIL)
					fprintf(g_DataFP,",FAIL");
				else
					fprintf(g_DataFP,",%.1f",g_PupilSizeData[i][BIN_RP]);				
				
			}

			//USBIO
			if(g_useUSBIO){
				getUSBIODataString(i, buff, sizeof(buff));
				fprintf(g_DataFP,",%s", buff);
			}

			//Camera Custom Data
			if(g_isOutputCameraSpecificData==USE_CAMERASPECIFIC_DATA)
				fprintf(g_DataFP,",%d",g_CameraSpecificData[i]);

			//End of line
			fprintf(g_DataFP,"\n");
		}

	}

	fflush(g_DataFP);
}

/*!
getGazeMono: convert relative Purkinje image position to gaze position and store data (for monocular recording).
Following global variables may be changed. If g_DataCounter reached to MAXDATA, data are 
flushed to the data file and g_DataCounter is rewinded to zero.
- g_EyeData
- g_CalPointData
- g_DataCounter
- g_TickData
- g_CalSamplesAtCurrentPoint

@param[in] detectionResults Center of pupil and Purkinje image.  Only four elements are used when recording mode is monocular.
@param[in] TimeImageAcquired Timestamp

@return No value is returned.

@date 2012/09/28
- Support for recording pupil size
@date 2012/10/25 output warning when g_DataCounter > MAXCAldata during calibration/validation
@date 2012/10/26 record current pupil size.
*/
void getGazeMono( double detectionResults[8], double TimeImageAcquired )
{
	if(g_isCalibrating || g_isValidating){
		if(detectionResults[MONO_PUPIL_X] <= E_FIRST_ERROR_CODE) //A value smaller than E_FIRST_ERROR_CODE is treated as an error.
		{
			// data should not be included in g_CalPointData.
			return;
		}
		if(g_CalSamplesAtCurrentPoint > 0)
		{
			g_CalPointData[g_DataCounter][MONO_X] = g_CurrentCalPoint[MONO_X];
			g_CalPointData[g_DataCounter][MONO_Y] = g_CurrentCalPoint[MONO_Y];
			g_EyeData[g_DataCounter][MONO_X] = detectionResults[MONO_PUPIL_X]-detectionResults[MONO_PURKINJE_X];
			g_EyeData[g_DataCounter][MONO_Y] = detectionResults[MONO_PUPIL_Y]-detectionResults[MONO_PURKINJE_Y];
			if(g_isOutputPupilSize)
			{
				g_PupilSizeData[g_DataCounter][MONO_P] = detectionResults[MONO_PUPILSIZE];
			}
			g_DataCounter++;
			if(g_DataCounter>=MAXCALDATA){
				g_LogFS << "Warning: number of calibration data exceeded its maximum (" << MAXCALDATA << ")" << std::endl;
				g_DataCounter = 0;
			}
			g_CalSamplesAtCurrentPoint--;
		}

	}else if(g_isRecording){
		g_TickData[g_DataCounter] = TimeImageAcquired;
		if(detectionResults[MONO_PUPIL_X] <= E_FIRST_ERROR_CODE) //A value smaller than E_FIRST_ERROR_CODE is treated as an error.
		{
			g_EyeData[g_DataCounter][MONO_X] = detectionResults[MONO_PUPIL_X];
			g_EyeData[g_DataCounter][MONO_Y] = detectionResults[MONO_PUPIL_X];
			g_CurrentEyeData[MONO_X] = detectionResults[MONO_PUPIL_X];
			g_CurrentEyeData[MONO_Y] = detectionResults[MONO_PUPIL_X];
			if(g_isOutputPupilSize)
			{
				g_PupilSizeData[g_DataCounter][MONO_P] = detectionResults[MONO_PUPILSIZE];
				g_CurrentPupilSize[MONO_P] = detectionResults[MONO_PUPILSIZE];
			}
		}
		else
		{
			g_EyeData[g_DataCounter][MONO_X] = detectionResults[MONO_PUPIL_X]-detectionResults[MONO_PURKINJE_X];
			g_EyeData[g_DataCounter][MONO_Y] = detectionResults[MONO_PUPIL_Y]-detectionResults[MONO_PURKINJE_Y];
			getGazePositionMono(g_EyeData[g_DataCounter], g_CurrentEyeData);
			if(g_isOutputPupilSize)
			{
				g_PupilSizeData[g_DataCounter][MONO_P] = detectionResults[MONO_PUPILSIZE];
				g_CurrentPupilSize[MONO_P] = detectionResults[MONO_PUPILSIZE];
			}
		}
		g_DataCounter++;
		//check overflow
		if(g_DataCounter >= MAXDATA)
		{
			//flush data
			flushGazeData();
			
			//insert overflow message
			fprintf(g_DataFP,"#OVERFLOW_FLUSH_GAZEDATA,%.3f\n",getCurrentTime()-g_RecStartTime);
			fflush(g_DataFP);

			//reset counter
			g_DataCounter = 0;
		}
	}
}

/*!
getGazeBin: convert relative Purkinje image position to gaze position and store data (for binocular recording).
Following global variables may be changed. If g_DataCounter reached to MAXDATA, data are 
flushed to the data file and g_DataCounter is rewinded to zero.
- g_EyeData
- g_CalPointData
- g_DataCounter
- g_TickData
- g_CalSamplesAtCurrentPoint

@param[in] detectionResults Center of pupil and Purkinje image.
@param[in] TimeImageAcquired Timestamp

@return No value is returned.

@date 2012/09/28
- Support for recording pupil size
@date 2012/10/25 output warning when g_DataCounter > MAXCAldata during calibration/validation
@date 2012/10/26 record current pupil size.
@date 2015/03/05 record pupil size during calibration/validation
*/
void getGazeBin( double detectionResults[8], double TimeImageAcquired )
{
	if(g_isCalibrating || g_isValidating){
		if(detectionResults[BIN_PUPIL_LX] <= E_FIRST_ERROR_CODE && 
			detectionResults[BIN_PUPIL_RX] <= E_FIRST_ERROR_CODE) //A value smaller than E_FIRST_ERROR_CODE is treated as an error.
		{
			// data should not be included in g_CalPointData.
			return;
		}
		if(g_CalSamplesAtCurrentPoint > 0)
		{
			g_CalPointData[g_DataCounter][BIN_X] = g_CurrentCalPoint[BIN_X];
			g_CalPointData[g_DataCounter][BIN_Y] = g_CurrentCalPoint[BIN_Y];
			g_EyeData[g_DataCounter][BIN_LX] = detectionResults[BIN_PUPIL_LX]-detectionResults[BIN_PURKINJE_LX];
			g_EyeData[g_DataCounter][BIN_LY] = detectionResults[BIN_PUPIL_LY]-detectionResults[BIN_PURKINJE_LY];
			g_EyeData[g_DataCounter][BIN_RX] = detectionResults[BIN_PUPIL_RX]-detectionResults[BIN_PURKINJE_RX];
			g_EyeData[g_DataCounter][BIN_RY] = detectionResults[BIN_PUPIL_RY]-detectionResults[BIN_PURKINJE_RY];
			if(g_isOutputPupilSize)
			{
				g_PupilSizeData[g_DataCounter][BIN_LP] = detectionResults[BIN_PUPILSIZE_L];
				g_PupilSizeData[g_DataCounter][BIN_RP] = detectionResults[BIN_PUPILSIZE_R];
			}
			g_DataCounter++;
			if(g_DataCounter>=MAXCALDATA){
				g_LogFS << "Warning: number of calibration data exceeded its maximum (" << MAXCALDATA << ")" << std::endl;
				g_DataCounter = 0;
			}
			g_CalSamplesAtCurrentPoint--;
		}

	}else if(g_isRecording){
		g_TickData[g_DataCounter] = TimeImageAcquired;
		g_EyeData[g_DataCounter][BIN_LX] = detectionResults[BIN_PUPIL_LX]-detectionResults[BIN_PURKINJE_LX];
		g_EyeData[g_DataCounter][BIN_LY] = detectionResults[BIN_PUPIL_LY]-detectionResults[BIN_PURKINJE_LY];
		g_EyeData[g_DataCounter][BIN_RX] = detectionResults[BIN_PUPIL_RX]-detectionResults[BIN_PURKINJE_RX];
		g_EyeData[g_DataCounter][BIN_RY] = detectionResults[BIN_PUPIL_RY]-detectionResults[BIN_PURKINJE_RY];
		getGazePositionBin(g_EyeData[g_DataCounter], g_CurrentEyeData);
		//pupil
		if(g_isOutputPupilSize)
		{
			g_PupilSizeData[g_DataCounter][BIN_LP] = detectionResults[BIN_PUPILSIZE_L];
			g_PupilSizeData[g_DataCounter][BIN_RP] = detectionResults[BIN_PUPILSIZE_R];
			g_CurrentPupilSize[BIN_LP] = detectionResults[BIN_PUPILSIZE_L];
			g_CurrentPupilSize[BIN_RP] = detectionResults[BIN_PUPILSIZE_R];
		}
		//left eye
		if(detectionResults[BIN_PUPIL_LX] <= E_FIRST_ERROR_CODE) //A value smaller than E_FIRST_ERROR_CODE is treated as an error.
		{
			g_EyeData[g_DataCounter][BIN_LX] = detectionResults[BIN_PUPIL_LX];
			g_EyeData[g_DataCounter][BIN_LY] = detectionResults[BIN_PUPIL_LX];
			g_CurrentEyeData[BIN_LX] = detectionResults[BIN_PUPIL_LX];
			g_CurrentEyeData[BIN_LY] = detectionResults[BIN_PUPIL_LX];
		}
		//right eye
		if(detectionResults[BIN_PUPIL_RX] <= E_FIRST_ERROR_CODE) //A value smaller than E_FIRST_ERROR_CODE is treated as an error.
		{
			g_EyeData[g_DataCounter][BIN_RX] = detectionResults[BIN_PUPIL_RX];
			g_EyeData[g_DataCounter][BIN_RY] = detectionResults[BIN_PUPIL_RX];
			g_CurrentEyeData[BIN_RX] = detectionResults[BIN_PUPIL_RX];
			g_CurrentEyeData[BIN_RY] = detectionResults[BIN_PUPIL_RX];
		}
		g_DataCounter++;
		//check overflow
		if(g_DataCounter >= MAXDATA)
		{
			//flush data
			flushGazeData();
			
			//insert overflow message
			fprintf(g_DataFP,"#OVERFLOW_FLUSH_GAZEDATA,%.3f\n",getCurrentTime()-g_RecStartTime);
			fflush(g_DataFP);

			//reset counter
			g_DataCounter = 0;
		}
	}
}

/*
render: Render SDL screen.


*/
void render(void)
{
	SDL_Rect dstRect;
	cv::Mat srcMat, scaledMat;

	SDL_FillRect(g_pSDLscreen, NULL, 0);

	if(g_isShowingCalResult)
	{
		dstRect.x = 0;
		dstRect.y = 0;
		SDL_BlitSurface(g_pCalResultTextureSurface, NULL, g_pSDLscreen, &dstRect);
	}
	else{
		if((g_PreviewWidth!=g_CameraWidth)||(g_PreviewHeight!=g_CameraHeight)){
			srcMat = cv::Mat(g_CameraHeight,g_CameraWidth,CV_8UC4,g_pCameraTextureBuffer);
			scaledMat = cv::Mat(g_PreviewHeight,g_PreviewWidth,CV_8UC4);
			cv::resize(srcMat,scaledMat,cv::Size(g_PreviewWidth,g_PreviewHeight));
			
			SDL_Surface* scaledSurface = SDL_CreateRGBSurfaceFrom((void*)scaledMat.data,
						g_PreviewWidth, g_PreviewHeight, 32, g_PreviewWidth*4,
						0xff0000, 0x00ff00, 0x0000ff, 0 );

			dstRect.x = 0;
			dstRect.y = 0;
			SDL_BlitSurface(scaledSurface, NULL, g_pSDLscreen, &dstRect);
		}
		else
		{
			dstRect.x = 0;
			dstRect.y = 0;
			SDL_BlitSurface(g_pCameraTextureSurface, NULL, g_pSDLscreen, &dstRect);
		}
	}

	dstRect.x = g_PreviewWidth + PANEL_OFFSET_X;
	dstRect.y = PANEL_OFFSET_Y;
	SDL_BlitSurface(g_pPanelSurface, NULL, g_pSDLscreen, &dstRect);

	dstRect.x = g_PreviewWidth + CURSOR_OFFSET;
	dstRect.y = PANEL_OFFSET_Y+MENU_ITEM_HEIGHT*g_CurrentMenuPosition+(MENU_ITEM_HEIGHT-CURSOR_SIZE)/2;
	dstRect.w = CURSOR_SIZE;
	dstRect.h = CURSOR_SIZE;
	SDL_FillRect(g_pSDLscreen, &dstRect, 0xFFFF00);

	SDL_UpdateTexture(g_pSDLtexture, NULL, g_pSDLscreen->pixels, g_pSDLscreen->pitch);
	SDL_RenderClear(g_pSDLrenderer);
	SDL_RenderCopy(g_pSDLrenderer, g_pSDLtexture, NULL, NULL);
	SDL_RenderPresent(g_pSDLrenderer);
}

/*
renderRecordingMessage: Render recording message.

This function renders a message informing that the application is now recording data.

@return No value is returned.
@todo show more information.

@date 2015/06/15
- renamed: renderBeforeRecroding -> renderRecordingMessage
- change text position
- message can be rendered without cleaning screen (when cleanScreen is true)
*/
void renderRecordingMessage(const char* message, bool clearScreen)
{
	SDL_Surface* textSurface;
	SDL_Rect dstRect;
	SDL_Color color={255,255,255};

	if(clearScreen){
		SDL_FillRect(g_pSDLscreen, NULL, 0);
	}

	textSurface = TTF_RenderUTF8_Blended(g_Font, "Now recording...", color);
	dstRect.x = 10;
	dstRect.y = 10;
	SDL_BlitSurface(textSurface, NULL, g_pSDLscreen, &dstRect);

	if(message[0]!='\0')
	{
		textSurface = TTF_RenderUTF8_Blended(g_Font, message, color);
		dstRect.y += MENU_ITEM_HEIGHT;
		SDL_BlitSurface(textSurface, NULL, g_pSDLscreen, &dstRect);
	}

	SDL_UpdateTexture(g_pSDLtexture, NULL, g_pSDLscreen->pixels, g_pSDLscreen->pitch);
	SDL_RenderClear(g_pSDLrenderer);
	SDL_RenderCopy(g_pSDLrenderer, g_pSDLtexture, NULL, NULL);
	SDL_RenderPresent(g_pSDLrenderer);
}


/*
renderInitMessage: Render intial message.

@param[in] n vertical position of the message
@param[in] message a message to be printed.

@return No value is returned.
*/
void renderInitMessages(int n, const char* message)
{
	SDL_Surface* textSurface;
	SDL_Rect dstRect;
	SDL_Color color={255,255,255};

	textSurface = TTF_RenderUTF8_Blended(g_Font, message, color);
	dstRect.x = 10;
	dstRect.y = MENU_ITEM_HEIGHT*n+10;
	SDL_BlitSurface(textSurface, NULL, g_pSDLscreen, &dstRect);

	SDL_UpdateTexture(g_pSDLtexture, NULL, g_pSDLscreen->pixels, g_pSDLscreen->pitch);
	SDL_RenderClear(g_pSDLrenderer);
	SDL_RenderCopy(g_pSDLrenderer, g_pSDLtexture, NULL, NULL);
	SDL_RenderPresent(g_pSDLrenderer);
}


/*
measureInterFrameInterval: measure inter-frame interval

@return No value is returned.
*/
void measureInterFrameInterval(void){
	double ifi[2000];
	double detectionResults[MAX_DETECTION_RESULTS];
	double t1, t2, startTime;
	int index, res;

	startTime = getCurrentTime();
	t1 = 0;
	index = 0;
	while (t1 < 1000 && index < 2000) {  // 1000ms or 2000 samples
		if (getCameraImage() == S_OK) {
			t2 = getCurrentTime() - startTime;
			ifi[index] = t2 - t1;
			t1 = t2;
			index++;
			if (g_RecordingMode == RECORDING_MONOCULAR) {
				res = detectPupilPurkinjeMono(g_Threshold, g_PurkinjeSearchArea, g_PurkinjeThreshold, g_PurkinjeExcludeArea, g_MinPupilWidth, g_MaxPupilWidth, detectionResults);
			}
			else {
				res = detectPupilPurkinjeBin(g_Threshold, g_PurkinjeSearchArea, g_PurkinjeThreshold, g_PurkinjeExcludeArea, g_MinPupilWidth, g_MaxPupilWidth, detectionResults);
			}
		}
	}
	g_MeanInterFrameInterval = 0;
	for (int i = 1; i < index; i++) {  // drop first sample (so index starts from 1)
		g_MeanInterFrameInterval += ifi[i];
	}
	g_MeanInterFrameInterval /= (index - 1);

	g_StdInterFrameInterval = 0;
	for (int i = 1; i < index; i++) {
		g_StdInterFrameInterval += (ifi[i] - g_MeanInterFrameInterval)*(ifi[i] - g_StdInterFrameInterval);
	}
	g_StdInterFrameInterval /= (index - 1);
	g_StdInterFrameInterval = sqrt(g_StdInterFrameInterval);

	g_LogFS << "Average inter-frame interval (without render) = " << g_MeanInterFrameInterval << "ms (sd: " << g_StdInterFrameInterval << "ms)" << std::endl;
}


/*
main: Entry point of the application

@return int termination code.

@date 2012/07/27 Don't render screen if g_isInhibitRendering is true.
@date 2012/07/30
- EOG-SimpleGazeTracker concurrent recording mode is appended.
@date 2012/12/13
- Change conditions for rendering screen (!g_isRecording -> g_isShowingCameraImage)
@date 2013/03/26
- Add log messages.
@date 2013/05/27
- Support camera custom data.
@date 2013/10/25
- Support commandline option.
@date 2013/12/12
- Support USB IO.
@date 2015/03/12
- Support MaxPupilWidth and MinPupilWidth
@date 2015/06/12
- support for rendering during the recording.
@date 2015/08/26
- support L key and I key.
*/
int main(int argc, char** argv)
{
	time_t t;
	struct tm *ltm;
	char datestr[256];
	char msg[256];
	int nInitMessage = 0;

	const SDL_MessageBoxButtonData sdlConfigMessageBoxButtons[] = {
		{ SDL_MESSAGEBOX_BUTTON_RETURNKEY_DEFAULT, 0, "Open Config" },
		{ SDL_MESSAGEBOX_BUTTON_ESCAPEKEY_DEFAULT, 1, "Exit" },
	};
	const SDL_MessageBoxButtonData sdlYesNoMessageBoxButtons[] = {
		{ SDL_MESSAGEBOX_BUTTON_RETURNKEY_DEFAULT, 0, "Yes" },
		{ SDL_MESSAGEBOX_BUTTON_ESCAPEKEY_DEFAULT, 1, "No" },
	};
	int sdlButtonID;


	//argv[0] must be copied to resolve application directory later.
	//see getApplicationDirectoryPath() in PratformDependent.cpp 
	g_AppDirPath.assign(argv[0]);
	//int index;
	//index = g_AppDirPath.find_last_of(PATH_SEPARATOR);
	//printf("find_last_of, %d\n",index);
	//if(index==-1)
	//{
	//	return E_FAIL;
	//}
	//g_AppDirPath.erase(index);
	getApplicationDirectoryPath(&g_AppDirPath);

	bool useCustomParamPath = false;
	bool useCustomDataPath = false;
	bool useCustomConfigFile = false;
	g_ConfigFileName.assign(getDefaultConfigFileName());
	if (argc > 0) {
		for (int i = 0; i < argc; i++) {
			if (strncmp(argv[i], "-configdir=", 11) == 0)
			{
				if (strlen(argv[i]) <= 11) {
					return -1;
				}
				g_ParamPath.assign(&argv[i][11]);
				useCustomParamPath = true;
			}
			else if (strncmp(argv[i], "-datadir=", 9) == 0)
			{
				if (strlen(argv[i]) <= 9) {
					return -1;
				}
				g_DataPath.assign(&argv[i][9]);
				useCustomDataPath = true;
			}
			else if (strncmp(argv[i], "-config=", 8) == 0) {
				if (strlen(argv[i]) <= 8) {
					return -1;
				}
				g_ConfigFileName.assign(&argv[i][8]);
				useCustomConfigFile = true;
			}
			else if (strncmp(argv[i], "-cameraconfig=", 14) == 0) {
				printf("Camera specific config file is  deprecated, Write camera specific parameters to CONFIG file");
				SDL_ShowSimpleMessageBox(SDL_MESSAGEBOX_ERROR,
					"Camera specific config file is  deprecated, Write camera specific parameters to CONFIG file",
					g_errorMessage, NULL);
				return -1;
			}
		}
	}

	//check directory and crate them if necessary.
	if (!useCustomParamPath) {
		getParameterDirectoryPath(&g_ParamPath);
		checkAndCreateDirectory(g_ParamPath);
	}
	if (!useCustomDataPath) {
		getDataDirectoryPath(&g_DataPath);
		checkAndCreateDirectory(g_DataPath);
	}

	//open logfile and output welcome message.
	std::string logFilePath;
	getLogFilePath(&logFilePath);
	g_LogFS.open(logFilePath.c_str(), std::ios::out);
	if (!g_LogFS.is_open()) {
		snprintf(g_errorMessage, sizeof(g_errorMessage), "Log file (%s) can't be opened.  Make sure that you have write permission to this file.", logFilePath.c_str());
		SDL_ShowSimpleMessageBox(SDL_MESSAGEBOX_ERROR,
			"SimpleGazeTracker initialization failed",
			g_errorMessage, NULL);
		return -1;
	}
	std::string str("Welcome to SimpleGazeTracker version ");
	str.append(VERSION);
	str.append(" ");
	str.append(getEditionString());
	g_LogFS << str << std::endl;
	time(&t);
	ltm = localtime(&t);
	strftime(datestr, sizeof(datestr), "%Y, %B, %d, %A %p%I:%M:%S", ltm);
	g_LogFS << datestr << std::endl;

	g_LogFS << "Searching AppDirPath directory..." << std::endl;
	g_LogFS << "check " << g_AppDirPath << " ..." << std::endl;
	if (FAILED(checkFile(g_AppDirPath, getDefaultConfigFileName()))) {
		//try /usr/local/lib/simplegazetracker
		g_AppDirPath.assign("/usr/local/lib/simplegazetracker");
		g_LogFS << "check " << g_AppDirPath << " ..." << std::endl;
		if (FAILED(checkFile(g_AppDirPath, getDefaultConfigFileName()))) {
			//try Debian directory (/usr/lib/simplegazetracker)
			g_AppDirPath.assign("/usr/lib/simplegazetracker");
			g_LogFS << "check " << g_AppDirPath << " ..." << std::endl;
			if (FAILED(checkFile(g_AppDirPath, getDefaultConfigFileName()))) {
				//try current directory
				g_AppDirPath.assign(getCurrentWorkingDirectory());
				g_LogFS << "check " << g_AppDirPath << " ..." << std::endl;
				if (FAILED(checkFile(g_AppDirPath, getDefaultConfigFileName()))) {
					printf("ERROR: Could not determine AppDirPath directory.\n");
					g_LogFS << "ERROR: Could not determine AppDirPath directory." << std::endl;
					SDL_ShowSimpleMessageBox(SDL_MESSAGEBOX_ERROR,
						"SimpleGazeTracker initialization failed",
						"Default CONFIG file was not found. Please confirm if SimpleGazeTracker is properly installed.",
						NULL);
					return -1;
				}
			}
		}
	}
	g_LogFS << "AppDirPath directory is " << g_AppDirPath << "." << std::endl;
	g_LogFS << "ParamPath directory is " << g_ParamPath << "." << std::endl;
	g_LogFS << "DataPath directory is " << g_DataPath << "." << std::endl;

	//if CONFIG file is not found in g_ParamPath, copy it.
	if (!useCustomConfigFile) {
		if (FAILED(checkAndCopyFile(g_ParamPath, getDefaultConfigFileName(), g_AppDirPath))) {
			snprintf(g_errorMessage, sizeof(g_errorMessage), "\"%s\" file is not found. Confirm that SimpleGazeTracker is properly installed.\n", getDefaultConfigFileName());
			printf("%s\n", g_errorMessage);
			g_LogFS << "Error: \"" << getDefaultConfigFileName() << "\" file is not found. Confirm that SimpleGazeTracker is properly installed." << std::endl;
			SDL_ShowSimpleMessageBox(SDL_MESSAGEBOX_ERROR,
				"SimpleGazeTracker initialization failed", g_errorMessage, NULL);
			return -1;
		}
	}
	else {
		if (FAILED(checkFile(g_ParamPath, g_ConfigFileName.c_str()))) {
			snprintf(g_errorMessage, sizeof(g_errorMessage), "Error: configuration file (%s) is not found.", g_ConfigFileName.c_str());
			printf("%s\n", g_errorMessage);
			g_LogFS << "Error: configuration file (" << g_ConfigFileName.c_str() << ")is not found.";
			SDL_ShowSimpleMessageBox(SDL_MESSAGEBOX_ERROR,
				"SimpleGazeTracker initialization failed", g_errorMessage, NULL);
			return -1;
		}
	}

	//start initialization
	SDL_Init(SDL_INIT_VIDEO);

	str.assign("SimpleGazeTracker ");
	str.append(VERSION);

	g_pSDLwindow = SDL_CreateWindow(str.c_str(),
		SDL_WINDOWPOS_UNDEFINED,
		SDL_WINDOWPOS_UNDEFINED,
		SCREEN_WIDTH, SCREEN_HEIGHT, 0);
	g_pSDLrenderer = SDL_CreateRenderer(g_pSDLwindow, -1, 0);

	if (g_pSDLwindow == NULL) {
		printf("Error: Could not prepare SDL window.\n");
		g_LogFS << "Error: Could not prepare SDL window." << std::endl;
		SDL_Quit();
		SDL_ShowSimpleMessageBox(SDL_MESSAGEBOX_ERROR,
			"SimpleGazeTracker initialization failed", "Could not prepare SDL window.", NULL);
		return -1;
	}

	g_pSDLscreen = SDL_CreateRGBSurface(0, SCREEN_WIDTH, SCREEN_HEIGHT, 32,
		0x00FF0000,
		0x0000FF00,
		0x000000FF,
		0xFF000000);
	g_pSDLtexture = SDL_CreateTexture(g_pSDLrenderer,
		SDL_PIXELFORMAT_ARGB8888,
		SDL_TEXTUREACCESS_STREAMING,
		SCREEN_WIDTH, SCREEN_HEIGHT);

	if (g_pSDLscreen == NULL || g_pSDLtexture == NULL) {
		printf("Error: Could not prepare SDL surface and texture.\n");
		g_LogFS << "Error: Could not prepare SDL surface and texture." << std::endl;
		SDL_Quit();
		SDL_ShowSimpleMessageBox(SDL_MESSAGEBOX_ERROR,
			"SimpleGazeTracker initialization failed", "Could not prepare SDL surface surface/texture.", NULL);
		return -1;
	}

	strncpy(g_errorMessage, "", sizeof(g_errorMessage));//clear errorMessage
	if (FAILED(initParameters())) {
		if (strcmp(g_errorMessage, "") == 0) {
			snprintf(g_errorMessage, sizeof(g_errorMessage), "Could not initialize parameters. Please check %s.", joinPath(g_ParamPath, g_ConfigFileName).c_str());
		}
		const SDL_MessageBoxData messageboxdata = {
			SDL_MESSAGEBOX_ERROR, NULL,
			"SimpleGazeTracker initialization failed", g_errorMessage,
			SDL_arraysize(sdlConfigMessageBoxButtons), sdlConfigMessageBoxButtons, NULL
		};
		if (SDL_ShowMessageBox(&messageboxdata, &sdlButtonID) >= 0 && sdlButtonID == 0) {
			if (openLocation(g_ParamPath) != 0) {
				snprintf(g_errorMessage, sizeof(g_errorMessage), "Failed to open %s. Please open this directory manually.", g_ParamPath.c_str());
				SDL_ShowSimpleMessageBox(SDL_MESSAGEBOX_ERROR, "Failed to open location", g_errorMessage, NULL);
			}
		}
		g_LogFS << "Error: Could not initialize parameters. Check configuration file." << std::endl;
		SDL_Quit();
		return -1;
	}
	g_LogFS << "initParameters ... OK." << std::endl;

	initTimer();
	//TODO output timer initialization results?

	if (FAILED(initSDLTTF())) {
		printf("Error: Could not prepare font.\n");
		g_LogFS << "initSDLTTF failed. check whether font (FreeSans.ttf) is properly installed.";
		SDL_Quit();
		SDL_ShowSimpleMessageBox(SDL_MESSAGEBOX_ERROR,
			"SimpleGazeTracker initialization failed", "Failed to initialize font rendering. Maybe the font file (FreeSans.ttf) is missing. Please confirm whether SimpleGazeTracker is properly installed", NULL);
		return -1;
	}
	g_LogFS << "initSDLTTF ... OK." << std::endl;

	//now message can be rendered on screen.
	renderInitMessages(nInitMessage, str.c_str());
	nInitMessage++;
	nInitMessage++;
	renderInitMessages(nInitMessage, "initParameters ... OK.");
	nInitMessage++;
	renderInitMessages(nInitMessage, "initSDLTTF ... OK.");
	nInitMessage++;

	if (FAILED(initBuffers())) {
		g_LogFS << "initBuffers failed. Exit." << std::endl;
		renderInitMessages(nInitMessage, "initBuffers failed. Exit.");
		const SDL_MessageBoxData messageboxdata = {
			SDL_MESSAGEBOX_ERROR, NULL,
			"SimpleGazeTracker initialization failed", "Failed to initialize image buffer. Settings of camera image size and preview image size may be wrong.",
			SDL_arraysize(sdlConfigMessageBoxButtons), sdlConfigMessageBoxButtons, NULL
		};
		if (SDL_ShowMessageBox(&messageboxdata, &sdlButtonID) >= 0 && sdlButtonID == 0) {
			if (openLocation(g_ParamPath) != 0) {
				snprintf(g_errorMessage, sizeof(g_errorMessage), "Failed to open %s. Please open this directory manually.", g_ParamPath.c_str());
				SDL_ShowSimpleMessageBox(SDL_MESSAGEBOX_ERROR, "Failed to open location", g_errorMessage, NULL);
			}
		}
		SDL_Quit();
		return -1;
	}

	g_LogFS << "initBuffers ... OK." << std::endl;
	renderInitMessages(nInitMessage, "initBuffers ... OK.");
	nInitMessage += 1;

	if (FAILED(sockInit())) {
		g_LogFS << "sockInit failed. Exit." << std::endl;
		renderInitMessages(nInitMessage, "sockInit failed. Exit.");
		SDL_ShowSimpleMessageBox(SDL_MESSAGEBOX_ERROR,
			"SimpleGazeTracker initialization failed", "Failed to initialize network socket.", NULL);
		SDL_Quit();
		return -1;
	}
	g_LogFS << "sockInit ... OK." << std::endl;
	renderInitMessages(nInitMessage, "sockInit ... OK.");
	nInitMessage += 1;

	if (FAILED(sockAccept())) {
		g_LogFS << "sockAccept failed. Exit." << std::endl;
		renderInitMessages(nInitMessage, "sockAccept failed. Exit.");
		SDL_ShowSimpleMessageBox(SDL_MESSAGEBOX_ERROR,
			"SimpleGazeTracker initialization failed", "Failed to initialize network socket.", NULL);
		SDL_Quit();
		return -1;
	}
	g_LogFS << "sockAccept ... OK." << std::endl;
	renderInitMessages(nInitMessage, "sockAccept ... OK.");
	nInitMessage += 1;

	strncpy(g_errorMessage, "", sizeof(g_errorMessage));//clear errorMessage
	if (FAILED(initCamera())) {
		if (strcmp(g_errorMessage, "") == 0) {
			snprintf(g_errorMessage, sizeof(g_errorMessage), "Could not initialize camera. Please check %s.\n\nDo you want to open Config Directory", joinPath(g_ConfigFileName, g_ParamPath).c_str());
		}
		const SDL_MessageBoxData messageboxdata = {
			SDL_MESSAGEBOX_ERROR, NULL,
			"SimpleGazeTracker initialization failed", g_errorMessage,
			SDL_arraysize(sdlConfigMessageBoxButtons), sdlConfigMessageBoxButtons, NULL
		};
		if (SDL_ShowMessageBox(&messageboxdata, &sdlButtonID) >= 0 && sdlButtonID == 0) {
			if (openLocation(g_ParamPath) != 0) {
				snprintf(g_errorMessage, sizeof(g_errorMessage), "Failed to open %s. Please open this directory manually.", g_ParamPath.c_str());
				SDL_ShowSimpleMessageBox(SDL_MESSAGEBOX_ERROR, "Failed to open location", g_errorMessage, NULL);
			}
		}
		g_LogFS << "initCamera failed. Exit." << std::endl;
		renderInitMessages(nInitMessage, "initCamera failed. Exit.");
		SDL_Quit();
		return -1;
	}
	g_LogFS << "initCamera ... OK." << std::endl;
	renderInitMessages(nInitMessage, "initCamera ... OK.");
	nInitMessage += 1;

	if (FAILED(initSDLSurfaces())) {
		g_LogFS << "initSDLSurfaces failed. Exit." << std::endl;
		renderInitMessages(nInitMessage, "initSDLSurfaces failed. Exit.");
		SDL_ShowSimpleMessageBox(SDL_MESSAGEBOX_ERROR,
			"SimpleGazeTracker initialization failed", "Failed to initialize SDL surfaces.", NULL);
		SDL_Quit();
		return -1;
	}
	g_LogFS << "initSDLSurfaces ... OK." << std::endl;
	renderInitMessages(nInitMessage, "initSDLSurfaces ... OK.");
	nInitMessage += 1;

	strncpy(g_errorMessage, "", sizeof(g_errorMessage));//clear errorMessage
	if (g_USBIOBoard.length() > 0 && g_USBIOBoard != "NONE") {
		if (FAILED(initUSBIO())) {
			if (strcmp(g_errorMessage, "") == 0) {
				snprintf(g_errorMessage, sizeof(g_errorMessage), "Could not initialize USB I/O. Please check %s.", joinPath(g_ParamPath, g_ConfigFileName).c_str());
			}
			const SDL_MessageBoxData messageboxdata = {
				SDL_MESSAGEBOX_ERROR, NULL,
				"SimpleGazeTracker initialization failed", g_errorMessage,
				SDL_arraysize(sdlConfigMessageBoxButtons), sdlConfigMessageBoxButtons, NULL
			};
			if (SDL_ShowMessageBox(&messageboxdata, &sdlButtonID) >= 0 && sdlButtonID == 0) {
				if (openLocation(g_ParamPath) != 0) {
					snprintf(g_errorMessage, sizeof(g_errorMessage), "Failed to open %s. Please open this directory manually.", g_ParamPath.c_str());
					SDL_ShowSimpleMessageBox(SDL_MESSAGEBOX_ERROR, "Failed to open location", g_errorMessage, NULL);
				}
			}
			g_LogFS << "initUSBIO failed. Exit." << std::endl;
			renderInitMessages(nInitMessage, "initUSBIO failed. Exit.");
			SDL_Quit();
			return -1;
		}
		g_LogFS << "initUSBIO ... OK." << std::endl;
		renderInitMessages(nInitMessage, "initUSBIO ... OK.");
		nInitMessage += 1;
	}
	else {
		g_LogFS << "USBIO is not used." << std::endl;
	}


	renderInitMessages(nInitMessage, "Measuring inter-frame interval... .");
	nInitMessage += 1;

	measureInterFrameInterval();

	snprintf(msg, sizeof(msg), "Average: %.1fms (%.1fHz)", g_MeanInterFrameInterval, 1000 / g_MeanInterFrameInterval);
	renderInitMessages(nInitMessage, msg);
	nInitMessage += 1;

	g_LogFS << "Start." << "\n" << std::endl;
	nInitMessage += 1; //blank line
	renderInitMessages(nInitMessage, "Start.");
	sleepMilliseconds(3000);


	//todo open set up tutorial?
	if (g_openSetupGuide){
		const SDL_MessageBoxData messageboxdata = {
			SDL_MESSAGEBOX_ERROR, NULL,
			"Welcome to SimpleGazeTracker", "Do you want to open setup guide in your borwser?\n(Hit H key to open help documents including the setup guide later.)",
			SDL_arraysize(sdlYesNoMessageBoxButtons), sdlYesNoMessageBoxButtons, NULL
		};
		if (SDL_ShowMessageBox(&messageboxdata, &sdlButtonID) >= 0 && sdlButtonID == 0) {
			if (openHTMLdoc("setup_guide.html") == E_FAIL) {
				SDL_ShowSimpleMessageBox(SDL_MESSAGEBOX_ERROR,
					"Error", "Help document is not installed.", NULL);
			}
		}
		g_openSetupGuide = false;
	}

	SDL_Event SDLevent;
	int done = false;
	while (!done){
		while (SDL_PollEvent(&SDLevent)){
			switch (SDLevent.type){
			case SDL_KEYDOWN:
				switch (SDLevent.key.keysym.sym)
				{
				case SDLK_q:
					if (g_isRecording || g_isCalibrating || g_isValidating)
					{
						g_isRecording = g_isCalibrating = g_isValidating = false;
					}
					done = 1;
					break;

				case SDLK_s:
					if (!g_isRecording && !g_isCalibrating && !g_isValidating){
						saveCalValResultsDetail();
					}
					break;

				case SDLK_i:
					char capfilename[64];
					time(&t);
					ltm = localtime(&t);
					snprintf(capfilename, sizeof(capfilename), "SGT_%d%02d%02d%02d%02d%02d_%08d.bmp", ltm->tm_year + 1900, ltm->tm_mon + 1, ltm->tm_mday, ltm->tm_hour, ltm->tm_min, ltm->tm_sec, g_captureNum);
					saveCameraImage(capfilename);
					g_captureNum++;
					break;

				case SDLK_l:
					if (g_isRecording){
						if (!g_isShowingCameraImage){
							g_isShowingCameraImage = true;
							g_LogFS << "WANING: Enable Camera Preview during recording.";
						}
						else{
							g_isShowingCameraImage = false;
							//draw message on calimage
							renderRecordingMessage(g_recordingMessage, true);
							g_LogFS << "WANING: Stop Camera Preview during recording.";
						}
					}
					break;

				case SDLK_h:
					if (!g_isRecording){
						/*
						SDL_ShowSimpleMessageBox(SDL_MESSAGEBOX_INFORMATION,
							"SimpleGazeTracker Help",
							"q: [Q]uit\ns: [S]ave calibration data\ni: save camera [I]mage\nl:toggle [L]ive view during recording\nh: show this [H]elp\n\nup/down: select menu item\nleft/right: adjust parameter",
							NULL);*/
						if (openHTMLdoc("index.html") == E_FAIL) {
							SDL_ShowSimpleMessageBox(SDL_MESSAGEBOX_ERROR,
								"Error", "Help document is not installed.", NULL);
						}
					}
					break;

				case SDLK_UP:
					if (!g_isRecording && !g_isCalibrating && !g_isValidating){
						g_CurrentMenuPosition--;
						if (g_CurrentMenuPosition < 0)
							g_CurrentMenuPosition = MENU_GENERAL_NUM + g_CustomMenuNum - 1;
					}
					break;
				case SDLK_DOWN:
					if (!g_isRecording && !g_isCalibrating && !g_isValidating){
						g_CurrentMenuPosition++;
						if (MENU_GENERAL_NUM + g_CustomMenuNum <= g_CurrentMenuPosition)
							g_CurrentMenuPosition = 0;
					}
					break;

				case SDLK_LEFT:
					switch (g_CurrentMenuPosition)
					{
					case MENU_THRESH_PUPIL:
						g_Threshold--;
						if (g_Threshold < 1)
							g_Threshold = 1;
						break;
					case MENU_THRESH_PURKINJE:
						g_PurkinjeThreshold--;
						if (g_PurkinjeThreshold < 1)
							g_PurkinjeThreshold = 1;
						break;
					case MENU_MIN_PUPILWIDTH:
						g_MinPupilWidth--;
						if (g_MinPupilWidth < 0)
							g_MinPupilWidth = 0;
						break;
					case MENU_MAX_PUPILWIDTH:
						g_MaxPupilWidth--;
						if (g_MaxPupilWidth <= g_MinPupilWidth)
							g_MaxPupilWidth = g_MinPupilWidth + 1;
						break;
					case MENU_SEARCHAREA:
						g_PurkinjeSearchArea--;
						if (g_PurkinjeSearchArea < 10)
							g_PurkinjeSearchArea = 10;
						break;
					case MENU_EXCLUDEAREA:
						g_PurkinjeExcludeArea--;
						if (g_PurkinjeExcludeArea < 2)
							g_PurkinjeExcludeArea = 2;
						break;
					case MENU_MORPHTRANS:
						g_MorphologicalTrans--;
						if (g_MorphologicalTrans < -100)
							g_MorphologicalTrans = -100;
						updateMorphTransKernel();
						break;
					default:
						customCameraMenu(&SDLevent, g_CurrentMenuPosition);
						break;
					}
					updateMenuText();
					updateCustomMenuText();
					printStringToTexture(0, 0, g_MenuString, MENU_GENERAL_NUM + g_CustomMenuNum, MENU_FONT_SIZE, g_pPanelSurface);
					break;

				case SDLK_RIGHT:
					switch (g_CurrentMenuPosition)
					{
					case MENU_THRESH_PUPIL:
						g_Threshold++;
						if (g_Threshold > 255)
							g_Threshold = 255;
						break;
					case MENU_THRESH_PURKINJE:
						g_PurkinjeThreshold++;
						if (g_PurkinjeThreshold > 255)
							g_PurkinjeThreshold = 255;
						break;
					case MENU_MIN_PUPILWIDTH:
						g_MinPupilWidth++;
						if (g_MinPupilWidth >= g_MaxPupilWidth)
							g_MinPupilWidth = g_MaxPupilWidth - 1;
						break;
					case MENU_MAX_PUPILWIDTH:
						g_MaxPupilWidth++;
						if (g_MaxPupilWidth > 100)
							g_MaxPupilWidth = 100;
						break;
					case MENU_SEARCHAREA:
						g_PurkinjeSearchArea++;
						if (g_PurkinjeSearchArea > 150)
							g_PurkinjeSearchArea = 150;
						break;
					case MENU_EXCLUDEAREA:
						g_PurkinjeExcludeArea++;
						if (g_PurkinjeExcludeArea > g_PurkinjeSearchArea)
							g_PurkinjeExcludeArea = g_PurkinjeSearchArea;
						break;
					case MENU_MORPHTRANS:
						g_MorphologicalTrans++;
						if (g_MorphologicalTrans > 100)
							g_MorphologicalTrans = 100;
						updateMorphTransKernel();
						break;
					default:
						customCameraMenu(&SDLevent, g_CurrentMenuPosition);
						break;
					}
					updateMenuText();
					updateCustomMenuText();
					printStringToTexture(0, 0, g_MenuString, MENU_GENERAL_NUM + g_CustomMenuNum, MENU_FONT_SIZE, g_pPanelSurface);
					break;

				}
				break;

			case SDL_QUIT:
				done = 1;
				break;
			}
		}

		sockProcess();

		//if there is no message to process, do application tasks.

		if (g_isShowingCalResult)
		{ //show calibration result.
			drawCalResult(g_DataCounter, g_EyeData, g_CalPointData, g_NumCalPoint, g_CalPointList, g_CalibrationArea);
		}
		else if (getCameraImage() == S_OK)
		{ //retrieve camera image and process it.
			int res;
			double detectionResults[MAX_DETECTION_RESULTS], TimeImageAcquired;
			TimeImageAcquired = getCurrentTime() - g_RecStartTime;
			//USB IO
			if (g_useUSBIO){
				setUSBIOData(g_DataCounter);
			}
			//CameraSpacificData
			if (g_isOutputCameraSpecificData == USE_CAMERASPECIFIC_DATA){
				g_CameraSpecificData[g_DataCounter] = getCameraSpecificData();
			}

			if (g_RecordingMode == RECORDING_MONOCULAR){
				res = detectPupilPurkinjeMono(g_Threshold, g_PurkinjeSearchArea, g_PurkinjeThreshold, g_PurkinjeExcludeArea, g_MinPupilWidth, g_MaxPupilWidth, detectionResults);
				if (res != S_PUPIL_PURKINJE)
				{
					detectionResults[MONO_PUPIL_X] = detectionResults[MONO_PUPIL_Y] = res;
					detectionResults[MONO_PURKINJE_X] = detectionResults[MONO_PURKINJE_Y] = res;
				}
				getGazeMono(detectionResults, TimeImageAcquired);
			}
			else{
				res = detectPupilPurkinjeBin(g_Threshold, g_PurkinjeSearchArea, g_PurkinjeThreshold, g_PurkinjeExcludeArea, g_MinPupilWidth, g_MaxPupilWidth, detectionResults);
				if (res != S_PUPIL_PURKINJE)
				{
					detectionResults[BIN_PUPIL_LX] = detectionResults[BIN_PUPIL_LY] = res;
					detectionResults[BIN_PURKINJE_LX] = detectionResults[BIN_PURKINJE_LY] = res;
					detectionResults[BIN_PUPIL_RX] = detectionResults[BIN_PUPIL_RY] = res;
					detectionResults[BIN_PURKINJE_RX] = detectionResults[BIN_PURKINJE_RY] = res;
				}
				getGazeBin(detectionResults, TimeImageAcquired);
			}
		}

		if (g_isShowingCameraImage && !g_isInhibitRendering)
		{ // if it is not under recording, flip screen in a regular way.
			render();
		}
	}
	//end mainloop

	g_LogFS << "\nShutting down.\nDoing camera-specific cleanup..." << std::endl;
	cleanupCamera();

	strncpy(g_errorMessage, "", sizeof(g_errorMessage));//clear errorMessage
	if (FAILED(saveParameters())){
		if (strcmp(g_errorMessage, "") == 0){
			snprintf(g_errorMessage, sizeof(g_errorMessage), "Failed to save parameters.");
		}
		g_LogFS << "Failed to save parameters." << std::endl;
		SDL_ShowSimpleMessageBox(SDL_MESSAGEBOX_ERROR,
			"SimpleGazeTracker warning", g_errorMessage, NULL);

	}
	cleanup();
	g_LogFS << "Shutdown SDL...";
	SDL_Quit();
	g_LogFS << "OK." << std::endl;
	time(&t);
	ltm = localtime(&t);
	strftime(datestr, sizeof(datestr), "%Y, %B, %d, %A %p%I:%M:%S", ltm);
	g_LogFS << datestr << std::endl;
	g_LogFS << "Done." << std::endl;
	return 0;
}

/*!
clearCalibrationData: clear calibration data buffer

This function should be called before starting calibration and validation.

@date 2012/07/24 Created.
*/
void clearCalibrationData(void)
{
	int i;
	for(i=0; i<g_NumCalPoint; i++)
	{
		g_CalPointData[i][0] = 0;
		g_CalPointData[i][1] = 0;
	}

	g_NumCalPoint = 0;
}


/*!
clearData: clear data buffer.

This function should be called before starting calibration, validation, measurement and recording.

@return No value is returned.
@date 2012/07/24 calibration data clearance is separated to clearCalibrationData()
@date 2012/09/28 Support for g_PupilSizeData
*/
void clearData(void)
{
	int i;

	for(i=0; i<g_DataCounter; i++)
	{
		g_EyeData[i][0] = 0;
		g_EyeData[i][1] = 0;
		g_EyeData[i][2] = 0;
		g_EyeData[i][3] = 0;
		
		g_PupilSizeData[i][0] = 0;
		g_PupilSizeData[i][1] = 0;
	}

	g_DataCounter = 0;
}

/*!
startCalibration: initialize calibration procedures.

This function must be called when starting calibration.

@param[in] x1 left of the calibration area.
@param[in] y1 top of the calibration area.
@param[in] x2 right of the calibration area.
@param[in] y2 bottom of the calibration area.
@param[in] clear clear previous calibration data if this value is 1.
@return No value is returned.

@date 2016/01/22 add 'clear' option.
*/
void startCalibration(int x1, int y1, int x2, int y2, int clear)
{
	g_LogFS << "StartCalibration" << std::endl;

	g_CalibrationArea[0] = x1;
	g_CalibrationArea[1] = y1;
	g_CalibrationArea[2] = x2;
	g_CalibrationArea[3] = y2;
	if(!g_isRecording && !g_isValidating && !g_isCalibrating){
		if (clear == 1){
			clearCalibrationData();
			clearData();
		}
		g_isCalibrating = true;
		g_isShowingCalResult = false; //erase calibration result screen.
		g_CalSamplesAtCurrentPoint = 0;
	}
}

/*!
endCalibration: finish calibration procedures.

This function must be called when terminating calibration.

@return No value is returned.
@date 2015/03/05 setCalibrationError() is called from this function.
@date 2015/03/13 last calibration data is preserved.
*/
void endCalibration(void)
{
	g_LogFS << "EndCalibration" << std::endl;

	if(g_RecordingMode==RECORDING_MONOCULAR){
		estimateParametersMono( g_DataCounter, g_EyeData, g_CalPointData );
	}else{
		estimateParametersBin( g_DataCounter, g_EyeData, g_CalPointData );
	}
	setCalibrationResults( g_DataCounter, g_EyeData, g_CalPointData, g_CalGoodness, g_CalMaxError, g_CalMeanError);
	setCalibrationError( g_DataCounter, g_EyeData, g_CalPointData, g_NumCalPoint, g_CalPointList, g_CalPointAccuracy, g_CalPointPrecision);
	//hold calibration data
	g_LastNumCalPoint = g_NumCalPoint;
	for(int j=0; j<2; j++){
		for(int i=0; i<MAXCALPOINT; i++){
			g_LastCalPointList[i][j] = g_CalPointList[i][j];
		}
	}
	
	g_isCalibrating=false;
	g_isCalibrated = true;
	g_isShowingCalResult = true;
	g_lastCalValType = TYPE_CALIBRATION;
}

/*!
getCalSample: start sampling calibration data

This function must be called when the calibration target jumped to a new position.
This function is called from sockProcess() when sockProcess() received "getCalSample" command.

@param[in] x position of the target.
@param[in] y position of the target.
@param[in] samples number of samples
@return No value is returned.

@date 2012/10/24 'samples' parameter is added.
@date 2012/10/25 output warning when g_NumCalPoint>=MAXCALPOINT
*/
void getCalSample(double x, double y, int samples)
{
	g_CalPointList[g_NumCalPoint][0] = x;
	g_CalPointList[g_NumCalPoint][1] = y;
	g_CurrentCalPoint[0] = x;
	g_CurrentCalPoint[1] = y;
	g_NumCalPoint++;
	if(g_NumCalPoint>=MAXCALPOINT){
		g_LogFS << "Warning: number of calibration point exceeded its maximum (" << MAXCALPOINT << ")" << std::endl;
		g_NumCalPoint = 0;
	}
	g_CalSamplesAtCurrentPoint = samples;
}

/*!
deleteCalibrationDataSubset: delete subset of calibration data.

This function removes subset of calibration data.
Points to be deleted is given as a string.
Format of the string is "x1,y1,x2,y2,...".

endCalibration() is called at the end of this function to 

@param[in] points Calibration points to be deleted.
@return No value is returned.

@date 2016/01/26 Created.
*/
void deleteCalibrationDataSubset(char* points)
{
	int x, y, datalen, newdatalen;
	char* p = points;
	datalen = g_DataCounter;

	g_LogFS << "DeleteCalibrationDataSubset:" << points << std::endl;

	while (*p != 0){
		x = strtol(p, &p, 10);
		p++;
		y = strtol(p, &p, 10);
		for (int i = 0; i < datalen; i++){
			g_CalPointDelList[i] = (g_CalPointData[i][0] == x && g_CalPointData[i][1] == y) ? true : false;
		}
		newdatalen = 0;
		for (int i = 0; i < datalen; i++){
			if (!g_CalPointDelList[i]){
				if (newdatalen != i){
					g_CalPointData[newdatalen][0] = g_CalPointData[i][0];
					g_CalPointData[newdatalen][1] = g_CalPointData[i][1];
					g_EyeData[newdatalen][0] = g_EyeData[i][0];
					g_EyeData[newdatalen][1] = g_EyeData[i][1];
				}
				newdatalen++;
			}
		}
		datalen = newdatalen;
		if (*p == 0) break;
		p++;
	}
	g_DataCounter = datalen;

	endCalibration();

}

/*!
startValidation: initialize validation procedures.

This function must be called when starting validation.

@param[in] x1 left of the validation area.
@param[in] y1 top of the validation area.
@param[in] x2 right of the validation area.
@param[in] y2 bottom of the validation area.
@return No value is returned.
*/
void startValidation(int x1, int y1, int x2, int y2)
{
	g_LogFS << "StartValidation" << std::endl;

	g_CalibrationArea[0] = x1;
	g_CalibrationArea[1] = y1;
	g_CalibrationArea[2] = x2;
	g_CalibrationArea[3] = y2;
	if(!g_isRecording && !g_isValidating && !g_isCalibrating){ //ready to start calibration?
		clearCalibrationData();
		clearData();
		g_isValidating = true;
		g_isShowingCalResult = false;
		g_CalSamplesAtCurrentPoint = 0;
	}
}

/*!
endValidation: finish validation procedures.

This function must be called when terminating validation.

@return No value is returned.
*/
void endValidation(void)
{
	g_LogFS << "EndValidation" << std::endl;

	setCalibrationResults( g_DataCounter, g_EyeData, g_CalPointData, g_CalGoodness, g_CalMaxError, g_CalMeanError);

	g_isValidating=false;
	g_isShowingCalResult = true;
	g_lastCalValType = TYPE_VALIDATION;
}

/*!
getValSample: start sampling validation data

This function must be called when the validation target jumped to a new position.
This function is called from sockProcess() when sockProcess() received "getValSample" command.

@param[in] x position of the target.
@param[in] y position of the target.
@param[in] samples number of samples
@return No value is returned.
@sa getCalSample

@date 2012/10/24 'samples' parameter is added.
*/
void getValSample(double x, double y, int samples)
{
	getCalSample(x, y, samples);
}


/*!
toggleCalRelsut: toggle camera preview and calibration result dislpay.
This function is called from sockProcess() when sockProcess() received "toggleCalResult" command.

@param[in] specify on/off calibration results (0=off, non_zero=on)
@return No value is returned.
@todo number of samples should be customizable.

@date 2012/11/02 specify on/off calibration results by 'on' parameter.
*/

void toggleCalResult(int param)
{
	if(g_isCalibrated && param != 0)
	{
		g_isShowingCalResult = true;
	}
	else
	{
		g_isShowingCalResult = false;
	}
}


/*!
saveCalValResultsDetail

@return No value is returned.
@date 2015/03/05 created.
*/
void saveCalValResultsDetail(void)
{
	if(g_isRecording || g_isCalibrating || g_isValidating) return;
	if(!g_isCalibrated) return;

	if(g_DataFP!=NULL)
	{
		time_t t;
		struct tm *ltm;
		time(&t);
		ltm = localtime(&t);
		double pos[4];
		if(g_lastCalValType == TYPE_CALIBRATION)
			fprintf(g_DataFP,"#START_DETAIL_CALDATA,%d,%d,%d,%d,%d,%d\n",ltm->tm_year+1900,ltm->tm_mon+1,ltm->tm_mday,ltm->tm_hour,ltm->tm_min,ltm->tm_sec);
		else if(g_lastCalValType == TYPE_VALIDATION)
			fprintf(g_DataFP,"#START_DETAIL_VALDATA,%d,%d,%d,%d,%d,%d\n",ltm->tm_year+1900,ltm->tm_mon+1,ltm->tm_mday,ltm->tm_hour,ltm->tm_min,ltm->tm_sec);
		else
			return;
		for(int i=0; i<g_DataCounter; i++)
		{
			if(g_RecordingMode==RECORDING_MONOCULAR){
				fprintf(g_DataFP,"#CALDATA,%.1f,%.1f,%.2f,%.2f,",g_CalPointData[i][0],g_CalPointData[i][1],g_EyeData[i][MONO_X],g_EyeData[i][MONO_Y]);
				getGazePositionMono(g_EyeData[i], pos);
				fprintf(g_DataFP,"%.2f,%.2f",pos[0],pos[1]);
				if(g_isOutputPupilSize){
					fprintf(g_DataFP,",%.2f\n",g_PupilSizeData[i][MONO_P]);
				}else				{
					fprintf(g_DataFP,"\n");
				}
			}else{
				fprintf(g_DataFP,"#CALDATA,%.1f,%.1f,%.2f,%.2f,%.2f,%.2f,",g_CalPointData[i][0],g_CalPointData[i][1],g_EyeData[i][BIN_LX],g_EyeData[i][BIN_LY],g_EyeData[i][BIN_RX],g_EyeData[i][BIN_RY]);
				getGazePositionBin(g_EyeData[i], pos);
				fprintf(g_DataFP,"%.2f,%.2f,%.2f,%.2f",pos[0],pos[1],pos[2],pos[3]);
				if(g_isOutputPupilSize){
					fprintf(g_DataFP,",%.2f,%f2\n",g_PupilSizeData[i][BIN_LP],g_PupilSizeData[i][BIN_RP]);
				}else{
					fprintf(g_DataFP,"\n");
				}
			}
		}
		if(g_lastCalValType == TYPE_CALIBRATION)
			fprintf(g_DataFP,"#END_DETAIL_CALDATA\n");
		else if(g_lastCalValType == TYPE_VALIDATION)
			fprintf(g_DataFP,"#END_DETAIL_VALDATA\n");

		fflush(g_DataFP);
	}
}


/*!
startRecording: initialize recording procedures.

This function must be called when starting recording.
Output #START_REC, #MESSAGE, #XPARAM and #YPARAM to the data file.
This function is called from sockProcess() when sockProcess() received "startRecording" command.

@param[in] message Message text to be inserted to the data file.
@return No value is returned.
@date 2012/09/28
-output data format.
-Tracker version is output when datafile is opened.
@date 2012/12/05 output message to log file.
@date 2013/03/27 clear g_MessageBuffer.
@date 2015/03/05 output accuracy and precision at each calibration point.
@date 2015/03/13 use preserved calibration points
@date 2015/06/12 support for rendering during the recording.
@date 2015/08/25 preparation of recording screen is moved to prepareRecordingScreen().
*/
void startRecording(const char* message)
{
	time_t t;
	struct tm *ltm;

	if(g_isCalibrated){ //if calibration has finished and recording has not been started, then start recording.

		if(g_DataFP!=NULL)
		{
			time(&t);
			ltm = localtime(&t);
			fprintf(g_DataFP,"#START_REC,%d,%d,%d,%d,%d,%d\n",ltm->tm_year+1900,ltm->tm_mon+1,ltm->tm_mday,ltm->tm_hour,ltm->tm_min,ltm->tm_sec);
			if(message[0]!='\0')
			{
				fprintf(g_DataFP,"#MESSAGE,0,%s\n",message);
			}
			if(g_RecordingMode==RECORDING_MONOCULAR){
				fprintf(g_DataFP,"#XPARAM,%f,%f,%f\n",g_ParamX[0],g_ParamX[1],g_ParamX[2]);
				fprintf(g_DataFP,"#YPARAM,%f,%f,%f\n",g_ParamY[0],g_ParamY[1],g_ParamY[2]);
			}else{
				fprintf(g_DataFP,"#XPARAM,%f,%f,%f,%f,%f,%f\n",g_ParamX[0],g_ParamX[1],g_ParamX[2],g_ParamX[3],g_ParamX[4],g_ParamX[5]);
				fprintf(g_DataFP,"#YPARAM,%f,%f,%f,%f,%f,%f\n",g_ParamY[0],g_ParamY[1],g_ParamY[2],g_ParamY[3],g_ParamY[4],g_ParamY[5]);
			}
			for(int i=0; i<g_LastNumCalPoint; i++){
				fprintf(g_DataFP,"#CALPOINT,%f,%f,",g_LastCalPointList[i][0],g_LastCalPointList[i][1]);
				if(g_RecordingMode == RECORDING_BINOCULAR){ //binocular
					if(g_CalPointAccuracy[i][BIN_LX]==E_NO_CALIBRATION_DATA)
						fprintf(g_DataFP,"NO_CALIBRATION_DATA,NO_CALIBRATION_DATA,");
					else
						fprintf(g_DataFP,"%f,%f,",g_CalPointAccuracy[i][BIN_LX],g_CalPointAccuracy[i][BIN_LY]);

					if(g_CalPointAccuracy[i][BIN_RX]==E_NO_CALIBRATION_DATA)
						fprintf(g_DataFP,"NO_CALIBRATION_DATA,NO_CALIBRATION_DATA,");
					else
						fprintf(g_DataFP,"%f,%f,",g_CalPointAccuracy[i][BIN_RX],g_CalPointAccuracy[i][BIN_RY]);

					if(g_CalPointPrecision[i][BIN_LX]==E_NO_CALIBRATION_DATA)
						fprintf(g_DataFP,"NO_CALIBRATION_DATA,NO_CALIBRATION_DATA,");
					else
						fprintf(g_DataFP,"%f,%f,",g_CalPointPrecision[i][BIN_LX],g_CalPointPrecision[i][BIN_LY]);

					if(g_CalPointAccuracy[i][BIN_RX]==E_NO_CALIBRATION_DATA)
						fprintf(g_DataFP,"NO_CALIBRATION_DATA,NO_CALIBRATION_DATA\n");
					else
						fprintf(g_DataFP,"%f,%f\n",g_CalPointPrecision[i][BIN_RX],g_CalPointPrecision[i][BIN_RY]);
				}else{ //monocular
					if(g_CalPointAccuracy[i][MONO_X]==E_NO_CALIBRATION_DATA){
						fprintf(g_DataFP,"NO_CALIBRATION_DATA,NO_CALIBRATION_DATA,");
						fprintf(g_DataFP,"NO_CALIBRATION_DATA,NO_CALIBRATION_DATA\n");
					}else{
						fprintf(g_DataFP,"%f,%f,",g_CalPointAccuracy[i][MONO_X],g_CalPointAccuracy[i][MONO_Y]);
						fprintf(g_DataFP,"%f,%f\n",g_CalPointPrecision[i][MONO_X],g_CalPointPrecision[i][MONO_Y]);
					}
				}
			}

			g_LogFS << "StartRecording " << message << std::endl;
		}else{
			g_LogFS << "StartRecording(no file) " << message << std::endl;
		}

		clearData();
		g_DataCounter = 0;
		g_MessageEnd = 0;
		g_MessageBuffer[0] = '\0';
		g_isRecording = true;
		g_isShowingCalResult = false;

		strncpy(g_recordingMessage, message, sizeof(g_recordingMessage));
		//draw message on calimage
		renderRecordingMessage(g_recordingMessage, true);

		//don't render camera image
		g_isShowingCameraImage = false;

		g_LogFS << "Camera preview during recording is disabled." << std::endl;

		g_RecStartTime = getCurrentTime();
	}
	else
	{
		g_LogFS << "Warning: startRecording is called before calibration" << std::endl;
	}
}

/*!
stopRecording: terminate recording procedures.

This function is called from sockProcess() when sockProcess() received "stopRecording" command.
Call flushGazeData(), output #MESSAGE and then output #STOP_REC.

@param[in] message Message text to be inserted to the data file.
@return No value is returned.
@date 2012/07/17 add warinig message.
@date 2012/12/05 output message to log file.
@date 2015/05/12 support for rendering during the recording.
*/
void stopRecording(const char* message)
{
	if(g_isRecording)
	{
		if(g_DataFP!=NULL)
		{
			flushGazeData();
			
			if(g_MessageEnd>0)
			{
				fprintf(g_DataFP,"%s",g_MessageBuffer);
			}
			if(message[0]!='\0')
			{
				fprintf(g_DataFP,"#MESSAGE,%.3f,%s\n",getCurrentTime()-g_RecStartTime,message);
			}
			fprintf(g_DataFP,"#STOP_REC\n");
			fflush(g_DataFP); //force writing.
	
			g_LogFS << "StopRecording" << message << std::endl;
		}
		else
		{
			g_LogFS << "StopRecording (no file) " << message << std::endl;
		}

		g_isRecording = false;
		g_isShowingCameraImage = true;
	}
	else
	{
		g_LogFS << "Warning: stopRecording is called before starting" << std::endl;
	}
}

/*!
openDataFile: open data file.

This function is called from sockProcess() when sockProcess() received "openDataFile" command.
If file has already been opned, close it and open it again with overwrite mode.
As a result, contents of existing file is lost.

@param[in] filename Name of the data file.
@return No value is returned.
@todo avoid overwriting (?)
@date 2012/09/28 output header
@date 2013/12/20 support USBIO.
*/
void openDataFile(char* filename, int overwrite)
{
	std::string str(g_DataPath);
	str.append(PATH_SEPARATOR);
	str.append(filename);

	if(g_DataFP!=NULL) //if data file has already been opened, close it.
	{
		fflush(g_DataFP);
		fclose(g_DataFP);
		g_LogFS << "Close datafile to open new datafile" << std::endl;
	}

	if(overwrite==0){
		checkAndRenameFile(str);
	}

	g_DataFP = fopen(str.c_str(),"w");
	if(g_DataFP==NULL){
		g_LogFS << "Failed to open data file (" << str << ")" << std::endl;
	}
	else
	{
		g_LogFS << "Open Data File (" << str << ")" << std::endl;
	}

	fprintf(g_DataFP,"#SimpleGazeTrackerDataFile\n#TRACKER_VERSION,%s\n",VERSION);

	fprintf(g_DataFP,"#DATAFORMAT,T,");
	if(g_RecordingMode==RECORDING_MONOCULAR){
		if(g_isOutputPupilSize)
			fprintf(g_DataFP,"X,Y,P");
		else
			fprintf(g_DataFP,"X,Y");
	}else{
		if(g_isOutputPupilSize)
			fprintf(g_DataFP,"LX,LY,RX,RY,LP,RP");
		else
			fprintf(g_DataFP,"LX,LY,RX,RY");
	}

	if(g_useUSBIO){
		char buff[255];
		getUSBIODataFormatString(buff,255);
		fprintf(g_DataFP,",USBIO;%s",buff);
	}

	if(g_isOutputCameraSpecificData==USE_CAMERASPECIFIC_DATA)
		fprintf(g_DataFP,",C");
	
	fprintf(g_DataFP,"\n");

}

/*!
closeDataFile: open data file.

This function is called from sockProcess() when sockProcess() received "closeDataFile" command.

@param[in] filename Name of the data file.
@return No value is returned.
*/
void closeDataFile(void)
{
	if(g_DataFP!=NULL)
	{
		fflush(g_DataFP);
		fclose(g_DataFP);
		g_DataFP = NULL;
		
		g_LogFS << "CloseDatafile" << std::endl;
	}
	else
	{
		g_LogFS << "No file to close" << std::endl;
	}

}

/*!
insertMessage: insert message to the message list.

This function is called from sockProcess() when sockProcess() received "insertMessage" command.
Usually, messages are written to the data file when recording is stopped, however,
if number of messages reached to MAXMESSAGE, messages are written to the file immediately.

@param[in] message Message text.
@return No value is returned.

@2012/07/26 support DelayCorrection.
@2013/03/27 clear g_MessageBuffer when overflow is detected.
*/
void insertMessage(char* message)
{
	double ctd;
	ctd = getCurrentTime() - (g_RecStartTime - g_DelayCorrection);
	g_MessageEnd += snprintf(g_MessageBuffer+g_MessageEnd,MAXMESSAGE-g_MessageEnd,"#MESSAGE,%.3f,%s\n",ctd,message);
	//check overflow
	if(MAXMESSAGE-g_MessageEnd < 128)
	{
		fprintf(g_DataFP,"%s",g_MessageBuffer);
		fprintf(g_DataFP,"#OVERFLOW_FLUSH_MESSAGES,%.3f\n",ctd);
		fflush(g_DataFP);
		g_MessageEnd = 0;
		g_MessageBuffer[0] = '\0';
	}
}

/*!
insertSettings: insert message to the message list.

This function is called from sockProcess() when sockProcess() received "insertSettings" command.

@param[in] settings.
@return No value is returned.
@2013/03/27
- original string is recovered to prevent parser error in sockProcess().
*/
void insertSettings(char* settings)
{
	char* p1 = settings;
	char* p2;

	if(g_DataFP!=NULL)
	{
		while(true)
		{
			p2 = strstr(p1,"/");
			if(p2==NULL){
				fprintf(g_DataFP,"%s\n",p1);
				break;
			}
			else
			{
				*p2 = '\0';
				fprintf(g_DataFP,"%s\n",p1);
				*p2 = '/';
				p1 = p2+1;
			}
		}
		
		fflush(g_DataFP);
	}
}


/*!
connectionClosed: Stop recording, calibration and validation when connection is unexpectedly closed.

@return No value is returned.
*/
void connectionClosed(void)
{
	if(g_isRecording)
	{
		stopRecording("ConnectionClosed");
	}
	else if(g_isCalibrating)
	{
		endCalibration();
	}
	else if(g_isValidating)
	{
		endValidation();
	}

}

/*!
getEyePosition: get current eye position.

This function is called from sockProcess() when sockProcess() received "getEyePosition" command.

@param[out] pos
@param[in] nSamples If nSamples<1, nSamples is assumed to be 1.
@return No value is returned.

@date 2012/10/26 pupil size is returned.
@date 2013/03/28 argument "nSamples" is added to support moving average.
*/
void getEyePosition(double* pos, int nSamples)
{
	if(nSamples<=1)
	{
		if(g_RecordingMode==RECORDING_MONOCULAR){
			pos[0] = g_CurrentEyeData[MONO_X];
			pos[1] = g_CurrentEyeData[MONO_Y];
			pos[2] = g_CurrentPupilSize[MONO_P];
		}else{
			pos[0] = g_CurrentEyeData[BIN_LX];
			pos[1] = g_CurrentEyeData[BIN_LY];
			pos[2] = g_CurrentEyeData[BIN_RX];
			pos[3] = g_CurrentEyeData[BIN_RY];
			pos[4] = g_CurrentPupilSize[BIN_LP];
			pos[5] = g_CurrentPupilSize[BIN_RP];
		}
	}
	else
	{
		double tmppos[4];
		if(g_RecordingMode==RECORDING_MONOCULAR){
			int index, n=0;
			pos[0] = pos[1] = pos[2] = 0;
			for(int i=0; i<nSamples; i++){
				index = g_DataCounter-1-i;
				if(index<0) break;
				if(g_EyeData[index][MONO_PUPIL_X]>E_FIRST_ERROR_CODE){
					getGazePositionMono(g_EyeData[index], tmppos); //One must be subtracted from g_DataCounter because it points next address.
					pos[0] += tmppos[MONO_X];
					pos[1] += tmppos[MONO_Y];
					pos[2] += g_PupilSizeData[index][MONO_P];
					n++;
				}
			}
			if(n>0){
				pos[0] /= n;
				pos[1] /= n;
				pos[2] /= n;
			}else{
				pos[0] = E_NAN_IN_MOVING_AVERAGE;
				pos[1] = E_NAN_IN_MOVING_AVERAGE;
				pos[2] = E_NAN_IN_MOVING_AVERAGE;
			}
		}else{
			int index, nl=0, nr=0;
			pos[0] = pos[1] = pos[2] = pos[3] = pos[4] = pos[5] = 0;
			for(int i=0; i<nSamples; i++){
				index = g_DataCounter-1-i;
				if(index<0) break;
				getGazePositionBin(g_EyeData[index], tmppos); //One must be subtracted from g_DataCounter because it points next address.
				if(g_EyeData[index][BIN_PUPIL_LX]>E_FIRST_ERROR_CODE){
					pos[0] += tmppos[BIN_LX];
					pos[1] += tmppos[BIN_LY];
					pos[4] += g_PupilSizeData[index][BIN_LP];
					nl++;
				}
				if(g_EyeData[index][BIN_PUPIL_RX]>E_FIRST_ERROR_CODE){
					pos[2] += tmppos[BIN_RX];
					pos[3] += tmppos[BIN_RY];
					pos[5] += g_PupilSizeData[index][BIN_RP];
					nr++;
				}
			}
			if(nl>0){
				pos[0] /= nl;
				pos[1] /= nl;
				pos[4] /= nl;
			}else{
				pos[0] /= E_NAN_IN_MOVING_AVERAGE;
				pos[1] /= E_NAN_IN_MOVING_AVERAGE;
				pos[4] /= E_NAN_IN_MOVING_AVERAGE;
			}
			if(nr>0)
			{
				pos[2] /= nr;
				pos[3] /= nr;
				pos[5] /= nr;
			}else{
				pos[2] /= E_NAN_IN_MOVING_AVERAGE;
				pos[3] /= E_NAN_IN_MOVING_AVERAGE;
				pos[5] /= E_NAN_IN_MOVING_AVERAGE;
			}
		}
	}
}


/*!
getPreviousEyePositionForward: get previous eye position from head

This function is called from sockProcess() when sockProcess() received "getEyePositionList" command.

@param[out] pos.
@param[in] index.
@return E_FAIL if offset is greater than number of data.
@todo overflow is not concidered.

@date 2013/03/06 created.
@date 2013/03/08 return tickdata.
@date 2013/03/28 check error code.
*/
int getPreviousEyePositionForward(double* pos, int offset)
{
	if((g_DataCounter-1)<offset){ //One must be subtracted from g_DataCounter because it points next address.
		return E_FAIL;
	}
	if(g_RecordingMode==RECORDING_MONOCULAR){
		pos[0] = g_TickData[offset];
		if(g_EyeData[offset][MONO_PUPIL_X]>E_FIRST_ERROR_CODE){
			getGazePositionMono(g_EyeData[offset], &pos[1]);
		}else{
			pos[1] = g_EyeData[offset][MONO_PUPIL_X];
			pos[2] = g_EyeData[offset][MONO_PUPIL_Y];
		}
		pos[3] = g_PupilSizeData[offset][MONO_P];
	}else{
		pos[0] = g_TickData[offset];
		getGazePositionBin(g_EyeData[offset], &pos[1]);
		if(g_EyeData[offset][BIN_PUPIL_LX]<=E_FIRST_ERROR_CODE){
			pos[1] = g_EyeData[offset][BIN_PUPIL_LX];
			pos[2] = g_EyeData[offset][BIN_PUPIL_LY];
		}
		if(g_EyeData[offset][BIN_PUPIL_RX]<=E_FIRST_ERROR_CODE){
			pos[3] = g_EyeData[offset][BIN_PUPIL_RX];
			pos[4] = g_EyeData[offset][BIN_PUPIL_RY];
		}
		pos[5] = g_PupilSizeData[offset][BIN_LP];
		pos[6] = g_PupilSizeData[offset][BIN_RP];
	}
	return S_OK;
}

/*!
getPreviousEyePositionReverse: get previous eye position from tail

This function is called from sockProcess() when sockProcess() received "getEyePositionList" command.

@param[out] pos.
@param[in] index.
@param[in] newDataOnly.
@return E_FAIL if offset is greater than number of data.
@todo overflow is not concidered.

@date 2013/02/28 created.
@date 2013/03/06 renamed: getPreviousEyePosition -> getPreviousEyePositionReverse
@date 2013/03/08 newDataOnly is added, return tickdata.
@date 2013/03/28 check error code.
*/
int getPreviousEyePositionReverse(double* pos, int offset, bool newDataOnly)
{
	int index = (g_DataCounter-1)-offset; //One must be subtracted from g_DataCounter because it points next address.

	if(index<0){
		return E_FAIL;
	}
	if(newDataOnly && index<=g_LastSentDataCounter){
		return E_FAIL;
	}
	if(g_RecordingMode==RECORDING_MONOCULAR){
		pos[0] = g_TickData[index];
		if(g_EyeData[index][MONO_PUPIL_X]>E_FIRST_ERROR_CODE){
			getGazePositionMono(g_EyeData[index], &pos[1]);
		}else{
			pos[1] = g_EyeData[index][MONO_PUPIL_X];
			pos[2] = g_EyeData[index][MONO_PUPIL_Y];
		}
		pos[3] = g_PupilSizeData[index][MONO_P];
	}else{
		pos[0] = g_TickData[index];
		getGazePositionBin(g_EyeData[index], &pos[1]);
		if(g_EyeData[index][BIN_PUPIL_LX]<=E_FIRST_ERROR_CODE){
			pos[1] = g_EyeData[index][BIN_PUPIL_LX];
			pos[2] = g_EyeData[index][BIN_PUPIL_LY];
		}
		if(g_EyeData[index][BIN_PUPIL_RX]<=E_FIRST_ERROR_CODE){
			pos[3] = g_EyeData[index][BIN_PUPIL_RX];
			pos[4] = g_EyeData[index][BIN_PUPIL_RY];
		}
		pos[5] = g_PupilSizeData[index][BIN_LP];
		pos[6] = g_PupilSizeData[index][BIN_RP];
	}
	return S_OK;
}

/*!
getMessageBufferPointer: returns a pointer to g_MessageBuffer.
@date 2013/03/27 Created.
*/
char* getMessageBufferPointer( void )
{
	return g_MessageBuffer;
}

/*!
updateLastSentDataCounter: update LastSentDataCounter.
This function is called from sockProcess() when sockProcess() received "getEyePositionList" command.

@date 2013/03/08 created.
*/
void updateLastSentDataCounter(void)
{
	g_LastSentDataCounter = g_DataCounter-1;
}

/*!
getCalibrationResults: get calibration error.

This function is called from sockProcess() when sockProcess() received "getCalResults" command.

@param[out] Goodness double Goodness of calibration results, defined as a ratio of linear regression coefficients to screen size.
.
@param[out] MaxError Maximum calibration error.
@param[out] MeanError Mean calibration error.
@return No value is returned.
*/
void getCalibrationResults( double *Goodness, double *MaxError, double *MeanError )
{
	if(g_RecordingMode==RECORDING_MONOCULAR){
		Goodness[MONO_X] = g_CalGoodness[MONO_X];
		Goodness[MONO_Y] = g_CalGoodness[MONO_Y];
		MaxError[MONO_1] = g_CalMaxError[MONO_1];
		MeanError[MONO_1] = g_CalMeanError[MONO_1];
	}else{
		Goodness[BIN_LX] = g_CalGoodness[BIN_LX];
		Goodness[BIN_LY] = g_CalGoodness[BIN_LY];
		Goodness[BIN_RX] = g_CalGoodness[BIN_RX];
		Goodness[BIN_RY] = g_CalGoodness[BIN_RY];
		MaxError[BIN_L] = g_CalMaxError[BIN_L];
		MaxError[BIN_R] = g_CalMaxError[BIN_R];
		MeanError[BIN_L] = g_CalMeanError[BIN_L];
		MeanError[BIN_R] = g_CalMeanError[BIN_R];
	}
}

/*!
getCalibrationResultsDetail: get detailed calibration error.

Pair of position of calibration/validation target point and recorded gaze position is returned as a string of comma-separated values
This function is called from sockProcess() when sockProcess() received "getCalResultsDetail" command.

@param[out] errorstr 
@param[in] size Size of errorstr buffer.
@param[out] len Length of the string written to errorstr buffer.

@return No value is returned.
@2012/10/25 terminator is changed to \0.
*/
void getCalibrationResultsDetail( char* errorstr, int size, int* len)
{
	char* dstbuf = errorstr;
	int s = size;
	int idx,l;
	double xy[4];

	for(idx=0; idx<g_DataCounter; idx++)
	{
		if(g_RecordingMode==RECORDING_MONOCULAR){ //monocular
			getGazePositionMono(g_EyeData[idx], xy);
			l = snprintf(dstbuf, s, "%.0f,%.0f,%.0f,%.0f,",g_CalPointData[idx][0],g_CalPointData[idx][1],xy[MONO_X],xy[MONO_Y]);
		}else{ //binocular
			getGazePositionBin(g_EyeData[idx], xy);
			l = snprintf(dstbuf, s, "%.0f,%.0f,%.0f,%.0f,%.0f,%.0f,",g_CalPointData[idx][0],g_CalPointData[idx][1],xy[BIN_LX],xy[BIN_LY],xy[BIN_RX],xy[BIN_RY]);
		}
		dstbuf = dstbuf+l;
		s -= l;
		if(s<=1) break; //check overflow
	}

	*len = size-s;
	if(*len>0){
		//Overwrite last comma by '\0'
		errorstr[*len-1] = '\0';
	}
}


/*!
getCurrentMenuString: get current menu text.

This function is called from sockProcess() when sockProcess() received "getCurrMenu" command.

@param[out] p Pointer to the buffer to which menu text is written.
@param[in] maxlen Size of buffer pointed by p.
@return No value is returned.
*/
void getCurrentMenuString(char *p, int maxlen)
{
	strncpy(p, g_MenuString[g_CurrentMenuPosition].c_str(), maxlen-1);
}


/*!
startMeasurement: start measurement without recording.

This function is called from sockProcess() when sockProcess() received "startMeasurement" command.

@param[out] p Pointer to the buffer to which menu text is written.
@param[in] maxlen Size of buffer pointed by p.
@return No value is returned.
@date 2012/07/17 Created.
@date 2012/12/13 g_isShowingCameraImage = true during measurement.
@date 2013/03/27 clear g_MessageBuffer.
*/
void startMeasurement(void)
{
	if(g_isCalibrated){
		clearData();
		g_DataCounter = 0;
		g_MessageEnd = 0;
		g_MessageBuffer[0] = '\0';
		g_isRecording = true;
		g_isShowingCameraImage = true;
		g_isShowingCalResult = false;

		g_RecStartTime = getCurrentTime();
		g_LogFS << "StartMeasurement" << std::endl;
	}
	else
	{
		g_LogFS << "Warning: StartMeasurement is called before calibration" << std::endl;
	}
}


/*!
startMeasurement: stop measurement.

This function is called from sockProcess() when sockProcess() received "stopMeasurement" command.

@return No value is returned.
@date 2012/07/17 Created.
*/
void stopMeasurement(void)
{
	if(g_isRecording)
	{
		g_LogFS << "StopMeasurement" << std::endl;
	
		g_isRecording = false;
		g_isShowingCameraImage = true;
	}
	else
	{
		g_LogFS << "Waring: StopMeasurement is called before starting." << std::endl;	
	}
}

/*!
allowRendering: allow rendering.

@return No value is returned.
@date 2012/07/27 Created.
*/
void allowRendering(void)
{
	g_isInhibitRendering = false;
}

/*!
inhibitRendering: inhibit rendering.

@return No value is returned.
@date 2012/07/27 Created.
*/
void inhibitRendering(void)
{
	g_isInhibitRendering = true;
}

/*!
isBinocularMode: check recording mode.

@return True if binocular mode.
@date 2013/03/26 Created.
*/
bool isBinocularMode(void)
{
	if(g_RecordingMode==RECORDING_BINOCULAR)
		return true;
	else
		return false;
}
