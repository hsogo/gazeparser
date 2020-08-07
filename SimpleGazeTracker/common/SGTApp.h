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
	SGTData* m_pData;
	SGTusbIO* m_pUSBIO;

	virtual bool OnInit() override;
	virtual int OnExit() override;
	virtual void OnInitCmdLine(wxCmdLineParser& parser);
	virtual bool OnCmdLineParsed(wxCmdLineParser& parser);

private:
	bool m_useCustomParamPath;
	bool m_useCustomDataPath;
	bool m_useCustomConfigFile;

	void measureInterFrameInterval();
};


