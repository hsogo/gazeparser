#define _CRT_SECURE_NO_WARNINGS

#include "opencv2/opencv.hpp"

#include "SGTCommon.h"
#include "SGTData.h"
#include "SGTusbIO.h"


void SGTData::clearData(void)
{
	int i;

	for (i = 0; i < m_DataCounter; i++)
	{
		m_EyeData[i][0] = 0;
		m_EyeData[i][1] = 0;
		m_EyeData[i][2] = 0;
		m_EyeData[i][3] = 0;

		m_PupilSizeData[i][0] = 0;
		m_PupilSizeData[i][1] = 0;
	}

	m_DataCounter = 0;
	m_MessageEnd = 0;
	m_MessageBuffer[0] = '\0';

}

void SGTData::clearCalibrationData()
{
	int i;
	for (i = 0; i < m_NumCalPoint; i++)
	{
		m_CalPointData[i][0] = 0;
		m_CalPointData[i][1] = 0;
	}
	m_NumCalPoint = 0;
}


void SGTData::setCalibrationResults()
{
	int idx;
	double xy[4];
	double error[2], sumerror[2], maxerror[2];

	sumerror[0] = sumerror[1] = 0;
	maxerror[0] = maxerror[1] = 0;

	if (m_RecordingMode == RECORDING_MONOCULAR) { //monocular
		for (idx = 0; idx < m_DataCounter; idx++) {
			getGazePositionMono(m_EyeData[idx], xy);
			error[MONO_1] = sqrt(pow(xy[MONO_X] - m_CalPointData[idx][0], 2) + pow(xy[MONO_Y] - m_CalPointData[idx][1], 2));
			if (maxerror[MONO_1] < error[MONO_1])
				maxerror[MONO_1] = error[MONO_1];
			sumerror[MONO_1] += error[MONO_1];
		}
		m_CalMaxError[MONO_1] = maxerror[MONO_1];
		m_CalMeanError[MONO_1] = sumerror[MONO_1] / m_DataCounter;
		m_CalGoodness[MONO_X] = 100 * (fabs(m_ParamX[0]) + fabs(m_ParamX[1])) / (2 * g_CameraWidth);
		m_CalGoodness[MONO_Y] = 100 * (fabs(m_ParamY[0]) + fabs(m_ParamY[1])) / (2 * g_CameraHeight);

	}
	else { //binocular
		for (idx = 0; idx < m_DataCounter; idx++) {
			getGazePositionBin(m_EyeData[idx], xy);
			error[BIN_L] = sqrt(pow(xy[BIN_LX] - m_CalPointData[idx][0], 2) + pow(xy[BIN_LY] - m_CalPointData[idx][1], 2));
			if (maxerror[BIN_L] < error[BIN_L])
				maxerror[BIN_L] = error[BIN_L];
			sumerror[BIN_L] += error[BIN_L];
			error[BIN_R] = sqrt(pow(xy[BIN_RX] - m_CalPointData[idx][0], 2) + pow(xy[BIN_RY] - m_CalPointData[idx][1], 2));
			if (maxerror[BIN_R] < error[BIN_R])
				maxerror[BIN_R] = error[BIN_R];
			sumerror[BIN_R] += error[BIN_R];
		}
		m_CalMaxError[BIN_L] = maxerror[BIN_L];
		m_CalMeanError[BIN_L] = sumerror[BIN_L] / m_DataCounter;
		m_CalGoodness[BIN_LX] = 100 * (fabs(m_ParamX[0]) + fabs(m_ParamX[1])) / (2 * g_CameraWidth);
		m_CalGoodness[BIN_LY] = 100 * (fabs(m_ParamY[0]) + fabs(m_ParamY[1])) / (2 * g_CameraHeight);

		m_CalMaxError[BIN_R] = maxerror[BIN_R];
		m_CalMeanError[BIN_R] = sumerror[BIN_R] / m_DataCounter;
		m_CalGoodness[BIN_RX] = 100 * (fabs(m_ParamX[3]) + fabs(m_ParamX[4])) / (2 * g_CameraWidth);
		m_CalGoodness[BIN_RY] = 100 * (fabs(m_ParamY[3]) + fabs(m_ParamY[4])) / (2 * g_CameraHeight);
	}

}

