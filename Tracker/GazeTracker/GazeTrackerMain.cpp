/*!
@file GazeTrackerMain.cpp
@author Hiroyuki Sogo
@copyright GNU General Public License (GPL) version 3.

@brief Main part of GazeParser.Tracker application.

@date 2012/03/23
- Custom menu is supported.
 */

#include <d3d9.h>
#include <D3dx9tex.h>

#include <atlbase.h>
#include <time.h>
#include <process.h>

#include "GazeTracker.h"
#include "resource.h"

#define FVF_CUSTOM ( D3DFVF_XYZRHW | D3DFVF_DIFFUSE | D3DFVF_TEX1 )

struct CUSTOMVERTEX{
   float x, y, z;
   float rhw;
   DWORD dwColor; 
   float u, v;
}; 

#define MARKER_SIZE_HALF 5
#define CURSOR_SIZE_HALF 5
#define MENU_ITEM_HEIGHT 24
#define MENU_FONT_SIZE 20

#define PANEL_WIDTH  256
#define PANEL_HEIGHT 256

#define INITMESSAGE_SUCCESS_ALL		1000
#define INITMESSAGE_FAIL_INIT		1001
#define INITMESSAGE_SUCCESS_INIT	1002
#define INITMESSAGE_FAIL_SOCK		1003
#define INITMESSAGE_SUCCESS_SOCK	1004
#define INITMESSAGE_FAIL_D3D		1005
#define INITMESSAGE_SUCCESS_D3D		1006
#define INITMESSAGE_FAIL_CAMERA		1007
#define INITMESSAGE_SUCCESS_CAMERA	1008
#define INITMESSAGE_FAIL_BUFFER		1009
#define INITMESSAGE_SUCCESS_BUFFER	1010

/*! Holds menu texts. 
@attention Number of menu items (sum of original items and custom items) and 
length of custom menu texts must be smaller than MENU_MAX_ITEMS and MENU_STRING_MAX, respectively.
*/
TCHAR g_MenuString[MENU_MAX_ITEMS][MENU_STRING_MAX]; 

LPDIRECT3D9         g_pD3D = NULL;
LPDIRECT3DDEVICE9   g_pd3dDevice = NULL;

unsigned char* g_frameBuffer;
int* g_pCameraTextureBuffer;
int* g_pCalResultTextureBuffer;
int g_CameraWidth;
int g_CameraHeight;
int g_PreviewWidth;
int g_PreviewHeight;
int g_ROIWidth;
int g_ROIHeight;

int g_Threshold = 55;  /*!< Pupil candidates are sought from image areas darker than this value. */
int g_MaxPoints = 500; /*!< Dark areas whose contour is longer than this value is removed from pupil candidates. */
int g_MinPoints = 200; /*!< Dark areas whose contour is shorter than this value is removed from pupil candidates. */
int g_PurkinjeThreshold = 240;  /*!<  */
int g_PurkinjeSearchArea = 60;  /*!<  */
int g_PurkinjeExcludeArea = 20; /*!<  */

IDirect3DVertexBuffer9* g_pCursorVertex;
IDirect3DVertexBuffer9* g_pGazeMarkerVertex;
IDirect3DVertexBuffer9* g_pCameraTextureVertex;
IDirect3DVertexBuffer9* g_pPanelTextureVertex;
IDirect3DTexture9* g_pCameraTexture;
IDirect3DTexture9* g_pPanelTexture;
IDirect3DTexture9* g_pCalResultTexture;

bool g_isShowingCameraImage = true; /*!< If true, camera image is rendered. This must be false while recording.*/
HANDLE g_hThread; /*!< @deprecated*/
unsigned g_threadID; /*!< @deprecated*/

char g_ParamPath[512]; /*!< Holds path to the parameter file directory*/
char g_DataPath[512];  /*!< Holds path to the data file directory*/

int g_CurrentMenuPosition = 0;  /*!< Holds current menu position.*/
int g_CustomMenuNum = 0; /*!< Holds how many custom menu items are defined.*/

double g_EyeData[MAXDATA][4]; /*!< Holds the center of purkinje image relative to the center of pupil. Only two columns are used when recording mode is monocular.*/
double g_TickData[MAXDATA]; /*!< Holids tickcount when data was obtained. */
double g_CalPointData[MAXCALDATA][2]; /*!< Holds where the calibration item is presented when calibration data is sampled.*/
double g_ParamX[6]; /*!< Holds calibration parameters for X coordinate. Only three elements are used when recording mode is monocular.*/
double g_ParamY[6]; /*!< Holds calibration parameters for Y coordinate. Only three elements are used when recording mode is monocular.*/
RECT g_CalibrationArea; /*!< Holds calibration area. These values are used when calibration results are rendered.*/

double g_CurrentEyeData[4]; /*!< Holds latest data. Only two elements are used when recording mode is monocular.*/
double g_CurrentCalPoint[2]; /*!< Holds current position of the calibration target. */
int g_NumCalPoint; /*!< Sum of the number of sampled calibration data.*/
int g_CalSamplesAtCurrentPoint; /*!< Number of calibdation data to be sampled at the current target position.*/

double g_CalGoodness[4]; /*!< Holds goodness of calibration results, defined as a ratio of linear regression coefficients to screen size. Only two elements are used when recording mode is monocular.*/
double g_CalMaxError[2]; /*!< Holds maximum calibration error. Only one element is used when recording mode is monocular.*/
double g_CalMeanError[2]; /*!< Holds mean calibration error. Only one element is used when recording mode is monocular.*/

int g_RecordingMode = RECORDING_BINOCULAR; /*! Holds recording mode. @note This value is modified only when application is being initialized (i.e. in initParam()).*/

int g_DataCounter = 0;
bool g_isRecording = false;
bool g_isCalibrating = false;
bool g_isValidating = false;
bool g_isCalibrated = false;
bool g_isShowingCalResult = false;
LARGE_INTEGER g_RecStartTime;
LARGE_INTEGER g_CounterFreq;
LARGE_INTEGER g_PrevRenderTime;

double g_CalPointList[MAXCALPOINT][2];

FILE *g_DataFP = NULL;
char g_MessageBuffer[MAXMESSAGE];
int g_MessageEnd;

CUSTOMVERTEX g_vCursor[4] = 
{
	   {  CURSOR_SIZE_HALF, -CURSOR_SIZE_HALF, 0.0f, 1.0f, 0x00FFFF00, 1.0f, 0.0f},
	   {  CURSOR_SIZE_HALF,  CURSOR_SIZE_HALF, 0.0f, 1.0f, 0x00FFFF00, 1.0f, 1.0f}, 
	   { -CURSOR_SIZE_HALF, -CURSOR_SIZE_HALF, 0.0f, 1.0f, 0x00FFFF00, 0.0f, 0.0f}, 
	   { -CURSOR_SIZE_HALF,  CURSOR_SIZE_HALF, 0.0f, 1.0f, 0x00FFFF00, 0.0f, 1.0f} 
};

CUSTOMVERTEX g_vGazeMarker[4] = 
{
	   { SCREEN_WIDTH/2+MARKER_SIZE_HALF, SCREEN_HEIGHT/2-MARKER_SIZE_HALF, 0.0f, 1.0f, 0x00FF0000, 1.0f, 0.0f},
	   { SCREEN_WIDTH/2+MARKER_SIZE_HALF, SCREEN_HEIGHT/2+MARKER_SIZE_HALF, 0.0f, 1.0f, 0x00FF0000, 1.0f, 1.0f}, 
	   { SCREEN_WIDTH/2-MARKER_SIZE_HALF, SCREEN_HEIGHT/2-MARKER_SIZE_HALF, 0.0f, 1.0f, 0x00FF0000, 0.0f, 0.0f}, 
	   { SCREEN_WIDTH/2-MARKER_SIZE_HALF, SCREEN_HEIGHT/2+MARKER_SIZE_HALF, 0.0f, 1.0f, 0x00FF0000, 0.0f, 1.0f} 
};


/*!
initParameters: Read parameters from the configuration file to initialize application.

Data directory is set to %HOMEDRIVE%%HOMEPATH%\GazeTracker.
Configuration file directory is set to %APPDATA%\GazeTracker.

Following parameters are read from a configuration file named "CONFIG".

-THRESHOLD  (g_Threshold)
-MAXPOINTS  (g_MaxPoints)
-MINPOINTS  (g_MinPoints)
-PURKINJE_THRESHOLD  (g_PurkinjeThreshold)
-PURKINJE_SEARCHAREA  (g_PurkinjeSearchArea)
-PURKINJE_EXCLUDEAREA  (g_PurkinjeExcludeArea)
-BINOCULAR  (g_RecordingMode)
-CAMERA_WIDTH  (g_CameraWidth)
-CAMERA_HEIGHT  (g_CameraHeight)
-PREVIEW_WIDTH  (g_PreviewWidth)
-PREVIEW_HEIGHT  (g_PreviewHeight)

@return HRESULT
@retval S_OK Camera is successfully initialized.
@retval E_FAIL Initialization is failed.

@date 2012/04/06 CAMERA_WIDTH, CAMERA_HEIGHT, PREVIEW_WIDTH and PREVIEW_HEIGHT are supported.
 */
