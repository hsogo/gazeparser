#pragma once

#include <wx/wxprec.h>
#ifndef WX_PRECOMP
#include <wx/wx.h>
#endif
#include <wx/cmdline.h>

#include "SGTMainFrame.h"
#include "SGTData.h"
#include "SGTusbIO_UL.h"
#include <fstream>

class SGTMainFrame;

class SGTApp : public wxApp
{
public:
	SGTMainFrame* m_pMainFrame;
	SGTData* m_pData;
	SGTusbIO* m_pUSBIO;
	std::vector<std::string> m_logVecotr;

	virtual bool OnInit() override;
	virtual int OnExit() override;
	virtual void OnInitCmdLine(wxCmdLineParser& parser);
	virtual bool OnCmdLineParsed(wxCmdLineParser& parser);
	void Log(const char*);
	int Log(const wxString &message, const wxString &caption, long	style);

private:
	bool m_useCustomParamPath;
	bool m_useCustomDataPath;
	bool m_useCustomConfigFile;

	void measureInterFrameInterval();
};

wxDECLARE_APP(SGTApp);

