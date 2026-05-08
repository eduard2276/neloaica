# Neloaica — Comenzi rapide

## Setup inițial

```powershell
# Crează și activează un virtual environment (opțional, recomandat)
python -m venv .venv
.venv\Scripts\Activate.ps1

# Instalează dependențele de runtime
pip install -r requirements.txt

# Instalează dependențele de dezvoltare (pytest, black, isort, flake8)
pip install -e ".[dev]"
```

---

## Rulare aplicație

```powershell
# Rulare directă din sursă (recomandat în dezvoltare)
python -m src.main

# Sau după instalarea pachetului cu pip install -e .
neloaica
```

---

## Teste

```powershell
# Rulează toate testele
python -m pytest

# Rulează cu output scurt (doar eșecuri + sumar)
python -m pytest --tb=short -q

# Rulează doar testele de model (DB layer)
python -m pytest tests/db/

# Rulează doar testele de UI
python -m pytest tests/ui/

# Rulează doar testele de export Excel
python -m pytest tests/excel/

# Rulează un fișier specific
python -m pytest tests/db/test_labor_model.py

# Rulează un test specific
python -m pytest tests/db/test_labor_model.py::TestGetByName::test_get_by_name_case_insensitive

# Rulează cu acoperire de cod (necesită pytest-cov)
pip install pytest-cov
python -m pytest --cov=src --cov-report=term-missing
```

---

## Build executabil (PyInstaller)

```powershell
# Instalează PyInstaller dacă nu e instalat
pip install pyinstaller

# Build folosind spec-ul existent (recomandat)
pyinstaller neloaica.spec --noconfirm

# Sau folosind scriptul bat inclus
.\build.bat

# Executabilul generat se află la:
#   dist\Neloaica\Neloaica.exe
```

> **Notă:** Dacă apare un `PermissionError` legat de OneDrive care blochează fișiere
> temporare din `build\`, build-ul se finalizează totuși cu succes.
> Verifică existența `dist\Neloaica\Neloaica.exe` după build.

---

## Formatare și linting

```powershell
# Formatare automată cu Black
black src/ tests/

# Sortare importuri
isort src/ tests/

# Verificare stil (fără modificare)
flake8 src/ tests/

# Verificare Black fără modificare
black --check src/ tests/
```

---

## Utilitare

```powershell
# Șterge fișierele de build (pentru un build curat)
Remove-Item -Recurse -Force build, dist

# Șterge cache-ul pytest și __pycache__
Remove-Item -Recurse -Force .pytest_cache
Get-ChildItem -Recurse -Filter __pycache__ | Remove-Item -Recurse -Force

# Verifică versiunea Python
python --version

# Listează pachetele instalate
pip list

# Verifică dependențele de runtime
pip install -r requirements.txt --dry-run
```

---

## Git

```powershell
# Verifică starea fișierelor
git status

# Adaugă toate modificările
git add .

# Adaugă un fișier specific
git add src/pages/labor.py

# Commit
git commit -m "mesaj commit"

# Vizualizează istoricul
git log --oneline -10

# Creează un branch nou și trece pe el
git checkout -b feature/nume-feature

# Listează branch-urile
git branch

# Trece pe un branch existent
git checkout main

# Merge branch în main
git checkout main
git merge feature/nume-feature

# Șterge un branch local după merge
git branch -d feature/nume-feature

# Push pe remote
git push origin main

# Pull ultimele modificări
git pull origin main

# Anulează modificările unui fișier (nestagged)
git restore src/pages/labor.py

# Anulează ultimul commit (păstrează modificările)
git reset --soft HEAD~1

# Vizualizează diferențele față de ultimul commit
git diff

# Vizualizează diferențele fișierelor staged
git diff --staged

# Creează un tag de versiune
git tag -a v1.0.0 -m "Release v1.0.0"
git push origin v1.0.0
```

---

## Structura output build

```
dist\
└── Neloaica\
    ├── Neloaica.exe        ← executabilul principal
    ├── _internal\          ← runtime Python + PySide6 DLL-uri
    └── templates\          ← template-uri Excel copiate automat
```
