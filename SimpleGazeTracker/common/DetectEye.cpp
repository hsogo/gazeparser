/*!
@file DetectEye.cpp
@author Hiroyuki Sogo
@copyright GNU General Public License (GPL) version 3.

@brief Fuctions for detecting pupils and Purkinje images, estimating gaze position, and plot calibration results.

@date 2012/03/23
- Custom menu is supported.
@date 2012/07/02
- define OBLATENESS_LOW and OBLATENESS_HIGH
*/


#include "opencv2/opencv.hpp"
#include "opencv2/core/core.hpp"
#include "opencv2/highgui/highgui.hpp"

#include "GazeTrackerCommon.h"

#include <fstream>

cv::Mat g_SrcImg;
cv::Mat g_DstImg;
cv::Mat g_CalImg;
static cv::Rect g_ROI;

#define OBLATENESS_LOW  0.67
#define OBLATENESS_HIGH 1.50
#define MAX_FIRST_CANDIDATES 5



/*!
Allocate buffers for receiving, processing and sending camera image.

This function must be called after initParameters() was called 
because patameters such as g_CameraWidth are initialized in initParameters().
This function should be called before initCamera() because, in some cameras,
buffers must be allocated before camera initialization.

@return int
@retval S_OK Initialization succeeded.
@retval E_FAIL Initialization failed.

@date 2012/04/06 created.
*/
int initBuffers(void)
{
	if(g_CameraWidth<=0 || g_CameraHeight<=0 || g_PreviewWidth<=0 || g_PreviewHeight<=0)
	{
		g_LogFS << "ERROR: wrong camera/preview size (" << g_CameraWidth << "," << g_CameraHeight
		        << "," << g_PreviewWidth << "," << g_PreviewHeight << ")"<< std::endl;
		return E_FAIL;
	}

	if(g_ROIWidth<=0||g_ROIHeight<=0||g_ROIWidth>g_CameraWidth||g_ROIHeight>g_ROIHeight)
	{
		g_LogFS << "ERROR: ROI width/height must be smaller than Camera width/height" << std::endl;
		return E_FAIL;
	}

	g_frameBuffer = (unsigned char*)malloc(g_CameraHeight*g_CameraWidth*sizeof(unsigned char));
	g_pCameraTextureBuffer = (int*)malloc(g_CameraHeight*g_CameraWidth*sizeof(int));
	g_pCalResultTextureBuffer = (int*)malloc(g_PreviewHeight*g_PreviewWidth*sizeof(int));
	g_SendImageBuffer = (unsigned char*)malloc(g_ROIHeight*g_ROIWidth*sizeof(unsigned char)+1);
	if(g_frameBuffer==NULL || g_pCameraTextureBuffer==NULL || g_pCalResultTextureBuffer==NULL){
		g_LogFS << "ERROR: failed to allocate camera/preview buffer" << std::endl;
		return E_FAIL;
	}

	g_SrcImg = cv::Mat(g_CameraHeight,g_CameraWidth,CV_8UC1,g_frameBuffer);
	g_DstImg = cv::Mat(g_CameraHeight,g_CameraWidth,CV_8UC4,g_pCameraTextureBuffer);
	g_CalImg = cv::Mat(g_PreviewHeight,g_PreviewWidth,CV_8UC4,g_pCalResultTextureBuffer);
	g_ROI = cv::Rect(int((g_CameraWidth-g_ROIWidth)/2),
	                 int((g_CameraHeight-g_ROIHeight)/2),
	                 g_ROIWidth,g_ROIHeight);

	return S_OK;
}


