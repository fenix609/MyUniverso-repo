# -*- coding: utf-8 -*-
import sys
from resources.lib import router

# Dirección del archivo menú.xml alojado en GitHub
MENU_URL = ("https://raw.githubusercontent.com/fenix609/Addon-multimedia/"
            "refs/heads/main/C%C3%B3digo/men%C3%BA.xml")

if __name__ == "__main__":
    router.run(sys.argv, MENU_URL)
