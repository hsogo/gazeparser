#include "wx/wxprec.h"
#include "wx/thread.h"

#ifndef WX_PRECOMP
#include "wx/wx.h"
#endif

#include "opencv2/opencv.hpp"
#include "opencv2/core/core.hpp"
#include "opencv2/highgui/highgui.hpp"

#include "GazeTrackerCommon.h"

#include "SGTMainThread.hpp"
#include "SGTMainFrame.hpp"
#include "SGTCameraView.hpp"
#include "SGTData.hpp"

cv::Mat g_SrcImg;
cv::Mat g_DstImg;
cv::Mat g_CalImg;
cv::Mat g_MorphTransKernel;
static cv::Rect g_ROI;

#define OBLATENESS_LOW  0.67
#define OBLATENESS_HIGH 1.50
#define MAX_FIRST_CANDIDATES 5


int detectPupilPurkinjeMono(int Threshold1, int PurkinjeSearchArea, int PurkinjeThreshold, int PurkinjeExclude, int MinWidth, int MaxWidth, double* results);
int detectPupilPurkinjeBin(int Threshold1, int PurkinjeSearchArea, int PurkinjeThreshold, int PurkinjeExclude, int MinWidth, int MaxWidth, double* results);
static const double PI = 6 * asin(0.5);

bool g_runMainThread;

SGTMainThread::SGTMainThread(SGTMainFrame* frame) : wxThread(wxTHREAD_DETACHED)
{
	m_pMainFrame = frame;
	m_pData = frame->getSGTData();
}


wxThread::ExitCode SGTMainThread::Entry()
{
	g_runMainThread = true;

	while (g_runMainThread)
	{
		if (m_pMainFrame->m_bShowCalResult)
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


			if (g_ShowCameraImage && !m_pMainFrame->m_bNoRendering)
			{ // if it is not under recording, flip screen in a regular way.
				if (m_pMainFrame != nullptr)
					m_pMainFrame->updateCameraView(g_pCameraTextureBuffer);
			}

		}
	}

	return (wxThread::ExitCode)0;
}


