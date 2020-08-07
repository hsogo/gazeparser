
#define _CRT_SECURE_NO_WARNINGS

#include <sstream>
#include <fstream>
#include <iostream>

#include <opencv2/opencv.hpp>
#include <opencv2/core/core.hpp>

#include <wx/wxprec.h>
#ifndef WX_PRECOMP
#include <wx/wx.h>
#endif
#include <wx/cmdline.h>

#include "SGTCommon.h"
#include "SGTApp.h"
#include "SGTMainFrame.h"


#ifdef _WIN32
#include "resource.h"
#endif

wxDECLARE_APP(SGTApp);

// common parameters (read from CONFIG)
int g_CameraWidth;
int g_CameraHeight;
int g_PreviewWidth;
int g_PreviewHeight;
int g_ROIWidth;
int g_ROIHeight;
int g_MorphologicalTrans;
bool g_useUSBIO;

int g_Threshold = 55;  /*!< Pupil candidates are sought from image areas darker than this value. */
int g_MaxPupilWidth = 30; /*!< Dark areas wider than this value is removed from pupil candidates. */
int g_MinPupilWidth = 10; /*!< Dark areas narrower than this value is removed from pupil candidates. */
int g_PurkinjeThreshold = 240;  /*!<  */
int g_PurkinjeSearchArea = 60;  /*!<  */
int g_PurkinjeExcludeArea = 20; /*!<  */

int g_RecordingMode = RECORDING_BINOCULAR; /*!< Holds recording mode. @note This value is modified only when application is being initialized (i.e. in initParameters()).*/
int g_ShowDetectionErrorMsg = 0; /*!< Holds DetectionError message visibility.*/
int g_OutputPupilSize = 1; /*!< Holds whether pupil size is output to datafile.*/
int g_OutputCameraSpecificData = NO_CAMERASPECIFIC_DATA;/*!< Holds whether camera-specific data is output to datafile.*/
int g_DelayCorrection = 0;

bool g_ShowCameraImage = true; /*!< If true, camera image is rendered. This must be false while recording.*/

// COFIG handling
std::string g_ParamPath;
std::string g_DataPath;
std::string g_ConfigFileName;
std::string g_AppDirPath;

// USB
std::string g_USBIOBoard;
std::string g_USBIOParamAD;
std::string g_USBIOParamDI;

// Image buffers
unsigned char* g_frameBuffer;
int* g_pCameraTextureBuffer;
int* g_pCalResultTextureBuffer;
unsigned char* g_SendImageBuffer;

//prototype definition
int initParameters(void);
int saveParameters(void);

int g_PortRecv = PORT_RECV;
int g_PortSend = PORT_SEND;

extern int detectPupilPurkinjeMono(int Threshold1, int PurkinjeSearchArea, int PurkinjeThreshold, int PurkinjeExclude, int MinWidth, int MaxWidth, double* results);
extern int detectPupilPurkinjeBin(int Threshold1, int PurkinjeSearchArea, int PurkinjeThreshold, int PurkinjeExclude, int MinWidth, int MaxWidth, double* results);


wxIMPLEMENT_APP(SGTApp);

static const wxCmdLineEntryDesc g_cmdLineDesc[] =
{
	 { wxCMD_LINE_SWITCH, "h", "help", "displays help on the command line parameters",
		  wxCMD_LINE_VAL_NONE, wxCMD_LINE_OPTION_HELP },
	 { wxCMD_LINE_SWITCH, "config", "config", "test switch",
		  wxCMD_LINE_VAL_NONE, wxCMD_LINE_PARAM_OPTIONAL },
	 { wxCMD_LINE_SWITCH, "configdir", "configdir", "Set configuration directory",
		  wxCMD_LINE_VAL_NONE, wxCMD_LINE_PARAM_OPTIONAL },
	 { wxCMD_LINE_SWITCH, "datadir", "datadir", "Set data directory",
		  wxCMD_LINE_VAL_NONE, wxCMD_LINE_PARAM_OPTIONAL },

	 { wxCMD_LINE_NONE }
};

