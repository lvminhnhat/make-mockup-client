# utils/enhanced_logger_manager.py - Phiên bản cải thiện
import logging
import os
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import json
from io import StringIO
import threading
import time
from logging.handlers import TimedRotatingFileHandler
import gzip
import shutil
import signal
import atexit
import photoshop

class TaskLogHandler(logging.Handler):
    """Custom log handler để thu thập logs cho từng task"""
    
    def __init__(self, task_id: str):
        super().__init__()
        self.task_id = task_id
        self.log_buffer = StringIO()
        self.task_logs = []
        self.lock = threading.RLock()  # Sử dụng RLock thay vì Lock
        self.closed = False
        
    def emit(self, record):
        if self.closed:
            return
            
        try:
            with self.lock:
                if self.closed:  # Double check
                    return
                    
                log_entry = self.format(record)
                self.log_buffer.write(log_entry + '\n')
                
                # Lưu log với metadata
                self.task_logs.append({
                    'timestamp': datetime.fromtimestamp(record.created).isoformat(),
                    'level': record.levelname,
                    'message': record.getMessage(),
                    'module': getattr(record, 'module', 'unknown'),
                    'funcName': getattr(record, 'funcName', 'unknown'),
                    'lineno': getattr(record, 'lineno', 0),
                    'task_id': self.task_id
                })
        except Exception as e:
            # Tránh infinite loop nếu logging bị lỗi
            print(f"Error in TaskLogHandler.emit: {e}")
    
    def get_logs(self) -> List[Dict[str, Any]]:
        """Lấy tất cả logs của task hiện tại"""
        if self.closed:
            return []
        try:
            with self.lock:
                return self.task_logs.copy()
        except:
            return []
    
    def get_logs_as_string(self) -> str:
        """Lấy logs dưới dạng string"""
        if self.closed:
            return ""
        try:
            with self.lock:
                return self.log_buffer.getvalue()
        except:
            return ""
    
    def get_summary_message(self) -> str:
        """Tạo summary message để gửi lên server"""
        if self.closed or not self.task_logs:
            return f"Task {self.task_id} completed"
            
        try:
            with self.lock:
                if not self.task_logs:
                    return f"Task {self.task_id} completed"
                
                summary_parts = []
                error_count = sum(1 for log in self.task_logs if log['level'] == 'ERROR')
                warning_count = sum(1 for log in self.task_logs if log['level'] == 'WARNING')
                info_count = sum(1 for log in self.task_logs if log['level'] == 'INFO')
                
                # Thêm thống kê
                summary_parts.append(f"📊 Logs: {len(self.task_logs)} entries")
                if error_count > 0:
                    summary_parts.append(f"❌ Errors: {error_count}")
                if warning_count > 0:
                    summary_parts.append(f"⚠️ Warnings: {warning_count}")
                if info_count > 0:
                    summary_parts.append(f"ℹ️ Info: {info_count}")
                
                # Thêm log cuối cùng
                last_log = self.task_logs[-1]
                last_message = last_log['message'][:100]
                if len(last_log['message']) > 100:
                    last_message += "..."
                summary_parts.append(f"📝 Last: {last_message}")
                
                return " | ".join(summary_parts)
        except Exception as e:
            return f"Task {self.task_id} completed with logging error: {str(e)}"
    
    def clear_logs(self):
        """Xóa logs hiện tại"""
        if self.closed:
            return
        try:
            with self.lock:
                self.log_buffer.truncate(0)
                self.log_buffer.seek(0)
                self.task_logs.clear()
        except:
            pass
    
    def close(self):
        """Đóng handler"""
        try:
            with self.lock:
                self.closed = True
                if hasattr(self.log_buffer, 'close'):
                    self.log_buffer.close()
        except:
            pass
        super().close()