void SGTData::setCalibrationError()
{
	int idx, idxp, numDataInPoint[MAXCALPOINT][2];
	double xy[4];

	for (idx = 0; idx < MAXCALPOINT; idx++) {
		numDataInPoint[idx][0] = numDataInPoint[idx][1] = 0;
		m_CalPointAccuracy[idx][0] = m_CalPointAccuracy[idx][1] = m_CalPointAccuracy[idx][2] = m_CalPointAccuracy[idx][3] = 0;
		m_CalPointPrecision[idx][0] = m_CalPointPrecision[idx][1] = m_CalPointPrecision[idx][2] = m_CalPointPrecision[idx][3] = 0;
	}

	if (m_RecordingMode == RECORDING_MONOCULAR) { //monocular
		for (idx = 0; idx < m_DataCounter; idx++) {
			getGazePositionMono(m_EyeData[idx], xy);
			for (idxp = 0; idxp < m_NumCalPoint; idxp++) {
				if (m_CalPointData[idx][0] == m_CalPointList[idxp][0] && m_CalPointData[idx][1] == m_CalPointList[idxp][1])
					break;
			}
			numDataInPoint[idxp][MONO_1]++;
			m_CalPointAccuracy[idxp][MONO_X] += xy[MONO_X] - m_CalPointList[idxp][0];
			m_CalPointAccuracy[idxp][MONO_Y] += xy[MONO_Y] - m_CalPointList[idxp][1];
			m_CalPointPrecision[idxp][MONO_X] += pow(xy[MONO_X] - m_CalPointList[idxp][0], 2);
			m_CalPointPrecision[idxp][MONO_Y] += pow(xy[MONO_Y] - m_CalPointList[idxp][1], 2);
		}
		//get average (accuracy) and sd (precision)
		for (idxp = 0; idxp < m_NumCalPoint; idxp++) {
			if (numDataInPoint[idxp][MONO_1] == 0) {
				m_CalPointAccuracy[idxp][MONO_X] = m_CalPointAccuracy[idxp][MONO_Y] = E_NO_CALIBRATION_DATA;
				m_CalPointPrecision[idxp][MONO_X] = m_CalPointPrecision[idxp][MONO_Y] = E_NO_CALIBRATION_DATA;
			}
			else {
				//average
				m_CalPointAccuracy[idxp][MONO_X] /= numDataInPoint[idxp][MONO_1];
				m_CalPointAccuracy[idxp][MONO_Y] /= numDataInPoint[idxp][MONO_1];
				//sd
				m_CalPointPrecision[idxp][MONO_X] = sqrt(m_CalPointPrecision[idxp][MONO_X] / numDataInPoint[idxp][MONO_1] - pow(m_CalPointAccuracy[idxp][MONO_X], 2));
				m_CalPointPrecision[idxp][MONO_Y] = sqrt(m_CalPointPrecision[idxp][MONO_Y] / numDataInPoint[idxp][MONO_1] - pow(m_CalPointAccuracy[idxp][MONO_Y], 2));
			}
		}

	}
	else { //binocular
		for (idx = 0; idx < m_DataCounter; idx++) {
			getGazePositionBin(m_EyeData[idx], xy);
			for (idxp = 0; idxp < m_NumCalPoint; idxp++) {
				if (m_CalPointData[idx][0] == m_CalPointList[idxp][0] && m_CalPointData[idx][1] == m_CalPointList[idxp][1])
					break;
			}
			if (xy[BIN_LX] > E_FIRST_ERROR_CODE) {
				numDataInPoint[idxp][BIN_L]++;
				m_CalPointAccuracy[idxp][BIN_LX] += xy[BIN_LX] - m_CalPointList[idxp][0];
				m_CalPointAccuracy[idxp][BIN_LY] += xy[BIN_LY] - m_CalPointList[idxp][1];
				m_CalPointPrecision[idxp][BIN_LX] += pow(xy[BIN_LX] - m_CalPointList[idxp][0], 2);
				m_CalPointPrecision[idxp][BIN_LY] += pow(xy[BIN_LY] - m_CalPointList[idxp][1], 2);
			}
			if (xy[BIN_RX] > E_FIRST_ERROR_CODE) {
				numDataInPoint[idxp][BIN_R]++;
				m_CalPointAccuracy[idxp][BIN_RX] += xy[BIN_RX] - m_CalPointList[idxp][0];
				m_CalPointAccuracy[idxp][BIN_RY] += xy[BIN_RY] - m_CalPointList[idxp][1];
				m_CalPointPrecision[idxp][BIN_RX] += pow(xy[BIN_RX] - m_CalPointList[idxp][0], 2);
				m_CalPointPrecision[idxp][BIN_RY] += pow(xy[BIN_RY] - m_CalPointList[idxp][1], 2);
			}
		}
		//get average (accuracy)
		for (idxp = 0; idxp < m_NumCalPoint; idxp++) {
			if (numDataInPoint[idxp][BIN_L] == 0) {
				m_CalPointAccuracy[idxp][BIN_LX] = m_CalPointAccuracy[idxp][BIN_LY] = E_NO_CALIBRATION_DATA;
				m_CalPointPrecision[idxp][BIN_LX] = m_CalPointPrecision[idxp][BIN_LY] = E_NO_CALIBRATION_DATA;
			}
			else {
				//average
				m_CalPointAccuracy[idxp][BIN_LX] /= numDataInPoint[idxp][BIN_L];
				m_CalPointAccuracy[idxp][BIN_LY] /= numDataInPoint[idxp][BIN_L];
				//sd
				m_CalPointPrecision[idxp][BIN_LX] = sqrt(m_CalPointPrecision[idxp][BIN_LX] / numDataInPoint[idxp][BIN_L] - pow(m_CalPointAccuracy[idxp][BIN_LX], 2));
				m_CalPointPrecision[idxp][BIN_LY] = sqrt(m_CalPointPrecision[idxp][BIN_LY] / numDataInPoint[idxp][BIN_L] - pow(m_CalPointAccuracy[idxp][BIN_LY], 2));
			}

			if (numDataInPoint[idxp][BIN_R] == 0) {
				m_CalPointAccuracy[idxp][BIN_RX] = m_CalPointAccuracy[idxp][BIN_RY] = E_NO_CALIBRATION_DATA;
				m_CalPointPrecision[idxp][BIN_RX] = m_CalPointPrecision[idxp][BIN_RY] = E_NO_CALIBRATION_DATA;
			}
			else {
				//average
				m_CalPointAccuracy[idxp][BIN_RX] /= numDataInPoint[idxp][BIN_R];
				m_CalPointAccuracy[idxp][BIN_RY] /= numDataInPoint[idxp][BIN_R];
				//sd
				m_CalPointPrecision[idxp][BIN_RX] = sqrt(m_CalPointPrecision[idxp][BIN_RX] / numDataInPoint[idxp][BIN_R] - pow(m_CalPointAccuracy[idxp][BIN_RX], 2));
				m_CalPointPrecision[idxp][BIN_RY] = sqrt(m_CalPointPrecision[idxp][BIN_RY] / numDataInPoint[idxp][BIN_R] - pow(m_CalPointAccuracy[idxp][BIN_RY], 2));
			}
		}
	}
}

void SGTData::insertSettings(char * param)
{
	char* p;

	if (m_DataFP != nullptr)
	{
		while (true)
		{
			p = strstr(param, "/");
			if (p == nullptr) {
				fprintf(m_DataFP, "%s\n", param);
				break;
			}
			else
			{
				*p = '\0';
				fprintf(m_DataFP, "%s\n", param);
				*p = '/';
				param = p + 1;
			}
		}

		fflush(m_DataFP);
	}
}

void SGTData::setCalibrationArea(int x1, int y1, int x2, int y2)
{
	m_CalibrationArea[0] = x1;
	m_CalibrationArea[1] = y1;
	m_CalibrationArea[2] = x2;
	m_CalibrationArea[3] = y2;
}

void SGTData::getCalibrationArea(int * x1, int * y1, int * x2, int * y2)
{
	*x1 = (int)m_CalibrationArea[0];
	*y1 = (int)m_CalibrationArea[1];
	*x2 = (int)m_CalibrationArea[2];
	*y2 = (int)m_CalibrationArea[3];
}



void SGTData::recordCalSample(double x, double y, int samples)
{
	m_CalPointList[m_NumCalPoint][0] = x;
	m_CalPointList[m_NumCalPoint][1] = y;
	m_CurrentCalPoint[0] = x;
	m_CurrentCalPoint[1] = y;
	m_NumCalPoint++;
	if (m_NumCalPoint >= MAXCALPOINT) {
		//g_LogFS << "Warning: number of calibration point exceeded its maximum (" << MAXCALPOINT << ")" << std::endl;
		m_NumCalPoint = 0;
	}
	m_CalSamplesAtCurrentPoint = samples;
}

void SGTData::deleteCalibrationDataSubset(char* points)
{
	int x, y, datalen, newdatalen;
	char* p = points;
	datalen = m_DataCounter;

	//g_LogFS << "DeleteCalibrationDataSubset:" << points << std::endl;

	while (*p != 0) {
		x = strtol(p, &p, 10);
		p++;
		y = strtol(p, &p, 10);
		for (int i = 0; i < datalen; i++) {
			m_CalPointDelList[i] = (m_CalPointData[i][0] == x && m_CalPointData[i][1] == y) ? true : false;
		}
		newdatalen = 0;
		for (int i = 0; i < datalen; i++) {
			if (!m_CalPointDelList[i]) {
				if (newdatalen != i) {
					m_CalPointData[newdatalen][0] = m_CalPointData[i][0];
					m_CalPointData[newdatalen][1] = m_CalPointData[i][1];
					m_EyeData[newdatalen][0] = m_EyeData[i][0];
					m_EyeData[newdatalen][1] = m_EyeData[i][1];
				}
				newdatalen++;
			}
		}
		datalen = newdatalen;
		if (*p == 0) break;
		p++;
	}
	m_DataCounter = datalen;

}

