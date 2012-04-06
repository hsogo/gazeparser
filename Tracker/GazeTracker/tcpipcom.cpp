/*!
@file tcpipcom.cpp
@author Hiroyuki Sogo
@copyright GNU General Public License (GPL) version 3.

@brief Functions concern TCP/IP communication are defined.

@date 2012/03/23
- Custom menu is supported.
*/

#include	<windows.h>
#include	<winsock.h>
#include	"GazeTracker.h"

#include	<stdio.h>

#define RECV_PORT        10000
#define SEND_PORT        10001

#define RECV_BUFFER_SIZE	1024

SOCKET g_SockRecv = INVALID_SOCKET; /*!< Socket for receiving */
SOCKET g_SockSend = INVALID_SOCKET; /*!< Socket for sending */
SOCKET g_SockServ = INVALID_SOCKET; /*!< Socket for service */
HOSTENT *g_pHE; /*!< */

unsigned char* g_SendImageBuffer;  /*!< Buffer for sending camera image. Additional 1 byte is necessary for the END code.*/
int g_Received; /*!< */

/*!
sockInit: Initialize socket.

@return HRESULT
@retval S_OK
@retval E_FAIL
*/
HRESULT sockInit(HWND hWnd)
{
    WSADATA wsa;
    int ret;
    if((ret=WSAStartup(MAKEWORD(1,1), &wsa))){
		return E_FAIL;
	}
    return S_OK;
}

/*!
sockClose: Close sockets.

@return HRESULT
@retval S_OK
*/
HRESULT sockClose(void)
{
	closesocket(g_SockRecv); 
	closesocket(g_SockSend);

	return S_OK;
}

/*!
sockConnect: Connect socket to the client PC to send data.

@param[in] hWnd Window handle.
@param[in] host Client PC's address.
@return HRESULT
@retval S_OK
@retval E_FAIL
*/
HRESULT sockConnect(HWND hWnd, LPCSTR host)
{
    SOCKADDR_IN cl_sin;                                     //SOCKADDR_IN structure

    //open socket
    g_SockSend = socket(AF_INET, SOCK_STREAM, IPPROTO_TCP);       //failed to create socket
    if(g_SockSend==INVALID_SOCKET){
		return E_FAIL;
    }

    memset(&cl_sin, 0x00, sizeof(cl_sin));                  //initialize structure
    cl_sin.sin_family = AF_INET;                            //internet
    cl_sin.sin_port   = htons(SEND_PORT);                        //port number

    if(!(g_pHE=gethostbyname(host))){                         //getting address
        return E_FAIL;
    }
    memcpy(&cl_sin.sin_addr, g_pHE->h_addr, g_pHE->h_length);   //copy the address

    //setting asynchronous mode
    if(WSAAsyncSelect(g_SockSend, hWnd, WM_TCPSOCKET, FD_CONNECT)==SOCKET_ERROR){
        closesocket(g_SockSend);
        g_SockSend=INVALID_SOCKET;
        return E_FAIL;
    }

    //connecting
    if(connect(g_SockSend, (LPSOCKADDR)&cl_sin, sizeof(cl_sin))==SOCKET_ERROR){
        if(WSAGetLastError()!=WSAEWOULDBLOCK){
            closesocket(g_SockSend);
            g_SockSend=INVALID_SOCKET;
            return E_FAIL;
        }
    }
    return S_OK;
}


/*!
sockAccept: Accept connection request from the client PC.

@param[in] hWnd Window handle.
@return HRESULT
@retval S_OK
@retval E_FAIL
*/
HRESULT sockAccept(HWND hWnd)
{
    SOCKADDR_IN sv_sin;                                 //SOCKADDR_IN\‘¢‘Ì

    //socket for server
    g_SockServ = socket(AF_INET, SOCK_STREAM, IPPROTO_TCP);
    if(g_SockServ == INVALID_SOCKET){                      //failed to create socket
        return E_FAIL;
    }

    memset(&sv_sin, 0x00, sizeof(sv_sin));              //initialize structure
    sv_sin.sin_family      = AF_INET;                   //internet
    sv_sin.sin_port        = htons(RECV_PORT);               //port number
    sv_sin.sin_addr.s_addr = htonl(INADDR_ANY);         //setting address

    if(bind(g_SockServ, (LPSOCKADDR)&sv_sin, sizeof(sv_sin))==SOCKET_ERROR){
        closesocket(g_SockServ);
        g_SockServ = INVALID_SOCKET;
        return E_FAIL;
    }

    if(listen(g_SockServ, 1)==SOCKET_ERROR){               //failed to accept connection
        closesocket(g_SockServ);
        g_SockServ = INVALID_SOCKET;
        return E_FAIL;
    }

    //setting asynchronous mode
    if(WSAAsyncSelect(g_SockServ, hWnd, WM_TCPSOCKET, FD_ACCEPT)==SOCKET_ERROR){
        closesocket(g_SockServ);
        g_SockServ = INVALID_SOCKET;
		return E_FAIL;
    }
    return S_OK;
}

