#!/usr/bin/env python3
import os
path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "resource_pool.py")
with open(path, "w", encoding="utf-8") as f:
    f.write("placeholder")
print("ok")