void SGTData::getCalSample(double x, double y, int samples)
{
	m_CalPointList[m_NumCalPoint][0] = x;
	m_CalPointList[m_NumCalPoint][1] = y;
	m_CurrentCalPoint[0] = x;
	m_CurrentCalPoint[1] = y;
	m_NumCalPoint++;
	if (m_NumCalPoint >= MAXCALPOINT) {
		//m_LogFS << "Warning: number of calibration point exceeded its maximum (" << MAXCALPOINT << ")" << std::endl;
		m_NumCalPoint = 0;
	}
	m_CalSamplesAtCurrentPoint = samples;
}

SGTData::SGTData(bool binocular)
{
	if (binocular)
		m_RecordingMode = RECORDING_BINOCULAR;
	else
		m_RecordingMode = RECORDING_MONOCULAR;
}


void SGTData::getGazePositionMono(double* im, double* xy)
{
	xy[MONO_X] = m_ParamX[0] * im[0] + m_ParamX[1] * im[1] + m_ParamX[2];
	xy[MONO_Y] = m_ParamY[0] * im[0] + m_ParamY[1] * im[1] + m_ParamY[2];
}

void SGTData::getGazePositionBin(double* im, double* xy)
{
	xy[BIN_LX] = m_ParamX[0] * im[0] + m_ParamX[1] * im[1] + m_ParamX[2];
	xy[BIN_LY] = m_ParamY[0] * im[0] + m_ParamY[1] * im[1] + m_ParamY[2];
	xy[BIN_RX] = m_ParamX[3] * im[2] + m_ParamX[4] * im[3] + m_ParamX[5];
	xy[BIN_RY] = m_ParamY[3] * im[2] + m_ParamY[4] * im[3] + m_ParamY[5];
}

void SGTData::recordGazeData(double TimeImageAcquired, double detectionResults[8])
{
	m_TickData[m_DataCounter] = TimeImageAcquired - m_RecStartTime;
	if (m_RecordingMode == RECORDING_MONOCULAR)
	{
		if (detectionResults[MONO_PUPIL_X] <= E_FIRST_ERROR_CODE) //A value smaller than E_FIRST_ERROR_CODE is treated as an error.
		{
			m_EyeData[m_DataCounter][MONO_X] = detectionResults[MONO_PUPIL_X];
			m_EyeData[m_DataCounter][MONO_Y] = detectionResults[MONO_PUPIL_X];
			m_CurrentEyeData[MONO_X] = detectionResults[MONO_PUPIL_X];
			m_CurrentEyeData[MONO_Y] = detectionResults[MONO_PUPIL_X];
			if (g_OutputPupilSize)
			{
				m_PupilSizeData[m_DataCounter][MONO_P] = detectionResults[MONO_PUPILSIZE];
				m_CurrentPupilSize[MONO_P] = detectionResults[MONO_PUPILSIZE];
			}
		}
		else
		{
			m_EyeData[m_DataCounter][MONO_X] = detectionResults[MONO_PUPIL_X] - detectionResults[MONO_PURKINJE_X];
			m_EyeData[m_DataCounter][MONO_Y] = detectionResults[MONO_PUPIL_Y] - detectionResults[MONO_PURKINJE_Y];
			getGazePositionMono(m_EyeData[m_DataCounter], m_CurrentEyeData);
			if (g_OutputPupilSize)
			{
				m_PupilSizeData[m_DataCounter][MONO_P] = detectionResults[MONO_PUPILSIZE];
				m_CurrentPupilSize[MONO_P] = detectionResults[MONO_PUPILSIZE];
			}
		}
	}
	else //binocular
	{
		m_EyeData[m_DataCounter][BIN_LX] = detectionResults[BIN_PUPIL_LX] - detectionResults[BIN_PURKINJE_LX];
		m_EyeData[m_DataCounter][BIN_LY] = detectionResults[BIN_PUPIL_LY] - detectionResults[BIN_PURKINJE_LY];
		m_EyeData[m_DataCounter][BIN_RX] = detectionResults[BIN_PUPIL_RX] - detectionResults[BIN_PURKINJE_RX];
		m_EyeData[m_DataCounter][BIN_RY] = detectionResults[BIN_PUPIL_RY] - detectionResults[BIN_PURKINJE_RY];
		getGazePositionBin(m_EyeData[m_DataCounter], m_CurrentEyeData);
		//pupil
		if (g_OutputPupilSize)
		{
			m_PupilSizeData[m_DataCounter][BIN_LP] = detectionResults[BIN_PUPILSIZE_L];
			m_PupilSizeData[m_DataCounter][BIN_RP] = detectionResults[BIN_PUPILSIZE_R];
			m_CurrentPupilSize[BIN_LP] = detectionResults[BIN_PUPILSIZE_L];
			m_CurrentPupilSize[BIN_RP] = detectionResults[BIN_PUPILSIZE_R];
		}
		//left eye
		if (detectionResults[BIN_PUPIL_LX] <= E_FIRST_ERROR_CODE) //A value smaller than E_FIRST_ERROR_CODE is treated as an error.
		{
			m_EyeData[m_DataCounter][BIN_LX] = detectionResults[BIN_PUPIL_LX];
			m_EyeData[m_DataCounter][BIN_LY] = detectionResults[BIN_PUPIL_LX];
			m_CurrentEyeData[BIN_LX] = detectionResults[BIN_PUPIL_LX];
			m_CurrentEyeData[BIN_LY] = detectionResults[BIN_PUPIL_LX];
		}
		//right eye
		if (detectionResults[BIN_PUPIL_RX] <= E_FIRST_ERROR_CODE) //A value smaller than E_FIRST_ERROR_CODE is treated as an error.
		{
			m_EyeData[m_DataCounter][BIN_RX] = detectionResults[BIN_PUPIL_RX];
			m_EyeData[m_DataCounter][BIN_RY] = detectionResults[BIN_PUPIL_RX];
			m_CurrentEyeData[BIN_RX] = detectionResults[BIN_PUPIL_RX];
			m_CurrentEyeData[BIN_RY] = detectionResults[BIN_PUPIL_RX];
		}
	}
}

