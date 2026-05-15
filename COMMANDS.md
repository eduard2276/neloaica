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
python -m PyInstaller --noconfirm --clean Neloaica.spec

# Executabilul generat se află la:
#   dist\Neloaica\Neloaica.exe
# Template-ul Excel ajunge la:
#   dist\Neloaica\_internal\templates\Template-deviz.xlsx
```

> **Notă:** Dacă apare un `PermissionError` legat de OneDrive care blochează fișiere
> temporare din `build\`, build-ul se finalizează totuși cu succes.
> Verifică existența `dist\Neloaica\Neloaica.exe` după build.

> În repo există și un `build.bat` (gitignored, local-only) care face același
> lucru — îl poți recrea cu un singur `python -m PyInstaller ...`.

---

## Release (publicare versiune nouă)

Pipeline-ul de release este complet automatizat prin `.github/workflows/release.yml`.
**Singurul lucru de făcut local este să bump-uiești versiunea și să împingi un tag.**

Workflow-ul:
1. Pornește doar la push de tag `vX.Y.Z` (SemVer strict).
2. Verifică că tag-ul se potrivește exact cu `__version__` din `src/__init__.py`.
3. Construiește bundle PyInstaller (onedir) pe `windows-latest` cu Python 3.12.
4. Sanity-check: confirmă că `Neloaica.exe` și template-ul Excel sunt în `dist/Neloaica/`.
5. Comprimă bundle-ul ca `Neloaica-vX.Y.Z-windows.zip`.
6. Atașează ZIP-ul la un GitHub Release nou (sau actualizează cel existent).
7. Calculează SHA-256 al ZIP-ului.
8. Rulează `scripts/update_manifest.py` și împinge `update-manifest.json` actualizat
   pe `main` (commit-ul include `[skip ci]` ca să nu trigger-eze CI inutil).
   Manifestul este sursa de adevăr pentru funcția in-app de auto-update
   (clienții citesc `raw.githubusercontent.com/.../main/update-manifest.json`).

### Pașii pentru un release nou

```powershell
# 0. Asigură-te că ești pe main, sincronizat cu remote și fără modificări locale
git checkout main
git pull origin main
git status                       # trebuie să fie "working tree clean"

# 1. Bump versiunea în UN SINGUR LOC: src/__init__.py
#    (pyproject.toml citește dinamic de acolo)
#    Exemplu pentru 1.0.0 → 1.0.1:
#       __version__ = "1.0.1"
#    Vezi nota despre SemVer mai jos.

# 2. Verifică local că totul trece înainte de tag (recomandat)
python -m black --check src/ tests/ scripts/
python -m isort  --check src/ tests/ scripts/
python -m flake8 src/ tests/ scripts/
$env:QT_QPA_PLATFORM = "offscreen"
python -m pytest -q

# 3. Commit cu mesaj standardizat
git add src/__init__.py
git commit -m "Bump version to 1.0.1"
git push origin main

# 4. Creează tag SemVer (DEVE să înceapă cu "v")
git tag -a v1.0.1 -m "Release v1.0.1"
git push origin v1.0.1

# 5. Urmărește build-ul în GitHub Actions
gh run watch                     # afișează jobul în terminal până se termină
# sau deschide în browser:
gh run list --workflow=release.yml --limit 1

# 6. După succes, link-ul Release apare aici:
gh release view v1.0.1
gh release view v1.0.1 --web     # deschide direct în browser
```

### SemVer — cum alegi numărul

- **PATCH** (`1.0.0 → 1.0.1`) — bugfix-uri compatibile, fără modificare de schemă DB sau API.
- **MINOR** (`1.0.0 → 1.1.0`) — feature nou compatibil cu datele existente.
- **MAJOR** (`1.0.0 → 2.0.0`) — migrare DB obligatorie sau breaking change vizibil utilizatorului.

### Troubleshooting

| Simptom | Cauză | Fix |
|---|---|---|
| Workflow eșuează la pasul **Verify tag matches src/__version__** | Ai uitat să bump-uiezi `src/__init__.py` înainte de tag | Șterge tag-ul (vezi mai jos), bump versiunea, recreează tag-ul |
| Workflow eșuează la **Sanity check the bundle** | PyInstaller a rulat dar n-a inclus template-ul Excel | Verifică că `templates/Template-deviz.xlsx` există în repo și că `Neloaica.spec` îl include în `datas` |
| **release.yml nu se declanșează** | Tag-ul nu respectă formatul `v*.*.*` (ex: `1.0.1` fără `v`, sau `v1.0.1-beta`) | Folosește strict `vX.Y.Z` cu numere întregi |
| **GitHub Release nu apare** dar workflow trecut | Permisiunea `contents: write` nu e activă pe repo | Settings → Actions → General → Workflow permissions → "Read and write permissions" |

### Anularea unui tag greșit

```powershell
# Șterge tag-ul local
git tag -d v1.0.1

# Șterge tag-ul de pe remote (asta NU oprește un workflow deja pornit;
# pentru asta foloseste `gh run cancel <run-id>`)
git push --delete origin v1.0.1

