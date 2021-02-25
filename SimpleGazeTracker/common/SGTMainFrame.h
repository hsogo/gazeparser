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
	void OnOpenConfigDialog(wxCommandEvent & event);
	void OnOpenIODialog(wxCommandEvent & event);
	void OnUpdateCameraView(wxThreadEvent& event);

	void updateParamFromTextCtrl(wxEvent &event);
	void clearMessageTextBox();
	void updateMessageTextBox(const char* message, bool newline);
	virtual ~SGTMainFrame();

	int initTCPConnection();
	SGTData* getSGTData() { return m_pData; }
	int startMainThread();

	bool getShowCalResult() { return m_bShowCalResult; }
	bool getNoRendering() { return m_bNoRendering; }
	bool getDrawing() { return m_isDrawing; }
	bool getSending() { return m_isSending; }
	int getCameraViewUpdateID() { return ID_CAMERAVIEW_UPDATE; }

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
	void updateCameraView(void);

	bool m_bShowCalResult = false;
	bool m_bNoRendering = true;
	bool m_isRecording = false;
	bool m_isCalibrating = false;
	bool m_isValidating = false;
	bool m_isDrawing = false;
	bool m_isSending = false;

	wxCriticalSection m_critsect;
	wxSemaphore m_semAllDone;

private:
	SGTApp* m_pApp;
	SGTData* m_pData;
	SGTCameraView* m_pCameraView;
	SGTMainThread* m_pMainThread;
	std::vector<wxStaticText*> m_pMenuItems;
	std::vector<wxTextCtrl*> m_pMenuTextCtrls;
	wxTextCtrl* m_MessageTextBox;
	wxPanel* m_pMenuPanel;

	int m_CurrentMenuPosition = 0;
	int m_captureNum = 0;

	bool m_TCPClientConnected = false;
	wxSocketServer *m_pServer;
	wxSocketClient *m_pClient;

	void processKeyPress(int code);
	void getCurrentMenuString(char *p, int maxlen);

	int ID_CAMERAVIEW_UPDATE;
	int ID_SERVER;
	int ID_RECV_SOCKET;
	int ID_MENU_TOGGLECALRESULT;
	int ID_MENU_NORENDERRECORDING;
	int ID_MENU_HTMLDOC;
	int ID_MENU_CAPTUREIMAGE;
	int ID_MENU_CONFIGDIALOG;
	int ID_MENU_IODIALOG;

	wxMenuBar* m_pMenuBar;
	wxMenu* m_pMenuSystem;
	wxMenu* m_pMenuTools;
	wxMenu* m_pMenuHelp;

	//std::vector<std::string> m_logVecotr;
};
