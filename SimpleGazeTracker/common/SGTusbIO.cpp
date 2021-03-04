#include "SGTCommon.h"

#include <string>
#include <fstream>
#include <iostream>
#include <list>

#include "SGTusbIO.h"

#ifdef  _WIN32
#include <cbw.h>
#else
#include "uldaq.h"
#endif

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
	size_t idx;

	while ((idx = targetstr.find_first_of(delim)) != std::string::npos)
	{
		if (idx > 0)
		{
			res.push_back(targetstr.substr(0, idx));
		}
		targetstr = targetstr.substr(idx + 1);
	}
	if (targetstr.length() > 0)
	{
		res.push_back(targetstr);
	}
	return res;
}

#ifdef  _WIN32
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
	if (strcmp(rangestr, "BIP15VOLTS") == 0)
		return BIP15VOLTS;
	else if (strcmp(rangestr, "BIP10VOLTS") == 0)
		return BIP10VOLTS;
	else if (strcmp(rangestr, "BIP5VOLTS") == 0)
		return BIP5VOLTS;
	else if (strcmp(rangestr, "BIP2PT5VOLTS") == 0)
		return BIP2PT5VOLTS;
	else if (strcmp(rangestr, "BIP1VOLTS") == 0)
		return BIP1VOLTS;
	else if (strcmp(rangestr, "UNI10VOLTS") == 0)
		return UNI10VOLTS;
	else if (strcmp(rangestr, "UNI5VOLTS") == 0)
		return UNI5VOLTS;
	else if (strcmp(rangestr, "UNI2PT5VOLTS") == 0)
		return UNI2PT5VOLTS;
	else if (strcmp(rangestr, "UNI1VOLTS") == 0)
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
	if (strcmp(portstr, "FIRSTPORTA") == 0)
		return FIRSTPORTA;
	else if (strcmp(portstr, "FIRSTPORTB") == 0)
		return FIRSTPORTB;
	else if (strcmp(portstr, "FIRSTPORTCL") == 0)
		return FIRSTPORTCL;
	else if (strcmp(portstr, "FIRSTPORTC") == 0)
		return FIRSTPORTC;
	else if (strcmp(portstr, "FIRSTPORTCH") == 0)
		return FIRSTPORTCH;

	return BADPORTNUM;
}

int SGTusbIO::checkAD(void)
{
	int ULStat = 0;
	WORD DataValue = 0;
	DWORD DataValue32 = 0;
	int options = 0;

	char error_message[1024];

	cbGetConfig(BOARDINFO, m_boardNum, 0, BIADRES, &m_ADResolution);
	if (ULStat != NOERRORS) {
		snprintf(error_message, sizeof(error_message), "Failed to get configuration for board %s.", m_board.c_str());
		outputLog(error_message);
		return E_FAIL;
	}

	for (int i = 0; i < m_numADChannels; i++)
	{

		if (m_ADResolution > 16) { //HighRes
			ULStat = cbAIn32(m_boardNum, m_ADChannelList[i][0], m_ADChannelList[i][1], &DataValue32, options);
		}
		else {
			ULStat = cbAIn(m_boardNum, m_ADChannelList[i][0], m_ADChannelList[i][1], &DataValue);
		}
		if (ULStat != NOERRORS) {
			snprintf(error_message, sizeof(error_message), "Failed to read AD channel %d (USBIO_AD=%s).",
				m_ADChannelList[i][0], m_paramAD.c_str());
			outputLog(error_message);
			return E_FAIL;
		}
	}
	return S_OK;
}


int SGTusbIO::checkDI(void)
{
	int ULStat = 0;
	WORD DataValue = 0;
	char error_message[1024];

	std::fill_n(&m_ADChannelList[0][0], MAX_USB_AD_CHANNELS*2, 0);
	std::fill_n(m_latestADValue32, MAX_USB_AD_CHANNELS, 0);
	std::fill_n(m_latestADValue16, MAX_USB_AD_CHANNELS, 0);

	ULStat = cbDConfigPort(m_boardNum, m_DIport, DIGITALIN);
	if (ULStat != NOERRORS) {
		snprintf(error_message, sizeof(error_message), "Failed to configure port (%s) as Digital input.", m_paramDI.c_str());
		outputLog(error_message);
		return E_FAIL;
	}

	ULStat = cbDIn(m_boardNum, m_DIport, &DataValue);
	if (ULStat != NOERRORS) {
		snprintf(error_message, sizeof(error_message), "Failed to read port (%s) as Digital input.", m_paramDI.c_str());
		outputLog(error_message);
		return E_FAIL;
	}

	return S_OK;
}


