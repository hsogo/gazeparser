
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
#include "SGTConfigDlg.h"


#ifdef _WIN32
#include "resource.h"
#endif

/*
#define _CRTDBG_MAP_ALLOC
#include "stdlib.h"
#include "crtdbg.h"
#define malloc(X) _malloc_dbg(X, _NORMAL_BLOCK, __FILE__, __LINE__)
#define new ::new(_NORMAL_BLOCK, __FILE__, __LINE__)
*/

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
std::string g_DefaultConfigFileName;
std::string g_AppDirPath;
std::string g_DocPath;

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

//TCP/IP port
int g_PortRecv = PORT_RECV;
int g_PortSend = PORT_SEND;

//measure IFI
double g_MeanInterFrameInterval;
double g_StdInterFrameInterval;
double g_measureIFItick[2011], g_IFI[2000];


extern int detectPupilPurkinjeMono(int Threshold1, int PurkinjeSearchArea, int PurkinjeThreshold, int PurkinjeExclude, int MinWidth, int MaxWidth, double* results);
extern int detectPupilPurkinjeBin(int Threshold1, int PurkinjeSearchArea, int PurkinjeThreshold, int PurkinjeExclude, int MinWidth, int MaxWidth, double* results);

extern std::vector<SGTParam*> g_pGeneralParamsVector;
extern std::vector<SGTParam*> g_pImageParamsVector;
extern std::vector<SGTParam*> g_pIOParamsVector;
extern std::vector<SGTParam*> g_pCameraParamsVector;

