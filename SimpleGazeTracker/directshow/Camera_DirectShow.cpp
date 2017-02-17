/*!
@file Camera_DirectShow.cpp
@author Hiroyuki Sogo
@copyright GNU General Public License (GPL) version 3.
@brief Camera-dependent procedures are defined.

@date 2017/01/17
- Created.
*/

#include "GazeTracker.h"

#include <fstream>
#include <string>

#include <SDL2/SDL.h>

#include <opencv2/highgui/highgui.hpp>
#include <opencv2/opencv.hpp>
#include <opencv2/core/core.hpp>

#include <dshow.h>
#include <wmsdkidl.h>

#define DSC_VPAMPMAX		10
#define DSC_CAMCTLMAX		7
#define DSC_ITEMMAX			(DSC_VPAMPMAX+DSC_CAMCTLMAX)
#define DSC_RUN_TIMEOUT		3000
#define DSC_STOP_TIMEOUT	3000
#define release(x) {if(x)x->Release();x=0;}



EXTERN_C const IID IID_ISampleGrabberCB;
MIDL_INTERFACE("0579154A-2B53-4994-B0D0-E773148EFF85")
ISampleGrabberCB : public IUnknown
{
public:
	virtual HRESULT STDMETHODCALLTYPE SampleCB(
		double SampleTime,
		IMediaSample *pSample) = 0;

	virtual HRESULT STDMETHODCALLTYPE BufferCB(
		double SampleTime,
		BYTE *pBuffer,
		long BufferLen) = 0;

};

EXTERN_C const CLSID CLSID_SampleGrabber;
class DECLSPEC_UUID("C1F400A0-3F08-11d3-9F0B-006008039E37")
	SampleGrabber;


EXTERN_C const IID IID_ISampleGrabber;
MIDL_INTERFACE("6B652FFF-11FE-4fce-92AD-0266B5D7C78F")
ISampleGrabber : public IUnknown
{
public:
	virtual HRESULT STDMETHODCALLTYPE SetOneShot(
		BOOL OneShot) = 0;

	virtual HRESULT STDMETHODCALLTYPE SetMediaType(
		const AM_MEDIA_TYPE *pType) = 0;

	virtual HRESULT STDMETHODCALLTYPE GetConnectedMediaType(
		AM_MEDIA_TYPE *pType) = 0;

	virtual HRESULT STDMETHODCALLTYPE SetBufferSamples(
		BOOL BufferThem) = 0;

	virtual HRESULT STDMETHODCALLTYPE GetCurrentBuffer(
		/* [out][in] */ long *pBufferSize,
		/* [out] */ long *pBuffer) = 0;

	virtual HRESULT STDMETHODCALLTYPE GetCurrentSample(
		/* [retval][out] */ IMediaSample **ppSample) = 0;

	virtual HRESULT STDMETHODCALLTYPE SetCallback(
		ISampleGrabberCB *pCallback,
		long WhichMethodToCallback) = 0;

};



struct DirectShowCamera{
	int width;				//camera width
	int height;				//camera height
	double fps;				//frame rate
	GUID mstype;			//output format
	GUID dev_mstype;		//device output pin format
	int *pbuf;				//buffer
	int *buffer;			//latest image frame
	volatile long bufsize;	//image size
	int vflag[DSC_ITEMMAX];
	IGraphBuilder *pGraph;
	IBaseFilter *pF;
	ISampleGrabber *pGrab;
	ICaptureGraphBuilder2 *pBuilder;
	IBaseFilter *pCap;
	IAMVideoProcAmp *pVPAmp;
	IAMCameraControl *pCamCtl;
	IMediaControl *pMediaControl;
	IAMStreamConfig *pConfig;
	IMoniker *pMoniker;
	IEnumMoniker *pEnum;
	ICreateDevEnum *pDevEnum;
	AM_MEDIA_TYPE *pmt;
	AM_MEDIA_TYPE mt;
	IPin *pSrcOut;
	IPin *pSGrabIn;
	IMediaEvent *pMediaEvent;
};

DirectShowCamera g_DirectShowCamera;

