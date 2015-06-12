/*!
@file usbioUL.cpp
@author Hiroyuki Sogo
@copyright GNU General Public License (GPL) version 3.

@brief Functions for USB-IO support.
*/

#include <string>
#include <fstream>
#include <iostream>
#include <list>
#include "GazeTrackerCommon.h"

#include <cbw.h>

#define MAX_USB_AD_CHANNELS 8

int g_BoardNum = NO_USBIO;

int g_USBDIPort;

int g_numUSBADChannels = 0;
int g_ADResolution = 0;
int g_USBADChannelList[MAX_USB_AD_CHANNELS][2]; /*0: Channel number  1:AD range**/

bool g_useUSBIO = false;
bool g_useUSBThread = false;
bool g_runUSBThread = false;

DWORD g_latestADValue32[MAX_USB_AD_CHANNELS];
WORD g_latestADValue16[MAX_USB_AD_CHANNELS];
WORD g_latestDIValue;

DWORD* g_USBADBuffer32;
WORD* g_USBADBuffer16;
unsigned short* g_USBDIBuffer;


SDL_Thread *g_pUSBThread;

/* debug
double g_debug_buffer[1000];
int g_debug_counter=0;
debug */

int pollUSBIOThread(void *unused)
{
	int ULStat;
	int options=0;

	/* debug
	double t, prev;
	prev = getCurrentTime();
	debug */

	while(g_runUSBThread)
	{
		if(g_USBADBuffer32!=NULL)
		{
			for(int i=0; i<g_numUSBADChannels; i++){
				ULStat = cbAIn32(g_BoardNum, g_USBADChannelList[i][0],
					g_USBADChannelList[i][1], &g_latestADValue32[i], options);
			}
		}
		else if(g_USBADBuffer16!=NULL)
		{
			for(int i=0; i<g_numUSBADChannels; i++){
				ULStat = cbAIn(g_BoardNum, g_USBADChannelList[i][0],
					g_USBADChannelList[i][1], &g_latestADValue16[i]);
			}
		}
		if(g_USBDIBuffer!=NULL)
			ULStat = cbDIn(g_BoardNum, g_USBDIPort, &g_latestDIValue);

		/* debug
		t = getCurrentTime();
		g_debug_buffer[g_debug_counter] = t-prev;
		prev = t;
		g_debug_counter++;
		g_debug_counter = g_debug_counter % 1000;
		debug */
	}
	
	return 0;
}

/*!
getRangeValue: Convert range string to range value.

Converted range value is returned.
Following range strings are supported.

- BIP15VOLTS
- BIP10VOLTS
- BIP5VOLTS
- BIP2PT5VOLTS
- BIP1VOLTS
- UNI10VOLTS
- UNI5VOLTS
- UNI2PT5VOLTS

@param[in] rangestr
@return int
@retval BADRANGE if range string is unsupported.
*/
int getRangeValue(const char* rangestr)
{
	if(strcmp(rangestr,"BIP15VOLTS")==0)
		return BIP15VOLTS;
	else if(strcmp(rangestr,"BIP10VOLTS")==0)
		return BIP10VOLTS;
	else if(strcmp(rangestr,"BIP5VOLTS")==0)
		return BIP5VOLTS;
	else if(strcmp(rangestr,"BIP2PT5VOLTS")==0)
		return BIP2PT5VOLTS;
	else if(strcmp(rangestr,"BIP1VOLTS")==0)
		return BIP1VOLTS;
	else if(strcmp(rangestr,"UNI10VOLTS")==0)
		return UNI10VOLTS;
	else if(strcmp(rangestr,"UNI5VOLTS")==0)
		return UNI5VOLTS;
	else if(strcmp(rangestr,"UNI2PT5VOLTS")==0)
		return UNI2PT5VOLTS;
	else if(strcmp(rangestr,"UNI1VOLTS")==0)
		return UNI1VOLTS;

	return BADRANGE;
}

/*!
getPortValue: Convert port string to port value.

Converted port value is returned.
Following port strings are supported.

- FIRSTPORTA
- FIRSTPORTB
- FIRSTPORTCL
- FIRSTPORTC
- FIRSTPORTCH

@param[in] portstr
@return int
@retval BADPORTNUM if range string is unsupported.
*/
int getPortValue(const char*portstr)
{
	if(strcmp(portstr,"FIRSTPORTA")==0)
		return FIRSTPORTA;
	else if(strcmp(portstr,"FIRSTPORTB")==0)
		return FIRSTPORTB;
	else if(strcmp(portstr,"FIRSTPORTCL")==0)
		return FIRSTPORTCL;
	else if(strcmp(portstr,"FIRSTPORTC")==0)
		return FIRSTPORTC;
	else if(strcmp(portstr,"FIRSTPORTCH")==0)
		return FIRSTPORTCH;

	return BADPORTNUM;
}