wxIMPLEMENT_APP_NO_MAIN(SGTApp);
int __stdcall WinMain(_In_ HINSTANCE hInstance, _In_opt_ HINSTANCE hPrevInstance, _In_ wxCmdLineArgType, _In_ int nCmdShow)
{
	//_CrtSetDbgFlag(_CRTDBG_ALLOC_MEM_DF | _CRTDBG_LEAK_CHECK_DF);
	//_CrtSetBreakAlloc(2513);
	return wxEntry(hInstance, hPrevInstance, 0, nCmdShow);
}
//wxIMPLEMENT_APP(SGTApp);


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
	bool bConfigCopied = false;

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
	if (FAILED(openLogFile(logFilePath.c_str()))) {
		snprintf(error_message, sizeof(error_message),
			"ERROR: Log file (%s) can't be opened.  Make sure that you have write permission to this file.\n(Isn't this file opened by other application such as text editor?)", logFilePath.c_str());
		outputLogDlg(error_message, "Error", wxICON_ERROR);
		return false;
	}

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

	if (FAILED(checkFile(g_AppDirPath, g_DefaultConfigFileName.c_str()))) {
		//try /usr/local/lib/simplegazetracker
		g_AppDirPath.assign("/usr/local/lib/simplegazetracker");
		if (FAILED(checkFile(g_AppDirPath, g_DefaultConfigFileName.c_str()))) {
			//try Debian directory (/usr/lib/simplegazetracker)
			g_AppDirPath.assign("/usr/lib/simplegazetracker");
			if (FAILED(checkFile(g_AppDirPath, g_DefaultConfigFileName.c_str()))) {
				//try current directory
				g_AppDirPath.assign(getCurrentWorkingDirectory());
				if (FAILED(checkFile(g_AppDirPath, g_DefaultConfigFileName.c_str()))) {
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

	// set DOC directory
	g_DocPath.assign(g_AppDirPath);
	g_DocPath.append(PATH_SEPARATOR);
	g_DocPath.append("doc");

	// index.html should be in doc directory
	if (checkFile(g_DocPath, "index.html") == E_FAIL) {
		// check parent directory (for debugging)
		const size_t last_slash_idx = g_AppDirPath.rfind(PATH_SEPARATOR);
		if (std::string::npos == last_slash_idx)
		{
			outputLogDlg("Cound not find Help Document directory.", "Error", wxICON_ERROR);
			return false;
		}

		g_DocPath = g_AppDirPath.substr(0, last_slash_idx);
		g_DocPath.append(PATH_SEPARATOR);
		g_DocPath.append("doc");

		if (checkFile(g_DocPath, "index.html") == E_FAIL)
		{
			outputLogDlg("Cound not find Help Document direcotry.", "Error", wxICON_ERROR);
			return false;
		}
	}

	if (!m_useCustomConfigFile) {
		//if CONFIG file is not found in g_ParamPath, copy it.
		if (FAILED(checkFile(g_ParamPath, g_DefaultConfigFileName.c_str()))) {
			if (FAILED(checkAndCopyFile(g_ParamPath, g_DefaultConfigFileName.c_str(), g_AppDirPath))) {
				snprintf(error_message, sizeof(error_message),
					"\"%s\" is not found. SimpleGazeTracker may not be properly installed.\n", g_DefaultConfigFileName.c_str());
				outputLogDlg(error_message, "SimpleGazeTracker initialization failed", wxICON_ERROR);
				return false;
			}
			else {
				snprintf(error_message, sizeof(error_message),
					"Configuration file (%s) is not found. Default configuration file is created at %s.\n", g_DefaultConfigFileName.c_str(), g_ParamPath.c_str());
				outputLogDlg(error_message, "Info", wxICON_INFORMATION);
				bConfigCopied = true;
			}
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
		// Error dialog has already been presented at initParameters()
		return false;
	}

	// now We can use SGTConfigDlg to edit configuration file.
	if (bConfigCopied) {
		std::string path;

		if (checkFile(g_DocPath, "params.html") == E_FAIL) {
			outputLogDlg("Cound not find HTML document (doc/params.html).", "Error", wxICON_ERROR);
		}

		path.assign(g_DocPath);
		path.insert(0, "file://");
		path.append(PATH_SEPARATOR);
		path.append("params.html");

		openLocation(path);

		SGTConfigDlg* dlg = new SGTConfigDlg(NULL, -1, "Configuration", wxDefaultPosition, wxDefaultSize, wxCAPTION | wxCLOSE_BOX, "configDlg");
		if (dlg->ShowModal() == wxOK) {
			wxMessageBox("Parameters are updated.", "Info", wxOK | wxICON_INFORMATION);
		}
		else
		{
			wxMessageBox("Parameters are not updated.", "Info", wxOK | wxICON_INFORMATION);
		}
	}

	// check Preview size before creating main frame
	if (g_PreviewWidth <= 0 || g_PreviewHeight <= 0)
	{
		wxMessageDialog* dlg = new wxMessageDialog(NULL,
			"PREVIEW_WIDTH and PREVIEW_HEIGHT must be potive integer.\nDo you want to open Config Directory and log file?",
			"SimpleGazeTracker initialization failed", wxICON_ERROR | wxYES_NO);
		if (dlg->ShowModal() == wxID_YES)
		{
			closeLogFile(); // Log file must be closed before opend by default viewer.
			if (openLocation(logFilePath) != 0) {
				snprintf(error_message, sizeof(error_message),
					"Failed to open %s. Please open log file manually.", logFilePath.c_str());
				outputLogDlg(error_message, "SimpleGazeTracker initialization failed", wxICON_ERROR);
			}
			SGTConfigDlg* dlg = new SGTConfigDlg(NULL, -1, "Configuration", wxDefaultPosition, wxDefaultSize, wxCAPTION | wxCLOSE_BOX, "configDlg");
			if (dlg->ShowModal() == wxOK) {
				saveParameters();
				wxMessageBox("Parameters are updated.  Application will shut down.", "Info", wxOK | wxICON_INFORMATION);
			}
		}
	}

	// now we can open main frame
	ss.str("");
	ss << "SimpleGazeTracker version " << VERSION << " " << getEditionString();
	m_pData = new SGTData(g_RecordingMode);
	SGTMainFrame* pMainFrame = new SGTMainFrame(NULL, ss.str(), wxPoint(-1,-1), wxDefaultSize, this);
	pMainFrame->Show();
	pMainFrame->updateMessageTextBox(ss.str().c_str(), true);
	pMainFrame->updateMenuPanel();

	//TODO output timer initialization results?
	initTimer();

	outputLog("Initializing image buffers...");
	// Initialize Buffers
	if (FAILED(initBuffers())) {
		outputLog( "Failed to initialize image buffer. Settings of camera image size and preview image size may be wrong." );
		wxMessageDialog* dlg = new wxMessageDialog(pMainFrame, 
			"Failed to initialize image buffer. Settings of camera image size and preview image size may be wrong.\nDo you want to open Config editor and log file?",
			"SimpleGazeTracker initialization failed", wxICON_ERROR | wxYES_NO);
		if (dlg->ShowModal() == wxID_YES)
		{
			closeLogFile(); // Log file must be closed before opend by default viewer.
			if (openLocation(logFilePath) != 0) {
				snprintf(error_message, sizeof(error_message),
					"Failed to open %s. Please open log file manually.", logFilePath.c_str());
				outputLogDlg(error_message, "SimpleGazeTracker initialization failed", wxICON_ERROR);
			}
			SGTConfigDlg* dlg = new SGTConfigDlg(pMainFrame, -1, "Configuration", wxDefaultPosition, wxDefaultSize, wxCAPTION | wxCLOSE_BOX, "configDlg");
			if (dlg->ShowModal() == wxOK) {
				saveParameters();
				wxMessageBox("Parameters are updated.  Application will shut down.", "Info", wxOK | wxICON_INFORMATION);
			}
		}
		return false;
	}

	outputLog("Initializing network...");
	if (FAILED(pMainFrame->initTCPConnection()))
	{
		wxMessageDialog* dlg = new wxMessageDialog(pMainFrame,
			"Failed to initialize newwork. nDo you want to open Config editor and log file?",
			"SimpleGazeTracker initialization failed", wxICON_ERROR | wxYES_NO);
		if (dlg->ShowModal() == wxID_YES)
		{
			closeLogFile(); // Log file must be closed before opend by default viewer.
			if (openLocation(logFilePath) != 0) {
				snprintf(error_message, sizeof(error_message),
					"Failed to open %s. Please open log file manually.", logFilePath.c_str());
				outputLogDlg(error_message, "SimpleGazeTracker initialization failed", wxICON_ERROR);
			}
			SGTConfigDlg* dlg = new SGTConfigDlg(pMainFrame, -1, "Configuration", wxDefaultPosition, wxDefaultSize, wxCAPTION | wxCLOSE_BOX, "configDlg");
			if (dlg->ShowModal() == wxOK) {
				saveParameters();
				wxMessageBox("Parameters are updated.  Application will shut down.", "Info", wxOK | wxICON_INFORMATION);
			}
		}
		outputLog("initTCPConnection failed. Exit.");
		return false;

	}

	outputLog("Initializing camera...");
	if (FAILED(initCamera())) {
		wxMessageDialog* dlg = new wxMessageDialog(pMainFrame,
			"Failed to initialize camera. nDo you want to open Config editor and log file?",
			"SimpleGazeTracker initialization failed", wxICON_ERROR | wxYES_NO);
		if (dlg->ShowModal() == wxID_YES)
		{
			closeLogFile(); // Log file must be closed before opend by default viewer.
			if (openLocation(logFilePath) != 0) {
				snprintf(error_message, sizeof(error_message),
					"Failed to open %s. Please open log file manually.", logFilePath.c_str());
				outputLogDlg(error_message, "SimpleGazeTracker initialization failed", wxICON_ERROR);
			}
			SGTConfigDlg* dlg = new SGTConfigDlg(pMainFrame, -1, "Configuration", wxDefaultPosition, wxDefaultSize, wxCAPTION | wxCLOSE_BOX, "configDlg");
			if (dlg->ShowModal() == wxOK) {
				saveParameters();
				wxMessageBox("Parameters are updated.  Application will shut down.", "Info", wxOK | wxICON_INFORMATION);
			}
		}
		outputLog( "initCamera failed. Exit." );
		return false;
	}

	// USB
	m_pUSBIO = new SGTusbIO();
	if (g_USBIOBoard.length() > 0 && g_USBIOBoard != "NONE") {
		outputLog("Initalizing USB I/O...");
		if (FAILED(m_pUSBIO->init(g_USBIOBoard, g_USBIOParamAD, g_USBIOParamDI, MAXDATA))) {
			wxMessageDialog* dlg = new wxMessageDialog(pMainFrame,
				"Failed to initialize USB I/O. nDo you want to open Config editor and log file?",
				"SimpleGazeTracker initialization failed", wxICON_ERROR | wxYES_NO);
			if (dlg->ShowModal() == wxID_YES)
			{
				closeLogFile(); // Log file must be closed before opend by default viewer.
				if (openLocation(logFilePath) != 0) {
					snprintf(error_message, sizeof(error_message),
						"Failed to open %s. Please open log file manually.", logFilePath.c_str());
					outputLogDlg(error_message, "SimpleGazeTracker initialization failed", wxICON_ERROR);
				}
				SGTConfigDlg* dlg = new SGTConfigDlg(pMainFrame, -1, "Configuration", wxDefaultPosition, wxDefaultSize, wxCAPTION | wxCLOSE_BOX, "configDlg");
				if (dlg->ShowModal() == wxOK) {
					saveParameters();
					wxMessageBox("Parameters are updated.  Application will shut down.", "Info", wxOK | wxICON_INFORMATION);
				}
			}
			outputLog("initUSBIO failed. Exit.");
			return false;
		}

		//set usbIO object
		m_pData->setUSBIO(m_pUSBIO);
	}
	else {
		outputLog("NO USB/IO");
	}
	
	outputLog("Measuring inter-frame interval...");
	measureInterFrameInterval();
	snprintf(error_message, sizeof(error_message), "Average inter-frame interval (without window rendering): %.1fms (%.1fHz)", g_MeanInterFrameInterval, 1000 / g_MeanInterFrameInterval);
	pMainFrame->updateMessageTextBox(error_message, true);
	outputLog(error_message);
	

	if (FAILED(pMainFrame->startMainThread()))
	{
		outputLog("Could not start main thread. exit.");
		wxExit();
	}

	outputLog("Application is successfully initialized.");


	return true;
}

int SGTApp::OnExit()
{
	time_t t;
	struct tm *ltm;
	char error_message[1024];
	char datestr[256];

	if (FAILED(saveParameters())) {
		snprintf(error_message, sizeof(error_message), "Failed to save parameters.");
		outputLogDlg(error_message, "SimpleGazeTracker warning", wxICON_ERROR);
	}

	outputLog( "Camera-specific cleanup..." );
	cleanupCamera();
	outputLog("OK.");

	releaseBuffers();

	//release objects
	wxDELETE( m_pUSBIO );
	wxDELETE( m_pData );

	std::vector<SGTParam*>::iterator it;
	for (it = g_pGeneralParamsVector.begin(); it != g_pGeneralParamsVector.end(); it++) delete(*it);
	for (it = g_pImageParamsVector.begin(); it != g_pImageParamsVector.end(); it++) delete(*it);
	for (it = g_pIOParamsVector.begin(); it != g_pIOParamsVector.end(); it++) delete(*it);
	for (it = g_pCameraParamsVector.begin(); it != g_pCameraParamsVector.end(); it++) delete(*it);
	std::vector<SGTParam*>().swap(g_pGeneralParamsVector);
	std::vector<SGTParam*>().swap(g_pImageParamsVector);
	std::vector<SGTParam*>().swap(g_pIOParamsVector);
	std::vector<SGTParam*>().swap(g_pCameraParamsVector);

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

	g_DefaultConfigFileName.append(getDefaultConfigString());

	g_ConfigFileName.assign(g_DefaultConfigFileName);
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
	char *p;
	bool inCommonSection = false;
	bool inCameraSection = false;

	fname.assign(g_ParamPath);
	fname.append(PATH_SEPARATOR);
	fname.append(g_ConfigFileName.c_str());
	fs.open(fname.c_str(), std::ios::in);
	if (!fs.is_open())
	{
		snprintf(error_message, sizeof(error_message), "Failed to open configuration file (%s).", fname.c_str());
		outputLogDlg(error_message, "SimpleGazeTracker initialization failed" ,wxICON_ERROR);
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
			//General
			if (strcmp(buff, "THRESHOLD") == 0) g_pGeneralParamsVector.push_back(new SGTParamInt("THRESHOLD", &g_Threshold, p,
				"Threshold for pupil detection.\n(Value: positive integer)"));
			else if (strcmp(buff, "MAX_PUPIL_WIDTH") == 0) g_pGeneralParamsVector.push_back(new SGTParamInt("MAX_PUPIL_WIDTH", &g_MaxPupilWidth, p,
				"Max radius of pupil in pixel.\n(Type: positive integer)"));
			else if (strcmp(buff, "MIN_PUPIL_WIDTH") == 0) g_pGeneralParamsVector.push_back(new SGTParamInt("MIN_PUPIL_WIDTH", &g_MinPupilWidth, p,
				"Min radius of pupil in pixel.\n(Value: positive integer)"));
			else if (strcmp(buff, "PURKINJE_THRESHOLD") == 0) g_pGeneralParamsVector.push_back(new SGTParamInt("PURKINJE_THRESHOLD", &g_PurkinjeThreshold, p,
				"Threshold for Purkinje image detection,\n(Value: positive integer)"));
			else if (strcmp(buff, "PURKINJE_SEARCHAREA") == 0) g_pGeneralParamsVector.push_back(new SGTParamInt("PURKINJE_SEARCHAREA", &g_PurkinjeSearchArea, p,
				"Size of search area for Purkinje image in pixel.\n(Value: positive integer)"));
			else if (strcmp(buff, "PURKINJE_EXCLUDEAREA") == 0) g_pGeneralParamsVector.push_back(new SGTParamInt("PURKINJE_EXCLUDEAREA", &g_PurkinjeExcludeArea, p,
				"Radius of exclude area for pupil fitting.\n(Value: positive integer)"));
			else if (strcmp(buff, "BINOCULAR") == 0) g_pGeneralParamsVector.push_back(new SGTParamInt("BINOCULAR", &g_RecordingMode, p,
				"Binocular mode.\n(Value: 0 for No / 1 for Yes)"));
			else if (strcmp(buff, "SHOW_DETECTIONERROR_MSG") == 0) g_pGeneralParamsVector.push_back(new SGTParamInt("SHOW_DETECTIONERROR_MSG", &g_ShowDetectionErrorMsg, p,
				"Show detection error message on preview pane.\n(Value: 0 for hide / 1 for show)"));
			else if (strcmp(buff, "MORPH_TRANS") == 0) g_pGeneralParamsVector.push_back(new SGTParamInt("MORPH_TRANS", &g_MorphologicalTrans, p,
				"Adjust effect of morphological transformation.\n(Value: positive integer for closing / negative integer for opening)"));
			//Image
			else if (strcmp(buff, "CAMERA_WIDTH") == 0) g_pImageParamsVector.push_back(new SGTParamInt("CAMERA_WIDTH", &g_CameraWidth, p, 
				"Width of camera image in pixel.\n(Value: positive integer)"));
			else if (strcmp(buff, "CAMERA_HEIGHT") == 0) g_pImageParamsVector.push_back(new SGTParamInt("CAMERA_HEIGHT", &g_CameraHeight, p,
				"Height of camera image in pixel.\n(Value: positive integer)"));
			else if (strcmp(buff, "PREVIEW_WIDTH") == 0) g_pImageParamsVector.push_back(new SGTParamInt("PREVIEW_WIDTH", &g_PreviewWidth, p,
				"Width of preview pane in pixel.\n(Value: positive integer)"));
			else if (strcmp(buff, "PREVIEW_HEIGHT") == 0) g_pImageParamsVector.push_back(new SGTParamInt("PREVIEW_HEIGHT", &g_PreviewHeight, p,
				"Height of preview pane in pixel.\n(Value: positive integer)"));
			else if (strcmp(buff, "CROP_WIDTH") == 0) g_pImageParamsVector.push_back(new SGTParamInt("CROP_WIDTH", &g_ROIWidth, p,
				"Width of region of interest in pixel.\n(Value: positive integer)"));
			else if (strcmp(buff, "CROP_HEIGHT") == 0) g_pImageParamsVector.push_back(new SGTParamInt("CROP_HEIGHT", &g_ROIHeight, p,
				"Height of region of interest in pixel.\n(Value: positive integer)"));
			//IO
			else if (strcmp(buff, "OUTPUT_PUPILSIZE") == 0) g_pIOParamsVector.push_back(new SGTParamInt("OUTPUT_PUPILSIZE", &g_OutputPupilSize, p,
				"Record pupil size.\n(Value: 0 for No / 1 for Yes)"));
			else if (strcmp(buff, "PORT_SEND") == 0) g_pIOParamsVector.push_back(new SGTParamInt("PORT_SEND", &g_PortSend, p,
				"TCP/IP port for sending data.\n(Value: positive integer)"));
			else if (strcmp(buff, "PORT_RECV") == 0) g_pIOParamsVector.push_back(new SGTParamInt("PORT_RECV", &g_PortRecv, p,
				"TCP/IP port for receiving data.\n(Value: positive integer)"));
			else if (strcmp(buff, "DELAY_CORRECTION") == 0) g_pIOParamsVector.push_back(new SGTParamInt("DELAY_CORRECTION", &g_DelayCorrection, p,
				"Delay correction in milliseconds.\n(Value: integer)"));
			else if (strcmp(buff, "USBIO_BOARD") == 0) g_pIOParamsVector.push_back(new SGTParamString("USBIO_BOARD", &g_USBIOBoard, p,
				"Name of USB I/O board. Leave this empty if USB I/O board is not available.\n(Value: string)"));
			else if (strcmp(buff, "USBIO_AD") == 0) g_pIOParamsVector.push_back(new SGTParamString("USBIO_AD", &g_USBIOParamAD, p,
				"Set channel and range of analog input (e.g. 0;BIP5V;1;UNI10V).\n(Value: string)"));
			else if (strcmp(buff, "USBIO_DI") == 0) g_pIOParamsVector.push_back(new SGTParamString("USBIO_DI", &g_USBIOParamDI, p,
				"Set port of digital input.\n(Value: string)"));
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

	// Not use SGTParam list to keep order of items in config file.
	fs << "#If you want to recover original settings, delete this file and start eye tracker program." << std::endl;
	fs << "[SimpleGazeTrackerCommon]" << std::endl;
	// general
	fs << "THRESHOLD=" << g_Threshold << std::endl;
	fs << "MAX_PUPIL_WIDTH=" << g_MaxPupilWidth << std::endl;
	fs << "MIN_PUPIL_WIDTH=" << g_MinPupilWidth << std::endl;
	fs << "PURKINJE_THRESHOLD=" << g_PurkinjeThreshold << std::endl;
	fs << "PURKINJE_SEARCHAREA=" << g_PurkinjeSearchArea << std::endl;
	fs << "PURKINJE_EXCLUDEAREA=" << g_PurkinjeExcludeArea << std::endl;
	fs << "BINOCULAR=" << g_RecordingMode << std::endl;
	fs << "SHOW_DETECTIONERROR_MSG=" << g_ShowDetectionErrorMsg << std::endl;
	fs << "MORPH_TRANS=" << g_MorphologicalTrans << std::endl;
	// image
	fs << "CAMERA_WIDTH=" << g_CameraWidth << std::endl;
	fs << "CAMERA_HEIGHT=" << g_CameraHeight << std::endl;
	fs << "PREVIEW_WIDTH=" << g_PreviewWidth << std::endl;
	fs << "PREVIEW_HEIGHT=" << g_PreviewHeight << std::endl;
	fs << "CROP_WIDTH=" << g_ROIWidth << std::endl;
	fs << "CROP_HEIGHT=" << g_ROIHeight << std::endl;
	// io
	fs << "PORT_SEND=" << g_PortSend << std::endl;
	fs << "PORT_RECV=" << g_PortRecv << std::endl;
	fs << "DELAY_CORRECTION=" << g_DelayCorrection << std::endl;
	fs << "OUTPUT_PUPILSIZE=" << g_OutputPupilSize << std::endl;
	fs << "USBIO_BOARD=" << g_USBIOBoard << std::endl;
	fs << "USBIO_AD=" << g_USBIOParamAD << std::endl;
	fs << "USBIO_DI=" << g_USBIOParamDI << std::endl;

	fs << std::endl << "[SimpleGazeTrackerCamera]" << std::endl;
	saveCameraParameters(&fs);

	fs.close();

	outputLog("OK.");
	return S_OK;
}



void SGTApp::measureInterFrameInterval()
{
	double startTime;
	int numSamples;

	// Run 2000ms
	startTime = getCurrentTime();
	numSamples = 0;
	while (getCurrentTime() - startTime < 2000)
	{
		if (getCameraImage() == S_OK)
		{ //retrieve camera image and process it.
			int res;
			double detectionResults[MAX_DETECTION_RESULTS], TimeImageAcquired;

			g_measureIFItick[numSamples] = getCurrentTime();
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
		g_IFI[i] = g_measureIFItick[i+11] - g_measureIFItick[i+10]; // drop first 10 sample
	}

	g_MeanInterFrameInterval = 0;
	for (int i = 0; i < numSamples; i++) {
		g_MeanInterFrameInterval += g_IFI[i];
	}
	g_MeanInterFrameInterval /= numSamples;

	g_StdInterFrameInterval = 0;
	for (int i = 0; i < numSamples; i++) {
		g_StdInterFrameInterval += (g_IFI[i] - g_MeanInterFrameInterval)*(g_IFI[i] - g_MeanInterFrameInterval);
	}
	g_StdInterFrameInterval /= numSamples;
	g_StdInterFrameInterval = sqrt(g_StdInterFrameInterval);
}
