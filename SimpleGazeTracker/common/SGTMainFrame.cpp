#define _CRT_SECURE_NO_WARNINGS

#include "opencv2/opencv.hpp"

#include <string>
#include <sstream>

#include <wx/wxprec.h>
#ifndef WX_PRECOMP
#include <wx/wx.h>
#endif

#include "wx/socket.h"

#if wxUSE_IPV6
typedef wxIPV6address IPaddress;
#else
typedef wxIPV4address IPaddress;
#endif

#include "SGTApp.h"
#include "SGTMainFrame.h"
#include "SGTConfigDlg.h"
#include "SGTIODlg.h"

#include "SGTCommon.h"

#define RECV_BUFFER_SIZE 4096
#define TMPSEND_BUFFER_SIZE 8192

char g_RecvBuffer[RECV_BUFFER_SIZE];
char g_TmpSendBuffer[TMPSEND_BUFFER_SIZE];

SGTMainFrame::SGTMainFrame(wxFrame* frame, const wxString& title, const wxPoint& pos, const wxSize& size, SGTApp* app) :
	wxFrame(frame, -1, title, pos, size, wxSYSTEM_MENU | wxCLOSE_BOX | wxCAPTION)
{
	wxIcon icon;
	if (FAILED(checkFile(g_AppDirPath, "simplegazetracker.ico"))) {
		// for debugging
		std::string path;
		path.assign(g_AppDirPath);
		#ifdef _WIN32
		path.append("\\..\\common\\simplegazetracker.ico");
		#else
		path.append("/common/simplegazetracker.ico");
		#endif
		if (!icon.LoadFile(path.c_str(), wxBITMAP_TYPE_ICO, -1, -1)) {
			outputLogDlg(path.c_str(), "Error", wxICON_ERROR);
		}
		SetIcon(icon);
	}
	else
	{
		std::string path;
		path.assign(g_AppDirPath);
		path.append(PATH_SEPARATOR);
		path.append("simplegazetracker.ico");
		icon.LoadFile(path.c_str(), wxBITMAP_TYPE_ICO, -1, -1);
		SetIcon(icon);
	}

	m_pApp = app;
	m_pData = app->m_pData;

	m_pClient = NULL;
	m_pServer = NULL;
	m_pMainThread = NULL;

	m_pMenuBar = new wxMenuBar;
	m_pMenuSystem = new wxMenu;
	m_pMenuTools = new wxMenu;
	m_pMenuHelp = new wxMenu;

	ID_CAMERAVIEW_UPDATE = wxNewId();
	ID_SERVER = wxNewId();
	ID_RECV_SOCKET = wxNewId();
	ID_MENU_HTMLDOC = wxNewId();
	ID_MENU_CAPTUREIMAGE = wxNewId();
	ID_MENU_CONFIGDIALOG = wxNewId();
	ID_MENU_IODIALOG = wxNewId();
	ID_MENU_TOGGLECALRESULT = wxNewId();
	ID_MENU_NORENDERRECORDING = wxNewId();

	m_pMenuSystem->AppendCheckItem(ID_MENU_TOGGLECALRESULT, "Show calibration result");
	m_pMenuSystem->Enable(ID_MENU_TOGGLECALRESULT, m_bShowCalResult);
	m_pMenuSystem->AppendCheckItem(ID_MENU_NORENDERRECORDING, "Don't update preview during recording (for better performance)");
	m_pMenuSystem->Check(ID_MENU_NORENDERRECORDING, m_bNoRendering);
	m_pMenuSystem->AppendSeparator();

	m_pMenuSystem->Append(wxID_EXIT);
	m_pMenuBar->Append(m_pMenuSystem, "System");

	m_pMenuTools->Append(ID_MENU_CONFIGDIALOG, "Open config dialog");
	m_pMenuTools ->Append(ID_MENU_IODIALOG, "Open USB I/O status dialog");
	m_pMenuTools->Append(ID_MENU_CAPTUREIMAGE, "Capture camera image");
	m_pMenuBar->Append(m_pMenuTools, "Tools");

	m_pMenuHelp->Append(ID_MENU_HTMLDOC, "Open HTML document");
	m_pMenuHelp->Append(wxID_ABOUT, "About...");
	m_pMenuBar->Append(m_pMenuHelp, "Help");

	Bind(wxEVT_COMMAND_MENU_SELECTED, &SGTMainFrame::OnAbout, this, wxID_ABOUT);
	Bind(wxEVT_COMMAND_MENU_SELECTED, &SGTMainFrame::OnExit, this, wxID_EXIT);
	Bind(wxEVT_COMMAND_MENU_SELECTED, &SGTMainFrame::OnHTMLDoc, this, ID_MENU_HTMLDOC);
	Bind(wxEVT_COMMAND_MENU_SELECTED, &SGTMainFrame::OnCaptureCameraImage, this, ID_MENU_CAPTUREIMAGE);
	Bind(wxEVT_COMMAND_MENU_SELECTED, &SGTMainFrame::OnOpenConfigDialog, this, ID_MENU_CONFIGDIALOG);
	Bind(wxEVT_COMMAND_MENU_SELECTED, &SGTMainFrame::OnOpenIODialog, this, ID_MENU_IODIALOG);
	Bind(wxEVT_COMMAND_MENU_SELECTED, &SGTMainFrame::OnToggleCalResults, this, ID_MENU_TOGGLECALRESULT);
	Bind(wxEVT_COMMAND_MENU_SELECTED, &SGTMainFrame::OnRenderRecording, this, ID_MENU_NORENDERRECORDING);
	Bind(wxEVT_CHAR_HOOK, &SGTMainFrame::OnKeyDown, this);

	Bind(wxEVT_SOCKET, &SGTMainFrame::OnServerEvent, this, ID_SERVER);
	Bind(wxEVT_SOCKET, &SGTMainFrame::OnRecvSocketEvent, this, ID_RECV_SOCKET);
	Bind(wxEVT_THREAD, &SGTMainFrame::OnUpdateCameraView, this, ID_CAMERAVIEW_UPDATE);

	SetMenuBar(m_pMenuBar);

	wxPanel* pRootPanel = new wxPanel(this, wxID_ANY, wxDefaultPosition, wxDefaultSize);
	wxPanel* pMainPanel = new wxPanel(pRootPanel, wxID_ANY, wxDefaultPosition, wxSize(g_PreviewWidth, g_PreviewHeight+128), 0);

	m_pCameraView = new SGTCameraView(pMainPanel, wxDefaultPosition, wxSize(g_PreviewWidth, g_PreviewHeight));
	wxBoxSizer *pMainSizer = new wxBoxSizer(wxVERTICAL);
	pMainSizer->Add(m_pCameraView, 1, wxEXPAND, 0);

	m_MessageTextBox = new wxTextCtrl(pMainPanel, wxID_ANY, "", wxDefaultPosition, wxSize(g_PreviewWidth, 128), wxTE_MULTILINE | wxTE_READONLY);
	pMainSizer->Add(m_MessageTextBox, 1, wxEXPAND, 0);

	pMainPanel->SetSizer(pMainSizer);
	pMainPanel->SetAutoLayout(true);


	m_pMenuPanel = new wxPanel(this, wxID_ANY, wxDefaultPosition, wxDefaultSize, 0);
	wxFlexGridSizer* pMenuSizer = new wxFlexGridSizer(2);

	for (int mi = 0; mi < MENU_GENERAL_NUM; mi++)
	{
		wxStaticText* menu = new wxStaticText(m_pMenuPanel, wxID_ANY, g_MenuString[mi]);
		pMenuSizer->Add(menu, 0, wxALL, 5);
		m_pMenuItems.push_back(menu);

		wxTextCtrl* ctrl = new wxTextCtrl(m_pMenuPanel, wxID_ANY, "", wxDefaultPosition, wxDefaultSize, wxTE_RIGHT | wxTE_PROCESS_ENTER);
		ctrl->Bind(wxEVT_COMMAND_TEXT_ENTER, &SGTMainFrame::OnTEProcessEnter, this);
		ctrl->Bind(wxEVT_KILL_FOCUS, &SGTMainFrame::OnKillFocus, this);
		pMenuSizer->Add(ctrl, wxALIGN_CENTER_VERTICAL);
		m_pMenuTextCtrls.push_back(ctrl);
	}

	if (g_CustomMenuNum > 0)
	{
		for (int mi = 0; mi < g_CustomMenuNum; mi++)
		{
			wxStaticText* menu = new wxStaticText(m_pMenuPanel, wxID_ANY, g_CustomMenuString[mi]);
			pMenuSizer->Add(menu, 0, wxALL, 5);
			m_pMenuItems.push_back(menu);

			wxTextCtrl* ctrl = new wxTextCtrl(m_pMenuPanel, wxID_ANY, "", wxDefaultPosition, wxDefaultSize, wxTE_RIGHT | wxTE_PROCESS_ENTER);
			ctrl->Bind(wxEVT_COMMAND_TEXT_ENTER, &SGTMainFrame::OnTEProcessEnter, this);
			ctrl->Bind(wxEVT_KILL_FOCUS, &SGTMainFrame::OnKillFocus, this);
			pMenuSizer->Add(ctrl, wxALIGN_CENTER_VERTICAL);
			m_pMenuTextCtrls.push_back(ctrl);
		}
	}
	m_pMenuPanel->SetSizer(pMenuSizer);
	m_pMenuPanel->SetAutoLayout(true);

	wxFlexGridSizer* pRootSizer = new wxFlexGridSizer(2);
	pRootSizer->Add(pMainPanel, 1, wxEXPAND, 0);
	pRootSizer->Add(m_pMenuPanel, 1, wxEXPAND, 0);
	pRootPanel->SetSizerAndFit(pRootSizer);

	Fit();
}