/*!
splitString: Split string.

http://goodjob.boy.jp/chirashinoura/id/100.html

@param[in] targetstr
@param[in] delim
@return std::list
*/
std::list<std::string> splitString(std::string targetstr, std::string delim)
{
	std::list<std::string> res;
	int idx;

	while( (idx = targetstr.find_first_of(delim)) != std::string::npos )
	{
		if(idx>0)
		{
			res.push_back(targetstr.substr(0, idx));
		}
		targetstr = targetstr.substr(idx + 1);
	}
	if(targetstr.length()>0)
	{
		res.push_back(targetstr);
	}
	return res;
}


/*!
checkAD: Test whether AD channels are valid.

@return int
@retval S_OK
@retval E_FAIL
*/
int checkAD(void)
{
	int ULStat = 0;
	WORD DataValue = 0;
	DWORD DataValue32 = 0;
	int options = 0;

	cbGetConfig(BOARDINFO, g_BoardNum, 0, BIADRES, &g_ADResolution);
	if(ULStat!=NOERRORS){
		g_LogFS << "Could not get configuration for Boad " << g_USBIOBoard << "." << std::endl;
		return E_FAIL;
	}

	for(int i=0; i<g_numUSBADChannels; i++)
	{

		if(g_ADResolution>16){ //HighRes
			ULStat = cbAIn32(g_BoardNum, g_USBADChannelList[i][0], g_USBADChannelList[i][1], &DataValue32, options);
		}else{
			ULStat = cbAIn(g_BoardNum, g_USBADChannelList[i][0], g_USBADChannelList[i][1], &DataValue);
		}
		if(ULStat!=NOERRORS){
			g_LogFS << "Could not read AD channel " << g_USBADChannelList[i][0] << "." << std::endl;
			return E_FAIL;
		}
	}
	return S_OK;
}

/*!
checkDI: Test whether DI port is valid.

@return int
@retval S_OK
@retval E_FAIL
*/
int checkDI(void)
{
	int ULStat = 0;
	WORD DataValue = 0;

	ULStat = cbDConfigPort(g_BoardNum, g_USBDIPort, DIGITALIN);
	if(ULStat!=NOERRORS){
		g_LogFS << "Could not configure port (" << g_USBIOParamDI << ") as Digital input." << std::endl;
		return E_FAIL;
	}

	ULStat = cbDIn(g_BoardNum, g_USBDIPort, &DataValue);
	if(ULStat!=NOERRORS){
		g_LogFS << "Could not read Digital input port (" << g_USBIOParamDI << ")." << std::endl;
		return E_FAIL;
	}

	return S_OK;
}

/*!
startUSBThread

@return int
@retval S_OK
@retval E_FAIL
*/
int startUSBThread(void)
{
	g_runUSBThread = true;
	g_pUSBThread = SDL_CreateThread(pollUSBIOThread, NULL);
	if(g_pUSBThread==NULL)
	{
		g_LogFS << "ERROR: failed to start USB thread." << std::endl;
		g_runUSBThread = false;
		return E_FAIL;
	}
	else
	{
		g_LogFS << "Start USB polling Thread." << std::endl;
	}
	return S_OK;
}

/*!
startUSBThread
*/
void stopUSBThread(void)
{
	if(g_runUSBThread){
		g_runUSBThread = false;
		SDL_WaitThread(g_pUSBThread, NULL);
		g_LogFS << "USB polling thread is stopped." << std::endl;

		/* debug
		for(int i=0; i<1000; i++){
			g_LogFS << g_debug_buffer[i] << std::endl;
		}
		debug */
	}
}

void cleanupUSBIO(void)
{
	if(g_useUSBThread){
		stopUSBThread();
	}

    if( g_USBADBuffer32 != NULL )
	{
        free(g_USBADBuffer32);
		g_USBADBuffer32 = NULL;
	}

    if( g_USBADBuffer16 != NULL )
	{
        free(g_USBADBuffer16);
		g_USBADBuffer16 = NULL;
	}

    if( g_USBDIBuffer != NULL )
	{
        free(g_USBDIBuffer);
		g_USBDIBuffer = NULL;
	}
}

