# 🇰🇿 Qazaq Loc QA (`qazaq-loc-intelligence`)

> **Automated Quality Assurance & UX Linter for Kazakh Localization in Flutter Applications (.arb / .json)**

[![GitHub Action](https://img.shields.io/badge/CI%2FCD-GitHub_Actions-2088FF?logo=github-actions&logoColor=white)](https://github.com/features/actions)
[![Flutter l10n](https://img.shields.io/badge/Flutter-ARB_Compatible-02569B?logo=flutter&logoColor=white)](https://flutter.dev/docs/development/accessibility-and-localization/internationalization)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

---

## 🎯 Проблема и решение

Локализация мобильных приложений на казахский язык имеет две критические проблемы в мобильных UI (Flutter):

### 1. `suffix_harmony` (Закон сингармонизма и ассимиляции)
В казахском языке падежные окончания зависят от гласных и согласных последнего слога слова (твердые/мягкие, звонкие/глухие):
- *Айзере* + барыс септік $\rightarrow$ *Айзере**ге***
- *Асқар* + барыс септік $\rightarrow$ *Асқар**ға***
- *Марат* + барыс септік $\rightarrow$ *Марат**қа***

Когда в строке локализации используется жесткое окончание после динамического плейсхолдера:
```arb
"send_to_user": "{name}-ға жіберу" // ❌ ОШИБКА: для имени "Айзере" будет неграмотно ("Айзере-ға")
```
**Решение линтера:** фиксировать ошибку и предлагать реструктуризацию фразы в именительный падеж (атау септік):
```arb
"send_to_user": "Жіберу: {name}" // ✅ КОРРЕКТНО для любых имен
```

---

### 2. `length_overflow` (Переполнение компактных UI-элементов)
Казахские составные глаголы и отглагольные существительные часто значительно длиннее русских и английских аналогов. На кнопках (`*_button`), вкладках (`*_tab`) и заголовках (`*_title`) длинный текст обрезается (`...`) или ломает верстку на экранах 360–390dp:
```arb
"confirm_order_button": "Тапсырысты рәсімдеуді растау" // ❌ 27 символов — обрезка на кнопке
```
**Решение линтера:** предупреждать разработчиков и предлагать лаконичные UI-эквиваленты ($\le 15$ символов):
```arb
"confirm_order_button": "Растау" // ✅ 6 символов — идеальный CTA
```

---

## 🚀 Быстрый старт в GitHub Actions

Добавьте файл `.github/workflows/kazakh_loc_qa.yml` в ваш Flutter-репозиторий:

```yaml
name: Kazakh Localization QA

on:
  pull_request:
    paths:
      - 'lib/l10n/**.arb'
      - 'assets/translations/**.json'
  push:
    branches: [main, master]
    paths:
      - 'lib/l10n/**.arb'

jobs:
  qazaq-qa:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Run Qazaq Loc QA
        uses: ./path-to-action # или qazaq-loc-intelligence/qazaq_loc_qa@v1
        with:
          target-file: 'lib/l10n/app_kk.arb'
          max-button-length: '15'
          fail-on-warnings: false
          json-output: 'loc_report.json'

      - name: Upload Report
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: qazaq-loc-qa-report
          path: loc_report.json
```

---

## 📊 Отчёт в Pull Request (`$GITHUB_STEP_SUMMARY`)

При обнаружении нарушений GitHub Action формирует наглядный отчет прямо в интерфейсе Pull Request:

| Статус | Ключ | Проблема | Текущий текст | Рекомендация |
| :---: | :--- | :--- | :--- | :--- |
| 🔴 ERROR | `send_to_user` | Жесткий аффикс `-ға` после `{name}` нарушает сингармонизм | `{name}-ға жіберу` | `Жіберу: {name}` |
| 🟡 WARN | `confirm_order_button` | Превышение лимита длины UI (27 > 15 симв.) | `Тапсырысты рәсімдеуді растау` | `Растау` |

---

## 💻 Локальный запуск (CLI)

Скрипт не требует сторонних библиотек и работает на чистом Python 3.8+:

```bash
# Базовый запуск:
python3 qazaq_loc_qa.py lib/l10n/app_kk.arb

# С сохранением отчета в JSON и строгим режимом:
python3 qazaq_loc_qa.py lib/l10n/app_kk.arb \
  --max-button-len 15 \
  --fail-on-warnings \
  --json-output report.json
```

### Параметры CLI:
- `target`: путь к `.arb` или `.json` файлу.
- `--max-button-len`: максимальная длина для ключей UI (по умолчанию `15`).
- `--key-regex`: пользовательский regex для ключей компактных элементов UI.
- `--fail-on-warnings`: завершать процесс с кодом `1` не только при ошибках сингармонизма, но и при предупреждениях длины.
- `--json-output`: путь для сохранения структурированного JSON-отчёта.