HRESULT initParameters( void )
{
	FILE* fp;
	char buff[512];
	char *p,*pp;
	int param;
	DWORD n;

	n = GetEnvironmentVariable("HOMEDRIVE",g_DataPath,sizeof(g_DataPath));
	n = GetEnvironmentVariable("HOMEPATH",g_DataPath+n,sizeof(g_DataPath)-n);
	strcat_s(g_DataPath, sizeof(g_DataPath), "\\GazeTracker");

	GetEnvironmentVariable("APPDATA",g_ParamPath,sizeof(g_ParamPath));
	strcat_s(g_ParamPath, sizeof(g_ParamPath), "\\GazeTracker");

	if(!PathIsDirectory(g_DataPath)){
		CreateDirectory(g_DataPath,NULL);
	}

	if(!PathIsDirectory(g_ParamPath)){
		CreateDirectory(g_ParamPath,NULL);		
	}

	strcpy_s(buff,sizeof(buff),g_ParamPath);
	strcat_s(buff,sizeof(buff),"\\CONFIG");
	if(!PathFileExists(buff)){
		char exefile[512];
		char configfile[512];
		char drive[4],dir[512],fname[32],ext[5];
		errno_t r;
		GetModuleFileName(NULL,exefile,sizeof(exefile));
		r = _splitpath_s(exefile,drive,sizeof(drive),dir,sizeof(dir),fname,sizeof(fname),ext,sizeof(ext));
		strcpy_s(configfile,sizeof(configfile),drive);
		strcat_s(configfile,sizeof(configfile),dir);
		strcat_s(configfile,sizeof(configfile),"\\CONFIG");
		CopyFile(configfile,buff,true);
	}

	if(fopen_s(&fp,buff,"r")!=NULL)
	{
		return E_FAIL;
	}

	while(fgets(buff,sizeof(buff),fp)!=NULL)
	{
		if(buff[0]=='#') continue;
		if((p=strchr(buff,'='))==NULL) continue;

		param = strtol(p+1,&pp,10);
		*p = NULL;

		if(strcmp(buff,"THRESHOLD")==0) g_Threshold = param;
		else if(strcmp(buff,"MAXPOINTS")==0) g_MaxPoints = param;
		else if(strcmp(buff,"MINPOINTS")==0) g_MinPoints = param;
		else if(strcmp(buff,"PURKINJE_THRESHOLD")==0) g_PurkinjeThreshold = param;
		else if(strcmp(buff,"PURKINJE_SEARCHAREA")==0) g_PurkinjeSearchArea = param;
		else if(strcmp(buff,"PURKINJE_EXCLUDEAREA")==0) g_PurkinjeExcludeArea = param;
		else if(strcmp(buff,"BINOCULAR")==0) g_RecordingMode = param;
		else if(strcmp(buff,"CAMERA_WIDTH")==0) g_CameraWidth = param;
		else if(strcmp(buff,"CAMERA_HEIGHT")==0) g_CameraHeight = param;
		else if(strcmp(buff,"PREVIEW_WIDTH")==0) g_PreviewWidth = param;
		else if(strcmp(buff,"PREVIEW_HEIGHT")==0) g_PreviewHeight = param;
	}
	g_ROIWidth = g_CameraWidth;
	g_ROIHeight = g_CameraHeight;

	fclose(fp);

	return S_OK;
}

/*!
saveParameters: Save current parameters to the configuration file.

Following parameters are wrote to the configuration file.

-THRESHOLD  (g_Threshold)
-MAXPOINTS  (g_MaxPoints)
-MINPOINTS  (g_MinPoints)
-PURKINJE_THRESHOLD  (g_PurkinjeThreshold)
-PURKINJE_SEARCHAREA  (g_PurkinjeSearchArea)
-PURKINJE_EXCLUDEAREA  (g_PurkinjeExcludeArea)
-BINOCULAR  (g_RecordingMode)
-CAMERA_WIDTH  (g_CameraWidth)
-CAMERA_HEIGHT  (g_CameraHeight)
-PREVIEW_WIDTH  (g_PreviewWidth)
-PREVIEW_HEIGHT  (g_PreviewHeight)

@return No value is returned.

@date 2012/04/06 CAMERA_WIDTH, CAMERA_HEIGHT, PREVIEW_WIDTH and PREVIEW_HEIGHT are supported.
*/
void saveParameters( void )
{
	FILE* fp;
	char buff[512];

	strcpy_s(buff,sizeof(buff),g_ParamPath);
	strcat_s(buff,sizeof(buff),"\\CONFIG");

	if(fopen_s(&fp,buff,"w")!=NULL)
	{
		return;
	}

	fprintf_s(fp,"#If you want to recover original settings, delete this file and start eye tracker program.\n");
	fprintf_s(fp,"THRESHOLD=%d\n",g_Threshold);
	fprintf_s(fp,"MAXPOINTS=%d\n",g_MaxPoints);
	fprintf_s(fp,"MINPOINTS=%d\n",g_MinPoints);
	fprintf_s(fp,"PURKINJE_THRESHOLD=%d\n",g_PurkinjeThreshold);
	fprintf_s(fp,"PURKINJE_SEARCHAREA=%d\n",g_PurkinjeSearchArea);
	fprintf_s(fp,"PURKINJE_EXCLUDEAREA=%d\n",g_PurkinjeExcludeArea);
	fprintf_s(fp,"BINOCULAR=%d\n",g_RecordingMode);
	fprintf_s(fp,"CAMERA_WIDTH=%d\n", g_CameraWidth);
	fprintf_s(fp,"CAMERA_HEIGHT=%d\n", g_CameraHeight);
	fprintf_s(fp,"PREVIEW_WIDTH=%d\n", g_PreviewWidth);
	fprintf_s(fp,"PREVIEW_HEIGHT=%d\n", g_PreviewHeight);
	fclose(fp);

}

/*!
updateMenuText: update menu text.

@return No value is returned.
*/
void updateMenuText( void )
{
	_stprintf_s(g_MenuString[MENU_THRESH_PUPIL],    MENU_STRING_MAX, _T("PupilThreshold(%d)"), g_Threshold);
	_stprintf_s(g_MenuString[MENU_THRESH_PURKINJE], MENU_STRING_MAX, _T("PurkinjeThreshold(%d)"), g_PurkinjeThreshold);
	_stprintf_s(g_MenuString[MENU_MINPOINTS],       MENU_STRING_MAX, _T("MinPoints(%d)"), g_MinPoints);
	_stprintf_s(g_MenuString[MENU_MAXPOINTS],       MENU_STRING_MAX, _T("MaxPoints(%d)"), g_MaxPoints);
	_stprintf_s(g_MenuString[MENU_SEARCHAREA],      MENU_STRING_MAX, _T("PurkinjeSearchArea(%d)"), g_PurkinjeSearchArea);
	_stprintf_s(g_MenuString[MENU_EXCLUDEAREA],     MENU_STRING_MAX, _T("PurkinjeExcludeArea(%d)"), g_PurkinjeExcludeArea);

	return;
}

/*!
printStringToTexture: render menu texts to DirectX texture.

@param[in] StartX Left end of the menu strings.
@param[in] StartY Top end of the menu strings.
@param[in] Array of menu strings.
@param[in] numItems Number of menu items (MENU_GENERAL_NUM + g_CustomMenuNum).
@param[in] fontsize Font size.
@param[in] pTex Pointer to the menu texture.
@return HRESULT
@retval S_OK 
@retval E_FAIL 

@note Thanks to following page for rendering fonts. http://marupeke296.com/DirectXMain.html
*/
HRESULT printStringToTexture(int StartX, int StartY, TCHAR string[][MENU_STRING_MAX], int numItems, int fontsize, IDirect3DTexture9* pTex)
{
	///////////////////////
	// Generate font
	LOGFONT lf = {fontsize, 0, 0, 0, 0, 0, 0, 0, SHIFTJIS_CHARSET, OUT_DEFAULT_PRECIS,
		CLIP_DEFAULT_PRECIS, PROOF_QUALITY, FIXED_PITCH | FF_MODERN, _T("Courier")};
	HFONT hFont;
	if(!(hFont = CreateFontIndirect(&lf))){
		return E_FAIL;
	}

	//Get device context
	HDC hdc = GetDC(NULL);
	HFONT oldFont = (HFONT)SelectObject(hdc, hFont);

	D3DSURFACE_DESC Desc;
	pTex->GetLevelDesc(0, &Desc);

	D3DLOCKED_RECT LockedRect;
	if(FAILED(pTex->LockRect(0, &LockedRect, NULL, D3DLOCK_DISCARD)))
	{
		if(FAILED(pTex->LockRect(0, &LockedRect, NULL, 0)))
		{
			return E_FAIL;
		}
	}
	FillMemory(LockedRect.pBits , LockedRect.Pitch * Desc.Height, 0);

	int SX = StartX;
	int SY = StartY;
	int iOfs_x,iOfs_y,iBmp_w,iBmp_h,Level;
	TEXTMETRIC TM;
	GetTextMetrics( hdc, &TM );
	GLYPHMETRICS GM;
	CONST MAT2 Mat = {{0,1},{0,0},{0,0},{0,1}};

	for(int l=0; l<numItems; l++)
	{
		TCHAR* sp = string[l];
		while(*sp != NULL)
		{
			// get character code.
			TCHAR *c = sp;
			UINT code = 0;
	#if _UNICODE
			code = (UINT)*c;
	#else
			if(IsDBCSLeadByte(*c)){
				code = (BYTE)c[0]<<8 | (BYTE)c[1];
			}
			else
			{
				code = c[0];
			}
	#endif

			// get FontBitmap
			DWORD size = GetGlyphOutline(hdc, code, GGO_GRAY4_BITMAP, &GM, 0, NULL, &Mat);
			BYTE *ptr = new BYTE[size];
			GetGlyphOutline(hdc, code, GGO_GRAY4_BITMAP, &GM, size, ptr, &Mat);

			iOfs_x = GM.gmptGlyphOrigin.x;
			iOfs_y = TM.tmAscent - GM.gmptGlyphOrigin.y;
			iBmp_w = GM.gmBlackBoxX + (4-(GM.gmBlackBoxX%4))%4;
			iBmp_h = GM.gmBlackBoxY;
			Level = 17;

			iOfs_x += SX;
			iOfs_y += SY;

			int x, y;
			DWORD Color;
			for(y=iOfs_y; y<iOfs_y+iBmp_h; y++){
				for(x=iOfs_x; x<iOfs_x+iBmp_w; x++){
					Color = (255 * ptr[x-iOfs_x + iBmp_w*(y-iOfs_y)]) / (Level-1);
					Color = Color<<16 | Color<<8 | Color;
					memcpy((BYTE*)LockedRect.pBits + LockedRect.Pitch*y + 4*x, &Color, sizeof(DWORD));
				}
			}
			delete[] ptr;

			SX += fontsize/2;
			sp++;
		}
		SY += MENU_ITEM_HEIGHT;
		SX = StartX;
	}

	pTex->UnlockRect(0);

	// Release device context and font handle
	SelectObject(hdc, oldFont);
	DeleteObject(hFont);
	ReleaseDC(NULL, hdc);

	return S_OK;
}

