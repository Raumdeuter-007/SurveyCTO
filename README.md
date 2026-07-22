## SurveyCTO Converter

Converts `.docx` surveys into SurveyCTO-compatible `.xlsx` files via a desktop GUI.

## Prerequisites

- [Python](https://www.python.org/downloads/)
- [uv](https://docs.astral.sh/uv/getting-started/installation/) — package manager
- [InnoSetup](https://jrsoftware.org/isdl.php/Inno-Setup-Downloads) — only needed to build an installer

## Setup

**Install dependencies:**

```bash
uv sync
```

**Run the app:**

```bash
.\.venv\Scripts\activate.ps1   # use .bat on CMD
uv pip install -e .
py main.py
```

**Build an installer (optional):**

```bash
.\.venv\Scripts\activate.ps1   # use .bat on CMD
py installer.py                # outputs .exe to dist/
```

Then open `Installer.iss` in InnoSetup and compile.

## Usage

**Prepare your document:**  
Wrap each module with `MODULE_DELIMITER` (configured in `config/pipeline.py`) at its start and end.

**In the app:**

1. Browse and select your `.docx` file.
2. Add all languages present in the survey.
3. Click **Process**.

**What happens under the hood — 3-stage pipeline:**

| Stage       | File          | Description                                                                       |
| ----------- | ------------- | --------------------------------------------------------------------------------- |
| 1. Splitter | `splitter.py` | Splits the `.docx` into modules by delimiter                                      |
| 2. Parser   | `parser.py`   | Sends each module to an LLM; returns structured survey + choice rows per language |
| 3. Compiler | `compiler.py` | Merges all modules into one `.xlsx`, deduplicates choices                         |

Configure settings sheet, then upload the output file to SurveyCTO.

## Running Tests

Create a `.env` at the project root:

```
DEBUG_PATH="D:\\path\\to\\your\\document.docx"
GOOGLE_API_KEY=your_api_key
```

> Escape backslashes as `\\` and apostrophes as `\'`. The file must use `MODULE_DELIMITER`.

Run tests:

```bash
uv run --env-file .env pytest
```

## Project Structure

```
SurveyCTO/
├── src/
│   ├── config/
│   │   ├── compiler.py
│   │   ├── lang.py
│   │   ├── pipeline.py
│   │   └── theme.py
│   ├── models/
│   │   └── survey.py
│   ├── pipeline/
│   │   ├── splitter.py       # Stage 1: docx → modules
│   │   ├── parser.py         # Stage 2: module → LLM → structured questions
│   │   └── compiler.py       # Stage 3: structured questions → xlsx
│   ├── ui/
│   │   ├── controller.py
│   │   └── language_input.py
│   ├── utils/
│   │   ├── logger.py
│   │   └── theme.py
│   └── app.py
├── prompts/
│   ├── parse_module.yaml
│   └── fixed_rows.yaml
├── tests/
│   ├── test_splitter.py
│   ├── test_parser.py
│   └── test_pipeline.py
├── pyproject.toml
├── main.py
├── installer.py
├── Installer.iss
└── .env
```

## License

[GNU GPL-3.0](LICENSE)
