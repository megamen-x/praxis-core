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
    
        # Параметры нового пользователя
    new_user = 'praxis_user'
    new_password = 'root'  # замените на безопасный пароль
    new_database = 'praxis_db'

    try:
        print("Подключение к PostgreSQL (системная БД)...")
        conn = psycopg2.connect(**db_params)
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()

        # --- Удаление существующей БД (если есть) ---
        cursor.execute("SELECT 1 FROM pg_database WHERE datname = %s", (new_database,))
        if cursor.fetchone():
            print(f"Завершение подключений к {new_database}...")
            cursor.execute("""
                SELECT pg_terminate_backend(pg_stat_activity.pid)
                FROM pg_stat_activity
                WHERE datname = %s;
            """, (new_database,))

            print(f"Удаление базы данных {new_database}...")
            cursor.execute(sql.SQL("DROP DATABASE IF EXISTS {}").format(
                sql.Identifier(new_database)
            ))
            print(f"База данных {new_database} удалена.")

        # --- Удаление существующего пользователя (если есть) ---
        cursor.execute("SELECT 1 FROM pg_roles WHERE rolname = %s", (new_user,))
        if cursor.fetchone():
            print(f"Удаление пользователя {new_user}...")
            cursor.execute(sql.SQL("DROP USER IF EXISTS {}").format(
                sql.Identifier(new_user)
            ))
            print(f"Пользователь {new_user} удалён.")

        # --- Создание новой БД ---
        print(f"Создание базы данных {new_database}...")
        cursor.execute(sql.SQL("CREATE DATABASE {}").format(
            sql.Identifier(new_database)
        ))
        print(f"База данных {new_database} создана.")

        # --- Создание нового пользователя ---
        print(f"Создание пользователя {new_user}...")
        cursor.execute(sql.SQL("CREATE USER {} WITH PASSWORD %s").format(
            sql.Identifier(new_user)
        ), (new_password,))
        print(f"Пользователь {new_user} создан.")

        # --- Назначение прав ---
        print(f"Назначение прав пользователю {new_user} на {new_database}...")
        cursor.execute(sql.SQL("GRANT ALL PRIVILEGES ON DATABASE {} TO {}").format(
            sql.Identifier(new_database),
            sql.Identifier(new_user)
        ))
        print(f"Права назначены успешно!")

        # --- Дополнительно: права на схему public (опционально) ---
        # Подключаемся к новой БД, чтобы назначить права на схему public
        conn_temp = psycopg2.connect(
            host=db_params['host'],
            port=db_params['port'],
            user=db_params['user'],
            password=db_params['password'],
            database=new_database
        )
        conn_temp.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor_temp = conn_temp.cursor()

        cursor_temp.execute(sql.SQL("GRANT ALL PRIVILEGES ON SCHEMA public TO {}").format(
            sql.Identifier(new_user)
        ))
        cursor_temp.execute(sql.SQL("GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO {}").format(
            sql.Identifier(new_user)
        ))
        cursor_temp.execute(sql.SQL("GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO {}").format(
            sql.Identifier(new_user)
        ))

        conn_temp.close()
        print("Права на схему public назначены.")

        cursor.close()
        conn.close()
        print("Настройка завершена успешно!")

    except psycopg2.Error as e:
        print(f"Ошибка PostgreSQL: {e}")
    except Exception as e:
        print(f"Неожиданная ошибка: {e}")


if __name__ == "__main__":
    recreate_database()