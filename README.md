## nfc-reader

Современный Python-проект для работы с USB NFC/RFID-картридером на базе библиотеки
[`pyscard`](https://github.com/LudovicRousseau/pyscard).

### Установка

python -m pip install .
# или для разработки
python -m pip install .[dev]### Зависимости

- `pyscard` загружается автоматически из GitHub:

pyscard @ git+https://github.com/LudovicRousseau/pyscard.gitОфициальная документация: [pyscard user guide](https://pyscard.sourceforge.io/user-guide.html#pyscard-user-guide).

### Использование

После установки доступна консольная команда:

nfc-readКоманда запускает ожидание NFC-карты и выводит дамп первой секции MIFARE 1K
(логика реализована в `src/nfc_reader/mifare.py`, основана на коде `nfc_read.py`).

### Разработка

python -m pip install .[dev]
ruff check src tests
pytestПроект включает GitHub Actions workflow для проверки линтера и тестов при каждом push/pull request.