/*!
initUSBIO: Initialize USB-IO

This function do following tasks.

1. Read board number, AD and DI settings from parameter strings.
2. Poll AD and DI ports to test whether they work properly.
3. Allocate memory buffers to record polled data.

@return int
@retval S_OK
@retval E_FAIL
*/
int initUSBIO(void)
{
	char *p;
	std::list<std::string> params;
	std::list<std::string>::iterator iter;
	int chan,rangeval;

	// Board number
	g_BoardNum = strtol(g_USBIOBoard.c_str(),&p,10);
	if( cbFlashLED(g_BoardNum) != NOERRORS ){
		g_LogFS << "ERROR: Could not open USB IO board. Is board number (=" << g_USBIOBoard << ") bad?" << std::endl;
		return E_FAIL;
	}else{
		g_LogFS << "USB IO board " << g_USBIOBoard << " is opened." << std::endl;
	}

	// AD
	if(g_USBIOParamAD!="NONE" && g_USBIOParamAD!=""){
		params = splitString(g_USBIOParamAD, ";");
		g_numUSBADChannels = 0;
		iter = params.begin();
		while( iter != params.end())
		{
			if(g_numUSBADChannels>=MAX_USB_AD_CHANNELS){
				g_LogFS << "ERROR: Too many AD channels." << std::endl;
				return E_FAIL;
			}
			chan = strtol(iter->c_str(),&p,10);
			for(int i=0; i<g_numUSBADChannels; i++){
				if(g_USBADChannelList[i][0]==chan){
					g_LogFS << "ERROR: USB AD channel " << chan << " is duplicated." << std::endl;
					return E_FAIL;
				}
			}

			iter++;
			if(iter==params.end())
			{
				g_LogFS << "ERROR: USB AD channel parameter is wrong (" << g_USBIOParamAD << ")." << std::endl;
				return E_FAIL;
			}

			if((rangeval = getRangeValue(iter->c_str())) == BADRANGE)
			{
				g_LogFS << "ERROR: Bad range (" << iter->c_str() << ") for channel " << chan << "." << std::endl;
				return E_FAIL;
			}

			g_USBADChannelList[g_numUSBADChannels][0] = chan;
			g_USBADChannelList[g_numUSBADChannels][1] = rangeval;
			g_numUSBADChannels++;
			iter++;
		}

		if(g_numUSBADChannels>0)
		{
			g_LogFS << "USB AD: ";
			for(int i=0; i<g_numUSBADChannels; i++){
				g_LogFS << g_USBADChannelList[i][0] << " ";
			}
			g_LogFS << std::endl;

			//vaild channels?
			if(FAILED(checkAD())){
				return E_FAIL;
			}

			//allocate memory
			if(g_ADResolution>16){
				g_USBADBuffer32 = (DWORD*)malloc(MAXDATA*g_numUSBADChannels*sizeof(DWORD));
				if(g_USBADBuffer32==NULL || g_pCameraTextureBuffer==NULL || g_pCalResultTextureBuffer==NULL){
					g_LogFS << "ERROR: failed to allocate AD buffer." << std::endl;
					return E_FAIL;
				}
			}else{
				g_USBADBuffer16 = (WORD*)malloc(MAXDATA*g_numUSBADChannels*sizeof(WORD));
				if(g_USBADBuffer16==NULL){
					g_LogFS << "ERROR: failed to allocate AD buffer." << std::endl;
					return E_FAIL;
				}
			}
		}
	}

	// DI
	if(g_USBIOParamDI!="NONE" && g_USBIOParamDI!=""){
		if( (g_USBDIPort = getPortValue(g_USBIOParamDI.c_str()))==BADPORTNUM ){
			g_LogFS << "ERROR: unsupported port (" << g_USBIOParamDI << ")." << std::endl;
			return E_FAIL;
		}else{
			g_LogFS << "USB DI: " << g_USBIOParamDI << "." << std::endl;
		}

		//vaild port?
		if(FAILED(checkDI())){
			return E_FAIL;
		}

		//allocate memory
		g_USBDIBuffer = (WORD*)malloc(MAXDATA*sizeof(WORD));
		if(g_USBDIBuffer==NULL){
			g_LogFS << "ERROR: failed to allocate DI buffer." << std::endl;
			return E_FAIL;
		}
	}

	if(g_USBADBuffer32==NULL && g_USBADBuffer16==NULL && g_USBDIBuffer==NULL)
	{
		g_LogFS << "ERROR: USBIO_BOARD is specified, but neither USBIO_AD nor USBIO_DI is specified." << std::endl;
		return E_FAIL;
	}

	if(g_useUSBThread){
		if(FAILED(startUSBThread())){
			cleanupUSBIO();
			return E_FAIL;
		}
	}

	g_useUSBIO = true;
	return S_OK;
}


