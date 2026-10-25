# Курсовая работа №1

## Вступление
Курсовая работа №1 состоит в разработке приложения для анализа транзакций, 
которые находятся в Excel-файле. Приложение должно генерировать JSON-данные для
веб-страниц, формировать Excel-отчеты, а также предоставлять другие сервисы.

## Условия выполнения
Задачи по категориям:
1. Веб-страницы:
   - Главная
   - События
2. Сервисы:
   - Выгодные категории повышенного кешбэка
   - Инвесткопилка
   - Простой поиск
   - Поиск по телефонным номерам
   - Поиск переводов физическим лицам
3. Отчеты:
   - Траты по категории
   - Траты по дням недели
   - Траты в рабочий/выходной день

### Функциональные требования
#### Веб-страницы
Основные функции для генерации JSON-ответов реализуйте в отдельном модуле 
`views.py`.

##### Страница «Главная»
Реализуйте набор функций и главную функцию, принимающую на вход строку с датой 
и временем в формате `YYYY-MM-DD HH:MM:SS` и возвращающую JSON-ответ 
со следующими данными:
1. Приветствие в формате "???", где 
??? — «Доброе утро» / «Добрый день» / «Добрый вечер» / «Доброй ночи» в 
зависимости от текущего времени.
2. По каждой карте:
    - последние 4 цифры карты;
    - общая сумма расходов;
    - кешбэк (1 рубль на каждые 100 рублей).
3. Топ-5 транзакций по сумме платежа.
4. Курс валют.
5. Стоимость акций из S&P500.

##### Страница «События»
Реализуйте набор функций и главную функцию, принимающую на вход строку с датой 
и второй необязательный параметр — диапазон данных. По умолчанию диапазон 
равен одному месяцу (с начала месяца, на который выпадает дата, по саму дату).

Возможные значения второго необязательного параметра:
- `W` — неделя, на которую приходится дата;
- `M` — месяц, на который приходится дата;
- `Y` — год, на который приходится дата;
- `ALL` — все данные до указанной даты.

Возвращаемый JSON-ответ содержит следующие данные:
1. «Расходы»:
   - Общая сумма расходов.
   - Раздел «Основные», в котором траты по категориям отсортированы по убыванию. Данные предоставляются по 7 категориям с наибольшими тратами, траты по остальным категориям суммируются и попадают в категорию «Остальное».
   - Раздел «Переводы и наличные», в котором сумма по категориям «Наличные» и «Переводы» отсортирована по убыванию.
2. «Поступления»:
    - Общая сумма поступлений.
    - Раздел «Основные», в котором поступления по категориям отсортированы по убыванию.
3. Курс валют.
4. Стоимость акций из S&P 500.

#### Сервисы
Реализуйте сервисы в отдельном модуле `services.py`.
При реализации сервисов должны использоваться элементы функционального 
программирования.

##### Выгодные категории повышенного кешбэка
Сервис позволяет проанализировать, какие категории были наиболее выгодными 
для выбора в качестве категорий повышенного кешбэка.

##### Инвесткопилка
Позволяет копить через округление ваших трат.
Можно задать комфортный порог округления: 10, 50 или 100 ₽. Траты будут 
округляться, и разница между фактической суммой трат по карте и суммой 
округления будет попадать на счет «Инвесткопилки».

##### Простой поиск
Пользователь передает строку для поиска, возвращается JSON-ответ со всеми 
транзакциями, содержащими запрос в описании или категории.

###### Поиск по телефонным номерам
Функция возвращает JSON со всеми транзакциями, содержащими в описании 
мобильные номера.

###### Поиск переводов физическим лицам
Функция возвращает JSON со всеми транзакциями, которые относятся к переводам 
физлицам.

Категория такой транзакции — `Переводы`, а в описании есть имя и первая буква 
фамилии с точкой.

#### Отчеты
Реализуйте отчеты в отдельном модуле `reports.py`.
Создайте декоратор для функций-отчетов, который записывает в файл результат, 
который возвращает функция, формирующая отчет.
- Декоратор без параметра — записывает данные отчета в файл с названием 
по умолчанию (формат имени файла придумайте самостоятельно).
- Декоратор с параметром — принимает имя файла в качестве параметра.

##### Траты по категории
Функция принимает на вход:
- датафрейм с транзакциями,
- название категории,
- опциональную дату.

Если дата не передана, то берется текущая дата.

Функция возвращает траты по заданной категории за последние три месяца 
(от переданной даты).

##### Траты по дням недели
Функция принимает на вход:
- датафрейм с транзакциями,
- опциональную дату.

Если дата не передана, то берется текущая дата.

Функция возвращает средние траты в каждый из дней недели за последние 
три месяца (от переданной даты).

##### Траты в рабочий/выходной день
Функция принимает на вход:
- датафрейм с транзакциями
- опциональную дату.