void SGTData::recordCalibrationData(double detectionResults[8])
{
	if (m_RecordingMode == RECORDING_MONOCULAR)
	{
		if (detectionResults[MONO_PUPIL_X] <= E_FIRST_ERROR_CODE) //A value smaller than E_FIRST_ERROR_CODE is treated as an error.
		{
			// data should not be included in m_CalPointData.
			return;
		}
		if (m_CalSamplesAtCurrentPoint > 0)
		{
			m_CalPointData[m_DataCounter][MONO_X] = m_CurrentCalPoint[MONO_X];
			m_CalPointData[m_DataCounter][MONO_Y] = m_CurrentCalPoint[MONO_Y];
			m_EyeData[m_DataCounter][MONO_X] = detectionResults[MONO_PUPIL_X] - detectionResults[MONO_PURKINJE_X];
			m_EyeData[m_DataCounter][MONO_Y] = detectionResults[MONO_PUPIL_Y] - detectionResults[MONO_PURKINJE_Y];
			if (g_OutputPupilSize)
			{
				m_PupilSizeData[m_DataCounter][MONO_P] = detectionResults[MONO_PUPILSIZE];
			}
			m_DataCounter++;
			if (m_DataCounter >= MAXCALDATA) {
				// g_pApp->Log("Warning: number of calibration data exceeded its maximum (" << MAXCALDATA << ")");
				m_DataCounter = 0;
			}
			m_CalSamplesAtCurrentPoint--;
		}
	}
	else // binocular mode
	{
		if (detectionResults[BIN_PUPIL_LX] <= E_FIRST_ERROR_CODE &&
			detectionResults[BIN_PUPIL_RX] <= E_FIRST_ERROR_CODE) //A value smaller than E_FIRST_ERROR_CODE is treated as an error.
		{
			// data should not be included in m_CalPointData.
			return;
		}
		if (m_CalSamplesAtCurrentPoint > 0)
		{
			m_CalPointData[m_DataCounter][BIN_X] = m_CurrentCalPoint[BIN_X];
			m_CalPointData[m_DataCounter][BIN_Y] = m_CurrentCalPoint[BIN_Y];
			m_EyeData[m_DataCounter][BIN_LX] = detectionResults[BIN_PUPIL_LX] - detectionResults[BIN_PURKINJE_LX];
			m_EyeData[m_DataCounter][BIN_LY] = detectionResults[BIN_PUPIL_LY] - detectionResults[BIN_PURKINJE_LY];
			m_EyeData[m_DataCounter][BIN_RX] = detectionResults[BIN_PUPIL_RX] - detectionResults[BIN_PURKINJE_RX];
			m_EyeData[m_DataCounter][BIN_RY] = detectionResults[BIN_PUPIL_RY] - detectionResults[BIN_PURKINJE_RY];
			if (g_OutputPupilSize)
			{
				m_PupilSizeData[m_DataCounter][BIN_LP] = detectionResults[BIN_PUPILSIZE_L];
				m_PupilSizeData[m_DataCounter][BIN_RP] = detectionResults[BIN_PUPILSIZE_R];
			}
			m_DataCounter++;
			if (m_DataCounter >= MAXCALDATA) {
				// g_LogFS << "Warning: number of calibration data exceeded its maximum (" << MAXCALDATA << ")" << std::endl;
				m_DataCounter = 0;
			}
			m_CalSamplesAtCurrentPoint--;
		}
	}

}

void SGTData::prepareForNextData()
{
	m_DataCounter++;
	//check overflow
	if (m_DataCounter >= MAXDATA)
	{
		//flush data
		flushGazeData();

		//insert overflow message
		fprintf(m_DataFP, "#OVERFLOW_FLUSH_GAZEDATA,%.3f\n", getCurrentTime() - m_RecStartTime);
		fflush(m_DataFP);

		//reset counter
		m_DataCounter = 0;
	}

}

void SGTData::setUSBIO(SGTusbIO * usbIO)
{
	m_pUSBIO = usbIO;
}

void SGTData::recordUSBIOData()
{
	m_pUSBIO->recordData(m_DataCounter);
}

void SGTData::recordCameraSpecificData()
{
	m_CameraSpecificData[m_DataCounter] = getCameraSpecificData();
}

void SGTData::flushGazeData(void)
{
	double xy[4];
	char buff[255];
	int len = 0;
	if (m_RecordingMode == RECORDING_MONOCULAR) {
		for (int i = 0; i < m_DataCounter; i++) {
			fprintf(m_DataFP, "%.3f,", m_TickData[i]);

			if (m_EyeData[i][0] < E_PUPIL_PURKINJE_DETECTION_FAIL) {
				if (m_EyeData[i][0] == E_MULTIPLE_PUPIL_CANDIDATES)
					fprintf(m_DataFP, "MULTIPUPIL,MULTIPUPIL");
				else if (m_EyeData[i][0] == E_NO_PUPIL_CANDIDATE)
					fprintf(m_DataFP, "NOPUPIL,NOPUPIL");
				else if (m_EyeData[i][0] == E_NO_PURKINJE_CANDIDATE)
					fprintf(m_DataFP, "NOPURKINJE,NOPURKINJE");
				else if (m_EyeData[i][0] == E_MULTIPLE_PURKINJE_CANDIDATES)
					fprintf(m_DataFP, "MULTIPURKINJE,MULTIPURKINJE");
				else if (m_EyeData[i][0] == E_NO_FINE_PUPIL_CANDIDATE)
					fprintf(m_DataFP, "NOFINEPUPIL,NOFINEPUPIL");
				else
					fprintf(m_DataFP, "FAIL,FAIL");

				if (g_OutputPupilSize)
					fprintf(m_DataFP, ",FAIL");

			}
			else {
				getGazePositionMono(m_EyeData[i], xy);
				if (g_OutputPupilSize)
					fprintf(m_DataFP, "%.1f,%.1f,%.1f", xy[MONO_X], xy[MONO_Y], m_PupilSizeData[i][MONO_P]);
				else
					fprintf(m_DataFP, "%.1f,%.1f", xy[MONO_X], xy[MONO_Y]);
			}

			//USBIO
			if (g_useUSBIO) {
				m_pUSBIO->getDataString(i, buff, sizeof(buff));
				fprintf(m_DataFP, ",%s", buff);
			}

			//Camera custom data
			if (g_OutputCameraSpecificData == USE_CAMERASPECIFIC_DATA)
				fprintf(m_DataFP, ",%d", m_CameraSpecificData[i]);

			//End of line
			fprintf(m_DataFP, "\n");
		}
	}
	else { //binocular
		for (int i = 0; i < m_DataCounter; i++) {
			fprintf(m_DataFP, "%.3f,", m_TickData[i]);
			getGazePositionBin(m_EyeData[i], xy);
			//left eye
			if (m_EyeData[i][BIN_LX] < E_PUPIL_PURKINJE_DETECTION_FAIL) {
				if (m_EyeData[i][BIN_LX] == E_MULTIPLE_PUPIL_CANDIDATES)
					fprintf(m_DataFP, "MULTIPUPIL,MULTIPUPIL,");
				else if (m_EyeData[i][BIN_LX] == E_NO_PUPIL_CANDIDATE)
					fprintf(m_DataFP, "NOPUPIL,NOPUPIL,");
				else if (m_EyeData[i][BIN_LX] == E_NO_PURKINJE_CANDIDATE)
					fprintf(m_DataFP, "NOPURKINJE,NOPURKINJE,");
				else if (m_EyeData[i][BIN_LX] == E_MULTIPLE_PURKINJE_CANDIDATES)
					fprintf(m_DataFP, "MULTIPURKINJE,MULTIPURKINJE,");
				else if (m_EyeData[i][BIN_LX] == E_NO_FINE_PUPIL_CANDIDATE)
					fprintf(m_DataFP, "NOFINEPUPIL,NOFINEPUPIL,");
				else
					fprintf(m_DataFP, "FAIL,FAIL,");
			}
			else {
				fprintf(m_DataFP, "%.1f,%.1f,", xy[BIN_LX], xy[BIN_LY]);
			}
			//right eye
			if (m_EyeData[i][BIN_RX] < E_PUPIL_PURKINJE_DETECTION_FAIL) {
				if (m_EyeData[i][BIN_RX] == E_MULTIPLE_PUPIL_CANDIDATES)
					fprintf(m_DataFP, "MULTIPUPIL,MULTIPUPIL");
				else if (m_EyeData[i][BIN_RX] == E_NO_PUPIL_CANDIDATE)
					fprintf(m_DataFP, "NOPUPIL,NOPUPIL");
				else if (m_EyeData[i][BIN_RX] == E_NO_PURKINJE_CANDIDATE)
					fprintf(m_DataFP, "NOPURKINJE,NOPURKINJE");
				else if (m_EyeData[i][BIN_LX] == E_MULTIPLE_PURKINJE_CANDIDATES)
					fprintf(m_DataFP, "MULTIPURKINJE,MULTIPURKINJE");
				else if (m_EyeData[i][BIN_RX] == E_NO_FINE_PUPIL_CANDIDATE)
					fprintf(m_DataFP, "NOFINEPUPIL,NOFINEPUPIL");
				else
					fprintf(m_DataFP, "FAIL,FAIL");
			}
			else {
				fprintf(m_DataFP, "%.1f,%.1f", xy[BIN_RX], xy[BIN_RY]);
			}

			//pupil
			if (g_OutputPupilSize) {
				//left
				if (m_EyeData[i][BIN_LX] < E_PUPIL_PURKINJE_DETECTION_FAIL)
					fprintf(m_DataFP, ",FAIL");
				else
					fprintf(m_DataFP, ",%.1f", m_PupilSizeData[i][BIN_LP]);

				//right
				if (m_EyeData[i][BIN_RX] < E_PUPIL_PURKINJE_DETECTION_FAIL)
					fprintf(m_DataFP, ",FAIL");
				else
					fprintf(m_DataFP, ",%.1f", m_PupilSizeData[i][BIN_RP]);

			}

			//USBIO
			if (g_useUSBIO) {
				m_pUSBIO->getDataString(i, buff, sizeof(buff));
				fprintf(m_DataFP, ",%s", buff);
			}

			//Camera Custom Data
			if (g_OutputCameraSpecificData == USE_CAMERASPECIFIC_DATA)
				fprintf(m_DataFP, ",%d", m_CameraSpecificData[i]);

			//End of line
			fprintf(m_DataFP, "\n");
		}

	}

	fflush(m_DataFP);
}

