# Hacathon Template

Это шаблон проекта для хакатонов на Python.

## Требования

- Python 3.8+
- pip (менеджер пакетов Python)

## Установка

### 1. Клонирование репозитория

```bash
git clone https://github.com/5PSIXDISPANCER/hacathon_template.git
cd hacathon_template
```

### 2. Создание виртуального окружения

#### На Linux/macOS:

```bash
python3 -m venv venv
source venv/bin/activate
```

#### На Windows:

```bash
python -m venv venv
venv\Scripts\activate
```

### 3. Установка зависимостей

```bash
pip install -r requirements.txt
```

## Запуск проекта

```bash
python main.py
```

## Структура проекта

```
hacathon_template/
├── main.py           # Основной файл проекта
├── requirements.txt   # Зависимости проекта
└── README.md         # Этот файл
```

## Возможные проблемы

### ModuleNotFoundError

Если вы получаете ошибку `ModuleNotFoundError`, убедитесь, что:

1. Виртуальное окружение активировано
2. Все зависимости установлены: `pip install -r requirements.txt`

### Permission denied (на Linux/macOS)

Если скрипт не запускается, добавьте права на выполнение:

```bash
chmod +x main.py
```

## Разработка

Для добавления новых зависимостей:

1. Установите пакет: `pip install package_name`
2. Обновите requirements.txt: `pip freeze > requirements.txt`
3. Добавьте изменения в git

## Лицензия

Этот проект распространяется свободно.

## Помощь

Если у вас есть вопросы, создайте issue в репозитории.