Если дата не передана, то берется текущая дата.

Функция выводит средние траты в рабочий и в выходной день за последние 
три месяца (от переданной даты).

## Возможности
- Получение актуальных курсов валют через API из внешнего источника.
- Получение актуальных котировок акций через API из внешнего источника.
- Загрузка транзакций из Excel и настроек из JSON.
- Логирование работы модулей и возникающих ошибок.
- Автоматизированное тестирование с помощью `pytest`.
- Контроль покрытия строк и ветвлений с помощью `pytest-cov`.

## Структура проекта
```text
.
├── configs/
│   ├── field_aliases.json
│   └── user_settings.json
├── data/
│   └── operations.xlsx
├── htmlcov/
├── logs/
├── reports/
├── src/
│   ├── __init__.py
│   ├── api_responses.py
│   ├── currencies.py
│   ├── fields.py
│   ├── processing_services.py
│   ├── processing_views.py
│   ├── readers.py
│   ├── reports.py
│   ├── services.py
│   ├── stocks.py
│   └── views.py
├── tests/
│   ├── __init__.py
│   ├── test_api_responses.py
│   ├── test_currencies.py
│   ├── test_fields.py
│   ├── test_processing_services.py
│   ├── test_processing_views.py
│   ├── test_readers.py
│   ├── test_reports.py
│   ├── test_services.py
│   ├── test_stocks.py
│   └── test_views.py
├── .coverage
├── .env.example
├── .flake8
├── .gitignore
├── poetry.lock
├── pyproject.toml
├── poetry.toml
└── README.md
```
## Требования
- Python 3.12 или новее;
- Poetry 2.x;
- Git — для клонирования проекта с GitHub.

Проверить установленные версии можно командами:

```shell
python --version
poetry --version
git --version
```

## Установка проекта с GitHub

1. На странице репозитория GitHub нажмите **Code** и скопируйте HTTPS-адрес.
2. Клонируйте репозиторий, заменив `USERNAME/REPOSITORY` на данные проекта:

   ```shell
   git clone https://github.com/USERNAME/REPOSITORY.git
   ```

3. Перейдите в каталог проекта:

   ```shell
   cd REPOSITORY
   ```

4. Установите зависимости из `poetry.lock`:

   ```shell
   poetry install
   ```

5. Проверьте, что проект работает:

   ```shell
   poetry run pytest
   ```

Поскольку GitHub-адрес ещё не привязан к текущему локальному репозиторию,
`USERNAME/REPOSITORY` в примерах необходимо заменить на реальный адрес после
публикации проекта.

## Реализация условий

### Модуль `api_responses`
Модуль `src.api_responses` содержит общие функции для обращения к внешним API.
При загрузке читаются переменные окружения из `.env`, создаётся каталог
`logs` и настраивается журнал. Тайм-аут HTTP-запроса равен 10 секундам.

#### `get_api_key`

~~~python
get_api_key(code_key: str) -> str | None
~~~

Получает имя переменной окружения `code_key`. Возвращает найденный API-ключ.
Если переменная отсутствует или пуста, записывает ошибку и возвращает `None`.

#### `get_response`

~~~python
get_response(
    url: str,
    params: dict[str, str | float],
) -> Any | None
~~~

Получает адрес API и параметры запроса. Выполняет GET-запрос и возвращает
декодированный JSON-объект в виде словаря. Если тело не является JSON или его
корневое значение не является словарём, возвращает `None`. Исключения
сетевого запроса передаются вызывающему коду.

#### Логирование
Сообщения записываются в `logs/api_responses.log`. Журнал содержит сведения
об отсутствующих ключах и некорректных ответах API.

### Модуль `currencies`
Модуль `src.currencies` получает курсы из ExchangeRate-API и формирует
котировки валют, указанных в `configs/user_settings.json`.

#### `_get_currency_rates_from_api`

~~~python
_get_currency_rates_from_api(
    currency_quote: str,
) -> dict[str, Any] | None
~~~

Получает код базовой валюты, формирует URL API и возвращает словарь `rates`.
При сетевой ошибке, пустом ответе, ошибке API или неверном формате `rates`
возвращает `None`.

#### `_calculate_currency_quote`

~~~python
_calculate_currency_quote(
    currency: str,
    currency_rates: dict[str, Any],
    digit: int,
) -> dict[str, Any] | None
~~~

Получает код валюты, словарь курсов и точность. Рассчитывает обратный курс
`1 / rate` и возвращает `{"currency": currency, "rate": value}`. При
отрицательной точности, отсутствующем, нечисловом, логическом, нулевом или
отрицательном курсе возвращает `None`.

#### `_build_currency_quotes`

~~~python
_build_currency_quotes(
    user_currencies: list[str],
    currency_rates: dict[str, Any],
    digit: int,
) -> list[dict[str, Any]]
~~~