void SGTMainFrame::clearMessageTextBox()
{
	m_MessageTextBox->Clear();
	m_MessageTextBox->Refresh(false);
}

void SGTMainFrame::updateMessageTextBox(const char* message, bool newline)
{
	/*std::vector<std::string>::iterator it;

	for (it = m_logVecotr.begin(); it != m_logVecotr.end(); it++)
	{
		m_MessageTextBox->AppendText(*it);
		m_MessageTextBox->AppendText("\n");
	}*/
	m_MessageTextBox->AppendText(message);
	if (newline) {
		m_MessageTextBox->AppendText("\n");
	}
	m_MessageTextBox->Refresh(false);
}

void SGTMainFrame::OnExit(wxCommandEvent& event)
{
	Close(false);
}

void SGTMainFrame::OnAbout(wxCommandEvent& event)
{
	std::stringstream ss;
	ss << "SimpleGazeTracker version " << VERSION << " " << getEditionString() << std::endl;
	ss << "    Copyright(C) 2012-  Hiroyuki Sogo." << std::endl;
	ss << "    http://gazeparser.sourceforge.net/" << std::endl;
	ss << "    https://github.com/hsogo/gazeparser" << std::endl;

	wxMessageBox(ss.str(), "About this application...", wxOK | wxICON_INFORMATION);
}

void SGTMainFrame::OnHTMLDoc(wxCommandEvent& event)
{
	std::string path;
	if (checkFile(g_DocPath, "index.html") == E_FAIL) {
		outputLogDlg("Cound not find HTML document.", "Error", wxICON_ERROR);
			return;
	}

	path.assign(g_DocPath);
	path.insert(0, "file://");
	path.append(PATH_SEPARATOR);
	path.append("index.html");

	openLocation(path);

	return;
}

void SGTMainFrame::OnOpenConfigDialog(wxCommandEvent & event)
{
	SGTConfigDlg* dlg = new SGTConfigDlg(this, -1, "Configuration", wxDefaultPosition, wxDefaultSize, wxCAPTION | wxCLOSE_BOX, "configDlg");
	if (dlg->ShowModal() == wxOK) {
		wxMessageBox("Parameters are updated.  Application will shut down.", "Info", wxOK|wxICON_INFORMATION);
		Close(false);
	}
}

void SGTMainFrame::OnOpenIODialog(wxCommandEvent & event)
{
	SGTIODlg* dlg = new SGTIODlg(this, -1, "USB I/O status", wxDefaultPosition, wxDefaultSize, wxCAPTION | wxCLOSE_BOX, "configDlg");
	dlg->setUSBIO( m_pData->getUSBIO() );
	dlg->ShowModal();
}

void SGTMainFrame::OnCaptureCameraImage(wxCommandEvent & event)
{
	time_t t;
	struct tm *ltm;
	char capfilename[64];

	time(&t);
	ltm = localtime(&t);
	snprintf(capfilename, sizeof(capfilename), "SGT_%d%02d%02d%02d%02d%02d_%08d.bmp",
		ltm->tm_year + 1900, ltm->tm_mon + 1, ltm->tm_mday, ltm->tm_hour, ltm->tm_min, ltm->tm_sec, m_captureNum);
	saveCameraImage(capfilename);
	m_captureNum++;

}

void SGTMainFrame::OnToggleCalResults(wxCommandEvent & event)
{
	if (m_pData->isCalibrated() && !m_bShowCalResult)
	{
		m_bShowCalResult = true;
		m_pMenuSystem->Check(ID_MENU_TOGGLECALRESULT, true);
	}
	else
	{
		m_bShowCalResult = false;
		m_pMenuSystem->Check(ID_MENU_TOGGLECALRESULT, false);
	}
	m_pMenuSystem->UpdateUI();
}

void SGTMainFrame::OnRenderRecording(wxCommandEvent & event)
{
	if (!m_bNoRendering) {
		m_bNoRendering = true;
		m_pMenuSystem->Check(ID_MENU_NORENDERRECORDING, true);
	}
	else {
		m_bNoRendering = false;
		m_pMenuSystem->Check(ID_MENU_NORENDERRECORDING, false);
	}

	m_pMenuSystem->UpdateUI();
}


SGTMainFrame::~SGTMainFrame()
{
	if (m_pMainThread != NULL) {
		m_pMainThread->Delete();
		//while (m_pMainThread->IsRunning()) {
		//	sleepMilliseconds(100);
		//}
		m_pMainThread->Wait();
		delete m_pMainThread;

	}

	if(m_pCameraView != NULL)
		delete m_pCameraView;

}