class ImageGrabberCB :public ISampleGrabberCB
{
public:
	STDMETHODIMP_(ULONG) AddRef()
	{
		return 2;
	}
	STDMETHODIMP_(ULONG) Release()
	{
		return 1;
	}
	STDMETHODIMP QueryInterface(REFIID riid, void ** ppv)
	{
		if (riid == IID_ISampleGrabberCB || riid == IID_IUnknown){
			*ppv = (void *)static_cast<ISampleGrabberCB*>(this);
			return NOERROR;
		}
		return E_NOINTERFACE;
	}
	STDMETHODIMP SampleCB(double SampleTime, IMediaSample *pSample)
	{
		return S_OK;
	}
	//callback function
	STDMETHODIMP BufferCB(double dblSampleTime, BYTE *pBuffer, long lBufferSize)
	{
		g_DirectShowCamera.bufsize = lBufferSize;
		int wx = g_DirectShowCamera.width;
		int wy = g_DirectShowCamera.height;
		int byte = lBufferSize / wy;
		//flip image and copy
		for (int y = 0; y<wy; y++){
			memcpy((unsigned char *)g_DirectShowCamera.pbuf + (wy - 1 - y)*byte, pBuffer + y*byte, byte);
		}
		internal_count++;
		return S_OK;
	}
	//constructor
	ImageGrabberCB()
	{
		g_DirectShowCamera.pbuf = g_DirectShowCamera.buffer;
		g_DirectShowCamera.bufsize = 0;
		internal_count = 0;
		prev_count = 0;
	}
	//destructor
	~ImageGrabberCB()
	{
	}
	int IsCaptured(void)
	{
		if (prev_count != internal_count)
		{
			prev_count = internal_count;
			return 1;
		}
		else return 0;
	}
private:
	int i;
	unsigned int internal_count;
	unsigned int prev_count;
};

ImageGrabberCB *g_pImageGrabberCB;

double g_FrameRate = 30;
bool g_isThreadMode = false;

cv::Mat g_OriginalImage;

#define CAMERA_PARAM_ID          0
#define CAMERA_PARAM_FRAMERATE   1
#define CAMERA_PARAM_NUM         2

bool g_isParameterSpecified[CAMERA_PARAM_NUM] = { false, false};

volatile bool g_NewFrameAvailable = false; /*!< True if new camera frame is grabbed. @note This function is necessary when you customize this file for your camera.*/


/*!
getEditionString: Get edition string.

@return edition string.

@date 2012/07/30 created.
*/
const char* getEditionString(void)
{
	return EDITION;
}