int detectPupilPurkinjeMono(int Threshold1, int PurkinjeSearchArea, int PurkinjeThreshold, int PurkinjeExclude, int MinWidth, int MaxWidth, double* results)
{
	cv::Mat tmp, tmp0;
	cv::Mat roi;
	std::vector<std::vector<cv::Point> > contours;
	std::vector<cv::Vec4i> hierarchy;
	std::vector<std::vector<cv::Point> >::iterator it;
	std::vector<cv::Point> firstCandidatePoints[MAX_FIRST_CANDIDATES], candidatePoints;
	std::vector<cv::Point> candidatePointsFine;
	std::vector<cv::Point>::iterator itFine;
	cv::RotatedRect firstCandidateRects[MAX_FIRST_CANDIDATES], candidateRect, candidateRectFine;
	int numCandidates = 0;
	int numPurkinjeCandidates = 0;
	int indexPupilPurkinjeCandidate;
	float PurkinjeCandidateCenterX, PurkinjeCandidateCenterY;

	//If g_ShowCameraImage is true, copy g_frameBuffer to g_pCameraTextureBuffer
	if (g_ShowCameraImage) {
		for (int idx = 0; idx < g_CameraHeight*g_CameraWidth; idx++) { //convert 8bit to 24bit color.
			g_pCameraTextureBuffer[idx] = g_frameBuffer[idx] << 16 | g_frameBuffer[idx] << 8 | g_frameBuffer[idx];
		}
	}

	//Find areas darker than Threshold1
	cv::threshold(g_SrcImg(g_ROI), tmp0, Threshold1, 127, CV_THRESH_BINARY);
	if (g_MorphologicalTrans > 1) {
		cv::morphologyEx(tmp0, tmp, cv::MORPH_CLOSE, g_MorphTransKernel);
	}
	else if (g_MorphologicalTrans < -1) {
		cv::morphologyEx(tmp0, tmp, cv::MORPH_OPEN, g_MorphTransKernel);
	}
	else {
		tmp = tmp0;
	}
	cv::findContours(tmp, contours, hierarchy, CV_RETR_TREE, CV_CHAIN_APPROX_NONE, cv::Point(g_ROI.x, g_ROI.y));

	//If g_ShowCameraImage is true, paint dark areas.
	if (g_ShowCameraImage) {
		for (int iy = 0; iy < g_ROI.height; iy++) {
			unsigned char* p = tmp.ptr<unsigned char>(iy);
			for (int ix = 0; ix < g_ROI.width; ix++)
			{
				if (p[ix] == 0) {
					g_pCameraTextureBuffer[(iy + g_ROI.y)*g_CameraWidth + (ix + g_ROI.x)] |= 150;
				}
			}
		}
	}

	//Find a pupil candidate.
	for (it = contours.begin(); it != contours.end(); it++) {
		if ((int)(*it).size() < 6) {
			continue;
		}

		cv::Rect rr;
		rr = cv::boundingRect(*it);
		double minw = (double)MinWidth / 100 * g_ROI.width;
		double maxw = (double)MaxWidth / 100 * g_ROI.width;
		if (rr.width < minw || rr.width > maxw || rr.height < minw || rr.height > maxw) {
			continue;
		}

		//Fit elliipse
		cv::Mat points(*it);
		cv::RotatedRect r;
		r = cv::fitEllipse(points);

		//Is Center of the ellipse in g_ROI? 
		if (r.center.x <= g_ROI.x || r.center.y <= g_ROI.y || r.center.x >= g_ROI.x + g_ROI.width || r.center.y >= g_ROI.y + g_ROI.height) {
			continue;
		}

		//Check the shape of the ellipse
		if (OBLATENESS_LOW > r.size.height / r.size.width || r.size.height / r.size.width > OBLATENESS_HIGH) {
			continue;
		}

		//Is PurkinjeSearchArea in CameraImage?
		if (r.center.x<PurkinjeSearchArea || r.center.y<PurkinjeSearchArea ||
			r.center.x>g_CameraWidth - PurkinjeSearchArea || r.center.y>g_CameraHeight - PurkinjeSearchArea) {
			continue;
		}

		//Count dark pixels within the ellipse
		double areac = 0;
		for (int ix = (int)(-r.size.width) / 2; ix < (int)r.size.width / 2; ix++) {
			for (int iy = (int)(-r.size.height) / 2; iy < (int)r.size.height / 2; iy++) {
				int xp;
				int yp;
				double rad;
				rad = r.angle*PI / 180;
				xp = (int)(ix*cos(rad) - iy * sin(rad) + r.center.x);
				yp = (int)(ix*sin(rad) + iy * cos(rad) + r.center.y);

				if (xp >= g_ROI.width || yp >= g_ROI.height || xp < 0 || yp < 0) continue;

				unsigned char* p = tmp.ptr<unsigned char>(yp);
				if (p[xp] == 0) {
					areac += 1;
				}
			}
		}
		areac /= (r.size.width*r.size.height*PI / 4);

		//Dark area occupies more than 75% of ellipse?
		if (areac < 0.75) {
			continue;
		}

		//This may be a pupil
		//If g_ShowCameraImage is true, draw ellipse with thick line and draw cross.
		if (g_ShowCameraImage) {
			cv::ellipse(g_DstImg, r, CV_RGB(0, 255, 0));
			cv::line(g_DstImg, cv::Point2f(r.center.x, r.center.y - 20), cv::Point2f(r.center.x, r.center.y + 20), CV_RGB(0, 255, 0));
			cv::line(g_DstImg, cv::Point2f(r.center.x - 20, r.center.y), cv::Point2f(r.center.x + 20, r.center.y), CV_RGB(0, 255, 0));
		}
		firstCandidateRects[numCandidates] = r;
		firstCandidatePoints[numCandidates] = *it;
		numCandidates++;
		if (numCandidates >= MAX_FIRST_CANDIDATES)
			break;
	}

	if (numCandidates >= MAX_FIRST_CANDIDATES) {
		//Too many candidates are found.
		if (g_ShowCameraImage && g_ShowDetectionErrorMsg == 1)
			cv::putText(g_DstImg, "MULTIPLE_PUPIL_CANDIDATES", cv::Point2d(0, 16), cv::FONT_HERSHEY_PLAIN, 1.0, CV_RGB(255, 255, 255));
		return E_MULTIPLE_PUPIL_CANDIDATES;
	}
	else if (numCandidates == 0) {
		//No candidate is found.
		if (g_ShowCameraImage && g_ShowDetectionErrorMsg == 1)
			cv::putText(g_DstImg, "NO_PUPIL_CANDIDATE", cv::Point2d(0, 16), cv::FONT_HERSHEY_PLAIN, 1.0, CV_RGB(255, 255, 255));
		return E_NO_PUPIL_CANDIDATE;
	}

	for (int ic = 0; ic < numCandidates; ic++)
	{
		//Get a region where we search the 1st Purkinje image.
		int x = (int)(firstCandidateRects[ic].center.x) - PurkinjeSearchArea;
		int y = (int)(firstCandidateRects[ic].center.y) - PurkinjeSearchArea;
		int w = PurkinjeSearchArea * 2;
		int h = PurkinjeSearchArea * 2;

		unsigned char* p;
		float cogx, cogy;

		//Find areas brighter than PurkinjeThreshold
		p = g_SrcImg.ptr<unsigned char>((int)firstCandidateRects[ic].center.y);
		cv::threshold(g_SrcImg(cv::Rect(x, y, w, h)), roi, PurkinjeThreshold, 200, CV_THRESH_BINARY);
		cv::findContours(roi, contours, hierarchy, CV_RETR_TREE, CV_CHAIN_APPROX_NONE, cv::Point(x, y));

		int npc = 0;
		float dx1, dx2, dy1, dy2;
		cogx = cogy = 0.0;
		for (it = contours.begin(); it != contours.end(); it++) {
			if ((int)(*it).size() < 6) {
				//Contour of the area is too short.
				continue;
			}

			//Fit elliipse
			cv::Mat points(*it);
			cv::RotatedRect r;
			r = cv::fitEllipse(points);
			dx1 = firstCandidateRects[ic].center.x - cogx;
			dy1 = firstCandidateRects[ic].center.y - cogy;
			dx2 = firstCandidateRects[ic].center.x - r.center.x;
			dy2 = firstCandidateRects[ic].center.y - r.center.y;
			//Find bright area nearest to the pupil center.
			if (dx1*dx1 + dy1 * dy1 > dx2*dx2 + dy2 * dy2) {
				cogx = r.center.x;
				cogy = r.center.y;
			}
			npc++;
		}

		if (npc != 0) {
			indexPupilPurkinjeCandidate = ic;
			candidateRect = firstCandidateRects[ic];
			candidatePoints = firstCandidatePoints[ic];
			PurkinjeCandidateCenterX = cogx;
			PurkinjeCandidateCenterY = cogy;
			numPurkinjeCandidates++;

			if (g_ShowCameraImage) {
				cv::rectangle(g_DstImg, cv::Rect(x, y, w, h), CV_RGB(255, 255, 255));
				cv::line(g_DstImg, cv::Point2f(cogx, cogy - 20), cv::Point2f(cogx, cogy + 20), CV_RGB(255, 192, 0));
				cv::line(g_DstImg, cv::Point2f(cogx - 20, cogy), cv::Point2f(cogx + 20, cogy), CV_RGB(255, 192, 0));
				cv::circle(g_DstImg, cv::Point2d(cogx, cogy), PurkinjeExclude, CV_RGB(255, 192, 0));
			}
		}
	}

	if (numPurkinjeCandidates == 0)
	{
		if (g_ShowCameraImage && g_ShowDetectionErrorMsg == 1)
			cv::putText(g_DstImg, "NO_PURKINJE_CANDIDATE", cv::Point2d(0, 16), cv::FONT_HERSHEY_PLAIN, 1.0, CV_RGB(255, 255, 255));
		return E_NO_PURKINJE_CANDIDATE;
	}
	else if (numPurkinjeCandidates > 1)
	{
		if (g_ShowCameraImage && g_ShowDetectionErrorMsg == 1)
			cv::putText(g_DstImg, "MULTIPLE_PURKINJE_CANDIDATES", cv::Point2d(0, 16), cv::FONT_HERSHEY_PLAIN, 1.0, CV_RGB(255, 255, 255));
		return E_MULTIPLE_PURKINJE_CANDIDATES;
	}


	//Re-fit ellipse
	for (itFine = candidatePoints.begin(); itFine != candidatePoints.end(); itFine++) {

		if (((*itFine).x - PurkinjeCandidateCenterX)*((*itFine).x - PurkinjeCandidateCenterX) + ((*itFine).y - PurkinjeCandidateCenterY)*((*itFine).y - PurkinjeCandidateCenterY) > PurkinjeExclude*PurkinjeExclude) {
			candidatePointsFine.push_back(*itFine);
			if (g_ShowCameraImage) cv::circle(g_DstImg, *itFine, 1, CV_RGB(255, 255, 255));
		}
	}

	if (candidatePointsFine.size() < 10)
	{
		//Re-fitted ellipse is too small
		if (g_ShowCameraImage && g_ShowDetectionErrorMsg == 1)
			cv::putText(g_DstImg, "NO_FINE_PUPIL_CANDIDATE", cv::Point2d(0, 16), cv::FONT_HERSHEY_PLAIN, 1.0, CV_RGB(255, 255, 255));
		return E_NO_FINE_PUPIL_CANDIDATE;
	}

	candidateRectFine = cv::fitEllipse(cv::Mat(candidatePointsFine));
	if (g_ShowCameraImage) {
		cv::ellipse(g_DstImg, candidateRectFine, CV_RGB(0, 255, 192), 2);
		cv::line(g_DstImg, cv::Point2f(candidateRectFine.center.x, candidateRectFine.center.y - 20), cv::Point2f(candidateRectFine.center.x, candidateRectFine.center.y + 20), CV_RGB(0, 255, 192));
		cv::line(g_DstImg, cv::Point2f(candidateRectFine.center.x - 20, candidateRectFine.center.y), cv::Point2f(candidateRectFine.center.x + 20, candidateRectFine.center.y), CV_RGB(0, 255, 192));
	}


	results[MONO_PUPIL_X] = candidateRectFine.center.x;
	results[MONO_PUPIL_Y] = candidateRectFine.center.y;
	results[MONO_PURKINJE_X] = PurkinjeCandidateCenterX;
	results[MONO_PURKINJE_Y] = PurkinjeCandidateCenterY;
	results[MONO_PUPILSIZE] = candidateRectFine.size.width * candidateRectFine.size.height / 4.0; //area

	return S_PUPIL_PURKINJE;
}