int SGTData::startRecording(const char * message)
{
	time_t t;
	struct tm *ltm;

	if (m_DataFP != nullptr)
	{
		time(&t);
		ltm = localtime(&t);

		fprintf(m_DataFP, "#START_REC,%d,%d,%d,%d,%d,%d\n", ltm->tm_year + 1900, ltm->tm_mon + 1, ltm->tm_mday, ltm->tm_hour, ltm->tm_min, ltm->tm_sec);
		if (message[0] != '\0')
		{
			fprintf(m_DataFP, "#MESSAGE,0,%s\n", message);
		}
		if (g_RecordingMode == RECORDING_MONOCULAR) {
			fprintf(m_DataFP, "#XPARAM,%f,%f,%f\n", m_ParamX[0], m_ParamX[1], m_ParamX[2]);
			fprintf(m_DataFP, "#YPARAM,%f,%f,%f\n", m_ParamY[0], m_ParamY[1], m_ParamY[2]);
		}
		else {
			fprintf(m_DataFP, "#XPARAM,%f,%f,%f,%f,%f,%f\n", m_ParamX[0], m_ParamX[1], m_ParamX[2], m_ParamX[3], m_ParamX[4], m_ParamX[5]);
			fprintf(m_DataFP, "#YPARAM,%f,%f,%f,%f,%f,%f\n", m_ParamY[0], m_ParamY[1], m_ParamY[2], m_ParamY[3], m_ParamY[4], m_ParamY[5]);
		}
		for (int i = 0; i < m_LastNumCalPoint; i++) {
			fprintf(m_DataFP, "#CALPOINT,%f,%f,", m_LastCalPointList[i][0], m_LastCalPointList[i][1]);
			if (g_RecordingMode == RECORDING_BINOCULAR) { //binocular
				if (m_CalPointAccuracy[i][BIN_LX] == E_NO_CALIBRATION_DATA)
					fprintf(m_DataFP, "NO_CALIBRATION_DATA,NO_CALIBRATION_DATA,");
				else
					fprintf(m_DataFP, "%f,%f,", m_CalPointAccuracy[i][BIN_LX], m_CalPointAccuracy[i][BIN_LY]);

				if (m_CalPointAccuracy[i][BIN_RX] == E_NO_CALIBRATION_DATA)
					fprintf(m_DataFP, "NO_CALIBRATION_DATA,NO_CALIBRATION_DATA,");
				else
					fprintf(m_DataFP, "%f,%f,", m_CalPointAccuracy[i][BIN_RX], m_CalPointAccuracy[i][BIN_RY]);

				if (m_CalPointPrecision[i][BIN_LX] == E_NO_CALIBRATION_DATA)
					fprintf(m_DataFP, "NO_CALIBRATION_DATA,NO_CALIBRATION_DATA,");
				else
					fprintf(m_DataFP, "%f,%f,", m_CalPointPrecision[i][BIN_LX], m_CalPointPrecision[i][BIN_LY]);

				if (m_CalPointAccuracy[i][BIN_RX] == E_NO_CALIBRATION_DATA)
					fprintf(m_DataFP, "NO_CALIBRATION_DATA,NO_CALIBRATION_DATA\n");
				else
					fprintf(m_DataFP, "%f,%f\n", m_CalPointPrecision[i][BIN_RX], m_CalPointPrecision[i][BIN_RY]);
			}
			else { //monocular
				if (m_CalPointAccuracy[i][MONO_X] == E_NO_CALIBRATION_DATA) {
					fprintf(m_DataFP, "NO_CALIBRATION_DATA,NO_CALIBRATION_DATA,");
					fprintf(m_DataFP, "NO_CALIBRATION_DATA,NO_CALIBRATION_DATA\n");
				}
				else {
					fprintf(m_DataFP, "%f,%f,", m_CalPointAccuracy[i][MONO_X], m_CalPointAccuracy[i][MONO_Y]);
					fprintf(m_DataFP, "%f,%f\n", m_CalPointPrecision[i][MONO_X], m_CalPointPrecision[i][MONO_Y]);
				}
			}
		}

		clearData();
		m_DataCounter = 0;
		m_MessageEnd = 0;
		m_MessageBuffer[0] = '\0';
		m_RecStartTime = getCurrentTime();
		m_State = STATE_RECORDING;

		return S_OK;
	}

	return E_FAIL;

}

