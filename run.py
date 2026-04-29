import ssl
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


try:
    _create_unverified_https_context = ssl._create_default_https_context
except AttributeError:
    pass
else:
    ssl._create_default_https_context = _create_unverified_https_context

# 然后才是你原有的导入和代码
from webui.app import main

if __name__ == "__main__":
    main()