/*!
detectPupilPurkinjeMono: Detect pupil and purkinje image (monocular recording)

@param[in] Threshold1 Pupil candidates are sought from image areas darker than this value.
@arg Positive Integer (max value is depending on camera).
@param[in] PurkinjeSearchArea 
    @arg Positive integer
@param[in] PurkinjeThreshold 
    @arg BYTE
@param[in] PurkinjeExclude 
    @arg Positive integer
@param[in] PointMin Dark areas whose contour is shorter than this value is removed from pupil candidates.
    @arg Positive integer.  This value must be smaller than PointMax.
@param[in] PointMax Dark areas whose contour is longer than this value is removed from pupil candidates.
    @arg Positive integer.  This value must be larger than PointMin.
@param[out] results 

@return int
@retval S_PUPIL_PURKINJE Pupil and Purkinje images are successfully detected.
@retval E_MULTIPLE_PUPIL_CANDIDATES There were more than MAX_FIRST_CANDIDATES candidates for pupil.
@retval E_NO_PURKINJE_CANDIDATE There was no candidate for Purkinje image.
@retval E_MULTIPLE_PURKINJE_CANDIDATES There were more than two Purkinje image candidates.
@retval E_NO_FINE_PUPIL_CANDIDATE Though candidates for pupil and Purkinje images were found, re-fitting was failed.

@date 2012/07/02
- Check MAX_FIRST_CANDIDATES pupil candidates at maximum.
@date 2012/09/28
- Return Pupil area.
*/
int detectPupilPurkinjeMono(int Threshold1, int PurkinjeSearchArea, int PurkinjeThreshold, int PurkinjeExclude, int PointMin, int PointMax, double results[MAX_DETECTION_RESULTS])
{
	cv::Mat tmp;
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

	//If g_isShowingCameraImage is true, copy g_frameBuffer to g_pCameraTextureBuffer
	if(g_isShowingCameraImage){
		for(int idx=0; idx<g_CameraHeight*g_CameraWidth; idx++){ //convert 8bit to 24bit color.
			g_pCameraTextureBuffer[idx] = g_frameBuffer[idx]<<16 | g_frameBuffer[idx]<<8 | g_frameBuffer[idx];
		}
		cv::rectangle(g_DstImg,g_ROI,CV_RGB(255,255,255));
	}

	//Find areas darker than Threshold1
	cv::threshold(g_SrcImg(g_ROI),tmp,Threshold1,127,CV_THRESH_BINARY);
	cv::findContours(tmp, contours, hierarchy, CV_RETR_TREE, CV_CHAIN_APPROX_NONE, cv::Point(g_ROI.x,g_ROI.y));

	//If g_isShowingCameraImage is true, paint dark areas blue.
	if(g_isShowingCameraImage){
		for (int iy=0; iy<g_ROI.height; iy++){
			unsigned char* p = tmp.ptr<unsigned char>(iy);
			for (int ix=0; ix<g_ROI.width; ix++)
			{
				if(p[ix]==0){
					g_pCameraTextureBuffer[(iy+g_ROI.y)*g_CameraWidth+(ix+g_ROI.x)] |= 150;
				}
			}
		}
	}

	//Find a pupil candidate.
	for(it=contours.begin(); it!=contours.end(); it++){
		if((int)(*it).size()<PointMin || (int)(*it).size()>PointMax){
			//Contour of the area is too short or too long.
			continue;
		}

		//Fit elliipse
		cv::Mat points(*it);
		cv::RotatedRect r;
		r = cv::fitEllipse(points);

		if(r.center.x<=g_ROI.x || r.center.y<=g_ROI.y || r.center.x>=g_ROI.x+g_ROI.width || r.center.y>=g_ROI.y+g_ROI.height){
			//Center of the ellipse is not in g_ROI 
			continue;
		}

		//Is the center of ellipse in dark area?
		unsigned char* p = tmp.ptr<unsigned char>((int)(r.center.y)-g_ROI.y);
		if(p[(int)(r.center.x)-g_ROI.x]>0){
			//The center is NOT in dark area.
			continue;
		}

		//Check the shape of the ellipse
		if( OBLATENESS_LOW < r.size.height/r.size.width && r.size.height/r.size.width < OBLATENESS_HIGH &&
			//This may be a pupil
			r.center.x>PurkinjeSearchArea && r.center.y>PurkinjeSearchArea && 
			r.center.x<g_CameraWidth-PurkinjeSearchArea && r.center.y<g_CameraHeight-PurkinjeSearchArea){
				//If g_isShowingCameraImage is true, draw ellipse with thick line and draw cross.
				if(g_isShowingCameraImage){
					cv::ellipse(g_DstImg,r,CV_RGB(0,255,0));
					cv::line(g_DstImg,cv::Point2f(r.center.x,r.center.y-20),cv::Point2f(r.center.x,r.center.y+20),CV_RGB(0,255,0));
					cv::line(g_DstImg,cv::Point2f(r.center.x-20,r.center.y),cv::Point2f(r.center.x+20,r.center.y),CV_RGB(0,255,0));
				}
			firstCandidateRects[numCandidates] = r;
			firstCandidatePoints[numCandidates] = *it;
			numCandidates++;
			if(numCandidates>=MAX_FIRST_CANDIDATES)
				break;
		}
	}

	if(numCandidates>=MAX_FIRST_CANDIDATES){
		//Too many candidates are found.
		if(g_isShowingCameraImage && g_isShowDetectionErrorMsg==1)
			cv::putText(g_DstImg,"MULTIPLE_PUPIL_CANDIDATES",cv::Point2d(0,16), cv::FONT_HERSHEY_PLAIN, 1.0, CV_RGB(255,255,255));
		return E_MULTIPLE_PUPIL_CANDIDATES;
	}else if(numCandidates==0){
		//No candidate is found.
		if(g_isShowingCameraImage && g_isShowDetectionErrorMsg==1)
			cv::putText(g_DstImg,"NO_PUPIL_CANDIDATE",cv::Point2d(0,16), cv::FONT_HERSHEY_PLAIN, 1.0, CV_RGB(255,255,255));
		return E_NO_PUPIL_CANDIDATE;
	}

	for(int ic=0; ic<numCandidates; ic++)
	{
		//Get a region where we search the 1st Purkinje image.
		int x = (int)(firstCandidateRects[ic].center.x)-PurkinjeSearchArea;
		int y = (int)(firstCandidateRects[ic].center.y)-PurkinjeSearchArea;
		int w = PurkinjeSearchArea*2;
		int h = PurkinjeSearchArea*2;
		
		unsigned char* p;
		float cogx,cogy;
		
		//Find areas brighter than PurkinjeThreshold
		p = g_SrcImg.ptr<unsigned char>((int)firstCandidateRects[ic].center.y);
		cv::threshold(g_SrcImg(cv::Rect(x,y,w,h)),roi,PurkinjeThreshold,200,CV_THRESH_BINARY);
		cv::findContours(roi, contours, hierarchy, CV_RETR_TREE, CV_CHAIN_APPROX_NONE, cv::Point(x,y));
		
		int npc = 0;
		float dx1,dx2,dy1,dy2;
		cogx = cogy = 0.0;
		for(it=contours.begin(); it!=contours.end(); it++){
			if((int)(*it).size()<6){
				//Contour of the area is too short.
				continue;
			}

			//Fit elliipse
			cv::Mat points(*it);
			cv::RotatedRect r;
			r = cv::fitEllipse(points);
			dx1 = firstCandidateRects[ic].center.x-cogx;
			dy1 = firstCandidateRects[ic].center.y-cogy;
			dx2 = firstCandidateRects[ic].center.x-r.center.x;
			dy2 = firstCandidateRects[ic].center.y-r.center.y;
			//Find bright area nearest to the pupil center.
			if(dx1*dx1+dy1*dy1 > dx2*dx2+dy2*dy2){
				cogx = r.center.x;
				cogy = r.center.y;
			}
			npc++;
		}

		if(npc!=0){
			indexPupilPurkinjeCandidate = ic;
			candidateRect = firstCandidateRects[ic];
			candidatePoints = firstCandidatePoints[ic];
			PurkinjeCandidateCenterX = cogx;
			PurkinjeCandidateCenterY = cogy;
			numPurkinjeCandidates++;

			if(g_isShowingCameraImage){
				cv::rectangle(g_DstImg,cv::Rect(x,y,w,h),CV_RGB(255,255,255));
				cv::line(g_DstImg,cv::Point2f(cogx,cogy-20),cv::Point2f(cogx,cogy+20),CV_RGB(255,192,0));
				cv::line(g_DstImg,cv::Point2f(cogx-20,cogy),cv::Point2f(cogx+20,cogy),CV_RGB(255,192,0));
				cv::circle(g_DstImg,cv::Point2d(cogx,cogy),PurkinjeExclude,CV_RGB(255,192,0));
			}
		}
	}

	if(numPurkinjeCandidates==0)
	{
		if(g_isShowingCameraImage && g_isShowDetectionErrorMsg==1)
			cv::putText(g_DstImg,"NO_PURKINJE_CANDIDATE",cv::Point2d(0,16), cv::FONT_HERSHEY_PLAIN, 1.0, CV_RGB(255,255,255));
		return E_NO_PURKINJE_CANDIDATE;
	}
	else if(numPurkinjeCandidates>1)
	{
		if(g_isShowingCameraImage && g_isShowDetectionErrorMsg==1)
			cv::putText(g_DstImg,"MULTIPLE_PURKINJE_CANDIDATES",cv::Point2d(0,16), cv::FONT_HERSHEY_PLAIN, 1.0, CV_RGB(255,255,255));
		return E_MULTIPLE_PURKINJE_CANDIDATES;
	}


	//Re-fit ellipse
	for(itFine = candidatePoints.begin(); itFine != candidatePoints.end(); itFine++){
		 
		if( ((*itFine).x-PurkinjeCandidateCenterX)*((*itFine).x-PurkinjeCandidateCenterX) + ((*itFine).y-PurkinjeCandidateCenterY)*((*itFine).y-PurkinjeCandidateCenterY) >PurkinjeExclude*PurkinjeExclude){
			candidatePointsFine.push_back(*itFine);
			if(g_isShowingCameraImage) cv::circle(g_DstImg,*itFine,1,CV_RGB(255,255,255));
		}
	}

	if(candidatePointsFine.size()<10)
	{
		//Re-fitted ellipse is too small
		if(g_isShowingCameraImage && g_isShowDetectionErrorMsg==1)
			cv::putText(g_DstImg,"NO_FINE_PUPIL_CANDIDATE",cv::Point2d(0,16), cv::FONT_HERSHEY_PLAIN, 1.0, CV_RGB(255,255,255));
		return E_NO_FINE_PUPIL_CANDIDATE;
	}
	
	candidateRectFine = cv::fitEllipse(cv::Mat(candidatePointsFine));
	if(g_isShowingCameraImage){
		cv::ellipse(g_DstImg,candidateRectFine,CV_RGB(0,255,192),2);
		cv::line(g_DstImg,cv::Point2f(candidateRectFine.center.x,candidateRectFine.center.y-20),cv::Point2f(candidateRectFine.center.x,candidateRectFine.center.y+20),CV_RGB(0,255,192));
		cv::line(g_DstImg,cv::Point2f(candidateRectFine.center.x-20,candidateRectFine.center.y),cv::Point2f(candidateRectFine.center.x+20,candidateRectFine.center.y),CV_RGB(0,255,192));
	}


	results[MONO_PUPIL_X] = candidateRectFine.center.x;
	results[MONO_PUPIL_Y] = candidateRectFine.center.y;
	results[MONO_PURKINJE_X] = PurkinjeCandidateCenterX;
	results[MONO_PURKINJE_Y] = PurkinjeCandidateCenterY;
	results[MONO_PUPILSIZE] = candidateRectFine.size.width * candidateRectFine.size.height / 4.0; //area

	return S_PUPIL_PURKINJE;
}

