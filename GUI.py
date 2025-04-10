import tkinter as tk
from tkinter import ttk, messagebox
import psutil
import pynvml
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.pyplot as plt
from main import get_process_info
import signal
import os

class TaskManagerGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Task Manager")
        self.root.geometry("1000x600")
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

        # Настройки интервалов обновления
        self.auto_refresh_interval = 3000  # 3 секунды для списка процессов
        self.performance_update_interval = 1000  # 1 секунда для графиков
        
        # Флаги управления
        self.auto_refresh_active = True
        self.performance_update_active = True
        self.gpu_update_active = True

        # Текущий активный график
        self.current_graph = "CPU"

        # Хранилище идентификаторов after
        self.after_ids = []

        # Настройки сортировки
        self.current_sort_column = "CPU"
        self.current_sort_reverse = False

        # Оптимизация: кэш для данных графиков
        self.max_data_points = 60  # 60 точек = 1 минута данных при обновлении раз в секунду
        self.cpu_data = []
        self.memory_data = []
        self.gpu_data = []

        # Инициализация NVML для GPU (один раз при запуске)
        try:
            pynvml.nvmlInit()
            self.gpu_handle = pynvml.nvmlDeviceGetHandleByIndex(0)
        except Exception as e:
            print(f"GPU initialization error: {e}")
            self.gpu_handle = None

        # Создание интерфейса
        self.create_widgets()

        # Инициализация данных
        self.refresh_process_list()
        self.setup_auto_refresh()
        self.setup_performance_charts()
        self.update_performance_charts()

    def create_widgets(self):
        """Создание всех элементов интерфейса"""
        self.style = ttk.Style()
        self.style.theme_use('clam')
        self.style.configure('green.Horizontal.TProgressbar', background='green')
        self.style.configure('yellow.Horizontal.TProgressbar', background='yellow')
        self.style.configure('red.Horizontal.TProgressbar', background='red')

        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(expand=True, fill=tk.BOTH)

        # Вкладка Details
        self.create_details_tab()
        
        # Вкладка Performance
        self.create_performance_tab()

    def create_details_tab(self):
        """Создание вкладки с деталями процессов"""
        self.details_frame = tk.Frame(self.notebook)
        self.notebook.add(self.details_frame, text="Details")

        self.content_frame = tk.Frame(self.details_frame)
        self.content_frame.pack(side=tk.RIGHT, expand=True, fill=tk.BOTH)

        # Treeview с сортировкой
        self.tree = ttk.Treeview(self.content_frame, columns=("PID", "Name", "Memory", "CPU"), show='headings')
        
        # Настройка колонок
        self.tree.heading("PID", text="PID", command=lambda: self.sort_column("PID", False))
        self.tree.heading("Name", text="Name", command=lambda: self.sort_column("Name", False))
        self.tree.heading("Memory", text="Memory (MB)", command=lambda: self.sort_column("Memory", False))
        self.tree.heading("CPU", text="CPU %", command=lambda: self.sort_column("CPU", False))
        
        self.tree.column("PID", width=80, anchor='center')
        self.tree.column("Name", width=150, anchor='w')
        self.tree.column("Memory", width=100, anchor='e')
        self.tree.column("CPU", width=80, anchor='e')
        
        self.tree.pack(expand=True, fill=tk.BOTH)

        # Контекстное меню
        self.context_menu = tk.Menu(self.root, tearoff=0)
        self.context_menu.add_command(label="View Details", command=self.show_process_details)
        self.context_menu.add_command(label="Kill Process", command=self.kill_selected_process)
        
        # Привязка правой кнопки мыши
        self.tree.bind("<Button-3>", self.show_context_menu)

    def show_context_menu(self, event):
        """Показ контекстного меню"""
        item = self.tree.identify_row(event.y)
        if item:
            self.tree.selection_set(item)
            self.context_menu.post(event.x_root, event.y_root)

    def show_process_details(self):
        """Показ деталей выбранного процесса"""
        selected_item = self.tree.selection()
        if not selected_item:
            messagebox.showwarning("Warning", "Please select a process first.")
            return

        pid, name, memory, cpu = self.tree.item(selected_item, "values")
        details = (
            f"Process Details:\n\n"
            f"PID: {pid}\n"
            f"Name: {name}\n"
            f"Memory Usage: {memory} MB\n"
            f"CPU Usage: {cpu}"
        )
        messagebox.showinfo("Process Details", details)

    def create_performance_tab(self):
        """Создание вкладки с графиками производительности"""
        self.performance_frame = tk.Frame(self.notebook)
        self.notebook.add(self.performance_frame, text="Performance")
        
        # Кнопки выбора графика
        self.graph_buttons_frame = tk.Frame(self.performance_frame)
        self.graph_buttons_frame.pack(pady=5)
        
        self.cpu_btn = tk.Button(self.graph_buttons_frame, text="CPU", 
                                command=lambda: self.switch_graph("CPU"), bg='lightblue')
        self.cpu_btn.pack(side=tk.LEFT, padx=5)
        
        self.memory_btn = tk.Button(self.graph_buttons_frame, text="Memory", 
                                   command=lambda: self.switch_graph("Memory"), bg='gray')
        self.memory_btn.pack(side=tk.LEFT, padx=5)
        
        self.gpu_btn = tk.Button(self.graph_buttons_frame, text="GPU", 
                                command=lambda: self.switch_graph("GPU"), bg='gray')
        self.gpu_btn.pack(side=tk.LEFT, padx=5)
        
        # Контейнер для графика
        self.graph_container = tk.Frame(self.performance_frame)
        self.graph_container.pack(expand=True, fill=tk.BOTH)

    def switch_graph(self, graph_type):
        """Переключение между графиками"""
        self.current_graph = graph_type
        
        # Обновляем цвета кнопок
        self.cpu_btn.config(bg='lightblue' if graph_type == "CPU" else 'gray')
        self.memory_btn.config(bg='lightgreen' if graph_type == "Memory" else 'gray')
        self.gpu_btn.config(bg='lightcoral' if graph_type == "GPU" else 'gray')
        
        # Обновляем отображение графика
        self.update_graph_display()

    def update_graph_display(self):
        """Обновление отображения текущего графика"""
        # Очищаем контейнер
        for widget in self.graph_container.winfo_children():
            widget.destroy()
        
        # Создаем новую фигуру для текущего графика
        self.fig, self.ax = plt.subplots(figsize=(10, 6))
        
        if self.current_graph == "CPU":
            self.line, = self.ax.plot(self.cpu_data, label='CPU Usage (%)')
            self.ax.set_ylim(0, 100)
            self.ax.set_ylabel('CPU (%)')
            self.ax.set_title('CPU Usage Over Time')
        elif self.current_graph == "Memory":
            self.line, = self.ax.plot(self.memory_data, label='Memory Usage (%)')
            self.ax.set_ylim(0, 100)
            self.ax.set_ylabel('Memory (%)')
            self.ax.set_title('Memory Usage Over Time')
        elif self.current_graph == "GPU":
            self.line, = self.ax.plot(self.gpu_data, label='GPU Usage (%)')
            self.ax.set_ylim(0, 100)
            self.ax.set_ylabel('GPU (%)')
            self.ax.set_title('GPU Usage Over Time')
        
        self.ax.set_xlabel('Time (seconds)')
        self.ax.legend()
        self.ax.grid(True)
        
        # Создаем новый canvas
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.graph_container)
        self.canvas.get_tk_widget().pack(expand=True, fill=tk.BOTH)
        self.canvas.draw()

    def on_close(self):
        """Обработчик закрытия окна"""
        self.auto_refresh_active = False
        self.performance_update_active = False
        self.gpu_update_active = False
        
        # Отменяем все запланированные вызовы
        for after_id in self.after_ids:
            try:
                self.root.after_cancel(after_id)
            except tk.TclError:
                pass
        self.after_ids.clear()
        
        # Закрываем фигуру matplotlib
        if hasattr(self, 'fig'):
            plt.close(self.fig)
        
        # Завершаем работу NVML
        if hasattr(self, 'gpu_handle') and self.gpu_handle is not None:
            try:
                pynvml.nvmlShutdown()
            except:
                pass
        
        self.root.destroy()
        os.kill(os.getpid(), signal.SIGTERM)

    def sort_column(self, column, reverse):
        """Сортировка колонки с сохранением параметров"""
        self.current_sort_column = column
        self.current_sort_reverse = reverse
        
        items = [(self.tree.set(item, column), item) for item in self.tree.get_children('')]
        
        if column in ["PID", "Memory", "CPU"]:
            items.sort(key=lambda x: float(x[0].replace('%', '') if x[0] else 0), reverse=reverse)
        else:
            items.sort(reverse=reverse)
        
        for index, (_, item) in enumerate(items):
            self.tree.move(item, '', index)
        
        # Обновляем заголовки
        for col in ["PID", "Name", "Memory", "CPU"]:
            if col == column:
                self.tree.heading(col, text=f"{col} {'▼' if reverse else '▲'}")
            else:
                self.tree.heading(col, text=col)
        
        self.tree.heading(column, command=lambda: self.sort_column(column, not reverse))

    def setup_auto_refresh(self):
        """Циклическое обновление списка процессов"""
        if self.auto_refresh_active:
            self.refresh_process_list()
            after_id = self.root.after(self.auto_refresh_interval, self.setup_auto_refresh)
            self.after_ids.append(after_id)

    def refresh_process_list(self):
        """Обновление списка процессов с сохранением сортировки"""
        selected_item = self.tree.selection()
        selected_pid = self.tree.item(selected_item, "values")[0] if selected_item else None
        
        for row in self.tree.get_children():
            self.tree.delete(row)

        process_list = get_process_info()
        # Фильтруем процессы с PID = 0
        process_list = [p for p in process_list if p.pid != 0]
        total_cpu = sum(p.cpu for p in process_list) or 1
        
        for process in process_list:
            cpu_percent = (process.cpu / total_cpu) * 100
            cpu_percent = min(100, max(0, cpu_percent))
            
            tag = 'high' if cpu_percent > 5 else 'medium' if cpu_percent > 1 else 'low'
            
            self.tree.insert("", tk.END, values=(
                process.pid, 
                process.name, 
                f"{process.memory:.2f}", 
                f"{cpu_percent:.1f}%"
            ), tags=(tag,))
        
        if selected_pid:
            for child in self.tree.get_children():
                if self.tree.item(child, "values")[0] == selected_pid:
                    self.tree.selection_set(child)
                    self.tree.focus(child)
                    break
        
        self.sort_column(self.current_sort_column, self.current_sort_reverse)

        self.tree.tag_configure('high', background='#ffcccc')
        self.tree.tag_configure('medium', background='#ffffcc')
        self.tree.tag_configure('low', background='#ffffff')

    def kill_selected_process(self):
        """Завершение выбранного процесса"""
        selected_item = self.tree.selection()
        if not selected_item:
            messagebox.showwarning("Warning", "Please select a process to kill.")
            return

        pid = self.tree.item(selected_item, "values")[0]
        try:
            psutil.Process(int(pid)).terminate()
            messagebox.showinfo("Success", f"Process {pid} terminated.")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to terminate process {pid}: {e}")

    def setup_performance_charts(self):
        """Инициализация данных для графиков производительности"""
        self.update_graph_display()

    def update_performance_charts(self):
        """Обновление данных для графиков производительности каждую секунду"""
        if self.performance_update_active:
            # CPU данные
            self.cpu_data.append(psutil.cpu_percent())
            if len(self.cpu_data) > self.max_data_points:
                self.cpu_data.pop(0)
            
            # Memory данные
            memory_info = psutil.virtual_memory()
            self.memory_data.append(memory_info.percent)
            if len(self.memory_data) > self.max_data_points:
                self.memory_data.pop(0)
            
            # GPU данные
            if self.gpu_update_active and self.gpu_handle is not None:
                try:
                    util = pynvml.nvmlDeviceGetUtilizationRates(self.gpu_handle)
                    gpu_usage = util.gpu
                except Exception as e:
                    print(f"Error getting GPU usage: {e}")
                    gpu_usage = 0
                self.gpu_data.append(gpu_usage)
                if len(self.gpu_data) > self.max_data_points:
                    self.gpu_data.pop(0)
            
            # Обновляем текущий график
            if hasattr(self, 'line'):
                if self.current_graph == "CPU":
                    self.line.set_ydata(self.cpu_data)
                    self.line.set_xdata(range(len(self.cpu_data)))
                    self.ax.set_xlim(0, len(self.cpu_data))
                elif self.current_graph == "Memory":
                    self.line.set_ydata(self.memory_data)
                    self.line.set_xdata(range(len(self.memory_data)))
                    self.ax.set_xlim(0, len(self.memory_data))
                elif self.current_graph == "GPU":
                    self.line.set_ydata(self.gpu_data)
                    self.line.set_xdata(range(len(self.gpu_data)))
                    self.ax.set_xlim(0, len(self.gpu_data))
                
                self.canvas.draw()
            
            after_id = self.root.after(self.performance_update_interval, self.update_performance_charts)
            self.after_ids.append(after_id)


def run_gui():
    root = tk.Tk()
    app = TaskManagerGUI(root)
    root.mainloop()

if __name__ == "__main__":
    run_gui()