int SGTMainFrame::initTCPConnection()
{
	IPaddress addr, addrReal;
	addr.Service(g_PortRecv);

	m_pServer = new wxSocketServer(addr);

	if (!m_pServer->IsOk())
	{
		outputLog("ERROR: Failed to create server socket.");
		return E_FAIL;
	}


	if (!m_pServer->GetLocal(addrReal))
	{
		outputLog("ERROR: Failed to get local address of server socket.");
		return E_FAIL;
	}

	m_pServer->SetEventHandler(*this, ID_SERVER);
	m_pServer->SetNotify(wxSOCKET_CONNECTION_FLAG);
	m_pServer->Notify(true);

	return S_OK;
}

int SGTMainFrame::startMainThread()
{
	m_pMainThread = new SGTMainThread(this);
	m_pMainThread->Create();

	m_pMainThread->SetPriority(100);
	
	if (m_pMainThread->Run() != wxTHREAD_NO_ERROR)
	{
		outputLog("ERROR: Failed to start main thread.");
		return E_FAIL;
	}

	return S_OK;
}

void SGTMainFrame::OnUpdateCameraView(wxThreadEvent& event)
{
	updateCameraView();
}

void SGTMainFrame::updateCameraView()
{
	if (!m_isDrawing)
	{
		m_isDrawing = true;
		m_pCameraView->DrawImage();
		m_isDrawing = false;
	}
}

void SGTMainFrame::updateMenuPanel()
{
	wxTextCtrl* ctrl;
	//general 
	ctrl = m_pMenuTextCtrls.at(MENU_THRESH_PUPIL);
	ctrl->SetValue(std::to_string(g_Threshold));

	ctrl = m_pMenuTextCtrls.at(MENU_THRESH_PURKINJE);
	ctrl->SetValue(std::to_string(g_PurkinjeThreshold));

	ctrl = m_pMenuTextCtrls.at(MENU_MIN_PUPILWIDTH);
	ctrl->SetValue(std::to_string(g_MinPupilWidth));

	ctrl = m_pMenuTextCtrls.at(MENU_MAX_PUPILWIDTH);
	ctrl->SetValue(std::to_string(g_MaxPupilWidth));

	ctrl = m_pMenuTextCtrls.at(MENU_SEARCHAREA);
	ctrl->SetValue(std::to_string(g_PurkinjeSearchArea));

	ctrl = m_pMenuTextCtrls.at(MENU_EXCLUDEAREA);
	ctrl->SetValue(std::to_string(g_PurkinjeExcludeArea));

	ctrl = m_pMenuTextCtrls.at(MENU_MORPHTRANS);
	ctrl->SetValue(std::to_string(g_MorphologicalTrans));

	if (g_CustomMenuNum > 0)
	{
		for (int i = 0; i < g_CustomMenuNum; i++)
		{
			ctrl = m_pMenuTextCtrls.at(MENU_GENERAL_NUM+i);
			ctrl->SetValue(updateCustomMenuText(MENU_GENERAL_NUM+i));
		}
	}

	// hilight
	for (int i = 0; i < MENU_GENERAL_NUM + g_CustomMenuNum; i++)
	{
		ctrl = m_pMenuTextCtrls.at(i);
		if (i== m_CurrentMenuPosition)
			ctrl->SetBackgroundColour("yellow");
		else
			ctrl->SetBackgroundColour("white");
	}

	m_pMenuPanel->Refresh(false);
	m_pMenuPanel->Update();
}


void SGTMainFrame::processKeyPress(int code)
{
	switch (code)
	{
	case WXK_UP:
		m_CurrentMenuPosition--;
		if (m_CurrentMenuPosition < 0) {
			m_CurrentMenuPosition = MENU_GENERAL_NUM + g_CustomMenuNum - 1;
		}
		break;
	case WXK_DOWN:
		m_CurrentMenuPosition++;
		if (m_CurrentMenuPosition >= MENU_GENERAL_NUM + g_CustomMenuNum) {
			m_CurrentMenuPosition = 0;
		}
		break;

	case WXK_LEFT:
		switch (m_CurrentMenuPosition)
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
			if (g_MaxPupilWidth < 1)
				g_MaxPupilWidth = 1;
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
			customCameraMenu(MENU_LEFT_KEY, m_CurrentMenuPosition);
			break;
		}
		break;
	case WXK_RIGHT:
		switch (m_CurrentMenuPosition)
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
			if (g_MinPupilWidth < 0)
				g_MinPupilWidth = 0;
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
			customCameraMenu(MENU_RIGHT_KEY, m_CurrentMenuPosition);
			break;
		}
		break;
	}

	updateMenuPanel();
}

void SGTMainFrame::OnKeyDown(wxKeyEvent& event)
{
	std::vector<wxTextCtrl*>::iterator it;
	for (it = m_pMenuTextCtrls.begin(); it != m_pMenuTextCtrls.end(); it++) {
		if ((*it)->GetId() == event.GetId())
		{
			event.DoAllowNextEvent();
			return;
		}
	}

	processKeyPress(event.GetKeyCode());

	event.Skip();
	return;
}

void SGTMainFrame::OnKillFocus(wxFocusEvent& event)
{
	std::vector<wxTextCtrl*>::iterator it;
	for (it = m_pMenuTextCtrls.begin(); it != m_pMenuTextCtrls.end(); it++) {
		if ((*it)->GetId() == event.GetId())
		{
			updateParamFromTextCtrl(event);
		}
	}
}

void SGTMainFrame::OnTEProcessEnter(wxEvent &event) {
	std::vector<wxTextCtrl*>::iterator it;
	for (it = m_pMenuTextCtrls.begin(); it != m_pMenuTextCtrls.end(); it++) {
		if ((*it)->GetId() == event.GetId())
		{
			updateParamFromTextCtrl(event);
		}
	}
}

void SGTMainFrame::updateParamFromTextCtrl(wxEvent &event)
{
	int index = 0;
	bool found = false;

	std::vector<wxTextCtrl*>::iterator it;
	for (it = m_pMenuTextCtrls.begin(); it != m_pMenuTextCtrls.end(); it++) {
		if ((*it)->GetId() == event.GetId())
		{
			found = true;
			break;
		}
		index++;
	}

	if (!found)
		return;

	wxString val = m_pMenuTextCtrls.at(index)->GetValue();
	if (!val.IsNumber())
	{
		// if not a number, revert change
		updateMenuPanel();
	}

	char *p;

	switch (index)
	{
	case MENU_THRESH_PUPIL:
		g_Threshold = std::strtol(val, &p, 10);
		break;
	case MENU_THRESH_PURKINJE:
		g_PurkinjeThreshold = std::strtol(val, &p, 10);
		break;
	case MENU_MIN_PUPILWIDTH:
		g_MinPupilWidth = std::strtol(val, &p, 10);
		break;
	case MENU_MAX_PUPILWIDTH:
		g_MaxPupilWidth = std::strtol(val, &p, 10);
		break;
	case MENU_SEARCHAREA:
		g_PurkinjeSearchArea = std::strtol(val, &p, 10);
		break;
	case MENU_EXCLUDEAREA:
		g_PurkinjeExcludeArea = std::strtol(val, &p, 10);
		break;
	case MENU_MORPHTRANS:
		g_MorphologicalTrans = std::strtol(val, &p, 10);
		updateMorphTransKernel();
		break;
	default:
		updateCustomCameraParameterFromMenu(index, std::string(val));
		break;
	}
	event.Skip();

}