SGTusbIO::~SGTusbIO()
{
	if (m_ADBuffer32 != NULL)
	{
		free(m_ADBuffer32);
		m_ADBuffer32 = NULL;
	}

	if (m_ADBuffer16 != NULL)
	{
		free(m_ADBuffer16);
		m_ADBuffer16 = NULL;
	}

	if (m_DIBuffer != NULL)
	{
		free(m_DIBuffer);
		m_DIBuffer = NULL;
	}
}

int SGTusbIO::init(std::string board, std::string paramAD, std::string paramDI, int maxdata)
{
	m_numADChannels = 0;
	m_ADResolution = 0;
	m_boardNum = NO_USBIO;
	m_board = board;
	m_paramAD = paramAD;
	m_paramDI = paramDI;
	char error_message[1024];

	char *p;
	std::list<std::string> params;
	std::list<std::string>::iterator iter;
	int chan, rangeval;

	// Board number
	m_boardNum = strtol(m_board.c_str(), &p, 10);
	if (p == m_board.c_str()) {
		snprintf(error_message, sizeof(error_message), "USBIO_BOARD (%s) must be decimal number of board ID.", m_board.c_str());
		outputLog(error_message);
		return E_FAIL;
	}
	if (cbFlashLED(m_boardNum) != NOERRORS) {
		snprintf(error_message, sizeof(error_message), "Failed to open USB I/O unit. USBIO_BOARD (%s) may be wrong.", m_board.c_str());
		outputLog(error_message);
		return E_FAIL;
	}
	else {
		snprintf(error_message, sizeof(error_message), "USB IO board %s is opened.", m_board.c_str());
		outputLog(error_message);
	}

	// AD
	if (paramAD != "NONE" && paramAD != "") {
		params = splitString(paramAD, ";");
		m_numADChannels = 0;
		iter = params.begin();
		while (iter != params.end())
		{
			if (m_numADChannels >= MAX_USB_AD_CHANNELS) {
				outputLog("ERROR: Too many AD channels.");
				return E_FAIL;
			}
			chan = strtol(iter->c_str(), &p, 10);
			for (int i = 0; i < m_numADChannels; i++) {
				if (m_ADChannelList[i][0] == chan) {
					snprintf(error_message, sizeof(error_message), "AD channel %d is duplicated.", chan);
					outputLog(error_message);
					return E_FAIL;
				}
			}

			iter++;
			if (iter == params.end())
			{
				snprintf(error_message, sizeof(error_message), "AD channel parameter (%s) is wrong.", paramAD.c_str());
				outputLog(error_message);
				return E_FAIL;
			}

			if ((rangeval = getRangeValue(iter->c_str())) == BADRANGE)
			{
				snprintf(error_message, sizeof(error_message), "Unsupported range (%s) for channel %d.", iter->c_str(), chan);
				outputLog(error_message);
				return E_FAIL;
			}

			m_ADChannelList[m_numADChannels][0] = chan;
			m_ADChannelList[m_numADChannels][1] = rangeval;
			m_numADChannels++;
			iter++;
		}

		if (m_numADChannels > 0)
		{
			int idx;
			idx = snprintf(error_message, sizeof(error_message), "USB AD: ");
			for (int i = 0; i < m_numADChannels; i++) {
				idx = snprintf(&error_message[idx], sizeof(error_message)-idx, "%d,", m_ADChannelList[i][0]);
			}
			outputLog(error_message);

			//vaild channels?
			if (FAILED(checkAD())) {
				// error_message is set in checkAD().
				return E_FAIL;
			}

			//allocate memory
			if (m_ADResolution > 16) {
				m_ADBuffer32 = (DWORD*)malloc(maxdata*m_numADChannels * sizeof(DWORD));
				if (m_ADBuffer32 == NULL) {
					outputLog("ERROR: failed to allocate AD buffer.");
					return E_FAIL;
				}
			}
			else {
				m_ADBuffer16 = (WORD*)malloc(maxdata*m_numADChannels * sizeof(WORD));
				if (m_ADBuffer16 == NULL) {
					outputLog("ERROR: failed to allocate AD buffer.");
					return E_FAIL;
				}
			}
		}
	}

	// DI
	if (paramDI != "NONE" && paramDI != "") {
		if ((m_DIport = getPortValue(paramDI.c_str())) == BADPORTNUM) {
			snprintf(error_message, sizeof(error_message), "Unsupported USB DI port (%s).", paramDI.c_str());
			outputLog(error_message);
			return E_FAIL;
		}
		else {
			snprintf(error_message, sizeof(error_message), "USB DI: %s.", paramDI.c_str());
			outputLog(error_message);
		}

		//vaild port?
		if (FAILED(checkDI())) {
			// error_message is set in checkDI().
			return E_FAIL;
		}

		//allocate memory
		m_DIBuffer = (WORD*)malloc(maxdata * sizeof(WORD));
		if (m_DIBuffer == NULL) {
			outputLog("ERROR: failed to allocate DI buffer.");
			return E_FAIL;
		}
	}

	if (m_ADBuffer32 == NULL && m_ADBuffer16 == NULL && m_DIBuffer == NULL)
	{
		outputLog("ERROR: USBIO_BOARD is specified, but neither USBIO_AD nor USBIO_DI is specified.");
		return E_FAIL;
	}

	// set flag
	g_useUSBIO = true;

	return S_OK;
}

