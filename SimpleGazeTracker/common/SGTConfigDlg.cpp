#include "SGTConfigDlg.h"
#include <wx/notebook.h>

#include "SGTCommon.h"

SGTParamInt::SGTParamInt(const char* name, int* var, const char* p, const char* hint)
{
	char* pp;
	strncpy(m_pName, name, sizeof(m_pName));
	m_Value = var;
	*m_Value = strtol(p, &pp, 10);
	m_hint.assign(hint);
	m_type = SGTPARAM_INT;
	backup();
}

bool SGTParamInt::validate(const std::string s, bool update)
{
	int i;
	try {
		i = std::stoi(s);
	}
	catch (std::invalid_argument e){
		return false;
	}
	catch (std::out_of_range e) {
		return false;
	}

	if (update)	*m_Value = i;
	return true;	
}


SGTParamFloat::SGTParamFloat(const char* name, float* var, const char* p, const char* hint)
{
	char* pp;
	strncpy(m_pName, name, sizeof(m_pName));
	m_Value = var;
	*m_Value = strtof(p, &pp);
	m_hint.assign(hint);
	m_type = SGTPARAM_FLOAT;
	backup();
}

bool SGTParamFloat::validate(const std::string s, bool update)
{
	float f;
	try {
		f = std::stof(s);
	}
	catch (std::invalid_argument e) {
		return false;
	}
	catch (std::out_of_range e) {
		return false;
	}

	if (update)	*m_Value = f;
	return true;
}

SGTParamString::SGTParamString(const char* name, std::string* var, const char* p, const char* hint)
{
	strncpy(m_pName, name, sizeof(m_pName));
	m_Value = var;
	m_Value->assign(p);
	m_hint.assign(hint);
	m_type = SGTPARAM_STRING;
	backup();
}

bool SGTParamString::validate(const std::string s, bool update)
{
	if (update) m_Value->assign(s);
	return true;
}

std::vector<SGTParam*> g_pGeneralParamsVector;
std::vector<SGTParam*> g_pImageParamsVector;
std::vector<SGTParam*> g_pIOParamsVector;
std::vector<SGTParam*> g_pCameraParamsVector;


