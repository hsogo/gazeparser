/*!
@file GazeTrackerCommon.h
@author Hiroyuki Sogo
@copyright GNU General Public License (GPL) version 3.
@brief Camera-independent constants, external functions and valiables are defined.

@date 2012/03/23
- Custom menu is supported.
@date 2012/07/02
- delete obsolete definitions
- define new error code: E_MULTIPLE_PURKINJE_CANDIDATES
@date 2012/09/28
- Support pupil size recording
@date 2012/10/15
- change version number
@date 2013/02/14
- change version number
@date 2013/03/06
- added: getPreviousEyePositionForward, getPreviousEyePositionReverse
@date 2015/03/12
- changed: MENU_MIN_PUPILWIDTH and MENU_MAX_PUPILWIDTH
- 
*/



#define VERSION "0.11.1"

#include <wx/wxprec.h>
#ifndef WX_PRECOMP
#include <wx/wx.h>
#endif

#ifdef _WIN32
#include <windows.h>
//#define snprintf sprintf_s
#define strncpy(dst,src,size) strcpy_s(dst,size,src)
#define PATH_SEPARATOR "\\"
#else
#define S_OK                             0
#define E_FAIL                 -2147467259
#define SUCCEEDED(Status) ((int)(Status) >= 0)
#define FAILED(Status) ((int)(Status)<0)
#define PATH_SEPARATOR "/"
#endif

#include <string>
#include <iostream> 
#include <opencv2/opencv.hpp>
#include <opencv2/core/core.hpp>


// Parameters

#define PREVIEW_WIDTH  640
#define PREVIEW_HEIGHT 480

#define SCREEN_WIDTH 1024
#define SCREEN_HEIGHT 768

#define PORT_RECV        10000
#define PORT_SEND        10001

#define USE_CAMERASPECIFIC_DATA 1
#define NO_CAMERASPECIFIC_DATA 0
#define NO_USBIO -1

// Gaze detection parameters

#define OBLATENESS_LOW  0.67
#define OBLATENESS_HIGH 1.50
#define MAX_FIRST_CANDIDATES 5


//Error codes
#define E_FIRST_ERROR_CODE -10000
#define E_PUPIL_PURKINJE_DETECTION_FAIL -10000
#define E_MULTIPLE_PUPIL_CANDIDATES     -10001
#define E_NO_PUPIL_CANDIDATE            -10002
#define	E_NO_PURKINJE_CANDIDATE         -10003
#define E_MULTIPLE_PURKINJE_CANDIDATES  -10004
#define E_NO_FINE_PUPIL_CANDIDATE       -10005
#define E_NAN_IN_MOVING_AVERAGE         -10006
#define E_NO_CALIBRATION_DATA			-11001

#define S_PUPIL_PURKINJE                     0
#define E_NO_PUPILSIZE                       0


// Data buffer size
#define MAXDATA 432000 //120*60min, 393*18min
#define MAXCALDATA 7200 // 120*60sec, 393*18.3sec
#define MAXCALPOINT 60
#define MAXCALSAMPLEPERPOINT (MAXCALDATA/MAXCALPOINT)
#define MAXMESSAGE 262144
#define RECV_BUFFER_SIZE 4096

//for g_Eyedata
#define MONO_X 0
#define MONO_Y 1
#define MONO_1 0
#define BIN_LX 0
#define BIN_LY 1
#define BIN_RX 2
#define BIN_RY 3
#define BIN_L 0
#define BIN_R 1
#define BIN_X 0
#define BIN_Y 1

//for g_PupilData
#define MONO_P 0
#define BIN_LP 0
#define BIN_RP 1

//for detectionResults
#define MONO_PUPIL_X    0
#define MONO_PUPIL_Y    1
#define MONO_PURKINJE_X 2
#define MONO_PURKINJE_Y 3
#define MONO_PUPILSIZE  4
#define BIN_PUPIL_LX    0
#define BIN_PUPIL_LY    1
#define BIN_PURKINJE_LX 2
#define BIN_PURKINJE_LY 3
#define BIN_PUPIL_RX    4
#define BIN_PUPIL_RY    5
#define BIN_PURKINJE_RX 6
#define BIN_PURKINJE_RY 7
#define BIN_PUPILSIZE_L 8
#define BIN_PUPILSIZE_R 9
#define MAX_DETECTION_RESULTS 10

// Recording Mode
#define RECORDING_MONOCULAR 0
#define RECORDING_BINOCULAR 1

// Application status
#define TYPE_CALIBRATION 0
#define TYPE_VALIDATION 1

