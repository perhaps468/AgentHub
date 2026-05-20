# -*- coding: utf-8 -*-
import subprocess

branch_name = "feature/初始化项目结构"
subprocess.run(["git", "checkout", "-b", branch_name], check=True)
subprocess.run(["git", "add", "."], check=True)
print("Done! Branch created and files added.")