void SGTMainFrame::OnServerEvent(wxSocketEvent& event)
{
	wxSocketBase *sock;
	IPaddress addr, client_addr;
	std::stringstream ss;

	switch (event.GetSocketEvent())
	{
	case wxSOCKET_CONNECTION:
		outputLog("TCP/IP connection is requested...");
		updateMessageTextBox("TCP/IP connection is requested...", true);
		break;
	default:
		outputLog("Unexpected TCP/IP event\n");
		updateMessageTextBox("Warning: Unexpected TCP/IP event", true);
		break;

	}

	if (m_TCPClientConnected)
	{
		outputLog("Client is already connected.");
		updateMessageTextBox("Warning: Client is alerady connected", true);
		m_pServer->Discard();
	}

	// Accept new connection if there is one in the pending
	// connections queue, else exit. We use Accept(false) for
	// non-blocking accept (although if we got here, there
	// should ALWAYS be a pending connection).
	sock = m_pServer->Accept(false);

	if (sock)
	{
		if (!sock->GetPeer(client_addr))
		{
			outputLog("Can't get client IP address.");
			updateMessageTextBox("Error: Can't get client IP address", true);
			sock->Destroy();
			return;
		}
		else
		{
			ss << "New client connection from " << client_addr.IPAddress() << ":" << client_addr.Service() << "... accepted";
			outputLog(ss.str().c_str());
			updateMessageTextBox(ss.str().c_str(), true);
		}
	}
	else
	{
		outputLog("Error: couldn't accept a new connection");
		updateMessageTextBox("Error: couldn't accept a new connection", true);
		return;
	}

	sock->SetEventHandler(*this, ID_RECV_SOCKET);
	sock->SetNotify(wxSOCKET_INPUT_FLAG | wxSOCKET_LOST_FLAG);
	sock->Notify(true);


	outputLog("Connecting to client...");

	addr.Hostname(client_addr.Hostname());
	addr.Service(g_PortSend);
	m_pClient = new wxSocketClient(wxSOCKET_NOWAIT);

	m_pClient->Connect(addr, true);

	if (!m_pClient->IsConnected()) {
		outputLog("Error: couldn't connect to client.");
		updateMessageTextBox("Error: could not connect to client.", true);
		sock->Destroy();
		return;
	}

	outputLog("Connected.");
	updateMessageTextBox("Connected to client.", true);
	m_TCPClientConnected = true;

	return;
}

int seekNextCommand(char* buff, int received, int nextp, int nSkip)
{
	for (int i = 0; i < nSkip; i++)
	{
		while (buff[nextp] != 0 && nextp <= received) nextp++;
		while (buff[nextp] == 0 && nextp <= received) nextp++;
		if (nextp >= received) break;
	}

	return nextp;
}


bool g_firstvisit = false;

