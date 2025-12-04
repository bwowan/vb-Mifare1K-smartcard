## nfc-reader

Modern Python project for working with USB NFC/RFID card readers based on the
[`pyscard`](https://github.com/LudovicRousseau/pyscard) library.

### Installation

```bash
python -m pip install .
# or for development
python -m pip install .[dev]
```

### Dependencies

- `pyscard` is automatically loaded from GitHub:

```
pyscard @ git+https://github.com/LudovicRousseau/pyscard.git
```

Official documentation: [pyscard user guide](https://pyscard.sourceforge.io/user-guide.html#pyscard-user-guide).

### Usage

After installation, a console command is available:

```bash
nfc-read
```

The command starts waiting for an NFC card and outputs a dump of the first MIFARE 1K sector
(logic is implemented in `src/nfc_reader/do_card.py`, based on code from `nfc_read.py`).

### Development

```bash
python -m pip install .[dev]
ruff check src tests
pytest
```

The project includes a GitHub Actions workflow for checking the linter and tests on every push/pull request.