void SGTusbIO::recordData(int dataCounter)
{
	int ULStat;
	int options = 0;

	if (m_ADBuffer32 != NULL)
	{
		for (int i = 0; i < m_numADChannels; i++) {
			ULStat = cbAIn32(m_boardNum, m_ADChannelList[i][0],
				m_ADChannelList[i][1], &m_ADBuffer32[dataCounter*m_numADChannels + i], options);
		}
	}
	else if (m_ADBuffer16 != NULL)
	{
		for (int i = 0; i < m_numADChannels; i++) {
			ULStat = cbAIn(m_boardNum, m_ADChannelList[i][0],
				m_ADChannelList[i][1], &m_ADBuffer16[dataCounter*m_numADChannels + i]);
		}
	}
	if (m_DIBuffer != NULL)
		ULStat = cbDIn(m_boardNum, m_DIport, &m_DIBuffer[dataCounter]);

}

int SGTusbIO::getCurrentAIData(int* nChan, int* chanList, int* valueList)
{
	int ULStat;
	int options = 0;

	if(m_ADBuffer32 != NULL)
	{
		*nChan = m_numADChannels;
		DWORD val;
		for (int i = 0; i < m_numADChannels; i++) {
			ULStat = cbAIn32(m_boardNum, m_ADChannelList[i][0],
				m_ADChannelList[i][1], &val, options);
			chanList[i] = m_ADChannelList[i][0];
			valueList[i] = (int)val;
		}
		return S_OK;
	}
	else if (m_ADBuffer16 != NULL)
	{
		*nChan = m_numADChannels;
		WORD val;
			for (int i = 0; i < m_numADChannels; i++) {
			ULStat = cbAIn(m_boardNum, m_ADChannelList[i][0],
				m_ADChannelList[i][1], &val);
			chanList[i] = m_ADChannelList[i][0];
			valueList[i] = (int)val;
		}
		return S_OK;
	}

	return E_FAIL;
}

int SGTusbIO::getCurrentDIData(unsigned short* value)
{
	int ULStat;

	if (m_DIBuffer != NULL)
	{
		ULStat = cbDIn(m_boardNum, m_DIport, value);
		return S_OK;
	}
	
	return E_FAIL;
}



void SGTusbIO::getDataFormatString(char* buff, int buffsize)
{
	int len = 0;
	for (int i = 0; i < m_numADChannels; i++) {
		len += snprintf(buff + len, buffsize - len, "AD%d;", m_ADChannelList[i][0]);
	}
	if (m_DIBuffer != NULL)
		len += snprintf(buff + len, buffsize - len, "DI");

	//delete ';'
	if (len > 0 && buff[len - 1] == ';')
		buff[len - 1] = '\0';

}