/*!
sockProcess: Process received data.

This function parses commands sent from the Client PC and call appropriate function mainly defined in GazeParserMain.cpp.

@param[in] hWnd Window handle.
@param[in] lParam received message.
@return HRESULT
@retval S_OK
@retval E_FAIL
*/
HRESULT sockProcess(HWND hWnd, LPARAM lParam)
{
	char buff[RECV_BUFFER_SIZE];

	if(WSAGETSELECTERROR(lParam)!=0)
		return E_FAIL;
	switch(WSAGETSELECTEVENT(lParam))
	{
	case FD_ACCEPT:
		//called when accepted.
		SOCKADDR_IN cl_sin;
		int len;
		len = sizeof(cl_sin);
		g_SockRecv = accept(g_SockServ,(LPSOCKADDR)&cl_sin,&len);
		WSAAsyncSelect(g_SockRecv, hWnd, WM_TCPSOCKET, FD_READ|FD_CLOSE);

		sockConnect(hWnd,inet_ntoa(cl_sin.sin_addr));
		break;

	case FD_READ:
		g_Received = recv(g_SockRecv, buff, RECV_BUFFER_SIZE, 0);
		if(g_Received>0)
		{
			int nextp=0;
			while(nextp<g_Received){
				if(strcmp(buff+nextp,"key_Q")==0){
					PostMessage(hWnd, WM_KEYDOWN, 'Q', NULL);
					while(buff[nextp]!=0) nextp++;
					nextp++;
				}
				else if(strcmp(buff+nextp,"key_UP")==0)
				{
					PostMessage(hWnd, WM_KEYDOWN, VK_UP, NULL);
					while(buff[nextp]!=0) nextp++;
					nextp++;
				}
				else if(strcmp(buff+nextp,"key_DOWN")==0)
				{
					PostMessage(hWnd, WM_KEYDOWN, VK_DOWN, NULL);				
					while(buff[nextp]!=0) nextp++;
					nextp++;
				}
				else if(strcmp(buff+nextp,"key_LEFT")==0)
				{
					PostMessage(hWnd, WM_KEYDOWN, VK_LEFT, NULL);
					while(buff[nextp]!=0) nextp++;
					nextp++;
				}
				else if(strcmp(buff+nextp,"key_RIGHT")==0)
				{
					PostMessage(hWnd, WM_KEYDOWN, VK_RIGHT, NULL);				
					while(buff[nextp]!=0) nextp++;
					nextp++;
				}
				else if(strcmp(buff+nextp,"getImageData")==0)
				{
					int index;
					for(int y = 0; y<g_ROIHeight; y++){
						for(int x=0; x<g_ROIWidth; x++){
							index = g_ROIWidth*y+x;
							g_SendImageBuffer[index] = (unsigned)(g_pCameraTextureBuffer[g_CameraWidth*(y+(g_CameraHeight-g_ROIHeight)/2)+(x+(g_CameraWidth-g_ROIWidth)/2)] & 0x000000ff);
							if(g_SendImageBuffer[index]==255){
								g_SendImageBuffer[index] = 254;
							}else if(g_SendImageBuffer[index] < g_Threshold){
								g_SendImageBuffer[index] = 0;
							}
						}
					}
					
					g_SendImageBuffer[index] = 255;
					send(g_SockSend, (char*)g_SendImageBuffer, g_ROIWidth*g_ROIHeight+1, 0);

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
					int flag;
					getEyePosition(pos);
					if(g_RecordingMode==RECORDING_MONOCULAR){
						len = sprintf_s(posstr,sizeof(posstr),"%.0f,%.0f#",pos[0],pos[1]);
					}else{
						len = sprintf_s(posstr,sizeof(posstr),"%.0f,%.0f,%.0f,%.0f#",pos[0],pos[1],pos[2],pos[3]);
					}
					flag = 1; //send with NO_DLAY mode.
					setsockopt(g_SockSend,IPPROTO_TCP,TCP_NODELAY,(char*)&flag, sizeof(flag));
					send(g_SockSend,posstr,len, 0);
					flag = 0; //exit from NO_DLAY mode.
					setsockopt(g_SockSend,IPPROTO_TCP,TCP_NODELAY,(char*)&flag, sizeof(flag));

					while(buff[nextp]!=0) nextp++;
					nextp++;
				}
				else if(strcmp(buff+nextp,"getCalResults")==0)
				{
					int len;
					int flag;
					char posstr[128];
					double goodness[4],maxError[2],meanError[2];

					getCalibrationResults(goodness,maxError,meanError);

					if(g_RecordingMode==RECORDING_MONOCULAR){
						len = sprintf_s(posstr,sizeof(posstr),"%.2f,%.2f,%.2f,%.2f#",goodness[MONO_X],goodness[MONO_Y],meanError[MONO_1],maxError[MONO_1]);
					}else{
						len = sprintf_s(posstr,sizeof(posstr),"%.2f,%.2f,%.2f,%.2f,%.2f,%.2f,%.2f,%.2f#",
							goodness[BIN_LX],goodness[BIN_LY],meanError[BIN_L],maxError[BIN_LX],
							goodness[BIN_RX],goodness[BIN_RY],meanError[BIN_R],maxError[BIN_RX]);
					}


					flag = 1; //send with NO_DLAY mode.
					setsockopt(g_SockSend,IPPROTO_TCP,TCP_NODELAY,(char*)&flag, sizeof(flag));
					send(g_SockSend,posstr,len, 0);
					flag = 0; //exit from NO_DLAY mode.
					setsockopt(g_SockSend,IPPROTO_TCP,TCP_NODELAY,(char*)&flag, sizeof(flag));

					while(buff[nextp]!=0) nextp++;
					nextp++;
				}
				else if(strcmp(buff+nextp,"getCalResultsDetail")==0)
				{
					int len;
					int flag;
					char errorstr[8192];

					getCalibrationResultsDetail(errorstr,sizeof(errorstr),&len);

					flag = 1; //send with NO_DLAY mode.
					setsockopt(g_SockSend,IPPROTO_TCP,TCP_NODELAY,(char*)&flag, sizeof(flag));
					send(g_SockSend,errorstr,len, 0);
					flag = 0; //exit from NO_DLAY mode.
					setsockopt(g_SockSend,IPPROTO_TCP,TCP_NODELAY,(char*)&flag, sizeof(flag));

					while(buff[nextp]!=0) nextp++;
					nextp++;
				}
				else if(strcmp(buff+nextp,"getCurrMenu")==0)
				{
					int len;
					int flag;
					char tmpstr[63];
					char menustr[64];

					getCurrentMenuString(tmpstr,sizeof(tmpstr));
					len = sprintf_s(menustr,sizeof(menustr),"%s#",tmpstr);

					flag = 1; //send with NO_DLAY mode.
					setsockopt(g_SockSend,IPPROTO_TCP,TCP_NODELAY,(char*)&flag, sizeof(flag));
					send(g_SockSend,menustr,len, 0);
					flag = 0; //exit from NO_DLAY mode.
					setsockopt(g_SockSend,IPPROTO_TCP,TCP_NODELAY,(char*)&flag, sizeof(flag));

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
					saveCameraImage(param);

					while(buff[nextp]!=0) nextp++;
					nextp++;
					while(buff[nextp]!=0) nextp++;
					nextp++;
				}
				else
				{
					return E_FAIL;
				}
			}
		}
		break;

	case FD_CONNECT:
		break;

	case FD_CLOSE:
		connectionClosed();
		break;
	}


	return S_OK;
}

