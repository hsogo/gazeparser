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

#define RECV_BUFFER_SIZE	4096

TCPsocket g_SockRecv; /*!< Socket for receiving */
TCPsocket g_SockSend; /*!< Socket for sending */
TCPsocket g_SockServ; /*!< @deprecated Socket for service */

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

@date 2013/03/25 edit log message.
*/
int sockClose(void)
{
	g_LogFS << "Closing sockets... ";

	if(g_SockRecv){
		SDLNet_TCP_Close(g_SockRecv);
		SDLNet_TCP_DelSocket(g_SocketSet, g_SockRecv);
	}
	if(g_SockSend){
		SDLNet_TCP_Close(g_SockSend);
	}
	g_SockRecv = NULL;
	g_SockSend = NULL;

	g_LogFS << "OK." << std::endl;
	return S_OK;
}

/*!
sockConnect: Connect socket to the client PC to send data.

@@deprecated Use sockConnectIP instead.
@param[in] host Client PC's address.
@return int
@retval S_OK
@retval E_FAIL

@date 2013/03/25 edit log message.
*/
int sockConnect(const char* host)
{
	IPaddress ip;

	g_LogFS << "Opening sending socket... ";

	if(SDLNet_ResolveHost(&ip, host, g_PortSend)==-1){
		g_LogFS << "ERROR: failed to resolve host (" << host << ")" << std::endl;
		return E_FAIL;
	}

	g_SockSend= SDLNet_TCP_Open(&ip);
	if(!g_SockSend){
		g_LogFS << "ERROR: failed to open sending socket" << std::endl;
		return E_FAIL;
	}
	
	g_LogFS << "OK." << std::endl;

    return S_OK;
}

/*!
sockConnectIP: Connect socket to the client PC to send data.

@param[in] host Client PC's IP address.
@return int
@retval S_OK
@retval E_FAIL

@date 2013/03/25 edit log message.
*/
int sockConnectIP(IPaddress* ip)
{
	g_LogFS << "Open sending socket...";
	
	ip->port = htons(g_PortSend);
	
	g_SockSend= SDLNet_TCP_Open(ip);
	if(!g_SockSend){
		g_LogFS << std::endl << "ERROR: failed to open sending socket" << std::endl;
		return E_FAIL;
	}
	
	g_LogFS << "OK." << std::endl;
    return S_OK;
}

/*!
sockAccept: Accept connection request from the client PC.

@return int
@retval S_OK
@retval E_FAIL

@date 2013/03/25 edit log message.
*/
int sockAccept(void)
{
	IPaddress ip;
	
	g_LogFS << "Opening server socket... " ;
	
	if(SDLNet_ResolveHost(&ip, NULL, g_PortRecv)==-1){
		g_LogFS << std::endl << "ERROR: failed to resolve host" << std::endl;
		return E_FAIL;
	}

	g_SockServ= SDLNet_TCP_Open(&ip);
	if(!g_SockServ){
		g_LogFS << std::endl << "ERROR: failed to open server socket" << std::endl;
		return E_FAIL;
	}

	g_LogFS << "OK." << std::endl;
	
    return S_OK;
}

int seekNextCommand(char* buff, int nextp, int nSkip)
{
	for(int i=0; i<nSkip; i++)
	{
		while(buff[nextp]!=0 && nextp<=g_Received) nextp++;
		while(buff[nextp]==0 && nextp<=g_Received) nextp++;
		if(nextp>=g_Received) break;
	}

	return nextp;
}