/*!
detectPupilPurkinjeBin: Detect pupil and purkinje image (Binocular recording)

@param[in] Threshold1 Pupil candidates are sought from image areas darker than this value.
@arg Positive Integer (max value is depending on camera).
@param[in] PurkinjeSearchArea 
    @arg Positive integer
@param[in] PurkinjeThreshold 
    @arg BYTE
@param[in] PurkinjeExclude 
    @arg Positive integer
@param[in] PointMin Dark areas whose contour is shorter than this value is removed from pupil candidates.
    @arg Positive integer.  This value must be smaller than PointMax.
@param[in] PointMax Dark areas whose contour is longer than this value is removed from pupil candidates.
    @arg Positive integer.  This value must be larger than PointMin.
@param[out] results 

@return int
@retval S_PUPIL_PURKINJE Pupil and Purkinje images are successfully detected.
@retval E_MULTIPLE_PUPIL_CANDIDATES There were more than MAX_FIRST_CANDIDATES candidates for pupil.
@retval E_NO_PURKINJE_CANDIDATE There was no candidate for Purkinje image.
@retval E_MULTIPLE_PURKINJE_CANDIDATES There were more than two Purkinje image candidates.
@retval E_NO_FINE_PUPIL_CANDIDATE Though candidates for pupil and Purkinje images were found, re-fitting was failed.

@date 2012/07/02
- Check MAX_FIRST_CANDIDATES pupil candidates at maximum.
@date 2012/09/28
- Return Pupil area.
*/
int detectPupilPurkinjeBin(int Threshold1, int PurkinjeSearchArea, int PurkinjeThreshold, int PurkinjeExclude, int PointMin, int PointMax, double results[MAX_DETECTION_RESULTS])
{
	cv::Mat tmp;
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

	//If g_isShowingCameraImage is true, copy g_frameBuffer to g_pCameraTextureBuffer
	if(g_isShowingCameraImage){
		for(int idx=0; idx<g_CameraHeight*g_CameraWidth; idx++){ //convert 8bit to 24bit color.
			g_pCameraTextureBuffer[idx] = g_frameBuffer[idx]<<16 | g_frameBuffer[idx]<<8 | g_frameBuffer[idx];
		}
		cv::rectangle(g_DstImg,g_ROI,CV_RGB(255,255,255));
	}

	//Find areas darker than Threshold1
	cv::threshold(g_SrcImg(g_ROI),tmp,Threshold1,127,CV_THRESH_BINARY);
	cv::findContours(tmp, contours, hierarchy, CV_RETR_TREE, CV_CHAIN_APPROX_NONE, cv::Point(g_ROI.x,g_ROI.y));

	//If g_isShowingCameraImage is true, paint dark areas blue.
	if(g_isShowingCameraImage){
		for (int iy=0; iy<g_ROI.height; iy++){
			unsigned char* p = tmp.ptr<unsigned char>(iy);
			for (int ix=0; ix<g_ROI.width; ix++)
			{
				if(p[ix]==0){
					g_pCameraTextureBuffer[(iy+g_ROI.y)*g_CameraWidth+(ix+g_ROI.x)] |= 150;
				}
			}
		}
	}

	//Find a pupil candidate.
	for(it=contours.begin(); it!=contours.end(); it++){
		if((int)(*it).size()<PointMin || (int)(*it).size()>PointMax){
			//Contour of the area is too short or too long.
			continue;
		}

		//Fit elliipse
		cv::Mat points(*it);
		cv::RotatedRect r;
		r = cv::fitEllipse(points);

		if(r.center.x<=g_ROI.x || r.center.y<=g_ROI.y || r.center.x>=g_ROI.x+g_ROI.width || r.center.y>=g_ROI.y+g_ROI.height){
			//Center of the ellipse is not in g_ROI 
			continue;
		}

		//Is the center of ellipse in dark area?
		unsigned char* p = tmp.ptr<unsigned char>((int)(r.center.y)-g_ROI.y);
		if(p[(int)(r.center.x)-g_ROI.x]>0){
			//The center is NOT in dark area.
			continue;
		}

		//Check the shape of the ellipse
		if( OBLATENESS_LOW < r.size.height/r.size.width && r.size.height/r.size.width < OBLATENESS_HIGH &&
			//This may be a pupil
			r.center.x>PurkinjeSearchArea && r.center.y>PurkinjeSearchArea && 
			r.center.x<g_CameraWidth-PurkinjeSearchArea && r.center.y<g_CameraHeight-PurkinjeSearchArea){
				//If g_isShowingCameraImage is true, draw ellipse with thick line and draw cross.
				if(g_isShowingCameraImage){
					cv::ellipse(g_DstImg,r,CV_RGB(0,255,0));
					cv::line(g_DstImg,cv::Point2f(r.center.x,r.center.y-20),cv::Point2f(r.center.x,r.center.y+20),CV_RGB(0,255,0));
					cv::line(g_DstImg,cv::Point2f(r.center.x-20,r.center.y),cv::Point2f(r.center.x+20,r.center.y),CV_RGB(0,255,0));
				}
			firstCandidateRects[numCandidates] = r;
			firstCandidatePoints[numCandidates] = *it;
			numCandidates++;
			if(numCandidates>=MAX_FIRST_CANDIDATES)
				break;
		}
	}

	if(numCandidates>=MAX_FIRST_CANDIDATES){
		//Too many candidates are found.
		if(g_isShowingCameraImage && g_isShowDetectionErrorMsg==1)
			cv::putText(g_DstImg,"MULTIPLE_PUPIL_CANDIDATES",cv::Point2d(0,16), cv::FONT_HERSHEY_PLAIN, 1.0, CV_RGB(255,255,255));
		return E_MULTIPLE_PUPIL_CANDIDATES;
	}else if(numCandidates==0){
		//No candidate is found.
		if(g_isShowingCameraImage && g_isShowDetectionErrorMsg==1)
			cv::putText(g_DstImg,"NO_PUPIL_CANDIDATE",cv::Point2d(0,16), cv::FONT_HERSHEY_PLAIN, 1.0, CV_RGB(255,255,255));
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
	for(int ic=0; ic<numCandidates; ic++){
		int x= (int)(firstCandidateRects[ic].center.x)-PurkinjeSearchArea;
		int y = (int)(firstCandidateRects[ic].center.y)-PurkinjeSearchArea;
		int w = PurkinjeSearchArea*2;
		int h = PurkinjeSearchArea*2;
	
		unsigned char* p;
		float cogx,cogy;
		
		//Find areas brighter than PurkinjeThreshold
		p = g_SrcImg.ptr<unsigned char>((int)firstCandidateRects[ic].center.y);
		cv::threshold(g_SrcImg(cv::Rect(x,y,w,h)),roi,PurkinjeThreshold,200,CV_THRESH_BINARY);
		cv::findContours(roi, contours, hierarchy, CV_RETR_TREE, CV_CHAIN_APPROX_NONE, cv::Point(x,y));
		
		int npc = 0;
		float dx1,dx2,dy1,dy2;
		cogx = cogy = 0.0;
		for(it=contours.begin(); it!=contours.end(); it++){
			if((int)(*it).size()<6){
				//Contour of the area is too short.
				continue;
			}

			//Fit elliipse
			cv::Mat points(*it);
			cv::RotatedRect r;
			r = cv::fitEllipse(points);
			dx1 = firstCandidateRects[ic].center.x-cogx;
			dy1 = firstCandidateRects[ic].center.y-cogy;
			dx2 = firstCandidateRects[ic].center.x-r.center.x;
			dy2 = firstCandidateRects[ic].center.y-r.center.y;
			//Find bright area nearest to the pupil center.
			if(dx1*dx1+dy1*dy1 > dx2*dx2+dy2*dy2){
				cogx = r.center.x;
				cogy = r.center.y;
			}
			npc++;
		}
		if(npc==0){
			//no Purkinje Image
			continue;
		}
		numPurkinjeCandidates++;
		
		if(g_isShowingCameraImage){
			cv::rectangle(g_DstImg,cv::Rect(x,y,w,h),CV_RGB(255,255,255));
			cv::line(g_DstImg,cv::Point2f(cogx,cogy-20),cv::Point2f(cogx,cogy+20),CV_RGB(255,192,0));
			cv::line(g_DstImg,cv::Point2f(cogx-20,cogy),cv::Point2f(cogx+20,cogy),CV_RGB(255,192,0));
			cv::circle(g_DstImg,cv::Point2d(cogx,cogy),PurkinjeExclude,CV_RGB(255,192,0));
		}
		
		if(numFinalPupilPurkinje<2)
		{
			//Re-fit ellipse
			for(itFine = firstCandidatePoints[ic].begin(); itFine != firstCandidatePoints[ic].end(); itFine++){
				 
				if( ((*itFine).x-cogx)*((*itFine).x-cogx) + ((*itFine).y-cogy)*((*itFine).y-cogy) >PurkinjeExclude*PurkinjeExclude){
					candidatePointsFine[numFinalPupilPurkinje].push_back(*itFine);
					if(g_isShowingCameraImage) cv::circle(g_DstImg,*itFine,1,CV_RGB(255,255,255));
				}
			}

			if(candidatePointsFine[numFinalPupilPurkinje].size()<10)
			{
				// no fine pupil candidates
				continue;
			}

			candidateRectFine[numFinalPupilPurkinje] = cv::fitEllipse(cv::Mat(candidatePointsFine[numFinalPupilPurkinje]));
			if(g_isShowingCameraImage){
				cv::ellipse(g_DstImg,candidateRectFine[numFinalPupilPurkinje],CV_RGB(0,255,192),2);
				cv::line(g_DstImg,cv::Point2f(candidateRectFine[numFinalPupilPurkinje].center.x,candidateRectFine[numFinalPupilPurkinje].center.y-20),cv::Point2f(candidateRectFine[numFinalPupilPurkinje].center.x,candidateRectFine[numFinalPupilPurkinje].center.y+20),CV_RGB(0,255,192));
				cv::line(g_DstImg,cv::Point2f(candidateRectFine[numFinalPupilPurkinje].center.x-20,candidateRectFine[numFinalPupilPurkinje].center.y),cv::Point2f(candidateRectFine[numFinalPupilPurkinje].center.x+20,candidateRectFine[numFinalPupilPurkinje].center.y),CV_RGB(0,255,192));
			}

			if(candidateRectFine[numFinalPupilPurkinje].center.x<g_CameraWidth/2){ //leftside of the camera image = right eye
				results[BIN_PUPIL_RX] = candidateRectFine[numFinalPupilPurkinje].center.x;
				results[BIN_PUPIL_RY] = candidateRectFine[numFinalPupilPurkinje].center.y;
				results[BIN_PURKINJE_RX] = cogx;
				results[BIN_PURKINJE_RY] = cogy;
				results[BIN_PUPILSIZE_R] = candidateRectFine[numFinalPupilPurkinje].size.width * candidateRectFine[numFinalPupilPurkinje].size.height / 4.0; //area
			}else{
				results[BIN_PUPIL_LX] = candidateRectFine[numFinalPupilPurkinje].center.x;
				results[BIN_PUPIL_LY] = candidateRectFine[numFinalPupilPurkinje].center.y;
				results[BIN_PURKINJE_LX] = cogx;
				results[BIN_PURKINJE_LY] = cogy;
				results[BIN_PUPILSIZE_L] = candidateRectFine[numFinalPupilPurkinje].size.width * candidateRectFine[numFinalPupilPurkinje].size.height / 4.0; //area
			}

			numFinalPupilPurkinje++;
		}
	}

	if(numPurkinjeCandidates==0)
	{
		if(g_isShowingCameraImage && g_isShowDetectionErrorMsg==1)
			cv::putText(g_DstImg,"NO_PURKINJE_CANDIDATE",cv::Point2d(0,16), cv::FONT_HERSHEY_PLAIN, 1.0, CV_RGB(255,255,255));
		return E_NO_PURKINJE_CANDIDATE;
	}
	else if(numPurkinjeCandidates>2)
	{
		if(g_isShowingCameraImage && g_isShowDetectionErrorMsg==1)
			cv::putText(g_DstImg,"MULTIPLE_PURKINJE_CANDIDATES",cv::Point2d(0,16), cv::FONT_HERSHEY_PLAIN, 1.0, CV_RGB(255,255,255));
		return E_MULTIPLE_PURKINJE_CANDIDATES;
	}
	else if(numFinalPupilPurkinje==0)
	{
		if(g_isShowingCameraImage && g_isShowDetectionErrorMsg==1)
			cv::putText(g_DstImg,"NO_FINE_PUPIL_CANDIDATE",cv::Point2d(0,16), cv::FONT_HERSHEY_PLAIN, 1.0, CV_RGB(255,255,255));
		return E_NO_FINE_PUPIL_CANDIDATE;
	}

	return S_PUPIL_PURKINJE;
}

/*!
estimateParametersMono: Estimating calibration parameters (for monocular recording).

@param[in] dataCounter Number of data aquired during calibration procedure.
@param[in] eyeData Data aquired during calibration procedure.
@param[in] calPointData Calibraition target positions when data is aquired.
@return No value is returned.
*/
void estimateParametersMono( int dataCounter, double eyeData[MAXDATA][4], double calPointData[MAXDATA][2] )
{
	if(dataCounter==0)
	{
		return;
	}
	cv::Mat IJ(dataCounter,3,CV_64FC1);
	cv::Mat X(dataCounter,1,CV_64FC1);
	cv::Mat Y(dataCounter,1,CV_64FC1);
	cv::MatIterator_<double> it;
	int i;
	for(i=0; i<IJ.rows; i++){
		double* Mi = IJ.ptr<double>(i);
		Mi[0] = eyeData[i][MONO_X];
		Mi[1] = eyeData[i][MONO_Y];
		Mi[2] = 1.0;
	}
	
	for(i=0, it=X.begin<double>(); it!=X.end<double>(); it++){
		*it = calPointData[i][MONO_X];
		i++;
	}

	for(i=0, it=Y.begin<double>(); it!=Y.end<double>(); it++){
		*it = calPointData[i][MONO_Y];
		i++;
	}
	cv::Mat PX = (IJ.t() * IJ).inv()*IJ.t()*X;
	cv::Mat PY = (IJ.t() * IJ).inv()*IJ.t()*Y;
	//g_GX = IJ*PX;  //If calibration results are necessary ...
	//g_GY = IJ*PY;

	//save parameters
	for(int i=0; i<3; i++){
		const double* MiX = PX.ptr<double>(i);
		const double* MiY = PY.ptr<double>(i);
		g_ParamX[i] = *MiX;
		g_ParamY[i] = *MiY;
	}
}

/*!
estimateParametersBin: Estimating calibration parameters (for binocular recording).

@param[in] dataCounter Number of data aquired during calibration procedure.
@param[in] eyeData Data aquired during calibration procedure.
@param[in] calPointData Calibraition target positions when data is aquired.
@return No value is returned.
*/
void estimateParametersBin( int dataCounter, double eyeData[MAXDATA][4], double calPointData[MAXDATA][2] )
{
	//TODO: return errorcode

	if(dataCounter==0)
	{
		return;
	}

	//Common
	cv::Mat X(dataCounter,1,CV_64FC1);
	cv::Mat Y(dataCounter,1,CV_64FC1);
	cv::MatIterator_<double> it;
	int i, j;
	int nValidData;

	for(i=0, it=X.begin<double>(); it!=X.end<double>(); it++){
		*it = calPointData[i][BIN_X];
		i++;
	}

	for(i=0, it=Y.begin<double>(); it!=Y.end<double>(); it++){
		*it = calPointData[i][BIN_Y];
		i++;
	}


	//Left eye
	nValidData = 0;
	for(i=0; i<dataCounter; i++){
		if(eyeData[i][BIN_LX] > E_FIRST_ERROR_CODE){
			nValidData++;
		}
	}
	if(nValidData == 0){
		return;
	}

	cv::Mat LIJ(nValidData,3,CV_64FC1);
	j = 0;
	for(i=0; i<dataCounter; i++){
		if(eyeData[i][BIN_LX] > E_FIRST_ERROR_CODE){
			double* Mi = LIJ.ptr<double>(j);
			Mi[0] = eyeData[i][BIN_LX];
			Mi[1] = eyeData[i][BIN_LY];
			Mi[2] = 1.0;
			j++;
		}
	}
	cv::Mat PLX = (LIJ.t() * LIJ).inv()*LIJ.t()*X;
	cv::Mat PLY = (LIJ.t() * LIJ).inv()*LIJ.t()*Y;

	//Right eye
	nValidData = 0;
	for(i=0; i<dataCounter; i++){
		if(eyeData[i][BIN_RX] > E_FIRST_ERROR_CODE){
			nValidData++;
		}
	}
	if(nValidData == 0){
		return;
	}

	cv::Mat RIJ(nValidData,3,CV_64FC1);
	j = 0;
	for(i=0; i<dataCounter; i++){
		if(eyeData[i][BIN_RX] > E_FIRST_ERROR_CODE){
			double* Mi = RIJ.ptr<double>(j);
			Mi[0] = eyeData[i][BIN_RX];
			Mi[1] = eyeData[i][BIN_RY];
			Mi[2] = 1.0;
			j++;
		}
	}
	for(i=0; i<RIJ.rows; i++){
		double* Mi = RIJ.ptr<double>(i);
		Mi[0] = eyeData[i][BIN_RX];
		Mi[1] = eyeData[i][BIN_RY];
		Mi[2] = 1.0;
	}
	cv::Mat PRX = (RIJ.t() * RIJ).inv()*RIJ.t()*X;
	cv::Mat PRY = (RIJ.t() * RIJ).inv()*RIJ.t()*Y;

	//save parameters
	for(int i=0; i<3; i++){
		const double* MiLX = PLX.ptr<double>(i);
		const double* MiLY = PLY.ptr<double>(i);
		const double* MiRX = PRX.ptr<double>(i);
		const double* MiRY = PRY.ptr<double>(i);
		g_ParamX[i] = *MiLX;
		g_ParamX[i+3] = *MiRX;
		g_ParamY[i] = *MiLY;
		g_ParamY[i+3] = *MiRY;
	}
}

/*!
getGazePositionMono: Convert relative Purkinje image position to gaze position (for monocular recording).

@param[in] im Pointer of two double values which represent Purkinje image position relative to pupil. 
@param[out] xy Pointer of two double values to which gaze position is stored.
@return No value is returned.
*/
void getGazePositionMono(double* im, double* xy)
{
	xy[MONO_X] = g_ParamX[0]*im[0]+g_ParamX[1]*im[1]+g_ParamX[2];
	xy[MONO_Y] = g_ParamY[0]*im[0]+g_ParamY[1]*im[1]+g_ParamY[2];
}

/*!
getGazePositionBin: Convert relative Purkinje image position to gaze position (for monocular recording).

@param[in] im Pointer of four double values which represent Purkinje image position relative to pupil. 
@param[out] xy Pointer of four double values to which gaze position is stored.
@return No value is returned.
*/
void getGazePositionBin(double* im, double* xy)
{
	xy[BIN_LX] = g_ParamX[0]*im[0]+g_ParamX[1]*im[1]+g_ParamX[2];
	xy[BIN_LY] = g_ParamY[0]*im[0]+g_ParamY[1]*im[1]+g_ParamY[2];
	xy[BIN_RX] = g_ParamX[3]*im[2]+g_ParamX[4]*im[3]+g_ParamX[5];
	xy[BIN_RY] = g_ParamY[3]*im[2]+g_ParamY[4]*im[3]+g_ParamY[5];
}

/*!
drawCalResult: Draw calibration result to a buffer.

@param[in] dataCounter Number of calibration data.
@param[in] eyeData Relative Purkinje image position aquired during calibration procedure.
@param[in] calPointData Calibraition target positions when data is aquired.
@param[in] numCalPoint Number of all calibration positions.
@param[in] calPointList List of x, y components of calibration positions.
@param[in] calArea top-left and bottom-right position of calibration area.
@return No value is returned.
*/
void drawCalResult( int dataCounter, double eyeData[MAXDATA][4], double calPointData[MAXDATA][2], int numCalPoint, double calPointList[MAXCALDATA][2], double calArea[4])
{
	double xy[4],r,x,y;
	double calAreaWidth, calAreaHeight,cx,cy;
	int idx;

	//clear image
	cv::rectangle(g_CalImg,cv::Rect(0,0,g_PreviewWidth,g_PreviewHeight),CV_RGB(255,255,255),-1);
	calAreaWidth = calArea[2]-calArea[0];
	calAreaHeight = calArea[3]-calArea[1];

	//draw target position
	for(idx=0; idx<numCalPoint; idx++){
		x = (calPointList[idx][0]-calArea[0]) * g_PreviewWidth/calAreaWidth;
		y = (calPointList[idx][1]-calArea[1]) * g_PreviewHeight/calAreaHeight;
		r = 20 * g_PreviewWidth/calAreaWidth;
		cv::circle(g_CalImg,cv::Point2d(x,y),(int)r,CV_RGB(255,0,0));
		cv::circle(g_CalImg,cv::Point2d(x,y),(int)r*2,CV_RGB(255,0,0));
	}

	//draw gaze postion
	if(g_RecordingMode==RECORDING_MONOCULAR){ //monocular
		for(idx=0; idx<dataCounter; idx++){
			getGazePositionMono(eyeData[idx], xy);
			xy[MONO_X] = xy[MONO_X]-calArea[0];
			xy[MONO_Y] = xy[MONO_Y]-calArea[1];

			cx = calPointData[idx][0]-calArea[0];
			cy = calPointData[idx][1]-calArea[1];

			cv::line(g_CalImg,
				cv::Point2d(xy[MONO_X]*g_PreviewWidth/calAreaWidth,xy[MONO_Y]*g_PreviewHeight/calAreaHeight),
				cv::Point2d(cx*g_PreviewWidth/calAreaWidth,cy*g_PreviewHeight/calAreaHeight),
				CV_RGB(0,0,127));
			cv::circle(g_CalImg,cv::Point2d(xy[MONO_X]* g_PreviewWidth/calAreaWidth,xy[MONO_Y]* g_PreviewHeight/calAreaHeight),3,CV_RGB(0,0,127));
		}
	}else{ //binocular
		cv::putText(g_CalImg,"Blue: left eye", cv::Point2d(8,16), cv::FONT_HERSHEY_COMPLEX, 0.5, CV_RGB(0,0,192));
		cv::putText(g_CalImg,"Green: right eye", cv::Point2d(8,32), cv::FONT_HERSHEY_COMPLEX, 0.5, CV_RGB(0,192,0));
		for(idx=0; idx<dataCounter; idx++){
			getGazePositionBin(eyeData[idx], xy);
			xy[BIN_LX] = xy[BIN_LX]-calArea[0];
			xy[BIN_LY] = xy[BIN_LY]-calArea[1];
			xy[BIN_RX] = xy[BIN_RX]-calArea[0];
			xy[BIN_RY] = xy[BIN_RY]-calArea[1];

			cx = calPointData[idx][0]-calArea[0];
			cy = calPointData[idx][1]-calArea[1];

			//left eye = blue
			cv::line(g_CalImg,
				cv::Point2d(xy[BIN_LX]*g_PreviewWidth/calAreaWidth,xy[BIN_LY]*g_PreviewHeight/calAreaHeight),
				cv::Point2d(cx*g_PreviewWidth/calAreaWidth,cy*g_PreviewHeight/calAreaHeight),
				CV_RGB(0,0,255));
			cv::circle(g_CalImg,cv::Point2d(xy[BIN_LX]* g_PreviewWidth/calAreaWidth,xy[BIN_LY]* g_PreviewHeight/calAreaHeight),3,CV_RGB(0,0,255));
			//right eye = green
			cv::line(g_CalImg,
				cv::Point2d(xy[BIN_RX]*g_PreviewWidth/calAreaWidth,xy[BIN_RY]*g_PreviewHeight/calAreaHeight),
				cv::Point2d(cx*g_PreviewWidth/calAreaWidth,cy*g_PreviewHeight/calAreaHeight),
				CV_RGB(0,255,0));
			cv::circle(g_CalImg,cv::Point2d(xy[BIN_RX]* g_PreviewWidth/calAreaWidth,xy[BIN_RY]* g_PreviewHeight/calAreaHeight),3,CV_RGB(0,255,0));
		}
	}


}

/*!
setCalibrationResults: Calculate goodness, mean and maximum error of calibration.

@param[in] dataCounter Number of calibration data.
@param[in] eyeData Relative Purkinje image position aquired during calibration procedure.
@param[in] calPointData Calibraition target positions when data is aquired.
@param[out] Goodness Goodness of calibration results, defined as a ratio of linear regression coefficients to screen size. Only two elements are used when recording mode is monocular.
@param[out] MaxError Maximum calibration error. Only one element is used when recording mode is monocular.
@param[out] MeanError mean calibration error. Only one element is used when recording mode is monocular.
@return No value is returned.
*/
void setCalibrationResults( int dataCounter, double eyeData[MAXDATA][4], double calPointData[MAXDATA][2], double Goodness[4], double MaxError[2], double MeanError[2] )
{
	int idx;
	double xy[4];
	double error[2], sumerror[2], maxerror[2];

	sumerror[0] = sumerror[1] = 0;
	maxerror[0] = maxerror[1] = 0;

	if(g_RecordingMode==RECORDING_MONOCULAR){ //monocular
		for(idx=0; idx<dataCounter; idx++){
			getGazePositionMono(eyeData[idx], xy);
			error[MONO_1] = sqrt( pow(xy[MONO_X]-calPointData[idx][0],2) + pow(xy[MONO_Y]-calPointData[idx][1],2) );
			if(maxerror[MONO_1]<error[MONO_1])
				maxerror[MONO_1] = error[MONO_1];
			sumerror[MONO_1] += error[MONO_1];
		}
		MaxError[MONO_1] = maxerror[MONO_1];
		MeanError[MONO_1] = sumerror[MONO_1]/dataCounter;
		Goodness[MONO_X] = 100 * (fabs(g_ParamX[0])+fabs(g_ParamX[1])) / (2*g_CameraWidth);
		Goodness[MONO_Y] = 100 * (fabs(g_ParamY[0])+fabs(g_ParamY[1])) / (2*g_CameraHeight);

	}else{ //binocular
		for(idx=0; idx<dataCounter; idx++){
			getGazePositionBin(eyeData[idx], xy);
			error[BIN_L] = sqrt( pow(xy[BIN_LX]-calPointData[idx][0],2) + pow(xy[BIN_LY]-calPointData[idx][1],2) );
			if(maxerror[BIN_L]<error[BIN_L])
				maxerror[BIN_L] = error[BIN_L];
			sumerror[BIN_L] += error[BIN_L];
			error[BIN_R] = sqrt( pow(xy[BIN_RX]-calPointData[idx][0],2) + pow(xy[BIN_RY]-calPointData[idx][1],2) );
			if(maxerror[BIN_R]<error[BIN_R])
				maxerror[BIN_R] = error[BIN_R];
			sumerror[BIN_R] += error[BIN_R];
		}
		MaxError[BIN_L] = maxerror[BIN_L];
		MeanError[BIN_L] = sumerror[BIN_L]/dataCounter;
		Goodness[BIN_LX] = 100 * (fabs(g_ParamX[0])+fabs(g_ParamX[1])) / (2*g_CameraWidth);
		Goodness[BIN_LY] = 100 * (fabs(g_ParamY[0])+fabs(g_ParamY[1])) / (2*g_CameraHeight);

		MaxError[BIN_R] = maxerror[BIN_R];
		MeanError[BIN_R] = sumerror[BIN_R]/dataCounter;
		Goodness[BIN_RX] = 100 * (fabs(g_ParamX[3])+fabs(g_ParamX[4])) / (2*g_CameraWidth);
		Goodness[BIN_RY] = 100 * (fabs(g_ParamY[3])+fabs(g_ParamY[4])) / (2*g_CameraHeight);
	}

}

/*!
setCalibrationResults: Calculate error for each calibration point.

@param[in] dataCounter Number of calibration data.
@param[in] eyeData Relative Purkinje image position aquired during calibration procedure.
@param[in] calPointData Calibraition target positions when data is aquired.
@param[in] numCalPoint Length of calPointList.
@param[in] calPointList Localition of calibration points.
@param[out] calPointAccuracy Accuracy at each calibration point.
@param[out] calPointPrecision Precision at each calibration point.
@return No value is returned.
*/
void setCalibrationError( int dataCounter, double eyeData[MAXDATA][4], double calPointData[MAXDATA][2], int numCalPoint, double calPointList[MAXCALPOINT][2], double calPointAccuracy[MAXCALPOINT][4], double calPointPrecision[MAXCALPOINT][4] )
{
	int idx, idxp, numDataInPoint[MAXCALPOINT][2];
	double xy[4];

	for(idx=0; idx<MAXCALPOINT; idx++){
		numDataInPoint[idx][0] = numDataInPoint[idx][1] = 0;
		calPointAccuracy[idx][0] = calPointAccuracy[idx][1] = calPointAccuracy[idx][2] = calPointAccuracy[idx][3] = 0;
		calPointPrecision[idx][0] = calPointPrecision[idx][1] = calPointPrecision[idx][2] = calPointPrecision[idx][3] = 0;
	}

	if(g_RecordingMode==RECORDING_MONOCULAR){ //monocular
		for(idx=0; idx<dataCounter; idx++){
			getGazePositionMono(eyeData[idx], xy);
			for(idxp=0; idxp<numCalPoint; idxp++){
				if(calPointData[idx][0]==calPointList[idxp][0] && calPointData[idx][1]==calPointList[idxp][1])
					break;
			}
			numDataInPoint[idxp][MONO_1]++;
			calPointAccuracy[idxp][MONO_X] += xy[MONO_X]-calPointList[idxp][0];
			calPointAccuracy[idxp][MONO_Y] += xy[MONO_Y]-calPointList[idxp][1];
			calPointPrecision[idxp][MONO_X] += pow(xy[MONO_X]-calPointList[idxp][0],2);
			calPointPrecision[idxp][MONO_Y] += pow(xy[MONO_Y]-calPointList[idxp][1],2);
		}
		//get average (accuracy) and sd (precision)
		for(idxp=0; idxp<numCalPoint; idxp++){
			if(numDataInPoint[idxp]==0){
				calPointAccuracy[idxp][MONO_X] = calPointAccuracy[idxp][MONO_Y] = E_NO_CALIBRATION_DATA;
				calPointPrecision[idxp][MONO_X] = calPointPrecision[idxp][MONO_Y] = E_NO_CALIBRATION_DATA;
			}else{
				//average
				calPointAccuracy[idxp][MONO_X] /= numDataInPoint[idxp][MONO_1];
				calPointAccuracy[idxp][MONO_Y] /= numDataInPoint[idxp][MONO_1];
				//sd
				calPointPrecision[idxp][MONO_X] = sqrt(calPointPrecision[idxp][MONO_X]/numDataInPoint[idxp][MONO_1]-calPointAccuracy[idxp][MONO_X]);
				calPointPrecision[idxp][MONO_Y] = sqrt(calPointPrecision[idxp][MONO_Y]/numDataInPoint[idxp][MONO_1]-calPointAccuracy[idxp][MONO_Y]);
			}
		}

	}else{ //binocular
		for(idx=0; idx<dataCounter; idx++){
			getGazePositionBin(eyeData[idx], xy);
			for(idxp=0; idxp<numCalPoint; idxp++){
				if(calPointData[idx][0]==calPointList[idxp][0] && calPointData[idx][1]==calPointList[idxp][1])
					break;
			}
			if(xy[BIN_LX]>E_FIRST_ERROR_CODE){
				numDataInPoint[idxp][BIN_L]++;
				calPointAccuracy[idxp][BIN_LX] += xy[BIN_LX]-calPointList[idxp][0];
				calPointAccuracy[idxp][BIN_LY] += xy[BIN_LY]-calPointList[idxp][1];
				calPointPrecision[idxp][BIN_LX] += pow(xy[BIN_LX]-calPointList[idxp][0],2);
				calPointPrecision[idxp][BIN_LY] += pow(xy[BIN_LY]-calPointList[idxp][1],2);
			}
			if(xy[BIN_RX]>E_FIRST_ERROR_CODE){
				numDataInPoint[idxp][BIN_R]++;
				calPointAccuracy[idxp][BIN_RX] += xy[BIN_RX]-calPointList[idxp][0];
				calPointAccuracy[idxp][BIN_RY] += xy[BIN_RY]-calPointList[idxp][1];
				calPointPrecision[idxp][BIN_RX] += pow(xy[BIN_RX]-calPointList[idxp][0],2);
				calPointPrecision[idxp][BIN_RY] += pow(xy[BIN_RY]-calPointList[idxp][1],2);
			}
		}
		//get average (accuracy)
		for(idxp=0; idxp<numCalPoint; idxp++){
			if(numDataInPoint[idxp][BIN_L]==0){
				calPointAccuracy[idxp][BIN_LX] = calPointAccuracy[idxp][BIN_LY] = E_NO_CALIBRATION_DATA;
				calPointPrecision[idxp][BIN_LX] = calPointPrecision[idxp][BIN_LY] = E_NO_CALIBRATION_DATA;
			}else{
				//average
				calPointAccuracy[idxp][BIN_LX] /= numDataInPoint[idxp][BIN_L];
				calPointAccuracy[idxp][BIN_LY] /= numDataInPoint[idxp][BIN_L];
				//sd
				calPointPrecision[idxp][BIN_LX] = sqrt(calPointPrecision[idxp][BIN_LX]/numDataInPoint[idxp][BIN_L]-calPointAccuracy[idxp][BIN_LX]);
				calPointPrecision[idxp][BIN_LY] = sqrt(calPointPrecision[idxp][BIN_LY]/numDataInPoint[idxp][BIN_L]-calPointAccuracy[idxp][BIN_LY]);
			}

			if(numDataInPoint[idxp][BIN_R]==0){
				calPointAccuracy[idxp][BIN_RX] = calPointAccuracy[idxp][BIN_RY] = E_NO_CALIBRATION_DATA;
				calPointPrecision[idxp][BIN_RX] = calPointPrecision[idxp][BIN_RY] = E_NO_CALIBRATION_DATA;
			}else{
				//average
				calPointAccuracy[idxp][BIN_RX] /= numDataInPoint[idxp][BIN_R];
				calPointAccuracy[idxp][BIN_RY] /= numDataInPoint[idxp][BIN_R];
				//sd
				calPointPrecision[idxp][BIN_RX] = sqrt(calPointPrecision[idxp][BIN_RX]/numDataInPoint[idxp][BIN_R]-calPointAccuracy[idxp][BIN_RX]);
				calPointPrecision[idxp][BIN_RY] = sqrt(calPointPrecision[idxp][BIN_RY]/numDataInPoint[idxp][BIN_R]-calPointAccuracy[idxp][BIN_RY]);
			}
		}
	}
}

/*!
saveCameraImage: save current camera image.

This function is called from sockProcess() when sockProcess() received "saveCameraImage" command.

@param[in] filename Name of image file.
@return No value is returned.
*/
void saveCameraImage(const char* filename)
{
	std::string str(g_DataPath);
	str.append(PATH_SEPARATOR);
	str.append(filename);
	cv::imwrite(str.c_str(), g_DstImg);
}