bool SGTApp::OnInit()
{
	char error_message[1024];

	if (!wxApp::OnInit())
		return false;

	time_t t;
	struct tm *ltm;
	char datestr[256];

	//check directory and crate them if necessary.
	if (!m_useCustomParamPath) {
		getParameterDirectoryPath(&g_ParamPath);
		checkAndCreateDirectory(g_ParamPath);
	}
	if (!m_useCustomDataPath) {
		getDataDirectoryPath(&g_DataPath);
		checkAndCreateDirectory(g_DataPath);
	}

	//open logfile and output welcome message.
	std::string logFilePath;
	logFilePath.assign(g_DataPath);
	logFilePath.append(PATH_SEPARATOR);
	logFilePath.append("SimpleGazeTracker.log");
	openLogFile(logFilePath.c_str());

	std::stringstream ss;
	ss << "Welcome to SimpleGazeTracker version " << VERSION << " " << getEditionString() << std::endl;
	outputLog(ss.str().c_str());
	time(&t);
	ltm = localtime(&t);
	strftime(datestr, sizeof(datestr), "%Y, %B, %d, %A %p%I:%M:%S", ltm);
	outputLog( datestr );

	outputLog( "Searching AppDirPath directory..." );
	snprintf(error_message, sizeof(error_message), "check %s ...", g_AppDirPath.c_str());
	outputLog( error_message );

	if (FAILED(checkFile(g_AppDirPath, DEFAULT_CONFIG_FILE))) {
		//try /usr/local/lib/simplegazetracker
		g_AppDirPath.assign("/usr/local/lib/simplegazetracker");
		if (FAILED(checkFile(g_AppDirPath, DEFAULT_CONFIG_FILE))) {
			//try Debian directory (/usr/lib/simplegazetracker)
			g_AppDirPath.assign("/usr/lib/simplegazetracker");
			if (FAILED(checkFile(g_AppDirPath, DEFAULT_CONFIG_FILE))) {
				//try current directory
				g_AppDirPath.assign(getCurrentWorkingDirectory());
				if (FAILED(checkFile(g_AppDirPath, DEFAULT_CONFIG_FILE))) {
					outputLogDlg(
						"ERROR: Could not determine AppDirPath directory. "
						"Default CONFIG file was not found. Please confirm if SimpleGazeTracker is properly installed. ",
						"SimpleGazeTracker initialization failed", wxICON_ERROR);
					return false;
				}
			}
		}
	}
	snprintf(error_message, sizeof(error_message),
		"AppDirPath directory is %s\nParamPath directory is %s\nDataPath directory is %s",
		g_AppDirPath.c_str(), g_ParamPath.c_str(), g_DataPath.c_str());
	outputLog(error_message);

	//if CONFIG file is not found in g_ParamPath, copy it.
	if (!m_useCustomConfigFile) {
		if (FAILED(checkAndCopyFile(g_ParamPath, DEFAULT_CONFIG_FILE, g_AppDirPath))) {
			snprintf(error_message, sizeof(error_message),
				"\"%s\" file is not found. SimpleGazeTracker may not be properly installed.\n", DEFAULT_CONFIG_FILE);
			outputLogDlg(error_message, "SimpleGazeTracker initialization failed", wxICON_ERROR);
			return false;
		}
	}
	else {
		if (FAILED(checkFile(g_ParamPath, g_ConfigFileName.c_str()))) {
			snprintf(error_message, sizeof(error_message),
				"Error: configuration file (%s) is not found.", g_ConfigFileName.c_str());
			outputLogDlg(error_message, "SimpleGazeTracker initialization failed", wxICON_ERROR);
			return false;
		}
	}

	outputLog("initParameters ... ");
	strncpy(error_message, "", sizeof(error_message));//clear errorMessage
	if (FAILED(initParameters())) {
		snprintf(error_message, sizeof(error_message),
			"Could not initialize parameters.\nDo you want to open Config Directory and log file?");
		wxMessageDialog* dlg = new wxMessageDialog(NULL, error_message, "SimpleGazeTracker initialization failed", wxICON_ERROR | wxYES_NO);
		if (dlg->ShowModal() == wxID_YES)
		{
			if (openLocation(g_ParamPath) != 0) {
				snprintf(error_message, sizeof(error_message),
					"Failed to open %s. Please open config directory manually.", g_ParamPath.c_str());
				outputLogDlg(error_message, "SimpleGazeTracker initialization failed", wxICON_ERROR);
			}
			closeLogFile(); // Log file must be closed before opend by default viewer.
			if (openLocation(logFilePath) != 0) {
				snprintf(error_message, sizeof(error_message),
					"Failed to open %s. Please open log file manually.", logFilePath.c_str());
				outputLogDlg(error_message, "SimpleGazeTracker initialization failed", wxICON_ERROR);
			}
		}
		outputLog( "Error: Could not initialize parameters. Check configuration file." );
		return false;
	}
	outputLog("Ok");

	// now we can open main frame
	ss.str("");
	ss << "SimpleGazeTracker version " << VERSION << " " << getEditionString();
	m_pData = new SGTData(g_RecordingMode);
	SGTMainFrame* pMainFrame = new SGTMainFrame(NULL, ss.str(), wxPoint(-1,-1), wxSize(1024,768), this);
	pMainFrame->Show();
	pMainFrame->UpdateLogTextBox();
	pMainFrame->updateMenuPanel();

	//TODO output timer initialization results?
	initTimer();

	outputLog("Initializing image buffers...");
	// Initialize Buffers
	if (FAILED(initBuffers())) {
		outputLog( "Failed to initialize image buffer. Settings of camera image size and preview image size may be wrong." );
		wxMessageDialog* dlg = new wxMessageDialog(NULL, 
			"Failed to initialize image buffer. Settings of camera image size and preview image size may be wrong.\nDo you want to open Config Directory and log file?",
			"SimpleGazeTracker initialization failed", wxICON_ERROR | wxYES_NO);
		if (dlg->ShowModal() == wxID_YES)
		{
			if (openLocation(g_ParamPath) != 0) {
				snprintf(error_message, sizeof(error_message),
					"Failed to open %s. Please open config directory manually.", g_ParamPath.c_str());
				outputLogDlg(error_message, "SimpleGazeTracker initialization failed", wxICON_ERROR);
			}
			closeLogFile(); // Log file must be closed before opend by default viewer.
			if (openLocation(logFilePath) != 0) {
				snprintf(error_message, sizeof(error_message),
					"Failed to open %s. Please open log file manually.", logFilePath.c_str());
				outputLogDlg(error_message, "SimpleGazeTracker initialization failed", wxICON_ERROR);
			}
		}
		return false;
	}
	outputLog("Ok");

	outputLog("Initializing network...");
	pMainFrame->initTCPConnection();

	outputLog("Initializing camera...");
	strncpy(error_message, "", sizeof(error_message));//clear errorMessage
	if (FAILED(initCamera())) {
		snprintf(error_message, sizeof(error_message),
			"Could not initialize camera. Please check %s.\n\nDo you want to open Config Directory and log file?",
			joinPath(g_ConfigFileName, g_ParamPath).c_str());
		wxMessageDialog* dlg = new wxMessageDialog(NULL, error_message, "SimpleGazeTracker initialization failed", wxICON_ERROR | wxYES_NO);
		if (dlg->ShowModal() == wxID_YES)
		{
			if (openLocation(g_ParamPath) != 0) {
				snprintf(error_message, sizeof(error_message),
					"Failed to open %s. Please open config directory manually.", g_ParamPath.c_str());
				outputLogDlg(error_message, "SimpleGazeTracker initialization failed", wxICON_ERROR);
			}
			closeLogFile(); // Log file must be closed before opend by default viewer.
			if (openLocation(logFilePath) != 0) {
				snprintf(error_message, sizeof(error_message),
					"Failed to open %s. Please open log file manually.", logFilePath.c_str());
				outputLogDlg(error_message, "SimpleGazeTracker initialization failed", wxICON_ERROR);
			}
		}
		outputLog( "initCamera failed. Exit." );
		return false;
	}
	outputLog("Ok");

	// USB
	m_pUSBIO = new SGTusbIO();
	strncpy(error_message, "", sizeof(error_message));//clear errorMessage
	if (g_USBIOBoard.length() > 0 && g_USBIOBoard != "NONE") {
		outputLog("Initalizing USB I/O...");
		if (FAILED(m_pUSBIO->init(g_USBIOBoard, g_USBIOParamAD, g_USBIOParamDI, MAXDATA))) {
			snprintf(error_message, sizeof(error_message),
				"Could not initialize USB I/O. Please check %s.", joinPath(g_ParamPath, g_ConfigFileName).c_str());
			wxMessageDialog* dlg = new wxMessageDialog(NULL, error_message, "SimpleGazeTracker initialization failed", wxICON_ERROR | wxYES_NO);
			dlg->SetYesNoLabels("Open config directory", "Cancel");
			if (dlg->ShowModal() == wxID_YES)
			{
				if (openLocation(g_ParamPath) != 0) {
					snprintf(error_message, sizeof(error_message),
						"Failed to open %s. Please open config directory manually.", g_ParamPath.c_str());
					outputLogDlg(error_message, "SimpleGazeTracker initialization failed", wxICON_ERROR);
				}
				closeLogFile(); // Log file must be closed before opend by default viewer.
				if (openLocation(logFilePath) != 0) {
					snprintf(error_message, sizeof(error_message),
						"Failed to open %s. Please open log file manually.", logFilePath.c_str());
					outputLogDlg(error_message, "SimpleGazeTracker initialization failed", wxICON_ERROR);
				}
			}
			outputLog("initUSBIO failed. Exit.");
			return false;
		}

		//set usbIO object
		m_pData->setUSBIO(m_pUSBIO);
		outputLog("Ok");
	}
	else {
		outputLog("NO USB/IO");
	}

	outputLog("Measuring inter-frame interval...");
	measureInterFrameInterval();

	if (FAILED(pMainFrame->startMainThread()))
	{
		outputLog("Could not start main thread. exit.");
		wxExit();
	}

	outputLog("Ok");


	return true;
}

