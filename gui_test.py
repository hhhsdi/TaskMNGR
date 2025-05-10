# test_gui.py
import pytest
from unittest.mock import MagicMock, patch
import tkinter as tk
from GUI import TaskManagerGUI
import psutil
import pynvml

@pytest.fixture
def root():
    return tk.Tk()

@pytest.fixture
def app(root):
    return TaskManagerGUI(root)

def test_initialization(app):
    """Тест инициализации приложения"""
    assert app.root.title() == "Task Manager"
    assert app.auto_refresh_interval == 3000
    assert app.performance_update_interval == 1000
    assert app.current_graph == "CPU"
    assert app.max_data_points == 60

def test_create_widgets(app):
    """Тест создания виджетов"""
    assert hasattr(app, 'notebook')
    assert hasattr(app, 'details_frame')
    assert hasattr(app, 'performance_frame')
    assert hasattr(app, 'tree')

def test_sort_column(app):
    """Тест сортировки колонок"""
    # Добавим тестовые данные
    app.tree.insert("", tk.END, values=("100", "Process1", "10.0", "5.0%"))
    app.tree.insert("", tk.END, values=("200", "Process2", "20.0", "10.0%"))
    
    # Тест сортировки по CPU (по убыванию)
    app.sort_column("CPU", True)
    items = app.tree.get_children()
    first_item = app.tree.item(items[0], "values")
    assert float(first_item[3].replace('%', '')) == 10.0
    
    # Тест сортировки по CPU (по возрастанию)
    app.sort_column("CPU", False)
    items = app.tree.get_children()
    first_item = app.tree.item(items[0], "values")
    assert float(first_item[3].replace('%', '')) == 5.0

@patch('psutil.Process')
def test_kill_selected_process(mock_process, app):
    """Тест завершения процесса"""
    # Добавим тестовый процесс
    app.tree.insert("", tk.END, values=("100", "Process1", "10.0", "5.0%"))
    app.tree.selection_set(app.tree.get_children()[0])
    
    # Вызовем метод
    app.kill_selected_process()
    
    # Проверим, что метод terminate был вызван
    mock_process.return_value.terminate.assert_called_once()

@patch('psutil.cpu_percent')
@patch('psutil.virtual_memory')
def test_update_performance_charts(mock_memory, mock_cpu, app):
    """Тест обновления графиков производительности"""
    # Настроим моки
    mock_cpu.return_value = 50.0
    memory_info = MagicMock()
    memory_info.percent = 75.0
    mock_memory.return_value = memory_info
    
    # Вызовем метод
    app.update_performance_charts()
    
    # Проверим обновление данных
    assert app.cpu_data[-1] == 50.0
    assert app.memory_data[-1] == 75.0

@patch('pynvml.nvmlDeviceGetUtilizationRates')
def test_gpu_update(mock_gpu_util, app):
    """Тест обновления данных GPU"""
    if app.gpu_handle is not None:
        # Настроим мок
        util = MagicMock()
        util.gpu = 30.0
        mock_gpu_util.return_value = util
        
        # Вызовем метод
        app.update_performance_charts()
        
        # Проверим обновление данных
        assert app.gpu_data[-1] == 30.0

def test_switch_graph(app):
    """Тест переключения графиков"""
    app.switch_graph("Memory")
    assert app.current_graph == "Memory"
    assert app.memory_btn['bg'] == 'lightgreen'
    
    app.switch_graph("GPU")
    assert app.current_graph == "GPU"
    assert app.gpu_btn['bg'] == 'lightcoral'

def test_on_close(app):
    """Тест обработки закрытия окна"""
    app.on_close()
    assert app.auto_refresh_active is False
    assert app.performance_update_active is False
    assert app.gpu_update_active is False