void SGTMainFrame::OnRecvSocketEvent(wxSocketEvent& event)
{
	wxSocketBase *sock = event.GetSocket();

	std::stringstream ss;

	// Now we process the event


	if (!g_firstvisit) {
		outputLog("OnRecvSocketEvent called");
		g_firstvisit = true;
	}
	switch (event.GetSocketEvent())
	{
	case wxSOCKET_INPUT:
		// We disable input events, so that the test doesn't trigger
		// wxSocketEvent again.
		sock->SetNotify(wxSOCKET_LOST_FLAG);

		// Which test are we going to run?
		sock->Read(g_RecvBuffer, RECV_BUFFER_SIZE);
		if (!sock->Error() && sock->LastCount()>0) {

			int nextp = 0;
			int received = sock->LastCount();
			while (nextp < received) {
				if (strcmp(g_RecvBuffer + nextp, "key_Q") == 0) {
					processKeyPress('Q');

					nextp = seekNextCommand(g_RecvBuffer, received, nextp, 1);
				}
				else if (strcmp(g_RecvBuffer + nextp, "key_UP") == 0)
				{
					processKeyPress(WXK_UP);

					nextp = seekNextCommand(g_RecvBuffer, received, nextp, 1);
				}
				else if (strcmp(g_RecvBuffer + nextp, "key_DOWN") == 0)
				{
					processKeyPress(WXK_DOWN);

					nextp = seekNextCommand(g_RecvBuffer, received, nextp, 1);
				}
				else if (strcmp(g_RecvBuffer + nextp, "key_LEFT") == 0)
				{
					processKeyPress(WXK_LEFT);

					nextp = seekNextCommand(g_RecvBuffer, received, nextp, 1);
				}
				else if (strcmp(g_RecvBuffer + nextp, "key_RIGHT") == 0)
				{
					processKeyPress(WXK_RIGHT);

					nextp = seekNextCommand(g_RecvBuffer, received, nextp, 1);
				}
				else if (strcmp(g_RecvBuffer + nextp, "getImageData") == 0)
				{
					m_isSending = true;
					m_pClient->Write((char*)g_SendImageBuffer, g_ROIWidth*g_ROIHeight + 1);
					m_isSending = false;

					nextp = seekNextCommand(g_RecvBuffer, received, nextp, 1);
				}
				else if (strcmp(g_RecvBuffer + nextp, "startCal") == 0)
				{
					char* param = g_RecvBuffer + nextp + 9;
					char* p;
					int x1, y1, x2, y2, clear;

					x1 = strtol(param, &p, 10);
					p++;
					y1 = strtol(p, &p, 10);
					p++;
					x2 = strtol(p, &p, 10);
					p++;
					y2 = strtol(p, &p, 10);

					nextp = seekNextCommand(g_RecvBuffer, received, nextp, 2);

					clear = strtol(g_RecvBuffer + nextp, &p, 10);

					m_pData->setCalibrationArea(x1, y1, x2, y2);
					startCalibration(clear);

					nextp = seekNextCommand(g_RecvBuffer, received, nextp, 1);
				}
				else if (strcmp(g_RecvBuffer + nextp, "getCalSample") == 0)
				{
					char* param = g_RecvBuffer + nextp + 13;
					char* p;
					double x, y;
					int samples;

					x = strtod(param, &p);
					p++;
					y = strtod(p, &p);
					p++;
					samples = strtol(p, &p, 10);
					if (samples <= 0) samples = 1;
					if (samples >= MAXCALSAMPLEPERPOINT) samples = MAXCALSAMPLEPERPOINT;
					m_pData->getCalSample(x, y, samples);

					nextp = seekNextCommand(g_RecvBuffer, received, nextp, 2);
				}
				else if (strcmp(g_RecvBuffer + nextp, "endCal") == 0)
				{
					endCalibration();

					nextp = seekNextCommand(g_RecvBuffer, received, nextp, 1);
				}
				else if (strcmp(g_RecvBuffer + nextp, "startVal") == 0)
				{
					char* param = g_RecvBuffer + nextp + 9;
					char* p;
					int x1, y1, x2, y2;

					x1 = strtol(param, &p, 10);
					p++;
					y1 = strtol(p, &p, 10);
					p++;
					x2 = strtol(p, &p, 10);
					p++;
					y2 = strtol(p, &p, 10);

					m_pData->setCalibrationArea(x1, y1, x2, y2);
					startValidation();

					nextp = seekNextCommand(g_RecvBuffer, received, nextp, 2);
				}
				else if (strcmp(g_RecvBuffer + nextp, "getValSample") == 0)
				{
					char* param = g_RecvBuffer + nextp + 13;
					char* p;
					double x, y;
					int samples;

					x = strtod(param, &p);
					p++;
					y = strtod(p, &p);
					p++;
					samples = strtol(p, &p, 10);
					if (samples <= 0) samples = 1;
					if (samples >= MAXCALSAMPLEPERPOINT) samples = MAXCALSAMPLEPERPOINT;
					m_pData->getCalSample(x, y, samples);

					nextp = seekNextCommand(g_RecvBuffer, received, nextp, 2);
				}
				else if (strcmp(g_RecvBuffer + nextp, "endVal") == 0)
				{
					endValidation();

					nextp = seekNextCommand(g_RecvBuffer, received, nextp, 1);
				}
				else if (strcmp(g_RecvBuffer + nextp, "toggleCalResult") == 0)
				{
					char* param = g_RecvBuffer + nextp + 16;
					char* p;
					int val;

					val = strtol(param, &p, 10);
					if (m_pData->isCalibrated() && val != 0)
					{
						m_bShowCalResult = true;
						m_pMenuSystem->Check(ID_MENU_TOGGLECALRESULT, true);
						m_pMenuSystem->UpdateUI();

					}
					else
					{
						m_bShowCalResult = false;
						m_pMenuSystem->Check(ID_MENU_TOGGLECALRESULT, false);
						m_pMenuSystem->UpdateUI();
					}

					nextp = seekNextCommand(g_RecvBuffer, received, nextp, 2);
				}
				else if (strcmp(g_RecvBuffer + nextp, "saveCalValResultsDetail") == 0)
				{
					m_pData->saveCalValResultsDetail();

					nextp = seekNextCommand(g_RecvBuffer, received, nextp, 1);
				}
				else if (strcmp(g_RecvBuffer + nextp, "startRecording") == 0)
				{
					char* param = g_RecvBuffer + nextp + 15;
					startRecording(param);

					nextp = seekNextCommand(g_RecvBuffer, received, nextp, 2);
				}
				else if (strcmp(g_RecvBuffer + nextp, "stopRecording") == 0)
				{
					char* param = g_RecvBuffer + nextp + 14;
					stopRecording(param);

					nextp = seekNextCommand(g_RecvBuffer, received, nextp, 2);
				}
				else if (strcmp(g_RecvBuffer + nextp, "openDataFile") == 0)
				{
					char* param = g_RecvBuffer + nextp + 13;
					char* p;
					int overwrite;
					char logstr[1024];

					nextp = seekNextCommand(g_RecvBuffer, received, nextp, 2);

					overwrite = strtol(g_RecvBuffer + nextp, &p, 10);
					if (FAILED(m_pData->openDataFile(param, overwrite)))
					{
						snprintf(logstr, sizeof(logstr), "Failed to open datafile: %s", param);
						outputLogDlg(logstr, "Error", wxICON_ERROR);
					}
					else
					{
						snprintf(logstr, sizeof(logstr), "Open datafile: %s", param);
						outputLog(logstr);
					}

					nextp = seekNextCommand(g_RecvBuffer, received, nextp, 1);
				}
				else if (strcmp(g_RecvBuffer + nextp, "closeDataFile") == 0)
				{
				if (FAILED(m_pData->closeDataFile()))
					outputLog("Failed to close data file becaue file pointer is NULL.");
				else
					outputLog("Close data file.");

					nextp = seekNextCommand(g_RecvBuffer, received, nextp, 1);
				}
				else if (strcmp(g_RecvBuffer + nextp, "insertMessage") == 0)
				{
					char* param = g_RecvBuffer + nextp + 14;
					m_pData->insertMessage(param);

					updateMessageTextBox(param, true);

					nextp = seekNextCommand(g_RecvBuffer, received, nextp, 2);
				}
				else if (strcmp(g_RecvBuffer + nextp, "getEyePosition") == 0)
				{
					char* param = g_RecvBuffer + nextp + 15;
					char* p;
					int nSamples;
					double pos[6];
					char posstr[256];
					int len;

					nSamples = strtol(param, &p, 10);
					if (nSamples < 1) nSamples = 1;

					m_pData->getEyePosition(pos, nSamples);

					if (g_RecordingMode == RECORDING_MONOCULAR) {
						len = snprintf(posstr, sizeof(posstr) - 1, "%.0f,%.0f,%.0f", pos[0], pos[1], pos[2]);
					}
					else {
						len = snprintf(posstr, sizeof(posstr) - 1, "%.0f,%.0f,%.0f,%.0f,%.0f,%.0f",
							pos[0], pos[1], pos[2], pos[3], pos[4], pos[5]);
					}
					m_pClient->Write(posstr, len + 1);

					nextp = seekNextCommand(g_RecvBuffer, received, nextp, 2);
				}
				else if (strcmp(g_RecvBuffer + nextp, "getEyePositionList") == 0)
				{
					char* param = g_RecvBuffer + nextp + 19;
					char* p, *dstbuf;
					int val, len, s, numGet;
					bool bGetPupil;

					double pos[7];
					bool newDataOnly;

					val = strtol(param, &p, 10);
					if (*p == '1') {
						bGetPupil = true;
					}
					else {
						bGetPupil = false;
					}

					s = sizeof(g_TmpSendBuffer);
					dstbuf = g_TmpSendBuffer;
					numGet = 0;

					if (val < 0) {
						newDataOnly = true;
						val *= -1;
					}
					else {
						newDataOnly = false;
					}

					for (int offset = 0; offset < val; offset++) {
						if (FAILED(m_pData->getPreviousEyePositionReverse(pos, offset, newDataOnly))) break;
						if (g_RecordingMode == RECORDING_MONOCULAR) {
							if (bGetPupil)
								len = snprintf(dstbuf, s, "%.1f,%.1f,%.1f,%.1f,",
									pos[0], pos[1], pos[2], pos[3]);
							else
								len = snprintf(dstbuf, s, "%.1f,%.1f,%.1f,",
									pos[0], pos[1], pos[2]);
						}
						else {
							if (bGetPupil)
								len = snprintf(dstbuf, s, "%.1f,%.1f,%.1f,%.1f,%.1f,%.1f,%.1f,",
									pos[0], pos[1], pos[2], pos[3], pos[4], pos[5], pos[6]);
							else
								len = snprintf(dstbuf, s, "%.1f,%.1f,%.1f,%.1f,%.1f,",
									pos[0], pos[1], pos[2], pos[3], pos[4]);
						}
						numGet++;
						dstbuf = dstbuf + len;
						s -= len;
						if (s <= 96) {//check overflow
							len = sizeof(g_TmpSendBuffer) - s;
							m_pClient->Write(g_TmpSendBuffer, len);
							s = sizeof(g_TmpSendBuffer);
							dstbuf = g_TmpSendBuffer;
						}
					}

					if (numGet <= 0) { //no data.
						g_TmpSendBuffer[0] = '\0';
						m_pClient->Write(g_TmpSendBuffer, 1);
					}

					m_pData->updateLastSentDataCounter();

					if (s != sizeof(g_TmpSendBuffer)) {
						len = sizeof(g_TmpSendBuffer) - s;
						g_TmpSendBuffer[len - 1] = '\0'; //replace the last camma with \0
						m_pClient->Write(g_TmpSendBuffer, len);
					}

					nextp = seekNextCommand(g_RecvBuffer, received, nextp, 3);
				}
				else if (strcmp(g_RecvBuffer + nextp, "getWholeEyePositionList") == 0) {
					char* param = g_RecvBuffer + nextp + 24;
					char* dstbuf;
					int len, s, numGet;
					bool bGetPupil;

					double pos[7];

					if (param[0] == '1') {
						bGetPupil = true;
					}
					else {
						bGetPupil = false;
					}

					s = sizeof(g_TmpSendBuffer);
					dstbuf = g_TmpSendBuffer;
					numGet = 0;

					int offset = 0;
					while (SUCCEEDED(m_pData->getPreviousEyePositionForward(pos, offset))) {
						if (g_RecordingMode == RECORDING_MONOCULAR) {
							if (bGetPupil)
								len = snprintf(dstbuf, s, "%.1f,%.1f,%.1f,%.1f,",
									pos[0], pos[1], pos[2], pos[3]);
							else
								len = snprintf(dstbuf, s, "%.1f,%.1f,%.1f,",
									pos[0], pos[1], pos[2]);
						}
						else {
							if (bGetPupil)
								len = snprintf(dstbuf, s, "%.1f,%.1f,%.1f,%.1f,%.1f,%.1f,%.1f,",
									pos[0], pos[1], pos[2], pos[3], pos[4], pos[5], pos[6]);
							else
								len = snprintf(dstbuf, s, "%.1f,%.1f,%.1f,%.1f,%.1f,",
									pos[0], pos[1], pos[2], pos[3], pos[4]);
						}
						numGet++;
						dstbuf = dstbuf + len;
						s -= len;
						if (s <= 96) {//check overflow
							len = sizeof(g_TmpSendBuffer) - s;
							m_pClient->Write(g_TmpSendBuffer, len);
							s = sizeof(g_TmpSendBuffer);
							dstbuf = g_TmpSendBuffer;
						}
						offset++;
					}

					if (numGet <= 0) { //no data.
						g_TmpSendBuffer[0] = '\0';
						m_pClient->Write(g_TmpSendBuffer, 1);
					}

					if (s != sizeof(g_TmpSendBuffer)) {
						len = sizeof(g_TmpSendBuffer) - s;
						g_TmpSendBuffer[len - 1] = '\0'; //replace the last camma with \0
						m_pClient->Write(g_TmpSendBuffer, len);
					}

					nextp = seekNextCommand(g_RecvBuffer, received, nextp, 2);
				}
				else if (strcmp(g_RecvBuffer + nextp, "getWholeMessageList") == 0)
				{
					char *msgp;
					size_t len;
					msgp = m_pData->getMessageBuffer();
					len = strlen(msgp);
					m_pClient->Write(msgp, int(len) + 1); //send with terminator

					nextp = seekNextCommand(g_RecvBuffer, received, nextp, 1);
				}
				else if (strcmp(g_RecvBuffer + nextp, "getCalResults") == 0)
				{
					int len;
					char posstr[128];
					double goodness[4], maxError[2], meanError[2];

					m_pData->getCalibrationResults(goodness, maxError, meanError);

					if (g_RecordingMode == RECORDING_MONOCULAR) {
						len = snprintf(posstr, sizeof(posstr) - 1, "%.2f,%.2f",
							meanError[MONO_1], maxError[MONO_1]);
					}
					else {
						len = snprintf(posstr, sizeof(posstr) - 1, "%.2f,%.2f,%.2f,%.2f",
							meanError[BIN_L], maxError[BIN_L], meanError[BIN_R], maxError[BIN_R]);
					}

					m_pClient->Write(posstr, len + 1);

					nextp = seekNextCommand(g_RecvBuffer, received, nextp, 1);
				}
				else if (strcmp(g_RecvBuffer + nextp, "getCalResultsDetail") == 0)
				{
					int len;
					char errorstr[8192];

					m_pData->getCalibrationResultsDetail(errorstr, sizeof(errorstr) - 1, &len);
					//'\0' is already appended at getCalibrationResultsDetail
					if (len > 0) {
						m_pClient->Write(errorstr, len);
					}
					else {
						//no calibration data
						errorstr[0] = '\0';
						m_pClient->Write(errorstr, 1);
					}

					nextp = seekNextCommand(g_RecvBuffer, received, nextp, 1);
				}
				else if (strcmp(g_RecvBuffer + nextp, "getCurrMenu") == 0)
				{
					int len;
					char tmpstr[63];
					char menustr[64];

					getCurrentMenuString(tmpstr, sizeof(tmpstr));
					len = snprintf(menustr, sizeof(menustr), "%s", tmpstr);

					m_pClient->Write(menustr, len + 1);

					nextp = seekNextCommand(g_RecvBuffer, received, nextp, 1);
				}
				else if (strcmp(g_RecvBuffer + nextp, "insertSettings") == 0)
				{
					char* param = g_RecvBuffer + nextp + 15;
					m_pData->insertSettings(param);

					nextp = seekNextCommand(g_RecvBuffer, received, nextp, 2);
				}
				else if (strcmp(g_RecvBuffer + nextp, "saveCameraImage") == 0)
				{
					char* param = g_RecvBuffer + nextp + 16;
					saveCameraImage((const char*)param);

					nextp = seekNextCommand(g_RecvBuffer, received, nextp, 2);
				}
				else if (strcmp(g_RecvBuffer + nextp, "startMeasurement") == 0)
				{
					startMeasurement(false);

					nextp = seekNextCommand(g_RecvBuffer, received, nextp, 1);
				}
				else if (strcmp(g_RecvBuffer + nextp, "stopMeasurement") == 0)
				{
					stopMeasurement();

					nextp = seekNextCommand(g_RecvBuffer, received, nextp, 1);
				}
				else if (strcmp(g_RecvBuffer + nextp, "allowRendering") == 0)
				{
					m_bNoRendering = false;
					m_pMenuSystem->Check(ID_MENU_NORENDERRECORDING, false);
					m_pMenuSystem->UpdateUI();

					nextp = seekNextCommand(g_RecvBuffer, received, nextp, 1);
				}
				else if (strcmp(g_RecvBuffer + nextp, "inhibitRendering") == 0)
				{
					m_bNoRendering = true;
					m_pMenuSystem->Check(ID_MENU_NORENDERRECORDING, true);
					m_pMenuSystem->UpdateUI();

					nextp = seekNextCommand(g_RecvBuffer, received, nextp, 1);
				}
				else if (strcmp(g_RecvBuffer + nextp, "isBinocularMode") == 0)
				{
					int len;
					char str[8];

					if (g_RecordingMode == RECORDING_BINOCULAR) {
						len = snprintf(str, sizeof(str), "1");
					}
					else {
						len = snprintf(str, sizeof(str), "0");
					}
					m_pClient->Write(str, len + 1);

					nextp = seekNextCommand(g_RecvBuffer, received, nextp, 1);
				}
				else if (strcmp(g_RecvBuffer + nextp, "getCameraImageSize") == 0)
				{
					int len;
					char str[16];

					len = snprintf(str, sizeof(str), "%d,%d", g_CameraWidth, g_CameraHeight);
					m_pClient->Write(str, len + 1);

					nextp = seekNextCommand(g_RecvBuffer, received, nextp, 1);
				}
				else if (strcmp(g_RecvBuffer + nextp, "deleteCalData") == 0)
				{
					char* param = g_RecvBuffer + nextp + 14;

					m_pData->deleteCalibrationDataSubset(param);
					endCalibration();

					nextp = seekNextCommand(g_RecvBuffer, received, nextp, 2);
				}
				else if (strcmp(g_RecvBuffer + nextp, "getCameraIFI") == 0)
				{
					int len;
					char str[256];

					len = snprintf(str, sizeof(str), "%.2f", g_MeanInterFrameInterval);
					m_pClient->Write(str, len + 1);

					nextp = seekNextCommand(g_RecvBuffer, received, nextp, 1);
				}
				else if (strcmp(g_RecvBuffer + nextp, "getBufferSizeInfo") == 0)
				{
					int len;
					char str[256];

					len = snprintf(str, sizeof(str), "%d,%d,%d", MAXDATA, MAXCALDATA, MAXCALPOINT);
					m_pClient->Write(str, len + 1);

					nextp = seekNextCommand(g_RecvBuffer, received, nextp, 1);
				}
				else
				{
					ss.str("");
					ss << "WARNING: Unknown command (" << g_RecvBuffer + nextp << ")" << std::endl;
					outputLog(ss.str().c_str());
					nextp = seekNextCommand(g_RecvBuffer, received, nextp, 1);
				}
			}
		}

		// Enable input events again.
		sock->SetNotify(wxSOCKET_LOST_FLAG | wxSOCKET_INPUT_FLAG);
		break;

	case wxSOCKET_LOST:
		// Destroy() should be used instead of delete wherever possible,
		// due to the fact that wxSocket uses 'delayed events' (see the
		// documentation for wxQueueEvent) and we don't want an event to
		// arrive to the event handler (the frame, here) after the socket
		// has been deleted. Also, we might be doing some other thing with
		// the socket at the same time; for example, we might be in the
		// middle of a test or something. Destroy() takes care of all
		// this for us.

		//outputLogDlg("Client is disconnected", "Info", wxICON_INFORMATION | wxOK);
		outputLog("Client is disconnected.");
		updateMessageTextBox("Client is disconnected.", true);
		sock->Destroy();

		// enable menu items
		m_pMenuTools->Enable(ID_MENU_CONFIGDIALOG, true);
		m_pMenuTools->Enable(ID_MENU_IODIALOG, true);
		m_pMenuTools->UpdateUI();

		break;

	default:
		break;
	}


}


