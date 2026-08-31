# WinBoost

Оптимизатор Windows: анализ системы, пошаговое применение твиков и откат изменений.

> ⚠️ Проект в стадии ремонта. Движок бэкапа сейчас покрывает только реестр —
> службы, задачи планировщика и план электропитания не восстанавливаются.
> См. `docs/` и план работ.

## Структура

```
app/            Приложение (Python 3.14, Dear PyGui)
  modules/      Модули оптимизации: анализ, приватность, игры, сеть, очистка…
  tests/        pytest
site/           Лендинг (Next.js 15 + Tailwind v4)
docs/
  design/       Дизайн-система: DESIGN.md, tokens.json, theme.css
  site-legacy/  Предыдущая версия сайта — источник контента
dist/archive/   Исторические сборки .exe (не в git)
```

## Разработка

```bash
# приложение
cd app && pip install -r requirements.txt && python WinBoostGUI.py

# тесты
cd app && python -m pytest tests/ -v

# сборка
cd app && powershell -ExecutionPolicy Bypass -File build.ps1

# сайт
cd site && npm install && npm run dev
```

## Лицензия

MIT — см. `LICENSE`.
