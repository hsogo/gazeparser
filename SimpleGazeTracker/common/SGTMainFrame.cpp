#pragma once
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

#include "SGTCommon.h"



SGTMainFrame::SGTMainFrame(wxFrame* frame, const wxString& title, const wxPoint& pos, const wxSize& size, SGTApp* app) :
	wxFrame(frame, -1, title, pos, size, wxSYSTEM_MENU | wxCLOSE_BOX | wxCAPTION)
{
	wxIcon icon("simplegazetracker.ico");
	SetIcon(icon);

	m_pApp = app;
	m_pData = app->m_pData;

	m_pMenuBar = new wxMenuBar;
	m_pMenuSystem = new wxMenu;
	m_pMenuHelp = new wxMenu;

	ID_SERVER = wxNewId();
	ID_RECV_SOCKET = wxNewId();
	int ID_MENU_HTMLDOC = wxNewId();
	int ID_MENU_CAPTUREIMAGE = wxNewId();
	ID_MENU_TOGGLECALRESULT = wxNewId();
	ID_MENU_NORENDERRECORDING = wxNewId();

	m_pMenuSystem->Append(ID_MENU_CAPTUREIMAGE, "Capture camera image");
	m_pMenuSystem->AppendSeparator();
	m_pMenuSystem->AppendCheckItem(ID_MENU_TOGGLECALRESULT, "Show calibration result");
	m_pMenuSystem->Enable(ID_MENU_TOGGLECALRESULT, false);
	m_pMenuSystem->AppendCheckItem(ID_MENU_NORENDERRECORDING, "Don't update preview during recording");
	m_pMenuSystem->AppendSeparator();

	m_pMenuSystem->Append(wxID_EXIT);
	m_pMenuBar->Append(m_pMenuSystem, "System");

	m_pMenuHelp->Append(ID_MENU_HTMLDOC, "Open HTML document");
	m_pMenuHelp->Append(wxID_ABOUT, "About...");
	m_pMenuBar->Append(m_pMenuHelp, "Help");

	Bind(wxEVT_COMMAND_MENU_SELECTED, &SGTMainFrame::OnAbout, this, wxID_ABOUT);
	Bind(wxEVT_COMMAND_MENU_SELECTED, &SGTMainFrame::OnExit, this, wxID_EXIT);
	Bind(wxEVT_COMMAND_MENU_SELECTED, &SGTMainFrame::OnHTMLDoc, this, ID_MENU_HTMLDOC);
	Bind(wxEVT_COMMAND_MENU_SELECTED, &SGTMainFrame::OnCaptureCameraImage, this, ID_MENU_CAPTUREIMAGE);
	Bind(wxEVT_COMMAND_MENU_SELECTED, &SGTMainFrame::OnToggleCalResults, this, ID_MENU_TOGGLECALRESULT);
	Bind(wxEVT_COMMAND_MENU_SELECTED, &SGTMainFrame::OnRenderRecording, this, ID_MENU_NORENDERRECORDING);
	Bind(wxEVT_CHAR_HOOK, &SGTMainFrame::OnKeyDown, this);

	Bind(wxEVT_SOCKET, &SGTMainFrame::OnServerEvent, this, ID_SERVER);
	Bind(wxEVT_SOCKET, &SGTMainFrame::OnRecvSocketEvent, this, ID_RECV_SOCKET);

	SetMenuBar(m_pMenuBar);

	wxPanel* pMainPanel = new wxPanel(this, wxID_ANY, wxPoint(0, 0), wxSize(640, 480), 0);

	m_pCameraView = new SGTCameraView(pMainPanel, wxPoint(0, 0), wxSize(640, 480));
	wxBoxSizer *pMainSizer = new wxBoxSizer(wxVERTICAL);
	pMainSizer->Add(m_pCameraView, 1, wxEXPAND, 0);

	m_LogTextBox = new wxTextCtrl(pMainPanel, wxID_ANY, "", wxPoint(0, 0), wxSize(640, 40), wxTE_MULTILINE | wxTE_READONLY);
	pMainSizer->Add(m_LogTextBox, 1, wxEXPAND, 0);

	pMainPanel->SetSizer(pMainSizer);
	pMainPanel->SetAutoLayout(true);


	m_pMenuPanel = new wxPanel(this, -1, wxPoint(0, 0), wxSize(200, 480+40), 0);
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

	wxBoxSizer* pTopSizer = new wxBoxSizer(wxHORIZONTAL);
	pTopSizer->Add(pMainPanel, 1, wxEXPAND, 0);
	pTopSizer->Add(m_pMenuPanel, 1, wxEXPAND, 0);

	SetSizer(pTopSizer);
	SetAutoLayout(true);

}

