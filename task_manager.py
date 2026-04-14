import threading
import queue
import time
from pathlib import Path
from doc_converter import process_file_logic, handle_failure, handle_success, get_timeout_for_file

class TaskStatus:
    PENDING = "Pending"
    RUNNING = "Running"
    SUCCESS = "Success"
    FAILED = "Failed"
    STOPPED = "Stopped"
    TIMEOUT = "Timeout"

class ConversionTask:
    def __init__(self, file_path, api_key, import_root=None):
        self.file_path = Path(file_path)
        self.api_key = api_key
        self.import_root = Path(import_root) if import_root else self.file_path.parent
        self.status = TaskStatus.PENDING
        self.stop_event = threading.Event()
        self.error_message = ""
        self.result_path = ""
        self.timeout = get_timeout_for_file(self.file_path)
        self.id = str(hash(str(self.file_path.absolute()) + str(time.time())))

    def stop(self):
        if self.status in [TaskStatus.PENDING, TaskStatus.RUNNING]:
            self.stop_event.set()
            if self.status == TaskStatus.PENDING:
                self.status = TaskStatus.STOPPED

class TaskManager:
    def __init__(self, max_workers=3, update_callback=None):
        self.tasks = []
        self.queue = queue.Queue()
        self.max_workers = max_workers
        self.update_callback = update_callback  # Called when any task status changes
        self.active_count = 0
        self.lock = threading.Lock()
        self.stop_all_requested = False
        
        # Statistics for progress bars
        self.total_files = 0
        self.processed_files = 0
        self.success_files = 0
        self.failed_files = 0

    def add_task(self, file_path, api_key, import_root=None):
        # Avoid duplicates in pending/running
        for task in self.tasks:
            if task.file_path == Path(file_path) and task.status in [TaskStatus.PENDING, TaskStatus.RUNNING]:
                return None
        
        task = ConversionTask(file_path, api_key, import_root=import_root)
        with self.lock:
            self.tasks.append(task)
            self.total_files += 1
            
        self.queue.put(task)
        self._trigger_workers()
        if self.update_callback:
            self.update_callback()
        return task

    def _trigger_workers(self):
        with self.lock:
            while self.active_count < self.max_workers and not self.queue.empty():
                task = self.queue.get()
                if task.stop_event.is_set():
                    task.status = TaskStatus.STOPPED
                    continue
                
                self.active_count += 1
                threading.Thread(target=self._worker, args=(task,), daemon=True).start()

    def _worker(self, task):
        task.status = TaskStatus.RUNNING
        if self.update_callback:
            self.update_callback()

        success = False
        result = ""
        
        # We run the process in a way we can track timeout
        # Since process_file_logic is blocking, we check stop_event inside it.
        # For a true "timeout" that kills the logic, we would need a subprocess,
        # but here we use the stop_event and library timeouts.
        
        try:
            # We wrap the blocking call to monitor timeout from outside if needed,
            # but for now we rely on the logic inside to check stop_event.
            success, result = process_file_logic(task.file_path, task.api_key, task.stop_event)
            
            if task.stop_event.is_set():
                task.status = TaskStatus.STOPPED
            elif success:
                task.status = TaskStatus.SUCCESS
                task.result_path = result
                handle_success(task.file_path, base_dir=task.import_root)
                with self.lock:
                    self.success_files += 1
                    self.processed_files += 1
            else:
                task.status = TaskStatus.FAILED
                task.error_message = result
                handle_failure(task.file_path, base_dir=task.import_root)
                with self.lock:
                    self.failed_files += 1
                    self.processed_files += 1
        except Exception as e:
            task.status = TaskStatus.FAILED
            task.error_message = str(e)
            handle_failure(task.file_path, base_dir=task.import_root)
            with self.lock:
                self.failed_files += 1
                self.processed_files += 1
        finally:
            with self.lock:
                self.active_count -= 1
            
            # Auto-remove success if desired (GUI will handle filtering)
            self._trigger_workers()
            if self.update_callback:
                self.update_callback()

    def retry_task(self, task_id):
        for task in self.tasks:
            if task.id == task_id:
                if task.status in [TaskStatus.FAILED, TaskStatus.STOPPED, TaskStatus.TIMEOUT]:
                    with self.lock:
                        if task.status == TaskStatus.FAILED:
                            self.failed_files -= 1
                            self.processed_files -= 1
                    task.status = TaskStatus.PENDING
                    task.stop_event.clear()
                    self.queue.put(task)
                    self._trigger_workers()
                    if self.update_callback:
                        self.update_callback()
                break

    def retry_all_failed(self):
        for task in self.tasks:
            if task.status in [TaskStatus.FAILED, TaskStatus.STOPPED, TaskStatus.TIMEOUT]:
                with self.lock:
                    if task.status == TaskStatus.FAILED:
                        self.failed_files -= 1
                        self.processed_files -= 1
                task.status = TaskStatus.PENDING
                task.stop_event.clear()
                self.queue.put(task)
        self._trigger_workers()
        if self.update_callback:
            self.update_callback()

    def stop_task(self, task_id):
        for task in self.tasks:
            if task.id == task_id:
                task.stop()
                if self.update_callback:
                    self.update_callback()
                break

    def stop_all(self):
        self.stop_all_requested = True
        # Clear the queue first
        with self.queue.mutex:
            self.queue.queue.clear()
        
        for task in self.tasks:
            task.stop()
        
        if self.update_callback:
            self.update_callback()

    def clear_successful(self):
        self.tasks = [t for t in self.tasks if t.status != TaskStatus.SUCCESS]
        if self.update_callback:
            self.update_callback()