int detectPupilPurkinjeBin(int Threshold1, int PurkinjeSearchArea, int PurkinjeThreshold, int PurkinjeExclude, int MinWidth, int MaxWidth, double* results)
{
	cv::Mat tmp, tmp0;
	cv::Mat roi;
	std::vector<std::vector<cv::Point> > contours;
	std::vector<cv::Vec4i> hierarchy;
	std::vector<std::vector<cv::Point> >::iterator it;
	std::vector<cv::Point> firstCandidatePoints[MAX_FIRST_CANDIDATES];
	std::vector<cv::Point> candidatePointsFine[2];
	std::vector<cv::Point>::iterator itFine;
	cv::RotatedRect firstCandidateRects[MAX_FIRST_CANDIDATES], candidateRectFine[2];
	int numCandidates = 0;
	int numPurkinjeCandidates = 0;
	int numFinalPupilPurkinje = 0;

	//If g_ShowCameraImage is true, copy g_frameBuffer to g_pCameraTextureBuffer
	if (g_ShowCameraImage) {
		for (int idx = 0; idx < g_CameraHeight*g_CameraWidth; idx++) { //convert 8bit to 24bit color.
			g_pCameraTextureBuffer[idx] = g_frameBuffer[idx] << 16 | g_frameBuffer[idx] << 8 | g_frameBuffer[idx];
		}
	}

	//Find areas darker than Threshold1
	cv::threshold(g_SrcImg(g_ROI), tmp0, Threshold1, 127, CV_THRESH_BINARY);
	if (g_MorphologicalTrans > 1) {
		cv::morphologyEx(tmp0, tmp, cv::MORPH_CLOSE, g_MorphTransKernel);
	}
	else if (g_MorphologicalTrans < -1) {
		cv::morphologyEx(tmp0, tmp, cv::MORPH_OPEN, g_MorphTransKernel);
	}
	else {
		tmp = tmp0;
	}
	cv::findContours(tmp, contours, hierarchy, CV_RETR_TREE, CV_CHAIN_APPROX_NONE, cv::Point(g_ROI.x, g_ROI.y));

	//If g_ShowCameraImage is true, paint dark areas.
	if (g_ShowCameraImage) {
		for (int iy = 0; iy < g_ROI.height; iy++) {
			unsigned char* p = tmp.ptr<unsigned char>(iy);
			for (int ix = 0; ix < g_ROI.width; ix++)
			{
				if (p[ix] == 0) {
					g_pCameraTextureBuffer[(iy + g_ROI.y)*g_CameraWidth + (ix + g_ROI.x)] |= 150;
				}
			}
		}
	}

	//Find a pupil candidate.
	for (it = contours.begin(); it != contours.end(); it++) {
		if ((int)(*it).size() < 6) {
			continue;
		}

		cv::Rect rr;
		rr = cv::boundingRect(*it);
		double minw = (double)MinWidth / 100 * g_ROI.width;
		double maxw = (double)MaxWidth / 100 * g_ROI.width;
		if (rr.width < minw || rr.width > maxw || rr.height < minw || rr.height > maxw) {
			continue;
		}

		//Fit elliipse
		cv::Mat points(*it);
		cv::RotatedRect r;
		r = cv::fitEllipse(points);

		//Is Center of the ellipse in g_ROI? 
		if (r.center.x <= g_ROI.x || r.center.y <= g_ROI.y || r.center.x >= g_ROI.x + g_ROI.width || r.center.y >= g_ROI.y + g_ROI.height) {
			continue;
		}

		//Check the shape of the ellipse
		if (OBLATENESS_LOW > r.size.height / r.size.width || r.size.height / r.size.width > OBLATENESS_HIGH) {
			continue;
		}

		//Is PurkinjeSearchArea in CameraImage?
		if (r.center.x<PurkinjeSearchArea || r.center.y<PurkinjeSearchArea ||
			r.center.x>g_CameraWidth - PurkinjeSearchArea || r.center.y>g_CameraHeight - PurkinjeSearchArea) {
			continue;
		}

		//Count dark pixels within the ellipse
		double areac = 0;
		for (int ix = (int)(-r.size.width) / 2; ix < (int)r.size.width / 2; ix++) {
			for (int iy = (int)(-r.size.height) / 2; iy < (int)r.size.height / 2; iy++) {
				int xp;
				int yp;
				double rad;
				rad = r.angle*PI / 180;
				xp = (int)(ix*cos(rad) - iy * sin(rad) + r.center.x);
				yp = (int)(ix*sin(rad) + iy * cos(rad) + r.center.y);

				if (xp >= g_ROI.width || yp >= g_ROI.height || xp < 0 || yp < 0) continue;

				unsigned char* p = tmp.ptr<unsigned char>(yp);
				if (p[xp] == 0) {
					areac += 1;
				}
			}
		}
		areac /= (r.size.width*r.size.height*PI / 4);

		//Dark area occupies more than 75% of ellipse?
		if (areac < 0.75) {
			continue;
		}

		//This may be a pupil
		//If g_ShowCameraImage is true, draw ellipse with thick line and draw cross.
		if (g_ShowCameraImage) {
			cv::ellipse(g_DstImg, r, CV_RGB(0, 255, 0));
			cv::line(g_DstImg, cv::Point2f(r.center.x, r.center.y - 20), cv::Point2f(r.center.x, r.center.y + 20), CV_RGB(0, 255, 0));
			cv::line(g_DstImg, cv::Point2f(r.center.x - 20, r.center.y), cv::Point2f(r.center.x + 20, r.center.y), CV_RGB(0, 255, 0));
		}
		firstCandidateRects[numCandidates] = r;
		firstCandidatePoints[numCandidates] = *it;
		numCandidates++;
		if (numCandidates >= MAX_FIRST_CANDIDATES)
			break;
	}

	if (numCandidates >= MAX_FIRST_CANDIDATES) {
		//Too many candidates are found.
		if (g_ShowCameraImage && g_ShowDetectionErrorMsg == 1)
			cv::putText(g_DstImg, "MULTIPLE_PUPIL_CANDIDATES", cv::Point2d(0, 16), cv::FONT_HERSHEY_PLAIN, 1.0, CV_RGB(255, 255, 255));
		return E_MULTIPLE_PUPIL_CANDIDATES;
	}
	else if (numCandidates == 0) {
		//No candidate is found.
		if (g_ShowCameraImage && g_ShowDetectionErrorMsg == 1)
			cv::putText(g_DstImg, "NO_PUPIL_CANDIDATE", cv::Point2d(0, 16), cv::FONT_HERSHEY_PLAIN, 1.0, CV_RGB(255, 255, 255));
		return E_NO_PUPIL_CANDIDATE;
	}

	results[BIN_PUPIL_LX] = E_NO_PUPIL_CANDIDATE;
	results[BIN_PUPIL_LY] = E_NO_PUPIL_CANDIDATE;
	results[BIN_PURKINJE_LX] = E_NO_PUPIL_CANDIDATE;
	results[BIN_PURKINJE_LY] = E_NO_PUPIL_CANDIDATE;
	results[BIN_PUPIL_RX] = E_NO_PUPIL_CANDIDATE;
	results[BIN_PUPIL_RY] = E_NO_PUPIL_CANDIDATE;
	results[BIN_PURKINJE_RX] = E_NO_PUPIL_CANDIDATE;
	results[BIN_PURKINJE_RY] = E_NO_PUPIL_CANDIDATE;

	//Get a region where we search the 1st Purkinje image.
	for (int ic = 0; ic < numCandidates; ic++) {
		int x = (int)(firstCandidateRects[ic].center.x) - PurkinjeSearchArea;
		int y = (int)(firstCandidateRects[ic].center.y) - PurkinjeSearchArea;
		int w = PurkinjeSearchArea * 2;
		int h = PurkinjeSearchArea * 2;

		unsigned char* p;
		float cogx, cogy;

		//Find areas brighter than PurkinjeThreshold
		p = g_SrcImg.ptr<unsigned char>((int)firstCandidateRects[ic].center.y);
		cv::threshold(g_SrcImg(cv::Rect(x, y, w, h)), roi, PurkinjeThreshold, 200, CV_THRESH_BINARY);
		cv::findContours(roi, contours, hierarchy, CV_RETR_TREE, CV_CHAIN_APPROX_NONE, cv::Point(x, y));

		int npc = 0;
		float dx1, dx2, dy1, dy2;
		cogx = cogy = 0.0;
		for (it = contours.begin(); it != contours.end(); it++) {
			if ((int)(*it).size() < 6) {
				//Contour of the area is too short.
				continue;
			}

			//Fit elliipse
			cv::Mat points(*it);
			cv::RotatedRect r;
			r = cv::fitEllipse(points);
			dx1 = firstCandidateRects[ic].center.x - cogx;
			dy1 = firstCandidateRects[ic].center.y - cogy;
			dx2 = firstCandidateRects[ic].center.x - r.center.x;
			dy2 = firstCandidateRects[ic].center.y - r.center.y;
			//Find bright area nearest to the pupil center.
			if (dx1*dx1 + dy1 * dy1 > dx2*dx2 + dy2 * dy2) {
				cogx = r.center.x;
				cogy = r.center.y;
			}
			npc++;
		}
		if (npc == 0) {
			//no Purkinje Image
			continue;
		}
		numPurkinjeCandidates++;

		if (g_ShowCameraImage) {
			cv::rectangle(g_DstImg, cv::Rect(x, y, w, h), CV_RGB(255, 255, 255));
			cv::line(g_DstImg, cv::Point2f(cogx, cogy - 20), cv::Point2f(cogx, cogy + 20), CV_RGB(255, 192, 0));
			cv::line(g_DstImg, cv::Point2f(cogx - 20, cogy), cv::Point2f(cogx + 20, cogy), CV_RGB(255, 192, 0));
			cv::circle(g_DstImg, cv::Point2d(cogx, cogy), PurkinjeExclude, CV_RGB(255, 192, 0));
		}

		if (numFinalPupilPurkinje < 2)
		{
			//Re-fit ellipse
			for (itFine = firstCandidatePoints[ic].begin(); itFine != firstCandidatePoints[ic].end(); itFine++) {

				if (((*itFine).x - cogx)*((*itFine).x - cogx) + ((*itFine).y - cogy)*((*itFine).y - cogy) > PurkinjeExclude*PurkinjeExclude) {
					candidatePointsFine[numFinalPupilPurkinje].push_back(*itFine);
					if (g_ShowCameraImage) cv::circle(g_DstImg, *itFine, 1, CV_RGB(255, 255, 255));
				}
			}

			if (candidatePointsFine[numFinalPupilPurkinje].size() < 10)
			{
				// no fine pupil candidates
				continue;
			}

			candidateRectFine[numFinalPupilPurkinje] = cv::fitEllipse(cv::Mat(candidatePointsFine[numFinalPupilPurkinje]));
			if (g_ShowCameraImage) {
				cv::ellipse(g_DstImg, candidateRectFine[numFinalPupilPurkinje], CV_RGB(0, 255, 192), 2);
				cv::line(g_DstImg, cv::Point2f(candidateRectFine[numFinalPupilPurkinje].center.x, candidateRectFine[numFinalPupilPurkinje].center.y - 20), cv::Point2f(candidateRectFine[numFinalPupilPurkinje].center.x, candidateRectFine[numFinalPupilPurkinje].center.y + 20), CV_RGB(0, 255, 192));
				cv::line(g_DstImg, cv::Point2f(candidateRectFine[numFinalPupilPurkinje].center.x - 20, candidateRectFine[numFinalPupilPurkinje].center.y), cv::Point2f(candidateRectFine[numFinalPupilPurkinje].center.x + 20, candidateRectFine[numFinalPupilPurkinje].center.y), CV_RGB(0, 255, 192));
			}

			if (candidateRectFine[numFinalPupilPurkinje].center.x < g_CameraWidth / 2) { //leftside of the camera image = right eye
				results[BIN_PUPIL_RX] = candidateRectFine[numFinalPupilPurkinje].center.x;
				results[BIN_PUPIL_RY] = candidateRectFine[numFinalPupilPurkinje].center.y;
				results[BIN_PURKINJE_RX] = cogx;
				results[BIN_PURKINJE_RY] = cogy;
				results[BIN_PUPILSIZE_R] = candidateRectFine[numFinalPupilPurkinje].size.width * candidateRectFine[numFinalPupilPurkinje].size.height / 4.0; //area
			}
			else {
				results[BIN_PUPIL_LX] = candidateRectFine[numFinalPupilPurkinje].center.x;
				results[BIN_PUPIL_LY] = candidateRectFine[numFinalPupilPurkinje].center.y;
				results[BIN_PURKINJE_LX] = cogx;
				results[BIN_PURKINJE_LY] = cogy;
				results[BIN_PUPILSIZE_L] = candidateRectFine[numFinalPupilPurkinje].size.width * candidateRectFine[numFinalPupilPurkinje].size.height / 4.0; //area
			}

			numFinalPupilPurkinje++;
		}
	}

	if (numPurkinjeCandidates == 0)
	{
		if (g_ShowCameraImage && g_ShowDetectionErrorMsg == 1)
			cv::putText(g_DstImg, "NO_PURKINJE_CANDIDATE", cv::Point2d(0, 16), cv::FONT_HERSHEY_PLAIN, 1.0, CV_RGB(255, 255, 255));
		return E_NO_PURKINJE_CANDIDATE;
	}
	else if (numPurkinjeCandidates > 2)
	{
		if (g_ShowCameraImage && g_ShowDetectionErrorMsg == 1)
			cv::putText(g_DstImg, "MULTIPLE_PURKINJE_CANDIDATES", cv::Point2d(0, 16), cv::FONT_HERSHEY_PLAIN, 1.0, CV_RGB(255, 255, 255));
		return E_MULTIPLE_PURKINJE_CANDIDATES;
	}
	else if (numFinalPupilPurkinje == 0)
	{
		if (g_ShowCameraImage && g_ShowDetectionErrorMsg == 1)
			cv::putText(g_DstImg, "NO_FINE_PUPIL_CANDIDATE", cv::Point2d(0, 16), cv::FONT_HERSHEY_PLAIN, 1.0, CV_RGB(255, 255, 255));
		return E_NO_FINE_PUPIL_CANDIDATE;
	}

	return S_PUPIL_PURKINJE;
}