Вызывает `_calculate_currency_quote` для каждой пользовательской валюты.
Корректные результаты добавляет в список, ошибочные значения пропускает.

#### `get_currency_rates`

~~~python
get_currency_rates() -> list[dict[str, Any]] | None
~~~

Загружает пользовательские валюты и базовую валюту, получает исходные курсы,
рассчитывает обратные котировки с точностью два знака и возвращает список
словарей с полями `currency` и `rate`. При ошибке настроек, пустых
параметрах, недоступности API или отсутствии корректных котировок возвращает
`None`.

#### Логирование
Сообщения записываются в `logs/currencies.log`: запросы к API, ошибки
настроек, некорректные курсы и итоговые котировки.

### Модуль `fields`
Модуль `src.fields` получает значения из словарей по ключам и вложенным путям,
работает со справочником псевдонимов и загружает настройки. Соответствие
внутренних полей столбцам хранится в `configs/field_aliases.json`.

#### `get_by_path`

~~~python
get_by_path(
    item: Mapping[str, Any],
    path: str,
) -> Any
~~~

Получает отображение и буквальный ключ либо путь с частями через точку.
Буквальный ключ имеет приоритет: для `currency.code` сначала проверяется ключ
с полным именем, затем `{"currency": {"code": ...}}`. Если значение не
найдено, создаётся `KeyError`.

#### `get_field_value`

~~~python
get_field_value(
    transaction: Mapping[str, Any],
    field_name: str,
    field_aliases: Mapping[str, list[str]],
) -> Any
~~~

Получает транзакцию, внутреннее имя поля и справочник псевдонимов. Проверяет
пути по порядку и возвращает первое найденное значение. Если поле отсутствует
в справочнике или транзакции, возвращает пустой список.

#### `load_user_settings`

~~~python
load_user_settings(
    file_path: str | Path,
) -> tuple[list[str], list[str], str]
~~~

Загружает обязательные поля `user_currencies`, `user_stocks` и
`user_currency_quote`. Возвращает кортеж: список валют, список тикеров и код
базовой валюты. Ошибки структуры `KeyError` и `TypeError` обрабатывает
вызывающий код.

#### `load_fields`

~~~python
load_fields(file_path: str | Path) -> Any
~~~

Передаёт путь функции `get_fields_from_json` и возвращает загруженный
справочник без дополнительного преобразования. Ошибка чтения приводит к
пустому списку, возвращаемому модулем `readers`.

#### Логирование
Сообщения записываются в `logs/fields.log`: отсутствующие ключи, вложенные
пути и ошибки справочника.

### Модуль `readers`
Модуль `src.readers` читает транзакции из Excel и конфигурационные словари из
JSON.

#### `get_transactions_from_xls`

~~~python
get_transactions_from_xls(
    file_path: str | Path,
) -> list[dict[str, Any]]
~~~

Читает лист `Отчет по операциям`. Названия столбцов становятся ключами
словаря, строки — транзакциями. Полностью пустые и пробельные строки
пропускаются. При пустом листе, отсутствии или повреждении файла, неверном
листе либо отсутствии движка Excel возвращает пустой список.

#### `get_fields_from_json`

~~~python
get_fields_from_json(file_path: str | Path) -> Any
~~~

Читает JSON в UTF-8. Корневое значение должно быть объектом. Возвращает
словарь, включая допустимый пустой словарь. При ошибке файла, кодировки,
синтаксиса JSON или корневом значении другого типа возвращает пустой список.

#### Логирование
Сообщения записываются в `logs/readers.log`: пути файлов, количество
загруженных и пропущенных записей, причины ошибок.

### Модуль `processing_views`
Модуль `src.processing_views` подготавливает транзакции для страниц «Главная»
и «События». Тип `CategoryResult` описывает поля `category: str`,
`amount: float` и `count: int`.

#### `_load_field_aliases`

~~~python
_load_field_aliases() -> dict[str, list[str]]
~~~

Загружает справочник псевдонимов и проверяет типы ключей, списков и путей.
Возвращает проверенный словарь либо пустой словарь. Вызывается при импорте, а
результат сохраняется в `FIELD_ALIASES`.

#### `_get_payment_amount`

~~~python
_get_payment_amount(
    transaction: dict[str, Any],
) -> float | None
~~~

Получает сумму платежа через справочник полей и возвращает конечный `float`.
Логические, нечисловые, бесконечные значения и `NaN` дают `None`.

#### `_get_last_digits`

~~~python
_get_last_digits(card_number: Any) -> str | None
~~~

Для непустой строки возвращает последние четыре символа номера карты после
удаления окружающих пробелов. Иначе возвращает `None`.

#### `_parse_operation_datetime`

~~~python
_parse_operation_datetime(value: Any) -> datetime | None
~~~