/*!
initD3D: render menu texts to DirectX texture.

initParameters() and initBuffers() must be called in this order before calling this function.

@param[in] hWnd Window handle
@return HRESULT
@retval S_OK 
@retval E_FAIL 
*/
HRESULT initD3D( HWND hWnd )
{
	HRESULT hr;
    // Create the D3D object, which is needed to create the D3DDevice.
    if( NULL == ( g_pD3D = Direct3DCreate9( D3D_SDK_VERSION ) ) )
        return E_FAIL;

    // Set up the structure used to create the D3DDevice.
    D3DPRESENT_PARAMETERS d3dpp;
    ZeroMemory( &d3dpp, sizeof( d3dpp ) );
	d3dpp.BackBufferWidth = SCREEN_WIDTH;
	d3dpp.BackBufferHeight = SCREEN_HEIGHT;
	d3dpp.BackBufferFormat = D3DFMT_X8R8G8B8;
	d3dpp.BackBufferCount = 1;
    d3dpp.Windowed = true;
    d3dpp.SwapEffect = D3DSWAPEFFECT_DISCARD;
	d3dpp.PresentationInterval = D3DPRESENT_INTERVAL_IMMEDIATE;

    // Create the Direct3D device.
    if( FAILED( g_pD3D->CreateDevice( D3DADAPTER_DEFAULT, D3DDEVTYPE_HAL, hWnd,
                                      D3DCREATE_SOFTWARE_VERTEXPROCESSING,
                                      &d3dpp, &g_pd3dDevice ) ) )
    {
        return E_FAIL;
    }

    // Device state would normally be set here

	CUSTOMVERTEX vCameraTexture[4] = 
	{
           { (float)g_PreviewWidth, 1,                      0.0f, 1.0f, 0x00ffffff, 1.0f, 0.0f},
           { (float)g_PreviewWidth, (float)g_PreviewHeight, 0.0f, 1.0f, 0x00ffffff, 1.0f, 1.0f}, 
           { 1,                     1,                      0.0f, 1.0f, 0x00ffffff, 0.0f, 0.0f}, 
           { 1,                     (float)g_PreviewHeight, 0.0f, 1.0f, 0x00ffffff, 0.0f, 1.0f} 
	};
	CUSTOMVERTEX vPanelTexture[4] = 
	{
           { (float)g_PreviewWidth+20+PANEL_WIDTH,    20+1,            0.0f, 1.0f, 0x00ffffff, 1.0f, 0.0f},
           { (float)g_PreviewWidth+20+PANEL_WIDTH,    20+PANEL_HEIGHT, 0.0f, 1.0f, 0x00ffffff, 1.0f, 1.0f}, 
           { (float)g_PreviewWidth+20+1,              20+1,            0.0f, 1.0f, 0x00ffffff, 0.0f, 0.0f}, 
           { (float)g_PreviewWidth+20+1,              20+PANEL_HEIGHT, 0.0f, 1.0f, 0x00ffffff, 0.0f, 1.0f} 
	};

	if(FAILED(g_pd3dDevice->CreateVertexBuffer(sizeof(CUSTOMVERTEX)*4,D3DUSAGE_WRITEONLY, FVF_CUSTOM, D3DPOOL_MANAGED, &g_pCameraTextureVertex, NULL))){
		return E_FAIL;
	}
	if(FAILED(g_pd3dDevice->CreateVertexBuffer(sizeof(CUSTOMVERTEX)*4,D3DUSAGE_WRITEONLY, FVF_CUSTOM, D3DPOOL_MANAGED, &g_pPanelTextureVertex, NULL))){
		return E_FAIL;
	}
	if(FAILED(g_pd3dDevice->CreateVertexBuffer(sizeof(CUSTOMVERTEX)*4,D3DUSAGE_WRITEONLY, FVF_CUSTOM, D3DPOOL_MANAGED, &g_pCursorVertex, NULL))){
		return E_FAIL;
	}
	if(FAILED(g_pd3dDevice->CreateVertexBuffer(sizeof(CUSTOMVERTEX)*4,D3DUSAGE_WRITEONLY, FVF_CUSTOM, D3DPOOL_MANAGED, &g_pGazeMarkerVertex, NULL))){
		return E_FAIL;
	}

	D3DXCreateTexture(g_pd3dDevice, g_ROIWidth, g_ROIHeight, 1, D3DUSAGE_DYNAMIC, D3DFMT_R8G8B8, D3DPOOL_DEFAULT, &g_pCameraTexture);
	D3DXCreateTexture(g_pd3dDevice, g_PreviewWidth, g_PreviewHeight, 1, D3DUSAGE_DYNAMIC, D3DFMT_R8G8B8, D3DPOOL_DEFAULT, &g_pCalResultTexture);
	D3DXCreateTexture(g_pd3dDevice, PANEL_WIDTH, PANEL_HEIGHT, 0, D3DUSAGE_DYNAMIC, D3DFMT_R8G8B8, D3DPOOL_DEFAULT, &g_pPanelTexture);

	void* pData;
	g_pCameraTextureVertex->Lock(0, sizeof(CUSTOMVERTEX)*4, (void**)&pData, 0);
	memcpy(pData,vCameraTexture,sizeof(CUSTOMVERTEX)*4);
	g_pCameraTextureVertex->Unlock();

	updateMenuText();
	updateCustomMenuText();
    hr = printStringToTexture(0,0,g_MenuString,MENU_GENERAL_NUM+g_CustomMenuNum,MENU_FONT_SIZE,g_pPanelTexture);

	g_pPanelTextureVertex->Lock(0, sizeof(CUSTOMVERTEX)*4, (void**)&pData, 0);
	memcpy(pData,vPanelTexture,sizeof(CUSTOMVERTEX)*4);
	g_pPanelTextureVertex->Unlock();

	return S_OK;
}


/*!
cleanup: release Direct3D resources.

@return No value is returned.

@date 2012/04/06 release buffers.
*/
void cleanup()
{
    if( g_pd3dDevice != NULL )
        g_pd3dDevice->Release();

    if( g_pD3D != NULL )
        g_pD3D->Release();

    if( g_frameBuffer != NULL )
        free(g_frameBuffer);

    if( g_pCameraTextureBuffer != NULL )
        free(g_pCameraTextureBuffer);

    if( g_pCalResultTextureBuffer != NULL )
        free(g_pCalResultTextureBuffer);

    if( g_SendImageBuffer != NULL )
        free(g_SendImageBuffer);

    if( g_frameBuffer != NULL )
        free(g_frameBuffer);

}

/*!
flushGazeData: write data to the datafile.

This function is called either when recording is stopped or g_DataCounter reached to MAXDATA.

@return No value is returned.
*/
void flushGazeData(void)
{
	double xy[4];
	if(g_RecordingMode==RECORDING_MONOCULAR){
		for(int i=0; i<g_DataCounter; i++){
			fprintf_s(g_DataFP,"%.3f,",g_TickData[i]);
			if(g_EyeData[i][0]<E_PUPIL_PURKINJE_DETECTION_FAIL){
				if(g_EyeData[i][0] == E_MULTIPLE_PUPIL_CANDIDATES)
					fprintf_s(g_DataFP,"MULTIPUPIL,MULTIPUPIL\n");
				else if(g_EyeData[i][0] == E_NO_PUPIL_CANDIDATE)
					fprintf_s(g_DataFP,"NOPUPIL,NOPUPIL\n");
				else if(g_EyeData[i][0] == E_NO_PURKINJE_CANDIDATE)
					fprintf_s(g_DataFP,"NOPURKINJE,NOPURKINJE\n");
				else if(g_EyeData[i][0] == E_NO_FINE_PUPIL_CANDIDATE)
					fprintf_s(g_DataFP,"NOFINEPUPIL,NOFINEPUPIL\n");
				else
					fprintf_s(g_DataFP,"FAIL,FAIL\n");					
			}else{
				getGazePositionMono(g_EyeData[i], xy);
				fprintf_s(g_DataFP,"%.1f,%.1f\n" ,xy[MONO_X],xy[MONO_Y]);
			}
		}
	}else{ //binocular
		for(int i=0; i<g_DataCounter; i++){
			fprintf_s(g_DataFP,"%.3f,",g_TickData[i]);
			getGazePositionBin(g_EyeData[i], xy);
			//left eye
			if(g_EyeData[i][BIN_LX]<E_PUPIL_PURKINJE_DETECTION_FAIL){
				if(g_EyeData[i][BIN_LX] == E_MULTIPLE_PUPIL_CANDIDATES)
					fprintf_s(g_DataFP,"MULTIPUPIL,MULTIPUPIL,");
				else if(g_EyeData[i][BIN_LX] == E_NO_PUPIL_CANDIDATE)
					fprintf_s(g_DataFP,"NOPUPIL,NOPUPIL,");
				else if(g_EyeData[i][BIN_LX] == E_NO_PURKINJE_CANDIDATE)
					fprintf_s(g_DataFP,"NOPURKINJE,NOPURKINJE,");
				else if(g_EyeData[i][BIN_LX] == E_NO_FINE_PUPIL_CANDIDATE)
					fprintf_s(g_DataFP,"NOFINEPUPIL,NOFINEPUPIL,");
				else
					fprintf_s(g_DataFP,"FAIL,FAIL,");		
			}else{
				fprintf_s(g_DataFP,"%.1f,%.1f," ,xy[BIN_LX],xy[BIN_LY]);
			}
			//right eye
			if(g_EyeData[i][BIN_RX]<E_PUPIL_PURKINJE_DETECTION_FAIL){
				if(g_EyeData[i][BIN_RX] == E_MULTIPLE_PUPIL_CANDIDATES)
					fprintf_s(g_DataFP,"MULTIPUPIL,MULTIPUPIL\n");
				else if(g_EyeData[i][BIN_RX] == E_NO_PUPIL_CANDIDATE)
					fprintf_s(g_DataFP,"NOPUPIL,NOPUPIL\n");
				else if(g_EyeData[i][BIN_RX] == E_NO_PURKINJE_CANDIDATE)
					fprintf_s(g_DataFP,"NOPURKINJE,NOPURKINJE\n");
				else if(g_EyeData[i][BIN_RX] == E_NO_FINE_PUPIL_CANDIDATE)
					fprintf_s(g_DataFP,"NOFINEPUPIL,NOFINEPUPIL\n");
				else
					fprintf_s(g_DataFP,"FAIL,FAIL\n");					
			}else{
				fprintf_s(g_DataFP,"%.1f,%.1f\n" ,xy[BIN_RX],xy[BIN_RY]);
			}
		}

	}

	fflush(g_DataFP);
}

