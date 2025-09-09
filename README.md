<a name="readme-top"></a>  
<div align="center"><img width="100%" src="https://github.com/megamen-x/praxis-core/blob/main/src/app/static/assets/praxis_banner.png" alt="product banner"></div>
<div align="center">
  <p align="center">
    <h1 align="center">Praxis Core</h1>
  </p>

  <p align="center">
    <p><strong>Turn feedback theory into actionable truth</strong></p>
    <br /><br />
  </p>
</div>

<center>

**Contents** |
:---:|
[Аннотация](#title1) |
[Описание](#title2) |
[Тестирование](#title3) |
[Обновления](#title4) |

</center>

## <h3 align="start"><a id="title1">Аннотация</a></h3> 
**Main theme of product development**

Актуальность данной темы связана с растущими требованиями к развитию персонала в условиях высокой конкурентной среды. Неэффективность традиционных методов сбора обратной связи, которые отнимают до 90% времени HR-менеджеров на рутинные задачи (рассылка, напоминания, агрегация данных), приводит к замедлению карьерного роста сотрудников, принятию необоснованных кадровых решений и, как следствие, к потере ключевых талантов и снижению продуктивности бизнеса. Потребность в быстром, объективном и глубоком анализе soft skills сотрудников highlights необходимость внедрения инновационных, автоматизированных решений в области управления персоналом.

**Разработанное решение может быть использовано для:**

* Автоматизации процесса сбора, анализа и представления обратной связи в корпоративной среде;
* Оптимизации бизнес-процессов в области управления эффективностью (Performance Management) и развития лидерских качеств.

**Задача подразумевает работу с текстовыми и числовыми данными от ревьюеров, поэтому решение включает несколько ключевых задач для обучения моделей:**

* Точное агрегирование количественных оценок и автоматическое формирование диаграмм Radar Chart;
* Анализ отзывов для выявления сильных сторон, зон роста и генерации персонализированных рекомендаций по развитию.

<p align="right">(<a href="#readme-top"><i>Back to top</i></a>)</p>

## <h3 align="start"><a id="title2">Описание</a></h3>

<h4 align="start"><a>Solution Architecture</a></h4>

<details>
  <summary> <strong><i>User interaction with the application</i></strong> </summary>

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
  <summary> <strong><i>Data processing sheme (WIP)</i></strong> </summary>

  ```mermaid
  
  ```
</details> 

<details>
  <summary> <strong><i>Current project tree</i></strong> </summary>

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


<h4 align="start"><a>FrontEnd & BackEnd</a></h4>

**Bootstrap5** В качестве основного стека разработки приложений был выбран, поскольку он обеспечивает:

- Простое масштабирование системы для растущих объемов данных;
- Кроссплатформенность, простое развертывание «из коробки»;
- Быстрая замена моделей глубокого обучения при необходимости;
- Вариативность анализа данных с помощью pandas, numpy и других.

[![Bootstrap5 Badge](https://img.shields.io/badge/Bootstrap-563D7C?style=for-the-badge&logo=bootstrap&logoColor=white&style=flat-square)](https://getbootstrap.com)
[![Telegram Badge](https://img.shields.io/badge/Telegram-2CA5E0?style=for-the-badge&logo=telegram&logoColor=white&style=flat-square)](https://web.telegram.org/)

**FastAPI** был выбран в качестве backend-фреймворка, поскольку он предоставляет:

- Высокую производительность, благодаря асинхронной работе;
- Простоту написания кода с поддержкой современных возможностей Python, таких как аннотации типов;
- Встроенную валидацию данных, сериализацию и обработку ошибок, что повышает надежность кода.

[![FastAPI Badge](https://img.shields.io/badge/FastAPI-005571?style=for-the-badge&logo=fastapi&style=flat-square)](https://fastapi.tiangolo.com)

<h4 align="start"><a>Data Base</a></h4>

**PostgreSQL** был выбран в качестве основной реляционной СУБД, так как он обеспечивает:

- Надежность, отказоустойчивость и строгую соответствие принципам ACID для целостности данных
- Богатый набор типов данных, включая JSONB для работы с полуструктурированными данными, и мощные расширения (PostGIS, Full-Text Search);
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

- Обеспечить идентичность сред разработки, тестирования и production, что исключает проблемы с совместимостью;
- Быстрое развертывание и масштабирование сервисов с помощью оркестраторов (например, Kubernetes);
- Упрощение управления зависимостями и конфигурацией приложения.


[![Docker Badge](https://img.shields.io/badge/docker-%230db7ed.svg?style=for-the-badge&logo=docker&logoColor=white&style=flat-square)](https://www.docker.com)


<h4 align="start"><a>Results (WIP)</a></h4>

Пример итогового отчета вы можете увидеть [здесь]()

<p align="right">(<a href="#readme-top"><i>Back to top</i></a>)</p>


## <h3 align="start"><a id="title3">Тестирование</a></h3> 

  <br />

<details>
  <summary> <strong><i>Локальный запуск решения (WIP):</i></strong> </summary>
  
  - В Visual Studio Code (**рекомендуется Windows-PowerShell**) через терминал последовательно выполните следующие команды:

    - Склонируйте репозиторий:
    ```
    git clone https://github.com/megamen-x/praxis-core.git
    ```
    - схема развертывания будет описана позже:
    ```
    тест-тест
    ```
</details> 

<!-- Additional instructions for installation and use can be found [here](https://github.com/megamen-x/praxis-core/blob/main/readme.md) and [there](https://github.com/megamen-x/praxis-core/blob/main/readme.md) -->

<p align="right">(<a href="#readme-top"><i>Back to top</i></a>)</p>

## <h3 align="start"><a id="title4">Обновления</a></h3> 

***ToDo list***
New feature | WIP | Done |
--- |:---:|:---:|
MVP 180° + base 360° | &#x2611; | &#x2611; | 
Advanced Analytics and Quality Control LLM | &#x2611; | &#x2610; | 
Integration with MAX messenger | &#x2611; | &#x2610; | 
Multi-tenant and enterprise-level compliance | &#x2610; | &#x2610; | 

<p align="right">(<a href="#readme-top"><i>Back to top</i></a>)</p>


<a name="readme-top"></a>