Поддерживает `datetime`, `date`, ISO-строку, `DD.MM.YYYY HH:MM:SS` и
`DD.MM.YYYY`. Пустые и нераспознаваемые значения дают `None`.

#### `_transaction_matches_view`

~~~python
_transaction_matches_view(
    transaction: Any,
    period_start: datetime,
    period_end: datetime,
    sent: bool,
    incoming: bool,
) -> bool
~~~

Проверяет тип транзакции, статус `OK`, дату внутри закрытого периода и знак
суммы. Сочетание `sent=True, incoming=False` выбирает расходы, обратное —
поступления. Возвращает `False` для некорректных данных.

#### `get_greeting`

~~~python
get_greeting(date_time: str) -> list[dict[str, str]]
~~~

Принимает `YYYY-MM-DD HH:MM:SS`. Возвращает список с одним словарём
`greeting`: утро с 05:00, день с 12:00, вечер с 18:00 до 22:59, ночь в
остальное время. Неверный тип или формат создаёт `TypeError` либо
`ValueError`.

#### `get_transactions`

~~~python
get_transactions() -> list[dict[str, Any]]
~~~

Загружает `data/operations.xlsx` через `get_transactions_from_xls`. Возвращает
список транзакций; при ожидаемой ошибке или результате другого типа — пустой
список.

#### `get_transactions_view`

~~~python
get_transactions_view(
    date_time: str,
    sent: bool = True,
    incoming: bool = False,
    date_range: str = "M",
) -> list[dict[str, Any]]
~~~

Фильтрует успешные операции до момента `date_time`. Диапазоны: `W` — неделя,
`M` — месяц, `Y` — год, другое значение, включая `ALL`, — с 01.01.1900.
Параметры `sent` и `incoming` выбирают расходы или поступления. Дата должна
иметь формат `YYYY-MM-DD HH:MM:SS`, `sent` — тип `bool`.

#### `get_cards_summary`

~~~python
get_cards_summary(
    date_time: str,
) -> list[dict[str, Any]]
~~~

Группирует расходы текущего месяца по последним четырём символам карты. Для
карты возвращает `last_digits`, абсолютную сумму `total_spent`, кешбэк
`total_spent / 100` и количество `count`.

#### `get_top_transactions`

~~~python
get_top_transactions(
    date_time: str,
    count_top: int,
) -> list[dict[str, Any]]
~~~

Возвращает крупнейшие операции по абсолютной сумме с полями `date`,
`amount`, `category` и `description`. `count_top` должен быть целым
неотрицательным числом и не `bool`. Ноль даёт пустой список.

#### `_validate_category_arguments`

~~~python
_validate_category_arguments(
    transactions: list[dict[str, Any]],
    count_top: int,
    expenses: bool,
) -> None
~~~

Проверяет список транзакций, целое неотрицательное `count_top` и логическое
`expenses`. При ошибке создаёт `TypeError` или `ValueError`.

#### `_get_category_amount`

~~~python
_get_category_amount(
    transaction: Any,
    index: int,
    expenses: bool,
) -> tuple[str, Decimal] | None
~~~

Извлекает непустую категорию и конечную сумму `Decimal`. Для расходов
принимает отрицательные, для поступлений — положительные суммы; возвращает
модуль суммы. Ошибочные записи дают `None`.

#### `_collect_category_totals`

~~~python
_collect_category_totals(
    transactions: list[dict[str, Any]],
    expenses: bool,
) -> tuple[defaultdict[str, Decimal], defaultdict[str, int]]
~~~

Возвращает два словаря: общую сумму и количество операций по каждой
корректной категории.

#### `_build_category_result`

~~~python
_build_category_result(
    category_totals: defaultdict[str, Decimal],
    category_counts: defaultdict[str, int],
    count_top: int,
    digit_round: int = 0,
) -> list[CategoryResult]
~~~

Сортирует категории по убыванию суммы и имени, оставляет первые `count_top`,
остальные объединяет в `Остальное`. Возвращает `category`, округлённый
`amount` и `count`. Исходная категория `Остальное` учитывается один раз.

#### `get_category_summary`

~~~python
get_category_summary(
    date_time: str,
    date_range: str = "M",
    count_top: int = 7,
    expenses: bool = True,
) -> tuple[list[CategoryResult], float, int]
~~~

Формирует сводку расходов или поступлений. Возвращает топ категорий, общую
сумму результата и общее количество операций. Ошибки аргументов передаются
вызывающему коду.

#### Логирование
Сообщения записываются в `logs/processing_views.log`: загрузка данных,
причины пропуска операций, границы периодов и результаты расчётов.

### Модуль `processing_services`
Модуль `src.processing_services` готовит данные для кешбэка,
«Инвесткопилки», текстового поиска, телефонов и переводов физическим лицам.

#### `_validate_period`

~~~python
_validate_period(year: int, month: int) -> None
~~~