/*!
getGazeMono: convert relative Purkinje image position to gaze position and store data (for monocular recording).
Following global variables may be changed. If g_DataCounter reached to MAXDATA, data are 
flushed to the data file and g_DataCounter is rewinded to zero.
- g_EyeData
- g_CalPointData
- g_DataCounter
- g_TickData
- g_CalSamplesAtCurrentPoint

@param[in] detectionResults Center of pupil and Purkinje image.  Only four elements are used when recording mode is monocular.
@param[in] TimeImageAquired Timestamp

@return No value is returned.
*/
void getGazeMono( double detectionResults[8], double TimeImageAquired )
{
	if(g_isCalibrating || g_isValidating){
		if(detectionResults[MONO_PUPIL_X] <= E_FIRST_ERROR_CODE) //A value smaller than E_FIRST_ERROR_CODE is treated as an error.
		{
			// data should not be included in g_CalPointData.
			return;
		}
		if(g_CalSamplesAtCurrentPoint > 0)
		{
			g_CalPointData[g_DataCounter][MONO_X] = g_CurrentCalPoint[MONO_X];
			g_CalPointData[g_DataCounter][MONO_Y] = g_CurrentCalPoint[MONO_Y];
			g_EyeData[g_DataCounter][MONO_X] = detectionResults[MONO_PUPIL_X]-detectionResults[MONO_PURKINJE_X];
			g_EyeData[g_DataCounter][MONO_Y] = detectionResults[MONO_PUPIL_Y]-detectionResults[MONO_PURKINJE_Y];
			g_DataCounter++;
			g_CalSamplesAtCurrentPoint--;
		}

	}else if(g_isRecording){
		g_TickData[g_DataCounter] = TimeImageAquired;
		if(detectionResults[MONO_PUPIL_X] <= E_FIRST_ERROR_CODE) //A value smaller than E_FIRST_ERROR_CODE is treated as an error.
		{
			g_EyeData[g_DataCounter][MONO_X] = detectionResults[MONO_PUPIL_X];
			g_EyeData[g_DataCounter][MONO_Y] = detectionResults[MONO_PUPIL_X];
			g_CurrentEyeData[MONO_X] = detectionResults[MONO_PUPIL_X];
			g_CurrentEyeData[MONO_Y] = detectionResults[MONO_PUPIL_X];
		}
		else
		{
			g_EyeData[g_DataCounter][MONO_X] = detectionResults[MONO_PUPIL_X]-detectionResults[MONO_PURKINJE_X];
			g_EyeData[g_DataCounter][MONO_Y] = detectionResults[MONO_PUPIL_Y]-detectionResults[MONO_PURKINJE_Y];
			getGazePositionMono(g_EyeData[g_DataCounter], g_CurrentEyeData);
		}
		g_DataCounter++;
		//check overflow
		if(g_DataCounter >= MAXDATA)
		{
			//flush data
			flushGazeData();
			
			//insert overflow message
			LARGE_INTEGER ct;
			double ctd;
			QueryPerformanceCounter(&ct);
			ctd = 1000 * ((double)(ct.QuadPart - g_RecStartTime.QuadPart) / g_CounterFreq.QuadPart);

			fprintf_s(g_DataFP,"#OVERFLOW_FLUSH_GAZEDATA,%.3f\n",ctd);
			fflush(g_DataFP);

			//reset counter
			g_DataCounter = 0;
		}
	}
}

/*!
getGazeBin: convert relative Purkinje image position to gaze position and store data (for binocular recording).
Following global variables may be changed. If g_DataCounter reached to MAXDATA, data are 
flushed to the data file and g_DataCounter is rewinded to zero.
- g_EyeData
- g_CalPointData
- g_DataCounter
- g_TickData
- g_CalSamplesAtCurrentPoint

@param[in] detectionResults Center of pupil and Purkinje image.
@param[in] TimeImageAquired Timestamp

@return No value is returned.
*/
void getGazeBin( double detectionResults[8], double TimeImageAquired )
{
	if(g_isCalibrating || g_isValidating){
		if(detectionResults[BIN_PUPIL_LX] <= E_FIRST_ERROR_CODE && 
			detectionResults[BIN_PUPIL_RX] <= E_FIRST_ERROR_CODE) //A value smaller than E_FIRST_ERROR_CODE is treated as an error.
		{
			// data should not be included in g_CalPointData.
			return;
		}
		if(g_CalSamplesAtCurrentPoint > 0)
		{
			g_CalPointData[g_DataCounter][BIN_X] = g_CurrentCalPoint[BIN_X];
			g_CalPointData[g_DataCounter][BIN_Y] = g_CurrentCalPoint[BIN_Y];
			g_EyeData[g_DataCounter][BIN_LX] = detectionResults[BIN_PUPIL_LX]-detectionResults[BIN_PURKINJE_LX];
			g_EyeData[g_DataCounter][BIN_LY] = detectionResults[BIN_PUPIL_LY]-detectionResults[BIN_PURKINJE_LY];
			g_EyeData[g_DataCounter][BIN_RX] = detectionResults[BIN_PUPIL_RX]-detectionResults[BIN_PURKINJE_RX];
			g_EyeData[g_DataCounter][BIN_RY] = detectionResults[BIN_PUPIL_RY]-detectionResults[BIN_PURKINJE_RY];
			g_DataCounter++;
			g_CalSamplesAtCurrentPoint--;
		}

	}else if(g_isRecording){
		g_TickData[g_DataCounter] = TimeImageAquired;
		g_EyeData[g_DataCounter][BIN_LX] = detectionResults[BIN_PUPIL_LX]-detectionResults[BIN_PURKINJE_LX];
		g_EyeData[g_DataCounter][BIN_LY] = detectionResults[BIN_PUPIL_LY]-detectionResults[BIN_PURKINJE_LY];
		g_EyeData[g_DataCounter][BIN_RX] = detectionResults[BIN_PUPIL_RX]-detectionResults[BIN_PURKINJE_RX];
		g_EyeData[g_DataCounter][BIN_RY] = detectionResults[BIN_PUPIL_RY]-detectionResults[BIN_PURKINJE_RY];
		getGazePositionBin(g_EyeData[g_DataCounter], g_CurrentEyeData);
		//left eye
		if(detectionResults[BIN_PUPIL_LX] <= E_FIRST_ERROR_CODE) //A value smaller than E_FIRST_ERROR_CODE is treated as an error.
		{
			g_EyeData[g_DataCounter][BIN_LX] = detectionResults[BIN_PUPIL_LX];
			g_EyeData[g_DataCounter][BIN_LY] = detectionResults[BIN_PUPIL_LX];
			g_CurrentEyeData[BIN_LX] = detectionResults[BIN_PUPIL_LX];
			g_CurrentEyeData[BIN_LY] = detectionResults[BIN_PUPIL_LX];
		}
		//right eye
		if(detectionResults[BIN_PUPIL_RX] <= E_FIRST_ERROR_CODE) //A value smaller than E_FIRST_ERROR_CODE is treated as an error.
		{
			g_EyeData[g_DataCounter][BIN_RX] = detectionResults[BIN_PUPIL_RX];
			g_EyeData[g_DataCounter][BIN_RY] = detectionResults[BIN_PUPIL_RX];
			g_CurrentEyeData[BIN_RX] = detectionResults[BIN_PUPIL_RX];
			g_CurrentEyeData[BIN_RY] = detectionResults[BIN_PUPIL_RX];
		}
		g_DataCounter++;
		//check overflow
		if(g_DataCounter >= MAXDATA)
		{
			//flush data
			flushGazeData();
			
			//insert overflow message
			LARGE_INTEGER ct;
			double ctd;
			QueryPerformanceCounter(&ct);
			ctd = 1000 * ((double)(ct.QuadPart - g_RecStartTime.QuadPart) / g_CounterFreq.QuadPart);

			fprintf_s(g_DataFP,"#OVERFLOW_FLUSH_GAZEDATA,%.3f\n",ctd);
			fflush(g_DataFP);

			//reset counter
			g_DataCounter = 0;
		}
	}
}

