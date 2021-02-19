#include "wx/wxprec.h"
#include "wx/thread.h"

#ifndef WX_PRECOMP
#include "wx/wx.h"
#endif

#include "SGTCommon.h"

#include "SGTMainThread.h"
#include "SGTMainFrame.h"
#include "SGTCameraView.h"
#include "SGTData.h"


SGTMainThread::SGTMainThread(SGTMainFrame* frame) : wxThread(wxTHREAD_JOINABLE)
{
	m_pMainFrame = frame;
	m_pData = frame->getSGTData();
}

wxThread::ExitCode SGTMainThread::Entry()
{
	while (true)
	{
		if (wxThread::TestDestroy())
			break;

		if (m_pMainFrame->getShowCalResult())
		{
			if (!m_pMainFrame->getDrawing())
			{
				m_pMainFrame->drawCalResult();
				memcpy(g_pPreviewTextureBuffer, g_pCalResultTextureBuffer, g_PreviewWidth * g_PreviewHeight * sizeof(int));
				wxThreadEvent ev(wxEVT_THREAD, m_pMainFrame->getCameraViewUpdateID());
				ev.SetInt(1);
				wxQueueEvent(m_pMainFrame, ev.Clone());
			}
		}
		else if (getCameraImage() == S_OK)
		{ //retrieve camera image and process it.
			int res;
			double detectionResults[MAX_DETECTION_RESULTS], TimeImageAcquired;
			bool drawCameraImage = true;

			TimeImageAcquired = getCurrentTime();
			if (!m_pData->isBinocular()) {
				res = detectPupilPurkinjeMono(
					g_Threshold,
					g_PurkinjeSearchArea,
					g_PurkinjeThreshold,
					g_PurkinjeExcludeArea,
					g_MinPupilWidth,
					g_MaxPupilWidth,
					detectionResults);
				if (res != S_PUPIL_PURKINJE)
				{
					detectionResults[MONO_PUPIL_X] = detectionResults[MONO_PUPIL_Y] = res;
					detectionResults[MONO_PURKINJE_X] = detectionResults[MONO_PURKINJE_Y] = res;
				}
			}
			else {
				res = detectPupilPurkinjeBin(
					g_Threshold,
					g_PurkinjeSearchArea,
					g_PurkinjeThreshold,
					g_PurkinjeExcludeArea,
					g_MinPupilWidth,
					g_MaxPupilWidth,
					detectionResults);
				if (res != S_PUPIL_PURKINJE)
				{
					detectionResults[BIN_PUPIL_LX] = detectionResults[BIN_PUPIL_LY] = res;
					detectionResults[BIN_PURKINJE_LX] = detectionResults[BIN_PURKINJE_LY] = res;
					detectionResults[BIN_PUPIL_RX] = detectionResults[BIN_PUPIL_RY] = res;
					detectionResults[BIN_PURKINJE_RX] = detectionResults[BIN_PURKINJE_RY] = res;
				}
			}

			if (m_pData->isRecording())
			{
				TimeImageAcquired = getCurrentTime();
				m_pData->recordGazeData(TimeImageAcquired, detectionResults);

				// USB IO data
				if (g_useUSBIO) {
					m_pData->recordUSBIOData();
				}

				// Camera Spacific Data
				if (g_OutputCameraSpecificData == USE_CAMERASPECIFIC_DATA) {
					m_pData->recordCameraSpecificData();
				}

				m_pData->prepareForNextData();

				drawCameraImage = !m_pMainFrame->getNoRendering();

			}
			else if(m_pData->isCalibratingOrVaridating())
			{
				m_pData->recordCalibrationData(detectionResults);
			}
			
			if (g_ShowCameraImage && drawCameraImage)
			{
				if (!m_pMainFrame->getDrawing())
				{
					cv::Mat dstMat;
					cv::resize(g_DstImg, dstMat, cv::Size(g_PreviewWidth, g_PreviewHeight));
					memcpy(g_pPreviewTextureBuffer, g_DstImg.data, g_PreviewWidth * g_PreviewHeight * sizeof(int));
					wxThreadEvent ev(wxEVT_THREAD, m_pMainFrame->getCameraViewUpdateID());
					wxQueueEvent(m_pMainFrame, ev.Clone());
				}
			}

		}
	}

	return (wxThread::ExitCode)0;
}