Проверяет целые год и месяц, год от 1970 до текущего, месяц от 1 до 12 и
запрещает будущий период. `bool` недопустим. Создаёт `TypeError` или
`ValueError` при ошибке.

#### `_get_cashback_amount`

~~~python
_get_cashback_amount(
    transaction: dict[str, Any],
) -> float | None
~~~

Возвращает конечный числовой кешбэк как `float`. Логические, нечисловые,
бесконечные значения и `NaN` дают `None`.

#### `_transaction_matches_cashback`

~~~python
_transaction_matches_cashback(
    transaction: Any,
    year: str,
    month: str,
) -> bool
~~~

Проверяет словарь, статус `OK`, дату платежа, неотрицательный кешбэк и
совпадение года и месяца. Возвращает логический результат.

#### `_transaction_matches_investment`

~~~python
_transaction_matches_investment(
    transaction: Any,
    year: str,
    month: str,
) -> bool
~~~

Проверяет статус `OK`, дату операции, непустой номер карты, отрицательную
конечную сумму и совпадение месяца для «Инвесткопилки».

#### `_get_category_cashback`

~~~python
_get_category_cashback(
    transaction: Any,
    index: int,
) -> tuple[str, Decimal] | None
~~~

Извлекает непустую категорию и абсолютный конечный кешбэк `Decimal`.
Некорректные данные дают `None`; `index` используется в журнале.

#### `_collect_category_cashback`

~~~python
_collect_category_cashback(
    transactions: list[dict[str, Any]],
) -> tuple[defaultdict[str, Decimal], defaultdict[str, int]]
~~~

Возвращает сумму кешбэка и количество транзакций по каждой категории.

#### `get_transactions_cashback`

~~~python
get_transactions_cashback(
    year: str,
    month: str,
) -> list[dict[str, Any]]
~~~

Проверяет период, загружает операции и возвращает подходящие транзакции для
кешбэка. Некорректный формат или период приводит к пустому списку.

#### `valid_limit`

~~~python
valid_limit(limit: int) -> bool
~~~

Возвращает `True` только для целых порогов `10`, `50` и `100`. `bool` и
другие значения дают `False`.

#### `get_transaction_investment_bank`

~~~python
get_transaction_investment_bank(
    date_value: str,
    transactions: list[dict[str, Any]],
) -> list[dict[str, Any]]
~~~

Принимает месяц строго `YYYY-MM`. Возвращает успешные расходные карточные
операции этого месяца. Неверный тип, формат или будущий период дают пустой
список.

#### `get_total_amount`

~~~python
get_total_amount(
    transactions: list[dict[str, Any]],
) -> float
~~~

Суммирует абсолютные числовые суммы платежа. `bool` и нечисловые значения
пропускаются. При отсутствии данных возвращает `0.0`.

#### `get_total_limit_amount`

~~~python
get_total_limit_amount(
    transactions: list[dict[str, Any]],
    limit: int,
) -> float
~~~

Округляет каждую сумму вверх по формуле
`ceil(abs(amount) / limit) * limit` и суммирует результат. Валидация порога
выполняется до вызова.

#### `_transaction_matches_search`

~~~python
_transaction_matches_search(
    transaction: Any,
    search_query: str,
) -> bool
~~~

Ищет нормализованную подстроку в категории или описании без учёта регистра.
Некорректный объект транзакции даёт `False`.

#### `_valid_search_query`

~~~python
_valid_search_query(search_query: str) -> str | None
~~~

Удаляет пробелы и применяет `casefold`. Неверный тип и пустая строка дают
`None`.

#### `_valid_search_query_phone`

~~~python
_valid_search_query_phone(search_query: str) -> str | None
~~~

Проверяет российский номер с `+7` или `8` и допустимыми разделителями.
Возвращает `+79991234567` либо `89991234567`. При ошибке возвращает `None`.

#### `get_phone_transactions`

~~~python
get_phone_transactions(
    transactions: list[dict[str, Any]],
) -> list[dict[str, Any]]
~~~

Ищет номера в описании и возвращает группы с полями `phone`, `count` и
`transactions`. Некорректные кандидаты помещает в `phone_error`, где
`count` — количество кандидатов, а `transactions` — связанные операции.

#### `get_phone_group`

~~~python
get_phone_group(
    transactions: list[dict[str, Any]],
) -> list[dict[str, Any]]
~~~

Возвращает сокращённые группы телефонов с полями `phone` и `count`. Группы с
неверными типами полей пропускает.

#### `_normalize_name_part`

~~~python
_normalize_name_part(value: str) -> str
~~~

Приводит имя, включая части через дефис, к регистру с первой заглавной и
остальными строчными буквами.

#### `_valid_search_query_person`

~~~python
_valid_search_query_person(search_query: Any) -> str | None
~~~