/*!
sockProcess: Process received data.

This function parses commands sent from the Client PC and call appropriate function mainly defined in GazeParserMain.cpp.

@param[in] hWnd Window handle.
@param[in] lParam received message.
@return int
@retval S_OK
@retval E_FAIL

@date 2012/10/24 support 'samples' parameter of getCalSample and getValSample.
@date 2012/10/25
- MAXCALSAMPLEPERPOINT is used to limit number of samples in getCalSample and getValSample.
- Terminator of sending data is changed to '\0'.
@date 2012/11/02 
- "toggleCalResult" command receives a parameter which specifies on/off of calibration results.
- TCP/IP connection is closed when SDLNet_SocketReady() failed.
@date 2013/03/06
- "getEyePositionList" command is added.
@date 2013/03/08
- "getWholeEyePositionList" command is added.
@date 2015/03/05
- "saveCalResultsDetail" command is added.
*/
int sockProcess( void )
{
	char buff[RECV_BUFFER_SIZE];
	SDL_Event sdlEvent;

	//check accepted
	if(!g_SockRecv)
	{
		g_SockRecv = SDLNet_TCP_Accept(g_SockServ);

		if(g_SockRecv){
			g_LogFS << "Open receiving socket ... ";
			SDLNet_TCP_AddSocket(g_SocketSet, g_SockRecv);
			IPaddress* remote_ip;
			remote_ip = SDLNet_TCP_GetPeerAddress(g_SockRecv);
			if(!remote_ip){
				g_LogFS << std::endl << "ERROR: could not get remote IP address." << std::endl;
				SDLNet_TCP_Close(g_SockRecv);
				g_SockRecv = NULL;
				g_LogFS << "ERROR: close receiving socket." << std::endl;
			}else{
				g_LogFS << "OK." << std::endl; //continued from: "Open receiving socket..."
				char ipaddrStr[32];
				unsigned int rip;
				rip = ntohl(remote_ip->host);
				snprintf(ipaddrStr, sizeof(ipaddrStr), "%u.%u.%u.%u",
					(rip & 0xFF000000)>>24, (rip & 0x00FF0000)>>16,
					(rip & 0x0000FF00)>> 8, (rip & 0x000000FF)); 
				g_LogFS << "Client IP address is " << ipaddrStr << "." << std::endl;
				if(FAILED(sockConnectIP(remote_ip)))
				{
					g_LogFS << std::endl << "ERROR: could not connect to " << remote_ip << std::endl;
					SDLNet_TCP_Close(g_SockRecv);
					g_SockRecv = NULL;
					g_LogFS << "ERROR: close receiving socket." << std::endl;
				}
			}
		}
	}
	
	if(!g_SockRecv || !g_SockSend)
		return S_OK;
	
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
						
						nextp = seekNextCommand(buff,nextp,1);
					}
					else if(strcmp(buff+nextp,"key_UP")==0)
					{
						sdlEvent.type = SDL_KEYDOWN;
						sdlEvent.key.keysym.sym = SDLK_UP;
						SDL_PushEvent(&sdlEvent);
						
						nextp = seekNextCommand(buff,nextp,1);
					}
					else if(strcmp(buff+nextp,"key_DOWN")==0)
					{
						sdlEvent.type = SDL_KEYDOWN;
						sdlEvent.key.keysym.sym = SDLK_DOWN;
						SDL_PushEvent(&sdlEvent);
						
						nextp = seekNextCommand(buff,nextp,1);
					}
					else if(strcmp(buff+nextp,"key_LEFT")==0)
					{
						sdlEvent.type = SDL_KEYDOWN;
						sdlEvent.key.keysym.sym = SDLK_LEFT;
						SDL_PushEvent(&sdlEvent);
						
						nextp = seekNextCommand(buff,nextp,1);
					}
					else if(strcmp(buff+nextp,"key_RIGHT")==0)
					{
						sdlEvent.type = SDL_KEYDOWN;
						sdlEvent.key.keysym.sym = SDLK_RIGHT;
						SDL_PushEvent(&sdlEvent);
						
						nextp = seekNextCommand(buff,nextp,1);
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
								if(g_SendImageBuffer[index]==0){
									g_SendImageBuffer[index] = 1;
								}else if(g_SendImageBuffer[index] < g_Threshold){
									g_SendImageBuffer[index] = 1;
								}
							}
						}
						if(index+1 != g_ROIWidth*g_ROIHeight)
						{
							g_LogFS << "ERROR: Image size is not matched." << std::endl;
							index = g_ROIWidth*g_ROIHeight;
						}
						g_SendImageBuffer[index+1] = 0;
						SDLNet_TCP_Send(g_SockSend, (char*)g_SendImageBuffer, g_ROIWidth*g_ROIHeight+1);

						nextp = seekNextCommand(buff,nextp,1);
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

						nextp = seekNextCommand(buff,nextp,2);
					}
					else if(strcmp(buff+nextp,"getCalSample")==0)
					{
						char* param = buff+nextp+13;
						char* p;
						double x,y;
						int samples;

						x = strtod(param, &p);
						p++;
						y = strtod(p, &p);
						p++;
						samples = strtol(p, &p, 10);
						if(samples<=0) samples=1;
						if(samples>=MAXCALSAMPLEPERPOINT) samples = MAXCALSAMPLEPERPOINT;
						getCalSample(x,y,samples);

						nextp = seekNextCommand(buff,nextp,2);
					}
					else if(strcmp(buff+nextp,"endCal")==0)
					{
						endCalibration();

						nextp = seekNextCommand(buff,nextp,1);
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

						nextp = seekNextCommand(buff,nextp,2);
					}
					else if(strcmp(buff+nextp,"getValSample")==0)
					{
						char* param = buff+nextp+13;
						char* p;
						double x,y;
						int samples;

						x = strtod(param, &p);
						p++;
						y = strtod(p, &p);
						p++;
						samples = strtol(p, &p, 10);
						if(samples<=0) samples=1;
						if(samples>=MAXCALSAMPLEPERPOINT) samples=MAXCALSAMPLEPERPOINT;
						getValSample(x,y,samples);

						nextp = seekNextCommand(buff,nextp,2);
					}
					else if(strcmp(buff+nextp,"endVal")==0)
					{
						endValidation();

						nextp = seekNextCommand(buff,nextp,1);
					}
					else if(strcmp(buff+nextp,"toggleCalResult")==0)
					{
						char* param = buff+nextp+16;
						char* p;
					    int val;

						val = strtol(param, &p, 10);
						
						toggleCalResult(val);
						
						nextp = seekNextCommand(buff,nextp,2);
					}
					else if(strcmp(buff+nextp,"saveCalResultsDetail")==0)
					{
						saveCalResultsDetail();

						nextp = seekNextCommand(buff,nextp,1);
					}
					else if(strcmp(buff+nextp,"startRecording")==0)
					{
						char* param = buff+nextp+15;
						startRecording(param);

						nextp = seekNextCommand(buff,nextp,2);
					}
					else if(strcmp(buff+nextp,"stopRecording")==0)
					{
						char* param = buff+nextp+14;
						stopRecording(param);

						nextp = seekNextCommand(buff,nextp,2);
					}
					else if(strcmp(buff+nextp,"openDataFile")==0)
					{
						char* param = buff+nextp+13;
						char* p;
						int overwrite;
						
						nextp = seekNextCommand(buff,nextp,2);
						
						overwrite =strtol(buff+nextp,&p,10);
						openDataFile(param, overwrite);
						
						nextp = seekNextCommand(buff,nextp,1);
					}
					else if(strcmp(buff+nextp,"closeDataFile")==0)
					{
						closeDataFile();

						nextp = seekNextCommand(buff,nextp,1);
					}
					else if(strcmp(buff+nextp,"insertMessage")==0)
					{
						char* param = buff+nextp+14;
						insertMessage(param);

						nextp = seekNextCommand(buff,nextp,2);
					}
					else if(strcmp(buff+nextp,"getEyePosition")==0)
					{
						char* param = buff+nextp+15;
						char* p;
						int nSamples;
						double pos[6];
						char posstr[256];
						int len;

						nSamples = strtol(param, &p, 10);
						if(nSamples<1) nSamples=1;

						getEyePosition(pos, nSamples);

						if(g_RecordingMode==RECORDING_MONOCULAR){
							len = snprintf(posstr,sizeof(posstr)-1,"%.0f,%.0f,%.0f",pos[0],pos[1],pos[2]);
						}else{
							len = snprintf(posstr,sizeof(posstr)-1,"%.0f,%.0f,%.0f,%.0f,%.0f,%.0f",
								pos[0],pos[1],pos[2],pos[3],pos[4],pos[5]);
						}
						SDLNet_TCP_Send(g_SockSend,posstr,len+1);

						nextp = seekNextCommand(buff,nextp,2);
					}
					else if(strcmp(buff+nextp,"getEyePositionList")==0)
					{
						char* param = buff+nextp+19;
						char* p, *dstbuf;
						int val, len, s, numGet;
						bool bGetPupil;

						double pos[7];
						char posstr[8192];
						bool newDataOnly;

						val = strtol(param, &p, 10);
						if(*p=='1'){
							bGetPupil = true;
						}else{
							bGetPupil = false;
						}

						s=sizeof(posstr);
						dstbuf = posstr;
						numGet = 0;

						if(val<0){
							newDataOnly = true;
							val *= -1;
						}else{
							newDataOnly = false;
						}

						for(int offset=0; offset<val; offset++){
							if(FAILED(getPreviousEyePositionReverse(pos, offset, newDataOnly))) break;
							if(g_RecordingMode==RECORDING_MONOCULAR){
								if(bGetPupil)
									len = snprintf(dstbuf,s,"%.1f,%.1f,%.1f,%.1f,",
										pos[0],pos[1],pos[2],pos[3]);
								else
									len = snprintf(dstbuf,s,"%.1f,%.1f,%.1f,",
										pos[0],pos[1],pos[2]);
							}else{
								if(bGetPupil)
									len = snprintf(dstbuf,s,"%.1f,%.1f,%.1f,%.1f,%.1f,%.1f,%.1f,",
										pos[0],pos[1],pos[2],pos[3],pos[4],pos[5],pos[6]);
								else
									len = snprintf(dstbuf,s,"%.1f,%.1f,%.1f,%.1f,%.1f,",
										pos[0],pos[1],pos[2],pos[3],pos[4]);
							}
							numGet++;
							dstbuf = dstbuf+len;
							s -= len;
							if(s<=96){//check overflow
								len = sizeof(posstr)-s;
								SDLNet_TCP_Send(g_SockSend,posstr,len);
								s=sizeof(posstr);
								dstbuf=posstr;
							}
						}

						if(numGet<=0){ //no data.
							posstr[0]='\0';
							SDLNet_TCP_Send(g_SockSend,posstr,1);
						}

						updateLastSentDataCounter();

						if(s!=sizeof(posstr)){
							len = sizeof(posstr)-s;
							posstr[len-1]='\0'; //replace the last camma with \0
							SDLNet_TCP_Send(g_SockSend,posstr,len);
						}

						nextp = seekNextCommand(buff,nextp,3);
					}
					else if(strcmp(buff+nextp,"getWholeEyePositionList")==0){
						char* param = buff+nextp+24;
						char* dstbuf;
						int len, s, numGet;
						bool bGetPupil;

						double pos[7];
						char posstr[8192];

						if(param[0]=='1'){
							bGetPupil = true;
						}else{
							bGetPupil = false;
						}

						s=sizeof(posstr);
						dstbuf = posstr;
						numGet = 0;

						int offset=0;
						while(SUCCEEDED(getPreviousEyePositionForward(pos, offset))){
							if(g_RecordingMode==RECORDING_MONOCULAR){
								if(bGetPupil)
									len = snprintf(dstbuf,s,"%.1f,%.1f,%.1f,%.1f,",
										pos[0],pos[1],pos[2],pos[3]);
								else
									len = snprintf(dstbuf,s,"%.1f,%.1f,%.1f,",
										pos[0],pos[1],pos[2]);
							}else{
								if(bGetPupil)
									len = snprintf(dstbuf,s,"%.1f,%.1f,%.1f,%.1f,%.1f,%.1f,%.1f,",
										pos[0],pos[1],pos[2],pos[3],pos[4],pos[5],pos[6]);
								else
									len = snprintf(dstbuf,s,"%.1f,%.1f,%.1f,%.1f,%.1f,",
										pos[0],pos[1],pos[2],pos[3],pos[4]);
							}
							numGet++;
							dstbuf = dstbuf+len;
							s -= len;
							if(s<=96){//check overflow
								len = sizeof(posstr)-s;
								SDLNet_TCP_Send(g_SockSend,posstr,len);
								s=sizeof(posstr);
								dstbuf=posstr;
							}
							offset++;
						}

						if(numGet<=0){ //no data.
							posstr[0]='\0';
							SDLNet_TCP_Send(g_SockSend,posstr,1);
						}

						if(s!=sizeof(posstr)){
							len = sizeof(posstr)-s;
							posstr[len-1]='\0'; //replace the last camma with \0
							SDLNet_TCP_Send(g_SockSend,posstr,len);
						}

						nextp = seekNextCommand(buff,nextp,2);
					}
					else if(strcmp(buff+nextp,"getWholeMessageList")==0)
					{
						char *msgp;
						size_t len;
						msgp = getMessageBufferPointer();
						len = strlen(msgp);
						SDLNet_TCP_Send(g_SockSend,msgp,len+1); //send with terminator

						nextp = seekNextCommand(buff,nextp,1);
					}
					else if(strcmp(buff+nextp,"getCalResults")==0)
					{
						int len;
						char posstr[128];
						double goodness[4],maxError[2],meanError[2];

						getCalibrationResults(goodness,maxError,meanError);

						if(g_RecordingMode==RECORDING_MONOCULAR){
							len = snprintf(posstr,sizeof(posstr)-1,"%.2f,%.2f",
								meanError[MONO_1],maxError[MONO_1]);
						}else{
							len = snprintf(posstr,sizeof(posstr)-1,"%.2f,%.2f,%.2f,%.2f",
								meanError[BIN_L],maxError[BIN_L],meanError[BIN_R],maxError[BIN_R]);
						}

						SDLNet_TCP_Send(g_SockSend,posstr,len+1);

						nextp = seekNextCommand(buff,nextp,1);
					}
					else if(strcmp(buff+nextp,"getCalResultsDetail")==0)
					{
						int len;
						char errorstr[8192];

						getCalibrationResultsDetail(errorstr,sizeof(errorstr)-1,&len);
						//'\0' is already appended at getCalibrationResultsDetail
						if(len>0){
							SDLNet_TCP_Send(g_SockSend,errorstr,len);
						}else{
							//no calibration data
							errorstr[0]='\0';
							SDLNet_TCP_Send(g_SockSend,errorstr,1);
						}

						nextp = seekNextCommand(buff,nextp,1);
					}
					else if(strcmp(buff+nextp,"getCurrMenu")==0)
					{
						int len;
						char tmpstr[63];
						char menustr[64];

						getCurrentMenuString(tmpstr,sizeof(tmpstr));
						len = snprintf(menustr,sizeof(menustr),"%s",tmpstr);

						SDLNet_TCP_Send(g_SockSend,menustr,len+1);

						nextp = seekNextCommand(buff,nextp,1);
					}
					else if(strcmp(buff+nextp,"insertSettings")==0)
					{
						char* param = buff+nextp+15;
						insertSettings(param);

						nextp = seekNextCommand(buff,nextp,2);
					}
					else if(strcmp(buff+nextp,"saveCameraImage")==0)
					{
						char* param = buff+nextp+16;
						saveCameraImage((const char*)param);

						nextp = seekNextCommand(buff,nextp,2);
					}
					else if(strcmp(buff+nextp,"startMeasurement")==0)
					{
						startMeasurement();

						nextp = seekNextCommand(buff,nextp,1);
					}
					else if(strcmp(buff+nextp,"stopMeasurement")==0)
					{
						stopMeasurement();

						nextp = seekNextCommand(buff,nextp,1);
					}
					else if(strcmp(buff+nextp,"allowRendering")==0)
					{
						allowRendering();

						nextp = seekNextCommand(buff,nextp,1);
					}
					else if(strcmp(buff+nextp,"inhibitRendering")==0)
					{
						inhibitRendering();

						nextp = seekNextCommand(buff,nextp,1);
					}
					else if(strcmp(buff+nextp,"isBinocularMode")==0)
					{
						int len;
						char str[8];

						if(isBinocularMode()){
							len = snprintf(str,sizeof(str),"1");
						}else{
							len = snprintf(str,sizeof(str),"0");
						}
						SDLNet_TCP_Send(g_SockSend,str,len+1);

						nextp = seekNextCommand(buff,nextp,1);
					}
					else
					{
						g_LogFS << "WARNING: Unknown command (" << buff+nextp << ")" << std::endl;
						nextp = seekNextCommand(buff,nextp,1);
					}
				}
			}
			else
			{
				g_LogFS << "SDLNet_TCP_Recv() failed. connection may be closed by peer" << std::endl;
				connectionClosed();
				sockClose();
			}
		}
	}

	return S_OK;
}