#define STATE_FREE 0
#define STATE_RECORDING 1
#define STATE_VALIDATION 2
#define STATE_CALIBRATION 3

// Menu

#define MENU_THRESH_PUPIL 0
#define MENU_THRESH_PURKINJE 1
#define MENU_MIN_PUPILWIDTH 2
#define MENU_MAX_PUPILWIDTH 3
#define MENU_SEARCHAREA 4
#define MENU_EXCLUDEAREA 5
#define MENU_MORPHTRANS 6
#define MENU_GENERAL_NUM 7

#define MENU_MAX_ITEMS 12
#define MENU_STRING_MAX 24

#define MENU_LEFT_KEY 0
#define MENU_RIGHT_KEY 1


// Image buffers

extern unsigned char* g_frameBuffer;
extern int* g_pCameraTextureBuffer;
extern int* g_pCalResultTextureBuffer;
extern unsigned char* g_pPreviewTextureBuffer;
extern unsigned char* g_SendImageBuffer;

extern cv::Mat g_SrcImg;
extern cv::Mat g_DstImg;
extern cv::Mat g_CalImg;
extern cv::Mat g_PreviewImg;
extern cv::Rect g_ROI;
extern cv::Mat g_MorphTransKernel;

extern int initBuffers(void);
extern void updateMorphTransKernel(void);
extern void releaseBuffers(void);


// Image processing

int detectPupilPurkinjeMono(int Threshold1, int PurkinjeSearchArea, int PurkinjeThreshold, int PurkinjeExclude, int MinWidth, int MaxWidth, double* results);
int detectPupilPurkinjeBin(int Threshold1, int PurkinjeSearchArea, int PurkinjeThreshold, int PurkinjeExclude, int MinWidth, int MaxWidth, double* results);


// Global parameters (read from CONFIG)
extern int g_CameraWidth;
extern int g_CameraHeight;
extern int g_PreviewWidth;
extern int g_PreviewHeight;
extern int g_ROIWidth;
extern int g_ROIHeight;
extern int g_MorphologicalTrans;
extern int g_DelayCorrection;

extern int g_ShowDetectionErrorMsg;
extern int g_OutputCameraSpecificData;
extern int g_OutputPupilSize;

extern int g_PortRecv;
extern int g_PortSend;

extern int g_Threshold;
extern int g_MaxPupilWidth;
extern int g_MinPupilWidth;
extern int g_PurkinjeThreshold;
extern int g_PurkinjeSearchArea;
extern int g_PurkinjeExcludeArea;

extern bool g_useUSBIO;

extern int g_RecordingMode;


// Application directies and files
extern std::string g_DataPath;
extern std::string g_AppDirPath;
extern std::string g_ParamPath;
extern std::string g_DocPath;
extern std::string g_ConfigFileName;


// Logging
//extern std::fstream g_LogFS;
extern int openLogFile(const char* fname);
extern int outputLog(const char* message);
extern int outputLogDlg(const wxString &message, const wxString &caption, long style);
extern void closeLogFile(void);


//Camera specific functions
extern int initCameraParameters( char* buff, char* parambuff );
extern int initCamera( void );
extern int getCameraImage( void );
extern void cleanupCamera( void );
extern void saveCameraParameters( std::fstream* fs );
extern const char* getEditionString( void );
extern const char* getDefaultConfigString(void);
extern unsigned int getCameraSpecificData( void );


//custom menu

extern std::string g_MenuString[MENU_MAX_ITEMS];
extern int g_CustomMenuNum;
extern std::string updateCustomMenuText(int id);
extern int customCameraMenu(int code, int currentMenuPosition);
extern void updateCustomCameraParameterFromMenu(int id, std::string val);


//Platform dependent

extern int initTimer(void);
extern double getCurrentTime(void);
extern void sleepMilliseconds(int);
extern int getDataDirectoryPath(std::string* path);
extern int getApplicationDirectoryPath(std::string* path);
extern int getParameterDirectoryPath(std::string* path);
extern int checkAndCreateDirectory(std::string path);
extern int checkAndRenameFile(std::string path);
extern int checkFile(std::string path, const char* filename);
extern int checkAndCopyFile(std::string path, const char* filename, std::string sourcePath);
extern int openLocation(std::string location);
extern std::string joinPath(const char* p1, const char* p2);
extern std::string joinPath(std::string p1, std::string p2);
extern std::string getCurrentWorkingDirectory(void);


// User interface

extern bool g_ShowCameraImage;
extern std::string g_MenuString[];
extern std::string g_CustomMenuString[];
extern bool g_runMainThread;

