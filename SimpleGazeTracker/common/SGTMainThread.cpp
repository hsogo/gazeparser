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
	g_runMainThread = true;

	while (g_runMainThread)
	{
		if (m_pMainFrame->getShowCalResult())
		{ //show calibration result.
			m_pMainFrame->drawCalResult();
			if (m_pMainFrame != nullptr)
				m_pMainFrame->updateCameraView(g_pCalResultTextureBuffer);
		}
		else if (getCameraImage() == S_OK)
		{ //retrieve camera image and process it.
			int res;
			double detectionResults[MAX_DETECTION_RESULTS], TimeImageAcquired;

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

			}
			else if(m_pData->isCalibratingOrVaridating())
			{
				m_pData->recordCalibrationData(detectionResults);
			}


			if (g_ShowCameraImage && !m_pMainFrame->getNoRendering())
			{ // if it is not under recording, flip screen in a regular way.
				if (m_pMainFrame != nullptr)
					m_pMainFrame->updateCameraView(g_pCameraTextureBuffer);
			}

		}
	}

	return (wxThread::ExitCode)0;
}

