import psutil
import threading
import time

class TaskMngrInfo:
    def __init__(self, pid, name, memory, cpu):
        self.pid = pid
        self.name = name
        self.memory = memory
        self.cpu = cpu
    
    def __repr__(self):
        return f"ИД: {self.pid}, Имя: {self.name}, Память: {self.memory} MB, ЦП: {self.cpu}%"


def get_process_info():
    process_list = []
    for proc in psutil.process_iter(attrs=['pid', 'name', 'memory_info', 'cpu_percent']):
        try:
            info = proc.info
            process = TaskMngrInfo(
                pid=info['pid'],
                name=info['name'],
                memory=info['memory_info'].rss / (1024 * 1024),
                cpu=info['cpu_percent']
            )
            process_list.append(process)
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue
    return process_list


def monitoring_system():
    while True:
        process_list = get_process_info()
        print("\nActive Processes:")
        for process in process_list:
            print(process)
        time.sleep(5)


def start_monitoring():
    monitor_thread = threading.Thread(target=monitoring_system, daemon=True)
    monitor_thread.start()


if __name__ == "__main__":
    start_monitoring()
    input("Monitoring started. Press Enter to stop...\n")
