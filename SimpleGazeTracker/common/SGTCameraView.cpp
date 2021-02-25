#define _CRT_SECURE_NO_WARNINGS

#include "opencv2/opencv.hpp"
#include "opencv2/core/core.hpp"

#include "wx/wxprec.h"

#include "SGTCommon.h"
#include "SGTCameraView.h"


SGTCameraView::SGTCameraView(wxWindow *frame, const wxPoint& pos, const wxSize& size) :
	wxWindow(frame, -1, pos, size, wxSIMPLE_BORDER)
{
	m_PreviewWidth = size.GetWidth();
	m_PreviewHeight = size.GetHeight();

	m_bDrawing = false;
	m_bNewImage = false;

	Bind(wxEVT_PAINT, &SGTCameraView::OnPaint, this);
}

void SGTCameraView::OnPaint(wxPaintEvent& event)
{
	wxPaintDC dc(this);
	Draw(dc);
}

void SGTCameraView::Draw(wxDC& dc)
{
	// don't update Image if drawing
	if (!dc.IsOk() || m_bDrawing) {
		return;
	}

	m_bDrawing = true;
	if (m_bNewImage)
	{
		dc.DrawBitmap(*m_pBitmap, 0, 0);
		wxDELETE(m_pBitmap);
		m_bNewImage = false;
	}
	m_bDrawing = false;
}

void SGTCameraView::DrawImage()
{
	// don't update Image if drawing
	if (m_bDrawing) {
		return;
	}

	cv::Mat srcMat, dstMat;

	m_bDrawing = true;

	wxImage pWxImg = wxImage(g_PreviewWidth, g_PreviewHeight, g_pPreviewTextureBuffer, true);
	m_pBitmap = new wxBitmap(pWxImg);
	m_bNewImage = true;
	m_bDrawing = false;

	// eraseBackground must be false to suppress flicker
	Refresh(false);
	Update();
}