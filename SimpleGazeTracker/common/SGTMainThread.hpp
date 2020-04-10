#pragma once

#include "wx/wxprec.h"
#include "wx/thread.h"

#ifndef WX_PRECOMP
#include "wx/wx.h"
#endif

#include "SGTMainFrame.hpp"
#include "SGTData.hpp"
#include "SGTCameraView.hpp"

class SGTMainFrame;
class SGTData;

class SGTMainThread : public wxThread
{
public:
	SGTMainThread(SGTMainFrame* frame);
	virtual wxThread::ExitCode Entry();

	SGTMainFrame* m_pMainFrame;
	SGTData* m_pData;

};