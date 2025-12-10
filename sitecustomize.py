# sitecustomize.py
try:
    import solcx.install as solcx_install
except ImportError:
    # py-solc-x not installed in this environment; nothing to patch
    pass
else:
    # replace outdated solc binaries URL with the current one
    solcx_install.BINARY_DOWNLOAD_BASE = "https://binaries.soliditylang.org/{}-amd64/{}"