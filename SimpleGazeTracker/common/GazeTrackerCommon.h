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
*/



#define VERSION "0.8.0"

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

#define SCREEN_WIDTH 1024
#define SCREEN_HEIGHT 768

#define MAXDATA 432000 //120*60sec*60min, 393*18min
#define MAXCALDATA 7200 // 120*30sec, 393*18.3sec
#define MAXCALPOINT 60
#define MAXCALSAMPLEPERPOINT (MAXCALDATA/MAXCALPOINT)
#define MAXMESSAGE 262144

#define PORT_RECV        10000
#define PORT_SEND        10001

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

//Recording Mode
#define RECORDING_MONOCULAR 0
#define RECORDING_BINOCULAR 1

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

#define MENU_THRESH_PUPIL 0
#define MENU_THRESH_PURKINJE 1
#define MENU_MINPOINTS 2
#define MENU_MAXPOINTS 3
#define MENU_SEARCHAREA 4
#define MENU_EXCLUDEAREA 5
#define MENU_GENERAL_NUM 6

#define MENU_MAX_ITEMS 12
#define MENU_STRING_MAX 24

#define USE_CAMERASPECIFIC_DATA 1
#define NO_CAMERASPECIFIC_DATA 0
#define NO_USBIO -1

#define TYPE_CALIBRATION 0
#define TYPE_VALIDATION 1

extern int detectPupilPurkinjeMono( int Threshold1, int PurkinjeSearchArea, int PurkinjeThreshold, int PurkinjeExclude, int PointMin, int PointMax, double results[MAX_DETECTION_RESULTS] );
extern int detectPupilPurkinjeBin( int Threshold1, int PurkinjeSearchArea, int PurkinjeThreshold, int PurkinjeExclude, int PointMin, int PointMax, double results[MAX_DETECTION_RESULTS] );
extern void estimateParametersMono(int dataCounter, double eyeData[MAXDATA][4], double calPointData[MAXDATA][2]);
extern void estimateParametersBin(int dataCounter, double eyeData[MAXDATA][4], double calPointData[MAXDATA][2]);
extern void getGazePositionMono(double* im, double* xy);
extern void getGazePositionBin(double* im, double* xy);
extern void drawCalResult(int dataCounter, double eyeData[MAXDATA][4], double calPointData[MAXDATA][2], int numCalPoint, double calPointList[MAXCALDATA][2], double calArea[4]);
extern void setCalibrationResults( int dataCounter, double eyeData[MAXDATA][4], double calPointData[MAXDATA][2], double Goodness[4], double MaxError[2], double MeanError[2] );
extern void setCalibrationError( int dataCounter, double eyeData[MAXDATA][4], double calPointData[MAXDATA][2], int numCalPoint, double calPointList[MAXCALPOINT][2], double calPointAccuracy[MAXCALPOINT][4], double calPointPrecision[MAXCALPOINT][4] );
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
extern int g_isShowDetectionErrorMsg;
extern int g_isOutputCameraSpecificData;

extern int g_PortRecv;
extern int g_PortSend;

extern double g_ParamX[6],g_ParamY[6]; //Monocular: 3 params, Binocular 6 parameters.
extern int g_Threshold;

extern int g_RecordingMode;

extern std::string g_DataPath;
extern std::string g_AppDirPath;
extern std::string g_ParamPath;

extern std::fstream g_LogFS;
extern std::string g_CameraConfigFileName;

extern void startCalibration(int x1, int y1, int x2, int y2);
extern void getCalSample(double x, double y, int samples);
extern void endCalibration(void);

extern void startValidation(int x1, int y1, int x2, int y2);
extern void getValSample(double x, double y, int samples);
extern void endValidation(void);
extern void getCalibrationResults( double Goodness[4], double MaxError[2], double MeanError[2] );
extern void getCalibrationResultsDetail( char* errorstr, int size, int* len);
extern void getCurrentMenuString(char *p, int maxlen);

extern void toggleCalResult(int param);
extern void saveCalValResultsDetail(void);

extern void startRecording(const char* message);
extern void stopRecording(const char* message);
extern void openDataFile(char* filename, int overwrite);
extern void closeDataFile(void);
extern void insertMessage(char* message);
extern void insertSettings(char* settings);
extern void connectionClosed(void);
extern void getEyePosition(double* pos, int nSamples);
extern int getPreviousEyePositionForward(double* pos, int offset);
extern int getPreviousEyePositionReverse(double* pos, int offset, bool newDataOnly);
extern char* getMessageBufferPointer( void );
extern void updateLastSentDataCounter(void);
extern void saveCameraImage(const char* filename);
extern void startMeasurement(void);
extern void stopMeasurement(void);
extern void allowRendering(void);
extern void inhibitRendering(void);
extern bool isBinocularMode(void);

//Camera.cpp
extern int initCamera( void );
extern int getCameraImage( void );
extern void cleanupCamera( void );
extern void saveCameraParameters( void );
extern const char* getEditionString( void );
extern unsigned int getCameraSpecificData( void );

//DetectEye.cpp
extern int initBuffers(void);

//custom menu
extern int customCameraMenu(SDL_Event* SDLevent, int currentMenuPosition);
extern int g_CustomMenuNum;
extern void updateCustomMenuText( void );
extern std::string g_MenuString[MENU_MAX_ITEMS];

//Platform dependent
extern int initTimer(void);
extern double getCurrentTime(void);
extern void sleepMilliseconds(int);
extern int getDataDirectoryPath(std::string* path);
extern int getApplicationDirectoryPath(std::string* path);
extern int getParameterDirectoryPath(std::string* path);
extern int getLogFilePath(std::string* path);
extern int checkAndCreateDirectory(std::string path);
extern int checkAndRenameFile(std::string path);
extern int checkFile(std::string path, const char* filename);
extern int checkAndCopyFile(std::string path, const char* filename, std::string sourcePath);

//USBIO
extern bool g_useUSBIO;
extern bool g_useUSBThread;
extern int g_numUSBADChannels;
extern int initUSBIO(void);
extern std::string g_USBIOBoard;
extern std::string g_USBIOParamAD;
extern std::string g_USBIOParamDI;
extern void setUSBIOData(int dataCounter);
extern void getUSBIODataFormatString(char* buff, int buffsize);
extern void getUSBIODataString(int index, char* buff, int buffsize);
extern void cleanupUSBIO(void);