int SGTApp::OnExit()
{
	time_t t;
	struct tm *ltm;
	char error_message[1024];
	char datestr[256];

	outputLog( "Camera-specific cleanup..." );
	cleanupCamera();

	strncpy(error_message, "", sizeof(error_message));//clear errorMessage
	if (FAILED(saveParameters())) {
		snprintf(error_message, sizeof(error_message), "Failed to save parameters.");
		outputLogDlg(error_message, "SimpleGazeTracker warning", wxICON_ERROR);
	}

	//TODO release buffers, USB I/O

	outputLog( "OK." );
	time(&t);
	ltm = localtime(&t);
	strftime(datestr, sizeof(datestr), "%Y, %B, %d, %A %p%I:%M:%S", ltm);
	outputLog( datestr );
	outputLog( "Done." );
	closeLogFile();

	return wxApp::OnExit();
}


void SGTApp::OnInitCmdLine(wxCmdLineParser& parser)
{
	parser.SetDesc(g_cmdLineDesc);
	// must refuse '/' as parameter starter or cannot use "/path" style paths
	parser.SetSwitchChars("-");
}

bool SGTApp::OnCmdLineParsed(wxCmdLineParser& parser)
{
	wxString customParamPath, customDataPath, customConfigFile;
	m_useCustomParamPath = parser.Found("configdir", &customParamPath);
	m_useCustomDataPath = parser.Found("datadir", &customDataPath);
	m_useCustomConfigFile = parser.Found("config", &customConfigFile);

	g_AppDirPath.assign(argv[0]);
	getApplicationDirectoryPath(&g_AppDirPath);

	g_ConfigFileName.assign(DEFAULT_CONFIG_FILE);
	if (m_useCustomDataPath) {
		g_ParamPath = customParamPath;
	}
	if (m_useCustomParamPath) {
		g_DataPath = customDataPath;
	}
	if (m_useCustomConfigFile) {
		g_ConfigFileName = customConfigFile;
	}

	// TODO: deal with invalid command

	return true;
}



