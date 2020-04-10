#pragma once

#define MAX_USB_AD_CHANNELS 8


class SGTusbIO
{
public:
	int init(std::string board, std::string paramAD, std::string paramDI, int maxdata);
	int checkAD(void);
	int checkDI(void);
	~SGTusbIO();

	void recordData(int dataCounter);
	void getDataFormatString(char* buff, int buffsize);
	void getDataString(int index, char* buff, int buffsize);

private:

	int m_DIport;

	int m_boardNum;
	int m_numADChannels;
	int m_ADResolution;
	int m_ADChannelList[MAX_USB_AD_CHANNELS][2]; /*0: Channel number  1:AD range**/

	DWORD m_latestADValue32[MAX_USB_AD_CHANNELS];
	WORD m_latestADValue16[MAX_USB_AD_CHANNELS];
	WORD m_latestDIValue;

	DWORD* m_ADBuffer32;
	WORD* m_ADBuffer16;
	unsigned short* m_DIBuffer;

};