void SGTMainFrame::getCurrentMenuString(char *p, int maxlen)
{
	std::string val;
	wxString label = m_pMenuItems.at(m_CurrentMenuPosition)->GetLabel();
	switch (m_CurrentMenuPosition)
	{
	case MENU_THRESH_PUPIL:
		val = std::to_string(g_Threshold);
		break;
	case MENU_THRESH_PURKINJE:
		val = std::to_string(g_PurkinjeThreshold);
		break;
	case MENU_MIN_PUPILWIDTH:
		val = std::to_string(g_MinPupilWidth);
		break;
	case MENU_MAX_PUPILWIDTH:
		val = std::to_string(g_MaxPupilWidth);
		break;
	case MENU_SEARCHAREA:
		val = std::to_string(g_PurkinjeSearchArea);
		break;
	case MENU_EXCLUDEAREA:
		val = std::to_string(g_PurkinjeExcludeArea);
		break;
	case MENU_MORPHTRANS:
		val = std::to_string(g_MorphologicalTrans);
		break;
	default:
		val = updateCustomMenuText(m_CurrentMenuPosition);
		break;
	}
	snprintf(p, maxlen - 1, "%s (%s)",
		(const char*)(label.mb_str()),
		val.c_str());
}

void SGTMainFrame::startRecording(char * message)
{
	if (m_pData->isCalibrated())
	{
		if (FAILED(m_pData->startRecording(message)))
		{
			outputLogDlg("Could not start recording because data file is not opened.", "Error", wxICON_ERROR);
			return;
		}
		m_pMenuTools->Enable(ID_MENU_CONFIGDIALOG, false);
		m_pMenuTools->Enable(ID_MENU_IODIALOG, false);
		m_pMenuTools->UpdateUI();

		m_isRecording = true;
		m_bShowCalResult = false;
		m_pMenuSystem->Check(ID_MENU_TOGGLECALRESULT, false);
		m_pMenuSystem->UpdateUI();
		//don't render camera image
		g_ShowCameraImage = false;

		/*
		strncpy(g_recordingMessage, message, sizeof(g_recordingMessage));
		//draw message on calimage
		renderRecordingMessage(g_recordingMessage, true);
		*/

		outputLog("StartRecording ");
		updateMessageTextBox("Start Recording...", true);
		return;
	}
	else
	{
		outputLogDlg("Could not start recording because calibration is not done.", "Error", wxICON_ERROR);
		return;
	}

}


