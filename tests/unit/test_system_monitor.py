"""Tests for system monitoring utilities."""

import pytest
from unittest.mock import patch, MagicMock
from src.utils.system_monitor import SystemMonitor, get_system_stats, get_memory_usage


class TestSystemMonitor:
    """Test system monitoring functionality."""
    
    def test_system_monitor_init(self):
        """Test SystemMonitor initialization."""
        monitor = SystemMonitor()
        assert hasattr(monitor, 'psutil_available')
        assert isinstance(monitor.psutil_available, bool)
    
    def test_get_system_stats_without_psutil(self):
        """Test system stats when psutil is not available."""
        with patch('src.utils.system_monitor.PSUTIL_AVAILABLE', False):
            monitor = SystemMonitor()
            stats = monitor.get_system_stats()
            
            assert 'timestamp' in stats
            assert 'psutil_available' in stats
            assert stats['psutil_available'] is False
            assert 'error' in stats
    
    @patch('src.utils.system_monitor.psutil')
    def test_get_system_stats_with_psutil(self, mock_psutil):
        """Test system stats when psutil is available."""
        # Mock psutil functions
        mock_psutil.cpu_percent.return_value = 25.5
        mock_psutil.cpu_count.return_value = 8
        
        mock_memory = MagicMock()
        mock_memory.total = 16 * 1024**3  # 16GB
        mock_memory.available = 8 * 1024**3  # 8GB
        mock_memory.percent = 50.0
        mock_memory.used = 8 * 1024**3
        mock_memory.free = 8 * 1024**3
        mock_psutil.virtual_memory.return_value = mock_memory
        
        mock_disk = MagicMock()
        mock_disk.total = 1024**3  # 1GB
        mock_disk.used = 512**3   # 512MB
        mock_disk.free = 512**3   # 512MB
        mock_psutil.disk_usage.return_value = mock_disk
        
        mock_process = MagicMock()
        mock_process.pid = 12345
        mock_process.memory_info.return_value._asdict.return_value = {'rss': 1024**2, 'vms': 2*1024**2}
        mock_process.cpu_percent.return_value = 5.0
        mock_process.num_threads.return_value = 4
        mock_process.create_time.return_value = 1234567890
        mock_psutil.Process.return_value = mock_process
        
        with patch('src.utils.system_monitor.PSUTIL_AVAILABLE', True):
            monitor = SystemMonitor()
            stats = monitor.get_system_stats()
            
            assert 'timestamp' in stats
            assert 'cpu' in stats
            assert 'memory' in stats
            assert 'disk' in stats
            assert 'process' in stats
            assert stats['cpu']['percent'] == 25.5
            assert stats['memory']['percent'] == 50.0
    
    def test_get_memory_usage_without_psutil(self):
        """Test memory usage when psutil is not available."""
        with patch('src.utils.system_monitor.PSUTIL_AVAILABLE', False):
            monitor = SystemMonitor()
            usage = monitor.get_memory_usage()
            
            assert 'error' in usage
            assert usage['error'] == 'psutil not available'
    
    @patch('src.utils.system_monitor.psutil')
    def test_get_memory_usage_with_psutil(self, mock_psutil):
        """Test memory usage when psutil is available."""
        mock_memory = MagicMock()
        mock_memory.total = 16 * 1024**3  # 16GB
        mock_memory.available = 8 * 1024**3  # 8GB
        mock_memory.percent = 50.0
        mock_psutil.virtual_memory.return_value = mock_memory
        
        mock_process = MagicMock()
        mock_memory_info = MagicMock()
        mock_memory_info.rss = 100 * 1024**2  # 100MB
        mock_memory_info.vms = 200 * 1024**2  # 200MB
        mock_process.memory_info.return_value = mock_memory_info
        mock_process.memory_percent.return_value = 1.5
        mock_psutil.Process.return_value = mock_process
        
        with patch('src.utils.system_monitor.PSUTIL_AVAILABLE', True):
            monitor = SystemMonitor()
            usage = monitor.get_memory_usage()
            
            assert 'system_memory' in usage
            assert 'process_memory' in usage
            assert usage['system_memory']['total_gb'] == 16.0
            assert usage['process_memory']['rss_mb'] == 100.0
    
    def test_check_resource_limits_without_psutil(self):
        """Test resource limits check when psutil is not available."""
        with patch('src.utils.system_monitor.PSUTIL_AVAILABLE', False):
            monitor = SystemMonitor()
            result = monitor.check_resource_limits()
            
            assert 'error' in result
            assert result['error'] == 'psutil not available'
    
    @patch('src.utils.system_monitor.psutil')
    def test_check_resource_limits_within_limits(self, mock_psutil):
        """Test resource limits check when within limits."""
        mock_memory = MagicMock()
        mock_memory.percent = 50.0  # Below 80% limit
        mock_psutil.virtual_memory.return_value = mock_memory
        mock_psutil.cpu_percent.return_value = 30.0  # Below 80% limit
        
        with patch('src.utils.system_monitor.PSUTIL_AVAILABLE', True):
            monitor = SystemMonitor()
            result = monitor.check_resource_limits()
            
            assert result['within_limits'] is True
            assert len(result['warnings']) == 0
            assert result['current_memory_percent'] == 50.0
            assert result['current_cpu_percent'] == 30.0
    
    @patch('src.utils.system_monitor.psutil')
    def test_check_resource_limits_exceeding_limits(self, mock_psutil):
        """Test resource limits check when exceeding limits."""
        mock_memory = MagicMock()
        mock_memory.percent = 90.0  # Above 80% limit
        mock_psutil.virtual_memory.return_value = mock_memory
        mock_psutil.cpu_percent.return_value = 85.0  # Above 80% limit
        
        with patch('src.utils.system_monitor.PSUTIL_AVAILABLE', True):
            monitor = SystemMonitor()
            result = monitor.check_resource_limits()
            
            assert result['within_limits'] is False
            assert len(result['warnings']) == 2
            assert 'Memory usage' in result['warnings'][0]
            assert 'CPU usage' in result['warnings'][1]
    
    def test_global_functions(self):
        """Test global convenience functions."""
        # These should not raise exceptions
        stats = get_system_stats()
        assert isinstance(stats, dict)
        assert 'timestamp' in stats
        
        memory = get_memory_usage()
        assert isinstance(memory, dict)


if __name__ == "__main__":
    pytest.main([__file__])