class SafeTimedRotatingFileHandler(TimedRotatingFileHandler):
    """Safe rotating handler với error handling tốt hơn"""
    
    def __init__(self, filename, when='midnight', interval=1, backupCount=30, 
                 encoding=None, delay=False, utc=False, atTime=None):
        # Tạo thư mục nếu chưa tồn tại
        log_dir = os.path.dirname(filename)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir, exist_ok=True)
            
        super().__init__(filename, when, interval, backupCount, encoding, delay, utc, atTime)
        self.suffix = "%Y-%m-%d"
        
    def doRollover(self):
        """Override với error handling tốt hơn"""
        try:
            # Đóng file hiện tại trước khi rotate
            if self.stream:
                self.stream.close()
                self.stream = None
                 
            # Gọi rollover gốc
            super().doRollover()
            
            # Compress và cleanup trong thread riêng để tránh block
            threading.Thread(target=self._safe_maintenance, daemon=True).start()
            
        except Exception as e:
            # Log error nhưng không làm crash ứng dụng
            print(f"Error in log rotation: {e}")
            # Cố gắng mở lại stream
            try:
                if not self.stream:
                    self.stream = self._open()
            except:
                pass
    
    def _safe_maintenance(self):
        """Thực hiện compress và cleanup an toàn"""
        try:
            self._compress_old_logs()
            self._cleanup_old_files()
        except Exception as e:
            print(f"Error in log maintenance: {e}")
    
    def _compress_old_logs(self):
        """Nén các file log cũ"""
        try:
            log_dir = os.path.dirname(self.baseFilename)
            base_name = os.path.basename(self.baseFilename)
            
            if not os.path.exists(log_dir):
                return
                
            for file in os.listdir(log_dir):
                if (file.startswith(base_name) and 
                    not file.endswith('.gz') and 
                    file != base_name and
                    '.' in file):  # Có extension date
                    
                    file_path = os.path.join(log_dir, file)
                    
                    # Kiểm tra file có tồn tại và cũ hơn 1 ngày
                    if (os.path.exists(file_path) and 
                        os.path.getmtime(file_path) < time.time() - 86400):
                        
                        try:
                            with open(file_path, 'rb') as f_in:
                                with gzip.open(f"{file_path}.gz", 'wb') as f_out:
                                    shutil.copyfileobj(f_in, f_out)
                            os.remove(file_path)
                        except Exception as e:
                            print(f"Error compressing {file_path}: {e}")
                            
        except Exception as e:
            print(f"Error in compress_old_logs: {e}")
    
    def _cleanup_old_files(self):
        """Dọn dẹp file quá cũ (>60 ngày)"""
        try:
            log_dir = os.path.dirname(self.baseFilename)
            base_name = os.path.basename(self.baseFilename)
            cutoff_time = time.time() - (60 * 86400)  # 60 ngày
            
            if not os.path.exists(log_dir):
                return
                
            for file in os.listdir(log_dir):
                if file.startswith(base_name) and file.endswith('.gz'):
                    file_path = os.path.join(log_dir, file)
                    try:
                        if (os.path.exists(file_path) and 
                            os.path.getmtime(file_path) < cutoff_time):
                            os.remove(file_path)
                    except Exception as e:
                        print(f"Error removing old file {file_path}: {e}")
                        
        except Exception as e:
            print(f"Error in cleanup_old_files: {e}")

