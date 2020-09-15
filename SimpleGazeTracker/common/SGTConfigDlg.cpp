#include "SGTConfigDlg.h"
#include <wx/notebook.h>

SGTParamInt::SGTParamInt(const char* name, int* var, const char* p)
{
	char* pp;
	strncpy(m_pName, name, sizeof(m_pName));
	m_Value = var;
	*m_Value = strtol(p, &pp, 10);
}

SGTParamFloat::SGTParamFloat(const char* name, float* var, const char* p)
{
	char* pp;
	strncpy(m_pName, name, sizeof(m_pName));
	m_Value = var;
	*m_Value = strtof(p, &pp);
}

SGTParamString::SGTParamString(const char* name, std::string* var, const char* p)
{
	strncpy(m_pName, name, sizeof(m_pName));
	m_Value = var;
	m_Value->assign(p);
}
std::vector<SGTParam*> g_pGeneralParamsVector;
std::vector<SGTParam*> g_pImageParamsVector;
std::vector<SGTParam*> g_pIOParamsVector;
std::vector<SGTParam*> g_pCameraParamsVector;


SGTConfigDlg::SGTConfigDlg(wxWindow *parent, wxWindowID id, const wxString &title, const wxPoint &pos, const wxSize &size, long style, const wxString &name) :
	wxDialog(parent, id, title, pos, size, style, name)
{

	notebook = new wxNotebook(this, -1, wxDefaultPosition, wxDefaultSize, wxNB_MULTILINE);

	wxNotebookPage* pPageGeneral = new wxNotebookPage(notebook, -1);
	wxNotebookPage* pPageImage = new wxNotebookPage(notebook, -1);
	wxNotebookPage* pPageIO = new wxNotebookPage(notebook, -1);
	wxNotebookPage* pPageCamera = new wxNotebookPage(notebook, -1);

	wxFlexGridSizer* pGeneralSizer = new wxFlexGridSizer(2);
	wxFlexGridSizer* pImageSizer = new wxFlexGridSizer(2);
	wxFlexGridSizer* pIOSizer = new wxFlexGridSizer(2);
	wxFlexGridSizer* pCameraSizer = new wxFlexGridSizer(2);

	std::vector<SGTParam*>::iterator it;

	//general
	for (it = g_pGeneralParamsVector.begin(); it != g_pGeneralParamsVector.end(); it++)
	{
		wxStaticText* menu = new wxStaticText(pPageGeneral, wxID_ANY, (*it)->getName());
		pGeneralSizer->Add(menu, 0, wxALL, 5);
		m_pParamItems.push_back(menu);

		wxTextCtrl* ctrl = new wxTextCtrl(pPageGeneral, wxID_ANY, (*it)->getValueStr(), wxDefaultPosition, wxDefaultSize, wxTE_RIGHT | wxTE_PROCESS_ENTER);
		pGeneralSizer->Add(ctrl, wxALIGN_CENTER_VERTICAL);
		m_pParamTextCtrls.push_back(ctrl);
	}

	//image
	//io
	for (it = g_pImageParamsVector.begin(); it != g_pImageParamsVector.end(); it++)
	{
		wxStaticText* menu = new wxStaticText(pPageIO, wxID_ANY, (*it)->getName());
		pImageSizer->Add(menu, 0, wxALL, 5);
		m_pParamItems.push_back(menu);

		wxTextCtrl* ctrl = new wxTextCtrl(pPageImage, wxID_ANY, (*it)->getValueStr(), wxDefaultPosition, wxDefaultSize, wxTE_RIGHT | wxTE_PROCESS_ENTER);
		pImageSizer->Add(ctrl, wxALIGN_CENTER_VERTICAL);
		m_pParamTextCtrls.push_back(ctrl);

	}

	//io
	for (it = g_pIOParamsVector.begin(); it != g_pIOParamsVector.end(); it++)
	{
		wxStaticText* menu = new wxStaticText(pPageIO, wxID_ANY, (*it)->getName());
		pIOSizer->Add(menu, 0, wxALL, 5);
		m_pParamItems.push_back(menu);

		wxTextCtrl* ctrl = new wxTextCtrl(pPageIO, wxID_ANY, (*it)->getValueStr(), wxDefaultPosition, wxDefaultSize, wxTE_RIGHT | wxTE_PROCESS_ENTER);
		pIOSizer->Add(ctrl, wxALIGN_CENTER_VERTICAL);
		m_pParamTextCtrls.push_back(ctrl);
	}

	//camera
	for (it = g_pCameraParamsVector.begin(); it != g_pCameraParamsVector.end(); it++)
	{
		wxStaticText* menu = new wxStaticText(pPageCamera, wxID_ANY, (*it)->getName());
		pCameraSizer->Add(menu, 0, wxALL, 5);
		m_pParamItems.push_back(menu);

		wxTextCtrl* ctrl = new wxTextCtrl(pPageCamera, wxID_ANY, (*it)->getValueStr(), wxDefaultPosition, wxDefaultSize, wxTE_RIGHT | wxTE_PROCESS_ENTER);
		pCameraSizer->Add(ctrl, wxALIGN_CENTER_VERTICAL);
		m_pParamTextCtrls.push_back(ctrl);
	}


	pPageGeneral->SetSizer(pGeneralSizer);
	pPageImage->SetSizer(pImageSizer);
	pPageIO->SetSizer(pIOSizer);
	pPageCamera->SetSizer(pCameraSizer);

	notebook->AddPage(pPageGeneral, "General");
	notebook->AddPage(pPageImage, "Image");
	notebook->AddPage(pPageIO, "I/O");
	notebook->AddPage(pPageCamera, "Camera");

	wxFlexGridSizer* pSizer = new wxFlexGridSizer(2, 1, 0, 0);
	pSizer->Add(notebook, 1, wxEXPAND);

	wxButton* pButtonOK = new wxButton(this, wxID_ANY, "OK");
	pSizer->Add(pButtonOK, 1,  wxALIGN_RIGHT|wxALIGN_BOTTOM);

	SetSizer(pSizer);
	this->Fit();
	//SetAutoLayout(true);
}
