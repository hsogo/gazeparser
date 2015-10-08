/*!
@file usbioDAQFlex.cpp
@author Hiroyuki Sogo
@copyright GNU General Public License (GPL) version 3.

@brief Functions for USB-IO support.
*/

#include <string>
#include <fstream>
#include <iostream>
#include <sstream>
#include <list>
#include "GazeTrackerCommon.h"

#include <libusb.h>
#define MCC_VENDOR_ID 0x09db
#define MAX_MESSAGE_LENGTH 64
#define STRINGMESSAGE 0x80

#define MAX_USB_AD_CHANNELS 8

libusb_device_handle* g_pUSBDevHandle = NULL;

int g_BoardNum = NO_USBIO;

int g_USBDIPort;

int g_numUSBADChannels = 0;
int g_ADResolution = 0;
int g_USBADChannelList[MAX_USB_AD_CHANNELS];
std::string g_USBADRangeList[MAX_USB_AD_CHANNELS];
std::string g_USBADCommandList[MAX_USB_AD_CHANNELS];
std::string g_USBDICommand;

bool g_useUSBIO = false;
bool g_useUSBThread = false;
bool g_runUSBThread = false;

unsigned int g_latestADValue[MAX_USB_AD_CHANNELS];
unsigned short g_latestDIValue;

unsigned int* g_USBADBuffer;
unsigned short* g_USBDIBuffer;


SDL_Thread *g_pUSBThread;

//debug//
double g_debug_buffer[1000];
int g_debug_counter=0;
//debug//

void sendControlTransfer(std::string message)
{
	int numBytesTransferred;

	uint16_t length = message.length();
	const char* msgData = message.data();
	unsigned char data[MAX_MESSAGE_LENGTH];
	for (uint16_t i = 0; i < MAX_MESSAGE_LENGTH; i++) {
		data[i] = (i < length) ? msgData[i] : 0;
	}
	numBytesTransferred = libusb_control_transfer(g_pUSBDevHandle, LIBUSB_REQUEST_TYPE_VENDOR + LIBUSB_ENDPOINT_OUT,
				STRINGMESSAGE, 0, 0, data, MAX_MESSAGE_LENGTH, 1000);
}

std::string getControlTransfer()
{
	int messageLength;
	unsigned char message[64];
	std::string strmessage;

	messageLength = libusb_control_transfer(g_pUSBDevHandle,  LIBUSB_REQUEST_TYPE_VENDOR + LIBUSB_ENDPOINT_IN,
				STRINGMESSAGE, 0, 0, message, 64, 1000);
	strmessage = (char*)message;
	return strmessage;
}

std::string sendMessage(std::string message)
{
	sendControlTransfer(message);
	return getControlTransfer();
}

int initDAQFlex(int idProduct)
{
	int i;
	bool found = false;
	ssize_t sizeOfList;
	
	libusb_device ** list;
	libusb_device_descriptor desc;
	libusb_device* device;

	
	//Initialize USB libraries
	if(libusb_init(NULL) != 0)
		return E_FAIL;

	//Get the list of USB devices connected to the PC
	sizeOfList = libusb_get_device_list(NULL, &list);

	//Traverse the list of USB devices to find the requested device
	for(i=0; (i<sizeOfList) && (!found); i++)
	{
		device = list[i];
		libusb_get_device_descriptor(device, &desc);
		if(desc.idVendor == MCC_VENDOR_ID && desc.idProduct == idProduct)
		{
			found = true;

			//Open the device
			if(!libusb_open(device, &g_pUSBDevHandle))
			{
				//Claim interface with the device
				if(!libusb_claim_interface(g_pUSBDevHandle,0))
				{
					//Get input and output endpoints
					//getEndpoints();
					found = true;
				}
			}
		}
	}

	if(!found)
		return E_FAIL;
	
	return S_OK;
}

int pollUSBIOThread(void *unused)
{
	std::string resstr;
	size_t pos;
	char* p;

	while(g_runUSBThread)
	{
		if(g_USBADBuffer!=NULL)
		{
			for(int i=0; i<g_numUSBADChannels; i++){
				resstr = sendMessage(g_USBADCommandList[i]);
				pos = resstr.find("=");
				if(pos!= std::string::npos){
					resstr.erase(0,pos+1);
					g_latestADValue[i] = strtol(resstr.c_str(),&p,10);
				}
			}
		}
		if(g_USBDIBuffer!=NULL){
			resstr = sendMessage(g_USBDICommand);
			pos = resstr.find("=");
			if(pos!= std::string::npos){
				resstr.erase(0,pos+1);
				g_latestDIValue = strtol(resstr.c_str(),&p,10);
			}
		}

	}
	
	return 0;
}

