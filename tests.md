1. Тестируемые компоненты
Компонент	                  |           Что проверяется	                                                                                      |Методы тестирования
Инициализация GUI	          Корректность создания окна, настройки интервалов, инициализации                                                     GPU	test_initialization
Завершение процесса	        Корректность вызова terminate() для выбранного процесса	test_kill_selected_process (с моком psutil.Process)
Графики производительности	Обновление данных CPU, памяти и GPU	test_update_performance_charts (с моками psutil.cpu_percent, virtual_memory)
Переключение графиков	      Изменение активного графика (CPU/Memory/GPU) и обновление интерфейса	                                              test_switch_graph
Закрытие приложения	        Корректность отмены всех запланированных задач и освобождения ресурсов	                                            test_on_close
create_widgets()	          Корректность создания всех виджетов интерфейса	Проверка атрибутов и структуры GUI	                                assert isinstance(app.tree, ttk.Treeview)

