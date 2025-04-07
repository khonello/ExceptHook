import os
import sys
import site
import shutil

def write_sitecustomize():
    '''Write the sitecustomize.py and if one already exists, copy that to sitecustomize.py.bak as backup incase things fail'''

    if sys.base_prefix == sys.prefix:
        print("You must be in a virtual environment")

    else:

        for sitepackage_directory in site.getsitepackages():
            if sitepackage_directory.__contains__("site-packages"):

                sitecustomize = os.path.join(sitepackage_directory, "sitecustomize.py")
                if os.path.exists(sitecustomize):

                    shutil.copyfile(sitecustomize, f"{sitecustomize}.bak")
                
                with open(sitecustomize, "w") as w:
                    with open("code.py", "r") as r:
                        
                        w.write(r.read())
                print("Successfully wrote sitecustomize.py")
                