/*!
getProductIDValue: Get product ID from string.

Following products are supported.

-USB_2001_TC (0x00F9)
-USB_7202 (0x00F2)
-USB_7204 (0x00F0)
-USB_1208 (0x00E8)

@param[in] prodstr
@return int
*/
int getProductIDValue(const char* prodstr)
{
	if(strcmp(prodstr,"USB_2001_TC")==0)
		return 0x00F9;
	else if(strcmp(prodstr,"USB_7202")==0)
		return 0x00F2;
	else if(strcmp(prodstr,"USB_7204")==0)
		return 0x00F0;
	else if(strcmp(prodstr,"USB_1208")==0)
		return 0x00E8;

	return E_FAIL;
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
	std::stringstream ss;
	std::string cmdstr;
	std::string validresstr;
	std::string resstr;
	size_t pos;

	for(int i=0; i<g_numUSBADChannels; i++)
	{
		ss << "AI{" << g_USBADChannelList[i] << "}:RANGE=" << g_USBADRangeList[i];
		cmdstr = ss.str();
		ss.str("");
		ss << "AI{" << g_USBADChannelList[i] << "}:RANGE";
		validresstr = ss.str();
		ss.str("");
		resstr = sendMessage(cmdstr);
		if(resstr != validresstr){
			snprintf(g_errorMessage, sizeof(g_errorMessage), "Unsupported range (%s) for channel %d.\nCheck %s in %s.", g_USBADRangeList[i].c_str(), g_USBADChannelList[i], g_ConfigFileName.c_str(), g_ParamPath.c_str());
			g_LogFS << "Could not set AD Range " << g_USBADChannelList[i] << " (" << g_USBADRangeList[i] << ")." << std::endl;
			return E_FAIL;
		}

		ss << "?AI{" << g_USBADChannelList[i] << "}:VALUE" ;
		cmdstr = ss.str();
		ss.str("");
		resstr = sendMessage(cmdstr);
		pos = resstr.find("=");
		if(pos == std::string::npos){
			snprintf(g_errorMessage, sizeof(g_errorMessage), "Failed to read AD channel %d (USBIO_AD=%s).\nCheck %s in %s.", g_USBADChannelList[i], g_USBIOParamAD.c_str(), g_ConfigFileName.c_str(), g_ParamPath.c_str());
			g_LogFS << "Could not read AD channel " << g_USBADChannelList[i] << "." << std::endl;
			return E_FAIL;
		}
		
		g_USBADCommandList[i] = cmdstr;
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
	std::stringstream ss;
	std::string cmdstr;
	std::string validresstr;
	std::string resstr;
	size_t pos;
	
	ss << "DIO{" << g_USBDIPort << "}:DIR=IN";
	cmdstr = ss.str();
	ss.str("");
	ss << "DIO{" << g_USBDIPort << "}:DIR";
	validresstr = ss.str();
	ss.str("");
	resstr = sendMessage(cmdstr);
	
	if(resstr != validresstr){
		snprintf(g_errorMessage, sizeof(g_errorMessage), "Failed to configure port (%s) as Digital input.\nCheck %s in %s.", g_USBIOParamDI.c_str(), g_ConfigFileName.c_str(), g_ParamPath.c_str());
		g_LogFS << "Could not configure port (" << g_USBIOParamDI << ") as Digital input." << std::endl;
		return E_FAIL;
	}
	
	ss << "?DIO{" << g_USBDIPort << "}:VALUE" ;
	cmdstr = ss.str();
	resstr = sendMessage(cmdstr);
	pos = resstr.find("=");
	if(pos == std::string::npos){
		snprintf(g_errorMessage, sizeof(g_errorMessage), "Failed to read port (%s) as Digital input.\nCheck %s in %s.", g_USBIOParamDI.c_str(), g_ConfigFileName.c_str(), g_ParamPath.c_str());
		g_LogFS << "Could not read Digital input port (" << g_USBIOParamDI << ")." << std::endl;
		return E_FAIL;
	}
	g_USBDICommand = cmdstr;
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
	g_pUSBThread = SDL_CreateThread(pollUSBIOThread, "USBIOThread", NULL);
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

		//debug//
		for(int i=0; i<1000; i++){
			g_LogFS << g_debug_buffer[i] << std::endl;
		}
		//debug//
	}
}

