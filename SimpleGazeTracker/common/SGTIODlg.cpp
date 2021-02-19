#include "SGTIODlg.h"
#include "SGTusbIO.h"

SGTIODlg::SGTIODlg(wxWindow *parent, wxWindowID id, const wxString &title, const wxPoint &pos, const wxSize &size, long style, const wxString &name) :
	wxDialog(parent, id, title, pos, size, style, name)
{
	char buff[256];
	m_pUSBIO = NULL;

	wxPanel* pRootPanel = new wxPanel(this);

	wxFlexGridSizer* pSizer = new wxFlexGridSizer(2, wxSize(10,0));

	wxStaticText* itemName, value;

	itemName = new wxStaticText(pRootPanel, wxID_ANY, "Digital I/O");
	pSizer->Add(itemName);
	m_pDIOStatusText = new wxStaticText(pRootPanel, wxID_ANY, "-");
	pSizer->Add(m_pDIOStatusText);

	for (int i = 0; i < MAX_USB_AD_CHANNELS; i++)
	{
		snprintf(buff, sizeof(buff), "Analog I/O #%d", i);
		itemName = new wxStaticText(pRootPanel, wxID_ANY, buff, wxDefaultPosition, wxDefaultSize, wxALIGN_RIGHT);
		pSizer->Add(itemName);
		m_pAIOStatusText[i] = new wxStaticText(pRootPanel, wxID_ANY, "-");
		pSizer->Add(m_pAIOStatusText[i]);

	}
	pRootPanel->SetSizerAndFit(pSizer);

	m_pTimer = new SGTIODlgRenderTimer(this);
	Show();
	m_pTimer->start();

	//Connect(wxID_ANY, wxEVT_IDLE, wxIdleEventHandler(SGTIODlg::onIdle));
}


void SGTIODlg::updateValue()
{
	unsigned short DIvalue;
	int nAIChan, AIchanList[MAX_USB_AD_CHANNELS], AIvalueList[MAX_USB_AD_CHANNELS];
	char buff[256];

	if (SUCCEEDED(m_pUSBIO->getCurrentDIData(&DIvalue))) {
		snprintf(buff, sizeof(buff), "%d", DIvalue);
		m_pDIOStatusText->SetLabel(buff);
		//m_pDIOStatusText->Refresh(false);
	}

	if (SUCCEEDED(m_pUSBIO->getCurrentAIData(&nAIChan, &AIchanList[0], &AIvalueList[0])))
	{
		for (int i = 0; i < nAIChan; i++) {
			for (int j = 0; j < MAX_USB_AD_CHANNELS; j++) {
				if (AIchanList[i] == j) {
					snprintf(buff, sizeof(buff), "%d", AIvalueList[i]);
					m_pAIOStatusText[j]->SetLabel(buff);
					//m_pAIOStatusText[j]->Refresh(false);
				}
			}
		}

	}
	Update();
}

void SGTIODlg::onClose(wxCloseEvent& evt)
{
	m_pTimer->Stop();
	evt.Skip();
}

/*
void SGTIODlg::onIdle(wxIdleEvent& event)
{
	unsigned short DIvalue;
	int nAIChan, AIchanList[MAX_USB_AD_CHANNELS], AIvalueList[MAX_USB_AD_CHANNELS];
	char buff[256];

	event.RequestMore();

	if (SUCCEEDED(m_pUSBIO->getCurrentDIData(&DIvalue))) {
		snprintf(buff, sizeof(buff), "%d", DIvalue);
		m_pDIOStatusText->SetLabel(buff);
		m_pDIOStatusText->Refresh(false);
	}

	if (SUCCEEDED(m_pUSBIO->getCurrentAIData(&nAIChan, &AIchanList[0], &AIvalueList[0])))
	{
		for (int i = 0; i < nAIChan; i++) {
			for (int j = 0; j < MAX_USB_AD_CHANNELS; j++) {
				if (AIchanList[i] == j) {
					snprintf(buff, sizeof(buff), "%d", AIvalueList[i]);
					m_pAIOStatusText[j]->SetLabel(buff);
					m_pAIOStatusText[j]->Refresh(false);
				}
			}
		}

	}
	Update();
}
*/