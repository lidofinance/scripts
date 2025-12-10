# sitecustomize.py

print("======================================================================applied")
try:
    import solcx.install as solcx_install
except ImportError:
    # py-solc-x not installed in this environment; nothing to patch
    pass
else:
    # change this to your mirror / URL
    solcx_install.BINARY_DOWNLOAD_BASE = "https://binaries.soliditylang.org/{}-amd64/{}"