class EnhancedLoggerManager:
    """Quản lý logging nâng cao với rotation theo ngày"""
    
    def __init__(self, log_dir: str = "logs"):
        self.log_dir = log_dir
        self.task_handlers = {}
        self.task_loggers = {}
        self.lock = threading.RLock()
        self.shutdown_event = threading.Event()
        self._setup_directories()
        self._setup_main_logger()
        
        # Start cleanup thread
        self._start_cleanup_thread()
        
        # Register cleanup on exit
        atexit.register(self.shutdown)
        signal.signal(signal.SIGTERM, self._signal_handler)
        signal.signal(signal.SIGINT, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        print(f"Received signal {signum}, shutting down logger manager...")
        self.shutdown()
    
    def shutdown(self):
        """Graceful shutdown"""
        print("Shutting down logger manager...")
        self.shutdown_event.set()
        
        # Cleanup all task loggers
        with self.lock:
            for task_id in list(self.task_handlers.keys()):
                try:
                    self.cleanup_task_logger(task_id)
                except:
                    pass
    
    def _setup_directories(self):
        """Tạo thư mục logs với cấu trúc rõ ràng"""
        directories = [
            self.log_dir,
            os.path.join(self.log_dir, "main"),
            os.path.join(self.log_dir, "tasks"),
            os.path.join(self.log_dir, "errors"),
            os.path.join(self.log_dir, "archived")
        ]
        
        for dir_path in directories:
            try:
                os.makedirs(dir_path, exist_ok=True)
            except Exception as e:
                print(f"Error creating directory {dir_path}: {e}")
    
    def _setup_main_logger(self):
        """Setup logger chính với daily rotation"""
        try:
            # Main log handler với rotation hàng ngày
            main_handler = SafeTimedRotatingFileHandler(
                filename=os.path.join(self.log_dir, "main", "application.log"),
                when='midnight',
                interval=1,
                backupCount=30,
                encoding='utf-8'
            )
            main_handler.setLevel(logging.INFO)
            
            # Error log handler riêng
            error_handler = SafeTimedRotatingFileHandler(
                filename=os.path.join(self.log_dir, "errors", "error.log"),
                when='midnight',
                interval=1,
                backupCount=60,  # Giữ error logs lâu hơn
                encoding='utf-8'
            )
            error_handler.setLevel(logging.ERROR)
            
            # Console handler
            console_handler = logging.StreamHandler()
            console_handler.setLevel(logging.INFO)
            
            # Formatters
            detailed_formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(funcName)s() - %(message)s'
            )
            
            console_formatter = logging.Formatter(
                '%(asctime)s - %(levelname)s - %(message)s'
            )
            
            main_handler.setFormatter(detailed_formatter)
            error_handler.setFormatter(detailed_formatter)
            console_handler.setFormatter(console_formatter)
            
            # Setup root logger
            root_logger = logging.getLogger()
            root_logger.setLevel(logging.INFO)
            
            # Clear existing handlers
            for handler in root_logger.handlers[:]:
                root_logger.removeHandler(handler)
            
            root_logger.addHandler(main_handler)
            root_logger.addHandler(error_handler)
            root_logger.addHandler(console_handler)
            
            # Prevent propagation to avoid duplication
            root_logger.propagate = False
            
        except Exception as e:
            print(f"Error setting up main logger: {e}")
    
    def create_task_logger(self, task_id: str) -> logging.Logger:
        """Tạo logger riêng cho từng task với daily rotation"""
        with self.lock:
            logger_name = f"task_{task_id}"
            
            # Nếu logger đã tồn tại, trả về luôn
            if task_id in self.task_loggers:
                return self.task_loggers[task_id]
            
            try:
                task_logger = logging.getLogger(logger_name)
                task_logger.setLevel(logging.INFO)
                task_logger.propagate = False  # Không propagate lên root logger
                
                # Tạo custom handler cho task
                task_handler = TaskLogHandler(task_id)
                task_formatter = logging.Formatter(
                    '%(asctime)s - %(levelname)s - %(message)s'
                )
                task_handler.setFormatter(task_formatter)
                
                # File handler cho task với daily rotation
                today = datetime.now().strftime("%Y-%m-%d")
                task_file_handler = SafeTimedRotatingFileHandler(
                    filename=os.path.join(self.log_dir, "tasks", f"task_{task_id}_{today}.log"),
                    when='midnight',
                    interval=1,
                    backupCount=7,  # Giữ task logs 7 ngày
                    encoding='utf-8'
                )
                task_file_handler.setFormatter(task_formatter)
                
                task_logger.addHandler(task_handler)
                task_logger.addHandler(task_file_handler)
                
                # Lưu references
                self.task_handlers[task_id] = task_handler
                self.task_loggers[task_id] = task_logger
                
                return task_logger
                
            except Exception as e:
                print(f"Error creating task logger for {task_id}: {e}")
                # Fallback to root logger
                return logging.getLogger()
    
    def get_task_logs(self, task_id: str) -> List[Dict[str, Any]]:
        """Lấy logs của task"""
        if task_id in self.task_handlers:
            return self.task_handlers[task_id].get_logs()
        return []
    
    def get_task_logs_string(self, task_id: str) -> str:
        """Lấy logs của task dưới dạng string"""
        if task_id in self.task_handlers:
            return self.task_handlers[task_id].get_logs_as_string()
        return ""
    
    def get_task_summary_message(self, task_id: str) -> str:
        """Lấy summary message để gửi lên server"""
        if task_id in self.task_handlers:
            return self.task_handlers[task_id].get_summary_message()
        return f"Task {task_id} completed"
    
    def clear_task_logs(self, task_id: str):
        """Xóa logs của task"""
        if task_id in self.task_handlers:
            self.task_handlers[task_id].clear_logs()
    
    def cleanup_task_logger(self, task_id: str):
        """Dọn dẹp logger của task sau khi hoàn thành"""
        with self.lock:
            try:
                logger_name = f"task_{task_id}"
                
                if task_id in self.task_loggers:
                    task_logger = self.task_loggers[task_id]
                    
                    # Xóa tất cả handlers
                    for handler in task_logger.handlers[:]:
                        handler.close()
                        task_logger.removeHandler(handler)
                    
                    # Xóa từ dictionaries
                    del self.task_loggers[task_id]
                
                if task_id in self.task_handlers:
                    self.task_handlers[task_id].close()
                    del self.task_handlers[task_id]
                    
            except Exception as e:
                print(f"Error cleaning up task logger {task_id}: {e}")
    
    def _start_cleanup_thread(self):
        """Khởi động thread dọn dẹp tự động"""
        def cleanup_worker():
            while not self.shutdown_event.is_set():
                try:
                    # Dọn dẹp mỗi giờ
                    if self.shutdown_event.wait(3600):  # 1 hour or shutdown
                        break
                    self._periodic_cleanup()
                except Exception as e:
                    print(f"Error in cleanup thread: {e}")
        
        cleanup_thread = threading.Thread(target=cleanup_worker, daemon=True)
        cleanup_thread.start()
    
    def _periodic_cleanup(self):
        """Dọn dẹp định kỳ"""
        try:
            # Dọn dẹp task loggers không sử dụng
            with self.lock:
                # Xóa các task logger quá cũ (>1 giờ không hoạt động)
                current_time = time.time()
                to_remove = []
                
                for task_id, handler in self.task_handlers.items():
                    try:
                        # Kiểm tra thời gian log cuối cùng
                        logs = handler.get_logs()
                        if logs:
                            last_log_time = datetime.fromisoformat(logs[-1]['timestamp']).timestamp()
                            if current_time - last_log_time > 3600:  # 1 giờ
                                to_remove.append(task_id)
                        else:
                            # Không có logs, có thể là task cũ
                            to_remove.append(task_id)
                    except Exception as e:
                        print(f"Error checking task {task_id} for cleanup: {e}")
                        to_remove.append(task_id)
                
                for task_id in to_remove:
                    self.cleanup_task_logger(task_id)
                    
        except Exception as e:
            print(f"Error in periodic cleanup: {e}")
    
    def get_log_statistics(self) -> Dict[str, Any]:
        """Lấy thống kê logging"""
        stats = {
            'active_tasks': len(self.task_handlers),
            'log_directories': [],
            'disk_usage': {}
        }
        
        try:
            # Thống kê thư mục
            for root, dirs, files in os.walk(self.log_dir):
                for dir_name in dirs:
                    dir_path = os.path.join(root, dir_name)
                    try:
                        if os.path.exists(dir_path):
                            file_count = len([f for f in os.listdir(dir_path) 
                                            if os.path.isfile(os.path.join(dir_path, f))])
                            total_size = sum(os.path.getsize(os.path.join(dir_path, f)) 
                                           for f in os.listdir(dir_path) 
                                           if os.path.isfile(os.path.join(dir_path, f)))
                            
                            stats['log_directories'].append({
                                'name': dir_name,
                                'path': dir_path,
                                'file_count': file_count,
                                'total_size_mb': round(total_size / (1024 * 1024), 2)
                            })
                    except Exception as e:
                        print(f"Error getting stats for {dir_path}: {e}")
        except Exception as e:
            print(f"Error getting log statistics: {e}")
        
        return stats

# Singleton instance
enhanced_logger_manager = EnhancedLoggerManager()

def get_task_logger(task_id: str) -> logging.Logger:
    """Helper function để lấy task logger"""
    return enhanced_logger_manager.create_task_logger(task_id)