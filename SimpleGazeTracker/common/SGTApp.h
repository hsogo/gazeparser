#pragma once

#include <wx/wxprec.h>
#ifndef WX_PRECOMP
#include <wx/wx.h>
#endif
#include <wx/cmdline.h>

#include "SGTData.h"
#include "SGTusbIO.h"
#include <fstream>

class SGTData;
class SGTusbIO;

class SGTApp : public wxApp
{
public:
	SGTData* m_pData = nullptr;
	SGTusbIO* m_pUSBIO = nullptr;

	virtual bool OnInit() override;
	virtual int OnExit() override;
	virtual void OnInitCmdLine(wxCmdLineParser& parser);
	virtual bool OnCmdLineParsed(wxCmdLineParser& parser);

private:
	bool m_useCustomParamPath = false;
	bool m_useCustomDataPath = false;
	bool m_useCustomConfigFile = false;

	void measureInterFrameInterval();
};


