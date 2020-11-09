#pragma once

#include <wx/wxprec.h>
#ifndef WX_PRECOMP
#include <wx/wx.h>
#endif

#include "SGTusbIO.h"

class SGTIODlgRenderTimer;

class SGTIODlg : public wxDialog
{
public:
	SGTIODlg(wxWindow *parent, wxWindowID id, const wxString &title, const wxPoint &pos, const wxSize &size, long style, const wxString &name);
	void setUSBIO(SGTusbIO* io) { m_pUSBIO = io; };
	void updateValue();
private:
	SGTusbIO* m_pUSBIO;
	wxStaticText* m_pDIOStatusText;
	wxStaticText* m_pAIOStatusText[MAX_USB_AD_CHANNELS];
	SGTIODlgRenderTimer* m_pTimer;
	//void onIdle(wxIdleEvent& evt);
	void onClose(wxCloseEvent& evt);

};

class SGTIODlgRenderTimer : public wxTimer
{
	SGTIODlg* m_dlg;

public:
	SGTIODlgRenderTimer(SGTIODlg* dlg) { m_dlg = dlg; };
	void Notify() { m_dlg->updateValue(); };
	void start() { wxTimer::Start(100); }; //update at 10Hz
};