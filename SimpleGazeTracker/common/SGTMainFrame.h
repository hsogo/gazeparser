#pragma once

#include <wx/wxprec.h>
#ifndef WX_PRECOMP
#include <wx/wx.h>
#endif

#include <wx/sckipc.h>

#include "SGTApp.h"
#include "SGTCameraView.h"
#include "SGTMainThread.h"
#include "SGTData.h"

class SGTApp;
class SGTMainThread;


class SGTMainFrame : public wxFrame
{
public:
	SGTMainFrame(wxFrame * frame, const wxString & title, const wxPoint & pos, const wxSize & size, SGTApp* app);
	void OnExit(wxCommandEvent & event);
	void OnAbout(wxCommandEvent & event);
	void OnHTMLDoc(wxCommandEvent & event);
	void OnCaptureCameraImage(wxCommandEvent & event);
	void OnToggleCalResults(wxCommandEvent & event);
	void OnRenderRecording(wxCommandEvent &event);
	void OnKeyDown(wxKeyEvent& event);
	void OnKillFocus(wxFocusEvent& event);
	void OnTEProcessEnter(wxEvent& event);
	void OnServerEvent(wxSocketEvent& event);
	void OnRecvSocketEvent(wxSocketEvent& event);

	void updateParamFromTextCtrl(wxEvent &event);
	void UpdateLogTextBox();
	virtual ~SGTMainFrame();

	int initTCPConnection();
	SGTData* getSGTData() { return m_pData; }
	int startMainThread();

	void updateCameraView(int* buffer);
	void updateMenuPanel();

	void startRecording(char* message);
	void stopRecording(char* message);
	void startMeasurement(bool ignoreCalibration);
	void stopMeasurement();
	void startCalibration(int clear);
	void endCalibration(void);
	void saveCameraImage(const char * filename);
	void drawCalResult();
	void startValidation(void);
	void endValidation(void);

	bool m_bShowCalResult = false;
	bool m_bNoRendering = false;
	bool m_isRecording = false;
	bool m_isCalibrating = false;
	bool m_isValidating = false;



private:
	SGTApp* m_pApp;
	SGTData* m_pData;
	SGTCameraView* m_pCameraView;
	SGTMainThread* m_pMainThread;
	std::vector<wxStaticText*> m_pMenuItems;
	std::vector<wxTextCtrl*> m_pMenuTextCtrls;
	wxTextCtrl* m_LogTextBox;
	wxPanel* m_pMenuPanel;

	int m_CurrentMenuPosition = 0;
	int m_captureNum = 0;

	bool m_TCPClientConnected = false;
	wxSocketServer *m_Server;
	wxSocketClient *m_Client;

	void processKeyPress(int code);
	void getCurrentMenuString(char *p, int maxlen);

	int ID_SERVER;
	int ID_RECV_SOCKET;
	int ID_MENU_TOGGLECALRESULT;
	int ID_MENU_NORENDERRECORDING;

	wxMenuBar* m_pMenuBar;
	wxMenu* m_pMenuSystem;
	wxMenu* m_pMenuHelp;

	std::vector<std::string> m_logVecotr;
};