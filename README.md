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
[Abstract](#title1) |
[Description](#title2) |
[Testing and Deployment](#title3) |
[Updates](#title4) |

</center>

## <h3 align="start"><a id="title1">Abstract</a></h3> 
**Main theme of product development**

The relevance of this topic is associated with smth idk lol xd.

**The developed solution can be used to:**
* usage varian 1;
* usage varian 1.

**The task involves working with real working environment, so the solution includes several key tasks:**
* smth about tg bot user experience;
* smth about own web-forms.

<p align="right">(<a href="#readme-top"><i>Back to top</i></a>)</p>

## <h3 align="start"><a id="title2">Description</a></h3>

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
  <summary> <strong><i>Data processing sheme</i></strong> </summary>

  ```mermaid
  
  ```
</details> 

<details>
  <summary> <strong><i>Current project tree</i></strong> </summary>

  ```python
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

**Bootstrap5** was chosen as the main application development stack, as it provides the solution with:
- Easy scaling of the system for growing data volumes;
- Cross-platform, easy deployment right out of the box;
- Quick replacement of deep learning models if necessary;
- Variability of data analysis with pandas, numpy and others.

[![Bootstrap5 Badge](https://img.shields.io/badge/Bootstrap-563D7C?style=for-the-badge&logo=bootstrap&logoColor=white&style=flat-square)](https://getbootstrap.com)
[![Telegram Badge](https://img.shields.io/badge/Telegram-2CA5E0?style=for-the-badge&logo=telegram&logoColor=white&style=flat-square)](https://web.telegram.org/)

**FastAPI** was chosen as it provides the solution with:
- napisat'.

[![FastAPI Badge](https://img.shields.io/badge/FastAPI-005571?style=for-the-badge&logo=fastapi&style=flat-square)](https://fastapi.tiangolo.com)






<h4 align="start"><a>Data Base</a></h4>

smth about postgresql and his improvements


[![SQL Badge](https://img.shields.io/badge/postgres-%23316192.svg?style=for-the-badge&logo=postgresql&logoColor=white&style=flat-square)](https://www.postgresql.org)


<h4 align="start"><a>Data Processing</a></h4>

smth about data processing and report generations with jinja


[![Python Badge](https://img.shields.io/badge/Python-3776AB?logo=python&logoColor=fff&style=flat-square)](https://www.python.org/)


<h4 align="start"><a>Deployment</a></h4>

smth about docker compose


[![Docker Badge](https://img.shields.io/badge/docker-%230db7ed.svg?style=for-the-badge&logo=docker&logoColor=white&style=flat-square)](https://www.docker.com)


<h4 align="start"><a>Results</a></h4>

Final Report example you can see [here]()

<p align="right">(<a href="#readme-top"><i>Back to top</i></a>)</p>


## <h3 align="start"><a id="title3">Testing and Deployment</a></h3> 

  <br />

<details>
  <summary> <strong><i>Testing models with an Inference app:</i></strong> </summary>
  
  - In Visual Studio Code (**Windows-PowerShell recommended**) through the terminal, run the following commands sequentially:

    - Clone the repository:
    ```
    git clone https://github.com/AlexeyLunyakov/SAFE-MACS.git
    ```
    - Create your parent directory for docker-machine results output:
    ```
    mkdir -p docker_files
    ```
    - Image build:
    ```
    docker build -t cv-app -f Dockerfile.gpu .
    ```
    - After installing the dependencies (3-5 minutes), you can run Container with GPU:
    ```
    docker run -d --gpus all -p 7860:7860 -v "$(pwd)/docker_files:/app/files" --name cv-container cv-app
    ```
    or with CPU-only:
    ```
    docker build -t cv-app -f Dockerfile.cpu .
    docker run -p 7861:7860 -v "$(pwd)/docker_files:/app/files" --name cv-container cv-app
    ```
</details> 

Additional instructions for installation and use can be found [here](https://github.com/megamen-x/praxis-core/blob/main/readme.md) and [there](https://github.com/megamen-x/praxis-core/blob/main/readme.md)

<p align="right">(<a href="#readme-top"><i>Back to top</i></a>)</p>

## <h3 align="start"><a id="title4">Updates</a></h3> 

***ToDo list***
New feature | WIP | Done |
--- |:---:|:---:|
MVP 180° + base 360° | &#x2611; | &#x2611; | 
Advanced Analytics and Quality Control LLM | &#x2611; | &#x2610; | 
Integration with MAX messenger | &#x2611; | &#x2610; | 
Multi-tenant and enterprise-level compliance | &#x2610; | &#x2610; | 

<p align="right">(<a href="#readme-top"><i>Back to top</i></a>)</p>


<a name="readme-top"></a>