int initParameters(void)
{
	std::fstream fs;
	std::string fname;
	char buff[1024];
	char error_message[1024];
	char *p, *pp;
	int param;
	bool inCommonSection = false;
	bool inCameraSection = false;

	fname.assign(g_ParamPath);
	fname.append(PATH_SEPARATOR);
	fname.append(g_ConfigFileName.c_str());
	fs.open(fname.c_str(), std::ios::in);
	if (!fs.is_open())
	{
		snprintf(error_message, sizeof(error_message), "Failed to open  %s", fname.c_str());
		outputLog(error_message);
		return E_FAIL;
	}
	snprintf(error_message, sizeof(error_message), "Configuration file is %s.", fname.c_str());
	outputLog(error_message);

	while (fs.getline(buff, sizeof(buff)))
	{
		if (buff[0] == '#') continue; //comments

		//in Section "[SimpleGazeTrackerCommon]"
		if (buff[0] == '[') {
			if (strcmp(buff, "[SimpleGazeTrackerCommon]") == 0) {
				inCommonSection = true;
				inCameraSection = false;
			}
			else if (strcmp(buff, "[SimpleGazeTrackerCamera]") == 0)
			{
				inCommonSection = false;
				inCameraSection = true;

			}
			else
			{
				inCommonSection = false;
				inCameraSection = false;
			}
			continue;
		}

		if (!(inCommonSection || inCameraSection)) continue; //not in section

		//Check options.
		//If "=" is not included, this line is not option.
		if ((p = strchr(buff, '=')) == NULL) continue;

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
			else if (strcmp(buff, "SHOW_DETECTIONERROR_MSG") == 0) g_ShowDetectionErrorMsg = param;
			else if (strcmp(buff, "PORT_SEND") == 0) g_PortSend = param;
			else if (strcmp(buff, "PORT_RECV") == 0) g_PortRecv = param;
			else if (strcmp(buff, "DELAY_CORRECTION") == 0) g_DelayCorrection = param;
			else if (strcmp(buff, "OUTPUT_PUPILSIZE") == 0) g_OutputPupilSize = param;
			else if (strcmp(buff, "USBIO_BOARD") == 0) g_USBIOBoard = p;
			else if (strcmp(buff, "USBIO_AD") == 0) g_USBIOParamAD = p;
			else if (strcmp(buff, "USBIO_DI") == 0) g_USBIOParamDI = p;
			else if (strcmp(buff, "MORPH_TRANS") == 0) g_MorphologicalTrans = param;
			//obsolete parameters
			else if (strcmp(buff, "MAXPOINTS") == 0) {
				outputLog("Warning: MAXPINTS is obsolete in this version. Use MAX_PUPIL_WIDTH instead.");
			}
			else if (strcmp(buff, "MINPOINTS") == 0) {
				outputLog("Warning: MINPINTS is obsolete in this version. Use MIN_PUPIL_WIDTH instead.");
			}
			//unknown option
			else {
				snprintf(error_message, sizeof(error_message), "Unknown option (\"%s\")\nPlease check %s", 
					buff, joinPath(g_ParamPath, g_ConfigFileName).c_str());
				outputLog(error_message);
				//return E_FAIL;
			}
		}
		else if (inCameraSection) {
			if (FAILED(initCameraParameters(buff, p))) {
				snprintf(error_message, sizeof(error_message), "Warning: Unknown camera specific option in configuration file (%s)", buff);
				outputLog(error_message);
				// return E_FAIL;
			}
		}
	}

	if (g_CameraWidth*g_CameraHeight == 0)
	{
		snprintf(error_message, sizeof(error_message), "Value of CAMERA_WIDTH and/or CAMERA_HEIGHT is zero.\nCheck  %s", joinPath(g_ParamPath, g_ConfigFileName).c_str());
		outputLog(error_message);
		return E_FAIL;
	}

	if (g_ROIWidth == 0) g_ROIWidth = g_CameraWidth;
	if (g_ROIHeight == 0) g_ROIHeight = g_CameraHeight;

	fs.close();

	return S_OK;
}