void SGTMainFrame::UpdateLogTextBox()
{
	std::vector<std::string>::iterator it;

	m_LogTextBox->Clear();
	for (it = m_logVecotr.begin(); it != m_logVecotr.end(); it++)
	{
		m_LogTextBox->AppendText(*it);
		m_LogTextBox->AppendText("\n");
	}
	m_LogTextBox->Refresh(false);
}

void SGTMainFrame::OnExit(wxCommandEvent& event)
{
	if (m_pMainThread != NULL && m_pMainThread->IsRunning()) {
		g_runMainThread = false;
	}

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
	path.assign(g_AppDirPath);
	path.append(PATH_SEPARATOR);
	path.append("doc");

	if (checkFile(path, "index.html") == E_FAIL) {
		const size_t last_slash_idx = g_AppDirPath.rfind(PATH_SEPARATOR);
		if (std::string::npos == last_slash_idx)
		{
			outputLogDlg("Cound not find HTML document.", "Error", wxICON_ERROR);
			return;
		}

		path = g_AppDirPath.substr(0, last_slash_idx);
		path.append(PATH_SEPARATOR);
		path.append("doc");

		if (checkFile(path, "index.html") == E_FAIL)
		{
			outputLogDlg("Cound not find HTML document.", "Error", wxICON_ERROR);
			return;
		}
	}

	path.insert(0, "file://");
	path.append(PATH_SEPARATOR);
	path.append("index.html");

	openLocation(path);

	return;
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

}

int SGTMainFrame::initTCPConnection()
{
	IPaddress addr, addrReal;
	addr.Service(g_PortRecv);

	m_Server = new wxSocketServer(addr);

	if (!m_Server->IsOk())
	{
		return E_FAIL;
	}


	if (!m_Server->GetLocal(addrReal))
	{
		return E_FAIL;
	}

	m_Server->SetEventHandler(*this, ID_SERVER);
	m_Server->SetNotify(wxSOCKET_CONNECTION_FLAG);
	m_Server->Notify(true);

	return S_OK;
}

int SGTMainFrame::startMainThread()
{
	m_pMainThread = new SGTMainThread(this);
	m_pMainThread->Create();

	m_pMainThread->SetPriority(100);
	
	if (m_pMainThread->Run() != wxTHREAD_NO_ERROR)
		return E_FAIL;

	return S_OK;
}

