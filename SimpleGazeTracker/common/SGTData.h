#pragma once

#include <stdio.h>
#include "SGTCommon.h"
#include "SGTusbIO_UL.h"



class SGTData
{
public:
	SGTData(bool binocular);

	void clearData();
	void clearCalibrationData();
	bool isCalibrated() { return m_bCalibrated; };
	bool isBinocular() {
		if (m_RecordingMode == RECORDING_BINOCULAR)
			return true;
		return false;
	}
	bool isBusy() {
		if (m_State == STATE_FREE)
			return false;
		return true;
	}
	bool isRecording() {
		if (m_State == STATE_RECORDING)
			return true;
		return false;
	}
	bool isCalibratingOrVaridating() {
		if (m_State == STATE_CALIBRATION || m_State == STATE_VALIDATION)
			return true;
		return false;
	}
	void setCalibrationResults();
	void setCalibrationError();
	void insertSettings(char* param);

	void setCalibrationArea(int x1, int y1, int x2, int y2);
	void getCalibrationArea(int* x1, int* y1, int* x2, int* y2);
	int getNumCalPoint(void) { return m_NumCalPoint; }
	int getDataCounter(void) { return m_DataCounter; }
	double* getCalPoint(int index) { return &m_CalPointList[index][0]; }
	double* getEyeData(int index) { return &m_EyeData[index][0]; }
	double* getCalPointData(int index) { return &m_CalPointData[index][0]; }
	double getTickData(int index) { return m_TickData[index]; }
	char* getMessageBuffer() { return m_MessageBuffer; }
	void recordCalSample(double x, double y, int samples);
	void deleteCalibrationDataSubset(char * points);
	void getCalSample(double x, double y, int samples);

	int openDataFile(char* filename, int overwrite);
	int closeDataFile();
	void estimateParametersMono();
	void estimateParametersBin();
	void saveCalValResultsDetail(void);
	void insertMessage(char * message);
	void getCalibrationResults(double * Goodness, double * MaxError, double * MeanError);
	void getCalibrationResultsDetail(char * errorstr, int size, int * len);
	void getEyePosition(double * pos, int nSamples);
	int getPreviousEyePositionForward(double * pos, int offset);
	int getPreviousEyePositionReverse(double * pos, int offset, bool newDataOnly);
	void updateLastSentDataCounter() { m_LastSentDataCounter = m_DataCounter - 1; }
	void flushGazeData(void);

	int startRecording(const char* message);
	int stopRecording(const char* message);
	void startMeasurement();
	void stopMeasurement();
	void startCalibration();
	void finishCalibration();
	void finishValidation();

	void getGazePositionMono(double * im, double * xy);
	void getGazePositionBin(double * im, double * xy);
	void recordGazeData(double time, double detectionResults[8]);
	void recordCalibrationData(double detectionResults[8]);
	void prepareForNextData();

	void setUSBIO(SGTusbIO* usbIO);
	void recordUSBIOData();

	void recordCameraSpecificData();


private:
	FILE* m_DataFP = nullptr;
	SGTusbIO* m_pUSBIO;

	double m_EyeData[MAXDATA][4]; /*!< Holds the center of purkinje image relative to the center of pupil. Only two columns are used when recording mode is monocular.*/
	double m_PupilSizeData[MAXDATA][2]; /*!< Holds pupil size*/
	double m_TickData[MAXDATA]; /*!< Holids tickcount when data was obtained. */
	double m_CalPointData[MAXCALDATA][2]; /*!< Holds where the calibration item is presented when calibration data is sampled.*/
	bool m_CalPointDelList[MAXCALDATA];
	double m_ParamX[6]; /*!< Holds calibration parameters for X coordinate. Only three elements are used when recording mode is monocular.*/
	double m_ParamY[6]; /*!< Holds calibration parameters for Y coordinate. Only three elements are used when recording mode is monocular.*/
	double m_CalibrationArea[4]; /*!< Holds calibration area. These values are used when calibration results are rendered.*/
	unsigned int m_CameraSpecificData[MAXDATA]; /*!< Holds camera-specific data*/

	double m_CurrentEyeData[4]; /*!< Holds latest data. Only two elements are used when recording mode is monocular.*/
	double m_CurrentPupilSize[2]; /*!< Holds latest data. Only one element is used when recording mode is monocular.*/
	double m_CurrentCalPoint[2]; /*!< Holds current position of the calibration target. */
	int m_NumCalPoint; /*!< Sum of the number of sampled calibration data.*/
	int m_CalSamplesAtCurrentPoint; /*!< Number of calibdation data to be sampled at the current target position.*/

	double m_CalGoodness[4]; /*!< Holds goodness of calibration results, defined as a ratio of linear regression coefficients to screen size. Only two elements are used when recording mode is monocular.*/
	double m_CalMaxError[2]; /*!< Holds maximum calibration error. Only one element is used when recording mode is monocular.*/
	double m_CalMeanError[2]; /*!< Holds mean calibration error. Only one element is used when recording mode is monocular.*/

	double m_LastCalPointList[MAXCALPOINT][2];
	int m_LastNumCalPoint = 0;

	int m_lastCalValType = TYPE_CALIBRATION;

	double m_CalPointList[MAXCALPOINT][2];
	double m_CalPointPrecision[MAXCALPOINT][4];
	double m_CalPointAccuracy[MAXCALPOINT][4];

	int m_DataCounter = 0;
	int m_MessageEnd = 0;
	double m_RecStartTime;
	char m_MessageBuffer[MAXMESSAGE];
	bool m_bCalibrated = false;
	int m_State = STATE_FREE;
	int m_RecordingMode = RECORDING_MONOCULAR;
	int m_LastSentDataCounter = 0;

};

