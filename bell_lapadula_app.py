
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import json
import os
import shutil
from pathlib import Path
from datetime import datetime

class BellLaPadulaApp:
    def __init__(self, root):
        self.root = root
        self.root.title("🔐 Модель Белла-Лападулы - Управление файловой системой")
        self.root.geometry("1200x800")

        # Путь к корневой директории
        self.root_path = Path.home() / "LAB4_BellLaPadula"
        self.config_file = self.root_path / "config.json"

        # Инициализация данных
        self.levels = []
        self.folders = []
        self.next_level_id = 1
        self.next_folder_id = 1

        # Создаем корневую директорию
        self.root_path.mkdir(exist_ok=True)

        # Загрузка или создание конфигурации
        self.load_config()

        # Создание интерфейса
        self.create_ui()

        # Обновление UI
        self.refresh_all()

    def load_config(self):
        """Загрузка конфигурации из файла"""
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.levels = data.get('levels', [])
                    self.folders = data.get('folders', [])
                    self.next_level_id = data.get('next_level_id', 1)
                    self.next_folder_id = data.get('next_folder_id', 1)
            except Exception as e:
                messagebox.showerror("Ошибка", f"Не удалось загрузить конфигурацию: {e}")

        # Создаем уровни по умолчанию, если их нет
        if not self.levels:
            self.levels = [
                {'id': 1, 'name': 'Несекретно', 'rank': 0},
                {'id': 2, 'name': 'Конфиденциально', 'rank': 1},
                {'id': 3, 'name': 'Секретно', 'rank': 2},
                {'id': 4, 'name': 'Совершенно секретно', 'rank': 3}
            ]
            self.next_level_id = 5

        # Создаем папки по умолчанию, если их нет
        if not self.folders:
            self.folders = [
                {'id': 1, 'name': 'public', 'parent': None, 'level_id': 1},
                {'id': 2, 'name': 'confidential', 'parent': None, 'level_id': 2},
                {'id': 3, 'name': 'secret', 'parent': None, 'level_id': 3}
            ]
            self.next_folder_id = 4

            # Создаем реальные папки
            for folder in self.folders:
                self.create_physical_folder(folder)

        self.save_config()

    def save_config(self):
        """Сохранение конфигурации в файл"""
        try:
            data = {
                'levels': self.levels,
                'folders': self.folders,
                'next_level_id': self.next_level_id,
                'next_folder_id': self.next_folder_id
            }
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось сохранить конфигурацию: {e}")

    def shift_ranks(self, from_rank):
        """Смещение рангов на 1 вперед начиная с from_rank"""
        for level in self.levels:
            if level['rank'] >= from_rank:
                level['rank'] += 1

    def check_bell_lapadula_hierarchy(self, folder_id=None, parent_id=None, new_level_id=None):
        """
        Проверка соответствия модели Белла-Лападулы для иерархии папок
        Правило: дочерняя папка должна иметь уровень <= родительской (No Read Up)
        Нельзя создавать более секретные данные внутри менее секретных папок
        """
        # Если изменяется существующая папка
        if folder_id:
            folder = next((f for f in self.folders if f['id'] == folder_id), None)
            if not folder:
                return True

            level_id = new_level_id if new_level_id else folder['level_id']
            parent_id = folder['parent']

        # Проверка родительской папки
        if parent_id:
            parent = next((f for f in self.folders if f['id'] == parent_id), None)
            if parent:
                parent_level = next((l for l in self.levels if l['id'] == parent['level_id']), None)
                child_level = next((l for l in self.levels if l['id'] == level_id), None)

                if parent_level and child_level:
                    # Дочерняя папка должна быть <= родительской
                    if child_level['rank'] > parent_level['rank']:
                        return False

        # Проверка дочерних папок
        if folder_id:
            children = [f for f in self.folders if f['parent'] == folder_id]
            current_level = next((l for l in self.levels if l['id'] == level_id), None)

            for child in children:
                child_level = next((l for l in self.levels if l['id'] == child['level_id']), None)
                if current_level and child_level:
                    # Дочерние папки должны быть <= текущей
                    if child_level['rank'] > current_level['rank']:
                        return False

        return True

    def validate_level_rank_change(self, level_id, new_rank):
        """Проверка возможности изменения ранга уровня с учетом модели Белла-Лападулы"""
        # Находим все папки с этим уровнем
        folders_with_level = [f for f in self.folders if f['level_id'] == level_id]

        for folder in folders_with_level:
            # Проверяем родительскую папку
            if folder['parent']:
                parent = next((f for f in self.folders if f['id'] == folder['parent']), None)
                if parent:
                    parent_level = next((l for l in self.levels if l['id'] == parent['level_id']), None)
                    if parent_level and new_rank > parent_level['rank']:
                        return False, f"Папка '{folder['name']}' станет более секретной, чем родитель"

            # Проверяем дочерние папки
            children = [f for f in self.folders if f['parent'] == folder['id']]
            for child in children:
                child_level = next((l for l in self.levels if l['id'] == child['level_id']), None)
                if child_level and child_level['rank'] > new_rank:
                    return False, f"Папка '{folder['name']}' имеет более секретную дочернюю папку '{child['name']}'"

        return True, ""

    def create_ui(self):
        """Создание пользовательского интерфейса"""
        # Notebook для вкладок
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Вкладка 1: Уровни секретности
        self.tab_levels = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_levels, text="Уровни секретности")
        self.create_levels_tab()

        # Вкладка 2: Управление папками
        self.tab_folders = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_folders, text="Управление папками")
        self.create_folders_tab()

        # Вкладка 3: Копирование файлов
        self.tab_copy = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_copy, text="Копирование файлов")
        self.create_copy_tab()

        # Статус бар
        self.status_bar = tk.Label(self.root, text=f"Корневая директория: {self.root_path}", 
                                   bd=1, relief=tk.SUNKEN, anchor=tk.W)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)

    def create_levels_tab(self):
        """Создание вкладки уровней секретности"""
        # Фрейм для создания уровня
        create_frame = ttk.LabelFrame(self.tab_levels, text="Создать уровень секретности", padding=10)
        create_frame.pack(fill=tk.X, padx=10, pady=5)

        ttk.Label(create_frame, text="Название:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.level_name_entry = ttk.Entry(create_frame, width=30)
        self.level_name_entry.grid(row=0, column=1, pady=5, padx=5)

        ttk.Label(create_frame, text="Ранг (0 и выше):").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.level_rank_entry = ttk.Spinbox(create_frame, from_=0, to=100, width=28)
        self.level_rank_entry.grid(row=1, column=1, pady=5, padx=5)

        ttk.Button(create_frame, text="Создать уровень", command=self.create_level).grid(row=2, column=0, columnspan=2, pady=10)

        # Список уровней
        list_frame = ttk.LabelFrame(self.tab_levels, text="Существующие уровни", padding=10)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        # Treeview для уровней
        columns = ('rank', 'folders_count')
        self.levels_tree = ttk.Treeview(list_frame, columns=columns, height=15)
        self.levels_tree.heading('#0', text='Название')
        self.levels_tree.heading('rank', text='Ранг')
        self.levels_tree.heading('folders_count', text='Папок')

        self.levels_tree.column('#0', width=300)
        self.levels_tree.column('rank', width=100)
        self.levels_tree.column('folders_count', width=100)

        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.levels_tree.yview)
        self.levels_tree.configure(yscroll=scrollbar.set)

        self.levels_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Кнопки управления
        btn_frame = ttk.Frame(list_frame)
        btn_frame.pack(fill=tk.X, pady=5)

        ttk.Button(btn_frame, text="Изменить название", command=self.edit_level_name).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Изменить ранг", command=self.edit_level_rank).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Удалить", command=self.delete_level).pack(side=tk.LEFT, padx=5)

    def create_folders_tab(self):
        """Создание вкладки управления папками"""
        # Фрейм для создания папки
        create_frame = ttk.LabelFrame(self.tab_folders, text="Создать папку", padding=10)
        create_frame.pack(fill=tk.X, padx=10, pady=5)

        ttk.Label(create_frame, text="Название:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.folder_name_entry = ttk.Entry(create_frame, width=30)
        self.folder_name_entry.grid(row=0, column=1, pady=5, padx=5)

        ttk.Label(create_frame, text="Родительская папка:").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.parent_folder_combo = ttk.Combobox(create_frame, width=28, state='readonly')
        self.parent_folder_combo.grid(row=1, column=1, pady=5, padx=5)

        ttk.Button(create_frame, text="Создать папку", command=self.create_folder).grid(row=2, column=0, columnspan=2, pady=10)

        # Дерево папок
        tree_frame = ttk.LabelFrame(self.tab_folders, text="Структура папок", padding=10)
        tree_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        # Treeview для папок
        columns = ('level', 'files_count', 'path')
        self.folders_tree = ttk.Treeview(tree_frame, columns=columns, height=20)
        self.folders_tree.heading('#0', text='Название')
        self.folders_tree.heading('level', text='Уровень секретности')
        self.folders_tree.heading('files_count', text='Файлов')
        self.folders_tree.heading('path', text='Путь')

        self.folders_tree.column('#0', width=200)
        self.folders_tree.column('level', width=200)
        self.folders_tree.column('files_count', width=100)
        self.folders_tree.column('path', width=300)

        scrollbar = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.folders_tree.yview)
        self.folders_tree.configure(yscroll=scrollbar.set)

        self.folders_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Кнопки управления
        btn_frame = ttk.Frame(tree_frame)
        btn_frame.pack(fill=tk.X, pady=5)

        ttk.Button(btn_frame, text="Изменить уровень", command=self.change_folder_level).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Переименовать", command=self.rename_folder).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Удалить", command=self.delete_folder).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Открыть в проводнике", command=self.open_folder).pack(side=tk.LEFT, padx=5)

    def create_copy_tab(self):
        """Создание вкладки копирования файлов"""
        # Информация
        info_frame = ttk.LabelFrame(self.tab_copy, text="Правила модели Белла-Лападулы", padding=10)
        info_frame.pack(fill=tk.X, padx=10, pady=5)

        info_text = "• No Read Up: нельзя читать файлы выше уровня доступа\n"
        info_text += "• No Write Down: нельзя записывать файлы ниже уровня доступа\n"
        info_text += "• Дочерняя папка должна иметь уровень <= родительской\n"
        info_text += "• Копирование разрешено с низкого уровня на высокий (или равный)"

        ttk.Label(info_frame, text=info_text, justify=tk.LEFT).pack()

        # Копирование
        copy_frame = ttk.LabelFrame(self.tab_copy, text="Копирование файлов", padding=10)
        copy_frame.pack(fill=tk.X, padx=10, pady=5)

        ttk.Label(copy_frame, text="Исходная папка:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.source_folder_combo = ttk.Combobox(copy_frame, width=40, state='readonly')
        self.source_folder_combo.grid(row=0, column=1, pady=5, padx=5)
        self.source_folder_combo.bind('<<ComboboxSelected>>', lambda e: self.validate_copy())

        ttk.Label(copy_frame, text="Папка назначения:").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.dest_folder_combo = ttk.Combobox(copy_frame, width=40, state='readonly')
        self.dest_folder_combo.grid(row=1, column=1, pady=5, padx=5)
        self.dest_folder_combo.bind('<<ComboboxSelected>>', lambda e: self.validate_copy())

        self.copy_status_label = ttk.Label(copy_frame, text="", foreground="blue")
        self.copy_status_label.grid(row=2, column=0, columnspan=2, pady=10)

        self.copy_button = ttk.Button(copy_frame, text="Скопировать файлы", command=self.copy_files, state=tk.DISABLED)
        self.copy_button.grid(row=3, column=0, columnspan=2, pady=5)

        # Создание тестовых файлов
        test_frame = ttk.LabelFrame(self.tab_copy, text="Создать тестовые файлы", padding=10)
        test_frame.pack(fill=tk.X, padx=10, pady=5)

        ttk.Label(test_frame, text="Папка:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.test_folder_combo = ttk.Combobox(test_frame, width=40, state='readonly')
        self.test_folder_combo.grid(row=0, column=1, pady=5, padx=5)

        ttk.Label(test_frame, text="Количество файлов:").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.num_files_spin = ttk.Spinbox(test_frame, from_=1, to=20, width=38)
        self.num_files_spin.set(3)
        self.num_files_spin.grid(row=1, column=1, pady=5, padx=5)

        ttk.Button(test_frame, text="Создать файлы", command=self.create_test_files).grid(row=2, column=0, columnspan=2, pady=10)

    # Методы для работы с уровнями
    def create_level(self):
        """Создание нового уровня секретности"""
        name = self.level_name_entry.get().strip()
        rank_str = self.level_rank_entry.get().strip()

        if not name:
            messagebox.showerror("Ошибка", "Введите название уровня")
            return

        try:
            rank = int(rank_str)
        except ValueError:
            messagebox.showerror("Ошибка", "Ранг должен быть числом")
            return

        # Проверка на отрицательный ранг
        if rank < 0:
            messagebox.showerror("Ошибка", "Ранг не может быть отрицательным")
            return

        # Проверка на дублирование названия
        if any(l['name'].lower() == name.lower() for l in self.levels):
            messagebox.showerror("Ошибка", "Уровень с таким названием уже существует")
            return

        # Если ранг уже существует - смещаем
        if any(l['rank'] == rank for l in self.levels):
            if messagebox.askyesno("Подтверждение", 
                f"Ранг {rank} уже существует. Сместить существующие уровни на 1 вперед?"):
                self.shift_ranks(rank)
            else:
                return

        # Создание уровня
        self.levels.append({
            'id': self.next_level_id,
            'name': name,
            'rank': rank
        })
        self.next_level_id += 1

        self.levels.sort(key=lambda x: x['rank'])
        self.save_config()
        self.refresh_all()

        self.level_name_entry.delete(0, tk.END)
        messagebox.showinfo("Успех", f"Уровень '{name}' создан с рангом {rank}")

    def edit_level_name(self):
        """Редактирование названия уровня"""
        selection = self.levels_tree.selection()
        if not selection:
            messagebox.showwarning("Предупреждение", "Выберите уровень для редактирования")
            return

        level_id = int(self.levels_tree.item(selection[0])['tags'][0])
        level = next((l for l in self.levels if l['id'] == level_id), None)

        if not level:
            return

        new_name = simpledialog.askstring("Редактирование", "Введите новое название:", 
                                         initialvalue=level['name'])
        if new_name and new_name != level['name']:
            if any(l['id'] != level_id and l['name'].lower() == new_name.lower() for l in self.levels):
                messagebox.showerror("Ошибка", "Уровень с таким названием уже существует")
                return

            level['name'] = new_name
            self.save_config()
            self.refresh_all()
            messagebox.showinfo("Успех", f"Уровень переименован в '{new_name}'")

    def edit_level_rank(self):
        """Редактирование ранга уровня"""
        selection = self.levels_tree.selection()
        if not selection:
            messagebox.showwarning("Предупреждение", "Выберите уровень для редактирования")
            return

        level_id = int(self.levels_tree.item(selection[0])['tags'][0])
        level = next((l for l in self.levels if l['id'] == level_id), None)

        if not level:
            return

        new_rank_str = simpledialog.askstring("Редактирование ранга", 
                                             f"Введите новый ранг (текущий: {level['rank']}):",
                                             initialvalue=str(level['rank']))

        if not new_rank_str:
            return

        try:
            new_rank = int(new_rank_str)
        except ValueError:
            messagebox.showerror("Ошибка", "Ранг должен быть числом")
            return

        if new_rank < 0:
            messagebox.showerror("Ошибка", "Ранг не может быть отрицательным")
            return

        if new_rank == level['rank']:
            return

        # Проверка модели Белла-Лападулы
        valid, error_msg = self.validate_level_rank_change(level_id, new_rank)
        if not valid:
            messagebox.showerror("Ошибка модели Белла-Лападулы", 
                f"Невозможно изменить ранг:\n{error_msg}\n\nНарушается правило: дочерняя папка должна иметь уровень <= родительской")
            return

        old_rank = level['rank']
        level['rank'] = new_rank

        # Проверка на конфликт рангов
        if any(l['id'] != level_id and l['rank'] == new_rank for l in self.levels):
            if messagebox.askyesno("Подтверждение", 
                f"Ранг {new_rank} уже существует. Сместить существующие уровни?"):
                # Временно возвращаем старый ранг
                level['rank'] = old_rank
                # Смещаем другие
                self.shift_ranks(new_rank)
                # Устанавливаем новый
                level['rank'] = new_rank
            else:
                level['rank'] = old_rank
                return

        self.levels.sort(key=lambda x: x['rank'])
        self.save_config()
        self.refresh_all()
        messagebox.showinfo("Успех", f"Ранг изменен на {new_rank}")

    def delete_level(self):
        """Удаление уровня"""
        selection = self.levels_tree.selection()
        if not selection:
            messagebox.showwarning("Предупреждение", "Выберите уровень для удаления")
            return

        if len(self.levels) == 1:
            messagebox.showerror("Ошибка", "Нельзя удалить последний уровень")
            return

        level_id = int(self.levels_tree.item(selection[0])['tags'][0])
        level = next((l for l in self.levels if l['id'] == level_id), None)

        if not level:
            return

        # Проверка использования
        folders_with_level = [f for f in self.folders if f['level_id'] == level_id]
        if folders_with_level:
            messagebox.showerror("Ошибка", "Невозможно удалить: уровень используется папками")
            return

        if messagebox.askyesno("Подтверждение", f"Удалить уровень '{level['name']}'?"):
            self.levels = [l for l in self.levels if l['id'] != level_id]
            self.save_config()
            self.refresh_all()
            messagebox.showinfo("Успех", "Уровень удален")

    # Методы для работы с папками
    def get_folder_path(self, folder_id):
        """Получение полного пути к папке"""
        parts = []
        current = next((f for f in self.folders if f['id'] == folder_id), None)

        while current:
            parts.insert(0, current['name'])
            if current['parent']:
                current = next((f for f in self.folders if f['id'] == current['parent']), None)
            else:
                break

        return self.root_path / Path(*parts)

    def create_physical_folder(self, folder):
        """Создание реальной папки в файловой системе"""
        try:
            path = self.get_folder_path(folder['id'])
            path.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось создать папку: {e}")

    def create_folder(self):
        """Создание новой папки"""
        name = self.folder_name_entry.get().strip()

        if not name:
            messagebox.showerror("Ошибка", "Введите название папки")
            return

        # Проверка на допустимые символы
        if not all(c.isalnum() or c in '_-' for c in name):
            messagebox.showerror("Ошибка", "Название может содержать только буквы, цифры, _ и -")
            return

        # Получение родительской папки
        parent_text = self.parent_folder_combo.get()
        parent_id = None
        if parent_text and parent_text != "Корневая папка":
            parent_id = int(parent_text.split('[ID:')[1].split(']')[0])

        # Проверка на дублирование
        siblings = [f for f in self.folders if f['parent'] == parent_id]
        if any(f['name'].lower() == name.lower() for f in siblings):
            messagebox.showerror("Ошибка", "Папка с таким именем уже существует")
            return

        # Определение минимального уровня с учетом родителя
        # Правило: дочерняя папка должна иметь уровень <= родительской (No Read Up)
        if parent_id:
            parent = next((f for f in self.folders if f['id'] == parent_id), None)
            parent_level = next((l for l in self.levels if l['id'] == parent['level_id']), None)
            # Дочерняя папка должна иметь уровень <= родительской
            available_levels = [l for l in self.levels if l['rank'] <= parent_level['rank']]
            if available_levels:
                min_level = min(available_levels, key=lambda x: x['rank'])
            else:
                messagebox.showerror("Ошибка", "Нет доступных уровней для создания папки")
                return
        else:
            # Корневая папка - минимальный уровень
            min_level = min(self.levels, key=lambda x: x['rank'])

        # Создание папки
        folder = {
            'id': self.next_folder_id,
            'name': name,
            'parent': parent_id,
            'level_id': min_level['id']
        }
        self.folders.append(folder)
        self.next_folder_id += 1

        self.create_physical_folder(folder)
        self.save_config()
        self.refresh_all()

        self.folder_name_entry.delete(0, tk.END)
        messagebox.showinfo("Успех", f"Папка '{name}' создана с уровнем '{min_level['name']}'")

    def rename_folder(self):
        """Переименование папки"""
        selection = self.folders_tree.selection()
        if not selection:
            messagebox.showwarning("Предупреждение", "Выберите папку для переименования")
            return

        folder_id = int(self.folders_tree.item(selection[0])['tags'][0])
        folder = next((f for f in self.folders if f['id'] == folder_id), None)

        if not folder:
            return

        new_name = simpledialog.askstring("Переименование", "Введите новое название:", 
                                         initialvalue=folder['name'])

        if not new_name or new_name == folder['name']:
            return

        if not all(c.isalnum() or c in '_-' for c in new_name):
            messagebox.showerror("Ошибка", "Название может содержать только буквы, цифры, _ и -")
            return

        # Проверка на дублирование
        siblings = [f for f in self.folders if f['parent'] == folder['parent'] and f['id'] != folder_id]
        if any(f['name'].lower() == new_name.lower() for f in siblings):
            messagebox.showerror("Ошибка", "Папка с таким именем уже существует")
            return

        try:
            # Переименование реальной папки
            old_path = self.get_folder_path(folder_id)
            old_name = folder['name']
            folder['name'] = new_name
            new_path = self.get_folder_path(folder_id)

            if old_path.exists():
                old_path.rename(new_path)

            self.save_config()
            self.refresh_all()
            messagebox.showinfo("Успех", f"Папка переименована в '{new_name}'")
        except Exception as e:
            folder['name'] = old_name  # Откат
            messagebox.showerror("Ошибка", f"Не удалось переименовать: {e}")

    def delete_folder(self):
        """Удаление папки"""
        selection = self.folders_tree.selection()
        if not selection:
            messagebox.showwarning("Предупреждение", "Выберите папку для удаления")
            return

        folder_id = int(self.folders_tree.item(selection[0])['tags'][0])
        folder = next((f for f in self.folders if f['id'] == folder_id), None)

        if not folder:
            return

        # Проверка на подпапки
        children = [f for f in self.folders if f['parent'] == folder_id]
        if children:
            messagebox.showerror("Ошибка", "Невозможно удалить: папка содержит подпапки")
            return

        if messagebox.askyesno("Подтверждение", f"Удалить папку '{folder['name']}'?"):
            try:
                # Удаление реальной папки
                path = self.get_folder_path(folder_id)
                if path.exists():
                    shutil.rmtree(path)

                self.folders = [f for f in self.folders if f['id'] != folder_id]
                self.save_config()
                self.refresh_all()
                messagebox.showinfo("Успех", "Папка удалена")
            except Exception as e:
                messagebox.showerror("Ошибка", f"Не удалось удалить: {e}")

    def change_folder_level(self):
        """Изменение уровня секретности папки"""
        selection = self.folders_tree.selection()
        if not selection:
            messagebox.showwarning("Предупреждение", "Выберите папку")
            return

        folder_id = int(self.folders_tree.item(selection[0])['tags'][0])
        folder = next((f for f in self.folders if f['id'] == folder_id), None)

        if not folder:
            return

        current_level = next((l for l in self.levels if l['id'] == folder['level_id']), None)

        # Фильтрация доступных уровней с учетом Bell-LaPadula
        available_levels = []
        for level in self.levels:
            # Временно меняем уровень для проверки
            old_level_id = folder['level_id']
            folder['level_id'] = level['id']

            if self.check_bell_lapadula_hierarchy(folder_id=folder_id):
                available_levels.append(level)

            # Возвращаем обратно
            folder['level_id'] = old_level_id

        if not available_levels:
            messagebox.showerror("Ошибка", "Нет доступных уровней согласно модели Белла-Лападулы")
            return

        # Диалог выбора уровня
        available_levels.sort(key=lambda x: x['rank'])
        level_names = [f"{l['name']} (Ранг {l['rank']})" for l in available_levels]
        current_index = next((i for i, l in enumerate(available_levels) if l['id'] == current_level['id']), 0)

        dialog = tk.Toplevel(self.root)
        dialog.title("Изменить уровень секретности")
        dialog.geometry("500x250")
        dialog.transient(self.root)
        dialog.grab_set()

        ttk.Label(dialog, text="Выберите уровень (согласно модели Белла-Лападулы):").pack(pady=10)

        level_var = tk.StringVar(value=level_names[current_index])
        level_combo = ttk.Combobox(dialog, textvariable=level_var, values=level_names, state='readonly', width=40)
        level_combo.pack(pady=10)

        # Информация
        info_text = "Правило: дочерняя папка должна иметь уровень <= родительской"
        ttk.Label(dialog, text=info_text, foreground="blue", wraplength=450).pack(pady=5)

        def apply_level():
            selected = level_combo.current()
            new_level = available_levels[selected]

            # Финальная проверка
            old_level_id = folder['level_id']
            folder['level_id'] = new_level['id']

            if not self.check_bell_lapadula_hierarchy(folder_id=folder_id):
                folder['level_id'] = old_level_id
                messagebox.showerror("Ошибка", "Изменение нарушает модель Белла-Лападулы")
                dialog.destroy()
                return

            self.save_config()
            self.refresh_all()
            messagebox.showinfo("Успех", f"Уровень изменен на '{new_level['name']}'")
            dialog.destroy()

        button_frame = ttk.Frame(dialog)
        button_frame.pack(pady=20)

        ttk.Button(button_frame, text="Применить", command=apply_level).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Отмена", command=dialog.destroy).pack(side=tk.LEFT, padx=5)

    def open_folder(self):
        """Открытие папки в проводнике"""
        selection = self.folders_tree.selection()
        if not selection:
            messagebox.showwarning("Предупреждение", "Выберите папку")
            return

        folder_id = int(self.folders_tree.item(selection[0])['tags'][0])
        path = self.get_folder_path(folder_id)

        try:
            if os.name == 'nt':  # Windows
                os.startfile(path)
            elif os.name == 'posix':  # macOS/Linux
                os.system(f'open "{path}"' if os.uname().sysname == 'Darwin' else f'xdg-open "{path}"')
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось открыть папку: {e}")

    # Методы для копирования файлов
    def get_files_in_folder(self, folder_id):
        """Получение списка файлов в папке"""
        path = self.get_folder_path(folder_id)
        try:
            if path.exists():
                return [f for f in path.iterdir() if f.is_file()]
        except:
            pass
        return []

    def get_max_parent_level_rank(self, folder_id):
        """Получить максимальный ранг среди всех родительских папок"""
        max_rank = 0
        current = next((f for f in self.folders if f['id'] == folder_id), None)

        while current and current['parent']:
            parent = next((f for f in self.folders if f['id'] == current['parent']), None)
            if parent:
                parent_level = next((l for l in self.levels if l['id'] == parent['level_id']), None)
                if parent_level:
                    max_rank = max(max_rank, parent_level['rank'])
                current = parent
            else:
                break

        return max_rank

    def validate_copy(self):
        """Валидация возможности копирования по модели Белла-Лападулы"""
        source_text = self.source_folder_combo.get()
        dest_text = self.dest_folder_combo.get()

        if not source_text or not dest_text:
            self.copy_status_label.config(text="", foreground="blue")
            self.copy_button.config(state=tk.DISABLED)
            return

        source_id = int(source_text.split('[ID:')[1].split(']')[0])
        dest_id = int(dest_text.split('[ID:')[1].split(']')[0])

        source_folder = next((f for f in self.folders if f['id'] == source_id), None)
        dest_folder = next((f for f in self.folders if f['id'] == dest_id), None)

        source_level = next((l for l in self.levels if l['id'] == source_folder['level_id']), None)
        dest_level = next((l for l in self.levels if l['id'] == dest_folder['level_id']), None)

        source_context_rank = self.get_max_parent_level_rank(source_id)
        source_context_rank = max(source_context_rank, source_level['rank'])

        # Получаем максимальный ранг среди родителей папки назначения
        dest_context_rank = self.get_max_parent_level_rank(dest_id)
        dest_context_rank = max(dest_context_rank, dest_level['rank'])

        files = self.get_files_in_folder(source_id)

        # Bell-LaPadula с контекстом: исходный контекст должен быть <= целевому контексту
        can_copy = source_context_rank <= dest_context_rank

        if can_copy:
            self.copy_status_label.config(
                text=f"✓ Копирование разрешено (контекст: {source_context_rank} → {dest_context_rank}, файлов: {len(files)})")
            self.copy_button.config(state=tk.NORMAL if files else tk.DISABLED)
        else:
            self.copy_status_label.config(
                text=f"✗ Копирование запрещено: контекст источника выше целевого ({source_context_rank} > {dest_context_rank})")
            self.copy_button.config(state=tk.DISABLED)

    def copy_files(self):
        """Копирование файлов между папками"""
        source_text = self.source_folder_combo.get()
        dest_text = self.dest_folder_combo.get()

        source_id = int(source_text.split('[ID:')[1].split(']')[0])
        dest_id = int(dest_text.split('[ID:')[1].split(']')[0])

        source_path = self.get_folder_path(source_id)
        dest_path = self.get_folder_path(dest_id)

        files = self.get_files_in_folder(source_id)

        if not files:
            messagebox.showwarning("Предупреждение", "В исходной папке нет файлов")
            return

        try:
            copied = 0
            for file in files:
                shutil.copy2(file, dest_path / file.name)
                copied += 1

            messagebox.showinfo("Успех", f"Скопировано файлов: {copied}")
            self.refresh_all()
        except Exception as e:
            messagebox.showerror("Ошибка", f"Ошибка при копировании: {e}")

    def create_test_files(self):
        """Создание тестовых файлов"""
        folder_text = self.test_folder_combo.get()

        if not folder_text:
            messagebox.showerror("Ошибка", "Выберите папку")
            return

        folder_id = int(folder_text.split('[ID:')[1].split(']')[0])
        num_files = int(self.num_files_spin.get())

        path = self.get_folder_path(folder_id)

        try:
            for i in range(num_files):
                filename = f"test_file_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{i}.txt"
                filepath = path / filename
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(f"Тестовый файл\nСоздан: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

            messagebox.showinfo("Успех", f"Создано файлов: {num_files}")
            self.refresh_all()
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось создать файлы: {e}")

    # Обновление UI
    def refresh_all(self):
        """Обновление всех элементов интерфейса"""
        self.refresh_levels()
        self.refresh_folders()
        self.refresh_combos()
        self.validate_copy()

    def refresh_levels(self):
        """Обновление списка уровней"""
        for item in self.levels_tree.get_children():
            self.levels_tree.delete(item)

        for level in sorted(self.levels, key=lambda x: x['rank']):
            folders_count = len([f for f in self.folders if f['level_id'] == level['id']])
            self.levels_tree.insert('', tk.END, text=level['name'], 
                                   values=(level['rank'], folders_count),
                                   tags=(str(level['id']),))

    def refresh_folders(self):
        """Обновление дерева папок"""
        for item in self.folders_tree.get_children():
            self.folders_tree.delete(item)

        def add_folder(parent_id, tree_parent=''):
            folders = [f for f in self.folders if f['parent'] == parent_id]
            folders.sort(key=lambda x: x['name'])

            for folder in folders:
                level = next((l for l in self.levels if l['id'] == folder['level_id']), None)
                files = self.get_files_in_folder(folder['id'])
                path = self.get_folder_path(folder['id'])

                item = self.folders_tree.insert(tree_parent, tk.END, text=folder['name'],
                                               values=(level['name'] if level else '', len(files), str(path)),
                                               tags=(str(folder['id']),))
                add_folder(folder['id'], item)

        add_folder(None)

    def refresh_combos(self):
        """Обновление combobox'ов"""
        folder_options = []
        for folder in self.folders:
            level = next((l for l in self.levels if l['id'] == folder['level_id']), None)
            path_parts = []
            current = folder
            while current:
                path_parts.insert(0, current['name'])
                current = next((f for f in self.folders if f['id'] == current['parent']), None) if current['parent'] else None

            path = '/'.join(path_parts)
            option = f"{path} [{level['name']}] [ID:{folder['id']}]"
            folder_options.append(option)

        folder_options.sort()

        self.parent_folder_combo['values'] = ['Корневая папка'] + folder_options
        self.source_folder_combo['values'] = folder_options
        self.dest_folder_combo['values'] = folder_options
        self.test_folder_combo['values'] = folder_options

def main():
    root = tk.Tk()
    app = BellLaPadulaApp(root)
    root.mainloop()

if __name__ == '__main__':
    main()
