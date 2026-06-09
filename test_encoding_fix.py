# -*- coding: utf-8 -*-
"""Test script to verify the encoding fix for Java command output."""

import subprocess
import sys
import os

# Add the app directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from app.runtime.tools.run_command_tool import RunCommandTool


def test_java_utf8_output():
    """Test that Java output is correctly decoded as UTF-8."""
    tool = RunCommandTool(workspace_root="D:\\code\\school\\java\\test2")
    
    # First compile
    result = tool.execute("javac Main.java", "D:\\code\\school\\java\\test2", 30)
    print("=== javac result ===")
    print(result)
    print()
    
    # Then run
    result = tool.execute("java Main", "D:\\code\\school\\java\\test2", 30)
    print("=== java result ===")
    print(result)
    print()
    
    # Check if the output contains correct Chinese characters
    if "张三" in result or "李四" in result:
        print("✓ SUCCESS: Chinese characters decoded correctly!")
        return True
    elif "寮犱笁" in result or "鏉庡洓" in result:
        print("✗ FAIL: Garbled characters still present!")
        return False
    else:
        print("? UNCLEAR: Could not verify encoding (no Chinese chars found)")
        return None


def test_echo_command():
    """Test a simple echo command to ensure basic functionality."""
    tool = RunCommandTool(workspace_root="D:\\code\\school\\java\\test2")
    
    if sys.platform == "win32":
        result = tool.execute("echo Hello", "D:\\code\\school\\java\\test2", 10)
    else:
        result = tool.execute("echo Hello", "/tmp", 10)
    
    print("=== echo result ===")
    print(result)
    print()
    
    if "Hello" in result:
        print("✓ echo command works")
        return True
    return False


if __name__ == "__main__":
    print(f"Platform: {sys.platform}")
    print(f"Python version: {sys.version}")
    print()
    
    test_echo_command()
    print("=" * 50)
    test_java_utf8_output()