int SGTData::stopRecording(const char * message)
{
	if (m_DataFP != NULL)
	{
		flushGazeData();

		if (m_MessageEnd > 0)
		{
			fprintf(m_DataFP, "%s", m_MessageBuffer);
		}
		if (message[0] != '\0')
		{
			fprintf(m_DataFP, "#MESSAGE,%.3f,%s\n", getCurrentTime() - m_RecStartTime, message);
		}
		fprintf(m_DataFP, "#STOP_REC\n");
		fflush(m_DataFP); //force writing.

		m_State = STATE_FREE;
		return S_OK;

	}
	m_State = STATE_FREE;
	return E_FAIL;
}

void SGTData::startMeasurement()
{
	clearData();
	m_DataCounter = 0;
	m_MessageEnd = 0;
	m_MessageBuffer[0] = '\0';
	m_State = STATE_RECORDING;

	m_RecStartTime = getCurrentTime();
}

void SGTData::stopMeasurement()
{
	m_State = STATE_FREE;
}

void SGTData::startCalibration()
{
	m_CalSamplesAtCurrentPoint = 0;
	m_State = STATE_CALIBRATION;
}

void SGTData::finishCalibration()
{
	if (m_RecordingMode == RECORDING_MONOCULAR) {
		estimateParametersMono();
	}
	else {
		estimateParametersBin();
	}
	setCalibrationResults();
	setCalibrationError();
	//hold calibration data

	m_LastNumCalPoint = m_NumCalPoint;
	for (int j = 0; j < 2; j++) {
		for (int i = 0; i < MAXCALPOINT; i++) {
			m_LastCalPointList[i][j] = m_CalPointList[i][j];
		}
	}

	m_bCalibrated = true;
	m_lastCalValType = TYPE_CALIBRATION;
	m_State = STATE_FREE;
}

void SGTData::finishValidation()
{
	setCalibrationResults();
	m_lastCalValType = TYPE_VALIDATION;
	m_State = STATE_FREE;
}


int SGTData::openDataFile(char* filename, int overwrite)
{
	std::string str(g_DataPath);
	str.append(PATH_SEPARATOR);
	str.append(filename);

	if (m_DataFP != nullptr) //if data file has already been opened, close it.
	{
		fflush(m_DataFP);
		fclose(m_DataFP);
	}

	if (overwrite == 0) {
		checkAndRenameFile(str);
	}

	m_DataFP = fopen(str.c_str(), "w");
	if (m_DataFP == nullptr) {
		return E_FAIL;
	}

	fprintf(m_DataFP, "#SimpleGazeTrackerDataFile\n#TRACKER_VERSION,%s\n", VERSION);

	fprintf(m_DataFP, "#DATAFORMAT,T,");
	if (g_RecordingMode == RECORDING_MONOCULAR) {
		if (g_OutputPupilSize)
			fprintf(m_DataFP, "X,Y,P");
		else
			fprintf(m_DataFP, "X,Y");
	}
	else {
		if (g_OutputPupilSize)
			fprintf(m_DataFP, "LX,LY,RX,RY,LP,RP");
		else
			fprintf(m_DataFP, "LX,LY,RX,RY");
	}

	if (g_useUSBIO) {
		char buff[255];
		m_pUSBIO->getDataFormatString(buff, sizeof(buff));
		fprintf(m_DataFP, ",USBIO;%s", buff);
	}

	if (g_OutputCameraSpecificData == USE_CAMERASPECIFIC_DATA)
		fprintf(m_DataFP, ",C");

	fprintf(m_DataFP, "\n");

	return S_OK;
}

int SGTData::closeDataFile(void)
{
	if (m_DataFP != nullptr)
	{
		fflush(m_DataFP);
		fclose(m_DataFP);
		m_DataFP = nullptr;

		return S_OK;
	}
	return E_FAIL;
}


void SGTData::estimateParametersMono()
{
	if (m_DataCounter == 0)
	{
		return;
	}
	cv::Mat IJ(m_DataCounter, 3, CV_64FC1);
	cv::Mat X(m_DataCounter, 1, CV_64FC1);
	cv::Mat Y(m_DataCounter, 1, CV_64FC1);
	cv::MatIterator_<double> it;
	int i;
	for (i = 0; i < IJ.rows; i++) {
		double* Mi = IJ.ptr<double>(i);
		Mi[0] = m_EyeData[i][MONO_X];
		Mi[1] = m_EyeData[i][MONO_Y];
		Mi[2] = 1.0;
	}

	for (i = 0, it = X.begin<double>(); it != X.end<double>(); it++) {
		*it = m_CalPointData[i][MONO_X];
		i++;
	}

	for (i = 0, it = Y.begin<double>(); it != Y.end<double>(); it++) {
		*it = m_CalPointData[i][MONO_Y];
		i++;
	}
	cv::Mat PX = (IJ.t() * IJ).inv()*IJ.t()*X;
	cv::Mat PY = (IJ.t() * IJ).inv()*IJ.t()*Y;
	//g_GX = IJ*PX;  //If calibration results are necessary ...
	//g_GY = IJ*PY;

	//save parameters
	for (int i = 0; i < 3; i++) {
		const double* MiX = PX.ptr<double>(i);
		const double* MiY = PY.ptr<double>(i);
		m_ParamX[i] = *MiX;
		m_ParamY[i] = *MiY;
	}
}


void SGTData::estimateParametersBin()
{
	//TODO: return errorcode

	if (m_DataCounter == 0)
	{
		return;
	}

	//Common
	cv::Mat X(m_DataCounter, 1, CV_64FC1);
	cv::Mat Y(m_DataCounter, 1, CV_64FC1);
	cv::MatIterator_<double> it;
	int i, j;
	int nValidData;

	for (i = 0, it = X.begin<double>(); it != X.end<double>(); it++) {
		*it = m_CalPointData[i][BIN_X];
		i++;
	}

	for (i = 0, it = Y.begin<double>(); it != Y.end<double>(); it++) {
		*it = m_CalPointData[i][BIN_Y];
		i++;
	}


	//Left eye
	nValidData = 0;
	for (i = 0; i < m_DataCounter; i++) {
		if (m_EyeData[i][BIN_LX] > E_FIRST_ERROR_CODE) {
			nValidData++;
		}
	}
	if (nValidData == 0) {
		return;
	}

	cv::Mat LIJ(nValidData, 3, CV_64FC1);
	j = 0;
	for (i = 0; i < m_DataCounter; i++) {
		if (m_EyeData[i][BIN_LX] > E_FIRST_ERROR_CODE) {
			double* Mi = LIJ.ptr<double>(j);
			Mi[0] = m_EyeData[i][BIN_LX];
			Mi[1] = m_EyeData[i][BIN_LY];
			Mi[2] = 1.0;
			j++;
		}
	}
	cv::Mat PLX = (LIJ.t() * LIJ).inv()*LIJ.t()*X;
	cv::Mat PLY = (LIJ.t() * LIJ).inv()*LIJ.t()*Y;

	//Right eye
	nValidData = 0;
	for (i = 0; i < m_DataCounter; i++) {
		if (m_EyeData[i][BIN_RX] > E_FIRST_ERROR_CODE) {
			nValidData++;
		}
	}
	if (nValidData == 0) {
		return;
	}

	cv::Mat RIJ(nValidData, 3, CV_64FC1);
	j = 0;
	for (i = 0; i < m_DataCounter; i++) {
		if (m_EyeData[i][BIN_RX] > E_FIRST_ERROR_CODE) {
			double* Mi = RIJ.ptr<double>(j);
			Mi[0] = m_EyeData[i][BIN_RX];
			Mi[1] = m_EyeData[i][BIN_RY];
			Mi[2] = 1.0;
			j++;
		}
	}
	for (i = 0; i < RIJ.rows; i++) {
		double* Mi = RIJ.ptr<double>(i);
		Mi[0] = m_EyeData[i][BIN_RX];
		Mi[1] = m_EyeData[i][BIN_RY];
		Mi[2] = 1.0;
	}
	cv::Mat PRX = (RIJ.t() * RIJ).inv()*RIJ.t()*X;
	cv::Mat PRY = (RIJ.t() * RIJ).inv()*RIJ.t()*Y;

	//save parameters
	for (int i = 0; i < 3; i++) {
		const double* MiLX = PLX.ptr<double>(i);
		const double* MiLY = PLY.ptr<double>(i);
		const double* MiRX = PRX.ptr<double>(i);
		const double* MiRY = PRY.ptr<double>(i);
		m_ParamX[i] = *MiLX;
		m_ParamX[i + 3] = *MiRX;
		m_ParamY[i] = *MiLY;
		m_ParamY[i + 3] = *MiRY;
	}
}

