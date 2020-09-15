#pragma once

#include <wx/wxprec.h>
#ifndef WX_PRECOMP
#include <wx/wx.h>
#endif

#include <wx/notebook.h>

class SGTParam
{
public:
	char m_pName[64];
	char* getName() { return m_pName; };
	virtual const char* getValueStr() = 0;
	virtual void serialize(std::string* buff) {};
};

class SGTParamInt : public SGTParam
{
public:
	SGTParamInt(const char* name, int* var, const char* p);
	const char* getValueStr() { snprintf(m_buff, sizeof(m_buff), "%d", *m_Value); return m_buff; };
	//void serialize(std::string* buff);
private:
	int* m_Value;
	char m_buff[100];
};


class SGTParamFloat : public SGTParam
{
public:
	SGTParamFloat(const char* name, float* var, const char* p);
	const char* getValueStr() { snprintf(m_buff, sizeof(m_buff), "%f", *m_Value); return m_buff; };
	//void serialize(std::string* buff);
private:
	float* m_Value;
	char m_buff[100];
};


class SGTParamString : public SGTParam
{
public:
	SGTParamString(const char* name, std::string* var, const char* p);
	const char* getValueStr() { return m_Value->c_str(); };
	//void serialize(std::string* buff);
private:
	std::string* m_Value;
};


class SGTConfigDlg : public wxDialog
{
public:
	SGTConfigDlg(wxWindow *parent, wxWindowID id, const wxString &title, const wxPoint &pos, const wxSize &size, long style, const wxString &name);


private:
	wxNotebook* notebook;
	std::vector<wxStaticText*> m_pParamItems;
	std::vector<wxTextCtrl*> m_pParamTextCtrls;
};

