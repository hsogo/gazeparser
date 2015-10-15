python setup.py clean --all
python setup.py sdist
python setup.py build bdist_wininst --install-script GazeParser_post_install.py