Проверяет имя с фамилией или инициалом, нормализует пробелы и возвращает
`Имя Ф.`. Поддерживает дефисы. Неверный запрос даёт `None`.

#### `_get_person_from_transaction`

~~~python
_get_person_from_transaction(
    transaction: Any,
) -> str | None
~~~

Для категории `Переводы` ищет в описании имя и инициал фамилии, например
`Валерий А.`. Возвращает найденное значение либо `None`.

#### `get_person_transactions`

~~~python
get_person_transactions(
    transactions: list[dict[str, Any]],
) -> list[dict[str, Any]]
~~~

Группирует переводы по физическим лицам. Элемент содержит `person`,
`count` и исходные `transactions`.

#### `get_person_group`

~~~python
get_person_group(
    transactions: list[dict[str, Any]],
) -> list[dict[str, Any]]
~~~

Возвращает сокращённые группы с полями `person` и `count`, пропуская
некорректные типы.

#### Логирование
Сообщения записываются в `logs/processing_services.log`: ошибки периодов,
поисковых строк, пропущенные записи и итоги группировки.

### Модуль `services`
Модуль `src.services` содержит публичные сервисы и преобразует результаты
`processing_services` в JSON.

#### `get_category_cashback`

~~~python
get_category_cashback(
    year: str,
    month: str,
) -> str
~~~

Возвращает JSON-объект `{"Категория": сумма_кешбэка}`. При некорректном
периоде или отсутствии транзакций возвращает JSON-массив `[]`.

#### `investment_bank`

~~~python
investment_bank(
    month: str,
    transactions: list[dict[str, Any]],
    limit: int,
) -> float | None
~~~

За месяц `YYYY-MM` рассчитывает разницу между суммой расходов, округлённых
вверх до `10`, `50` или `100`, и фактической суммой. Возвращает результат с
двумя знаками, `0.0` без операций или `None` при ошибочном пороге и
отрицательном результате.

#### `get_transactions_search`

~~~python
get_transactions_search(
    transactions: list[dict[str, Any]],
    search_query: str,
) -> str
~~~

Ищет строку в категории и описании. Возвращает JSON с полями `count` и
`result`. Некорректный запрос даёт ноль и пустой список.

#### `get_transactions_search_phone`

~~~python
get_transactions_search_phone(
    transactions: list[dict[str, Any]],
    phone_num: str,
) -> str
~~~

Ищет транзакции по нормализованному телефону. Возвращает JSON `phone`,
`count` и `result`. Для некорректного или отсутствующего номера используется
`"phone": "None"` и пустой результат.

#### `get_transactions_search_phone_total`

~~~python
get_transactions_search_phone_total(
    transactions: list[dict[str, Any]],
) -> str
~~~

Возвращает JSON с общим `total`, блоком корректных групп `result` и блоком
ошибочных кандидатов `error`. В каждом блоке содержатся `count` и
`transactions`.

#### `get_transactions_search_person`

~~~python
get_transactions_search_person(
    transactions: list[dict[str, Any]],
    person: str,
) -> str
~~~

Ищет переводы конкретному лицу. Возвращает JSON `person`, `count` и
`result`. Ошибочный запрос даёт `"person": "None"`; корректное имя без
совпадений сохраняется в ответе с пустым списком.

#### `get_transactions_total_person`

~~~python
get_transactions_total_person(
    transactions: list[dict[str, Any]],
) -> str
~~~

Объединяет переводы всем физическим лицам. Возвращает JSON с общим `count` и
массивом `transactions`.

#### Логирование
Отдельного журнала нет. Проверка и группировка выполняются в
`processing_services` с журналом `logs/processing_services.log`.

### Модуль `reports`
Модуль `src.reports` формирует отчёты из `pandas.DataFrame` и автоматически
сохраняет результаты в JSON.

#### `_save_report_result`

~~~python
_save_report_result(
    result: Any,
    file_path: Path,
) -> None
~~~

Создаёт каталоги и записывает результат. Датафрейм сохраняется массивом
JSON-записей с кириллицей и ISO-датами; другие объекты — через `json.dump`.

#### `_decorate_report`

~~~python
_decorate_report(
    function: Callable[ReportParameters, TransactionResult],
    filename: str | Path | None,
) -> Callable[ReportParameters, TransactionResult]
~~~

Создаёт обёртку, которая вызывает отчёт, сохраняет результат и возвращает его
без изменения. Ошибку записи журналирует и передаёт далее.

#### `report_to_file`

~~~python
report_to_file(
    function_or_filename: Callable[..., Any] | str | Path | None = None,
    *,
    filename: str | Path | None = None,
) -> Callable[..., Any]
~~~

Поддерживает `@report_to_file`, `@report_to_file()`,
`@report_to_file("file.json")` и `@report_to_file(filename="file.json")`.
Без параметра использует `reports/<имя_функции>_report.json`.

