Видимо, ты решил всё-таки помочь с проектом, раз зашёл сюда. Сейчас подскажу, что да как.

## Установка
Рекомендуемая версия питона: 3.9 \
Минимальная (но это не точно): 3.6
```
python3 -m pip install poetry
poetry install
poetry run pre-commit install
```

## Отправка изменений
Понятно, что делаем fork проекта и уже у себя делаем все изменения.

Когда делаешь `git commit`, то все изменения проверяются (линтеры, типизация).
Если он не сделался с первого раза, то, скорее всего, он автоматически что-то подправил.
Если со второго раза тоже появляется ошибка, то смотрим на ошибку и разбираемся.

Если всё готово, делаем push. Я проверяю и отправляю изменения на сервер.

## Вопросы?
Пиши мне в vk или в tg (todo)