SGTConfigDlg::SGTConfigDlg(wxWindow *parent, wxWindowID id, const wxString &title, const wxPoint &pos, const wxSize &size, long style, const wxString &name) :
	wxDialog(parent, id, title, pos, size, style, name)
{
	long tc_style = 0L;

	wxPanel* rootPanel = new wxPanel(this);

	notebook = new wxNotebook(rootPanel, -1, wxDefaultPosition, wxDefaultSize, wxNB_MULTILINE);

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
		(*it)->backup();
		wxStaticText* menu = new wxStaticText(pPageGeneral, wxID_ANY, (*it)->getName());
		pGeneralSizer->Add(menu, 0, wxALL, 5);
		m_pParamItems.push_back(*it);

		tc_style = ((*it)->getType() != SGTPARAM_STRING) ? (wxTE_RIGHT | wxTE_PROCESS_ENTER) : wxTE_PROCESS_ENTER;
		wxTextCtrl* ctrl = new wxTextCtrl(pPageGeneral, wxID_ANY, (*it)->getValueStr(), wxDefaultPosition, wxDefaultSize, tc_style);
		ctrl->SetToolTip((*it)->getHint());
		pGeneralSizer->Add(ctrl, wxALIGN_CENTER_VERTICAL);
		m_pParamTextCtrls.push_back(ctrl);
	}

	//image
	for (it = g_pImageParamsVector.begin(); it != g_pImageParamsVector.end(); it++)
	{
		(*it)->backup();
		wxStaticText* menu = new wxStaticText(pPageImage, wxID_ANY, (*it)->getName());
		pImageSizer->Add(menu, 0, wxALL, 5);
		m_pParamItems.push_back(*it);

		tc_style = ((*it)->getType() != SGTPARAM_STRING) ? (wxTE_RIGHT | wxTE_PROCESS_ENTER) : wxTE_PROCESS_ENTER;
		wxTextCtrl* ctrl = new wxTextCtrl(pPageImage, wxID_ANY, (*it)->getValueStr(), wxDefaultPosition, wxDefaultSize, tc_style);
		ctrl->SetToolTip((*it)->getHint());
		pImageSizer->Add(ctrl, wxALIGN_CENTER_VERTICAL);
		m_pParamTextCtrls.push_back(ctrl);

	}

	//io
	for (it = g_pIOParamsVector.begin(); it != g_pIOParamsVector.end(); it++)
	{
		int ttt;
		(*it)->backup();
		wxStaticText* menu = new wxStaticText(pPageIO, wxID_ANY, (*it)->getName());
		pIOSizer->Add(menu, 0, wxALL, 5);
		m_pParamItems.push_back(*it);

		ttt = (*it)->getType();
		tc_style = ((*it)->getType() != SGTPARAM_STRING) ? (wxTE_RIGHT | wxTE_PROCESS_ENTER) : wxTE_PROCESS_ENTER;
		wxTextCtrl* ctrl = new wxTextCtrl(pPageIO, wxID_ANY, (*it)->getValueStr(), wxDefaultPosition, wxDefaultSize, tc_style);
		ctrl->SetToolTip((*it)->getHint());
		pIOSizer->Add(ctrl, wxALIGN_CENTER_VERTICAL);
		m_pParamTextCtrls.push_back(ctrl);
	}

	//camera
	for (it = g_pCameraParamsVector.begin(); it != g_pCameraParamsVector.end(); it++)
	{
		(*it)->backup();
		wxStaticText* menu = new wxStaticText(pPageCamera, wxID_ANY, (*it)->getName());
		pCameraSizer->Add(menu, 0, wxALL, 5);
		m_pParamItems.push_back(*it);

		tc_style = ((*it)->getType() != SGTPARAM_STRING) ? (wxTE_RIGHT | wxTE_PROCESS_ENTER) : wxTE_PROCESS_ENTER;
		wxTextCtrl* ctrl = new wxTextCtrl(pPageCamera, wxID_ANY, (*it)->getValueStr(), wxDefaultPosition, wxDefaultSize, tc_style);
		ctrl->SetToolTip((*it)->getHint());
		pCameraSizer->Add(ctrl, wxALIGN_CENTER_VERTICAL);
		m_pParamTextCtrls.push_back(ctrl);
	}


	pPageGeneral->SetSizerAndFit(pGeneralSizer);
	pPageImage->SetSizerAndFit(pImageSizer);
	pPageIO->SetSizerAndFit(pIOSizer);
	pPageCamera->SetSizerAndFit(pCameraSizer);

	notebook->AddPage(pPageGeneral, "General");
	notebook->AddPage(pPageImage, "Image");
	notebook->AddPage(pPageIO, "I/O");
	notebook->AddPage(pPageCamera, "Camera specific");

	wxPanel* pButtonPanel = new wxPanel(rootPanel, wxID_ANY);
	wxBoxSizer* pButtonPanelSizer = new wxBoxSizer(wxHORIZONTAL);

	wxButton* pButtonHelp = new wxButton(pButtonPanel, wxID_ANY, "Help");
	wxButton* pButtonSaveExit = new wxButton(pButtonPanel, wxID_ANY, "Save and exit");
	wxButton* pButtonCancel = new wxButton(pButtonPanel, wxID_ANY, "Cancel");

	pButtonPanelSizer->Add(pButtonHelp);
	pButtonPanelSizer->Add(pButtonSaveExit);
	pButtonPanelSizer->Add(pButtonCancel);

	pButtonPanel->SetSizerAndFit(pButtonPanelSizer);
	pButtonPanel->Fit();

	wxBoxSizer* pSizer = new wxBoxSizer(wxVERTICAL);
	pSizer->Add(notebook);
	pSizer->Add(pButtonPanel, 1, wxEXPAND);

	rootPanel->SetSizerAndFit(pSizer);
	Fit();

	pButtonHelp->Bind(wxEVT_BUTTON, &SGTConfigDlg::onHelpButton, this);
	pButtonSaveExit->Bind(wxEVT_BUTTON, &SGTConfigDlg::onSaveExitButton, this);
	pButtonCancel->Bind(wxEVT_BUTTON, &SGTConfigDlg::onCancelButton, this);

}

void SGTConfigDlg::onHelpButton(wxCommandEvent & event)
{
	std::string path;

	if (checkFile(g_DocPath, "params.html") == E_FAIL) {
		outputLogDlg("Cound not find HTML document (doc/params.html).", "Error", wxICON_ERROR);
		return;
	}

	path.assign(g_DocPath);
	path.insert(0, "file://");
	path.append(PATH_SEPARATOR);
	path.append("params.html");

	openLocation(path);

	return;
}

void SGTConfigDlg::onCancelButton(wxCommandEvent & event)
{
	EndModal(wxCANCEL);
}

void SGTConfigDlg::onSaveExitButton(wxCommandEvent & event)
{
	std::string s;
	std::string error_msg;
	std::vector<SGTParam*>::iterator it;
	int num_error = 0;
	error_msg.assign("Invalid value(s) at:\n");

	for (it = m_pParamItems.begin(); it != m_pParamItems.end(); it++) (*it)->backup();

	for (int i=0; i<m_pParamItems.size(); i++)
	{
		s = m_pParamTextCtrls.at(i)->GetValue();
		if (!m_pParamItems.at(i)->validate(s, true)) {
			if (num_error < 8) { //only 8 erros on Error Dialog
				error_msg.append(m_pParamItems.at(i)->getName());
				error_msg.append("\n");
				num_error += 1;
			}
		}
	}

	if (num_error>0)
	{
		for (it = m_pParamItems.begin(); it != m_pParamItems.end(); it++) (*it)->restore();
		wxMessageBox(error_msg, "Error", wxICON_ERROR);
		return;
	}

	EndModal(wxOK);
}