void SGTMainFrame::updateCameraView(int* buffer)
{
	// update only if main thread is active.
	if (g_runMainThread) {
		m_pCameraView->DrawImage(buffer);
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
		break;
	default:
		outputLog("Unexpected TCP/IP event\n");
		break;

	}

	if (m_TCPClientConnected)
	{
		outputLog("Client is already connected.");
		m_Server->Discard();
	}

	// Accept new connection if there is one in the pending
	// connections queue, else exit. We use Accept(false) for
	// non-blocking accept (although if we got here, there
	// should ALWAYS be a pending connection).
	sock = m_Server->Accept(false);

	if (sock)
	{
		if (!sock->GetPeer(client_addr))
		{
			outputLog("Can't get client IP address.");
			sock->Destroy();
			return;
		}
		else
		{
			ss << "New client connection from " << client_addr.IPAddress() << ":" << client_addr.Service() << "... accepted";
			outputLog(ss.str().c_str());
		}
	}
	else
	{
		outputLog("Error: couldn't accept a new connection");
		return;
	}

	sock->SetEventHandler(*this, ID_RECV_SOCKET);
	sock->SetNotify(wxSOCKET_INPUT_FLAG | wxSOCKET_LOST_FLAG);
	sock->Notify(true);


	outputLog("Connecting to client...");

	addr.Hostname(client_addr.Hostname());
	addr.Service(g_PortSend);
	m_Client = new wxSocketClient(TCP_NODELAY);

	m_Client->Connect(addr, true);

	if (!m_Client->IsConnected()) {
		outputLog("Error: couldn't connect to client.");
		sock->Destroy();
		return;
	}

	outputLog("Connected.");
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


void SGTMainFrame::OnRecvSocketEvent(wxSocketEvent& event)
{
	wxSocketBase *sock = event.GetSocket();

	std::stringstream ss;

	// Now we process the event

	switch (event.GetSocketEvent())
	{
	case wxSOCKET_INPUT:
		// We disable input events, so that the test doesn't trigger
		// wxSocketEvent again.
		sock->SetNotify(wxSOCKET_LOST_FLAG);

		// Which test are we going to run?
		char buff[RECV_BUFFER_SIZE];
		sock->Read(buff, RECV_BUFFER_SIZE);
		if (!sock->Error() && sock->LastCount()>0) {

			int nextp = 0;
			int received = sock->LastCount();
			while (nextp < received) {
				if (strcmp(buff + nextp, "key_Q") == 0) {
					processKeyPress('Q');

					nextp = seekNextCommand(buff, received, nextp, 1);
				}
				else if (strcmp(buff + nextp, "key_UP") == 0)
				{
					processKeyPress(WXK_UP);

					nextp = seekNextCommand(buff, received, nextp, 1);
				}
				else if (strcmp(buff + nextp, "key_DOWN") == 0)
				{
					processKeyPress(WXK_DOWN);

					nextp = seekNextCommand(buff, received, nextp, 1);
				}
				else if (strcmp(buff + nextp, "key_LEFT") == 0)
				{
					processKeyPress(WXK_LEFT);

					nextp = seekNextCommand(buff, received, nextp, 1);
				}
				else if (strcmp(buff + nextp, "key_RIGHT") == 0)
				{
					processKeyPress(WXK_RIGHT);

					nextp = seekNextCommand(buff, received, nextp, 1);
				}
				else if (strcmp(buff + nextp, "getImageData") == 0)
				{
					int index;
					for (int y = 0; y < g_ROIHeight; y++) {
						for (int x = 0; x < g_ROIWidth; x++) {
							index = g_ROIWidth * y + x;
							g_SendImageBuffer[index] = (unsigned)(g_pCameraTextureBuffer[
								g_CameraWidth*(y + (g_CameraHeight - g_ROIHeight) / 2) +
									(x + (g_CameraWidth - g_ROIWidth) / 2)] & 0x000000ff);
							if (g_SendImageBuffer[index] == 0) {
								g_SendImageBuffer[index] = 1;
							}
							else if (g_SendImageBuffer[index] < g_Threshold) {
								g_SendImageBuffer[index] = 1;
							}
						}
					}
					if (index + 1 != g_ROIWidth * g_ROIHeight)
					{
						outputLog("ERROR: Image size is not matched.");
						index = g_ROIWidth * g_ROIHeight;
					}
					g_SendImageBuffer[index + 1] = 0;
					m_Client->Write((char*)g_SendImageBuffer, g_ROIWidth*g_ROIHeight + 1);

					nextp = seekNextCommand(buff, received, nextp, 1);
				}
				else if (strcmp(buff + nextp, "startCal") == 0)
				{
					char* param = buff + nextp + 9;
					char* p;
					int x1, y1, x2, y2, clear;

					x1 = strtol(param, &p, 10);
					p++;
					y1 = strtol(p, &p, 10);
					p++;
					x2 = strtol(p, &p, 10);
					p++;
					y2 = strtol(p, &p, 10);

					nextp = seekNextCommand(buff, received, nextp, 2);

					clear = strtol(buff + nextp, &p, 10);

					m_pData->setCalibrationArea(x1, y1, x2, y2);
					startCalibration(clear);

					nextp = seekNextCommand(buff, received, nextp, 1);
				}
				else if (strcmp(buff + nextp, "getCalSample") == 0)
				{
					char* param = buff + nextp + 13;
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

					nextp = seekNextCommand(buff, received, nextp, 2);
				}
				else if (strcmp(buff + nextp, "endCal") == 0)
				{
					endCalibration();

					nextp = seekNextCommand(buff, received, nextp, 1);
				}
				else if (strcmp(buff + nextp, "startVal") == 0)
				{
					char* param = buff + nextp + 9;
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

					nextp = seekNextCommand(buff, received, nextp, 2);
				}
				else if (strcmp(buff + nextp, "getValSample") == 0)
				{
					char* param = buff + nextp + 13;
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

					nextp = seekNextCommand(buff, received, nextp, 2);
				}
				else if (strcmp(buff + nextp, "endVal") == 0)
				{
					endValidation();

					nextp = seekNextCommand(buff, received, nextp, 1);
				}
				else if (strcmp(buff + nextp, "toggleCalResult") == 0)
				{
					char* param = buff + nextp + 16;
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
						m_pMenuSystem->Check(ID_MENU_TOGGLECALRESULT, true);
						m_pMenuSystem->UpdateUI();
					}

					nextp = seekNextCommand(buff, received, nextp, 2);
				}
				else if (strcmp(buff + nextp, "saveCalValResultsDetail") == 0)
				{
					m_pData->saveCalValResultsDetail();

					nextp = seekNextCommand(buff, received, nextp, 1);
				}
				else if (strcmp(buff + nextp, "startRecording") == 0)
				{
					char* param = buff + nextp + 15;
					startRecording(param);

					nextp = seekNextCommand(buff, received, nextp, 2);
				}
				else if (strcmp(buff + nextp, "stopRecording") == 0)
				{
					char* param = buff + nextp + 14;
					stopRecording(param);

					nextp = seekNextCommand(buff, received, nextp, 2);
				}
				else if (strcmp(buff + nextp, "openDataFile") == 0)
				{
					char* param = buff + nextp + 13;
					char* p;
					int overwrite;
					char logstr[1024];

					nextp = seekNextCommand(buff, received, nextp, 2);

					overwrite = strtol(buff + nextp, &p, 10);
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

					nextp = seekNextCommand(buff, received, nextp, 1);
				}
				else if (strcmp(buff + nextp, "closeDataFile") == 0)
				{
				if (FAILED(m_pData->closeDataFile()))
					outputLog("Failed to close data file becaue file pointer is NULL.");
				else
					outputLog("Close data file.");

					nextp = seekNextCommand(buff, received, nextp, 1);
				}
				else if (strcmp(buff + nextp, "insertMessage") == 0)
				{
					char* param = buff + nextp + 14;
					m_pData->insertMessage(param);

					nextp = seekNextCommand(buff, received, nextp, 2);
				}
				else if (strcmp(buff + nextp, "getEyePosition") == 0)
				{
					char* param = buff + nextp + 15;
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
					m_Client->Write(posstr, len + 1);

					nextp = seekNextCommand(buff, received, nextp, 2);
				}
				else if (strcmp(buff + nextp, "getEyePositionList") == 0)
				{
					char* param = buff + nextp + 19;
					char* p, *dstbuf;
					int val, len, s, numGet;
					bool bGetPupil;

					double pos[7];
					char posstr[8192];
					bool newDataOnly;

					val = strtol(param, &p, 10);
					if (*p == '1') {
						bGetPupil = true;
					}
					else {
						bGetPupil = false;
					}

					s = sizeof(posstr);
					dstbuf = posstr;
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
							len = sizeof(posstr) - s;
							m_Client->Write(posstr, len);
							s = sizeof(posstr);
							dstbuf = posstr;
						}
					}

					if (numGet <= 0) { //no data.
						posstr[0] = '\0';
						m_Client->Write(posstr, 1);
					}

					m_pData->updateLastSentDataCounter();

					if (s != sizeof(posstr)) {
						len = sizeof(posstr) - s;
						posstr[len - 1] = '\0'; //replace the last camma with \0
						m_Client->Write(posstr, len);
					}

					nextp = seekNextCommand(buff, received, nextp, 3);
				}
				else if (strcmp(buff + nextp, "getWholeEyePositionList") == 0) {
					char* param = buff + nextp + 24;
					char* dstbuf;
					int len, s, numGet;
					bool bGetPupil;

					double pos[7];
					char posstr[8192];

					if (param[0] == '1') {
						bGetPupil = true;
					}
					else {
						bGetPupil = false;
					}

					s = sizeof(posstr);
					dstbuf = posstr;
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
							len = sizeof(posstr) - s;
							m_Client->Write(posstr, len);
							s = sizeof(posstr);
							dstbuf = posstr;
						}
						offset++;
					}

					if (numGet <= 0) { //no data.
						posstr[0] = '\0';
						m_Client->Write(posstr, 1);
					}

					if (s != sizeof(posstr)) {
						len = sizeof(posstr) - s;
						posstr[len - 1] = '\0'; //replace the last camma with \0
						m_Client->Write(posstr, len);
					}

					nextp = seekNextCommand(buff, received, nextp, 2);
				}
				else if (strcmp(buff + nextp, "getWholeMessageList") == 0)
				{
					char *msgp;
					size_t len;
					msgp = m_pData->getMessageBuffer();
					len = strlen(msgp);
					m_Client->Write(msgp, int(len) + 1); //send with terminator

					nextp = seekNextCommand(buff, received, nextp, 1);
				}
				else if (strcmp(buff + nextp, "getCalResults") == 0)
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

					m_Client->Write(posstr, len + 1);

					nextp = seekNextCommand(buff, received, nextp, 1);
				}
				else if (strcmp(buff + nextp, "getCalResultsDetail") == 0)
				{
					int len;
					char errorstr[8192];

					m_pData->getCalibrationResultsDetail(errorstr, sizeof(errorstr) - 1, &len);
					//'\0' is already appended at getCalibrationResultsDetail
					if (len > 0) {
						m_Client->Write(errorstr, len);
					}
					else {
						//no calibration data
						errorstr[0] = '\0';
						m_Client->Write(errorstr, 1);
					}

					nextp = seekNextCommand(buff, received, nextp, 1);
				}
				else if (strcmp(buff + nextp, "getCurrMenu") == 0)
				{
					int len;
					char tmpstr[63];
					char menustr[64];

					getCurrentMenuString(tmpstr, sizeof(tmpstr));
					len = snprintf(menustr, sizeof(menustr), "%s", tmpstr);

					m_Client->Write(menustr, len + 1);

					nextp = seekNextCommand(buff, received, nextp, 1);
				}
				else if (strcmp(buff + nextp, "insertSettings") == 0)
				{
					char* param = buff + nextp + 15;
					m_pData->insertSettings(param);

					nextp = seekNextCommand(buff, received, nextp, 2);
				}
				else if (strcmp(buff + nextp, "saveCameraImage") == 0)
				{
					char* param = buff + nextp + 16;
					saveCameraImage((const char*)param);

					nextp = seekNextCommand(buff, received, nextp, 2);
				}
				else if (strcmp(buff + nextp, "startMeasurement") == 0)
				{
					startMeasurement(false);

					nextp = seekNextCommand(buff, received, nextp, 1);
				}
				else if (strcmp(buff + nextp, "stopMeasurement") == 0)
				{
					stopMeasurement();

					nextp = seekNextCommand(buff, received, nextp, 1);
				}
				else if (strcmp(buff + nextp, "allowRendering") == 0)
				{
					m_bNoRendering = false;
					m_pMenuSystem->Check(ID_MENU_NORENDERRECORDING, false);
					m_pMenuSystem->UpdateUI();

					nextp = seekNextCommand(buff, received, nextp, 1);
				}
				else if (strcmp(buff + nextp, "inhibitRendering") == 0)
				{
					m_bNoRendering = true;
					m_pMenuSystem->Check(ID_MENU_NORENDERRECORDING, true);
					m_pMenuSystem->UpdateUI();

					nextp = seekNextCommand(buff, received, nextp, 1);
				}
				else if (strcmp(buff + nextp, "isBinocularMode") == 0)
				{
					int len;
					char str[8];

					if (g_RecordingMode == RECORDING_BINOCULAR) {
						len = snprintf(str, sizeof(str), "1");
					}
					else {
						len = snprintf(str, sizeof(str), "0");
					}
					m_Client->Write(str, len + 1);

					nextp = seekNextCommand(buff, received, nextp, 1);
				}
				else if (strcmp(buff + nextp, "getCameraImageSize") == 0)
				{
					int len;
					char str[16];

					len = snprintf(str, sizeof(str), "%d,%d", g_CameraWidth, g_CameraHeight);
					m_Client->Write(str, len + 1);

					nextp = seekNextCommand(buff, received, nextp, 1);
				}
				else if (strcmp(buff + nextp, "deleteCalData") == 0)
				{
					char* param = buff + nextp + 14;

					m_pData->deleteCalibrationDataSubset(param);
					endCalibration();

					nextp = seekNextCommand(buff, received, nextp, 2);
				}
				else
				{
					ss.str("");
					ss << "WARNING: Unknown command (" << buff + nextp << ")" << std::endl;
					outputLog(ss.str().c_str());
					nextp = seekNextCommand(buff, received, nextp, 1);
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

		outputLogDlg("Client is disconnected", "Info", wxICON_INFORMATION | wxOK);
		sock->Destroy();
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
		m_isRecording = true;
		m_bShowCalResult = false;
		m_pMenuSystem->Check(ID_MENU_TOGGLECALRESULT, false);
		//don't render camera image
		g_ShowCameraImage = false;

		/*
		strncpy(g_recordingMessage, message, sizeof(g_recordingMessage));
		//draw message on calimage
		renderRecordingMessage(g_recordingMessage, true);
		*/

		outputLog("StartRecording ");
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

		}
		else
		{
			outputLog("StopRecording");
		}

		m_isRecording = false;
		g_ShowCameraImage = true;
	}
	else
	{
		outputLog("Warning: stopRecording is called before starting");
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

		g_ShowCameraImage = true;
	}
}