/*!
Render: Render DirectX polygons.

This function should not be called during recording.

@return No value is returned.
*/
VOID render( void )
{
	void* pData;

	//move menu cursor position.
	float cursorX, cursorY;
	cursorX = (float)g_PreviewWidth+10;
	cursorY = 20+10+MENU_ITEM_HEIGHT*(float)g_CurrentMenuPosition;
	//if(g_CurrentMenuPosition>=MENU_CALIBRATION)
	//	cursorY += MENU_ITEM_HEIGHT;
	g_vCursor[0].x = cursorX+CURSOR_SIZE_HALF;
	g_vCursor[0].y = cursorY-CURSOR_SIZE_HALF;
	g_vCursor[1].x = cursorX+CURSOR_SIZE_HALF;
	g_vCursor[1].y = cursorY+CURSOR_SIZE_HALF;
	g_vCursor[2].x = cursorX-CURSOR_SIZE_HALF;
	g_vCursor[2].y = cursorY-CURSOR_SIZE_HALF;
	g_vCursor[3].x = cursorX-CURSOR_SIZE_HALF;
	g_vCursor[3].y = cursorY+CURSOR_SIZE_HALF;
	g_pCursorVertex->Lock(0, sizeof(CUSTOMVERTEX)*4, (void**)&pData, 0);
	memcpy(pData,g_vCursor,sizeof(CUSTOMVERTEX)*4);
	g_pCursorVertex->Unlock();

	if(g_isShowingCalResult)
	{
		D3DLOCKED_RECT TexRect;
		g_pCalResultTexture->LockRect(0, &TexRect, NULL, 0);
		LPDWORD p1 = (LPDWORD)TexRect.pBits;
		DWORD pitch = TexRect.Pitch / sizeof(DWORD);
		for(int iy=0; iy<g_PreviewHeight; iy++){
			for(int ix=0; ix<g_PreviewWidth; ix++){
				p1[ix] = g_pCalResultTextureBuffer[g_PreviewWidth*iy+ix];
			}
			p1 += pitch;
		}
		g_pCalResultTexture->UnlockRect(0);
	}
	else
	{
		D3DLOCKED_RECT TexRect;
		g_pCameraTexture->LockRect(0, &TexRect, NULL, 0);
		LPDWORD p1 = (LPDWORD)TexRect.pBits;
		DWORD pitch = TexRect.Pitch / sizeof(DWORD);
		for(int iy=0; iy<g_ROIHeight; iy++){
			for(int ix=0; ix<g_ROIWidth; ix++){
				p1[ix] = g_pCameraTextureBuffer[g_CameraWidth*(iy+(g_CameraHeight-g_ROIHeight)/2)+(ix+(g_CameraWidth-g_ROIWidth)/2)];
			}
			p1 += pitch;
		}
		g_pCameraTexture->UnlockRect(0);
	}

    if( NULL == g_pd3dDevice )
        return;

    // Clear the backbuffer to a blue color
    g_pd3dDevice->Clear( 0, NULL, D3DCLEAR_TARGET, D3DCOLOR_XRGB( 0, 0, 0 ), 1.0f, 0 );

    // Begin the scene
    if( SUCCEEDED( g_pd3dDevice->BeginScene() ) )
    {
		g_pd3dDevice->SetTextureStageState(0, D3DTSS_COLORARG1, D3DTA_TEXTURE ); 
		g_pd3dDevice->SetTextureStageState(0, D3DTSS_COLOROP , D3DTOP_MODULATE );
		g_pd3dDevice->SetTextureStageState(0, D3DTSS_COLORARG2, D3DTA_DIFFUSE ); 

		if(g_isShowingCalResult)
		{
			g_pd3dDevice->SetTexture(0, g_pCalResultTexture);
			g_pd3dDevice->SetStreamSource(0, g_pCameraTextureVertex, 0, sizeof(CUSTOMVERTEX));
			g_pd3dDevice->SetFVF(FVF_CUSTOM);
			g_pd3dDevice->DrawPrimitive(D3DPT_TRIANGLESTRIP, 0, 2);
		}
		else
		{
			g_pd3dDevice->SetTexture(0, g_pCameraTexture);
			g_pd3dDevice->SetStreamSource(0, g_pCameraTextureVertex, 0, sizeof(CUSTOMVERTEX));
			g_pd3dDevice->SetFVF(FVF_CUSTOM);
			g_pd3dDevice->DrawPrimitive(D3DPT_TRIANGLESTRIP, 0, 2);
		}

		g_pd3dDevice->SetTexture(0, g_pPanelTexture);
		//g_pd3dDevice->SetTexture(0, NULL);
		g_pd3dDevice->SetStreamSource(0, g_pPanelTextureVertex, 0, sizeof(CUSTOMVERTEX));
		g_pd3dDevice->SetFVF(FVF_CUSTOM);
		g_pd3dDevice->DrawPrimitive(D3DPT_TRIANGLESTRIP, 0, 2);

		g_pd3dDevice->SetTexture(0, NULL);
		g_pd3dDevice->SetStreamSource(0, g_pCursorVertex, 0, sizeof(CUSTOMVERTEX));
		g_pd3dDevice->SetFVF(FVF_CUSTOM);
		g_pd3dDevice->DrawPrimitive(D3DPT_TRIANGLESTRIP, 0, 2);

        // End the scene
        g_pd3dDevice->EndScene();
    }

    // Present the backbuffer contents to the display
    g_pd3dDevice->Present( NULL, NULL, NULL, NULL );
}

/*!
renderBeforeRecording: Render DirectX polygons.

This function renders a message informing that the application is now recording data.
Call this function once immediately before start recording.

@return No value is returned.
*/
VOID renderBeforeRecording(void)
{
	D3DLOCKED_RECT TexRect;
	g_pCalResultTexture->LockRect(0, &TexRect, NULL, 0);
	LPDWORD p1 = (LPDWORD)TexRect.pBits;
	DWORD pitch = TexRect.Pitch / sizeof(DWORD);
	for(int iy=0; iy<g_PreviewHeight; iy++){
		for(int ix=0; ix<g_PreviewWidth; ix++){
			p1[ix] = g_pCalResultTextureBuffer[g_PreviewWidth*iy+ix];
		}
		p1 += pitch;
	}
	g_pCalResultTexture->UnlockRect(0);

    if( NULL == g_pd3dDevice )
        return;

    // Clear the backbuffer to a blue color
    g_pd3dDevice->Clear( 0, NULL, D3DCLEAR_TARGET, D3DCOLOR_XRGB( 0, 0, 0 ), 1.0f, 0 );

    // Begin the scene
    if( SUCCEEDED( g_pd3dDevice->BeginScene() ) )
    {
		g_pd3dDevice->SetTextureStageState(0, D3DTSS_COLORARG1, D3DTA_TEXTURE ); 
		g_pd3dDevice->SetTextureStageState(0, D3DTSS_COLOROP , D3DTOP_MODULATE );
		g_pd3dDevice->SetTextureStageState(0, D3DTSS_COLORARG2, D3DTA_DIFFUSE );

		// only calimage is drawn
		g_pd3dDevice->SetTexture(0, g_pCalResultTexture);
		g_pd3dDevice->SetStreamSource(0, g_pCameraTextureVertex, 0, sizeof(CUSTOMVERTEX));
		g_pd3dDevice->SetFVF(FVF_CUSTOM);
		g_pd3dDevice->DrawPrimitive(D3DPT_TRIANGLESTRIP, 0, 2);

        // End the scene
        g_pd3dDevice->EndScene();
    }

    // Present the backbuffer contents to the display
    g_pd3dDevice->Present( NULL, NULL, NULL, NULL );
}


/*!
msgProc: Message procedure for main application window.

@param[in] hWnd Window handle
@param[in] msg Received message
@param[in] wParam Message parameter
@param[in] lParam Message parameter
@return LRESULT
@retval value which is returned from DefWindowProc().
*/
LRESULT WINAPI msgProc( HWND hWnd, UINT msg, WPARAM wParam, LPARAM lParam )
{
	HRESULT hr;

	switch( msg )
    {
	case WM_KEYDOWN:
		switch(wParam)
		{
		case 'Q':
			if(g_isRecording || g_isCalibrating || g_isValidating)
			{
				g_isRecording = g_isCalibrating = g_isValidating = false;
			}
			else
			{
				DestroyWindow(hWnd);
			}
			break;

		case VK_UP:
			if(!g_isRecording && !g_isCalibrating && !g_isValidating){
				g_CurrentMenuPosition--;
				if(g_CurrentMenuPosition<0)
					g_CurrentMenuPosition = MENU_GENERAL_NUM + g_CustomMenuNum -1;
			}
			break;

		case VK_DOWN:
			if(!g_isRecording && !g_isCalibrating && !g_isValidating){
				g_CurrentMenuPosition++;
				if(MENU_GENERAL_NUM + g_CustomMenuNum <= g_CurrentMenuPosition)
				g_CurrentMenuPosition = 0;
			}
			break;

		case VK_LEFT:
			switch(g_CurrentMenuPosition)
			{
			case MENU_THRESH_PUPIL:
				g_Threshold--;
				if(g_Threshold<1)
					g_Threshold = 1;
				break;
			case MENU_THRESH_PURKINJE:
				g_PurkinjeThreshold--;
				if(g_PurkinjeThreshold<1)
					g_PurkinjeThreshold = 1;
				break;
			case MENU_MINPOINTS:
				g_MinPoints--;
				if(g_MinPoints<1)
					g_MinPoints = 1;
				break;
			case MENU_MAXPOINTS:
				g_MaxPoints--;
				if(g_MaxPoints<=g_MinPoints)
					g_MaxPoints = g_MinPoints+1;
				break;
			case MENU_SEARCHAREA:
				g_PurkinjeSearchArea--;
				if(g_PurkinjeSearchArea<10)
					g_PurkinjeSearchArea = 10;
				break;
			case MENU_EXCLUDEAREA:
				g_PurkinjeExcludeArea--;
				if(g_PurkinjeExcludeArea<2)
					g_PurkinjeExcludeArea = 2;
				break;
			default:
				customCameraMenu(hWnd, msg, wParam, lParam, g_CurrentMenuPosition);
				break;
			}
			updateMenuText();
			updateCustomMenuText();
			hr = printStringToTexture(0,0,g_MenuString,MENU_GENERAL_NUM+g_CustomMenuNum,MENU_FONT_SIZE,g_pPanelTexture);
			break;

		case VK_RIGHT:
			switch(g_CurrentMenuPosition)
			{
			case MENU_THRESH_PUPIL:
				g_Threshold++;
				if(g_Threshold>255)
					g_Threshold = 255;
				break;
			case MENU_THRESH_PURKINJE:
				g_PurkinjeThreshold++;
				if(g_PurkinjeThreshold>255)
					g_PurkinjeThreshold = 255;
				break;
			case MENU_MINPOINTS:
				g_MinPoints++;
				if(g_MinPoints>=g_MaxPoints)
					g_MinPoints = g_MaxPoints-1;
				break;
			case MENU_MAXPOINTS:
				g_MaxPoints++;
				if(g_MaxPoints>1000)
					g_MaxPoints = 1000;
				break;
			case MENU_SEARCHAREA:
				g_PurkinjeSearchArea++;
				if(g_PurkinjeSearchArea>150)
					g_PurkinjeSearchArea = 150;
				break;
			case MENU_EXCLUDEAREA:
				g_PurkinjeExcludeArea++;
				if(g_PurkinjeExcludeArea>g_PurkinjeSearchArea)
					g_PurkinjeExcludeArea = g_PurkinjeSearchArea;
				break;
			default:
				customCameraMenu(hWnd, msg, wParam, lParam, g_CurrentMenuPosition);
				break;
			}
			updateMenuText();
			updateCustomMenuText();
			hr = printStringToTexture(0,0,g_MenuString,MENU_GENERAL_NUM+g_CustomMenuNum,MENU_FONT_SIZE,g_pPanelTexture);
			break;

		//case VK_SPACE:

		default:
			break;
		}
		return 0;

	case WM_TCPSOCKET:
		sockProcess(hWnd, lParam);
		return 0;

	case WM_DESTROY:
        cleanup();
		cleanupCamera();
		saveParameters();
		saveCameraParameters(g_ParamPath);
        PostQuitMessage( 0 );
        return 0;

    }

    return DefWindowProc( hWnd, msg, wParam, lParam );
}

