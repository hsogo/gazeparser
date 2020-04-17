#pragma once

#include "wx/wxprec.h"
#ifndef WX_PRECOMP
#include "wx/wx.h"
#endif

class SGTCameraView : public wxWindow
{
public:
	SGTCameraView(wxWindow* frame, const wxPoint& pos, const wxSize& size);

	//virtual ~SGTCameraView();
	//void CheckUpdate();

	void Draw( wxDC& dc );

	void DrawImage(int * buffer);

protected:
	wxBitmap m_pBitmap;
	bool m_bDrawing;
	bool m_bNewImage;

	int m_PreviewWidth;
	int m_PreviewHeight;

private:
	void OnPaint(wxPaintEvent& event);
	//void OnSize(wxSizeEvent& event);

};