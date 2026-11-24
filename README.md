# Finance Tracker

A desktop personal-finance app built with **Python, PyQt5, matplotlib, OpenCV and Tesseract OCR**.
Track your balance and expenses, see where your money goes in a live pie chart, scan receipts
to pre-fill amounts (Greek and English), keep separate profiles, and build a streak by staying
under a daily spending limit.

> Originally a university group project (*Applied Programming in Python*, Ionian University,
> supervised by Prof. Ioannis Karydis). Extended into a complete, tested application.

<!-- Add a screenshot here: ![screenshot](docs/screenshot.png) -->

## Features

- **Balance & expense logging** with category selection (Food, Transportation, Shopping, Entertainment, Bills, Others)
- **Live expense-distribution pie chart** (matplotlib embedded in Qt)
- **Receipt scanning**: OpenCV pre-processing + Tesseract OCR, detects the *total* on Greek and English receipts (`12,50`, `1.234,56`, `ΣΥΝΟΛΟ`, `ΠΛΗΡΩΤΕΟ`...)
- **Multiple profiles**, with data persisted to `~/.finance_tracker/data.json` (atomic writes, corrupt-file backup)
- **Streaks**: consecutive days within your daily spending limit
- **Settings**: light/dark theme, currency symbol, daily limit, profile management

## Getting started

Requires Python 3.9+.

```bash
git clone https://github.com/<your-username>/finance-tracker.git
cd finance-tracker

# Windows (PowerShell)
python -m venv .venv
.venv\Scripts\activate

# macOS / Linux
python3 -m venv .venv
source .venv/bin/activate

pip install -r requirements.txt
python -m finance_tracker
```

Run the last command from the repository root. Your data is stored in `~/.finance_tracker/data.json`
(delete that file to reset the app).

The app works without Tesseract; only the **Scan Receipt** button needs it.

## Installing Tesseract OCR (for receipt scanning)

Tesseract is a separate program: `pip install pytesseract` only installs the Python wrapper.
You also need the **Greek (`ell`)** language data for Greek receipts. If it is missing, the app falls
back to English.

### Windows

1. Download the 64-bit installer from the [UB Mannheim Tesseract page](https://github.com/UB-Mannheim/tesseract/wiki).
2. Run it. On the **Choose Components** screen, expand **Additional language data** and tick **Greek**.
3. Add the install folder (default `C:\Program Files\Tesseract-OCR`) to your `PATH`
   (*Start → "Edit the system environment variables" → Environment Variables → Path → New*).
4. Open a **new** terminal and verify:

   ```powershell
   tesseract --version
   tesseract --list-langs     # should list both eng and ell
   ```

Prefer not to edit `PATH`? Point the app at the executable instead:

```powershell
$env:TESSERACT_CMD = "C:\Program Files\Tesseract-OCR\tesseract.exe"   # current session
setx TESSERACT_CMD "C:\Program Files\Tesseract-OCR\tesseract.exe"     # permanent (new terminal needed)
```

Already installed without Greek? Re-run the installer and add the language, or download
`ell.traineddata` (see the [Tesseract data files](https://github.com/tesseract-ocr/tesseract/wiki/Data-Files))
into `C:\Program Files\Tesseract-OCR\tessdata`.
Avoid `choco install tesseract` for this project: it only ships English.

### macOS (Homebrew)

```bash
brew install tesseract tesseract-lang
```

### Linux

```bash
sudo apt update && sudo apt install tesseract-ocr tesseract-ocr-ell     # Debian/Ubuntu
sudo dnf install tesseract tesseract-langpack-ell                       # Fedora
sudo pacman -S tesseract tesseract-data-eng tesseract-data-ell          # Arch
```

### Try the scanner on its own

```bash
python -m finance_tracker.receipt_ocr path/to/receipt.png
```

It prints the recognised text, every amount found, and the detected total.

## Tests

```bash
pip install -r requirements-dev.txt
pytest -q
```

The data layer (`models.py`) and the receipt parser (`receipt_ocr.py`) have no Qt/OpenCV dependency at
import time, so the test suite runs anywhere, including CI.

## Troubleshooting

| Symptom | Fix |
|---|---|
| `ModuleNotFoundError: finance_tracker` | Run commands from the repository root. |
| `ModuleNotFoundError: PyQt5` / `cv2` | Activate the virtualenv and re-run `pip install -r requirements.txt`. |
| PyQt5 fails to install | `python -m pip install -U pip`, and use 64-bit Python 3.9–3.12. |
| Linux: `Could not load the Qt platform plugin "xcb"` | `sudo apt install libxcb-xinerama0 libxcb-cursor0 libgl1` |
| "Tesseract OCR is not installed or not on PATH" | Install it (see above), reopen the terminal, or set `TESSERACT_CMD`. |
| Greek receipts give gibberish | The `ell` language data is missing. Check `tesseract --list-langs`. |
| Wrong total detected | Run the scanner CLI to inspect the raw text; use a flat, well-lit, cropped photo. |
| App starts with an empty "User" profile | The data file was unreadable; it was renamed to `data.json.bak`. |

## Project structure

```
finance_tracker/
  models.py           Profile, Transaction, ProfileStore (JSON persistence), streak logic
  receipt_ocr.py      OpenCV preprocessing, Tesseract OCR, amount/total extraction
  main_window.py      Main PyQt5 window + pie chart
  settings_dialog.py  Profiles, theme, currency, daily limit
  themes.py           Light/dark stylesheets
tests/                Unit tests
```

## Design notes

- UI and logic are separated: all money logic lives in `models.py` and is unit tested.
- The OCR total is chosen by keyword (`TOTAL`, `ΣΥΝΟΛΟ`...) rather than "largest number", skips `SUBTOTAL`
  lines and ignores dates.
- Images are loaded via `np.fromfile` + `cv2.imdecode` so Greek/non-ASCII Windows paths work.

## Roadmap

- Monthly budgets and per-category limits
- CSV export / import
- Receipt line-item extraction
- Packaged installer bundling Tesseract

## Authors

Aikaterini Analyti, Panagiotis-Fotios Iliopoulos, Fotios Tzelepis, Stavros Kouroupis.