#### `_get_report_end_date`

~~~python
_get_report_end_date(
    date_value: str | None,
) -> pd.Timestamp
~~~

Преобразует строку в дату без времени и часового пояса; `None` заменяет
текущей датой. Неверный тип создаёт `TypeError`, пустое или нераспознаваемое
значение — `ValueError`.

#### `_validate_report_columns`

~~~python
_validate_report_columns(
    transactions: pd.DataFrame,
    required_columns: set[str],
) -> None
~~~

Проверяет тип `DataFrame` и обязательные столбцы. Создаёт `TypeError` либо
`ValueError` с перечнем отсутствующих столбцов.

#### `_filter_expenses_for_period`

~~~python
_filter_expenses_for_period(
    transactions: pd.DataFrame,
    date_value: str | None,
    *,
    require_category: bool = False,
) -> pd.DataFrame
~~~

Отбирает отрицательные суммы за последние три календарных месяца до конца
выбранного дня. При наличии `Статус` оставляет `OK`. Опционально требует
`Категория`. Возвращает копию со служебными датой, суммой и модулем расхода.

#### `spending_by_category`

~~~python
spending_by_category(
    transactions: pd.DataFrame,
    category: str,
    date: str | None = None,
) -> pd.DataFrame
~~~

Возвращает расходы категории без учёта регистра и пробелов. Удаляет служебные
столбцы и сбрасывает индекс. Категория должна быть непустой строкой. JSON
сохраняется в `reports/spending_by_category_report.json`.

#### `spending_by_weekday`

~~~python
spending_by_weekday(
    transactions: pd.DataFrame,
    date: str | None = None,
) -> pd.DataFrame
~~~

Возвращает семь дней недели. Среднее равно среднему модулей отдельных
расходных транзакций дня и округляется до двух знаков. Для пустого дня
возвращается `0.0`. JSON сохраняется в
`reports/spending_by_weekday_report.json`.

#### `spending_by_workday`

~~~python
spending_by_workday(
    transactions: pd.DataFrame,
    date: str | None = None,
) -> pd.DataFrame
~~~

Возвращает среднее одной операции для `Рабочий день` (понедельник–пятница) и
`Выходной день` (суббота–воскресенье). Пустая группа получает `0.0`. JSON
сохраняется в `reports/spending_by_workday_report.json`.

#### Логирование
Сообщения записываются в `logs/reports.log`: периоды, число операций,
результаты и ошибки записи.

### Модуль `views`
Модуль `src.views` формирует итоговые JSON-ответы страниц приложения.

#### `get_main_response`

~~~python
get_main_response(date_time: str) -> Any
~~~

Получает `YYYY-MM-DD HH:MM:SS`. Возвращает JSON с `greeting`, `cards`,
`top_transactions`, `currency_rates` и `stock_prices`. Для топа запрашивает
пять операций. Ошибки вызываемых функций не подавляет.

#### `get_events_response`

~~~python
get_events_response(
    date_time: str,
    date_range: str = "M",
) -> Any
~~~

Возвращает JSON страницы «События». Блоки `expenses` и `income` содержат
`total_amount`, `total_count` и `main`. Для каждого используется топ из семи
категорий. Также включаются `currency_rates` и `stock_prices`. Диапазоны:
`W`, `M`, `Y` и `ALL`.

#### Логирование
Отдельного журнала нет. Диагностика выполняется в `processing_views`,
`currencies` и `stocks`.

### Модуль `stocks`
Модуль `src.stocks` получает котировки Marketstack и переводит их в базовую
валюту пользователя. Для API используется `RATES_API_KEY`.

#### `_get_stock_rates_from_api`

~~~python
_get_stock_rates_from_api(
    stocks: list[str],
) -> list[dict[str, Any]] | None
~~~

Проверяет список тикеров и API-ключ, объединяет тикеры запятыми и запрашивает
Marketstack. Возвращает список из `data`. При сетевой ошибке, пустом ответе,
`message`, `error`, неверном типе списка или его элементов возвращает
`None`.

#### `_convert_stock_price`

~~~python
_convert_stock_price(
    price: Any,
    source_currency: Any,
    target_currency: str,
    currency_rates: dict[str, Any],
    digit: int,
) -> float | None
~~~

Проверяет неотрицательную числовую цену. Пустую исходную валюту заменяет на
`USD`. При совпадении валют округляет цену, иначе рассчитывает
`price / rate`. Некорректная цена или курс дают `None`.

#### `_calculate_stock_rates`

~~~python
_calculate_stock_rates(
    currency: str,
    stock_rates: list[dict[str, Any]],
    digit: int,
) -> list[dict[str, Any]] | None
~~~