void SGTData::saveCalValResultsDetail(void)
{
	if (isBusy()) return;
	if (!isCalibrated()) return;

	if (m_DataFP != nullptr)
	{
		time_t t;
		struct tm *ltm;
		time(&t);
		ltm = localtime(&t);

		double pos[4];
		if (m_lastCalValType == TYPE_CALIBRATION)
			fprintf(m_DataFP, "#START_DETAIL_CALDATA,%d,%d,%d,%d,%d,%d\n", ltm->tm_year + 1900, ltm->tm_mon + 1, ltm->tm_mday, ltm->tm_hour, ltm->tm_min, ltm->tm_sec);
		else if (m_lastCalValType == TYPE_VALIDATION)
			fprintf(m_DataFP, "#START_DETAIL_VALDATA,%d,%d,%d,%d,%d,%d\n", ltm->tm_year + 1900, ltm->tm_mon + 1, ltm->tm_mday, ltm->tm_hour, ltm->tm_min, ltm->tm_sec);
		else
			return;
		for (int i = 0; i < m_DataCounter; i++)
		{
			if (m_RecordingMode == RECORDING_MONOCULAR) {
				fprintf(m_DataFP, "#CALDATA,%.1f,%.1f,%.2f,%.2f,", m_CalPointData[i][0], m_CalPointData[i][1], m_EyeData[i][MONO_X], m_EyeData[i][MONO_Y]);
				getGazePositionMono(m_EyeData[i], pos);
				fprintf(m_DataFP, "%.2f,%.2f", pos[0], pos[1]);
				if (g_OutputPupilSize) {
					fprintf(m_DataFP, ",%.2f\n", m_PupilSizeData[i][MONO_P]);
				}
				else {
					fprintf(m_DataFP, "\n");
				}
			}
			else {
				fprintf(m_DataFP, "#CALDATA,%.1f,%.1f,%.2f,%.2f,%.2f,%.2f,", m_CalPointData[i][0], m_CalPointData[i][1], m_EyeData[i][BIN_LX], m_EyeData[i][BIN_LY], m_EyeData[i][BIN_RX], m_EyeData[i][BIN_RY]);
				getGazePositionBin(m_EyeData[i], pos);
				fprintf(m_DataFP, "%.2f,%.2f,%.2f,%.2f", pos[0], pos[1], pos[2], pos[3]);
				if (g_OutputPupilSize) {
					fprintf(m_DataFP, ",%.2f,%f2\n", m_PupilSizeData[i][BIN_LP], m_PupilSizeData[i][BIN_RP]);
				}
				else {
					fprintf(m_DataFP, "\n");
				}
			}
		}
		if (m_lastCalValType == TYPE_CALIBRATION)
			fprintf(m_DataFP, "#END_DETAIL_CALDATA\n");
		else if (m_lastCalValType == TYPE_VALIDATION)
			fprintf(m_DataFP, "#END_DETAIL_VALDATA\n");

		fflush(m_DataFP);
	}
}

void SGTData::insertMessage(char* message)
{
	double ctd;
	ctd = getCurrentTime() - (m_RecStartTime - g_DelayCorrection);
	m_MessageEnd += snprintf(m_MessageBuffer + m_MessageEnd, MAXMESSAGE - m_MessageEnd, "#MESSAGE,%.3f,%s\n", ctd, message);
	//check overflow
	if (MAXMESSAGE - m_MessageEnd < 128)
	{
		fprintf(m_DataFP, "%s", m_MessageBuffer);
		fprintf(m_DataFP, "#OVERFLOW_FLUSH_MESSAGES,%.3f\n", ctd);
		fflush(m_DataFP);
		m_MessageEnd = 0;
		m_MessageBuffer[0] = '\0';
	}
}

void SGTData::getCalibrationResults(double *Goodness, double *MaxError, double *MeanError)
{
	if (m_RecordingMode == RECORDING_MONOCULAR) {
		Goodness[MONO_X] = m_CalGoodness[MONO_X];
		Goodness[MONO_Y] = m_CalGoodness[MONO_Y];
		MaxError[MONO_1] = m_CalMaxError[MONO_1];
		MeanError[MONO_1] = m_CalMeanError[MONO_1];
	}
	else {
		Goodness[BIN_LX] = m_CalGoodness[BIN_LX];
		Goodness[BIN_LY] = m_CalGoodness[BIN_LY];
		Goodness[BIN_RX] = m_CalGoodness[BIN_RX];
		Goodness[BIN_RY] = m_CalGoodness[BIN_RY];
		MaxError[BIN_L] = m_CalMaxError[BIN_L];
		MaxError[BIN_R] = m_CalMaxError[BIN_R];
		MeanError[BIN_L] = m_CalMeanError[BIN_L];
		MeanError[BIN_R] = m_CalMeanError[BIN_R];
	}
}



void SGTData::getCalibrationResultsDetail(char* errorstr, int size, int* len)
{
	char* dstbuf = errorstr;
	int s = size;
	int idx, l;
	double xy[4];

	for (idx = 0; idx < m_DataCounter; idx++)
	{
		if (m_RecordingMode == RECORDING_MONOCULAR) { //monocular
			getGazePositionMono(m_EyeData[idx], xy);
			l = snprintf(dstbuf, s, "%.0f,%.0f,%.0f,%.0f,", m_CalPointData[idx][0], m_CalPointData[idx][1], xy[MONO_X], xy[MONO_Y]);
		}
		else { //binocular
			getGazePositionBin(m_EyeData[idx], xy);
			l = snprintf(dstbuf, s, "%.0f,%.0f,%.0f,%.0f,%.0f,%.0f,", m_CalPointData[idx][0], m_CalPointData[idx][1], xy[BIN_LX], xy[BIN_LY], xy[BIN_RX], xy[BIN_RY]);
		}
		dstbuf = dstbuf + l;
		s -= l;
		if (s <= 1) break; //check overflow
	}

	*len = size - s;
	if (*len > 0) {
		//Overwrite last comma by '\0'
		errorstr[*len - 1] = '\0';
	}
}