/*!
initCamera: Initialize camera.

Read parameters from the configuration file, start camera and set callback function.
@attention If there are custom camera menu items, number of custom menu items must be set to g_CustomMenuNum in this function.

@return int
@retval S_OK Camera is successfully initialized.
@retval E_FAIL Initialization is failed.
@note This function is necessary when you customize this file for your camera.
@todo check whether number of custom menus are too many.

@date 2012/11/05
- Section header [SimpleGazeTrackerOpenCV] is supported.
- spaces and tabs around '=' are removed.
@date 2013/03/15
- Argument "ParamPath" was removed. Use g_ParamPath instead.
@date 2013/10/23
- Camera configuration file is customizable.
*/
int initCamera(void)
{
	std::fstream fs;
	std::string fname;
	char *p, *pp;
	char buff[1024];
	double param;
	bool isInSection = true; //default is True to support old config file

	int cameraID = 0;

	fname = g_ParamPath.c_str();
	fname.append(PATH_SEPARATOR);
	if (g_CameraConfigFileName == ""){
		g_CameraConfigFileName = CAMERA_CONFIG_FILE;
		checkAndCopyFile(g_ParamPath, CAMERA_CONFIG_FILE, g_AppDirPath);
	}
	fname.append(g_CameraConfigFileName.c_str());

	fs.open(fname.c_str(), std::ios::in);
	if (fs.is_open())
	{
		g_LogFS << "Open camera configuration file (" << fname << ")" << std::endl;
		while (fs.getline(buff, sizeof(buff) - 1))
		{
			if (buff[0] == '#') continue;

			//in Section "[SimpleGazeTrackerOpenCV]"
			if (buff[0] == '['){
				if (strcmp(buff, "[SimpleGazeTrackerDirectShow]") == 0){
					isInSection = true;
				}
				else
				{
					isInSection = false;
				}
				continue;
			}

			if (!isInSection) continue; //not in section


			//Check options.
			//If "=" is not included, this line is not option.
			if ((p = strchr(buff, '=')) == NULL) continue;

			//remove space/tab
			*p = '\0';
			while (*(p - 1) == 0x09 || *(p - 1) == 0x20)
			{
				p--;
				*p = '\0';
			}
			while (*(p + 1) == 0x09 || *(p + 1) == 0x20) p++;
			param = strtod(p + 1, &pp); //paramete is not int but double

			if (strcmp(buff, "CAMERA_ID") == 0)
			{
				cameraID = (int)param;
			}
			else if (strcmp(buff, "FRAME_RATE") == 0)
			{
				g_FrameRate = param;
				g_isParameterSpecified[CAMERA_PARAM_FRAMERATE] = true;
			}
		}
		fs.close();
	}
	else{
		snprintf(g_errorMessage, sizeof(g_errorMessage), "Failed to open camera configuration file (%s)", fname.c_str());
		g_LogFS << "ERROR: failed to open camera configuration file (" << fname << ")" << std::endl;
		return E_FAIL;
	}

	// set Camera Image size to DSC
	g_DirectShowCamera.width = g_CameraWidth;
	g_DirectShowCamera.height = g_CameraHeight;
	g_DirectShowCamera.fps = g_FrameRate;
	g_DirectShowCamera.mstype = MEDIASUBTYPE_RGB24;
	g_DirectShowCamera.dev_mstype = GUID_NULL;

	// Initialize DirectShow camera
	HRESULT hr;
	ULONG cFetched;

	hr = CoCreateInstance(CLSID_FilterGraph, 0, CLSCTX_INPROC_SERVER, IID_IGraphBuilder, (void **)&g_DirectShowCamera.pGraph);
	hr = CoCreateInstance(CLSID_SystemDeviceEnum, 0, CLSCTX_INPROC_SERVER, IID_ICreateDevEnum, (void **)&g_DirectShowCamera.pDevEnum);
	if (hr != S_OK)	{
		snprintf(g_errorMessage, sizeof(g_errorMessage), "Failed to initialize DirectShow camera interface (No DirectShow camera is connected?).");
		g_LogFS << "ERROR: failed to initialize DirectShow camera interface." << std::endl;
		return E_FAIL;
	}
	hr = g_DirectShowCamera.pDevEnum->CreateClassEnumerator(CLSID_VideoInputDeviceCategory, &g_DirectShowCamera.pEnum, 0);
	if (hr != S_OK){
		snprintf(g_errorMessage, sizeof(g_errorMessage), "Failed to initialize DirectShow camera interface (No DirectShow camera is connected?).");
		g_LogFS << "ERROR: failed to initialize DirectShow camera interface." << std::endl;
		return E_FAIL;
	}

	for (int i = 0; i <= cameraID; i++)
	{
		hr = g_DirectShowCamera.pEnum->Next(1, &g_DirectShowCamera.pMoniker, &cFetched);
	}

	if (hr == S_OK){
		LPOLESTR strMonikerName = 0;
		hr = g_DirectShowCamera.pMoniker->GetDisplayName(NULL, NULL, &strMonikerName);
		if (hr != S_OK){
			snprintf(g_errorMessage, sizeof(g_errorMessage), "Failed to initialize DirectShow Camera");
			g_LogFS << "ERROR: failed to get Camera's moniker name." << std::endl;
			return E_FAIL;
		}

		int cntflag = 0;
		if (wcsstr(strMonikerName, L"@device:pnp") != NULL) cntflag = 1;	//'@device:pnp' is included
		if (wcsstr(strMonikerName, L"@device:sw") != NULL) cntflag = 1;	//'@device:sw' is included

		if (cntflag){
			// initialize pCap
			g_DirectShowCamera.pMoniker->BindToObject(0, 0, IID_IBaseFilter, (void **)&g_DirectShowCamera.pCap);
			// add filter to graph
			hr = g_DirectShowCamera.pGraph->AddFilter(g_DirectShowCamera.pCap, L"Video Capture 0");
			if (hr != S_OK){ 
				snprintf(g_errorMessage, sizeof(g_errorMessage), "Failed to initialize DirectShow Camera");
				g_LogFS << "ERROR: failed to add Camera." << std::endl;
				return E_FAIL;
			}
		}
		release(g_DirectShowCamera.pMoniker);
	}
	else{
		snprintf(g_errorMessage, sizeof(g_errorMessage), "Could not open Camera #%d.", cameraID);
		g_LogFS << "ERROR: could not open Camera #" << cameraID << "." << std::endl;
		return E_FAIL;
	}

	// create pBuilder
	CoCreateInstance(CLSID_CaptureGraphBuilder2, 0, CLSCTX_INPROC_SERVER,
		IID_ICaptureGraphBuilder2, (void **)&g_DirectShowCamera.pBuilder);
	hr = g_DirectShowCamera.pBuilder->SetFiltergraph(g_DirectShowCamera.pGraph);
	if (hr != S_OK){
		snprintf(g_errorMessage, sizeof(g_errorMessage), "Failed to initialize DirectShow Camera");
		g_LogFS << "ERROR: failed to set Capture Graph Builder." << std::endl;
		return E_FAIL;
	}

	// get IAMStreamConfig interface
	hr = g_DirectShowCamera.pBuilder->FindInterface(&PIN_CATEGORY_CAPTURE, &MEDIATYPE_Video,
		g_DirectShowCamera.pCap, IID_IAMStreamConfig, (void**)&g_DirectShowCamera.pConfig);
	if (hr != S_OK){
		snprintf(g_errorMessage, sizeof(g_errorMessage), "Failed to initialize DirectShow Camera");
		g_LogFS << "ERROR: failed to get IAMStreamConfig interface." << std::endl;
		return E_FAIL;
	}

	// set camera image size and fps
	hr = g_DirectShowCamera.pConfig->GetFormat(&g_DirectShowCamera.pmt);
	VIDEOINFOHEADER *vh = (VIDEOINFOHEADER*)g_DirectShowCamera.pmt->pbFormat;
	vh->bmiHeader.biWidth = g_DirectShowCamera.width;
	vh->bmiHeader.biHeight = g_DirectShowCamera.height;
	vh->AvgTimePerFrame = (LONGLONG)floor((10000000.0 / g_DirectShowCamera.fps + 0.5));
	LONGLONG targetAvgTimePerFrame = vh->AvgTimePerFrame;

	// get device output pin format
	if (g_DirectShowCamera.dev_mstype != GUID_NULL){
		g_DirectShowCamera.pmt->subtype = g_DirectShowCamera.dev_mstype;
	}
	g_DirectShowCamera.dev_mstype = g_DirectShowCamera.pmt->subtype;

	hr = g_DirectShowCamera.pConfig->SetFormat(g_DirectShowCamera.pmt);
	if (hr != S_OK){
		snprintf(g_errorMessage, sizeof(g_errorMessage), "Failed to set camera format (%dx%d @%.2ffps).", g_DirectShowCamera.width, g_DirectShowCamera.height, g_DirectShowCamera.fps);
		g_LogFS << "ERROR: failed to set camera format (" << g_DirectShowCamera.width << "x" << g_DirectShowCamera.height << " @" << g_DirectShowCamera.fps << "fps)." << std::endl;
		return E_FAIL;
	}
	hr = g_DirectShowCamera.pConfig->GetFormat(&g_DirectShowCamera.pmt);
	vh = (VIDEOINFOHEADER*)g_DirectShowCamera.pmt->pbFormat;
	if (vh->bmiHeader.biWidth != g_DirectShowCamera.width || vh->bmiHeader.biHeight != g_DirectShowCamera.height || vh->AvgTimePerFrame != targetAvgTimePerFrame)
	{
		snprintf(g_errorMessage, sizeof(g_errorMessage), "Failed to set camera format (%dx%d @%.2ffps).", g_DirectShowCamera.width, g_DirectShowCamera.height, g_DirectShowCamera.fps);
		g_LogFS << "ERROR: failed to set camera format (" << g_DirectShowCamera.width << "x" << g_DirectShowCamera.height << " @" << g_DirectShowCamera.fps << "fps)." << std::endl;
		return E_FAIL;
	}
	release(g_DirectShowCamera.pConfig);

	// create sample grabber pF,pGrab
	CoCreateInstance(CLSID_SampleGrabber, 0, CLSCTX_INPROC_SERVER, IID_IBaseFilter, (LPVOID *)&g_DirectShowCamera.pF);
	hr = g_DirectShowCamera.pF->QueryInterface(IID_ISampleGrabber, (void **)&g_DirectShowCamera.pGrab);
	if (hr != S_OK){
		snprintf(g_errorMessage, sizeof(g_errorMessage), "Failed to initialize DirectShow Camera");
		g_LogFS << "ERROR: failed to get SampleGrabber interface." << std::endl;
		return E_FAIL;
	}

	// set media type
	ZeroMemory(&g_DirectShowCamera.mt, sizeof(AM_MEDIA_TYPE));
	g_DirectShowCamera.mt.majortype = MEDIATYPE_Video;
	g_DirectShowCamera.mt.subtype = g_DirectShowCamera.mstype;
	g_DirectShowCamera.mt.formattype = FORMAT_VideoInfo;
	hr = g_DirectShowCamera.pGrab->SetMediaType(&g_DirectShowCamera.mt);
	if (hr != S_OK){
		snprintf(g_errorMessage, sizeof(g_errorMessage), "Failed to initialize DirectShow Camera");
		g_LogFS << "ERROR: failed to set media type." << std::endl;
		return E_FAIL;
	}
	// add filter to grabber
	hr = g_DirectShowCamera.pGraph->AddFilter(g_DirectShowCamera.pF, L"Grabber 1");
	if (hr != S_OK){
		snprintf(g_errorMessage, sizeof(g_errorMessage), "Failed to initialize DirectShow Camera");
		g_LogFS << "ERROR: failed to add filter." << std::endl;
		return E_FAIL;
	}

	// connecting sample grabber
	// get pin
	IEnumPins *pEnum;
	PIN_DIRECTION PinDirThis;
	g_DirectShowCamera.pCap->EnumPins(&pEnum);
	while (pEnum->Next(1, &(g_DirectShowCamera.pSrcOut), 0) == S_OK){
		g_DirectShowCamera.pSrcOut->QueryDirection(&PinDirThis);
		if (PinDirThis == PINDIR_OUTPUT) break;
		g_DirectShowCamera.pSrcOut->Release();
	}
	pEnum->Release();

	g_DirectShowCamera.pF->EnumPins(&pEnum);
	while (pEnum->Next(1, &(g_DirectShowCamera.pSGrabIn), 0) == S_OK){
		g_DirectShowCamera.pSGrabIn->QueryDirection(&PinDirThis);
		if (PinDirThis == PINDIR_INPUT) break;
		g_DirectShowCamera.pSGrabIn->Release();
	}
	pEnum->Release();

	// connect pins
	hr = g_DirectShowCamera.pGraph->Connect(g_DirectShowCamera.pSrcOut, g_DirectShowCamera.pSGrabIn);
	if (hr != S_OK){
		snprintf(g_errorMessage, sizeof(g_errorMessage), "Failed to initialize DirectShow Camera");
		g_LogFS << "ERROR: failed to connect pins." << std::endl;
		return E_FAIL;
	}

	release(g_DirectShowCamera.pSrcOut);
	release(g_DirectShowCamera.pSGrabIn);

	// set grabber mode
	hr = g_DirectShowCamera.pGrab->SetBufferSamples(FALSE);
	if (hr != S_OK){
		snprintf(g_errorMessage, sizeof(g_errorMessage), "Failed to initialize DirectShow Camera");
		g_LogFS << "ERROR: failed to set buffer samples." << std::endl;
		return E_FAIL;
	}
	hr = g_DirectShowCamera.pGrab->SetOneShot(FALSE);
	if (hr != S_OK){
		snprintf(g_errorMessage, sizeof(g_errorMessage), "Failed to initialize DirectShow Camera");
		g_LogFS << "ERROR: failed to set one shot." << std::endl;
		return E_FAIL;
	}

	// create buffer, register dsc_pSampleGrabberCB[]
	g_DirectShowCamera.buffer = (int *)new int[g_DirectShowCamera.width*g_DirectShowCamera.height];
	g_OriginalImage = cv::Mat(g_CameraHeight, g_CameraWidth, CV_8UC3, g_DirectShowCamera.buffer);
	g_pImageGrabberCB = new ImageGrabberCB();
	hr = g_DirectShowCamera.pGrab->SetCallback(g_pImageGrabberCB, 1);
	if (hr != S_OK){
		snprintf(g_errorMessage, sizeof(g_errorMessage), "Failed to initialize DirectShow Camera");
		g_LogFS << "ERROR: failed to set callback function for ImageGrabber." << std::endl;
		return E_FAIL;
	}

	// get IAMVideoProcAmp
	hr = g_DirectShowCamera.pCap->QueryInterface(IID_IAMVideoProcAmp, (void **)&g_DirectShowCamera.pVPAmp);
	if (hr != S_OK){
		for (int j = 0; j<DSC_VPAMPMAX; j++){
			//not supported
			g_DirectShowCamera.vflag[j] = 0;
		}
	}
	else{
		for (int j = 0; j<DSC_VPAMPMAX; j++){
			long Min, Max, Step, Default, Flags;
			hr = g_DirectShowCamera.pVPAmp->GetRange(j, &Min, &Max, &Step, &Default, &Flags);
			if (hr == S_OK){
				g_DirectShowCamera.vflag[j] = 1;
			}
			else{
				//not supported
				g_DirectShowCamera.vflag[j] = 0;
			}
		}
	}
	release(g_DirectShowCamera.pVPAmp);

	// get IAMCameraControl
	hr = g_DirectShowCamera.pCap->QueryInterface(IID_IAMCameraControl, (void **)&g_DirectShowCamera.pCamCtl);
	if (hr != S_OK){
		for (int j = 0; j<DSC_CAMCTLMAX; j++){
			//not supported
			g_DirectShowCamera.vflag[j + DSC_VPAMPMAX] = 0;
		}
	}
	else{
		for (int j = 0; j<DSC_CAMCTLMAX; j++){
			long Min, Max, Step, Default, Flags;
			hr = g_DirectShowCamera.pCamCtl->GetRange(j, &Min, &Max, &Step, &Default, &Flags);
			if (hr == S_OK){
				g_DirectShowCamera.vflag[j + DSC_VPAMPMAX] = 1;
			}
			else{
				//not supported
				g_DirectShowCamera.vflag[j + DSC_VPAMPMAX] = 0;
			}
		}
	}
	release(g_DirectShowCamera.pCamCtl);

	//get IMediaEvent
	hr = g_DirectShowCamera.pGraph->QueryInterface(IID_IMediaEvent, (LPVOID *)&g_DirectShowCamera.pMediaEvent);
	if (hr != S_OK){
		snprintf(g_errorMessage, sizeof(g_errorMessage), "Failed to initialize DirectShow Camera");
		g_LogFS << "ERROR: failed to get MediaEvent interface." << std::endl;
		return E_FAIL;
	}

	// start capture
	hr = g_DirectShowCamera.pGraph->QueryInterface(IID_IMediaControl, (void **)&g_DirectShowCamera.pMediaControl);
	if (hr != S_OK){
		snprintf(g_errorMessage, sizeof(g_errorMessage), "Failed to initialize DirectShow Camera");
		g_LogFS << "ERROR: failed to get MediaControl interface." << std::endl;
		return E_FAIL;
	}
	hr = g_DirectShowCamera.pMediaControl->Run();
	if (hr != S_OK){
		snprintf(g_errorMessage, sizeof(g_errorMessage), "Failed to run camera.");
		g_LogFS << "ERROR: failed to run camera." << std::endl;
		return E_FAIL;
	}
	release(g_DirectShowCamera.pMediaControl);

	// wait for sample
	long evCode;
	g_DirectShowCamera.pMediaEvent->WaitForCompletion(DSC_RUN_TIMEOUT, &evCode);
	int t0 = GetTickCount();
	do{
		if ((GetTickCount() - t0) > DSC_RUN_TIMEOUT)
		{
			snprintf(g_errorMessage, sizeof(g_errorMessage), "Failed to run camera.");
			g_LogFS << "ERROR: failed to run camera." << std::endl;
			return E_FAIL;
		}
	} while (g_DirectShowCamera.bufsize == 0);

	g_LogFS << "Start" << std::endl;

	return S_OK;
}