Проверяет валюту, неотрицательную целую точность и непустые котировки,
получает валютные курсы и преобразует `adj_close`. Элемент результата содержит
`symbol`, `stock_name`, `price_currency` и `adj_close`. Ошибочные элементы
пропускаются; при отсутствии результата возвращается `None`.

#### `get_stock_rates`

~~~python
get_stock_rates() -> list[dict[str, Any]] | None
~~~

Загружает тикеры и валюту из настроек, получает котировки, пересчитывает их с
точностью два знака и возвращает список `{"stock": symbol, "price": value}`.
При ошибках настроек, API, пустых данных или отсутствии корректных котировок
возвращает `None`.

#### Логирование
Сообщения записываются в `logs/stocks.log`: запросы, ошибки API и курсов,
пропущенные котировки и количество результатов.

## Тестирование

Тесты проекта написаны с помощью `pytest`. Для измерения покрытия исходного
кода используется плагин `pytest-cov`.

Тестовый набор проверяет все модули, находящиеся в каталоге `src`:

- `test_api_responses.py` — получение API-ключей, выполнение HTTP-запросов,
  обработка корректных и некорректных JSON-ответов, сетевых исключений;
- `test_currencies.py` — получение валютных курсов, проверка ответа API,
  расчёт обратных курсов, обработка настроек и ошибочных значений;
- `test_fields.py` — поиск по буквальным ключам и вложенным путям, работа с
  псевдонимами полей, загрузка пользовательских настроек;
- `test_processing_services.py` — проверка периода, фильтрация транзакций по
  статусу, дате, карте и кешбэку, обработка некорректных значений, группировка
  сумм по категориям, проверка порогов «Инвесткопилки», расчёт исходной и
  округлённой сумм, нормализация поисковых запросов, распознавание корректных
  и ошибочных телефонных кандидатов, группировка телефонов и переводов
  физическим лицам;
- `test_processing_views.py` — выбор приветствия, загрузка и фильтрация
  транзакций по диапазонам `W`, `M`, `Y`, `ALL`, разделение расходов и
  поступлений, группировка по картам и категориям, расчёт кешбэка, сумм и
  количества операций, формирование топов и категории `Остальное`;
- `test_readers.py` — чтение Excel и JSON, пропуск пустых строк, обработка
  отсутствующих, повреждённых и неверно закодированных файлов;
- `test_reports.py` — проверка декоратора с именем файла по умолчанию и с
  пользовательским путём, сериализации датафреймов, ошибок записи, валидации
  дат и обязательных столбцов, границ трёхмесячного периода, фильтрации
  расходов и расчётов по категориям, дням недели и типам дня;
- `test_services.py` — формирование итогового JSON с кешбэком по категориям,
  сохранение кириллицы, обработка пустого результата и расчёт накоплений
  «Инвесткопилки», простой поиск, поиск по номеру телефона, объединение
  телефонных групп и поиск переводов физическим лицам;
- `test_stocks.py` — получение котировок акций, проверка ответа API,
  преобразование стоимости в другую валюту и обработка некорректных данных;
- `test_views.py` — формирование JSON-ответов страниц «Главная» и «События» и
  правильная передача рассчитанных сумм, количества операций и котировок.

Для категории `Остальное` предусмотрен отдельный регрессионный тест: он
проверяет, что суммы и количество транзакций категорий вне топа добавляются
ровно один раз.

Внешние HTTP-запросы изолированы с помощью объектов `Mock` и фикстуры
`monkeypatch`, поэтому для запуска тестов не требуются доступ в интернет и
настоящие API-ключи. Временные файлы создаются через фикстуру `tmp_path` и не
изменяют файлы проекта.

### Запуск тестов

Запустить весь набор тестов:

```shell
poetry run pytest
```

Запустить тесты одного модуля:

```shell
poetry run pytest tests/test_reports.py
```

Запустить один тест:

```shell
poetry run pytest tests/test_stocks.py::test_get_stock_rates_returns_simplified_quotes
```

Выбрать тесты по части имени:

```shell
poetry run pytest -k "currency"
```

### Проверка покрытия

Запустить тесты с измерением покрытия строк и ветвлений:

```shell
poetry run pytest --cov=src --cov-branch --cov-report=term-missing
```

Текущий набор включает 352 теста. Актуальное покрытие строк и ветвлений можно
проверить приведённой выше командой.

Создать интерактивный HTML-отчёт о покрытии:

```shell
poetry run pytest --cov=src --cov-branch --cov-report=html
```

После выполнения команды отчёт будет сохранён в каталоге `htmlcov`. Главная
страница отчёта:

```text
htmlcov/index.html
```

### Проверка качества тестов

Проверить форматирование с помощью Black:

```shell
poetry run black --check tests
```

Проверить порядок импортов:

```shell
poetry run isort --check-only tests
```

Запустить Flake8:

```shell
poetry run flake8 tests
```

Проверить аннотации типов:

```shell
poetry run mypy tests
```