/*!
MessageDlgProc: Message procedure for initialization message window.

@param[in] hWnd Window handle
@param[in] msg Received message
@param[in] wp Message parameter
@param[in] lp Message parameter
@return LRESULT
@retval value which is returned from DefWindowProc().

@date 2012/04/06 INITMESSAGE_SUCCESS_BUFFER, INITMESSAGE_FAIL_BUFFER and INITMESSAGE_SUCCESS_ALL are supported.
@date 2012/03/27 return value is modifyed from False to DefWindowProc().
*/
LRESULT CALLBACK MessageDlgProc(HWND hWnd, UINT msg, WPARAM wp, LPARAM lp)
{
    static HWND hParent;
    hParent = GetParent(hWnd);
	char msgtext[2048];

    switch (msg) {
        case WM_INITDIALOG:
				SetWindowText(GetDlgItem(hWnd,IDC_EDIT_MESSAGE),"Welcome to GazeTracker.\r\n\r\n");
			EnableWindow(GetDlgItem(hWnd,IDOK),false);
            return TRUE;
		case WM_PAINT:
			if(wp==INITMESSAGE_FAIL_INIT){
				GetWindowText(GetDlgItem(hWnd,IDC_EDIT_MESSAGE),msgtext,sizeof(msgtext));
				sprintf_s(msgtext,sizeof(msgtext),"%sLocation of setting files: %s\r\nLocation of data files: %s\r\nFAIL: can't read parameter files.\r\n",msgtext,g_ParamPath,g_DataPath);
				SetWindowText(GetDlgItem(hWnd,IDC_EDIT_MESSAGE),msgtext);
				EnableWindow(GetDlgItem(hWnd,IDOK),true);
			}else if(wp==INITMESSAGE_SUCCESS_INIT){
				GetWindowText(GetDlgItem(hWnd,IDC_EDIT_MESSAGE),msgtext,sizeof(msgtext));
				sprintf_s(msgtext,sizeof(msgtext),"%sLocation of setting files: %s\r\nLocation of data files: %s\r\nRead config.\r\n",msgtext,g_ParamPath,g_DataPath);
				SetWindowText(GetDlgItem(hWnd,IDC_EDIT_MESSAGE),msgtext);
			}else if(wp==INITMESSAGE_FAIL_SOCK){
				GetWindowText(GetDlgItem(hWnd,IDC_EDIT_MESSAGE),msgtext,sizeof(msgtext));
				sprintf_s(msgtext,sizeof(msgtext),"%sFAIL: can't open socket.\r\n",msgtext);
				SetWindowText(GetDlgItem(hWnd,IDC_EDIT_MESSAGE),msgtext);
				EnableWindow(GetDlgItem(hWnd,IDOK),true);
			}else if(wp==INITMESSAGE_SUCCESS_SOCK){
				GetWindowText(GetDlgItem(hWnd,IDC_EDIT_MESSAGE),msgtext,sizeof(msgtext));
				sprintf_s(msgtext,sizeof(msgtext),"%sOpen socket.\r\n",msgtext);
				SetWindowText(GetDlgItem(hWnd,IDC_EDIT_MESSAGE),msgtext);
			}else if(wp==INITMESSAGE_FAIL_D3D){
				GetWindowText(GetDlgItem(hWnd,IDC_EDIT_MESSAGE),msgtext,sizeof(msgtext));
				sprintf_s(msgtext,sizeof(msgtext),"%sFAIL: can't initialize Direct3D.\r\n",msgtext);
				SetWindowText(GetDlgItem(hWnd,IDC_EDIT_MESSAGE),msgtext);
				EnableWindow(GetDlgItem(hWnd,IDOK),true);
			}else if(wp==INITMESSAGE_SUCCESS_D3D){
				GetWindowText(GetDlgItem(hWnd,IDC_EDIT_MESSAGE),msgtext,sizeof(msgtext));
				sprintf_s(msgtext,sizeof(msgtext),"%sInitialize Direct3D.\r\n",msgtext);
				SetWindowText(GetDlgItem(hWnd,IDC_EDIT_MESSAGE),msgtext);
			}else if(wp==INITMESSAGE_FAIL_CAMERA){
				GetWindowText(GetDlgItem(hWnd,IDC_EDIT_MESSAGE),msgtext,sizeof(msgtext));
				sprintf_s(msgtext,sizeof(msgtext),"%sFAIL: can't initialize camera.\r\n",msgtext);
				SetWindowText(GetDlgItem(hWnd,IDC_EDIT_MESSAGE),msgtext);
				EnableWindow(GetDlgItem(hWnd,IDOK),true);
			}else if(wp==INITMESSAGE_SUCCESS_CAMERA){
				GetWindowText(GetDlgItem(hWnd,IDC_EDIT_MESSAGE),msgtext,sizeof(msgtext));
				sprintf_s(msgtext,sizeof(msgtext),"%sInitialize camera.\r\n",msgtext);
				SetWindowText(GetDlgItem(hWnd,IDC_EDIT_MESSAGE),msgtext);
			}else if(wp==INITMESSAGE_FAIL_BUFFER){
				GetWindowText(GetDlgItem(hWnd,IDC_EDIT_MESSAGE),msgtext,sizeof(msgtext));
				sprintf_s(msgtext,sizeof(msgtext),"%sFAIL: can't initialize buffers.\r\n",msgtext);
				SetWindowText(GetDlgItem(hWnd,IDC_EDIT_MESSAGE),msgtext);
				EnableWindow(GetDlgItem(hWnd,IDOK),true);
			}else if(wp==INITMESSAGE_SUCCESS_BUFFER){
				GetWindowText(GetDlgItem(hWnd,IDC_EDIT_MESSAGE),msgtext,sizeof(msgtext));
				sprintf_s(msgtext,sizeof(msgtext),"%sInitialize buffers.\r\n",msgtext);
				SetWindowText(GetDlgItem(hWnd,IDC_EDIT_MESSAGE),msgtext);
			}else if(wp==INITMESSAGE_SUCCESS_ALL){
				GetWindowText(GetDlgItem(hWnd,IDC_EDIT_MESSAGE),msgtext,sizeof(msgtext));
				sprintf_s(msgtext,sizeof(msgtext),"%s\r\nOk. Let's go.\r\n",msgtext);
				SetWindowText(GetDlgItem(hWnd,IDC_EDIT_MESSAGE),msgtext);
			}
        case WM_COMMAND:
            switch (LOWORD(wp)) {
                case IDOK:
                    SendMessage(hParent, WM_CLOSE, 0, 0L);
                    return TRUE;
            }
            break;
    }
    return DefWindowProc( hWnd, msg, wp, lp );
}

/*!
waitQuitLoop: holds error message when initialization process failed.

@param[in] hWnd HWND of the main window.

@date 2012/04/06 created.
*/
void waitQuitLoop( HWND hWnd )
{
	bool bGotMsg;
	MSG msg;
	msg.message = WM_NULL;

	while(WM_QUIT != msg.message)
	{
		bGotMsg = ( PeekMessage( &msg, NULL, 0U, 0U, PM_REMOVE ) != 0 );
		if( bGotMsg )
		{
			if( 0 == TranslateAccelerator( hWnd, NULL, &msg )){
				TranslateMessage( &msg );
				DispatchMessage( &msg );
			}
		}
	}
}