void SGTMainFrame::endCalibration(void)
{
	outputLog("EndCalibration");

	m_pData->finishCalibration();

	m_isCalibrating = false;
	m_bShowCalResult = true;
	m_pMenuSystem->Enable(ID_MENU_TOGGLECALRESULT, true);
	m_pMenuSystem->UpdateUI();
	g_ShowCameraImage = true;

}


void SGTMainFrame::startValidation(void)
{
	outputLog("StartValidation");

	if (!m_pData->isBusy()) { //ready to start calibration?
		m_pData->clearCalibrationData();
		m_pData->clearData();
		m_pData->startCalibration();
		m_isValidating = true;
		m_bShowCalResult = false;
		g_ShowCameraImage = true;
	}
}

void SGTMainFrame::endValidation(void)
{
	outputLog("EndValidation");
	m_pData->setCalibrationResults();

	m_isValidating = false;
	m_bShowCalResult = true;
}


void SGTMainFrame::saveCameraImage(const char* filename)
{
	std::string str(g_DataPath);
	str.append(PATH_SEPARATOR);
	str.append(filename);
	cv::imwrite(str.c_str(), g_DstImg);

	str.insert(0, "Capture camera image as ");
	outputLog(str.c_str());
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
				cv::Point2d(cx*g_PreviewWidth / calAreaWidth, cy*g_PreviewHeight / calAreaHeight),
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
				cv::Point2d(cx*g_PreviewWidth / calAreaWidth, cy*g_PreviewHeight / calAreaHeight),
				CV_RGB(0, 0, 255));
			cv::circle(g_CalImg, cv::Point2d(xy[BIN_LX] * g_PreviewWidth / calAreaWidth, xy[BIN_LY] * g_PreviewHeight / calAreaHeight), 3, CV_RGB(0, 0, 255));
			//right eye = green
			cv::line(g_CalImg,
				cv::Point2d(xy[BIN_RX] * g_PreviewWidth / calAreaWidth, xy[BIN_RY] * g_PreviewHeight / calAreaHeight),
				cv::Point2d(cx*g_PreviewWidth / calAreaWidth, cy*g_PreviewHeight / calAreaHeight),
				CV_RGB(0, 255, 0));
			cv::circle(g_CalImg, cv::Point2d(xy[BIN_RX] * g_PreviewWidth / calAreaWidth, xy[BIN_RY] * g_PreviewHeight / calAreaHeight), 3, CV_RGB(0, 255, 0));
		}
	}


}
