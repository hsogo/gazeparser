/*!
@file tcpipcom.cpp
@author Hiroyuki Sogo
@copyright GNU General Public License (GPL) version 3.

@brief Functions concern TCP/IP communication are defined.

@date 2012/03/23
- Custom menu is supported.
*/

#ifdef _WIN32
#include	<Winsock2.h>
#else
#include	<arpa/inet.h>
#endif

#include	"GazeTrackerCommon.h"
#include	<SDL/SDL_net.h>
#include	<SDL/SDL.h>
#include	<stdio.h>
#include	<fstream>

#define RECV_BUFFER_SIZE	1024

TCPsocket g_SockRecv; /*!< Socket for receiving */
TCPsocket g_SockSend; /*!< Socket for sending */
TCPsocket g_SockServ; /*!< Socket for service */

SDLNet_SocketSet g_SocketSet;

unsigned char* g_SendImageBuffer;  /*!< Buffer for sending camera image. Additional 1 byte is necessary for the END code.*/
int g_Received; /*!< */

/*!
sockInit: Initialize socket.

@return int
@retval S_OK
@retval E_FAIL
*/
int sockInit(void)
{
	SDLNet_Init();
	g_SocketSet = SDLNet_AllocSocketSet(1);
	if(!g_SocketSet){
		g_LogFS << "ERROR: failed to allocate socket set" << std::endl;
		return E_FAIL;
	}

    return S_OK;
}

/*!
sockClose: Close sockets.

@return int
@retval S_OK
*/
int sockClose(void)
{
	SDLNet_TCP_Close(g_SockRecv); 
	SDLNet_TCP_Close(g_SockSend);
	g_SockRecv = NULL;
	g_SockSend = NULL;

	return S_OK;
}

/*!
sockConnect: Connect socket to the client PC to send data.

@param[in] host Client PC's address.
@return int
@retval S_OK
@retval E_FAIL
*/
int sockConnect(const char* host)
{
	IPaddress ip;
	if(SDLNet_ResolveHost(&ip, host, g_PortSend)==-1){
		g_LogFS << "ERROR: failed to resolve host (" << host << ")" << std::endl;
		return E_FAIL;
	}

	g_SockSend= SDLNet_TCP_Open(&ip);
	if(!g_SockSend){
		g_LogFS << "ERROR: failed to open sending socket" << std::endl;
		return E_FAIL;
	}
	g_LogFS << "open sending socket" << std::endl;

    return S_OK;
}

int sockConnectIP(IPaddress* ip)
{
	ip->port = htons(g_PortSend);

	g_SockSend= SDLNet_TCP_Open(ip);
	if(!g_SockSend){
		g_LogFS << "ERROR: failed to open sending socket" << std::endl;
		return E_FAIL;
	}
	g_LogFS << "open sending socket" << std::endl;

    return S_OK;
}

/*!
sockAccept: Accept connection request from the client PC.

@return int
@retval S_OK
@retval E_FAIL
*/
int sockAccept(void)
{
	IPaddress ip;
	if(SDLNet_ResolveHost(&ip, NULL, g_PortRecv)==-1){
		g_LogFS << "ERROR: failed to resolve host" << std::endl;
		return E_FAIL;
	}

	g_SockServ= SDLNet_TCP_Open(&ip);
	if(!g_SockServ){
		g_LogFS << "ERROR: failed to open server socket" << std::endl;
		return E_FAIL;
	}

	g_LogFS << "open server socket" << std::endl;
    return S_OK;
}