/*!
wWinMain: Entry point of the application.

@param[in] hInst

@return int termination code.
*/
INT WINAPI wWinMain( HINSTANCE hInst, HINSTANCE, LPWSTR, INT )
{
	bool bGotMsg;
	MSG msg;
	msg.message = WM_NULL;

	// Register the window class
    WNDCLASSEX wc =
    {
        sizeof( WNDCLASSEX ), CS_CLASSDC, msgProc, 0L, 0L,
        GetModuleHandle( NULL ), NULL, NULL, NULL, NULL,
        "GazeTracker", NULL
    };
	wc.hIcon = (HICON)LoadImage(hInst, MAKEINTRESOURCE(IDI_ICON), IMAGE_ICON,0, 0, LR_DEFAULTSIZE);

    RegisterClassEx( &wc );

	RECT deskRect;
	HWND hWndDesktop = GetDesktopWindow();
	GetWindowRect(hWndDesktop, &deskRect);
	
    // Create the application's window
    HWND hWnd = CreateWindow( "GazeTracker", "GazeTracker",
                              //WS_VISIBLE | WS_POPUP,
                              WS_VISIBLE | WS_POPUP | WS_BORDER | WS_CAPTION | WS_SYSMENU ,
							  (deskRect.right-SCREEN_WIDTH)/2, (deskRect.bottom-SCREEN_HEIGHT)/2, SCREEN_WIDTH, SCREEN_HEIGHT,
                              NULL, NULL, wc.hInstance, NULL );

	QueryPerformanceFrequency(&g_CounterFreq);
	QueryPerformanceCounter(&g_PrevRenderTime);

	HANDLE hProcessID = GetCurrentProcess();
	//SetPriorityClass(hProcessID,NORMAL_PRIORITY_CLASS);
	SetPriorityClass(hProcessID,HIGH_PRIORITY_CLASS);
	//SetPriorityClass(hProcessID,REALTIME_PRIORITY_CLASS);

    // Show the window
    ShowWindow( hWnd, SW_SHOWDEFAULT );
    UpdateWindow( hWnd );
	
	HWND hWnd_message;
	hWnd_message = CreateDialog(hInst, MAKEINTRESOURCE(IDD_MESSAGE), hWnd, (DLGPROC)MessageDlgProc);
	if(hWnd_message==NULL){
		return false;
	}
	ShowWindow( hWnd_message, SW_SHOWDEFAULT );
	UpdateWindow( hWnd_message );


	if(FAILED(initParameters())){
		SendMessage(hWnd_message, WM_PAINT, INITMESSAGE_FAIL_INIT, 0L);
		UpdateWindow( hWnd_message );
		waitQuitLoop( hWnd );
	}
	SendMessage(hWnd_message, WM_PAINT, INITMESSAGE_SUCCESS_INIT, 0L);
	UpdateWindow( hWnd_message );

	if(FAILED(initBuffers())){
		SendMessage(hWnd_message, WM_PAINT, INITMESSAGE_FAIL_BUFFER, 0L);
		UpdateWindow( hWnd_message );
		waitQuitLoop( hWnd );
	}
	SendMessage(hWnd_message, WM_PAINT, INITMESSAGE_SUCCESS_BUFFER, 0L);
	UpdateWindow( hWnd_message );

	if(FAILED(sockInit(hWnd))||sockAccept(hWnd)){
		SendMessage(hWnd_message, WM_PAINT, INITMESSAGE_FAIL_SOCK, 0L);
		UpdateWindow( hWnd_message );
		waitQuitLoop( hWnd );
	}
	SendMessage(hWnd_message, WM_PAINT, INITMESSAGE_SUCCESS_SOCK, 0L);
	UpdateWindow( hWnd_message );

	if(FAILED(initCamera(g_ParamPath))){
		SendMessage(hWnd_message, WM_PAINT, INITMESSAGE_FAIL_CAMERA, 0L);
		UpdateWindow( hWnd_message );
		waitQuitLoop( hWnd );
	}
	SendMessage(hWnd_message, WM_PAINT, INITMESSAGE_SUCCESS_CAMERA, 0L);
	UpdateWindow( hWnd_message );

	if( FAILED(initD3D( hWnd ))){
		SendMessage(hWnd_message, WM_PAINT, INITMESSAGE_FAIL_D3D, 0L);
		UpdateWindow( hWnd_message );
		waitQuitLoop( hWnd );
	}
	SendMessage(hWnd_message, WM_PAINT, INITMESSAGE_SUCCESS_D3D, 0L);
	SendMessage(hWnd_message, WM_PAINT, INITMESSAGE_SUCCESS_ALL, 0L);
	UpdateWindow( hWnd_message );


	Sleep(2000);
	DestroyWindow(hWnd_message);

	// main loop
	//PeekMessage( &msg, NULL, 0U, 0U, PM_NOREMOVE );

	while(WM_QUIT != msg.message)
	{
		bGotMsg = ( PeekMessage( &msg, NULL, 0U, 0U, PM_REMOVE ) != 0 );
		if( bGotMsg )
		{
			// Translate and dispatch the message
			if( 0 == TranslateAccelerator( hWnd, NULL, &msg ) )
			{
				TranslateMessage( &msg );
				DispatchMessage( &msg );
			}
		}
		else
		{
			//if there is no message to process, do application tasks.

			if(g_isShowingCalResult)
			{ //show calibration result.
				drawCalResult(g_DataCounter, g_EyeData, g_CalPointData, g_NumCalPoint, g_CalPointList, g_CalibrationArea);
			}
			else if(getCameraImage( )==S_OK)
			{ //retrieve camera image and process it.
				int res;
				double detectionResults[8], TimeImageAquired;
				LARGE_INTEGER ct;
				
				QueryPerformanceCounter(&ct);
				TimeImageAquired = 1000 * ((double)(ct.QuadPart - g_RecStartTime.QuadPart) / g_CounterFreq.QuadPart);

				if(g_RecordingMode==RECORDING_MONOCULAR){
					res = detectPupilPurkinjeMono(g_Threshold, g_PurkinjeSearchArea, g_PurkinjeThreshold, g_PurkinjeExcludeArea, g_MinPoints, g_MaxPoints, detectionResults);
					if(res!=S_PUPIL_PURKINJE)
					{
						detectionResults[MONO_PUPIL_X] = detectionResults[MONO_PUPIL_Y] = res;
						detectionResults[MONO_PURKINJE_X] = detectionResults[MONO_PURKINJE_Y] = res;
					}
					getGazeMono(detectionResults, TimeImageAquired);
				}else{
					res = detectPupilPurkinjeBin(g_Threshold, g_PurkinjeSearchArea, g_PurkinjeThreshold, g_PurkinjeExcludeArea, g_MinPoints, g_MaxPoints, detectionResults);
					if(res!=S_PUPIL_PURKINJE)
					{
						detectionResults[BIN_PUPIL_LX] = detectionResults[BIN_PUPIL_LY] = res;
						detectionResults[BIN_PURKINJE_LX] = detectionResults[BIN_PURKINJE_LY] = res;
						detectionResults[BIN_PUPIL_RX] = detectionResults[BIN_PUPIL_RY] = res;
						detectionResults[BIN_PURKINJE_RX] = detectionResults[BIN_PURKINJE_RY] = res;
					}
					getGazeBin(detectionResults, TimeImageAquired);
				}

			}

			if(!g_isRecording)
			{ // if it is not under recording, flip screen in a regular way.
				render();
			}
			/* 2012/3/6 don't update screen while recording.
			else
			{ // if it is under recording, flip screen without waiting VSYNC.
				LARGE_INTEGER ct;
				QueryPerformanceCounter(&ct);
				if((double)((ct.QuadPart-g_PrevRenderTime.QuadPart)/g_CounterFreq.QuadPart)>0.016) //16msec
				{
					RenderWhileRecording();
					g_PrevRenderTime = ct;
				}
			}*/
		}

	}

	//end mainloop

    UnregisterClass( "GazeTracker", wc.hInstance );
    return 0;
}

/*!
clearData: clear data buffer.

This function should be called before starting calibration, validation and recording.

@return No value is returned.
*/
void clearData(void)
{
	int i;
	for(i=0; i<g_NumCalPoint; i++)
	{
		g_CalPointData[i][0] = 0;
		g_CalPointData[i][0] = 0;
	}

	for(i=0; i<g_DataCounter; i++)
	{
		g_EyeData[i][0] = 0;
		g_EyeData[i][1] = 0;
		g_EyeData[i][2] = 0;
		g_EyeData[i][3] = 0;
	}

	g_NumCalPoint = 0;
	g_DataCounter = 0;
}

/*!
startCalibration: initialize calibration procedures.

This function must be called when starting calibration.

@param[in] x1 left of the calibration area.
@param[in] y1 top of the calibration area.
@param[in] x2 right of the calibration area.
@param[in] y2 bottom of the calibration area.
@return No value is returned.
*/
void startCalibration(int x1, int y1, int x2, int y2)
{
	g_CalibrationArea.left = x1;
	g_CalibrationArea.top = y1;
	g_CalibrationArea.right = x2;
	g_CalibrationArea.bottom = y2;
	if(!g_isRecording && !g_isValidating && !g_isCalibrating){
		clearData();
		g_isCalibrating = true;
		g_isShowingCalResult = false; //erase calibration result screen.
	    g_CalSamplesAtCurrentPoint = 0;
	}
}

/*!
startCalibration: finish calibration procedures.

This function must be called when terminating calibration.

@return No value is returned.
*/
void endCalibration(void)
{
	if(g_RecordingMode==RECORDING_MONOCULAR){
		estimateParametersMono( g_DataCounter, g_EyeData, g_CalPointData );
		setCalibrationResults( g_DataCounter, g_EyeData, g_CalPointData, g_CalGoodness, g_CalMaxError, g_CalMeanError);
	}else{
		estimateParametersBin( g_DataCounter, g_EyeData, g_CalPointData );
		/*TODO*/
		setCalibrationResults( g_DataCounter, g_EyeData, g_CalPointData, g_CalGoodness, g_CalMaxError, g_CalMeanError);
	}

	g_isCalibrating=false;
	g_isCalibrated = true;
	g_isShowingCalResult = true;
}

/*!
getCalSample: start sampling calibration data

This function must be called when the calibration target jumped to a new position.
This function is called from sockProcess() when sockProcess() received "getCalSample" command.

@param[in] x position of the target.
@param[in] y position of the target.
@return No value is returned.
@todo currently g_CalSamplesAtCurrentPoint is initialized to 10. This value should be customizable.
*/
void getCalSample(double x, double y)
{
	g_CalPointList[g_NumCalPoint][0] = x;
	g_CalPointList[g_NumCalPoint][1] = y;
	g_CurrentCalPoint[0] = x;
	g_CurrentCalPoint[1] = y;
	g_NumCalPoint++;
    g_CalSamplesAtCurrentPoint = 10;
}

/*!
startValidation: initialize validation procedures.

This function must be called when starting validation.

@param[in] x1 left of the validation area.
@param[in] y1 top of the validation area.
@param[in] x2 right of the validation area.
@param[in] y2 bottom of the validation area.
@return No value is returned.
*/
void startValidation(int x1, int y1, int x2, int y2)
{
	g_CalibrationArea.left = x1;
	g_CalibrationArea.top = y1;
	g_CalibrationArea.right = x2;
	g_CalibrationArea.bottom = y2;
	if(!g_isRecording && !g_isValidating && !g_isCalibrating){ //ready to start calibration?
		clearData();
		g_isValidating = true;
		g_isShowingCalResult = false;
	    g_CalSamplesAtCurrentPoint = 0;
	}
}

/*!
endValidation: finish validation procedures.

This function must be called when terminating validation.

@return No value is returned.
*/
void endValidation(void)
{
	setCalibrationResults( g_DataCounter, g_EyeData, g_CalPointData, g_CalGoodness, g_CalMaxError, g_CalMeanError);

	g_isValidating=false;
	g_isShowingCalResult = true;
}

/*!
getValSample: start sampling validation data

This function must be called when the validation target jumped to a new position.
This function is called from sockProcess() when sockProcess() received "getValSample" command.

@param[in] x position of the target.
@param[in] y position of the target.
@return No value is returned.
@todo number of samples should be customizable.
@sa getCalSample
*/
void getValSample(double x, double y)
{
	getCalSample(x, y);
}


/*!
toggleCalRelsut: toggle camera preview and calibration result dislpay.
This function is called from sockProcess() when sockProcess() received "toggleCalResult" command.

@param[in] x position of the target.
@param[in] y position of the target.
@return No value is returned.
@todo number of samples should be customizable.
*/

void toggleCalResult(void)
{
	if(g_isCalibrated)
	{
		g_isShowingCalResult = !g_isShowingCalResult;
	}
}


