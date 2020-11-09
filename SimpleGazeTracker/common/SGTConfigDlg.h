#pragma once

#include <wx/wxprec.h>
#ifndef WX_PRECOMP
#include <wx/wx.h>
#endif

#include <wx/notebook.h>

#define SGTPARAM_ORIG	0
#define SGTPARAM_INT	1
#define SGTPARAM_FLOAT	2
#define SGTPARAM_STRING	3

class SGTParam
{
public:
	char* getName() { return m_pName; };
	std::string getHint() { return m_hint; };
	int getType() { return m_type; };
	virtual const char* getValueStr() = 0;
	virtual void backup() {};
	virtual void restore() {};
	virtual bool validate(const std::string s, bool update) { return true; };

protected:
	char m_pName[64];
	std::string m_hint;
	int m_type = SGTPARAM_ORIG;
};

class SGTParamInt : public SGTParam
{
public:
	SGTParamInt(const char* name, int* var, const char* p, const char* hint);
	const char* getValueStr() { snprintf(m_buff, sizeof(m_buff), "%d", *m_Value); return m_buff; };
	void backup() { m_Backup = *m_Value; };
	void restore() { *m_Value = m_Backup; };
	bool validate(const std::string s, bool update);
private:
	int* m_Value;
	int m_Backup;
	char m_buff[100];
};


class SGTParamFloat : public SGTParam
{
public:
	SGTParamFloat(const char* name, float* var, const char* p, const char* hint);
	const char* getValueStr() { snprintf(m_buff, sizeof(m_buff), "%f", *m_Value); return m_buff; };
	void backup() { m_Backup = *m_Value; };
	void restore() { *m_Value = m_Backup; };
	bool validate(const std::string s, bool update);
private:
	float* m_Value;
	float m_Backup;
	char m_buff[100];
};


class SGTParamString : public SGTParam
{
public:
	SGTParamString(const char* name, std::string* var, const char* p, const char* hint);
	const char* getValueStr() { return m_Value->c_str(); };
	void backup() { m_Backup.assign(*m_Value); };
	void restore() { m_Value->assign(m_Backup); };
	bool validate(const std::string s, bool update); // always true
private:
	std::string* m_Value;
	std::string m_Backup;
};


class SGTConfigDlg : public wxDialog
{
public:
	SGTConfigDlg(wxWindow *parent, wxWindowID id, const wxString &title, const wxPoint &pos, const wxSize &size, long style, const wxString &name);


private:
	wxNotebook* notebook;
	std::vector<SGTParam*> m_pParamItems;
	std::vector<wxTextCtrl*> m_pParamTextCtrls;
	void onHelpButton(wxCommandEvent& event);
	void onCancelButton(wxCommandEvent& event);
	void onSaveExitButton(wxCommandEvent& event);
};

