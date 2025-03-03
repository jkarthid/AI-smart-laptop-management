#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
System Sensors Module for AI Smart Laptop Management

This module collects data from various system sensors on a Windows machine,
including CPU, memory, disk usage, battery status, and system logs.
"""

import logging
import os
import platform
import subprocess
import time
from typing import Dict, List, Any, Optional, Union

# For Windows-specific functionality
import psutil
import win32api
import win32con
import win32evtlog

logger = logging.getLogger('system_sensors')


class SystemSensorManager:
    """Manages the collection of system sensor data."""
    
    def __init__(self):
        """Initialize the system sensor manager."""
        # Verify we're running on Windows
        if platform.system() != 'Windows':
            logger.warning("This module is designed for Windows systems")
        
        # Initialize sensor cache
        self.cache = {}
        self.cache_timeout = 5  # seconds
        self.last_cache_time = 0
    
    def collect_data(self) -> Dict:
        """Collect data from all system sensors.
        
        Returns:
            Dictionary containing all collected system data
        """
        current_time = time.time()
        
        # Use cached data if it's recent enough
        if current_time - self.last_cache_time < self.cache_timeout and self.cache:
            return self.cache.copy()
        
        try:
            # Collect all sensor data
            data = {
                # System resource usage
                'cpu_usage': self._get_cpu_usage(),
                'memory_usage': self._get_memory_usage(),
                'disk_usage': self._get_disk_usage(),
                
                # System state
                'battery': self._get_battery_info(),
                'power_state': self._get_power_state(),
                'running_processes': self._get_running_processes(),
                'system_logs': self._get_system_logs(),
                
                # System info
                'system_info': self._get_system_info()
            }
            
            # Update cache
            self.cache = data.copy()
            self.last_cache_time = current_time
            
            return data
        except Exception as e:
            logger.error(f"Error collecting system data: {e}")
            return {}
    
    def _get_cpu_usage(self) -> float:
        """Get current CPU usage percentage.
        
        Returns:
            CPU usage as a percentage (0-100)
        """
        try:
            return psutil.cpu_percent(interval=0.5)
        except Exception as e:
            logger.error(f"Error getting CPU usage: {e}")
            return 0.0
    
    def _get_memory_usage(self) -> float:
        """Get current memory usage percentage.
        
        Returns:
            Memory usage as a percentage (0-100)
        """
        try:
            memory = psutil.virtual_memory()
            return memory.percent
        except Exception as e:
            logger.error(f"Error getting memory usage: {e}")
            return 0.0
    
    def _get_disk_usage(self) -> Dict:
        """Get disk usage for all drives.
        
        Returns:
            Dictionary with drive letters as keys and usage info as values
        """
        try:
            # Get system drive usage (usually C:)
            system_drive = os.environ.get('SystemDrive', 'C:')
            usage = psutil.disk_usage(system_drive)
            
            return {
                'total': usage.total,
                'used': usage.used,
                'free': usage.free,
                'percent': usage.percent
            }
        except Exception as e:
            logger.error(f"Error getting disk usage: {e}")
            return {'percent': 0.0}
    
    def _get_battery_info(self) -> Dict:
        """Get battery status information.
        
        Returns:
            Dictionary containing battery information
        """
        try:
            if not hasattr(psutil, 'sensors_battery'):
                return {'present': False}
            
            battery = psutil.sensors_battery()
            if battery is None:
                return {'present': False}
            
            return {
                'present': True,
                'percentage': battery.percent,
                'is_charging': battery.power_plugged,
                'seconds_left': battery.secsleft if battery.secsleft != -1 else None
            }
        except Exception as e:
            logger.error(f"Error getting battery info: {e}")
            return {'present': False}
    
    def _get_power_state(self) -> str:
        """Get the current power state of the system.
        
        Returns:
            String indicating power state ('AC', 'Battery', 'Unknown')
        """
        try:
            battery = psutil.sensors_battery()
            if battery is None:
                return 'AC'  # Assume desktop
            
            return 'AC' if battery.power_plugged else 'Battery'
        except Exception as e:
            logger.error(f"Error getting power state: {e}")
            return 'Unknown'
    
    def _get_running_processes(self, limit: int = 10) -> List[Dict]:
        """Get information about running processes.
        
        Args:
            limit: Maximum number of processes to return
            
        Returns:
            List of dictionaries containing process information
        """
        try:
            processes = []
            for proc in psutil.process_iter(['pid', 'name', 'username', 'cpu_percent', 'memory_percent']):
                try:
                    pinfo = proc.info
                    processes.append({
                        'pid': pinfo['pid'],
                        'name': pinfo['name'],
                        'username': pinfo['username'],
                        'cpu_usage': pinfo['cpu_percent'],
                        'memory_usage': pinfo['memory_percent']
                    })
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    pass
            
            # Sort by CPU usage and limit results
            return sorted(processes, key=lambda p: p['cpu_usage'], reverse=True)[:limit]
        except Exception as e:
            logger.error(f"Error getting running processes: {e}")
            return []
    
    def _get_system_logs(self, limit: int = 10) -> List[Dict]:
        """Get recent system event logs.
        
        Args:
            limit: Maximum number of logs to return
            
        Returns:
            List of dictionaries containing log information
        """
        try:
            logs = []
            server = 'localhost'
            log_type = 'System'
            
            hand = win32evtlog.OpenEventLog(server, log_type)
            flags = win32evtlog.EVENTLOG_BACKWARDS_READ | win32evtlog.EVENTLOG_SEQUENTIAL_READ
            total = win32evtlog.GetNumberOfEventLogRecords(hand)
            
            events = win32evtlog.ReadEventLog(hand, flags, 0)
            count = 0
            
            while events and count < limit:
                for event in events:
                    level = 'INFO'
                    if event.EventType == win32evtlog.EVENTLOG_ERROR_TYPE:
                        level = 'ERROR'
                    elif event.EventType == win32evtlog.EVENTLOG_WARNING_TYPE:
                        level = 'WARNING'
                    
                    logs.append({
                        'source': event.SourceName,
                        'time': event.TimeGenerated.Format(),
                        'level': level,
                        'event_id': event.EventID,
                        'description': str(win32evtlogutil.SafeFormatMessage(event, log_type))
                    })
                    count += 1
                    if count >= limit:
                        break
                
                events = win32evtlog.ReadEventLog(hand, flags, 0)
            
            win32evtlog.CloseEventLog(hand)
            return logs
        except Exception as e:
            logger.error(f"Error getting system logs: {e}")
            return []
    
    def _get_system_info(self) -> Dict:
        """Get general system information.
        
        Returns:
            Dictionary containing system information
        """
        try:
            info = {
                'os': platform.system(),
                'os_version': platform.version(),
                'hostname': platform.node(),
                'cpu_count': psutil.cpu_count(logical=True),
                'physical_cpu_count': psutil.cpu_count(logical=False),
                'total_memory': psutil.virtual_memory().total,
                'boot_time': psutil.boot_time()
            }
            return info
        except Exception as e:
            logger.error(f"Error getting system info: {e}")
            return {}


# For testing
if __name__ == '__main__':
    # Configure logging for standalone testing
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Create sensor manager and collect data
    sensor_manager = SystemSensorManager()
    data = sensor_manager.collect_data()
    
    # Print collected data
    print("\nSystem Sensor Data:")
    for key, value in data.items():
        if isinstance(value, dict):
            print(f"\n{key}:")
            for k, v in value.items():
                print(f"  {k}: {v}")
        elif isinstance(value, list):
            print(f"\n{key}:")
            for i, item in enumerate(value):
                print(f"  Item {i+1}:")
                if isinstance(item, dict):
                    for k, v in item.items():
                        print(f"    {k}: {v}")
                else:
                    print(f"    {item}")
        else:
            print(f"\n{key}: {value}")