/*!
sockProcess: Process received data.

This function parses commands sent from the Client PC and call appropriate function mainly defined in GazeParserMain.cpp.

@param[in] hWnd Window handle.
@param[in] lParam received message.
@return int
@retval S_OK
@retval E_FAIL
*/
int sockProcess(void)
{
	char buff[RECV_BUFFER_SIZE];
	SDL_Event sdlEvent;

	//check accepted
	if(!g_SockRecv)
	{
		g_SockRecv = SDLNet_TCP_Accept(g_SockServ);

		if(g_SockRecv){
			g_LogFS << "open receiving socket" << std::endl;
			SDLNet_TCP_AddSocket(g_SocketSet, g_SockRecv);
			IPaddress* remote_ip;
			remote_ip = SDLNet_TCP_GetPeerAddress(g_SockRecv);
			if(!remote_ip){
				g_LogFS << "could not get remote IP address" << std::endl;
				SDLNet_TCP_Close(g_SockRecv);
				g_SockRecv = NULL;
				g_LogFS << "close receiving socket" << std::endl;
			}else{
				if(FAILED(sockConnectIP(remote_ip)))
				{
					SDLNet_TCP_Close(g_SockRecv);
					g_SockRecv = NULL;
					g_LogFS << "close receiving socket" << std::endl;
				}
			}
		}
	}

	int numReady;
	numReady = SDLNet_CheckSockets(g_SocketSet,0);
	if(numReady>0)
	{
		if(SDLNet_SocketReady(g_SockRecv))
		{
			g_Received = SDLNet_TCP_Recv(g_SockRecv, buff, RECV_BUFFER_SIZE);
			if(g_Received>0)
			{
				int nextp=0;
				while(nextp<g_Received){
					if(strcmp(buff+nextp,"key_Q")==0){
						sdlEvent.type = SDL_KEYDOWN;
						sdlEvent.key.keysym.sym = SDLK_q;
						SDL_PushEvent(&sdlEvent);
						while(buff[nextp]!=0) nextp++;
						nextp++;
					}
					else if(strcmp(buff+nextp,"key_UP")==0)
					{
						sdlEvent.type = SDL_KEYDOWN;
						sdlEvent.key.keysym.sym = SDLK_UP;
						SDL_PushEvent(&sdlEvent);
						while(buff[nextp]!=0) nextp++;
						nextp++;
					}
					else if(strcmp(buff+nextp,"key_DOWN")==0)
					{
						sdlEvent.type = SDL_KEYDOWN;
						sdlEvent.key.keysym.sym = SDLK_DOWN;
						SDL_PushEvent(&sdlEvent);
						while(buff[nextp]!=0) nextp++;
						nextp++;
					}
					else if(strcmp(buff+nextp,"key_LEFT")==0)
					{
						sdlEvent.type = SDL_KEYDOWN;
						sdlEvent.key.keysym.sym = SDLK_LEFT;
						SDL_PushEvent(&sdlEvent);
						while(buff[nextp]!=0) nextp++;
						nextp++;
					}
					else if(strcmp(buff+nextp,"key_RIGHT")==0)
					{
						sdlEvent.type = SDL_KEYDOWN;
						sdlEvent.key.keysym.sym = SDLK_RIGHT;
						SDL_PushEvent(&sdlEvent);
						while(buff[nextp]!=0) nextp++;
						nextp++;
					}
					else if(strcmp(buff+nextp,"getImageData")==0)
					{
						int index;
						for(int y=0; y<g_ROIHeight; y++){
							for(int x=0; x<g_ROIWidth; x++){
								index = g_ROIWidth*y+x;
								g_SendImageBuffer[index] = (unsigned)(g_pCameraTextureBuffer[
								        g_CameraWidth*(y+(g_CameraHeight-g_ROIHeight)/2)+
								                      (x+(g_CameraWidth-g_ROIWidth)/2)] & 0x000000ff);
								if(g_SendImageBuffer[index]==255){
									g_SendImageBuffer[index] = 254;
								}else if(g_SendImageBuffer[index] < g_Threshold){
									g_SendImageBuffer[index] = 0;
								}
							}
						}
						
						g_SendImageBuffer[index] = 255;
						SDLNet_TCP_Send(g_SockSend, (char*)g_SendImageBuffer, g_ROIWidth*g_ROIHeight+1);

						while(buff[nextp]!=0) nextp++;
						nextp++;
					}
					else if(strcmp(buff+nextp,"startCal")==0)
					{
						char* param = buff+nextp+9;
						char* p;
						int x1,y1,x2,y2;

						x1 = strtol(param, &p, 10);
						p++;
						y1 = strtol(p, &p, 10);
						p++;
						x2 = strtol(p, &p, 10);
						p++;
						y2 = strtol(p, &p, 10);

						startCalibration(x1,y1,x2,y2);

						while(buff[nextp]!=0) nextp++;
						nextp++;
						while(buff[nextp]!=0) nextp++;
						nextp++;
					}
					else if(strcmp(buff+nextp,"getCalSample")==0)
					{
						char* param = buff+nextp+13;
						char* p;
						double x,y;

						x = strtod(param, &p);
						p++;
						y = strtod(p, &p);
						getCalSample(x,y);

						while(buff[nextp]!=0) nextp++;
						nextp++;
						while(buff[nextp]!=0) nextp++;
						nextp++;
					}
					else if(strcmp(buff+nextp,"endCal")==0)
					{
						endCalibration();

						while(buff[nextp]!=0) nextp++;
						nextp++;
					}
					else if(strcmp(buff+nextp,"startVal")==0)
					{
						char* param = buff+nextp+9;
						char* p;
						int x1,y1,x2,y2;

						x1 = strtol(param, &p, 10);
						p++;
						y1 = strtol(p, &p, 10);
						p++;
						x2 = strtol(p, &p, 10);
						p++;
						y2 = strtol(p, &p, 10);

						startValidation(x1,y1,x2,y2);

						while(buff[nextp]!=0) nextp++;
						nextp++;
						while(buff[nextp]!=0) nextp++;
						nextp++;
					}
					else if(strcmp(buff+nextp,"getValSample")==0)
					{
						char* param = buff+nextp+13;
						char* p;
						double x,y;

						x = strtod(param, &p);
						p++;
						y = strtod(p, &p);
						getValSample(x,y);

						while(buff[nextp]!=0) nextp++;
						nextp++;
						while(buff[nextp]!=0) nextp++;
						nextp++;
					}
					else if(strcmp(buff+nextp,"endVal")==0)
					{
						endValidation();

						while(buff[nextp]!=0) nextp++;
						nextp++;
					}
					else if(strcmp(buff+nextp,"toggleCalResult")==0)
					{
						toggleCalResult();

						while(buff[nextp]!=0) nextp++;
						nextp++;
					}
					else if(strcmp(buff+nextp,"startRecording")==0)
					{
						char* param = buff+nextp+15;
						startRecording(param);

						while(buff[nextp]!=0) nextp++;
						nextp++;
						while(buff[nextp]!=0) nextp++;
						nextp++;
					}
					else if(strcmp(buff+nextp,"stopRecording")==0)
					{
						char* param = buff+nextp+14;
						stopRecording(param);

						while(buff[nextp]!=0) nextp++;
						nextp++;
						while(buff[nextp]!=0) nextp++;
						nextp++;
					}
					else if(strcmp(buff+nextp,"openDataFile")==0)
					{
						char* param = buff+nextp+13;
						openDataFile(param);

						while(buff[nextp]!=0) nextp++;
						nextp++;
						while(buff[nextp]!=0) nextp++;
						nextp++;
					}
					else if(strcmp(buff+nextp,"closeDataFile")==0)
					{
						closeDataFile();

						while(buff[nextp]!=0) nextp++;
						nextp++;
					}
					else if(strcmp(buff+nextp,"insertMessage")==0)
					{
						char* param = buff+nextp+14;
						insertMessage(param);

						while(buff[nextp]!=0) nextp++;
						nextp++;
						while(buff[nextp]!=0) nextp++;
						nextp++;
					}
					else if(strcmp(buff+nextp,"getEyePosition")==0)
					{
						double pos[4];
						char posstr[64];
						int len;
						getEyePosition(pos);
						if(g_RecordingMode==RECORDING_MONOCULAR){
							len = snprintf(posstr,sizeof(posstr),"%.0f,%.0f#",pos[0],pos[1]);
						}else{
							len = snprintf(posstr,sizeof(posstr),"%.0f,%.0f,%.0f,%.0f#",pos[0],pos[1],pos[2],pos[3]);
						}
						SDLNet_TCP_Send(g_SockSend,posstr,len);

						while(buff[nextp]!=0) nextp++;
						nextp++;
					}
					else if(strcmp(buff+nextp,"getCalResults")==0)
					{
						int len;
						char posstr[128];
						double goodness[4],maxError[2],meanError[2];

						getCalibrationResults(goodness,maxError,meanError);

						if(g_RecordingMode==RECORDING_MONOCULAR){
							len = snprintf(posstr,sizeof(posstr),"%.2f,%.2f,%.2f,%.2f#",goodness[MONO_X],goodness[MONO_Y],meanError[MONO_1],maxError[MONO_1]);
						}else{
							len = snprintf(posstr,sizeof(posstr),"%.2f,%.2f,%.2f,%.2f,%.2f,%.2f,%.2f,%.2f#",
								goodness[BIN_LX],goodness[BIN_LY],meanError[BIN_L],maxError[BIN_LX],
								goodness[BIN_RX],goodness[BIN_RY],meanError[BIN_R],maxError[BIN_RX]);
						}

						SDLNet_TCP_Send(g_SockSend,posstr,len);

						while(buff[nextp]!=0) nextp++;
						nextp++;
					}
					else if(strcmp(buff+nextp,"getCalResultsDetail")==0)
					{
						int len;
						char errorstr[8192];

						getCalibrationResultsDetail(errorstr,sizeof(errorstr),&len);

						SDLNet_TCP_Send(g_SockSend,errorstr,len);

						while(buff[nextp]!=0) nextp++;
						nextp++;
					}
					else if(strcmp(buff+nextp,"getCurrMenu")==0)
					{
						int len;
						char tmpstr[63];
						char menustr[64];

						getCurrentMenuString(tmpstr,sizeof(tmpstr));
						len = snprintf(menustr,sizeof(menustr),"%s#",tmpstr);

						SDLNet_TCP_Send(g_SockSend,menustr,len);

						while(buff[nextp]!=0) nextp++;
						nextp++;
					}
					else if(strcmp(buff+nextp,"insertSettings")==0)
					{
						char* param = buff+nextp+15;
						insertSettings(param);

						while(buff[nextp]!=0) nextp++;
						nextp++;
						while(buff[nextp]!=0) nextp++;
						nextp++;
					}
					else if(strcmp(buff+nextp,"saveCameraImage")==0)
					{
						char* param = buff+nextp+16;
						saveCameraImage((const char*)param);

						while(buff[nextp]!=0) nextp++;
						nextp++;
						while(buff[nextp]!=0) nextp++;
						nextp++;
					}
					else if(strcmp(buff+nextp,"startMeasurement")==0)
					{
						startMeasurement();

						while(buff[nextp]!=0) nextp++;
						nextp++;
					}
					else if(strcmp(buff+nextp,"stopMeasurement")==0)
					{
						stopMeasurement();

						while(buff[nextp]!=0) nextp++;
						nextp++;
					}
					else if(strcmp(buff+nextp,"allowRendering")==0)
					{
						allowRendering();

						while(buff[nextp]!=0) nextp++;
						nextp++;
					}
					else if(strcmp(buff+nextp,"inhibitRendering")==0)
					{
						inhibitRendering();

						while(buff[nextp]!=0) nextp++;
						nextp++;
					}					
					else
					{
						return E_FAIL;
					}
				}
			}
			else
			{
				g_LogFS << "connection may be closed by peer" << std::endl;
				connectionClosed();
				SDLNet_TCP_DelSocket(g_SocketSet, g_SockRecv);
				sockClose();
			}
		}
	}

	return S_OK;
}

