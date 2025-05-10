import tkinter as tk
from tkinter import ttk, messagebox
import ctypes
import os
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import threading
import time

class ProcessInfo(ctypes.Structure):
    _fields_ = [
        ("pid", ctypes.c_ulong),
        ("name", ctypes.c_wchar * 260),
        ("cpuUsage", ctypes.c_double),
        ("memoryMB", ctypes.c_double)
    ]

class GpuInfo(ctypes.Structure):
    _fields_ = [
        ("name", ctypes.c_wchar * 256),
        ("usagePercent", ctypes.c_float),
        ("memoryUsedMB", ctypes.c_float),
        ("memoryTotalMB", ctypes.c_float)
    ]

class TaskManagerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Advanced Task Manager")
        self.root.geometry("1200x800")
        
        # Загрузка DLL
        self.load_dll()
        
        # Инициализация мониторинга
        self.monitor = PerformanceMonitor(self)
        
        # Создание интерфейса
        self.create_notebook()
        self.create_process_tab()
        self.create_performance_tab()
        
        # Запуск обновления данных
        self.update_process_list()
        self.update_metrics()

    def load_dll(self):
        try:
            dll_path = os.path.abspath("Dll3.dll")
            self.dll = ctypes.CDLL(dll_path)
            
            # Настройка функций
            self.dll.GetProcessesInfo.argtypes = [ctypes.POINTER(ctypes.POINTER(ProcessInfo))]
            self.dll.GetProcessesInfo.restype = ctypes.c_int
            self.dll.FreeProcessesInfo.argtypes = [ctypes.POINTER(ProcessInfo)]
            self.dll.GetTotalCPUUsage.restype = ctypes.c_float
            self.dll.GetTotalMemoryUsage.restype = ctypes.c_float
            self.dll.KillProcess.argtypes = [ctypes.c_ulong]
            self.dll.KillProcess.restype = ctypes.c_int
            self.dll.InitGpuMonitor.restype = None
            self.dll.GetGpuInfo.argtypes = [ctypes.POINTER(GpuInfo)]
            self.dll.GetGpuInfo.restype = ctypes.c_int
            self.dll.CleanupGpuMonitor.restype = None
            
            # Инициализация GPU монитора
            self.dll.InitGpuMonitor()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load DLL: {str(e)}")
            self.root.destroy()

    def create_notebook(self):
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True)
        
        self.process_tab = ttk.Frame(self.notebook)
        self.performance_tab = ttk.Frame(self.notebook)
        
        self.notebook.add(self.process_tab, text="Processes")
        self.notebook.add(self.performance_tab, text="Performance")

    def create_process_tab(self):
        # Метки для CPU и RAM
        metrics_frame = ttk.Frame(self.process_tab)
        metrics_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.cpu_label = ttk.Label(metrics_frame, text="CPU Usage: 0%", font=('Arial', 10, 'bold'))
        self.cpu_label.pack(side=tk.LEFT, padx=10)
        
        self.ram_label = ttk.Label(metrics_frame, text="RAM Usage: 0%", font=('Arial', 10, 'bold'))
        self.ram_label.pack(side=tk.LEFT, padx=10)
        
        self.gpu_label = ttk.Label(metrics_frame, text="GPU Usage: 0%", font=('Arial', 10, 'bold'))
        self.gpu_label.pack(side=tk.LEFT, padx=10)

        # Таблица процессов
        self.tree = ttk.Treeview(self.process_tab, columns=("PID", "Name", "Memory", "CPU"), show="headings")
        self.tree.heading("PID", text="PID", command=lambda: self.sort_column("PID", False))
        self.tree.heading("Name", text="Name", command=lambda: self.sort_column("Name", False))
        self.tree.heading("Memory", text="Memory (MB)", command=lambda: self.sort_column("Memory", False))
        self.tree.heading("CPU", text="CPU (%)", command=lambda: self.sort_column("CPU", False))
        
        self.tree.column("PID", width=80, anchor="center")
        self.tree.column("Name", width=300, anchor="w")
        self.tree.column("Memory", width=120, anchor="e")
        self.tree.column("CPU", width=100, anchor="e")
        
        scrollbar = ttk.Scrollbar(self.process_tab, orient="vertical", command=self.tree.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree.configure(yscrollcommand=scrollbar.set)
        self.tree.pack(expand=True, fill=tk.BOTH, padx=5, pady=5)

        # Контекстное меню
        self.context_menu = tk.Menu(self.root, tearoff=0)
        self.context_menu.add_command(label="Show Details", command=self.show_process_details)
        self.context_menu.add_command(label="End Process", command=self.kill_selected_process)
        self.tree.bind("<Button-3>", self.show_context_menu)

    def create_performance_tab(self):
        self.figure = Figure(figsize=(10, 8), dpi=100)
        
        # График CPU
        self.cpu_ax = self.figure.add_subplot(411)
        self.cpu_ax.set_title('CPU Usage (%)')
        self.cpu_ax.set_ylim(0, 100)
        self.cpu_ax.grid(True)
        self.cpu_line, = self.cpu_ax.plot([], [], 'r-')
        
        # График RAM
        self.ram_ax = self.figure.add_subplot(412)
        self.ram_ax.set_title('RAM Usage (%)')
        self.ram_ax.set_ylim(0, 100)
        self.ram_ax.grid(True)
        self.ram_line, = self.ram_ax.plot([], [], 'b-')
        
        # График GPU
        self.gpu_ax = self.figure.add_subplot(413)
        self.gpu_ax.set_title('GPU Usage (%)')
        self.gpu_ax.set_ylim(0, 100)
        self.gpu_ax.grid(True)
        self.gpu_line, = self.gpu_ax.plot([], [], 'g-')
        
        # График памяти GPU
        self.gpu_mem_ax = self.figure.add_subplot(414)
        self.gpu_mem_ax.set_title('GPU Memory Usage (%)')
        self.gpu_mem_ax.set_ylim(0, 100)
        self.gpu_mem_ax.grid(True)
        self.gpu_mem_line, = self.gpu_mem_ax.plot([], [], 'm-')
        
        self.figure.tight_layout(pad=3.0)
        
        self.canvas = FigureCanvasTkAgg(self.figure, self.performance_tab)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

    def update_metrics(self):
        try:
            # Обновление CPU и RAM
            cpu_usage = self.dll.GetTotalCPUUsage()
            ram_usage = self.dll.GetTotalMemoryUsage()
            
            self.cpu_label.config(text=f"CPU Usage: {cpu_usage:.1f}%")
            self.ram_label.config(text=f"RAM Usage: {ram_usage:.1f}%")
            
            # Обновление GPU
            gpu_info = GpuInfo()
            if self.dll.GetGpuInfo(ctypes.byref(gpu_info)) > 0:
                gpu_text = f"GPU: {gpu_info.name} | Usage: {gpu_info.usagePercent:.1f}% | "
                gpu_text += f"Memory: {gpu_info.memoryUsedMB:.1f}/{gpu_info.memoryTotalMB:.1f} MB"
                self.gpu_label.config(text=gpu_text)
            
            # Обновление графиков
            if hasattr(self, 'monitor'):
                self.cpu_line.set_data(range(len(self.monitor.cpu_history)), self.monitor.cpu_history)
                self.ram_line.set_data(range(len(self.monitor.ram_history)), self.monitor.ram_history)
                self.gpu_line.set_data(range(len(self.monitor.gpu_history)), self.monitor.gpu_history)
                self.gpu_mem_line.set_data(range(len(self.monitor.gpu_mem_history)), self.monitor.gpu_mem_history)
                
                for ax in [self.cpu_ax, self.ram_ax, self.gpu_ax, self.gpu_mem_ax]:
                    ax.relim()
                    ax.autoscale_view()
                
                self.canvas.draw()
                
        except Exception as e:
            print(f"Error updating metrics: {e}")
        
        self.root.after(1000, self.update_metrics)

    def update_process_list(self):
        try:
            proc_ptr = ctypes.POINTER(ProcessInfo)()
            count = self.dll.GetProcessesInfo(ctypes.byref(proc_ptr))

            if count > 0:
                # Очистка текущего списка
                for item in self.tree.get_children():
                    self.tree.delete(item)

                # Добавление новых процессов
                processes = []
                for i in range(count):
                    processes.append(proc_ptr[i])
                
                # Сортировка по использованию CPU
                processes.sort(key=lambda p: p.cpuUsage, reverse=True)
                
                for proc in processes:
                    self.tree.insert("", tk.END, values=(
                        proc.pid,
                        os.path.basename(proc.name),
                        f"{proc.memoryMB:.1f}",
                        f"{proc.cpuUsage:.1f}%"
                    ))

                self.dll.FreeProcessesInfo(proc_ptr)
                
        except Exception as e:
            print(f"Error updating process list: {e}")
        
        self.root.after(3000, self.update_process_list)

    def sort_column(self, col, reverse):
        items = [(self.tree.set(item, col), item) for item in self.tree.get_children('')]
        
        try:
            if col in ("PID", "Memory", "CPU"):
                items.sort(key=lambda x: float(x[0].rstrip('%')), reverse=reverse)
            else:
                items.sort(key=lambda x: x[0], reverse=reverse)
        except ValueError:
            items.sort(key=lambda x: x[0], reverse=reverse)
        
        for index, (val, item) in enumerate(items):
            self.tree.move(item, '', index)
        
        self.tree.heading(col, command=lambda: self.sort_column(col, not reverse))

    def show_context_menu(self, event):
        item = self.tree.identify_row(event.y)
        if item:
            self.tree.selection_set(item)
            self.context_menu.post(event.x_root, event.y_root)

    def show_process_details(self):
        selected_item = self.tree.selection()
        if selected_item:
            values = self.tree.item(selected_item, 'values')
            details = f"PID: {values[0]}\nName: {values[1]}\nMemory: {values[2]} MB\nCPU: {values[3]}"
            messagebox.showinfo("Process Details", details)

    def kill_selected_process(self):
        selected_item = self.tree.selection()
        if selected_item:
            pid = int(self.tree.item(selected_item, 'values')[0])
            try:
                result = self.dll.KillProcess(pid)
                if result == 0:
                    messagebox.showinfo("Success", f"Process {pid} terminated successfully")
                    self.update_process_list()
                else:
                    messagebox.showerror("Error", f"Failed to terminate process {pid}")
            except Exception as e:
                messagebox.showerror("Error", f"Error terminating process: {str(e)}")

    def on_close(self):
        if hasattr(self, 'monitor'):
            self.monitor.stop()
        if hasattr(self, 'dll'):
            self.dll.CleanupGpuMonitor()
        self.root.destroy()

class PerformanceMonitor:
    def __init__(self, app):
        self.app = app
        self.cpu_history = []
        self.ram_history = []
        self.gpu_history = []
        self.gpu_mem_history = []
        self.max_history = 60
        self.running = True
        
        self.thread = threading.Thread(target=self.update_performance_data)
        self.thread.daemon = True
        self.thread.start()

    def update_performance_data(self):
        while self.running:
            try:
                # CPU и RAM
                cpu_usage = self.app.dll.GetTotalCPUUsage()
                ram_usage = self.app.dll.GetTotalMemoryUsage()
                
                # GPU
                gpu_info = GpuInfo()
                if self.app.dll.GetGpuInfo(ctypes.byref(gpu_info)) > 0:
                    gpu_usage = gpu_info.usagePercent
                    gpu_mem_usage = (gpu_info.memoryUsedMB / gpu_info.memoryTotalMB) * 100
                else:
                    gpu_usage = 0
                    gpu_mem_usage = 0
                
                # Сохранение данных
                self.cpu_history.append(cpu_usage)
                self.ram_history.append(ram_usage)
                self.gpu_history.append(gpu_usage)
                self.gpu_mem_history.append(gpu_mem_usage)
                
                # Ограничение истории
                if len(self.cpu_history) > self.max_history:
                    self.cpu_history.pop(0)
                    self.ram_history.pop(0)
                    self.gpu_history.pop(0)
                    self.gpu_mem_history.pop(0)
                
            except Exception as e:
                print(f"Error updating performance data: {e}")
            
            time.sleep(1)

    def stop(self):
        self.running = False

if __name__ == "__main__":
    root = tk.Tk()
    app = TaskManagerApp(root)
    root.protocol("WM_DELETE_WINDOW", app.on_close)
    root.mainloop()