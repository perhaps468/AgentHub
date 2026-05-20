$content = "@echo off`nchcp 65001 >nul`ngit checkout -b `"feature:初始化项目结构`"`ngit add .`n"
[System.IO.File]::WriteAllText("$PWD\create-branch.bat", $content, [System.Text.Encoding]::GetEncoding(65001))