/*!
startRecording: initialize recording procedures.

This function must be called when starting recording.
Output #START_REC, #MESSAGE, #XPARAM and #YPARAM to the data file.
This function is called from sockProcess() when sockProcess() received "startRecording" command.

@param[in] message Message text to be inserted to the data file.
@return No value is returned.
*/
void startRecording(char* message)
{
	time_t t;
	errno_t e;
	struct tm ltm;

	if(g_isCalibrated){ //if calibration has finished and recording has not been started, then start recording.
		clearData();
		
		g_DataCounter = 0;
		g_MessageEnd = 0;
		g_isRecording = true;
		g_isShowingCameraImage = false;
		g_isShowingCalResult = false;

		if(g_DataFP!=NULL)
		{
			//draw message on calimage
			drawRecordingMessage();
			renderBeforeRecording();

			time(&t);
			e = localtime_s(&ltm, &t);
			fprintf_s(g_DataFP,"#START_REC,%d,%d,%d,%d,%d,%d\n",ltm.tm_year+1900,ltm.tm_mon+1,ltm.tm_mday,ltm.tm_hour,ltm.tm_min,ltm.tm_sec);
			if(message[0]!=NULL)
			{
				fprintf_s(g_DataFP,"#MESSAGE,0,%s\n",message);
			}
			if(g_RecordingMode==RECORDING_MONOCULAR){
				fprintf_s(g_DataFP,"#XPARAM,%f,%f,%f\n",g_ParamX[0],g_ParamX[1],g_ParamX[2]);
				fprintf_s(g_DataFP,"#YPARAM,%f,%f,%f\n",g_ParamY[0],g_ParamY[1],g_ParamY[2]);
			}else{
				fprintf_s(g_DataFP,"#XPARAM,%f,%f,%f,%f,%f,%f\n",g_ParamX[0],g_ParamX[1],g_ParamX[2],g_ParamX[3],g_ParamX[4],g_ParamX[5]);
				fprintf_s(g_DataFP,"#YPARAM,%f,%f,%f,%f,%f,%f\n",g_ParamY[0],g_ParamY[1],g_ParamY[2],g_ParamY[3],g_ParamY[4],g_ParamY[5]);
			}
		}

		QueryPerformanceCounter(&g_RecStartTime);
	}
}

/*!
stopRecording: terminate recording procedures.

This function is called from sockProcess() when sockProcess() received "stopRecording" command.
Call flushGazeData(), output #MESSAGE and then output #STOP_REC.

@param[in] message Message text to be inserted to the data file.
@return No value is returned.
*/
void stopRecording(char* message)
{
	if(g_DataFP!=NULL)
	{
		flushGazeData();
		
		if(g_MessageEnd>0)
		{
			fprintf_s(g_DataFP,"%s",g_MessageBuffer);
		}
		if(message[0]!=NULL)
		{
			LARGE_INTEGER ct;
			double ctd;
			QueryPerformanceCounter(&ct);
			ctd = 1000 * ((double)(ct.QuadPart - g_RecStartTime.QuadPart) / g_CounterFreq.QuadPart);
			fprintf_s(g_DataFP,"#MESSAGE,%.3f,%s\n",ctd,message);
		}
		fprintf_s(g_DataFP,"#STOP_REC\n");
		fflush(g_DataFP); //force writing.
	}
	
	g_isRecording = false;
	g_isShowingCameraImage = true;
}

/*!
openDataFile: open data file.

This function is called from sockProcess() when sockProcess() received "openDataFile" command.
If file has already been opned, close it and open it again with overwrite mode.
As a result, contents of existing file is lost.

@param[in] filename Name of the data file.
@return No value is returned.
@todo avoid overwriting (?)
*/
void openDataFile(char* filename)
{
	char buff[512];
	strcpy_s(buff,sizeof(buff),g_DataPath);
	strcat_s(buff,sizeof(buff),"\\");
	strcat_s(buff,sizeof(buff),filename);

	if(g_DataFP!=NULL) //if data file has already been opened, close it.
	{
		fflush(g_DataFP);
		fclose(g_DataFP);
	}

	fopen_s(&g_DataFP,buff,"w");
}

/*!
closeDataFile: open data file.

This function is called from sockProcess() when sockProcess() received "closeDataFile" command.

@param[in] filename Name of the data file.
@return No value is returned.
*/
void closeDataFile(void)
{
	if(g_DataFP!=NULL)
	{
		fflush(g_DataFP);
		fclose(g_DataFP);
		g_DataFP = NULL;
	}
}

/*!
insertMessage: insert message to the message list.

This function is called from sockProcess() when sockProcess() received "insertMessage" command.
Usually, messages are written to the data file when recording is stopped, however,
if number of messages reached to MAXMESSAGE, messages are written to the file immediately.

@param[in] message Message text.
@return No value is returned.
*/
void insertMessage(char* message)
{
	LARGE_INTEGER ct;
	double ctd;
	QueryPerformanceCounter(&ct);
	ctd = 1000 * ((double)(ct.QuadPart - g_RecStartTime.QuadPart) / g_CounterFreq.QuadPart);
	g_MessageEnd += sprintf_s(g_MessageBuffer+g_MessageEnd,MAXMESSAGE-g_MessageEnd,"#MESSAGE,%.3f,%s\n",ctd,message);
	//check overflow
	if(MAXMESSAGE-g_MessageEnd < 128)
	{
		fprintf_s(g_DataFP,"%s",g_MessageBuffer);
		fprintf_s(g_DataFP,"#OVERFLOW_FLUSH_MESSAGES,%.3f\n",ctd);
		fflush(g_DataFP);
		g_MessageEnd = 0;
	}
}

/*!
insertSettings: insert message to the message list.

This function is called from sockProcess() when sockProcess() received "insertSettings" command.

@param[in] settings.
@return No value is returned.
*/
void insertSettings(char* settings)
{
	char* p1 = settings;
	char* p2;

	if(g_DataFP!=NULL)
	{
		while(true)
		{
			p2 = strstr(p1,"\\");
			if(p2==NULL){
				fprintf_s(g_DataFP,"%s\n",p1);
				break;
			}
			else
			{
				*p2 = NULL;
				fprintf_s(g_DataFP,"%s\n",p1);
				p1 = p2+1;
			}
		}
		
		fflush(g_DataFP);
	}
}


/*!
connectionClosed: Stop recording, calibration and validation when connection is unexpectedly closed.

@return No value is returned.
*/
void connectionClosed(void)
{
	if(g_isRecording)
	{
		stopRecording("ConnectionClosed");
	}
	else if(g_isCalibrating)
	{
		endCalibration();
	}
	else if(g_isValidating)
	{
		endValidation();
	}

}

/*!
getEyePosition: get current eye position.

This function is called from sockProcess() when sockProcess() received "getEyePosition" command.

@param[out] pos.
@return No value is returned.
*/
void getEyePosition(double* pos)
{
	if(g_RecordingMode==RECORDING_MONOCULAR){
		pos[0] = g_CurrentEyeData[MONO_X];
		pos[1] = g_CurrentEyeData[MONO_Y];
	}else{
		pos[0] = g_CurrentEyeData[BIN_LX];
		pos[1] = g_CurrentEyeData[BIN_LY];
		pos[2] = g_CurrentEyeData[BIN_RX];
		pos[3] = g_CurrentEyeData[BIN_RY];
	}
}

/*!
getCalibrationResults: get calibration error.

This function is called from sockProcess() when sockProcess() received "getCalResults" command.

@param[out] Goodness double Goodness of calibration results, defined as a ratio of linear regression coefficients to screen size.
.
@param[out] MaxError Maximum calibration error.
@param[out] MeanError Mean calibration error.
@return No value is returned.
*/
void getCalibrationResults( double *Goodness, double *MaxError, double *MeanError )
{
	if(g_RecordingMode==RECORDING_MONOCULAR){
		Goodness[MONO_X] = g_CalGoodness[MONO_X];
		Goodness[MONO_Y] = g_CalGoodness[MONO_Y];
		MaxError[MONO_1] = g_CalMaxError[MONO_1];
		MeanError[MONO_1] = g_CalMeanError[MONO_1];
	}else{
		Goodness[BIN_LX] = g_CalGoodness[BIN_LX];
		Goodness[BIN_LY] = g_CalGoodness[BIN_LY];
		Goodness[BIN_RX] = g_CalGoodness[BIN_RX];
		Goodness[BIN_RY] = g_CalGoodness[BIN_RY];
		MaxError[BIN_L] = g_CalMaxError[BIN_L];
		MaxError[BIN_R] = g_CalMaxError[BIN_R];
		MeanError[BIN_L] = g_CalMeanError[BIN_L];
		MeanError[BIN_R] = g_CalMeanError[BIN_R];
	}
}

/*!
getCalibrationResults: get detailed calibration error.

Pair of position of calibration/validation target point and recorded gaze position is returned as a string of comma-separated values
This function is called from sockProcess() when sockProcess() received "getCalResultsDetail" command.

@param[out] errorstr 
@param[in] size Size of errorstr buffer.
@param[out] len Length of the string written to errorstr buffer.

@return No value is returned.
*/
void getCalibrationResultsDetail( char* errorstr, int size, int* len)
{
	char* dstbuf = errorstr;
	int s = size;
	int idx,l;
	double xy[4];

    for(idx=0; idx<g_DataCounter; idx++)
	{
		if(g_RecordingMode==RECORDING_MONOCULAR){ //monocular
			getGazePositionMono(g_EyeData[idx], xy);
			l = sprintf_s(dstbuf, s, "%.0f,%.0f,%.0f,%.0f,",g_CalPointData[idx][0],g_CalPointData[idx][1],xy[MONO_X],xy[MONO_Y]);
		}else{ //binocular
			getGazePositionBin(g_EyeData[idx], xy);
			l = sprintf_s(dstbuf, s, "%.0f,%.0f,%.0f,%.0f,%.0f,%.0f,",g_CalPointData[idx][0],g_CalPointData[idx][1],xy[BIN_LX],xy[BIN_LY],xy[BIN_RX],xy[BIN_RY]);
		}
		dstbuf = dstbuf+l;
		s -= l;
		if(s<=1) break; //check overflow
	}

	*len = size-s;
	errorstr[*len-1] = '#';
}


/*!
getCurrentMenuString: get current menu text.

This function is called from sockProcess() when sockProcess() received "getCurrMenu" command.

@param[out] p Pointer to the buffer to which menu text is written.
@param[in] maxlen Size of buffer pointed by p.
@return No value is returned.
*/
void getCurrentMenuString(char *p, int maxlen)
{
	sprintf_s(p,maxlen,"%s", g_MenuString[g_CurrentMenuPosition]);
}

