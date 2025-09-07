import psycopg2
from psycopg2 import sql
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

def recreate_database():
    # Параметры подключения (замените на свои)
    db_params = {
        'host': 'localhost',
        'port': '5432',
        'user': 'postgres',
        'password': 'qwerty',  # замените на ваш пароль
        'database': 'postgres'  # подключаемся к системной БД
    }
    
    try:
        # Подключаемся к системной БД postgres
        print("Подключение к PostgreSQL...")
        conn = psycopg2.connect(**db_params)
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()
        
        # Проверяем существование базы данных
        cursor.execute("SELECT 1 FROM pg_database WHERE datname = 'praxis_db'")
        exists = cursor.fetchone()
        
        if exists:
            # Завершаем все активные подключения к БД
            print("Завершение активных подключений к praxis_db...")
            cursor.execute("""
                SELECT pg_terminate_backend(pg_stat_activity.pid)
                FROM pg_stat_activity
                WHERE pg_stat_activity.datname = 'praxis_db'
                AND pid <> pg_backend_pid();
            """)
            
            # Удаляем базу данных
            print("Удаление базы данных praxis_db...")
            cursor.execute(sql.SQL("DROP DATABASE IF EXISTS praxis_db"))
            print("База данных praxis_db удалена")
        
        # Создаем новую базу данных
        print("Создание базы данных praxis_db...")
        cursor.execute(sql.SQL("CREATE DATABASE praxis_db"))
        print("База данных praxis_db создана успешно!")
        
        # Закрываем соединение
        cursor.close()
        conn.close()
        print("Операция завершена успешно!")
        
    except psycopg2.Error as e:
        print(f"Ошибка при работе с базой данных: {e}")
    except Exception as e:
        print(f"Неожиданная ошибка: {e}")

if __name__ == "__main__":
    recreate_database()