void cleanupUSBIO(void)
{
	if(g_useUSBThread){
		stopUSBThread();
	}

	if( g_USBADBuffer != NULL )
	{
		free(g_USBADBuffer);
		g_USBADBuffer = NULL;
	}

	if( g_USBDIBuffer != NULL )
	{
		free(g_USBDIBuffer);
		g_USBDIBuffer = NULL;
	}

	if(g_pUSBDevHandle!=NULL){
		libusb_close(g_pUSBDevHandle);
		g_pUSBDevHandle = NULL;
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

	if(g_pUSBDevHandle != NULL){
		g_LogFS << "ERROR: USB Device Handle is not null." << std::endl;
		return E_FAIL;
	}

	// Board number
	if(g_USBIOBoard.compare(0,2,"0x")==0){
		g_BoardNum = strtol(g_USBIOBoard.c_str(),&p,16);
	}else{
		g_BoardNum = strtol(g_USBIOBoard.c_str(),&p,10);
	}
	if(g_USBIOBoard.c_str()==p) // strtol was failed.
	{	//Guess Product ID
		printf("hoge %s\n",g_USBIOBoard.c_str());
		if(FAILED(g_BoardNum = getProductIDValue(g_USBIOBoard.c_str()))){
			snprintf(g_errorMessage, sizeof(g_errorMessage), "Failed to open USB I/O board (%s).\nCheck %s in %s.", g_USBIOBoard.c_str(), g_ConfigFileName.c_str(), g_ParamPath.c_str());
			g_LogFS << "ERROR: Could not open USB I/O board. Board number (=" << g_USBIOBoard << ") seems invalid." << std::endl;
			return E_FAIL;
		}
	}
	
	if(FAILED(initDAQFlex(g_BoardNum))){
		snprintf(g_errorMessage, sizeof(g_errorMessage), "Failed to find USB I/O board (%s).\nCheck %s in %s.", g_USBIOBoard.c_str(), g_ConfigFileName.c_str(), g_ParamPath.c_str());
		g_LogFS << "ERROR: Could not find USB IO board. Is board number (=" << g_USBIOBoard << ") bad?" << std::endl;
		return E_FAIL;
	}
	g_LogFS << "USB IO board " << g_USBIOBoard << " is opened." << std::endl;

	// AD
	if(g_USBIOParamAD!="NONE" && g_USBIOParamAD!=""){
		params = splitString(g_USBIOParamAD, ";");
		g_numUSBADChannels = 0;
		iter = params.begin();
		while( iter != params.end())
		{
			if(g_numUSBADChannels>=MAX_USB_AD_CHANNELS){
				snprintf(g_errorMessage, sizeof(g_errorMessage), "Too many AD channels are listed.\nCheck %s in %s.", g_ConfigFileName.c_str(), g_ParamPath.c_str());
				g_LogFS << "ERROR: Too many AD channels." << std::endl;
				return E_FAIL;
			}
			chan = strtol(iter->c_str(),&p,10);
			for(int i=0; i<g_numUSBADChannels; i++){
				if(g_USBADChannelList[i]==chan){
					snprintf(g_errorMessage, sizeof(g_errorMessage), "AD channel %d is duplicated.\nCheck %s in %s.", chan, g_ConfigFileName.c_str(), g_ParamPath.c_str());
					g_LogFS << "ERROR: USB AD channel " << chan << " is duplicated." << std::endl;
					return E_FAIL;
				}
			}

			iter++;
			if(iter==params.end())
			{
				snprintf(g_errorMessage, sizeof(g_errorMessage), "AD channel parameter (%s) is wrong.\nCheck %s in %s.", g_USBIOParamAD.c_str(), g_ConfigFileName.c_str(), g_ParamPath.c_str());
				g_LogFS << "ERROR: USB AD channel parameter is wrong (" << g_USBIOParamAD << ")." << std::endl;
				return E_FAIL;
			}

			g_USBADChannelList[g_numUSBADChannels] = chan;
			g_USBADRangeList[g_numUSBADChannels] = iter->c_str();
			g_numUSBADChannels++;
			iter++;
		}

		if(g_numUSBADChannels>0)
		{
			g_LogFS << "USB AD: ";
			for(int i=0; i<g_numUSBADChannels; i++){
				g_LogFS << g_USBADChannelList[i] << " ";
			}
			g_LogFS << std::endl;

			//vaild channels?
			if(FAILED(checkAD())){
				// g_errorMessage is set in checkAD().
				return E_FAIL;
			}

			//allocate memory
			g_USBADBuffer = (unsigned int*)malloc(MAXDATA*g_numUSBADChannels*sizeof(unsigned int));
			if(g_USBADBuffer==NULL){
				snprintf(g_errorMessage, sizeof(g_errorMessage), "Failed to allocate AD buffer.");
				g_LogFS << "ERROR: failed to allocate AD buffer." << std::endl;
				return E_FAIL;
			}
		}
	}

	// DI
	if(g_USBIOParamDI!="NONE" && g_USBIOParamDI!=""){
		g_USBDIPort = strtol(g_USBIOParamDI.c_str(),&p,10);
		if( g_USBDIPort==0 && g_USBIOParamDI!="0" ){
			snprintf(g_errorMessage, sizeof(g_errorMessage), "Unsupported USB DI port (%s).\nCheck %s in %s.", g_USBIOParamDI.c_str(), g_ConfigFileName.c_str(), g_ParamPath.c_str());
			g_LogFS << "ERROR: unsupported port (" << g_USBIOParamDI << ")." << std::endl;
			return E_FAIL;
		}else{
			g_LogFS << "USB DI: " << g_USBIOParamDI << "." << std::endl;
		}

		//vaild port?
		if(FAILED(checkDI())){
			// g_errorMessage is set in checkDI().
			return E_FAIL;
		}

		//allocate memory
		g_USBDIBuffer = (unsigned short*)malloc(MAXDATA*sizeof(unsigned short));
		if(g_USBDIBuffer==NULL){
			snprintf(g_errorMessage, sizeof(g_errorMessage), "Failed to allocate DI buffer.");
			g_LogFS << "ERROR: failed to allocate DI buffer." << std::endl;
			return E_FAIL;
		}
	}

	if(g_USBADBuffer==NULL && g_USBDIBuffer==NULL)
	{
		snprintf(g_errorMessage, sizeof(g_errorMessage), "USBIO_BOARD is specified, but neither USBIO_AD nor USBIO_DI is specified.\nCheck %s in %s.", g_ConfigFileName.c_str(), g_ParamPath.c_str());
		g_LogFS << "ERROR: USBIO_BOARD is specified, but neither USBIO_AD nor USBIO_DI is specified." << std::endl;
		return E_FAIL;
	}

	if(g_useUSBThread){
		if(FAILED(startUSBThread())){
			snprintf(g_errorMessage, sizeof(g_errorMessage), "Failed to start a new thread for asynchronous USB I/O.");
			g_LogFS << "ERROR: failed to start thread" << std::endl;
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
	std::string resstr;
	size_t pos;
	char* p;

	if(g_useUSBThread)
	{
		if(g_USBADBuffer!=NULL)
		{
			for(int i=0; i<g_numUSBADChannels; i++){
				g_USBADBuffer[dataCounter*g_numUSBADChannels+i] = g_latestADValue[i];
			}
		}
		if(g_USBDIBuffer!=NULL)
			g_USBDIBuffer[dataCounter] = g_latestDIValue;
	}
	else
	{
		if(g_USBADBuffer!=NULL)
		{
			for(int i=0; i<g_numUSBADChannels; i++){
				resstr = sendMessage(g_USBADCommandList[i]);
				pos = resstr.find("=");
				if(pos!= std::string::npos){
					resstr.erase(0,pos+1);
					g_USBADBuffer[dataCounter*g_numUSBADChannels+i] = strtol(resstr.c_str(),&p,10);
				}				
			}
		}
		if(g_USBDIBuffer!=NULL){
			resstr = sendMessage(g_USBDICommand);
			pos = resstr.find("=");
			if(pos!= std::string::npos){
				resstr.erase(0,pos+1);
				g_USBDIBuffer[dataCounter] = strtol(resstr.c_str(),&p,10);
			}				
		}
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
		len += snprintf(buff+len, buffsize-len, "AD%d;", g_USBADChannelList[i]);
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
	if(g_USBADBuffer!=NULL)
		for(int chan=0; chan<g_numUSBADChannels; chan++)
		{
			len += snprintf(buff+len, buffsize-len,"%d;",g_USBADBuffer[index*g_numUSBADChannels+chan]);
		}
	if(g_USBDIBuffer!=NULL)
		len += snprintf(buff+len, buffsize-len, "%d",g_USBDIBuffer[index]);
	
	//delete ';'
	if(len>0 && buff[len-1]==';')
		buff[len-1]='\0';
		
}

