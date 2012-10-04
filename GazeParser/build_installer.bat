.\setup.py clean --all
.\setup.py sdist
.\setup.py build
.\setup.py bdist_wininst --install-script GazeParser_post_install.py --user-access-control force
