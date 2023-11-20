
# for backword compatibility
# python -m GazePaser.app.Viewer
from .viewer.DataViewer import ViewerApp
application = ViewerApp()
application.MainLoop()
