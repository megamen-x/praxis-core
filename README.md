<div align="center">
  <p align="center">
    <h1 align="center">Praxis Core</h1>
  </p>
</div>
<div align="center"><img width="100%" src="https://github.com/megamen-x/praxis-core/blob/main/src/app/static/assets/praxis_banner.png" alt="product banner"></div>

<h1 align="center"> </h1>

<br /><br />

<center>

## **Содержание**
- [Введение](#title1)
- [Архитектура](#title2)
- [Технологии](#title3)
- [Deployment](#title4)
- [ToDo & WIP](#title5)
- [Команда](#title6)

</center>

## <h3 align="start"><a id="title1">Введение</a></h3> 
**Актуальность разработки продукта**

Актуальность данной темы связана с растущими требованиями к развитию персонала в условиях высокой конкурентной среды. Неэффективность традиционных методов сбора обратной связи, которые отнимают до 90% времени HR-менеджеров на рутинные задачи (рассылка, напоминания, агрегация данных), приводит к замедлению карьерного роста сотрудников, принятию необоснованных кадровых решений и, как следствие, к потере ключевых талантов и снижению продуктивности бизнеса. Потребность в быстром, объективном и глубоком анализе soft skills сотрудников highlights необходимость внедрения инновационных, автоматизированных решений в области управления персоналом.

**Разработанное решение может быть использовано для:**

* Автоматизации процесса сбора, анализа и представления обратной связи в корпоративной среде;
* Оптимизации бизнес-процессов в области управления эффективностью (Performance Management) и развития лидерских качеств.

**Задача подразумевает работу с текстовыми и числовыми данными от ревьюеров, поэтому решение включает несколько ключевых задач для обучения моделей:**

* Точное агрегирование количественных оценок и автоматическое формирование диаграмм Radar Chart;
* Анализ отзывов для выявления сильных сторон, зон роста и генерации персонализированных рекомендаций по развитию.

<p align="right">(<a href="#readme-top"><i>Вернуться наверх</i></a>)</p>

## <h3 align="start"><a id="title2">Архитектура</a></h3>

<details>
  <summary> <strong><i>Взаимодействие пользователя с приложением (WIP)</i></strong> </summary>

  ```mermaid
  sequenceDiagram
    actor Alice as HR
    actor Jonh as Employees
    participant TG Bot as Praxis-Bot
    participant Site as Praxis-Web

    Alice ->> TG Bot: User auth, new form create
    activate TG Bot
    TG Bot ->> Site: New Empty Form + Subject-User Data
    activate Site
    Site -->> Alice: Pre-filled Form
    Alice ->> Site: New data to Pre-filled Form
    Site -->> TG Bot: Filled Form
    TG Bot -->> Alice: Survey can be created
    Alice ->> TG Bot: Create Surveys and assignment  
    TG Bot ->> Site: Create Surveys from Filled Form
    Site -->> TG Bot: Empty Survey
    TG Bot -->> Jonh: Survey mailing
    Jonh ->> Site: Filled Survey
    Site -->> Site: LLM process
    Site -->> TG Bot: Overall Report
    deactivate Site
    TG Bot -->> Alice: Report is created
    deactivate TG Bot
  ```
</details> 

<details>
  <summary> <strong><i>Схема обработки данных</i></strong> </summary>

  ```mermaid
  classDiagram
    class Side {
        +String Качество
        +String Описание качества
        +String Объяснение выбора
        +Integer Количество отзывов
        +String[] Доказывающие фразы рецензентов
    }

    class SideRef {
        +String Описание рассматриваемого качества
        +String Классификация качества
    }

    class RecommendationItem {
        +String Описание
        +String Объяснение важности
        +String Рекомендация
    }

    class AmbiguousSide {
        +String Описание качества
        +String Объяснение причины
        +Integer Положительные отзывы
        +Integer Отрицательные отзывы
        +String[] Аргументы по положительным отзывам
        +String[] Аргументы по отрицательным отзывам
    }

    class Sides {
        +String[] Все качества человека из ответа ревьюеров
        +String Краткое резюме, основанное на всех качествах
    }

    class Recommendations {
        +RecommendationItem[] Список рекомендаций
        +String Глобальное примечание
    }

    Side --> SideRef
    SideRef --> RecommendationItem
    RecommendationItem --> Recommendations
    Side --> Sides
    Sides <-- AmbiguousSide
    
  ```
</details> 

<details>
  <summary> <strong><i>Текущее дерево проекта</i></strong> </summary>

  ```md
    praxis-core/
    ├── src/
    │   ├── db/
    │   │   ├── models/
    │   │   │   ├── __init__.py
    │   │   │   ├── answer.py
    │   │   │   ├── question.py
    │   │   │   ├── report.py
    │   │   │   ├── review.py
    │   │   │   ├── survey.py
    │   │   │   └── user.py
    │   │   ├── __init__.py
    │   │   └── session.py
    │   ├── app/
    │   │   ├── core/
    │   │   │   ├── config.py
    │   │   │   └── security.py
    │   │   ├── routers/
    │   │   │   ├── __init__.py
    │   │   │   ├── admin.py
    │   │   │   ├── surveys.py
    │   │   │   └── tg.py
    │   │   ├── schemas/
    │   │   │   ├── __init__.py
    │   │   │   ├── answer.py
    │   │   │   ├── common.py
    │   │   │   ├── question.py
    │   │   │   ├── review.py
    │   │   │   └── survey.py
    │   │   ├── services/
    │   │   │   ├── __init__.py
    │   │   │   └── links.py
    │   │   ├── static/
    │   │   │   ├── assets/
    │   │   │   │   └── site_bg_1.png
    │   │   │   ├── css/
    │   │   │   │   └── style.css
    │   │   │   └── js/
    │   │   │       └── form.js
    │   │   ├── templates/
    │   │   │   ├── admin_edit.html
    │   │   │   ├── base.html
    │   │   │   ├── form.html
    │   │   │   └── thanks.html
    │   │   └── main.py
    │   └── tg_bot/
    │       ├── __init__.py
    │       └── main.py
    └── pyproject.toml
  ```
</details> 

<br>

<h4 align="start"><a>Примеры отчетов, сгенерированных системой (WIP)</a></h4>

Пример итогового отчета вы можете увидеть [здесь]()

<p align="right">(<a href="#readme-top"><i>Вернуться наверх</i></a>)</p>

## <h3 align="start"><a id="title3">Технологии</a></h3>

<h4 align="start"><a>FrontEnd & BackEnd</a></h4>

**Bootstrap5** был выбран в качестве основного инструмента FrontEnd, поскольку он обеспечивает:

- Простоту и удобство пользовательской части решения.
- Кроссплатформенность, простое развертывание «из коробки»;
- Быструю замену компонентов и работу с популярными шаблонизаторами, в нашем случае Jinja;

Использовали [**Telegram-бота**](https://t.me/praxis_core_bot) для верификации (аутентификации) сотрудников, а также рассылки напоминаний.

[![Bootstrap5 Badge](https://img.shields.io/badge/Bootstrap-563D7C?style=for-the-badge&logo=bootstrap&logoColor=white&style=flat-square)](https://getbootstrap.com)
[![Telegram Badge](https://img.shields.io/badge/Telegram-2CA5E0?style=for-the-badge&logo=telegram&logoColor=white&style=flat-square)](https://web.telegram.org/)

**FastAPI** был выбран в качестве backend-фреймворка, поскольку он предоставляет:

- Простоту интеграции новых функций;
- Высокую производительность, благодаря асинхронной работе;
- Встроенную валидацию данных, сериализацию и обработку ошибок.

[![FastAPI Badge](https://img.shields.io/badge/FastAPI-005571?style=for-the-badge&logo=fastapi&style=flat-square)](https://fastapi.tiangolo.com)

<h4 align="start"><a>Data Base</a></h4>

**PostgreSQL** был выбран в качестве основной реляционной СУБД, так как он обеспечивает:

- Богатый набор типов данных и удобство интеграции с асинхронными процессами FastAPI;
- Надежность, отказоустойчивость и строгую соответствие принципам ACID для целостности данных;
- Высокую производительность и масштабируемость для больших объемов данных и сложных нагрузок;
- Соответствие SQL-стандартам и развитую экосистему инструментов для администрирования и миграций

[![SQL Badge](https://img.shields.io/badge/postgres-%23316192.svg?style=for-the-badge&logo=postgresql&logoColor=white&style=flat-square)](https://www.postgresql.org)

<h4 align="start"><a>Data Processing (WIP)</a></h4>

Был использован Schema-guided reasoning для:
- Анализа противоречивых отзывов;
- Генерации траектории развития сотрудника;

Реализована автоматизированная генерация отчетов с помощью Jinja2.

[![Python Badge](https://img.shields.io/badge/Python-3776AB?logo=python&logoColor=fff&style=flat-square)](https://www.python.org/)

<h4 align="start"><a>Deployment</a></h4>

**Docker** был выбран для контейнеризации и развертывания, так как он позволяет:

- Упрощение управления зависимостями и конфигурацией приложения.
- Быстрое развертывание и масштабирование сервисов с помощью оркестраторов (например, Kubernetes);
- Обеспечить идентичность сред разработки, тестирования и production, что исключает проблемы с совместимостью;

[![Docker Badge](https://img.shields.io/badge/docker-%230db7ed.svg?style=for-the-badge&logo=docker&logoColor=white&style=flat-square)](https://www.docker.com)

## <h3 align="start"><a id="title4">Тестирование</a></h3> 

  <br />

<details>
  <summary> <strong><i>Локальный запуск решения:</i></strong> </summary>
  
  - В Visual Studio Code (**протестировано через WSL2**) через терминал последовательно выполните следующие команды:

    - Склонируйте репозиторий:
    ```
    git clone https://github.com/megamen-x/praxis-core.git
    ```
    - Загрузите PostgreSQL:
    ```
    sudo apt update
    sudo apt install postgresql postgresql-contrib
    sudo -u postgres psql
    ```
    - Создайте базу данных и пользователя:
    ```
    CREATE DATABASE praxis_db;
    CREATE USER praxis_user WITH PASSWORD 'your_secure_password';
    GRANT ALL PRIVILEGES ON DATABASE praxis_db TO praxis_user;
    ```
    - Создайте окружение и установите зависимости проекта:
    ```
    python -m venv .venv
    source .venv/bin/activate
    pip install -e .
    ```
    - В файле .env добавьте привязку к PostgreSQL:
    ```
    DATABASE_URL=postgresql://praxis_user:your_secure_password@localhost:5432/praxis_db
    ```
    - После окончания предыдущих этапов можно запустить сервер:
    ```
    uvicorn src.app.main:app --reload --host 0.0.0.0 --port 8000
    ```

</details> 

<details>
  <summary> <strong><i>Запуск при помощи docker compose</i></strong> </summary>

  - Выполните в терминале следующие команды:
  
    - Если у вас нет базы данных PostgreSQL, запустите код следующим образом, предварительно указав в файле ``docker-compose.yml`` имя пользователя, пароль, порт и название базы данных:
    ```
    docker-compose up
    ```
    - Если у вас уже создана и настроена локальная база данных PostgreSQL, запустите код через следующую команду. Укажите в файле ``docker-compose-local-db.yml`` корректный URI-путь до базы данных. 
    ```
    docker-compose -f docker-compose-local-db.yml up
    ```
</details>

<!-- Additional instructions for installation and use can be found [here](https://github.com/megamen-x/praxis-core/blob/main/readme.md) and [there](https://github.com/megamen-x/praxis-core/blob/main/readme.md) -->

<p align="right">(<a href="#readme-top"><i>Вернуться наверх</i></a>)</p>

## <h3 align="start"><a id="title6">ToDo & WIP</a></h3> 

***ToDo list***
New feature | WIP | Done |
--- |:---:|:---:|
MVP 180° + base 360° | &#x2611; | &#x2611; | 
Расширенная аналитика и контроль качества LLM | &#x2611; | &#x2610; | 
AI-помощник для создания умных и креативных опросов | &#x2611; | &#x2610; | 
Соответствие требованиям корпоративного уровня | &#x2610; | &#x2610; | 

<p align="right">(<a href="#readme-top"><i>Вернуться наверх</i></a>)</p>

## <h3 align="start"><a id="title5">Команда</a></h3> 

- [Луняков Алексей](https://github.com/AlexeyLunyakov) - UX\UI, Full-Stack / Research Engineer
- [Калинин Александр](https://github.com/Agar1us) - TL, DL / Full-Stack Engineer
- [Полетаев Владислав](https://github.com/whatisslove11) - ML / DL Engineer
- [Чуфистов Георгий](https://github.com/georgechufff) - ML / DL Engineer, ML Ops

<p align="right">(<a href="#readme-top"><i>Вернуться наверх</i></a>)</p>

<a name="readme-top"></a>
