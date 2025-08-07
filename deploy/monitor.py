#!/usr/bin/env python3
"""
Monitoring script for trading bot health
Sends alerts if bot crashes or loses connection
"""

import os
import sys
import time
import psutil
import requests
from datetime import datetime, timedelta
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from src.core import get_alpaca_client, Config
from src.utils import AlertSystem


class BotMonitor:
    def __init__(self):
        self.alert_system = AlertSystem()
        self.last_heartbeat = datetime.now()
        self.error_count = 0
        self.max_errors = 5
        
    def check_process(self):
        """Check if trading bot process is running"""
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                cmdline = proc.info.get('cmdline', [])
                if cmdline and 'main.py' in ' '.join(cmdline) and 'paper' in ' '.join(cmdline):
                    return True, proc.info['pid']
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        return False, None
    
    def check_alpaca_connection(self):
        """Check if Alpaca API is accessible"""
        try:
            api = get_alpaca_client()
            account = api.get_account()
            return True, float(account.portfolio_value)
        except Exception as e:
            return False, str(e)
    
    def check_recent_logs(self):
        """Check if bot is actively logging"""
        log_dir = Path('/opt/trading-bot/logs')
        if not log_dir.exists():
            return False, "Log directory not found"
        
        # Find most recent log file
        log_files = list(log_dir.glob('trading_*.log'))
        if not log_files:
            return False, "No log files found"
        
        latest_log = max(log_files, key=lambda f: f.stat().st_mtime)
        
        # Check if log was updated in last 5 minutes
        last_modified = datetime.fromtimestamp(latest_log.stat().st_mtime)
        if datetime.now() - last_modified > timedelta(minutes=5):
            return False, f"Log not updated since {last_modified}"
        
        return True, "Logging active"
    
    def check_disk_space(self):
        """Check if enough disk space available"""
        disk = psutil.disk_usage('/')
        free_gb = disk.free / (1024**3)
        
        if free_gb < 1:  # Less than 1GB free
            return False, f"Low disk space: {free_gb:.2f}GB"
        return True, f"{free_gb:.2f}GB free"
    
    def check_memory(self):
        """Check memory usage"""
        memory = psutil.virtual_memory()
        
        if memory.percent > 90:
            return False, f"High memory usage: {memory.percent}%"
        return True, f"Memory usage: {memory.percent}%"
    
    def run_health_check(self):
        """Run all health checks"""
        results = {}
        all_healthy = True
        
        # Check process
        is_running, pid = self.check_process()
        results['process'] = {'healthy': is_running, 'detail': f"PID: {pid}" if pid else "Not running"}
        all_healthy = all_healthy and is_running
        
        # Check Alpaca connection
        connected, detail = self.check_alpaca_connection()
        results['alpaca'] = {'healthy': connected, 'detail': f"Portfolio: ${detail}" if connected else detail}
        
        # Check logs
        logging, detail = self.check_recent_logs()
        results['logging'] = {'healthy': logging, 'detail': detail}
        
        # Check resources
        disk_ok, detail = self.check_disk_space()
        results['disk'] = {'healthy': disk_ok, 'detail': detail}
        
        mem_ok, detail = self.check_memory()
        results['memory'] = {'healthy': mem_ok, 'detail': detail}
        
        return all_healthy, results
    
    def send_status_alert(self, healthy, results):
        """Send alert if issues detected"""
        if healthy:
            # Only send success every 6 hours
            if datetime.now().hour % 6 == 0 and datetime.now().minute < 5:
                self.alert_system.send_system_status(
                    "healthy",
                    f"Bot running smoothly. Portfolio: {results['alpaca']['detail']}"
                )
        else:
            # Send alert for any issues
            issues = []
            for check, result in results.items():
                if not result['healthy']:
                    issues.append(f"{check}: {result['detail']}")
            
            self.alert_system.send_error_alert(
                f"Bot health check failed:\n" + "\n".join(issues)
            )
            
            self.error_count += 1
            
            # Restart bot if too many errors
            if self.error_count >= self.max_errors:
                os.system('sudo systemctl restart trading-bot')
                self.alert_system.send_system_status("restarted", "Bot restarted due to errors")
                self.error_count = 0
    
    def monitor_loop(self):
        """Main monitoring loop"""
        print("Starting bot monitor...")
        
        while True:
            try:
                healthy, results = self.run_health_check()
                
                # Print status
                print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Health Check")
                for check, result in results.items():
                    status = "✅" if result['healthy'] else "❌"
                    print(f"  {status} {check}: {result['detail']}")
                
                # Send alerts if needed
                self.send_status_alert(healthy, results)
                
                # Reset error count if healthy
                if healthy:
                    self.error_count = 0
                
                # Wait 60 seconds before next check
                time.sleep(60)
                
            except KeyboardInterrupt:
                print("\nMonitor stopped by user")
                break
            except Exception as e:
                print(f"Monitor error: {e}")
                time.sleep(60)


if __name__ == "__main__":
    monitor = BotMonitor()
    monitor.monitor_loop()