/*!
getCameraImage: Get new camera image.

@return int
@retval S_OK New frame is available.
@retval E_FAIL There is no new frame.
@note This function is necessary when you customize this file for your camera.
*/
int getCameraImage(void)
{
	cv::Mat monoFrame;

	if (g_pImageGrabberCB->IsCaptured())
	{
		cv::cvtColor(g_OriginalImage, monoFrame, CV_RGB2GRAY);
		for (int idx = 0; idx<g_CameraWidth*g_CameraHeight; idx++)
		{
			g_frameBuffer[idx] = (unsigned char)monoFrame.data[idx];
		}
		return S_OK;
	}

	return E_FAIL;
}

/*!
cleanupCamera: release camera resources.

@return No value is returned.

@note This function is necessary when you customize this file for your camera.
*/
void cleanupCamera()
{
	HRESULT hr;
	long evCode;

	hr = g_DirectShowCamera.pGraph->QueryInterface(IID_IMediaControl, (void **)&g_DirectShowCamera.pMediaControl);
	//if (hr == S_OK) g_DirectShowCamera.pMediaControl->Stop(); else return 2;
	g_DirectShowCamera.pMediaControl->Stop();
	release(g_DirectShowCamera.pMediaControl);

	hr = g_DirectShowCamera.pMediaEvent->WaitForCompletion(DSC_STOP_TIMEOUT, &evCode);
	//if (hr != S_OK){
	//	if (hr == E_ABORT) return 3;
	//}

	release(g_DirectShowCamera.pMediaEvent);
	release(g_DirectShowCamera.pMediaControl);
	release(g_DirectShowCamera.pCamCtl);
	release(g_DirectShowCamera.pVPAmp);
	release(g_DirectShowCamera.pGrab);
	release(g_DirectShowCamera.pF);
	release(g_DirectShowCamera.pBuilder);
	release(g_DirectShowCamera.pCap);
	if (g_DirectShowCamera.buffer){
		delete[] g_DirectShowCamera.buffer;
		g_DirectShowCamera.buffer = 0;
	}
	release(g_DirectShowCamera.pGraph);
	if (g_pImageGrabberCB){
		delete g_pImageGrabberCB;
		g_pImageGrabberCB = 0;
	}
	CoUninitialize();
}

