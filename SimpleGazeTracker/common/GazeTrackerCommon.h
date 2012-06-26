/*!
@file GazeTrackerCommon.h
@author Hiroyuki Sogo
@copyright GNU General Public License (GPL) version 3.
@brief Camera-independent constants, external functions and valiables are defined.

@date 2012/03/23
- Custom menu is supported.
*/



#define VERSION "0.5.0"

#ifdef _WIN32
#include <windows.h>
#define snprintf sprintf_s
#define strncpy(dst,src,size) strcpy_s(dst,size,src)
#define PATH_SEPARATOR "\\"
#else
#define S_OK                             0
#define E_FAIL                 -2147467259
#define SUCCEEDED(Status) ((int)(Status) >= 0)
#define FAILED(Status) ((int)(Status)<0)
#define PATH_SEPARATOR "/"
#endif

#include <SDL/SDL.h>
#include <string>
#include <iostream> 

#define PREVIEW_WIDTH  640
#define PREVIEW_HEIGHT 480

#define SENDIMAGE_WIDTH ROI_WIDTH
#define SENDIMAGE_HEIGHT ROI_HEIGHT

#define SCREEN_WIDTH 1024
#define SCREEN_HEIGHT 768

#define MAXDATA 432000 //120*60sec*60min, 393*18min
#define MAXCALDATA 7200 // 120*30sec, 393*18.3sec
#define MAXCALPOINT 100
#define MAXMESSAGE 65536

//Error codes
#define E_FIRST_ERROR_CODE -10000
#define E_PUPIL_PURKINJE_DETECTION_FAIL -10000 
#define E_MULTIPLE_PUPIL_CANDIDATES -10001
#define E_NO_PUPIL_CANDIDATE        -10002
#define	E_NO_PURKINJE_CANDIDATE     -10003
#define E_NO_FINE_PUPIL_CANDIDATE   -10004
#define S_PUPIL_PURKINJE                 0

//Recording Mode
#define RECORDING_MONOCULAR 0
#define RECORDING_BINOCULAR 1

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

#define MONO_PUPIL_X    0
#define MONO_PUPIL_Y    1
#define MONO_PURKINJE_X 2
#define MONO_PURKINJE_Y 3
#define BIN_PUPIL_LX    0
#define BIN_PUPIL_LY    1
#define BIN_PURKINJE_LX 2
#define BIN_PURKINJE_LY 3
#define BIN_PUPIL_RX    4
#define BIN_PUPIL_RY    5
#define BIN_PURKINJE_RX 6
#define BIN_PURKINJE_RY 7

#define MENU_THRESH_PUPIL 0
#define MENU_THRESH_PURKINJE 1
#define MENU_MINPOINTS 2
#define MENU_MAXPOINTS 3
#define MENU_SEARCHAREA 4
#define MENU_EXCLUDEAREA 5
#define MENU_GENERAL_NUM 6

#define MENU_MAX_ITEMS 12
#define MENU_STRING_MAX 24

extern int detectPupilPurkinjeMono( int Threshold1, int PurkinjeSearchArea, int PurkinjeThreshold, int PurkinjeExclude, int PointMin, int PointMax, double results[8] );
extern int detectPupilPurkinjeBin( int Threshold1, int PurkinjeSearchArea, int PurkinjeThreshold, int PurkinjeExclude, int PointMin, int PointMax, double results[8] );
extern void estimateParametersMono(int dataCounter, double eyeData[MAXDATA][4], double calPointData[MAXDATA][2]);
extern void estimateParametersBin(int dataCounter, double eyeData[MAXDATA][4], double calPointData[MAXDATA][2]);
extern void getGazePositionMono(double* im, double* xy);
extern void getGazePositionBin(double* im, double* xy);
extern void drawCalResult(int dataCounter, double eyeData[MAXDATA][4], double calPointData[MAXDATA][2], int numCalPoint, double calPointList[MAXCALDATA][2], double calArea[4]);
extern void setCalibrationResults( int dataCounter, double eyeData[MAXDATA][4], double calPointData[MAXDATA][2], double Goodness[4], double MaxError[2], double MeanError[2] );
extern void drawRecordingMessage( void );

extern int sockInit(void);
extern int sockAccept(void);
extern int sockProcess(void);

extern unsigned char* g_frameBuffer;
extern int* g_pCameraTextureBuffer;
extern int* g_pCalResultTextureBuffer;
extern unsigned char* g_SendImageBuffer;
extern int g_CameraWidth;
extern int g_CameraHeight;
extern int g_PreviewWidth;
extern int g_PreviewHeight;
extern int g_ROIWidth;
extern int g_ROIHeight;

extern bool g_isShowingCameraImage;

extern double g_ParamX[6],g_ParamY[6]; //Monocular: 3 params, Binocular 6 parameters.
extern int g_Threshold;

extern int g_RecordingMode;

extern std::string g_DataPath;
extern std::string g_AppDirPath;
extern std::string g_ParamPath;

extern std::fstream g_LogFS;

extern void startCalibration(int x1, int y1, int x2, int y2);
extern void getCalSample(double x, double y);
extern void endCalibration(void);

extern void startValidation(int x1, int y1, int x2, int y2);
extern void getValSample(double x, double y);
extern void endValidation(void);
extern void getCalibrationResults( double Goodness[4], double MaxError[2], double MeanError[2] );
extern void getCalibrationResultsDetail( char* errorstr, int size, int* len);
extern void getCurrentMenuString(char *p, int maxlen);

extern void toggleCalResult(void);

extern void startRecording(const char* message);
extern void stopRecording(const char* message);
extern void openDataFile(char* filename);
extern void closeDataFile(void);
extern void insertMessage(char* message);
extern void insertSettings(char* settings);
extern void connectionClosed(void);
extern void getEyePosition(double* pos);
extern void saveCameraImage(const char* filename);

//Camera.cpp
extern int initCamera( const char* ParamPath );
extern int getCameraImage( void );
extern void cleanupCamera( void );
extern void saveCameraParameters(const char* ParamPath);

//DetectEye.cpp
extern int initBuffers(void);

//custom menu
extern int customCameraMenu(SDL_Event* SDLevent, int currentMenuPosition);
extern int g_CustomMenuNum;
extern void updateCustomMenuText( void );
extern std::string g_MenuString[MENU_MAX_ITEMS];

//Platform dependent
int initTimer(void);
double getCurrentTime(void);
void sleepMilliseconds(int);
int getDataDirectoryPath(std::string* path);
//int getApplicationDirectoryPath(std::string* path);
int getParameterDirectoryPath(std::string* path);
int getLogFilePath(std::string* path);
int checkDirectory(std::string path);
int checkAndCopyFile(std::string path, const char* filename, std::string sourcePath);

