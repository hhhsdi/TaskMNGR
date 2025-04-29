import tkinter as tk
from tkinter import ttk, messagebox
import psutil
import pynvml
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.pyplot as plt
from main import get_process_info

class TaskManagerGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Task Manager")
        self.root.geometry("800x600")

        self.notebook = ttk.Notebook(root)
        self.notebook.pack(expand=True, fill=tk.BOTH)

        self.details_frame = tk.Frame(self.notebook)
        self.notebook.add(self.details_frame, text="Details")
 
        self.tree = ttk.Treeview(self.details_frame, columns=("PID", "Name", "Memory", "CPU"), show='headings')
        self.tree.heading("PID", text="PID")
        self.tree.heading("Name", text="Name")
        self.tree.heading("Memory", text="Memory (MB)")
        self.tree.heading("CPU", text="CPU")
        self.tree.pack(expand=True, fill=tk.BOTH)

        self.refresh_button = tk.Button(self.details_frame, text="Refresh", command=self.refresh_process_list)
        self.refresh_button.pack(pady=5)

        self.kill_button = tk.Button(self.details_frame, text="Kill Process", command=self.kill_selected_process)
        self.kill_button.pack(pady=5) 

        self.refresh_process_list()

        self.performance_frame = tk.Frame(self.notebook)
        self.notebook.add(self.performance_frame, text="Performance")

        self.setup_performance_charts()
        self.update_performance_charts()

        self.gpu_button = tk.Button(self.details_frame, text="View GPU Performance", command=self.show_gpu_performance)
        self.gpu_button.pack(pady=5)

    def refresh_process_list(self):
        for row in self.tree.get_children():
            self.tree.delete(row)

        self.process_list = get_process_info()
        for process in self.process_list:
            self.tree.insert("", tk.END, values=(process.pid, process.name, f"{process.memory:.2f}", process.cpu))

    def kill_selected_process(self):
        selected_item = self.tree.selection()
        if not selected_item:
            messagebox.showwarning("Warning", "Please select a process to kill.")
            return

        pid = self.tree.item(selected_item, "values")[0]
        try:
            psutil.Process(int(pid)).terminate()
            messagebox.showinfo("Success", f"Process {pid} terminated.")
            self.refresh_process_list()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to terminate process {pid}: {e}")

    def setup_performance_charts(self):
        self.cpu_data = []
        self.memory_data = []

        self.fig, (self.cpu_ax, self.memory_ax) = plt.subplots(2, 1, figsize=(5, 4))

        self.cpu_line, = self.cpu_ax.plot(self.cpu_data, label='CPU Usage (%)')
        self.cpu_ax.set_ylim(0, 100)
        self.cpu_ax.set_ylabel('CPU (%)')
        self.cpu_ax.legend()

        self.memory_line, = self.memory_ax.plot(self.memory_data, label='Memory Usage (%)')
        self.memory_ax.set_ylim(0, 100)
        self.memory_ax.set_ylabel('Memory (%)')
        self.memory_ax.legend()

        self.canvas = FigureCanvasTkAgg(self.fig, master=self.performance_frame)
        self.canvas.get_tk_widget().pack(expand=True, fill=tk.BOTH)

    def update_performance_charts(self):
        self.cpu_data.append(psutil.cpu_percent())
        memory_info = psutil.virtual_memory()
        self.memory_data.append(memory_info.percent)

        if len(self.cpu_data) > 50:
            self.cpu_data.pop(0)
            self.memory_data.pop(0)

        self.cpu_line.set_ydata(self.cpu_data)
        self.cpu_line.set_xdata(range(len(self.cpu_data)))
        self.cpu_ax.set_xlim(0, len(self.cpu_data))

        self.memory_line.set_ydata(self.memory_data)
        self.memory_line.set_xdata(range(len(self.memory_data)))
        self.memory_ax.set_xlim(0, len(self.memory_data))

        self.canvas.draw()
        self.root.after(1000, self.update_performance_charts)

    def show_gpu_performance(self):
        gpu_window = tk.Toplevel(self.root)
        gpu_window.title("GPU Performance")
        gpu_window.geometry("600x400")

        self.gpu_data = []

        self.gpu_fig, self.gpu_ax = plt.subplots(figsize=(5, 3))
        self.gpu_line, = self.gpu_ax.plot(self.gpu_data, label='GPU Usage (%)')
        self.gpu_ax.set_ylim(0, 100)
        self.gpu_ax.set_ylabel('GPU (%)')
        self.gpu_ax.legend()

        self.gpu_canvas = FigureCanvasTkAgg(self.gpu_fig, master=gpu_window)
        self.gpu_canvas.get_tk_widget().pack(expand=True, fill=tk.BOTH)

        self.update_gpu_performance(gpu_window)

    def update_gpu_performance(self, window):
        try:
            pynvml.nvmlInit()
            handle = pynvml.nvmlDeviceGetHandleByIndex(0)  # Используем первую видеокарту
            util = pynvml.nvmlDeviceGetUtilizationRates(handle)
            gpu_usage = util.gpu  # Получаем процент использования GPU
            pynvml.nvmlShutdown()
        except Exception as e:
            print(f"Error getting GPU usage: {e}")
            gpu_usage = 0  # В случае ошибки используем 0

        self.gpu_data.append(gpu_usage)

        if len(self.gpu_data) > 50:
            self.gpu_data.pop(0)

        self.gpu_line.set_ydata(self.gpu_data)
        self.gpu_line.set_xdata(range(len(self.gpu_data)))
        self.gpu_ax.set_xlim(0, len(self.gpu_data))

        self.gpu_canvas.draw()
        window.after(1000, lambda: self.update_gpu_performance(window))


def run_gui():
    root = tk.Tk()
    app = TaskManagerGUI(root)
    root.mainloop()

if __name__ == "__main__":
    run_gui()