/*!
saveCameraParameters: Save current camera parameters to the camera configuration file.

@param[in] ParamPath Path to the camera configuration file.
@return No value is returned.
@note This function is necessary when you customize this file for your camera.

@date 2013/03/15
- Argument "ParamPath" was removed. Use g_ParamPath instead.
*/
void saveCameraParameters(void)
{
	// no custom parameters for this camera
	return;
}

/*!
customCameraMenu: Process camera-dependent custom menu items. If there is no custom menu items, this function do nothing.

Your camera may have some parameters which you want to adjust with previewing camera image.
In such cases, write nesessary codes to adjust these parameters in this function.
This function is called when left or right cursor key is pressed.

@param[in] SDLevent Event object.
@param[in] currentMenuPosition Current menu position.
@return int
@retval S_OK
@retval E_FAIL
@note This function is necessary when you customize this file for your camera.
*/
int customCameraMenu(SDL_Event* SDLevent, int currentMenuPosition)
{
	// no custom menu for this camera
	return S_OK;
}


/*!
updateCustomMenuText: update menu text of custom camera menu items.

Your camera may have some parameters which you want to adjust with previewing camera image.
If your custom menu need to update its text, write nessesary codes to update text in this function.
This function is called from initD3D() at first, and from MsgProc() when left or right cursor key is pressed.

@return No value is returned.
@note This function is necessary when you customize this file for your camera.
*/
void updateCustomMenuText(void)
{
	// no custom parameters for this camera
	return;
}


/*!
getCameraSpecificData: return Camera specific data.

If your camera has input port, you can insert its value to the SimpleGazeTracker data file
using this function. Currently, only single value (unsigned int) can be returned.

@date 2013/05/27 created.
*/
unsigned int getCameraSpecificData(void)
{
	//no custom input
	return 0;
}
