#define _CRT_SECURE_NO_WARNINGS

#include "opencv2/opencv.hpp"
#include "opencv2/core/core.hpp"

#include "wx/wxprec.h"

#include "GazeTrackerCommon.h"
#include "SGTCameraView.hpp"


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
		dc.DrawBitmap(m_pBitmap, 0, 0);
		m_bNewImage = false;
	}
	m_bDrawing = false;
}

void SGTCameraView::DrawImage(int* buffer)
{
	// don't update Image if drawing
	if (m_bDrawing) {
		return;
	}

	cv::Mat srcMat, dstMat, scaledMat;

	m_bDrawing = true;
	srcMat = cv::Mat(g_CameraHeight, g_CameraWidth, CV_8UC4, buffer);
	cv::cvtColor(srcMat, dstMat, cv::COLOR_BGRA2RGB);
	cv::resize(dstMat, scaledMat, cv::Size(640, 480));

	wxImage pWxImg = wxImage(640, 480, scaledMat.data, true);
	m_pBitmap = wxBitmap(pWxImg);
	m_bNewImage = true;
	m_bDrawing = false;

	// eraseBackground must be false to suppress flicker
	Refresh(false);
	Update();
}