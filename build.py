#!/usr/bin/env python3
import os
import shutil
import sys

include_libs = '--skip-libs' not in sys.argv

os.chdir(os.path.normpath(os.path.join(__file__, '..')))

if include_libs:
    os.system('pip install -r requirements.txt --target ./build/libs/python --upgrade')

os.makedirs('build/lambda_stage', exist_ok=True)
shutil.copytree('barbot', 'build/lambda_stage/barbot', dirs_exist_ok=True)
