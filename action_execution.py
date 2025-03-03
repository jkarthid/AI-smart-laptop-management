#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Action Execution Module for AI Smart Laptop Management

This module handles the execution of actions on the Windows system based on
LLM recommendations, such as changing system settings, managing processes,
and displaying notifications.
"""

import logging
import os
import subprocess
import psutil
from typing import Dict, List, Any, Optional, Union

# For Windows notifications
from win32api import *
from win32gui import *
from win32con import *

logger = logging.getLogger('action_execution')


class ActionExecutor:
    """Handles execution of system actions based on LLM recommendations."""
    
    def __init__(self):
        """Initialize the action executor."""
        self.available_actions = {
            'terminate_process': self._terminate_process,
            'show_notification': self._show_notification,
            'set_power_plan': self._set_power_plan,
            'close_application': self._close_application,
            'start_application': self._start_application
        }
    
    def execute_actions(self, actions: List[Dict]) -> List[str]:
        """Execute a list of actions.
        
        Args:
            actions: List of action dictionaries with name and parameters
            
        Returns:
            List of result messages for each action
        """
        results = []
        
        for action in actions:
            try:
                action_name = action['name']
                params = action.get('parameters', {})
                
                if action_name in self.available_actions:
                    result = self.available_actions[action_name](**params)
                    results.append(result)
                else:
                    error_msg = f"Unknown action: {action_name}"
                    logger.warning(error_msg)
                    results.append(error_msg)
            except Exception as e:
                error_msg = f"Error executing action {action.get('name', 'unknown')}: {e}"
                logger.error(error_msg)
                results.append(error_msg)
        
        return results
    
    def _terminate_process(self, pid: int = None, name: str = None) -> str:
        """Terminate a process by PID or name.
        
        Args:
            pid: Process ID to terminate
            name: Process name to terminate
            
        Returns:
            Result message
        """
        try:
            if pid:
                process = psutil.Process(pid)
                process.terminate()
                return f"Process with PID {pid} terminated"
            elif name:
                count = 0
                for process in psutil.process_iter(['pid', 'name']):
                    if process.info['name'].lower() == name.lower():
                        process.terminate()
                        count += 1
                return f"{count} processes named '{name}' terminated"
            else:
                return "No PID or process name provided"
        except psutil.NoSuchProcess:
            return f"Process not found"
        except psutil.AccessDenied:
            return f"Access denied when trying to terminate process"
        except Exception as e:
            return f"Error terminating process: {e}"
    
    def _show_notification(self, title: str, message: str) -> str:
        """Show a Windows notification.
        
        Args:
            title: Notification title
            message: Notification message
            
        Returns:
            Result message
        """
        try:
            # Initialize notification parameters
            wc = WNDCLASS()
            hinst = wc.hInstance = GetModuleHandle(None)
            wc.lpszClassName = "PythonTaskbar"
            wc.lpfnWndProc = DefWindowProc
            classAtom = RegisterClass(wc)
            
            # Create the window
            style = WS_OVERLAPPED | WS_SYSMENU
            hwnd = CreateWindow(classAtom, "Taskbar", style,
                              0, 0, CW_USEDEFAULT, CW_USEDEFAULT,
                              0, 0, hinst, None)
            UpdateWindow(hwnd)
            
            # Show notification
            Shell_NotifyIcon(NIM_ADD, (
                hwnd, 0, NIF_ICON | NIF_MESSAGE | NIF_TIP,
                WM_USER+20, hinst, "Notification", message, 0, 0, "Tooltip"))
            
            # Clean up
            DestroyWindow(hwnd)
            UnregisterClass(wc.lpszClassName, None)
            
            return "Notification displayed"
        except Exception as e:
            return f"Error showing notification: {e}"
    
    def _set_power_plan(self, plan: str) -> str:
        """Change the Windows power plan.
        
        Args:
            plan: Power plan name ('balanced', 'high_performance', 'power_saver')
            
        Returns:
            Result message
        """
        try:
            # Map friendly names to GUIDs
            power_plans = {
                'balanced': '381b4222-f694-41f0-9685-ff5bb260df2e',
                'high_performance': '8c5e7fda-e8bf-4a96-9a85-a6e23a8c635c',
                'power_saver': 'a1841308-3541-4fab-bc81-f71556f20b4a'
            }
            
            if plan.lower() not in power_plans:
                return f"Unknown power plan: {plan}"
            
            guid = power_plans[plan.lower()]
            result = subprocess.run(['powercfg', '/s', guid], capture_output=True, text=True)
            
            if result.returncode == 0:
                return f"Power plan changed to {plan}"
            else:
                return f"Error changing power plan: {result.stderr}"
        except Exception as e:
            return f"Error setting power plan: {e}"
    
    def _close_application(self, name: str) -> str:
        """Close an application gracefully.
        
        Args:
            name: Application name
            
        Returns:
            Result message
        """
        try:
            count = 0
            for process in psutil.process_iter(['pid', 'name']):
                if process.info['name'].lower() == name.lower():
                    # Try to close gracefully first
                    process.terminate()
                    count += 1
            
            if count > 0:
                return f"{count} instances of {name} closed"
            else:
                return f"No running instances of {name} found"
        except Exception as e:
            return f"Error closing application: {e}"
    
    def _start_application(self, path: str, args: List[str] = None) -> str:
        """Start an application.
        
        Args:
            path: Path to the application
            args: Optional list of command-line arguments
            
        Returns:
            Result message
        """
        try:
            if not os.path.exists(path):
                return f"Application not found: {path}"
            
            cmd = [path]
            if args:
                cmd.extend(args)
            
            process = subprocess.Popen(cmd)
            return f"Application started with PID {process.pid}"
        except Exception as e:
            return f"Error starting application: {e}"


# For testing
if __name__ == '__main__':
    # Configure logging for standalone testing
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Create action executor
    executor = ActionExecutor()
    
    # Test notification
    test_actions = [
        {
            'name': 'show_notification',
            'parameters': {
                'title': 'Test Notification',
                'message': 'This is a test notification'
            }
        }
    ]
    
    results = executor.execute_actions(test_actions)
    for result in results:
        print(f"\nResult: {result}")