import sqlite3

class Database:
    """
    Класс для ленивых: управление SQLite без SQL-боли.
    Автоматически экранирует данные, защищая от инъекций.
    """
    def __init__(self, db_file="database.db"):
        self.db_file = db_file
        self.conn = None
        self.cursor = None

    # ==========================================
    # Магия Context Manager (для оператора with)
    # ==========================================
    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    # ==========================================
    # Базовые методы
    # ==========================================
    def connect(self):
        """Открывает соединение."""
        self.conn = sqlite3.connect(self.db_file)
        # Позволяет обращаться к колонкам по имени (row['name']), а не по индексу (row[0])
        self.conn.row_factory = sqlite3.Row 
        self.cursor = self.conn.cursor()

    def close(self):
        """Сохраняет и закрывает."""
        if self.conn:
            self.conn.commit()
            self.conn.close()

    def commit(self):
        """Принудительное сохранение."""
        if self.conn:
            self.conn.commit()

    # ==========================================
    # Основной функционал
    # ==========================================
    
    def create_table(self, table_name: str, columns: dict):
        """
        Создает таблицу.
        columns: словарь вида {'name': 'TEXT', 'age': 'INTEGER'}
        """
        # Собираем строку "name TEXT, age INTEGER"
        cols = ", ".join([f"{k} {v}" for k, v in columns.items()])
        query = f"CREATE TABLE IF NOT EXISTS {table_name} (id INTEGER PRIMARY KEY AUTOINCREMENT, {cols})"
        self.cursor.execute(query)
        self.commit()

    def add(self, table_name: str, data: dict):
        """
        Добавляет запись.
        data: {'login': 'admin', 'pass': '123'}
        """
        keys = ", ".join(data.keys())
        # Создаем строку вопросов: "?, ?, ?"
        placeholders = ", ".join(["?"] * len(data))
        
        query = f"INSERT INTO {table_name} ({keys}) VALUES ({placeholders})"
        self.cursor.execute(query, list(data.values()))
        self.commit()
        return self.cursor.lastrowid # Возвращает ID новой записи

    def get(self, table_name: str, criteria: dict = None):
        """
        Получает ОДНУ запись по критериям.
        criteria: {'id': 5} или {'login': 'root'}
        """
        query = f"SELECT * FROM {table_name}"
        params = []
        
        if criteria:
            # Собираем "WHERE key1=? AND key2=?"
            conditions = " AND ".join([f"{k}=?" for k in criteria.keys()])
            query += f" WHERE {conditions}"
            params = list(criteria.values())
        
        self.cursor.execute(query, params)
        row = self.cursor.fetchone()
        # Превращаем результат в обычный словарь
        return dict(row) if row else None

    def get_all(self, table_name: str, criteria: dict = None):
        """
        Получает ВСЕ записи (списком словарей).
        """
        query = f"SELECT * FROM {table_name}"
        params = []
        
        if criteria:
            conditions = " AND ".join([f"{k}=?" for k in criteria.keys()])
            query += f" WHERE {conditions}"
            params = list(criteria.values())
            
        self.cursor.execute(query, params)
        rows = self.cursor.fetchall()
        return [dict(row) for row in rows]

    def update(self, table_name: str, new_data: dict, criteria: dict):
        """
        Обновляет данные.
        new_data: что меняем {'status': 'banned'}
        criteria: у кого меняем {'id': 15}
        """
        # "SET name=?, age=?"
        set_str = ", ".join([f"{k}=?" for k in new_data.keys()])
        # "WHERE id=?"
        where_str = " AND ".join([f"{k}=?" for k in criteria.keys()])
        
        query = f"UPDATE {table_name} SET {set_str} WHERE {where_str}"
        
        # Объединяем значения для SET и для WHERE
        params = list(new_data.values()) + list(criteria.values())
        
        self.cursor.execute(query, params)
        self.commit()

    def delete(self, table_name: str, criteria: dict):
        """
        Удаляет записи.
        criteria: {'id': 5}
        """
        conditions = " AND ".join([f"{k}=?" for k in criteria.keys()])
        query = f"DELETE FROM {table_name} WHERE {conditions}"
        self.cursor.execute(query, list(criteria.values()))
        self.commit()

    def execute_raw(self, sql: str):
        """
        Если вдруг захочется хардкора (чистый SQL).
        """
        self.cursor.execute(sql)
        self.commit()