void updateMorphTransKernel(void)
{
	if (g_MorphologicalTrans > 1)
		g_MorphTransKernel = cv::getStructuringElement(cv::MORPH_ELLIPSE, cv::Size(g_MorphologicalTrans, g_MorphologicalTrans));
	else if (g_MorphologicalTrans < -1)
		g_MorphTransKernel = cv::getStructuringElement(cv::MORPH_ELLIPSE, cv::Size(-g_MorphologicalTrans, -g_MorphologicalTrans));
}

int initBuffers(void)
{
	if (g_CameraWidth <= 0 || g_CameraHeight <= 0 || g_PreviewWidth <= 0 || g_PreviewHeight <= 0)
	{
		g_LogFS << "ERROR: wrong camera/preview size (" << g_CameraWidth << "," << g_CameraHeight
			<< "," << g_PreviewWidth << "," << g_PreviewHeight << ")" << std::endl;
		return E_FAIL;
	}

	if (g_ROIWidth <= 0 || g_ROIHeight <= 0 || g_ROIWidth > g_CameraWidth || g_ROIHeight > g_ROIHeight)
	{
		g_LogFS << "ERROR: ROI width/height must be smaller than Camera width/height" << std::endl;
		return E_FAIL;
	}

	g_frameBuffer = (unsigned char*)malloc(g_CameraHeight*g_CameraWidth * sizeof(unsigned char));
	g_pCameraTextureBuffer = (int*)malloc(g_CameraHeight*g_CameraWidth * sizeof(int));
	g_pCalResultTextureBuffer = (int*)malloc(g_PreviewHeight*g_PreviewWidth * sizeof(int));
	g_SendImageBuffer = (unsigned char*)malloc(g_ROIHeight*g_ROIWidth * sizeof(unsigned char) + 1);
	if (g_frameBuffer == NULL || g_pCameraTextureBuffer == NULL || g_pCalResultTextureBuffer == NULL) {
		g_LogFS << "ERROR: failed to allocate camera/preview buffer" << std::endl;
		return E_FAIL;
	}

	g_SrcImg = cv::Mat(g_CameraHeight, g_CameraWidth, CV_8UC1, g_frameBuffer);
	g_DstImg = cv::Mat(g_CameraHeight, g_CameraWidth, CV_8UC4, g_pCameraTextureBuffer);
	g_CalImg = cv::Mat(g_PreviewHeight, g_PreviewWidth, CV_8UC4, g_pCalResultTextureBuffer);
	g_ROI = cv::Rect(int((g_CameraWidth - g_ROIWidth) / 2),
		int((g_CameraHeight - g_ROIHeight) / 2),
		g_ROIWidth, g_ROIHeight);

	updateMorphTransKernel();

	return S_OK;
}