void SGTusbIO::getDataString(int index, char* buff, int buffsize)
{
	int len = 0;
	if (m_ADBuffer32 != NULL)
		for (int chan = 0; chan < m_numADChannels; chan++)
		{
			len += snprintf(buff + len, buffsize - len, "%d;", m_ADBuffer32[index*m_numADChannels + chan]);
		}
	else if (m_ADBuffer16 != NULL)
		for (int chan = 0; chan < m_numADChannels; chan++)
		{
			len += snprintf(buff + len, buffsize - len, "%d;", m_ADBuffer16[index*m_numADChannels + chan]);
		}
	if (m_DIBuffer != NULL)
		len += snprintf(buff + len, buffsize - len, "%d", m_DIBuffer[index]);

	//delete ';'
	if (len > 0 && buff[len - 1] == ';')
		buff[len - 1] = '\0';
}


#else

#define MAX_DEV_COUNT 100
#define BADRANGE (Range)-1
#define BADPORTNUM (DigitalPortType)-1

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
Range getRangeValue(const char* rangestr)
{
	if (strcmp(rangestr, "BIP15VOLTS") == 0)
		return BIP15VOLTS;
	else if (strcmp(rangestr, "BIP10VOLTS") == 0)
		return BIP10VOLTS;
	else if (strcmp(rangestr, "BIP5VOLTS") == 0)
		return BIP5VOLTS;
	else if (strcmp(rangestr, "BIP2PT5VOLTS") == 0)
		return BIP2PT5VOLTS;
	else if (strcmp(rangestr, "BIP1VOLTS") == 0)
		return BIP1VOLTS;
	else if (strcmp(rangestr, "UNI10VOLTS") == 0)
		return UNI10VOLTS;
	else if (strcmp(rangestr, "UNI5VOLTS") == 0)
		return UNI5VOLTS;
	else if (strcmp(rangestr, "UNI2PT5VOLTS") == 0)
		return UNI2PT5VOLTS;
	else if (strcmp(rangestr, "UNI1VOLTS") == 0)
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
DigitalPortType getPortValue(const char*portstr)
{
	if (strcmp(portstr, "FIRSTPORTA") == 0)
		return FIRSTPORTA;
	else if (strcmp(portstr, "FIRSTPORTB") == 0)
		return FIRSTPORTB;
	else if (strcmp(portstr, "FIRSTPORTCL") == 0)
		return FIRSTPORTCL;
	else if (strcmp(portstr, "FIRSTPORTC") == 0)
		return FIRSTPORTC;
	else if (strcmp(portstr, "FIRSTPORTCH") == 0)
		return FIRSTPORTCH;

	return BADPORTNUM;
}

int SGTusbIO::checkAD(void)
{
    long long infoValue;
	double dataValue = 0;

	char error_message[1024];

	if (ulDevGetInfo(m_handle, DEV_INFO_HAS_AI_DEV , 0, &infoValue) != ERR_NO_ERROR) {
		snprintf(error_message, sizeof(error_message), "Failed to get resolution of board %s.", m_board.c_str());
		outputLog(error_message);
		return E_FAIL;
	}

    if(infoValue==0){
		snprintf(error_message, sizeof(error_message), "Board %s doesn't have analog input.", m_board.c_str());
		outputLog(error_message);
		return E_FAIL;
    }

	for (int i = 0; i < m_numADChannels; i++)
	{
		if (ulAIn(m_handle, m_ADChannelList[i], AI_SINGLE_ENDED, m_ADRangeList[i], AIN_FF_NOSCALEDATA, &dataValue) != ERR_NO_ERROR) {
			snprintf(error_message, sizeof(error_message), "Failed to read AD channel %d (USBIO_AD=%s).",
				m_ADChannelList[i], m_paramAD.c_str());
			outputLog(error_message);
			return E_FAIL;
		}
	}
	return S_OK;
}


int SGTusbIO::checkDI(void)
{
	char error_message[1024];
    long long infoValue;
	unsigned long long data;

	if (ulDIOGetInfo(m_handle, DIO_INFO_NUM_PORTS, 0, &infoValue) != ERR_NO_ERROR) {
		snprintf(error_message, sizeof(error_message), "Failed to get num of Digital input ports.");
		outputLog(error_message);
		return E_FAIL;
	}

    if(infoValue==0){
		snprintf(error_message, sizeof(error_message), "Board %s doesn't have digital input.", m_board.c_str());
		outputLog(error_message);
		return E_FAIL;
    }

	if (ulDIn(m_handle, m_DIport, &data) != ERR_NO_ERROR) {
		snprintf(error_message, sizeof(error_message), "Failed to read port (%s) as Digital input.", m_paramDI.c_str());
		outputLog(error_message);
		return E_FAIL;
	}

	return S_OK;
}


SGTusbIO::~SGTusbIO()
{
	if (m_ADBuffer != NULL)
	{
		free(m_ADBuffer);
		m_ADBuffer = NULL;
	}

	if (m_DIBuffer != NULL)
	{
		free(m_DIBuffer);
		m_DIBuffer = NULL;
	}
}

int SGTusbIO::init(std::string board, std::string paramAD, std::string paramDI, int maxdata)
{
	m_numADChannels = 0;
	m_boardNum = NO_USBIO;
	m_board = board;
	m_paramAD = paramAD;
	m_paramDI = paramDI;
	char error_message[1024];

	char *p;
	std::list<std::string> params;
	std::list<std::string>::iterator iter;
	int chan;
	Range rangeval;

	unsigned int numDevs = MAX_DEV_COUNT;
	DaqDeviceDescriptor devDescriptors[MAX_DEV_COUNT];
	UlError err = ERR_NO_ERROR;

	std::fill_n(&m_ADChannelList[0], MAX_USB_AD_CHANNELS, 0);
	for(int i=0; i<MAX_USB_AD_CHANNELS; i++) m_ADRangeList[i] = (Range)0;
	std::fill_n(m_latestADValue, MAX_USB_AD_CHANNELS, 0);

	// Board number
	m_boardNum = strtol(m_board.c_str(), &p, 10);
	if (p == m_board.c_str()) {
		snprintf(error_message, sizeof(error_message), "USBIO_BOARD (%s) must be decimal number.", m_board.c_str());
		outputLog(error_message);
		return E_FAIL;
	}

    // Get descriptors for all of the available DAQ devices
    ulGetDaqDeviceInventory(USB_IFC, devDescriptors, &numDevs);
    if (numDevs==0) {
		snprintf(error_message, sizeof(error_message), "Supported I/O unit was not found.");
		outputLog(error_message);
		return E_FAIL;
    }

    if(m_boardNum >= numDevs ){
		snprintf(error_message, sizeof(error_message), "USBIO_BOARD must be smaller than number of devices (%d).", numDevs);
		outputLog(error_message);
		return E_FAIL;
    }

    // get a handle to the DAQ device associated with the first descriptor
	m_handle = ulCreateDaqDevice(devDescriptors[m_boardNum]);

	if (!m_handle) {
		snprintf(error_message, sizeof(error_message), "Failed to open USB I/O unit. USBIO_BOARD (%s) may be wrong.", m_board.c_str());
		outputLog(error_message);
		return E_FAIL;
	}
	else {
		snprintf(error_message, sizeof(error_message), "USB IO board %s is opened.", m_board.c_str());
		outputLog(error_message);
	}

	// AD
	if (paramAD != "NONE" && paramAD != "") {
		params = splitString(paramAD, ";");
		m_numADChannels = 0;
		iter = params.begin();
		while (iter != params.end())
		{
			if (m_numADChannels >= MAX_USB_AD_CHANNELS) {
				outputLog("ERROR: Too many AD channels.");
				return E_FAIL;
			}
			chan = strtol(iter->c_str(), &p, 10);
			for (int i = 0; i < m_numADChannels; i++) {
				if (m_ADChannelList[i] == chan) {
					snprintf(error_message, sizeof(error_message), "AD channel %d is duplicated.", chan);
					outputLog(error_message);
					return E_FAIL;
				}
			}

			iter++;
			if (iter == params.end())
			{
				snprintf(error_message, sizeof(error_message), "AD channel parameter (%s) is wrong.", paramAD.c_str());
				outputLog(error_message);
				return E_FAIL;
			}

			if ((rangeval = getRangeValue(iter->c_str())) == BADRANGE)
			{
				snprintf(error_message, sizeof(error_message), "Unsupported range (%s) for channel %d.", iter->c_str(), chan);
				outputLog(error_message);
				return E_FAIL;
			}

			m_ADChannelList[m_numADChannels] = chan;
			m_ADRangeList[m_numADChannels] = rangeval;
			m_numADChannels++;
			iter++;
		}

		if (m_numADChannels > 0)
		{
			int idx;
			idx = snprintf(error_message, sizeof(error_message), "USB AD: ");
			for (int i = 0; i < m_numADChannels; i++) {
				idx = snprintf(&error_message[idx], sizeof(error_message)-idx, "%d,", m_ADChannelList[i]);
			}
			outputLog(error_message);

			//vaild channels?
			if (FAILED(checkAD())) {
				// error_message is set in checkAD().
				return E_FAIL;
			}

			//allocate memory
			m_ADBuffer = (double*)malloc(maxdata*m_numADChannels * sizeof(double));
			if (m_ADBuffer == NULL) {
				outputLog("ERROR: failed to allocate AD buffer.");
				return E_FAIL;
			}
		}
	}

	// DI
	if (paramDI != "NONE" && paramDI != "") {
		if ((m_DIport = getPortValue(paramDI.c_str())) == BADPORTNUM) {
			snprintf(error_message, sizeof(error_message), "Unsupported USB DI port (%s).", paramDI.c_str());
			outputLog(error_message);
			return E_FAIL;
		}
		else {
			snprintf(error_message, sizeof(error_message), "USB DI: %s.", paramDI.c_str());
			outputLog(error_message);
		}

		//vaild port?
		if (FAILED(checkDI())) {
			// error_message is set in checkDI().
			return E_FAIL;
		}

		//allocate memory
		m_DIBuffer = (unsigned long long *)malloc(maxdata * sizeof(unsigned long long));
		if (m_DIBuffer == NULL) {
			outputLog("ERROR: failed to allocate DI buffer.");
			return E_FAIL;
		}
	}

	if (m_ADBuffer == NULL && m_DIBuffer == NULL)
	{
		outputLog("ERROR: USBIO_BOARD is specified, but neither USBIO_AD nor USBIO_DI is specified.");
		return E_FAIL;
	}

	// set flag
	g_useUSBIO = true;

	return S_OK;
}

void SGTusbIO::recordData(int dataCounter)
{
	if (m_ADBuffer != NULL)
	{
		for (int i = 0; i < m_numADChannels; i++) {
			ulAIn(m_handle, m_ADChannelList[i], AI_SINGLE_ENDED,	m_ADRangeList[i],
            AIN_FF_NOSCALEDATA, &m_ADBuffer[dataCounter*m_numADChannels + i]);
		}
	}
	if (m_DIBuffer != NULL)
		ulDIn(m_handle, m_DIport, &m_DIBuffer[dataCounter]);

}

int SGTusbIO::getCurrentAIData(int* nChan, int* chanList, int* valueList)
{
	if(m_ADBuffer != NULL)
	{
		*nChan = m_numADChannels;
		double val;
		for (int i = 0; i < m_numADChannels; i++) {
			ulAIn(m_handle, m_ADChannelList[i], AI_SINGLE_ENDED,
				m_ADRangeList[i], AIN_FF_NOSCALEDATA, &val);
			chanList[i] = m_ADChannelList[i];
			valueList[i] = (int)val;
		}
		return S_OK;
	}

	return E_FAIL;
}

int SGTusbIO::getCurrentDIData(unsigned short* value)
{
	unsigned long long data;
	if (m_DIBuffer != NULL)
	{
		ulDIn(m_handle, m_DIport, &data);
		*value = (unsigned short)data;
		return S_OK;
	}
	
	return E_FAIL;
}

void SGTusbIO::getDataFormatString(char* buff, int buffsize)
{
	int len = 0;
	for (int i = 0; i < m_numADChannels; i++) {
		len += snprintf(buff + len, buffsize - len, "AD%d;", (int)m_ADChannelList[i]);
	}
	if (m_DIBuffer != NULL)
		len += snprintf(buff + len, buffsize - len, "DI");

	//delete ';'
	if (len > 0 && buff[len - 1] == ';')
		buff[len - 1] = '\0';

}


void SGTusbIO::getDataString(int index, char* buff, int buffsize)
{
	int len = 0;
	if (m_ADBuffer != NULL)
		for (int chan = 0; chan < m_numADChannels; chan++)
		{
			len += snprintf(buff + len, buffsize - len, "%d;", (int)m_ADBuffer[index*m_numADChannels + chan]);
		}
	if (m_DIBuffer != NULL)
		len += snprintf(buff + len, buffsize - len, "%lld", m_DIBuffer[index]);

	//delete ';'
	if (len > 0 && buff[len - 1] == ';')
		buff[len - 1] = '\0';
}

#endif