void SGTMainFrame::stopRecording(char * message)
{
	if (m_isRecording)
	{
		if (FAILED(m_pData->stopRecording(message)))
		{
			outputLog("StopRecording (no file) ");
			updateMessageTextBox("Stop Recording (no file)", true);
		}
		else
		{
			outputLog("StopRecording");
			updateMessageTextBox("Stop Recording.", true);
		}

		m_isRecording = false;
		g_ShowCameraImage = true;

		m_pMenuTools->Enable(ID_MENU_CONFIGDIALOG, true);
		m_pMenuTools->Enable(ID_MENU_IODIALOG, true);
		m_pMenuTools->UpdateUI();

	}
	else
	{
		outputLog("Warning: stopRecording is called before starting");
		updateMessageTextBox("Warning: stopRecording is called before starting.", true);
	}
}



void SGTMainFrame::startMeasurement(bool ignoreCalibration = false)
{
	if (m_pData->isCalibrated() || ignoreCalibration) {
		m_pData->clearData();
		m_pData->startMeasurement();
		m_isRecording = true;
		m_bShowCalResult = false;
		m_pMenuSystem->Check(ID_MENU_TOGGLECALRESULT, false);
		m_pMenuSystem->UpdateUI();

		g_ShowCameraImage = true;

		outputLog("StartMeasurement");
	}
	else
	{
		outputLog("Warning: StartMeasurement is called before calibration");
	}
}


void SGTMainFrame::stopMeasurement(void)
{
	if (m_isRecording)
	{
		outputLog("StopMeasurement");
		m_pData->stopMeasurement();
		m_isRecording = false;
		g_ShowCameraImage = true;
	}
	else
	{
		outputLog("Waring: StopMeasurement is called before starting.");
	}
}


void SGTMainFrame::startCalibration(int clear)
{
	outputLog("StartCalibration");
	updateMessageTextBox("Start Calibration...", true);

	if (!m_pData->isBusy())
	{
		if (clear == 1) {
			m_pData->clearCalibrationData();
			m_pData->clearData();
		}
		m_pData->startCalibration();

		m_isCalibrating = true;
		m_bShowCalResult = false; //erase calibration result screen.
		m_pMenuSystem->Check(ID_MENU_TOGGLECALRESULT, false);
		m_pMenuSystem->UpdateUI();

		m_pMenuTools->Enable(ID_MENU_CONFIGDIALOG, false);
		m_pMenuTools->Enable(ID_MENU_IODIALOG, false);
		m_pMenuTools->UpdateUI();

		g_ShowCameraImage = true;
	}
}

