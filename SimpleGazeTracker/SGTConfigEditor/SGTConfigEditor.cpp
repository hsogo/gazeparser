#include <wx/wx.h>

extern int getApplicationDirectoryPath(wxString* path);
extern int getParameterDirectoryPath(wxString* path);

class SGTConfigApp : public wxApp
{
    virtual bool OnInit() override;
 
};

wxDECLARE_APP(SGTConfigApp);

class SGTConfigFrame : public wxFrame
{
public:
    SGTConfigFrame();
    virtual ~SGTConfigFrame();

    bool OnOpenFile(void);
    void OnClose(wxCloseEvent& event);

private:
    wxString mConfigFileName;
};

bool SGTConfigApp::OnInit()
{
    wxString config_file;
    if (!wxApp::OnInit())
        return false;

    if (argc > 1) {
        config_file.assign(argv[1]);
    }
    else {
        wxString paramDir;
        getParameterDirectoryPath(&paramDir);
        wxFileDialog dlg(NULL,
            "Select SimpleGazeTracker Configuration file",
            paramDir,
            wxEmptyString,
            wxString::Format
            (
                "All files (%s)|%s",
                wxFileSelectorDefaultWildcardStr,
                wxFileSelectorDefaultWildcardStr
            ));
        dlg.ShowModal();
        config_file = dlg.GetFilename();

    }

    SGTConfigFrame* frame = new SGTConfigFrame;
    frame->Show();

    return true;
}

SGTConfigFrame::SGTConfigFrame()
    : wxFrame(nullptr, wxID_ANY, "Minimal App")
{
    // main menu
    auto menuBar = new wxMenuBar;
    auto menuFile = new wxMenu;
    menuFile->Append(wxID_EXIT, "Quit");
    menuBar->Append(menuFile, "File");
    SetMenuBar(menuBar);

    Bind(wxEVT_CLOSE_WINDOW, &SGTConfigFrame::OnClose, this);
    Bind(wxEVT_MENU, [this](wxCommandEvent&) { Close(true); }, wxID_EXIT);
}

SGTConfigFrame::~SGTConfigFrame()
{
}

void SGTConfigFrame::OnClose(wxCloseEvent& event)
{
    Destroy();
}

bool SGTConfigFrame::OnOpenFile(void)
{
    if (mConfigFileName.length() == 0) {
        return(false);
    }



    return(true);
}

wxIMPLEMENT_APP(SGTConfigApp);