int saveParameters(void)
{
	char error_message[1024];
	std::fstream fs;
	std::string fname(g_ParamPath);

	fname.append(PATH_SEPARATOR);
	fname.append(g_ConfigFileName);

	snprintf(error_message, sizeof(error_message), "Saving parameters to %s ...", fname.c_str());
	outputLog(error_message);

	fs.open(fname.c_str(), std::ios::out);
	if (!fs.is_open())
	{
		snprintf(error_message, sizeof(error_message), "Failed to save parameters to %s.\nThe file may be write protected or opened by another program.", fname.c_str());
		outputLog(error_message);
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
	fs << "CAMERA_WIDTH=" << g_CameraWidth << std::endl;
	fs << "CAMERA_HEIGHT=" << g_CameraHeight << std::endl;
	fs << "PREVIEW_WIDTH=" << g_PreviewWidth << std::endl;
	fs << "PREVIEW_HEIGHT=" << g_PreviewHeight << std::endl;
	if (g_ROIWidth == g_CameraWidth)
	{
		fs << "ROI_WIDTH=0" << std::endl;
	}
	else {
		fs << "ROI_WIDTH=" << g_ROIWidth << std::endl;
	}
	if (g_ROIHeight == g_CameraHeight)
	{
		fs << "ROI_HEIGHT=0" << std::endl;
	}
	else
	{
		fs << "ROI_HEIGHT=" << g_ROIHeight << std::endl;
	}
	fs << "SHOW_DETECTIONERROR_MSG=" << g_ShowDetectionErrorMsg << std::endl;
	fs << "PORT_SEND=" << g_PortSend << std::endl;
	fs << "PORT_RECV=" << g_PortRecv << std::endl;
	fs << "DELAY_CORRECTION=" << g_DelayCorrection << std::endl;
	fs << "OUTPUT_PUPILSIZE=" << g_OutputPupilSize << std::endl;
	fs << "USBIO_BOARD=" << g_USBIOBoard << std::endl;
	fs << "USBIO_AD=" << g_USBIOParamAD << std::endl;
	fs << "USBIO_DI=" << g_USBIOParamDI << std::endl;
	fs << "MORPH_TRANS=" << g_MorphologicalTrans << std::endl;

	fs << std::endl << "[SimpleGazeTrackerCamera]" << std::endl;
	saveCameraParameters(&fs);

	fs.close();

	outputLog("OK.");
	return S_OK;
}

void SGTApp::measureInterFrameInterval()
{
	double meanInterFrameInterval, stdInterFrameInterval;
	double tick[2011], ifi[2000], startTime;
	int numSamples;
	char error_message[1024];

	// Run 2000ms
	startTime = getCurrentTime();
	numSamples = 0;
	while (getCurrentTime() - startTime < 2000)
	{
		if (getCameraImage() == S_OK)
		{ //retrieve camera image and process it.
			int res;
			double detectionResults[MAX_DETECTION_RESULTS], TimeImageAcquired;

			tick[numSamples] = getCurrentTime();
			numSamples++;
			if (numSamples >= 2011) break;

			TimeImageAcquired = getCurrentTime();
			if (!m_pData->isBinocular()) {
				res = detectPupilPurkinjeMono(
					g_Threshold,
					g_PurkinjeSearchArea,
					g_PurkinjeThreshold,
					g_PurkinjeExcludeArea,
					g_MinPupilWidth,
					g_MaxPupilWidth,
					detectionResults);
				if (res != S_PUPIL_PURKINJE)
				{
					detectionResults[MONO_PUPIL_X] = detectionResults[MONO_PUPIL_Y] = res;
					detectionResults[MONO_PURKINJE_X] = detectionResults[MONO_PURKINJE_Y] = res;
				}
			}
			else
			{
				res = detectPupilPurkinjeBin(
					g_Threshold,
					g_PurkinjeSearchArea,
					g_PurkinjeThreshold,
					g_PurkinjeExcludeArea,
					g_MinPupilWidth,
					g_MaxPupilWidth,
					detectionResults);
				if (res != S_PUPIL_PURKINJE)
				{
					detectionResults[BIN_PUPIL_LX] = detectionResults[BIN_PUPIL_LY] = res;
					detectionResults[BIN_PURKINJE_LX] = detectionResults[BIN_PURKINJE_LY] = res;
					detectionResults[BIN_PUPIL_RX] = detectionResults[BIN_PUPIL_RY] = res;
					detectionResults[BIN_PURKINJE_RX] = detectionResults[BIN_PURKINJE_RY] = res;
				}
			}
		}
	}


	if (m_pData->getDataCounter() > 2011) //
	{
		numSamples = 2000;
	}
	else
	{
		numSamples -= 11;
	}

	for (int i = 0; i < numSamples; i++) {
		ifi[i] = tick[i+11] - tick[i+10]; // drop first 10 sample
	}

	meanInterFrameInterval = 0;
	for (int i = 0; i < numSamples; i++) {
		meanInterFrameInterval += ifi[i];
	}
	meanInterFrameInterval /= numSamples;

	stdInterFrameInterval = 0;
	for (int i = 0; i < numSamples; i++) {
		stdInterFrameInterval += (ifi[i] - meanInterFrameInterval)*(ifi[i] - meanInterFrameInterval);
	}
	stdInterFrameInterval /= numSamples;
	stdInterFrameInterval = sqrt(stdInterFrameInterval);

	//g_LogFS << "Average inter-frame interval (without render) = " << meanInterFrameInterval << "ms (sd: " << stdInterFrameInterval << "ms)" << std::endl;
	snprintf(error_message, sizeof(error_message), "Average: %.1fms (%.1fHz)", meanInterFrameInterval, 1000 / meanInterFrameInterval);
	outputLog(error_message);
}