void SGTMainFrame::endCalibration(void)
{
	outputLog("EndCalibration");
	updateMessageTextBox("Finished.", true);

	m_pData->finishCalibration();

	m_isCalibrating = false;
	drawCalResult();
	cv::cvtColor(g_CalImg, g_PreviewImg, cv::COLOR_BGRA2RGB);
	updateCameraView();

	m_bShowCalResult = true;
	m_pMenuSystem->Enable(ID_MENU_TOGGLECALRESULT, true);
	m_pMenuSystem->UpdateUI();

	m_pMenuTools->Enable(ID_MENU_CONFIGDIALOG, true);
	m_pMenuTools->Enable(ID_MENU_IODIALOG, true);
	m_pMenuTools->UpdateUI();

	g_ShowCameraImage = true;
}


void SGTMainFrame::startValidation(void)
{
	outputLog("StartValidation");
	updateMessageTextBox("Start Varidation...", true);

	if (!m_pData->isBusy()) { //ready to start calibration?
		m_pData->clearCalibrationData();
		m_pData->clearData();
		m_pData->startCalibration();
		m_isValidating = true;
		m_bShowCalResult = false;
		g_ShowCameraImage = true;

		m_pMenuSystem->Enable(ID_MENU_TOGGLECALRESULT, false);
		m_pMenuSystem->UpdateUI();

		m_pMenuTools->Enable(ID_MENU_CONFIGDIALOG, false);
		m_pMenuTools->Enable(ID_MENU_IODIALOG, false);
		m_pMenuTools->UpdateUI();
	}
}

void SGTMainFrame::endValidation(void)
{
	outputLog("EndValidation");
	updateMessageTextBox("Finished.", true);

	m_pData->setCalibrationResults();

	m_isValidating = false;
	drawCalResult();
	cv::cvtColor(g_CalImg, g_PreviewImg, cv::COLOR_BGRA2RGB);
	updateCameraView();
	m_bShowCalResult = true;

	m_pMenuSystem->Enable(ID_MENU_TOGGLECALRESULT, true);
	m_pMenuSystem->UpdateUI();

	m_pMenuTools->Enable(ID_MENU_CONFIGDIALOG, true);
	m_pMenuTools->Enable(ID_MENU_IODIALOG, true);
	m_pMenuTools->UpdateUI();
}


void SGTMainFrame::saveCameraImage(const char* filename)
{
	std::string str(g_DataPath);
	str.append(PATH_SEPARATOR);
	str.append(filename);
	cv::imwrite(str.c_str(), g_DstImg);

	str.insert(0, "Capture camera image as ");
	outputLog(str.c_str());
	updateMessageTextBox(str.c_str(), true);
}


void SGTMainFrame::drawCalResult()
{
	double xy[4], r, x, y;
	double calAreaWidth, calAreaHeight, cx, cy;
	int idx, x1, y1, x2, y2, numCalPoint, dataCounter;

	//clear image
	cv::rectangle(g_CalImg, cv::Rect(0, 0, g_PreviewWidth, g_PreviewHeight), CV_RGB(255, 255, 255), -1);
	m_pData->getCalibrationArea(&x1, &y1, &x2, &y2);
	calAreaWidth = x2 - x1;
	calAreaHeight = y2 - y1;
	numCalPoint = m_pData->getNumCalPoint();
	dataCounter = m_pData->getDataCounter();

	//draw target position
	for (idx = 0; idx < numCalPoint; idx++) {
		x = (m_pData->getCalPoint(idx)[0] - x1) * g_PreviewWidth / calAreaWidth;
		y = (m_pData->getCalPoint(idx)[1] - y1) * g_PreviewHeight / calAreaHeight;
		r = 20 * g_PreviewWidth / calAreaWidth;
		cv::circle(g_CalImg, cv::Point2d(x, y), (int)r, CV_RGB(255, 0, 0));
		cv::circle(g_CalImg, cv::Point2d(x, y), (int)r * 2, CV_RGB(255, 0, 0));
	}
	//draw gaze postion
	if (!m_pData->isBinocular()) { //monocular
		for (idx = 0; idx < dataCounter; idx++) {
			m_pData->getGazePositionMono(m_pData->getEyeData(idx), xy);
			xy[MONO_X] = xy[MONO_X] - x1;
			xy[MONO_Y] = xy[MONO_Y] - y1;
			cx = m_pData->getCalPointData(idx)[0] - x1;
			cy = m_pData->getCalPointData(idx)[1] - y1;

			cv::line(g_CalImg,
				cv::Point2d(xy[MONO_X] * g_PreviewWidth / calAreaWidth, xy[MONO_Y] * g_PreviewHeight / calAreaHeight),
				cv::Point2d(cx * g_PreviewWidth / calAreaWidth, cy * g_PreviewHeight / calAreaHeight),
				CV_RGB(0, 0, 127));
			cv::circle(g_CalImg, cv::Point2d(xy[MONO_X] * g_PreviewWidth / calAreaWidth, xy[MONO_Y] * g_PreviewHeight / calAreaHeight), 3, CV_RGB(0, 0, 127));
		}
	}
	else { //binocular
		cv::putText(g_CalImg, "Blue: left eye", cv::Point2d(8, 16), cv::FONT_HERSHEY_COMPLEX, 0.5, CV_RGB(0, 0, 192));
		cv::putText(g_CalImg, "Green: right eye", cv::Point2d(8, 32), cv::FONT_HERSHEY_COMPLEX, 0.5, CV_RGB(0, 192, 0));
		for (idx = 0; idx < dataCounter; idx++) {
			m_pData->getGazePositionBin(m_pData->getEyeData(idx), xy);
			xy[BIN_LX] = xy[BIN_LX] - x1;
			xy[BIN_LY] = xy[BIN_LY] - y1;
			xy[BIN_RX] = xy[BIN_RX] - x1;
			xy[BIN_RY] = xy[BIN_RY] - y1;

			cx = m_pData->getCalPointData(idx)[0] - x1;
			cy = m_pData->getCalPointData(idx)[1] - y1;

			//left eye = blue
			cv::line(g_CalImg,
				cv::Point2d(xy[BIN_LX] * g_PreviewWidth / calAreaWidth, xy[BIN_LY] * g_PreviewHeight / calAreaHeight),
				cv::Point2d(cx * g_PreviewWidth / calAreaWidth, cy * g_PreviewHeight / calAreaHeight),
				CV_RGB(0, 0, 255));
			cv::circle(g_CalImg, cv::Point2d(xy[BIN_LX] * g_PreviewWidth / calAreaWidth, xy[BIN_LY] * g_PreviewHeight / calAreaHeight), 3, CV_RGB(0, 0, 255));
			//right eye = green
			cv::line(g_CalImg,
				cv::Point2d(xy[BIN_RX] * g_PreviewWidth / calAreaWidth, xy[BIN_RY] * g_PreviewHeight / calAreaHeight),
				cv::Point2d(cx * g_PreviewWidth / calAreaWidth, cy * g_PreviewHeight / calAreaHeight),
				CV_RGB(0, 255, 0));
			cv::circle(g_CalImg, cv::Point2d(xy[BIN_RX] * g_PreviewWidth / calAreaWidth, xy[BIN_RY] * g_PreviewHeight / calAreaHeight), 3, CV_RGB(0, 255, 0));
		}
	}
}