void SGTData::getEyePosition(double* pos, int nSamples)
{
	if (nSamples <= 1)
	{
		if (g_RecordingMode == RECORDING_MONOCULAR) {
			pos[0] = m_CurrentEyeData[MONO_X];
			pos[1] = m_CurrentEyeData[MONO_Y];
			pos[2] = m_CurrentPupilSize[MONO_P];
		}
		else {
			pos[0] = m_CurrentEyeData[BIN_LX];
			pos[1] = m_CurrentEyeData[BIN_LY];
			pos[2] = m_CurrentEyeData[BIN_RX];
			pos[3] = m_CurrentEyeData[BIN_RY];
			pos[4] = m_CurrentPupilSize[BIN_LP];
			pos[5] = m_CurrentPupilSize[BIN_RP];
		}
	}
	else
	{
		double tmppos[4];
		if (g_RecordingMode == RECORDING_MONOCULAR) {
			int index, n = 0;
			pos[0] = pos[1] = pos[2] = 0;
			for (int i = 0; i < nSamples; i++) {
				index = m_DataCounter - 1 - i;
				if (index < 0) break;
				if (m_EyeData[index][MONO_PUPIL_X] > E_FIRST_ERROR_CODE) {
					getGazePositionMono(m_EyeData[index], tmppos); //One must be subtracted from m_DataCounter because it points next address.
					pos[0] += tmppos[MONO_X];
					pos[1] += tmppos[MONO_Y];
					pos[2] += m_PupilSizeData[index][MONO_P];
					n++;
				}
			}
			if (n > 0) {
				pos[0] /= n;
				pos[1] /= n;
				pos[2] /= n;
			}
			else {
				pos[0] = E_NAN_IN_MOVING_AVERAGE;
				pos[1] = E_NAN_IN_MOVING_AVERAGE;
				pos[2] = E_NAN_IN_MOVING_AVERAGE;
			}
		}
		else {
			int index, nl = 0, nr = 0;
			pos[0] = pos[1] = pos[2] = pos[3] = pos[4] = pos[5] = 0;
			for (int i = 0; i < nSamples; i++) {
				index = m_DataCounter - 1 - i;
				if (index < 0) break;
				getGazePositionBin(m_EyeData[index], tmppos); //One must be subtracted from m_DataCounter because it points next address.
				if (m_EyeData[index][BIN_PUPIL_LX] > E_FIRST_ERROR_CODE) {
					pos[0] += tmppos[BIN_LX];
					pos[1] += tmppos[BIN_LY];
					pos[4] += m_PupilSizeData[index][BIN_LP];
					nl++;
				}
				if (m_EyeData[index][BIN_PUPIL_RX] > E_FIRST_ERROR_CODE) {
					pos[2] += tmppos[BIN_RX];
					pos[3] += tmppos[BIN_RY];
					pos[5] += m_PupilSizeData[index][BIN_RP];
					nr++;
				}
			}
			if (nl > 0) {
				pos[0] /= nl;
				pos[1] /= nl;
				pos[4] /= nl;
			}
			else {
				pos[0] /= E_NAN_IN_MOVING_AVERAGE;
				pos[1] /= E_NAN_IN_MOVING_AVERAGE;
				pos[4] /= E_NAN_IN_MOVING_AVERAGE;
			}
			if (nr > 0)
			{
				pos[2] /= nr;
				pos[3] /= nr;
				pos[5] /= nr;
			}
			else {
				pos[2] /= E_NAN_IN_MOVING_AVERAGE;
				pos[3] /= E_NAN_IN_MOVING_AVERAGE;
				pos[5] /= E_NAN_IN_MOVING_AVERAGE;
			}
		}
	}
}



int SGTData::getPreviousEyePositionForward(double* pos, int offset)
{
	if ((m_DataCounter - 1) < offset) { //One must be subtracted from m_DataCounter because it points next address.
		return E_FAIL;
	}
	if (g_RecordingMode == RECORDING_MONOCULAR) {
		pos[0] = m_TickData[offset];
		if (m_EyeData[offset][MONO_X] > E_FIRST_ERROR_CODE) {
			getGazePositionMono(m_EyeData[offset], &pos[1]);
		}
		else {
			pos[1] = m_EyeData[offset][MONO_X];
			pos[2] = m_EyeData[offset][MONO_Y];
		}
		pos[3] = m_PupilSizeData[offset][MONO_P];
	}
	else {
		pos[0] = m_TickData[offset];
		getGazePositionBin(m_EyeData[offset], &pos[1]);
		if (m_EyeData[offset][BIN_LX] <= E_FIRST_ERROR_CODE) {
			pos[1] = m_EyeData[offset][BIN_LX];
			pos[2] = m_EyeData[offset][BIN_LY];
		}
		if (m_EyeData[offset][BIN_RX] <= E_FIRST_ERROR_CODE) {
			pos[3] = m_EyeData[offset][BIN_RX];
			pos[4] = m_EyeData[offset][BIN_RY];
		}
		pos[5] = m_PupilSizeData[offset][BIN_LP];
		pos[6] = m_PupilSizeData[offset][BIN_RP];
	}
	return S_OK;
}


int SGTData::getPreviousEyePositionReverse(double* pos, int offset, bool newDataOnly)
{
	int index = (m_DataCounter - 1) - offset; //One must be subtracted from m_DataCounter because it points next address.

	if (index < 0) {
		return E_FAIL;
	}
	if (newDataOnly && index <= m_LastSentDataCounter) {
		return E_FAIL;
	}
	if (g_RecordingMode == RECORDING_MONOCULAR) {
		pos[0] = m_TickData[index];
		if (m_EyeData[index][MONO_X] > E_FIRST_ERROR_CODE) {
			getGazePositionMono(m_EyeData[index], &pos[1]);
		}
		else {
			pos[1] = m_EyeData[index][MONO_X];
			pos[2] = m_EyeData[index][MONO_Y];
		}
		pos[3] = m_PupilSizeData[index][MONO_P];
	}
	else {
		pos[0] = m_TickData[index];
		getGazePositionBin(m_EyeData[index], &pos[1]);
		if (m_EyeData[index][BIN_LX] <= E_FIRST_ERROR_CODE) {
			pos[1] = m_EyeData[index][BIN_LX];
			pos[2] = m_EyeData[index][BIN_LY];
		}
		if (m_EyeData[index][BIN_RX] <= E_FIRST_ERROR_CODE) {
			pos[3] = m_EyeData[index][BIN_RX];
			pos[4] = m_EyeData[index][BIN_RY];
		}
		pos[5] = m_PupilSizeData[index][BIN_LP];
		pos[6] = m_PupilSizeData[index][BIN_RP];
	}
	return S_OK;
}