# Dacă workflow-ul a apucat să creeze un GitHub Release defect:
gh release delete v1.0.1 --yes --cleanup-tag
```

### Livrare către utilizator

După ce release-ul e publicat:

```powershell
# Copiază link-ul de download al ZIP-ului
gh release view v1.0.1 --json assets --jq '.assets[].url'
```

Trimite utilizatorului link-ul → descarcă ZIP-ul → dezarhivează unde vrea → rulează `Neloaica.exe`.
**La prima pornire**, aplicația migrează automat orice `neloaica.db` și folder `backups/`
existente lângă vechiul `.exe` în `%LOCALAPPDATA%\Neloaica\` (vezi log-ul din
`%LOCALAPPDATA%\Neloaica\logs\neloaica.log`).

---

## Testarea auto-update-ului (end-to-end local)

PR-urile #4-8 implementează un sistem complet de auto-update prin butonul
**"🔄 Verifică actualizări"** din pagina **Settings**. Acesta:
1. Apelează `UpdateChecker` care citește un manifest JSON de pe GitHub
   (URL implicit: `raw.githubusercontent.com/.../main/update-manifest.json`).
2. Dacă există versiune nouă, oferă să o descarce (`UpdateDownloader`
   cu progress bar + verificare SHA-256).
3. La final lansează un helper PowerShell care înlocuiește instalarea
   curentă cu cea nouă și relansează aplicația.

### Override URL manifest pentru testare

Înainte ca PR #3 să fie merged pe `main`, manifestul **nu există** pe `main`,
ci doar pe branch-ul `feature/auto-update-roadmap`. Pentru a testa local
fără merge, setează variabila de mediu înainte să pornești aplicația:

```powershell
$env:NELOAICA_UPDATE_MANIFEST_URL = "https://raw.githubusercontent.com/eduard2276/neloaica/feature/auto-update-roadmap/update-manifest.json"
.\Neloaica.exe   # sau python -m src.main
```

Pentru un test izolat 100% (fără GitHub), folosește un fișier local:

```powershell
# Servește local cu http.server (din altă fereastră)
cd C:\tmp\my-test-manifest
python -m http.server 8000

# In aplicație
$env:NELOAICA_UPDATE_MANIFEST_URL = "http://localhost:8000/update-manifest.json"
.\Neloaica.exe
```

### Scenariul recomandat de testare end-to-end

```text
Pas 1 (LOCAL)  — Build versiunea curentă ca "instalat":
  python -m PyInstaller --noconfirm --clean Neloaica.spec
  Move-Item dist\Neloaica C:\TestApp\Neloaica
  C:\TestApp\Neloaica\Neloaica.exe        # confirmă că pornește

Pas 2 (LOCAL)  — Bump versiunea + commit + tag:
  # Edit src/__init__.py: __version__ = "1.0.1"
  git add src/__init__.py
  git commit -m "Bump version to 1.0.1"
  git tag -a v1.0.1 -m "Release v1.0.1"

Pas 3 (REMOTE) — Push tag → workflow GitHub Actions face automat:
  git push origin main
  git push origin v1.0.1
  gh run watch                            # urmărește build-ul
  # Workflow-ul:
  #   - build PyInstaller
  #   - publică GitHub Release v1.0.1 cu ZIP
  #   - calculează SHA-256 al ZIP-ului
  #   - actualizează update-manifest.json pe main (commit [skip ci])

Pas 4 (LOCAL)  — Verifică update-ul din app:
  cd C:\TestApp\Neloaica
  .\Neloaica.exe
  # Settings → "🔄 Verifică actualizări"
  # → "Versiunea 1.0.1 este disponibilă..."
  # → Da pe download → progress bar → Da pe instalează → app se închide
  # → după 2-3 sec, app repornește în versiunea 1.0.1

Pas 5 (POST)   — Inspectează log-urile pentru diagnostic:
  type %LOCALAPPDATA%\Neloaica\logs\neloaica.log
  type %LOCALAPPDATA%\Neloaica\updates\apply_update.log
  ls %LOCALAPPDATA%\Neloaica\updates\         # archive descărcate
  ls C:\TestApp\                              # Neloaica + Neloaica.old.<ts>
```

### Troubleshooting auto-update

| Simptom | Cauză | Fix |
|---|---|---|
| "Manifest is not valid JSON" | URL-ul pointează la o pagină HTML (404) | Verifică variabila `NELOAICA_UPDATE_MANIFEST_URL` |
| "Nu am putut verifica..." | Conexiune Internet / firewall | Vezi log `neloaica.log` pentru exception completă |
| "SHA-256 mismatch" | Manifest are hash vechi, ZIP-ul de pe Release e altul | Re-rulează workflow-ul de release (`Compute artefact SHA-256`) |
| App nu repornește după apply | Helper-ul PowerShell a eșuat | Citește `%LOCALAPPDATA%\Neloaica\updates\apply_update.log` |
| "Staged archive does not contain Neloaica.exe" | ZIP-ul de pe Release nu are layout-ul corect | Verifică pasul "Zip bundle" din `release.yml` |

### Curățare după teste

```powershell
# Șterge instalarea de test
Remove-Item -Recurse C:\TestApp\Neloaica
Remove-Item -Recurse C:\TestApp\Neloaica.old.*

# Șterge artefactele de update (cache descărcat + staging)
Remove-Item -Recurse $env:LOCALAPPDATA\Neloaica\updates\

# Șterge release-ul de test (dacă a fost real pe GitHub)
gh release delete v1.0.1 --yes --cleanup-tag
```

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
```

> Pentru tag-uri de versiune și release-uri, vezi secțiunea
> [Release (publicare versiune nouă)](#release-publicare-versiune-nouă).

---

## Structura output build

```
dist\
└── Neloaica\
    ├── Neloaica.exe        ← executabilul principal
    ├── _internal\          ← runtime Python + PySide6 DLL-uri
    └── templates\          ← template-uri Excel copiate automat
```
