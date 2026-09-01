# Публикация в winget

Манифесты для `microsoft/winget-pkgs`. Даёт установку одной командой и обходит
предупреждение SmartScreen, которое видят все, кто скачивает неподписанный
`.exe` кнопкой из браузера.

```
winget install imalisherbekenov.WinBoost
```

## Что лежит здесь

`3.1/` — три файла, как требует схема winget 1.6.0:

| файл | что описывает |
|---|---|
| `imalisherbekenov.WinBoost.yaml` | версия и локаль по умолчанию |
| `imalisherbekenov.WinBoost.locale.ru-RU.yaml` | издатель, название, лицензия, описание |
| `imalisherbekenov.WinBoost.installer.yaml` | архитектура, ссылка на релиз, SHA256 |

Тип установки — `portable`: WinBoost это самостоятельное приложение, а не
инсталлятор. `ElevationRequirement: elevatesSelf` описывает то, что приложение
само запрашивает права администратора при старте.

## Как отправить

1. Форкнуть `microsoft/winget-pkgs`.
2. Скопировать `3.1/` в `manifests/i/imalisherbekenov/WinBoost/3.1/`.
3. Открыть pull request. Автоматика проверит схему, скачает файл, сверит
   SHA256 и прогонит установку в песочнице.

Проще — через официальный инструмент, он же соберёт манифест и откроет PR:

```bash
winget install wingetcreate
wingetcreate update imalisherbekenov.WinBoost --version 3.2 --urls <ссылка на .exe> --submit
```

## Локальная проверка

```bash
winget validate --manifest 3.1
```

Валидатор не терпит подкаталогов рядом с манифестами. Локальный тулинг создаёт
здесь папку `.omc`, поэтому для проверки скопируйте три `.yaml` в пустую
директорию, иначе получите `Subdirectory not supported in manifest path`.

Полная проверка установкой требует настройки, которую включает администратор:

```bash
winget settings --enable LocalManifestFiles
```

Она разрешает ставить пакеты из произвольных локальных манифестов в обход
курируемого репозитория — включайте осознанно и выключайте после проверки.

## При выпуске новой версии

Меняются три вещи: `PackageVersion` во всех трёх файлах, `InstallerUrl` и
`InstallerSha256`. Хеш берётся так:

```bash
sha256sum dist/WinBoost-<версия>.exe
```

winget ждёт его заглавными буквами.