/*!
setUSBIOData: Read values from AD and DI ports and set them to memory buffer.

Read values from AD and DI ports and set them to memory buffer.
Ports and buffers must be initialized by initUSBIO().
dataCounter should be equal to global data counter (g_dataCounter).

@param[in] dataCounter
*/
void setUSBIOData(int dataCounter)
{
	int ULStat;
	int options=0;

	if(g_useUSBThread)
	{
		if(g_USBADBuffer32!=NULL)
		{
			for(int i=0; i<g_numUSBADChannels; i++){
				g_USBADBuffer32[dataCounter*g_numUSBADChannels+i] = g_latestADValue32[i];
			}
		}
		else if(g_USBADBuffer16!=NULL)
		{
			for(int i=0; i<g_numUSBADChannels; i++){
				g_USBADBuffer16[dataCounter*g_numUSBADChannels+i] = g_latestADValue16[i];
			}
		}
		if(g_USBDIBuffer!=NULL)
			g_USBDIBuffer[dataCounter] = g_latestDIValue;
	}
	else
	{
		if(g_USBADBuffer32!=NULL)
		{
			for(int i=0; i<g_numUSBADChannels; i++){
				ULStat = cbAIn32(g_BoardNum, g_USBADChannelList[i][0],
					g_USBADChannelList[i][1], &g_USBADBuffer32[dataCounter*g_numUSBADChannels+i], options);
			}
		}
		else if(g_USBADBuffer16!=NULL)
		{
			for(int i=0; i<g_numUSBADChannels; i++){
				ULStat = cbAIn(g_BoardNum, g_USBADChannelList[i][0],
					g_USBADChannelList[i][1], &g_USBADBuffer16[dataCounter*g_numUSBADChannels+i]);
			}
		}
		if(g_USBDIBuffer!=NULL)
			ULStat = cbDIn(g_BoardNum, g_USBDIPort, &g_USBDIBuffer[dataCounter]);
	}

}

/*!
getUSBIODataFormatString: Return data-format string.

This function sets data-format string to buff.
Data-format string is output to SimpleGazeTracker data file.
Size of buff must be given by buffsize.

@param[out] buff
@param[in] buffsize
*/
void getUSBIODataFormatString(char* buff, int buffsize)
{
	int len=0;
	for(int i=0; i<g_numUSBADChannels; i++){
		len += snprintf(buff+len, buffsize-len, "AD%d;", g_USBADChannelList[i][0]);
	}
	if(g_USBDIBuffer!=NULL)
		len += snprintf(buff+len, buffsize-len, "DI");

	//delete ';'
	if(len>0 && buff[len-1]==';')
		buff[len-1]='\0';
	
}

/*!
getUSBIODataFormatString: Return data-format string.

This function outputs data as a semicolon-separated string.
Size of buff must be given by buffsize.

@param[in] index
@param[out] buff
@param[in] buffsize
*/
void getUSBIODataString(int index, char* buff, int buffsize)
{
	int len=0;
	if(g_USBADBuffer32!=NULL)
		for(int chan=0; chan<g_numUSBADChannels; chan++)
		{
			len += snprintf(buff+len, buffsize-len,"%d;",g_USBADBuffer32[index*g_numUSBADChannels+chan]);
		}
	else if(g_USBADBuffer16!=NULL)
		for(int chan=0; chan<g_numUSBADChannels; chan++)
		{
			len += snprintf(buff+len, buffsize-len,"%d;",g_USBADBuffer16[index*g_numUSBADChannels+chan]);
		}
	if(g_USBDIBuffer!=NULL)
		len += snprintf(buff+len, buffsize-len, "%d",g_USBDIBuffer[index]);
				
	//delete ';'
	if(len>0 && buff[len-1]==';')
		buff[len-1]='\0';
}
