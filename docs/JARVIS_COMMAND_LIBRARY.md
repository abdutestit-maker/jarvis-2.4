# JARVIS COMMAND LIBRARY

Библиотека реальных пользовательских команд для сверхспособного персонального агента JARVIS.

Формат записи:
- **Cat** — категория / подкатегория
- **Diff** — уровень сложности: L0 (мгновенно) … L7 (почти «сделай всё сам»)
- **Tools** — ожидаемые инструменты
- Флаги: Web / Code / Files / Vision / Voice / Long (1 = нужен)
- **Auto** — уровень автономии 0–10

Легенда уровней: L0 — мгновенная команда; L1 — простая задача; L2 — несколько действий; L3 — сложная задача; L4 — автономная mission; L5 — многоэтапная исследовательская/инженерная mission; L6 — долгосрочная автономная работа; L7 — «сделай всё сам».

Пометка SAFETY-SENSITIVE означает: capability потенциально опасна, для выполнения требуется отдельный permission/confirmation mechanism.

---

### 001 — Полная диагностика компьютера
«Джарвис, мой компьютер сегодня ведёт себя странно. Сам проведи диагностику: процессы, память, диски, события, автозагрузка. Найди наиболее вероятные причины, ничего опасного не меняй и составь план исправления.»
Cat: SYSTEM ADMIN | Diagnostic
Diff: L3 | Tools: tasklist, wmic/powershell, eventvwr, perfmon | Web0 Code1 Files1 Vision0 Long0 | Auto 8
Why: Ключевая «мусорная корзина» любого запроса — пользователь не знает, что именно проверить.
Caps: system inventory, log mining, health scoring, remediation planning

### 002 — Почему компьютер медленный
«Джарвис, разберись, почему мой компьютер тормозит. Проверь нагрузку на CPU, RAM, диск и сеть, найди виновника и предложи, что сделать.»
Cat: PERFORMANCE | Diagnostics
Diff: L2 | Tools: tasklist, resmon, wmic | Web0 Code1 Files0 Vision0 Long0 | Auto 6
Caps: bottleneck detection, process attribution

### 003 — Утренняя сводка состояния системы
«Джарвис, каждое утро в 9:00 давай мне короткую сводку: температура, память, диск, последние ошибки системы, есть ли обновления.»
Cat: SCHEDULED TASKS | Reporting
Diff: L2 | Tools: scheduler, hwmon, eventlog | Web1 Code1 Files0 Vision0 Long1 | Auto 8
Why: Постоянный фоновый ритуал, который делает ассистента частью дня.
Caps: scheduled digests, hardware telemetry

### 004 — Кто съедает всю память
«Джарвис, найди процессы, которые съедают больше всего оперативной памяти, и объясни, какие из них можно безопасно закрыть.»
Cat: PERFORMANCE | RAM
Diff: L1 | Tools: tasklist, powershell | Web0 Code1 Files0 Vision0 Long0 | Auto 5
Caps: memory profiling

### 005 — Нагрев компонентов
«Джарвис, проверь температуру процессора, видеокарты и дисков. Если что-то греется — найди причину и предложи решение.»
Cat: PERFORMANCE | Thermal
Diff: L2 | Tools: OpenHardwareMonitor, wmic, smartctl | Web0 Code1 Files0 Vision0 Long0 | Auto 6
Caps: thermal telemetry, cooling advice

### 006 — Нагрузка на диск
«Джарвис, диск работает на 100%, хотя я ничего не делаю. Найди процесс, который его нагружает, и объясни, нормально ли это.»
Cat: PERFORMANCE | Disk
Diff: L2 | Tools: resmon, process explorer | Web0 Code1 Files0 Vision0 Long0 | Auto 6
Caps: disk I/O attribution

### 007 — Разбор автозагрузки
«Джарвис, посмотри, что у меня в автозагрузке, отметь, что можно отключить без вреда, и скажи, сколько времени это сэкономит при старте.»
Cat: SYSTEM ADMIN | Startup
Diff: L2 | Tools: msconfig, taskmgr, registry | Web0 Code1 Files1 Vision0 Long0 | Auto 7
Caps: startup audit, boot time estimation

### 008 — Ускорить запуск Windows
«Джарвис, Windows у меня грузится 3 минуты. Найди причины медленного старта и сделай всё безопасное, чтобы ускорить.»
Cat: PERFORMANCE | Boot
Diff: L3 | Tools: eventlog, msconfig, defrag | Web1 Code1 Files1 Vision0 Long0 | Auto 7
Caps: boot-time optimization

### 009 — Программы, которые давно не открывались
«Джарвис, составь список программ, которыми я не пользовался больше полугода, и предложи, что можно удалить или отключить из автозагрузки.»
Cat: SYSTEM ADMIN | Cleanup
Diff: L2 | Tools: appx, registry, filesystem | Web0 Code1 Files1 Vision0 Long0 | Auto 6
Caps: app usage analytics, stale-app cleanup

### 010 — Найти дубликаты файлов
«Джарвис, найди все дубликаты файлов в папке Загрузки и в Документах, покажи, сколько места они занимают, и предложи, что удалить.»
Cat: FILE MANAGEMENT | Deduplication
Diff: L2 | Tools: hashing, python | Web0 Code1 Files1 Vision0 Long0 | Auto 6
Caps: duplicate detection, space reclaiming

### 011 — Самые тяжёлые файлы
«Джарвис, найди 50 самых больших файлов на диске и покажи, что из них можно смело удалить.»
Cat: STORAGE | Cleanup
Diff: L1 | Tools: filesystem walk | Web0 Code1 Files1 Vision0 Long0 | Auto 5
Caps: storage tree analysis

### 012 — Временные файлы
«Джарвис, почисти временные файлы, кэши и мусор, но сначала покажи, сколько места мы освободим.»
Cat: STORAGE | Cleanup
Diff: L2 | Tools: cleanmgr, temp dirs, browser caches | Web0 Code1 Files1 Vision0 Long0 | Auto 7
Caps: junk cleanup with preview

### 013 — Сводка по дискам
«Джарвис, покажи состояние всех дисков: сколько занято, сколько свободно, есть ли ошибки SMART, и какие диски пора менять.»
Cat: STORAGE | Health
Diff: L2 | Tools: smartctl, wmic, diskmgmt | Web0 Code1 Files0 Vision0 Long0 | Auto 5
Caps: disk health scoring, SMART telemetry

### 014 — Карта дискового пространства
«Джарвис, построй карту того, куда девается место на моём диске, с наглядной визуализацией по папкам.»
Cat: DATA VISUALIZATION | Storage
Diff: L2 | Tools: python, matplotlib, treemap | Web0 Code1 Files1 Vision0 Long0 | Auto 6
Caps: space visualization, treemap generation

### 015 — Что занимает место в системной папке
«Джарвис, у меня разрослась папка AppData. Разберись, что в ней лежит, что можно удалить, а что трогать нельзя.»
Cat: STORAGE | Cleanup
Diff: L2 | Tools: filesystem walk, registry | Web0 Code1 Files1 Vision0 Long0 | Auto 6
Caps: appdata analysis, safe-cleanup guidance

### 016 — Очистить корзину и старые точки восстановления
«Джарвис, очисти корзину и удали точки восстановления системы старше трёх месяцев.»
Cat: STORAGE | Cleanup
Diff: L2 | Tools: powershell, vssadmin | Web0 Code1 Files0 Vision0 Long0 | Auto 6
Caps: system cleanup automation

### 017 — Общий отчёт о здоровье системы
«Джарвис, собери всё в один отчёт: здоровье дисков, память, ошибки, обновления, срок службы. Сделай красивый HTML-отчёт и открой его.»
Cat: SYSTEM ADMIN | Reporting
Diff: L3 | Tools: сбор метрик, html-генерация | Web0 Code1 Files1 Vision0 Long0 | Auto 7
Caps: health report generation, HTML templating

### 018 — Список всех установленных программ
«Джарвис, выгрузи список всех установленных программ с версиями и датами установки в таблицу Excel.»
Cat: APPLICATIONS | Inventory
Diff: L1 | Tools: registry, xlsx | Web0 Code1 Files1 Vision0 Long0 | Auto 5
Caps: software inventory export

### 019 — Устаревшие программы
«Джарвис, найди программы, у которых давно вышли новые версии, и предложи обновить те, что стоит.»
Cat: APPLICATIONS | Updates
Diff: L2 | Tools: winget, web | Web1 Code1 Files0 Vision0 Long0 | Auto 6
Caps: outdated-app detection, update orchestration

### 020 — Массовое обновление программ
«Джарвис, обнови все программы, у которых есть обновления. Не обновляй ничего, что может сломать работу, и составь отчёт.»
Cat: APPLICATIONS | Updates
Diff: L3 | Tools: winget, choco | Web1 Code1 Files0 Vision0 Long0 | Auto 7
Caps: bulk package update, rollback planning

### 021 — Установка программы по названию
«Джарвис, установи мне [название программы], выбрав правильный источник, и настрой так, как обычно настраивают.»
Cat: APPLICATIONS | Install
Diff: L2 | Tools: winget, web | Web1 Code1 Files0 Vision0 Long0 | Auto 7
Caps: unattended install, source trust scoring

### 022 — Полное удаление программы
«Джарвис, удали [программу] полностью: вместе с настройками, кэшем и записями в реестре.»
Cat: APPLICATIONS | Uninstall
Diff: L2 | Tools: uninstaller, registry | Web0 Code1 Files1 Vision0 Long0 | Auto 7
Caps: deep uninstall

### 023 — Перенос программы на другой диск
«Джарвис, перенеси [программу] с C: на D:, чтобы освободить системный диск, не сломав её.»
Cat: APPLICATIONS | Migration
Diff: L3 | Tools: symlinks, registry | Web0 Code1 Files1 Vision0 Long0 | Auto 6
Caps: app relocation, symlink management

### 024 — Скрытые установщики
«Джарвис, найди в папке Загрузки установщики, которые я скачал и забыл, и спроси, что с ними делать.»
Cat: FILE MANAGEMENT | Hygiene
Diff: L1 | Tools: filesystem | Web0 Code1 Files1 Vision0 Long0 | Auto 4
Caps: download hygiene

### 025 — План ускорения ПК
«Джарвис, проведи полный аудит производительности и дай мне план из 10 шагов по ускорению, от простых к сложным.»
Cat: PERFORMANCE | Audit
Diff: L3 | Tools: сбор метрик | Web0 Code1 Files1 Vision0 Long0 | Auto 7
Caps: performance audit, prioritized action plan

### 026 — Разогнан ли мой компьютер
«Джарвис, проверь, работает ли мой CPU и GPU на заводских частотах, и расскажи, какой разгон безопасен для моей системы.»
Cat: PERFORMANCE | Overclocking
Diff: L2 | Tools: cpu-z, hwinfo | Web1 Code1 Files0 Vision0 Long0 | Auto 5
Caps: frequency telemetry, overclock guidance

### 027 — Сравнение с эталоном
«Джарвис, прогони мой компьютер через тесты производительности и сравни результат с другими похожими конфигурациями.»
Cat: PERFORMANCE | Benchmark
Diff: L3 | Tools: benchmark-утилиты, web | Web1 Code1 Files0 Vision0 Long0 | Auto 6
Caps: benchmarking, percentile comparison

### 028 — Сколько проживёт мой SSD
«Джарвис, оцени остаточный ресурс моего SSD по SMART-данным и скажи, сколько примерно он ещё проживёт.»
Cat: STORAGE | Health
Diff: L1 | Tools: smartctl | Web0 Code1 Files0 Vision0 Long0 | Auto 5
Caps: SSD endurance estimate

### 029 — Дефрагментация
«Джарвис, проверь, нужно ли дефрагментировать мои диски, и сделай это, если нужно.»
Cat: STORAGE | Maintenance
Diff: L1 | Tools: defrag | Web0 Code1 Files0 Vision0 Long0 | Auto 6
Caps: fragmentation analysis

### 030 — Ошибки диска
«Джарвис, проверь диски на ошибки и битые сектора, но так, чтобы это не заняло весь день.»
Cat: STORAGE | Health
Diff: L2 | Tools: chkdsk | Web0 Code1 Files0 Vision0 Long0 | Auto 6
Caps: surface scan, error repair

### 031 — Синхронизация двух папок
«Джарвис, настрой постоянную синхронизацию между папкой [А] и [Б], чтобы всё новое появлялось в обеих.»
Cat: FILE MANAGEMENT | Sync
Diff: L2 | Tools: rsync, watchdog | Web0 Code1 Files1 Vision0 Long0 | Auto 7
Caps: folder sync, conflict resolution

### 032 — Копия проекта на флешку
«Джарвис, скопируй мой проект на флешку, проверь, что все файлы скопировались правильно, и покажи отчёт.»
Cat: BACKUPS | Copy
Diff: L1 | Tools: robocopy | Web0 Code1 Files1 Vision0 Long0 | Auto 6
Caps: verified copy

### 033 — Массовое переименование
«Джарвис, переименуй все файлы в этой папке по шаблону [IMG_2023_001.jpg → фото_001.jpg], но сначала покажи, как будет выглядеть результат.»
Cat: FILE MANAGEMENT | Renaming
Diff: L2 | Tools: python, preview | Web0 Code1 Files1 Vision0 Long0 | Auto 6
Caps: batch rename with preview

### 034 — Привести папку в порядок
«Джарвис, у меня в папке Загрузки хаос. Разложи всё по подпапкам по типам и датам, но ничего не удаляй.»
Cat: FILE MANAGEMENT | Organization
Diff: L2 | Tools: python | Web0 Code1 Files1 Vision0 Long0 | Auto 7
Caps: auto-organization, dry-run planning

### 035 — Сортировка фото по датам
«Джарвис, разложи мои фотографии по папкам в формате Год/Месяц на основе даты съёмки из метаданных.»
Cat: FILE MANAGEMENT | Photos
Diff: L2 | Tools: exiftool, python | Web0 Code1 Files1 Vision0 Long0 | Auto 7
Caps: EXIF-based sorting

### 036 — Найти файл по описанию
«Джарвис, найди файл, который я потерял. Это был документ про отпуск, примерно с прошлого лета, вроде в Word.»
Cat: FILESYSTEM | Search
Diff: L2 | Tools: everything, семантика | Web0 Code1 Files1 Vision0 Long0 | Auto 6
Caps: fuzzy file search, semantic guessing

### 037 — Что изменилось в папке
«Джарвис, покажи, какие файлы в этой папке изменились за последнюю неделю.»
Cat: FILESYSTEM | Audit
Diff: L1 | Tools: find | Web0 Code1 Files1 Vision0 Long0 | Auto 4
Caps: change detection

### 038 — Папка с одинаковыми именами
«Джарвис, найди все файлы с одинаковыми именами в разных папках и покажи, чем они отличаются.»
Cat: FILE MANAGEMENT | Deduplication
Diff: L2 | Tools: hashing | Web0 Code1 Files1 Vision0 Long0 | Auto 6
Caps: near-duplicate detection, diff preview

### 039 — Сравнение двух файлов
«Джарвис, сравни эти два документа и покажи мне все отличия простым языком.»
Cat: DOCUMENTS | Diff
Diff: L1 | Tools: diff, python | Web0 Code1 Files1 Vision0 Long0 | Auto 5
Caps: text diff, plain-language summary

### 040 — Сравнение двух папок
«Джарвис, сравни две папки и скажи, какие файлы есть только в одной, какие отличаются и какие одинаковые.»
Cat: FILE MANAGEMENT | Diff
Diff: L1 | Tools: robocopy /L, python | Web0 Code1 Files1 Vision0 Long0 | Auto 5
Caps: folder diff

### 041 — Архив проекта
«Джарвис, заархивируй мой проект с паролем и проверь, что архив открывается.»
Cat: FILE MANAGEMENT | Archive
Diff: L1 | Tools: 7z | Web0 Code1 Files1 Vision0 Long0 | Auto 6
Caps: encrypted archiving, archive verification

### 042 — Распаковать архив с мусором
«Джарвис, распакуй этот архив в отдельную папку, но сначала покажи, что внутри, чтобы туда не просочился мусор.»
Cat: FILE MANAGEMENT | Archive
Diff: L1 | Tools: 7z, предпросмотр | Web0 Code1 Files1 Vision0 Long0 | Auto 5
Caps: safe extraction preview

### 043 — Сломанный архив
«Джарвис, этот архив не открывается. Попробуй починить его или вытащить из него что можно.»
Cat: ERROR RECOVERY | Archive
Diff: L2 | Tools: 7z repair, python | Web0 Code1 Files1 Vision0 Long0 | Auto 6
Caps: archive recovery

### 044 — Восстановление удалённых файлов
«Джарвис, я случайно удалил файлы. Попробуй восстановить их, но сначала скажи, какие есть шансы.»
Cat: ERROR RECOVERY | Data
Diff: L3 | Tools: photorec, shadow copies | Web0 Code1 Files1 Vision0 Long0 | Auto 6
Caps: deleted-file recovery, shadow-copy restore

### 045 — Скрытые файлы
«Джарвис, покажи мне скрытые и системные файлы в этой папке и объясни, что каждый из них делает.»
Cat: FILESYSTEM | Visibility
Diff: L1 | Tools: ls -la, powershell | Web0 Code1 Files1 Vision0 Long0 | Auto 4
Caps: hidden-file disclosure with explanation

### 046 — Что за файл
«Джарвис, посмотри на этот файл и скажи, что это, откуда он мог взяться и можно ли его удалить.»
Cat: FILESYSTEM | Analysis
Diff: L1 | Tools: file, strings, metadata | Web0 Code1 Files1 Vision0 Long0 | Auto 5
Caps: file fingerprinting, provenance guess

### 047 — Текстовый файл с кодировкой-кракозяброй
«Джарвис, этот текстовый файл открывается кракозябрами. Определи кодировку и пересохрани правильно.»
Cat: ERROR RECOVERY | Encoding
Diff: L1 | Tools: chardet, python | Web0 Code1 Files1 Vision0 Long0 | Auto 5
Caps: encoding detection, re-encoding

### 048 — Перенос всей папки с сохранением структуры
«Джарвис, перенеси папку [А] в [Б] так, чтобы внутри ничего не сломалось, и проверь целостность после переноса.»
Cat: FILE MANAGEMENT | Move
Diff: L1 | Tools: robocopy | Web0 Code1 Files1 Vision0 Long0 | Auto 6
Caps: safe move with verification

### 049 — Скачивание файла по ссылке
«Джарвис, скачай файл по этой ссылке в папку [А], проверь, что он не повреждён, и распакуй, если это архив.»
Cat: WEB | Download
Diff: L1 | Tools: curl, web | Web1 Code1 Files1 Vision0 Long0 | Auto 6
Caps: download + integrity check + extraction

### 050 — Проверить ссылку на безопасность
«Джарвис, проверь эту ссылку: куда она ведёт, не фишинг ли это, стоит ли её открывать.»
Cat: SECURITY | Link analysis
Diff: L1 | Tools: web, whois, vt | Web1 Code1 Files0 Vision0 Long0 | Auto 5
Caps: URL reputation, redirect tracing

### 051 — Скачать все картинки со страницы
«Джарвис, скачай все изображения с этой страницы в папку [А], переименуй по порядку и убери мелкий мусор.»
Cat: WEB | Scraping
Diff: L2 | Tools: curl, python, bs4 | Web1 Code1 Files1 Vision0 Long0 | Auto 6
Caps: media harvesting

### 052 — Сохранить страницу целиком
«Джарвис, сохрани эту страницу полностью, включая картинки и стили, чтобы она открывалась без интернета.»
Cat: WEB | Archiving
Diff: L2 | Tools: single-file, wget | Web1 Code1 Files1 Vision0 Long0 | Auto 6
Caps: page archiving

### 053 — Веб-архив для оффлайна
«Джарвис, сделай оффлайн-копию этого сайта глубиной в два уровня ссылок, чтобы я мог читать его без интернета.»
Cat: WEB | Archiving
Diff: L3 | Tools: wget mirror | Web1 Code1 Files1 Vision0 Long0 | Auto 7
Caps: site mirroring

### 054 — Сравнить два сайта
«Джарвис, сравни эти два сайта: чем они похожи, чем отличаются, какой сделан лучше с точки зрения UX.»
Cat: WEB | Analysis
Diff: L2 | Tools: browser, screenshots | Web1 Code0 Files1 Vision1 Long0 | Auto 6
Caps: comparative site analysis

### 055 — Скриншот сайта
«Джарвис, сделай скриншот этого сайта в полный рост и сохрани его.»
Cat: BROWSER AUTOMATION | Screenshot
Diff: L1 | Tools: headless browser | Web1 Code1 Files1 Vision1 Long0 | Auto 5
Caps: full-page screenshot

### 056 — Проверить, что сайт лежит
«Джарвис, проверь, почему не открывается [сайт]: недоступен ли он вообще, блокирует ли его провайдер или проблема у меня.»
Cat: NETWORK DIAGNOSTICS | Connectivity
Diff: L2 | Tools: ping, dns, traceroute, curl | Web1 Code0 Files0 Vision0 Long0 | Auto 6
Caps: outage triage, geo-availability check

### 057 — Скорость интернета
«Джарвис, замерь скорость моего интернета в обе стороны и сравни с тем, что обещает тариф.»
Cat: NETWORK DIAGNOSTICS | Speed
Diff: L1 | Tools: speedtest | Web1 Code1 Files0 Vision0 Long0 | Auto 5
Caps: bandwidth measurement, tariff comparison

### 058 — Проверить Wi-Fi
«Джарвис, проанализируй мой Wi-Fi: сила сигнала, соседние сети, занятые каналы, и предложи лучший канал и место для роутера.»
Cat: NETWORK DIAGNOSTICS | Wi-Fi
Diff: L2 | Tools: wifi-анализ | Web1 Code1 Files0 Vision0 Long0 | Auto 6
Caps: RF analysis, channel planning

### 059 — Кто подключён к моему Wi-Fi
«Джарвис, посмотри, какие устройства подключены к моему роутеру, и отметь подозрительные.»
Cat: SECURITY | Network
Diff: L2 | Tools: nmap, arp, роутер API | Web1 Code1 Files0 Vision0 Long0 | Auto 6
Caps: device inventory, rogue detection

### 060 — Кто занимает мой интернет
«Джарвис, найди, какое устройство или программа съедает весь мой интернет-трафик прямо сейчас.»
Cat: NETWORK DIAGNOSTICS | Usage
Diff: L2 | Tools: netstat, tcpview | Web0 Code1 Files0 Vision0 Long0 | Auto 5
Caps: per-process bandwidth attribution

### 061 — Трафик по приложениям за неделю
«Джарвис, собери статистику, какие приложения больше всего тратили интернет за последнюю неделю, и покажи в виде графика.»
Cat: NETWORK DIAGNOSTICS | Analytics
Diff: L3 | Tools: netmon, python | Web0 Code1 Files1 Vision0 Long0 | Auto 6
Caps: traffic analytics, chart generation

### 062 — Проверка DNS
«Джарвис, проверь, не ворует ли мой DNS запросы: сравни ответы моего провайдера с публичными DNS.»
Cat: SECURITY | DNS
Diff: L2 | Tools: nslookup, dig, web | Web1 Code1 Files0 Vision0 Long0 | Auto 6
Caps: DNS health check, poisoning detection

### 063 — VPN: нужен ли он мне
«Джарвис, проанализируй, какие сайты я посещаю чаще всего, и скажи, где мне реально нужен VPN, а где нет.»
Cat: PRIVACY | VPN advisory
Diff: L2 | Tools: история, web | Web1 Code1 Files1 Vision0 Long0 | Auto 5
Caps: privacy risk scoring, VPN recommendation

### 064 — Настройка VPN
«Джарвис, настрой мне VPN-подключение по этим данным и проверь, что трафик реально шифруется и не утекает.»
Cat: SECURITY | VPN
Diff: L2 | Tools: openvpn, wireguard, тесты утечек | Web1 Code1 Files1 Vision0 Long0 | Auto 7
Caps: VPN setup, leak testing

### 065 — Проверка утечки данных по почте
«Джарвис, проверь, не светилась ли моя почта в утечках данных, и скажи, что мне поменять.»
Cat: SECURITY | Breach check
Diff: L1 | Tools: web | Web1 Code0 Files0 Vision0 Long0 | Auto 4
Caps: breach lookup, exposure triage

### 066 — Аудит паролей
«Джарвис, найди в моём менеджере паролей пароли, которые повторяются, слишком слабые или старые, и предложи замену.»
Cat: SECURITY | Passwords
Diff: L2 | Tools: password manager API | Web0 Code1 Files1 Vision0 Long0 | Auto 6
Caps: password strength audit, reuse detection

### 067 — Генератор надёжных паролей
«Джарвис, сгенерируй мне 10 сложных паролей и сохрани их в менеджер паролей.»
Cat: SECURITY | Passwords
Diff: L0 | Tools: генератор | Web0 Code0 Files0 Vision0 Long0 | Auto 4
Caps: password generation

### 068 — Включить 2FA везде
«Джарвис, проверь мои аккаунты и скажи, где у меня не включена двухфакторная аутентификация, и подготовь инструкцию по включению.»
Cat: SECURITY | Accounts
Diff: L3 | Tools: web | Web1 Code0 Files0 Vision0 Long0 | Auto 5
Caps: 2FA coverage audit, step-by-step guides

### 069 — Настройка 2FA
«Джарвис, настрой двухфакторную аутентификацию для моего аккаунта [X] с помощью аутентификатора.»
Cat: SECURITY | Accounts
Diff: L3 | Tools: browser, totp | Web1 Code1 Files1 Vision0 Long0 | Auto 6
Caps: TOTP enrollment automation

### 070 — Проверка антивируса
«Джарвис, проверь, что мой антивирус работает, базы свежие, защита в реальном времени включена.»
Cat: SECURITY | Endpoint
Diff: L1 | Tools: wmic, powershell | Web0 Code1 Files0 Vision0 Long0 | Auto 4
Caps: AV health check

### 071 — Сканирование на вирусы
«Джарвис, проведи полное сканирование системы на вредоносное ПО в фоне и сообщи, если найдёшь что-то подозрительное.»
Cat: SECURITY | Malware
Diff: L3 | Tools: defender, малварь-сканеры | Web1 Code1 Files1 Vision0 Long0 | Auto 7
Caps: deep malware scan, quarantine handling

### 072 — Подозрительный процесс
«Джарвис, у меня в диспетчере задач процесс с непонятным именем. Определи, что это, откуда запущен и стоит ли его бояться.»
Cat: SECURITY | Analysis
Diff: L2 | Tools: process explorer, strings, web | Web1 Code1 Files1 Vision0 Long0 | Auto 6
Caps: process reputation lookup, binary analysis

### 073 — Проверить USB-флешку
«Джарвис, проверь эту флешку на вирусы и покажи, какие файлы на ней есть и можно ли ей доверять.»
Cat: SECURITY | Removable media
Diff: L1 | Tools: сканер, filesystem | Web0 Code1 Files1 Vision0 Long0 | Auto 5
Caps: removable media vetting

### 074 — Публичные файлы
«Джарвис, найди все папки на моём компьютере, которые расшарены по сети, и проверь, не открыт ли лишний доступ.»
Cat: SECURITY | Exposure
Diff: L2 | Tools: net share, smb | Web0 Code1 Files0 Vision0 Long0 | Auto 6
Caps: share exposure audit

### 075 — Открытые порты
«Джарвис, проверь, какие порты открыты на моём компьютере, какие службы их слушают и не опасно ли это.»
Cat: SECURITY | Network
Diff: L2 | Tools: netstat, nmap | Web0 Code1 Files0 Vision0 Long0 | Auto 6
Caps: open port audit, service mapping

### 076 — Файрвол
«Джарвис, проверь настройки моего брандмауэра и скажи, какие правила можно убрать, а какие добавить.»
Cat: SECURITY | Firewall
Diff: L2 | Tools: netsh, firewall API | Web0 Code1 Files0 Vision0 Long0 | Auto 6
Caps: firewall rule audit

### 077 — Шпионские программы в автозагрузке
«Джарвис, проверь автозагрузку и службы на подозрительные записи, которые туда не попадают при обычной установке.»
Cat: SECURITY | Persistence
Diff: L2 | Tools: autoruns, registry | Web0 Code1 Files1 Vision0 Long0 | Auto 6
Caps: persistence audit, suspicious-entry detection

### 078 — Последние изменения системы
«Джарвис, покажи, что изменилось в системе за последние 24 часа: установленные программы, обновления, изменения реестра.»
Cat: SYSTEM ADMIN | Audit
Diff: L2 | Tools: eventlog, setupapi, registry | Web0 Code1 Files0 Vision0 Long0 | Auto 5
Caps: change log reconstruction

### 079 — Правда ли обновилась Windows
«Джарвис, проверь, какие обновления Windows установлены, какие пропущены и нет ли среди них критических.»
Cat: SYSTEM ADMIN | Updates
Diff: L1 | Tools: wuapi, powershell | Web1 Code1 Files0 Vision0 Long0 | Auto 5
Caps: patch-level audit, critical update flagging

### 080 — Ошибки в журнале событий
«Джарвис, просмотри журнал событий за последнюю неделю, сгруппируй ошибки по типам и скажи, на какие стоит обратить внимание.»
Cat: LOG ANALYSIS | Events
Diff: L2 | Tools: eventvwr, powershell | Web0 Code1 Files1 Vision0 Long0 | Auto 6
Caps: log clustering, error prioritization

### 081 — Синие экраны
«Джарвис, у меня иногда падает система в синий экран. Проанализируй дампы памяти и найди причину.»
Cat: ERROR RECOVERY | BSOD
Diff: L3 | Tools: windbg, minidump | Web1 Code1 Files1 Vision0 Long0 | Auto 7
Caps: crash dump analysis, driver attribution

### 082 — Ошибки драйверов
«Джарвис, проверь, нет ли проблем с драйверами, и обнови те, что устарели.»
Cat: SYSTEM ADMIN | Drivers
Diff: L2 | Tools: pnputil, devcon, winget | Web1 Code1 Files0 Vision0 Long0 | Auto 6
Caps: driver health check, driver update

### 083 — Устройства с проблемами
«Джарвис, покажи все устройства в диспетчере с жёлтым восклицательным знаком и попробуй починить их.»
Cat: SYSTEM ADMIN | Devices
Diff: L2 | Tools: devmgmt, pnputil | Web0 Code1 Files0 Vision0 Long0 | Auto 6
Caps: device error triage

### 084 — Не работает Bluetooth
«Джарвис, Bluetooth перестал находить устройства. Диагностируй и почини.»
Cat: ERROR RECOVERY | Devices
Diff: L2 | Tools: services, driver | Web0 Code1 Files0 Vision0 Long0 | Auto 6
Caps: bluetooth troubleshooting

### 085 — Не работает микрофон
«Джарвис, микрофон перестал работать. Проверь драйверы, настройки приватности и уровень сигнала.»
Cat: ERROR RECOVERY | Audio
Diff: L2 | Tools: sound settings, driver | Web0 Code1 Files0 Vision0 Long0 | Auto 6
Caps: audio device troubleshooting

### 086 — Нет звука
«Джарвис, пропал звук. Пройди по всем шагам: устройство вывода, громкость, службы, драйверы — и почини.»
Cat: ERROR RECOVERY | Audio
Diff: L2 | Tools: sound, services, driver | Web0 Code1 Files0 Vision0 Long0 | Auto 6
Caps: audio chain diagnosis

### 087 — Не работает камера
«Джарвис, веб-камера не работает. Проверь, не занята ли она другим приложением, драйверы и настройки конфиденциальности.»
Cat: ERROR RECOVERY | Devices
Diff: L2 | Tools: devmgmt, settings | Web0 Code1 Files0 Vision0 Long0 | Auto 6
Caps: camera troubleshooting

### 088 — Принтер не печатает
«Джарвис, принтер не печатает. Проверь очередь печати, драйверы, подключение и почини.»
Cat: ERROR RECOVERY | Printing
Diff: L2 | Tools: printui, services | Web0 Code1 Files0 Vision0 Long0 | Auto 6
Caps: print queue repair

### 089 — Приложение не запускается
«Джарвис, программа [X] не запускается. Найди причину: проверь журнал, зависимости, права, .NET и прочее. Почини.»
Cat: ERROR RECOVERY | Apps
Diff: L3 | Tools: eventlog, procmon | Web1 Code1 Files1 Vision0 Long0 | Auto 7
Caps: app-launch forensics, dependency repair

### 090 — Программа зависает
«Джарвис, программа [X] регулярно зависает. Собери дамп, проанализируй, где она застревает, и предложи решение.»
Cat: DEBUGGING | Hangs
Diff: L3 | Tools: procdump, windbg | Web1 Code1 Files1 Vision0 Long0 | Auto 7
Caps: hang analysis, stack capture

### 091 — Сбой после обновления
«Джарвис, после последнего обновления всё сломалось. Выясни, что изменилось, и верни всё как было или почини.»
Cat: ERROR RECOVERY | Updates
Diff: L3 | Tools: update history, restore points | Web1 Code1 Files1 Vision0 Long0 | Auto 7
Caps: update rollback, regression hunting

### 092 — Создание точки восстановления
«Джарвис, создай точку восстановления системы перед тем, как я буду что-то менять.»
Cat: SYSTEM ADMIN | Restore
Diff: L0 | Tools: systemrestore | Web0 Code1 Files0 Vision0 Long0 | Auto 4
Caps: restore point creation

### 093 — Автовосстановление системы
«Джарвис, настрой автоматическое создание точек восстановления перед каждым крупным обновлением.»
Cat: SYSTEM ADMIN | Restore
Diff: L2 | Tools: task scheduler, systemrestore | Web0 Code1 Files0 Vision0 Long0 | Auto 6
Caps: scheduled snapshotting

### 094 — Диск переполнен, система тормозит
«Джарвис, у меня на C: осталось 2 гигабайта, и всё тормозит. Найди, что можно освободить без риска, и сделай это.»
Cat: STORAGE | Emergency
Diff: L3 | Tools: анализ, очистка | Web0 Code1 Files1 Vision0 Long0 | Auto 7
Caps: emergency space reclamation

### 095 — Проверить целостность системы
«Джарвис, проверь целостность системных файлов Windows и почини повреждённые.»
Cat: SYSTEM ADMIN | Integrity
Diff: L2 | Tools: sfc, dism | Web0 Code1 Files0 Vision0 Long0 | Auto 6
Caps: system file integrity restore

### 096 — Чистая загрузка
«Джарвис, выполни чистую загрузку Windows, чтобы понять, какая программа мешает системе, и верни всё обратно.»
Cat: DEBUGGING | Isolation
Diff: L3 | Tools: msconfig | Web0 Code1 Files0 Vision0 Long0 | Auto 7
Caps: clean-boot isolation testing

### 097 — Фоновые программы
«Джарвис, покажи, какие программы работают в фоне прямо сейчас, и скажи, какие из них можно закрыть без последствий.»
Cat: COMPUTER CONTROL | Processes
Diff: L1 | Tools: tasklist | Web0 Code1 Files0 Vision0 Long0 | Auto 5
Caps: background app audit

### 098 — Сводка запущенных окон
«Джарвис, расскажи, какие окна у меня сейчас открыты и в каком приложении я работаю.»
Cat: COMPUTER CONTROL | Windows
Diff: L0 | Tools: win32 api | Web0 Code1 Files0 Vision0 Long0 | Auto 4
Caps: window inventory, focus detection

### 099 — Закрыть всё лишнее
«Джарвис, закрой все окна, кроме моего редактора и браузера, и спроси перед закрытием, если что-то не сохранено.»
Cat: COMPUTER CONTROL | Windows
Diff: L2 | Tools: win32 api | Web0 Code1 Files0 Vision0 Long0 | Auto 6
Caps: safe bulk close, unsaved-work detection

### 100 — Окно не закрывается
«Джарвис, у меня окно программы не закрывается. Принудительно заверши её, но сначала проверь, не потеряю ли я данные.»
Cat: ERROR RECOVERY | Apps
Diff: L1 | Tools: taskkill, проверка сохранности | Web0 Code1 Files0 Vision0 Long0 | Auto 5
Caps: graceful force-quit

### 101 — Свернуть всё, кроме нужного
«Джарвис, сверни все окна, открой [программу] и разверни её на весь экран.»
Cat: COMPUTER CONTROL | Windows
Diff: L1 | Tools: win32 api | Web0 Code1 Files0 Vision0 Long0 | Auto 5
Caps: window orchestration

### 102 — Расположить окна рядом
«Джарвис, расположи окна [A] и [B] рядом друг с другом на пол-экрана каждое.»
Cat: COMPUTER CONTROL | Layout
Diff: L1 | Tools: win32 api | Web0 Code1 Files0 Vision0 Long0 | Auto 5
Caps: window tiling

### 103 — Быстро переключить раскладку
«Джарвис, переключи раскладку клавиатуры на английскую и обратно, когда я скажу.»
Cat: COMPUTER CONTROL | Input
Diff: L0 | Tools: win32 api | Web0 Code1 Files0 Vision0 Long0 | Auto 4
Caps: input switching

### 104 — Набрать текст за меня
«Джарвис, набери вот этот текст в активном окне.»
Cat: COMPUTER CONTROL | Input
Diff: L0 | Tools: keyboard automation | Web0 Code1 Files0 Vision0 Long0 | Auto 4
Caps: text typing, keystroke injection

### 105 — Эмуляция нажатий
«Джарвис, выполни последовательность нажатий: Ctrl+S, подожди, потом Alt+F4.»
Cat: COMPUTER CONTROL | Input
Diff: L0 | Tools: keyboard automation | Web0 Code1 Files0 Vision0 Long0 | Auto 4
Caps: macro keystrokes

### 106 — Записать и повторить действия
«Джарвис, запиши, что я делаю в программе [X], и потом повторяй это по моей команде.»
Cat: UI AUTOMATION | Macro
Diff: L4 | Tools: recorder, ui automation | Web0 Code1 Files0 Vision1 Long0 | Auto 7
Caps: macro recording, playback automation

### 107 — Управление мышью
«Джарвис, перемести курсор на кнопку «Сохранить» и нажми на неё.»
Cat: COMPUTER CONTROL | Mouse
Diff: L0 | Tools: mouse automation, vision | Web0 Code1 Files0 Vision1 Long0 | Auto 5
Caps: visual cursor control

### 108 — Скриншот экрана
«Джарвис, сделай скриншот экрана и сохрани в [папка].»
Cat: COMPUTER CONTROL | Screenshot
Diff: L0 | Tools: screenshot | Web0 Code0 Files1 Vision0 Long0 | Auto 3
Caps: screen capture

### 109 — Скриншот области
«Джарвис, сделай скриншот области, которую я укажу, и сразу открой его для редактирования.»
Cat: COMPUTER CONTROL | Screenshot
Diff: L1 | Tools: screenshot, editor | Web0 Code0 Files1 Vision1 Long0 | Auto 4
Caps: region capture

### 110 — Что сейчас на экране
«Джарвис, посмотри на мой экран и скажи, что там происходит.»
Cat: SCREEN UNDERSTANDING | Analysis
Diff: L1 | Tools: vision, screenshot | Web0 Code0 Files0 Vision1 Long0 | Auto 4
Caps: screen comprehension, context awareness

### 111 — Найди кнопку на экране
«Джарвис, найди на экране кнопку «Отправить» и нажми её.»
Cat: UI AUTOMATION | Visual search
Diff: L2 | Tools: vision, mouse | Web0 Code0 Files0 Vision1 Long0 | Auto 6
Caps: visual element location, UI interaction

### 112 — Прочитать, что написано на экране
«Джарвис, прочитай текст из этого окна и сохрани его в файл.»
Cat: OCR | Screen
Diff: L1 | Tools: ocr, screenshot | Web0 Code0 Files1 Vision1 Long0 | Auto 4
Caps: screen OCR

### 113 — Следить за экраном
«Джарвис, наблюдай за моим экраном и предупреди, если появится окно с ошибкой или обновлением.»
Cat: MONITORING | Screen
Diff: L3 | Tools: vision loop | Web0 Code1 Files0 Vision1 Long1 | Auto 7
Caps: ambient screen monitoring, alerting

### 114 — Темы и оформление
«Джарвис, подбери тёмную тему для всей системы и настрой её единообразно.»
Cat: PERSONALIZATION | Appearance
Diff: L1 | Tools: settings, registry | Web0 Code1 Files0 Vision0 Long0 | Auto 5
Caps: theme orchestration

### 115 — Скринсейвер и блокировка
«Джарвис, настрой блокировку экрана через 5 минут бездействия и красивую заставку.»
Cat: PERSONALIZATION | Security
Diff: L1 | Tools: settings | Web0 Code1 Files0 Vision0 Long0 | Auto 5
Caps: lock-screen configuration

### 116 — Автоблокировка при уходе
«Джарвис, настрой автоблокировку экрана, если я отхожу от компьютера и камера не видит меня.»
Cat: SECURITY | Presence
Diff: L3 | Tools: камера, vision, settings | Web0 Code1 Files0 Vision1 Long0 | Auto 6
Caps: presence-based locking SAFETY-SENSITIVE (камера — только с разрешения пользователя)

### 117 — Пробуждение по голосу
«Джарвис, настрой пробуждение по голосовой команде «Джарвис» из любого состояния.»
Cat: VOICE | Wake word
Diff: L2 | Tools: microphone, стt | Web0 Code1 Files0 Voice1 Long1 | Auto 6
Caps: wake-word detection, always-on listening

### 118 — Голосовое управление компьютером
«Джарвис, дальше я буду говорить команды голосом, а ты выполняй их на компьютере.»
Cat: VOICE | Control
Diff: L3 | Tools: mic, stt, computer control | Web0 Code1 Files0 Voice1 Long1 | Auto 8
Caps: voice-to-action pipeline

### 119 — Озвучить текст
«Джарвис, прочитай вслух этот документ.»
Cat: SPEECH | TTS
Diff: L0 | Tools: tts | Web0 Code0 Files1 Voice0 Long0 | Auto 3
Caps: text-to-speech

### 120 — Озвучить с естественным голосом
«Джарвис, озвучь эту статью голосом, который звучит как живой человек, и сохрани в mp3.»
Cat: SPEECH | TTS
Diff: L1 | Tools: neural tts | Web1 Code1 Files1 Voice0 Long0 | Auto 4
Caps: neural voice synthesis, audio export

### 121 — Озвучить голосом пользователя
«Джарвис, сделай мой голосовой клон по этим записям и озвучь им мою презентацию.»
Cat: VOICE | Voice cloning
Diff: L4 | Tools: voice cloning | Web1 Code1 Files1 Voice1 Long1 | Auto 6
Caps: voice cloning SAFETY-SENSITIVE (только голос самого пользователя)

### 122 — Голосовая заметка в текст
«Джарвис, расшифруй мою голосовую заметку в текст и разложи по пунктам.»
Cat: VOICE | STT
Diff: L1 | Tools: stt | Web1 Code1 Files1 Voice1 Long0 | Auto 5
Caps: speech-to-text, note structuring

### 123 — Транскрибация совещания
«Джарвис, запиши наш разговор, расшифруй его и составь протокол с решениями и задачами.»
Cat: VOICE | Meeting
Diff: L2 | Tools: stt, speaker diarization | Web1 Code1 Files1 Voice1 Long0 | Auto 6
Caps: meeting transcription, action-item extraction

### 124 — Синхронный перевод голоса
«Джарвис, переводи мне в реальном времени всё, что говорят в этом видео.»
Cat: VOICE | Translation
Diff: L3 | Tools: stt, mt, tts | Web1 Code1 Files0 Voice1 Long1 | Auto 6
Caps: live interpretation

### 125 — Найти все вкладки браузера
«Джарвис, покажи список всех моих открытых вкладок и сгруппируй их по темам.»
Cat: BROWSER | Tabs
Diff: L1 | Tools: browser api | Web0 Code1 Files0 Vision0 Long0 | Auto 4
Caps: tab inventory, topic clustering

### 126 — Закрыть дубли вкладок
«Джарвис, закрой вкладки-дубликаты и вкладки, которые я не открывал больше суток.»
Cat: BROWSER | Tabs
Diff: L1 | Tools: browser api | Web0 Code1 Files0 Vision0 Long0 | Auto 5
Caps: tab deduplication, tab hygiene

### 127 — Закладки в порядок
«Джарвис, разбери мои закладки: убери битые, сгруппируй по темам, удали дубли.»
Cat: BROWSER | Bookmarks
Diff: L2 | Tools: browser api | Web0 Code1 Files0 Vision0 Long0 | Auto 6
Caps: bookmark cleanup, broken-link detection

### 128 — История браузера
«Джарвис, покажи, какие сайты я посещал на этой неделе, и сделай выжимку, на что я трачу время.»
Cat: BROWSER | History
Diff: L1 | Tools: browser history | Web0 Code1 Files1 Vision0 Long0 | Auto 5
Caps: browsing analytics, time audit

### 129 — Открыть сайт
«Джарвис, открой [сайт] и покажи мне его главную страницу.»
Cat: BROWSER | Navigation
Diff: L0 | Tools: browser | Web1 Code0 Files0 Vision0 Long0 | Auto 3
Caps: page navigation

### 130 — Искать в интернете
«Джарвис, поищи в интернете [запрос] и дай мне выжимку из лучших результатов.»
Cat: INTERNET RESEARCH | Search
Diff: L1 | Tools: web search | Web1 Code0 Files0 Vision0 Long0 | Auto 4
Caps: web search, result synthesis

### 131 — Найти ответ на вопрос
«Джарвис, ответь на вопрос: [вопрос]. Поищи в интернете, сверь несколько источников и дай точный ответ со ссылками.»
Cat: INTERNET RESEARCH | Q&A
Diff: L2 | Tools: web search | Web1 Code0 Files0 Vision0 Long0 | Auto 5
Caps: sourced Q&A, cross-source verification

### 132 — Проверить факт
«Джарвис, проверь, правда ли, что [утверждение]. Найди первоисточник.»
Cat: INTERNET RESEARCH | Fact-check
Diff: L2 | Tools: web search | Web1 Code0 Files0 Vision0 Long0 | Auto 5
Caps: fact verification, primary sourcing

### 133 — Свежие новости по теме
«Джарвис, собери свежие новости по теме [X] за последние 24 часа и сделай дайджест из 10 пунктов.»
Cat: INTERNET RESEARCH | News
Diff: L1 | Tools: web, rss | Web1 Code0 Files1 Vision0 Long0 | Auto 5
Caps: news aggregation, digest generation

### 134 — Ежедневный новостной дайджест
«Джарвис, каждое утро присылай мне дайджест новостей по моим темам: AI, космос, экономика.»
Cat: SCHEDULED TASKS | News
Diff: L2 | Tools: scheduler, web, rss | Web1 Code1 Files1 Vision0 Long0 | Long1 | Auto 8
Caps: personalized news pipeline

### 135 — Разбор статьи
«Джарвис, прочитай эту статью и объясни мне её главную мысль простыми словами.»
Cat: SUMMARIZATION | Article
Diff: L1 | Tools: web, llm | Web1 Code0 Files0 Vision0 Long0 | Auto 4
Caps: article summarization, simplification

### 136 — Конспект длинного текста
«Джарвис, сделай конспект этого документа по главам с ключевыми тезисами.»
Cat: SUMMARIZATION | Documents
Diff: L1 | Tools: llm | Web0 Code1 Files1 Vision0 Long0 | Auto 5
Caps: structured summarization

### 137 — Сравнение источников
«Джарвис, найди 5 разных источников по теме [X], сравни их позиции и покажи, где они расходятся.»
Cat: INTERNET RESEARCH | Synthesis
Diff: L3 | Tools: web search | Web1 Code0 Files0 Vision0 Long0 | Auto 6
Caps: multi-source comparison, contradiction detection

### 138 — Исследование темы
«Джарвис, проведи исследование по теме [X]: собери информацию из разных источников, структурируй и сохрани в документ.»
Cat: DEEP RESEARCH | General
Diff: L3 | Tools: web, документы | Web1 Code1 Files1 Vision0 Long0 | Auto 7
Caps: research pipeline, report authoring

### 139 — Глубокое исследование с отчётом
«Джарвис, исследуй [тему] на уровне эксперта: история, современное состояние, тренды, ключевые люди, риски. Сделай отчёт на 20 страниц с источниками.»
Cat: DEEP RESEARCH | Expert
Diff: L5 | Tools: web, llm, документы | Web1 Code1 Files1 Vision0 Long1 | Auto 8
Caps: expert-level research, long-form report

### 140 — Научный обзор литературы
«Джарвис, найди научные статьи по теме [X] за последние 3 года, прочитай аннотации и составь обзор с ключевыми выводами.»
Cat: RESEARCH ASSISTANT | Literature
Diff: L4 | Tools: scholar, pdf | Web1 Code1 Files1 Vision0 Long1 | Auto 8
Caps: literature review, citation management

### 141 — Подбор источников для статьи
«Джарвис, подбери 20 надёжных источников для моей статьи на тему [X] и оформи их в список с аннотациями.»
Cat: RESEARCH ASSISTANT | Sourcing
Diff: L2 | Tools: web | Web1 Code0 Files1 Vision0 Long0 | Auto 6
Caps: source curation, annotated bibliography

### 142 — Проверка цитат
«Джарвис, проверь цитаты в моей статье: найди оригиналы и отметь, где текст искажён.»
Cat: RESEARCH ASSISTANT | Verification
Diff: L3 | Tools: web | Web1 Code0 Files1 Vision0 Long0 | Auto 7
Caps: quote verification, attribution audit

### 143 — Кто это
«Джарвис, найди информацию об этом человеке: кто он, чем известен, стоит ли ему доверять.»
Cat: INTERNET RESEARCH | People
Diff: L1 | Tools: web search | Web1 Code0 Files0 Vision0 Long0 | Auto 4
Caps: people lookup, reputation check

### 144 — Что это за компания
«Джарвис, собери досье на компанию [X]: владельцы, финансы, новости, судебные дела, репутация.»
Cat: INTERNET RESEARCH | Business
Diff: L3 | Tools: web, реестры | Web1 Code0 Files1 Vision0 Long0 | Auto 7
Caps: company dossier, risk screening

### 145 — Отзывы о товаре
«Джарвис, собери отзывы о товаре [X] с разных сайтов, отфильтруй накрученные и сделай честное резюме.»
Cat: SHOPPING RESEARCH | Reviews
Diff: L2 | Tools: web | Web1 Code0 Files1 Vision0 Long0 | Auto 6
Caps: review scraping, fake-review filtering

### 146 — Сравнение товаров
«Джарвис, сравни [товар A] и [товар B]: характеристики, цены, отзывы. Сделай таблицу и рекомендацию.»
Cat: COMPARISON | Products
Diff: L2 | Tools: web | Web1 Code0 Files1 Vision0 Long0 | Auto 6
Caps: product comparison matrix

### 147 — Лучший товар в категории
«Джарвис, найди лучший [ноутбук до 1000$ / смартфон / кофеварку] прямо сейчас: изучи обзоры, рейтинги и цены, дай топ-5 с объяснением.»
Cat: SHOPPING RESEARCH | Recommendations
Diff: L3 | Tools: web | Web1 Code0 Files1 Vision0 Long0 | Auto 6
Caps: best-in-class research, ranked shortlist

### 148 — Следить за ценой
«Джарвис, следи за ценой этого товара и сообщи, если она упадёт ниже [сумма].»
Cat: BACKGROUND MISSIONS | Price watch
Diff: L2 | Tools: web, scheduler | Web1 Code1 Files0 Vision0 Long1 | Auto 8
Caps: price monitoring, threshold alerting

### 149 — Найти дешевле
«Джарвис, найди, где этот товар продаётся дешевле всего, с учётом доставки.»
Cat: SHOPPING RESEARCH | Price
Diff: L2 | Tools: web | Web1 Code0 Files0 Vision0 Long0 | Auto 6
Caps: price comparison, total-cost analysis

### 150 — Купоны и скидки
«Джарвис, найди действующие промокоды и скидки для магазина [X].»
Cat: SHOPPING RESEARCH | Discounts
Diff: L1 | Tools: web | Web1 Code0 Files0 Vision0 Long0 | Auto 5
Caps: coupon discovery, promo validation

### 151 — Собрать корзину
«Джарвис, собери корзину продуктов в [магазине] по моему списку и проверь итоговую цену с доставкой.»
Cat: BROWSER AUTOMATION | Shopping
Diff: L3 | Tools: browser, web | Web1 Code1 Files0 Vision1 Long0 | Auto 6
Caps: cart assembly, checkout prep

### 152 — Расписание поездов/самолётов
«Джарвис, найди рейсы [город А → город Б] на [дату], сравни цены и предложи лучший вариант.»
Cat: TRAVEL RESEARCH | Flights
Diff: L2 | Tools: web | Web1 Code0 Files0 Vision0 Long0 | Auto 6
Caps: flight search, fare comparison

### 153 — Маршрут поездки
«Джарвис, спланируй поездку в [город] на [N] дней: транспорт, жильё, что посмотреть, бюджет.»
Cat: TRAVEL RESEARCH | Planning
Diff: L4 | Tools: web, карты | Web1 Code0 Files1 Vision0 Long0 | Auto 7
Caps: itinerary generation, budget planning

### 154 — Погода
«Джарвис, какая погода будет в [город] на этой неделе? Сообщи, когда лучше выйти на пробежку.»
Cat: WEB | Weather
Diff: L0 | Tools: api погоды | Web1 Code0 Files0 Vision0 Long0 | Auto 3
Caps: weather lookup, activity planning

### 155 — Курс валют
«Джарвис, покажи текущие курсы валют и динамику за месяц.»
Cat: WEB | Finance data
Diff: L0 | Tools: api | Web1 Code0 Files0 Vision0 Long0 | Auto 3
Caps: exchange rate monitoring

### 156 — Курсы акций
«Джарвис, проверь, как сегодня движутся мои акции, и собери новости, которые могут на них повлиять.»
Cat: FINANCE ANALYSIS | Portfolio
Diff: L2 | Tools: web, api | Web1 Code0 Files0 Vision0 Long0 | Auto 5
Caps: portfolio tracking, news correlation

### 157 — Криптовалюты
«Джарвис, собери актуальную информацию по [криптовалюте]: цена, капитализация, новости, настроение рынка.»
Cat: FINANCE ANALYSIS | Crypto
Diff: L1 | Tools: web | Web1 Code0 Files0 Vision0 Long0 | Auto 4
Caps: crypto market digest

### 158 — Следить за рынком
«Джарвис, следи за [индекс/акцией] и предупреди, если произойдёт движение больше чем на [N]% за день.»
Cat: MONITORING | Markets
Diff: L2 | Tools: api, scheduler | Web1 Code1 Files0 Vision0 Long1 | Auto 8
Caps: market alerting, threshold triggers

### 159 — Перевод текста
«Джарвис, переведи этот текст на [язык] и сохрани рядом с оригиналом.»
Cat: TRANSLATION | General
Diff: L0 | Tools: mt | Web1 Code1 Files1 Vision0 Long0 | Auto 4
Caps: text translation

### 160 — Перевод документа целиком
«Джарвис, переведи весь этот документ на [язык], сохранив форматирование, и сделай обе версии.»
Cat: TRANSLATION | Documents
Diff: L2 | Tools: mt, документы | Web1 Code1 Files1 Vision0 Long0 | Auto 6
Caps: document translation with layout preservation

### 161 — Перевод с сохранением стиля
«Джарвис, переведи эту статью, но сохрани стиль автора: иронию, разговорные обороты, термины.»
Cat: TRANSLATION | Literary
Diff: L2 | Tools: llm, mt | Web1 Code0 Files0 Vision0 Long0 | Auto 5
Caps: style-aware translation

### 162 — Перевести и объяснить
«Джарвис, переведи этот документ и рядом объясни, что в нём написано простым языком.»
Cat: TRANSLATION | Explain
Diff: L1 | Tools: llm | Web0 Code0 Files1 Vision0 Long0 | Auto 5
Caps: translate-and-explain

### 163 — Субтитры
«Джарвис, сделай субтитры для этого видео на русском и английском.»
Cat: VIDEO | Subtitles
Diff: L3 | Tools: stt, mt, srt | Web1 Code1 Files1 Voice1 Long0 | Auto 7
Caps: subtitle generation, timing sync

### 164 — Создать документ Word
«Джарвис, создай документ Word по этой структуре с заголовками и оформлением.»
Cat: WORD PROCESSING | Creation
Diff: L1 | Tools: docx | Web0 Code1 Files1 Vision0 Long0 | Auto 5
Caps: document generation, styling

### 165 — Написать письмо
«Джарвис, напиши официальное письмо на английском по этому черновику и сохрани в Word.»
Cat: WRITING | Correspondence
Diff: L1 | Tools: llm, docx | Web0 Code1 Files1 Vision0 Long0 | Auto 4
Caps: letter drafting, formal tone

### 166 — Отформатировать документ
«Джарвис, приведи этот документ к единому стилю: шрифты, заголовки, отступы, нумерация.»
Cat: WORD PROCESSING | Formatting
Diff: L2 | Tools: docx | Web0 Code1 Files1 Vision0 Long0 | Auto 6
Caps: document normalization

### 167 — Проверить правописание и стиль
«Джарвис, проверь мой текст на ошибки, стиль и читаемость и предложи исправления.»
Cat: WRITING | Editing
Diff: L1 | Tools: llm | Web0 Code1 Files1 Vision0 Long0 | Auto 5
Caps: proofreading, style grading

### 168 — Переписать текст лучше
«Джарвис, перепиши этот абзац, чтобы он звучал убедительнее и профессиональнее.»
Cat: WRITING | Rewriting
Diff: L0 | Tools: llm | Web0 Code0 Files0 Vision0 Long0 | Auto 3
Caps: copy polishing

### 169 — Сократить текст
«Джарвис, сократи этот текст вдвое, сохранив все важные мысли.»
Cat: WRITING | Editing
Diff: L0 | Tools: llm | Web0 Code0 Files0 Vision0 Long0 | Auto 3
Caps: text compression

### 170 — Расширить текст
«Джарвис, расширь этот набросок в полноценную статью на [N] слов, сохранив мои идеи.»
Cat: WRITING | Expansion
Diff: L2 | Tools: llm | Web0 Code0 Files1 Vision0 Long0 | Auto 5
Caps: long-form expansion

### 171 — Реферат по теме
«Джарвис, напиши реферат на тему [X] объёмом 10 страниц с введением, главами и выводами.»
Cat: WRITING | Academic
Diff: L2 | Tools: llm, docx | Web0 Code1 Files1 Vision0 Long0 | Auto 6
Caps: academic writing, structure generation

### 172 — План книги
«Джарвис, придумай структуру книги на тему [X]: главы, разделы, примерное содержание каждой главы.»
Cat: WRITING | Books
Diff: L2 | Tools: llm | Web0 Code0 Files1 Vision0 Long0 | Auto 5
Caps: book outlining

### 173 — Написать главу книги
«Джарвис, напиши первую главу моей книги по этому плану в моём стиле.»
Cat: WRITING | Books
Diff: L2 | Tools: llm, docx | Web0 Code0 Files1 Vision0 Long0 | Auto 5
Caps: fiction/non-fiction writing

### 174 — Пост для соцсетей
«Джарвис, напиши пост для [LinkedIn/Telegram/Instagram] на тему [X]: заголовок, текст, хэштеги.»
Cat: CONTENT CREATION | Social
Diff: L1 | Tools: llm | Web0 Code0 Files0 Vision0 Long0 | Auto 4
Caps: social copy generation

### 175 — Серия постов на месяц
«Джарвис, придумай контент-план на месяц для моего канала: 20 тем, заголовки и форматы.»
Cat: CONTENT CREATION | Planning
Diff: L2 | Tools: llm, таблицы | Web0 Code1 Files1 Vision0 Long0 | Auto 6
Caps: content calendar generation

### 176 — Сценарий видео
«Джарвис, напиши сценарий для YouTube-видео на тему [X]: зацепка, структура, таймкоды, CTA.»
Cat: CONTENT CREATION | Video
Diff: L2 | Tools: llm | Web0 Code0 Files1 Vision0 Long0 | Auto 5
Caps: video scripting, hook crafting

### 177 — Тизер и описание
«Джарвис, придумай название, обложку-концепцию и описание для моего видео на тему [X].»
Cat: CONTENT CREATION | Video
Diff: L1 | Tools: llm, image gen | Web0 Code0 Files0 Vision0 Long0 | Auto 4
Caps: video metadata generation

### 178 — Скрипт подкаста
«Джарвис, напиши сценарий выпуска подкаста на [N] минут: интро, вопросы гостю, аутро.»
Cat: CONTENT CREATION | Podcast
Diff: L2 | Tools: llm | Web0 Code0 Files1 Vision0 Long0 | Auto 5
Caps: podcast script generation

### 179 — Сценарий выступления
«Джарвис, подготовь речь на [N] минут для выступления перед [аудиторией] на тему [X].»
Cat: CONTENT CREATION | Speech
Diff: L2 | Tools: llm | Web0 Code0 Files0 Vision0 Long0 | Auto 4
Caps: speech writing, audience adaptation

### 180 — Резюме
«Джарвис, составь моё резюме по информации из моих проектов, адаптированное под вакансию [X].»
Cat: WRITING | CV
Diff: L2 | Tools: llm, документы | Web0 Code1 Files1 Vision0 Long0 | Auto 5
Caps: resume tailoring, achievement extraction

### 181 — Мониторинг цены товара
«Джарвис, следи за ценой [товар] на [сайтах] и сообщи, если она упадёт ниже [N].»
Cat: SHOPPING | Price watch
Diff: L3 | Tools: browser, scheduler, notifier | Web1 Code1 Files1 Vision0 Long1 | Auto 8
Caps: price tracking, change detection, alerting

### 182 — Сравнение товаров с рекомендацией
«Джарвис, найди лучший [товар] до [бюджет]: собери характеристики, отзывы и цены из 3+ магазинов, сведи в таблицу и дай итоговую рекомендацию.»
Cat: SHOPPING | Comparison
Diff: L2 | Tools: browser, spreadsheets | Web1 Code1 Files1 Vision0 Long0 | Auto 7
Caps: multi-source comparison, score-based ranking

### 183 — Проверка фактов
«Джарвис, проверь утверждения: [список]. Найди первоисточники, оцени достоверность и пометь, что подтверждено, а что нет.»
Cat: WEB | Fact checking
Diff: L2 | Tools: browser, search | Web1 Code0 Files1 Vision0 Long0 | Auto 6
Caps: source verification, claim scoring

### 184 — Глубокое исследование темы
«Джарвис, изучи тему [X] за последние 2 года: свежие статьи, исследования, мнения экспертов. Составь структурированный отчёт с источниками.»
Cat: DEEP RESEARCH | Topic deep-dive
Diff: L4 | Tools: search, browser, notes, llm | Web1 Code0 Files1 Vision0 Long0 | Auto 8
Caps: multi-source synthesis, structured reporting

### 185 — Обзор научных статей
«Джарвис, найди свежие статьи по [теме] на arXiv/PubMed/Scholar, вытащи ключевые результаты каждой и сделай обзор.»
Cat: RESEARCH | Academic
Diff: L3 | Tools: browser, llm, citations | Web1 Code1 Files1 Vision0 Long0 | Auto 7
Caps: academic search, paper summarization

### 186 — Мониторинг новостей по теме
«Джарвис, каждые [N] часов проверяй новости по [теме] и присылай сводку, только если появилось что-то важное.»
Cat: MONITORING | News watch
Diff: L3 | Tools: scheduler, rss, notifier | Web1 Code1 Files0 Vision0 Long1 | Auto 8
Caps: keyword monitoring, dedup, importance filtering

### 187 — Анализ конкурентов
«Джарвис, изучи конкурентов для [продукт]: сайты, цены, отзывы, рекламу. Составь таблицу и найди их слабые места.»
Cat: BUSINESS | Competitive analysis
Diff: L3 | Tools: browser, spreadsheets, llm | Web1 Code1 Files1 Vision0 Long0 | Auto 7
Caps: competitor profiling, gap analysis

### 188 — Анализ YouTube-канала
«Джарвис, проанализируй канал [X]: темы, частота публикаций, средние просмотры, что заходит лучше. Составь отчёт.»
Cat: DATA ANALYSIS | Content metrics
Diff: L3 | Tools: browser, yt-dlp, spreadsheets | Web1 Code1 Files1 Vision0 Long0 | Auto 7
Caps: channel analytics, trend extraction

### 189 — Проверка надёжности сайта
«Джарвис, проверь сайт [URL]: кто владелец, когда создан, признаки мошенничества, отзывы. Дай вердикт о надёжности.»
Cat: SECURITY | Reputation check
Diff: L2 | Tools: whois, browser, search | Web1 Code0 Files0 Vision0 Long0 | Auto 6
Caps: domain intelligence, scam detection

### 190 — Поиск вакансий
«Джарвис, найди вакансии по [запрос] на [сайтах], отфильтруй подходящие, составь список со ссылками и ключевыми требованиями.»
Cat: CAREER | Job search
Diff: L2 | Tools: browser, spreadsheets | Web1 Code1 Files1 Vision0 Long0 | Auto 6
Caps: vacancy aggregation, fit scoring

### 191 — Сравнение авиабилетов
«Джарвис, сравни цены на авиабилеты [маршрут] на ближайшие [N] дней, покажи дешёвые варианты и лучшее окно покупки.»
Cat: TRAVEL | Flights
Diff: L3 | Tools: browser, price apis | Web1 Code1 Files1 Vision0 Long0 | Auto 7
Caps: flight price aggregation, timing advice

### 192 — Подбор отеля
«Джарвис, найди отель в [город] на [даты] для [N] человек: сравни цену, рейтинг, расположение, предложи топ-3.»
Cat: TRAVEL | Hotels
Diff: L2 | Tools: browser | Web1 Code0 Files1 Vision0 Long0 | Auto 6
Caps: hotel shortlisting, value scoring

### 193 — Лучшие рестораны рядом
«Джарвис, найди лучшие рестораны [кухня] рядом с [адрес]: сравни отзывы и цены, покажи топ и средний чек.»
Cat: TRAVEL | Local search
Diff: L1 | Tools: browser, maps | Web1 Code0 Files0 Vision0 Long0 | Auto 5
Caps: local discovery, review mining

### 194 — Слежка за курсом валют
«Джарвис, следи за курсом [валюта] и предупреди, когда он станет выгоднее текущего на [N]%.»
Cat: FINANCE | Currency watch
Diff: L3 | Tools: scheduler, api, notifier | Web1 Code1 Files0 Vision0 Long1 | Auto 8
Caps: rate tracking, threshold alerting

### 195 — Актуальность информации
«Джарвис, проверь актуальность [статья/данные]: найди более свежие источники и покажи, что изменилось.»
Cat: RESEARCH | Recency check
Diff: L2 | Tools: search | Web1 Code0 Files0 Vision0 Long0 | Auto 6
Caps: staleness detection, delta reporting

### 196 — Утренняя сводка
«Джарвис, каждое утро собирай сводку главных новостей по моим темам: [темы].»
Cat: ALERTING | Daily briefing
Diff: L2 | Tools: scheduler, rss, tts | Web1 Code1 Files0 Vision0 Long1 | Auto 8
Caps: news digest, personalization, voice briefing

### 197 — Стоит ли обновляться
«Джарвис, сравни [софт] версии [X] и [Y]: список изменений, известные баги, отзывы. Стоит ли обновляться?»
Cat: RESEARCH | Version compare
Diff: L2 | Tools: search, browser | Web1 Code0 Files0 Vision0 Long0 | Auto 6
Caps: changelog analysis, regression risk

### 198 — Вердикт по отзывам на товар
«Джарвис, собери отзывы на [товар], проанализируй частые жалобы и похвалы, выведи вердикт «покупать или нет».»
Cat: SHOPPING | Review analysis
Diff: L2 | Tools: browser, llm | Web1 Code1 Files1 Vision0 Long0 | Auto 7
Caps: sentiment extraction, issue clustering

### 199 — Рецепты из имеющихся продуктов
«Джарвис, найди рецепты из: [список продуктов]. Покажи топ-5 по простоте и времени.»
Cat: FOOD | Recipe search
Diff: L1 | Tools: browser | Web1 Code0 Files0 Vision0 Long0 | Auto 5
Caps: ingredient matching, recipe ranking

### 200 — Дайджест подписок
«Джарвис, собери недельный дайджест из моих источников: [список]. Сгруппируй по темам и выдели важное.»
Cat: SUMMARIZATION | Digest
Diff: L2 | Tools: rss, llm, notes | Web1 Code1 Files1 Vision0 Long0 | Auto 7
Caps: feed aggregation, topical clustering

### 201 — Офлайн-копия документации
«Джарвис, скачай документацию по [технология] в офлайн-копию, сделай оглавление с аннотациями к разделам.»
Cat: WEB | Offline docs
Diff: L3 | Tools: wget/httrack, llm | Web1 Code1 Files1 Vision0 Long0 | Auto 7
Caps: site mirroring, annotated index

### 202 — План обучения по курсам
«Джарвис, найди лучшие бесплатные курсы по [теме], сравни программы и отзывы, составь план обучения на [N] недель.»
Cat: LEARNING | Course planning
Diff: L2 | Tools: browser, notes | Web1 Code0 Files1 Vision0 Long0 | Auto 6
Caps: curriculum research, study scheduling

### 203 — Анализ трендов
«Джарвис, проанализируй тренды по [запрос] за год: Google Trends, соцсети, новости. Построй график и объясни всплески.»
Cat: DATA VISUALIZATION | Trends
Diff: L3 | Tools: trends api, charts, llm | Web1 Code1 Files1 Vision0 Long0 | Auto 7
Caps: trend mining, causal explanation

### 204 — Поиск мероприятий
«Джарвис, найди ближайшие конференции/митапы по [теме] в [город]: даты, стоимость, дедлайны регистрации.»
Cat: PLANNING | Events
Diff: L2 | Tools: browser | Web1 Code0 Files1 Vision0 Long0 | Auto 6
Caps: event aggregation, deadline tracking

### 205 — Мониторинг доступности сайтов
«Джарвис, проверяй доступность [сайты] каждые [N] минут; при сбое сразу сообщи и сделай скриншот ошибки.»
Cat: MONITORING | Uptime
Diff: L3 | Tools: http probes, scheduler, notifier | Web1 Code1 Files1 Vision1 Long1 | Auto 9
Caps: uptime probing, outage alerting, screenshot evidence

### 206 — Патентный обзор
«Джарвис, найди патенты по [технология], вытащи ключевые идеи и даты, сделай обзорную справку.»
Cat: RESEARCH | Patents
Diff: L3 | Tools: browser, llm | Web1 Code0 Files1 Vision0 Long0 | Auto 7
Caps: patent mining, claim abstraction

### 207 — Аналитика рынка труда
«Джарвис, собери данные о зарплатах и требованиях для [профессия] в [страна]: вакансии, статистика, прогнозы.»
Cat: CAREER | Market analytics
Diff: L3 | Tools: browser, spreadsheets, llm | Web1 Code1 Files1 Vision0 Long0 | Auto 7
Caps: salary benchmarking, skills demand

### 208 — Разбор open-source проекта
«Джарвис, найди open-source проект с реализацией [X], скачай, изучи архитектуру и объясни, как он работает, с примерами кода.»
Cat: CODING | Code study
Diff: L3 | Tools: git, llm, ide | Web1 Code1 Files1 Vision0 Long0 | Auto 7
Caps: codebase exploration, architecture explanation

### 209 — Шпаргалка по API
«Джарвис, изучи API [сервис]: методы, лимиты, цены. Напиши примеры вызовов и сделай шпаргалку.»
Cat: APIs | API research
Diff: L2 | Tools: browser, llm | Web1 Code1 Files1 Vision0 Long0 | Auto 6
Caps: API documentation digestion, cheat sheet

### 210 — Мониторинг конкурента в соцсетях
«Джарвис, следи за публикациями [конкурент] в соцсетях и сообщай о значимых анонсах в течение [N] минут.»
Cat: MONITORING | Social watch
Diff: L3 | Tools: rss/social api, notifier | Web1 Code1 Files0 Vision0 Long1 | Auto 8
Caps: social feed monitoring, significance filter

### 211 — Чек-лист лучших практик
«Джарвис, собери лучшие практики по [область] из авторитетных источников и оформи в чек-лист для внедрения.»
Cat: RESEARCH | Best practices
Diff: L2 | Tools: search, llm | Web1 Code0 Files1 Vision0 Long0 | Auto 6
Caps: practice harvesting, actionable checklist

### 212 — Сравнение подписок
«Джарвис, сравни [сервис] и аналоги: функции, цены, лимиты, отзывы. Посчитай, какой выгоднее для моего сценария.»
Cat: SHOPPING | Subscriptions
Diff: L2 | Tools: browser, spreadsheets | Web1 Code1 Files1 Vision0 Long0 | Auto 6
Caps: subscription comparison, ROI modeling

### 213 — Памятка по условиям сервиса
«Джарвис, изучи условия [банк/платформа]: комиссии, лимиты, подводные камни. Составь памятку с предупреждениями.»
Cat: FINANCE | Terms analysis
Diff: L2 | Tools: browser, llm | Web1 Code0 Files1 Vision0 Long0 | Auto 6
Caps: terms mining, risk flagging

### 214 — Волонтёрские возможности
«Джарвис, найди волонтёрские возможности по [тема] в [город], сравни организации по прозрачности.»
Cat: RESEARCH | Volunteering
Diff: L2 | Tools: browser | Web1 Code0 Files1 Vision0 Long0 | Auto 5
Caps: opportunity search, org vetting

### 215 — Проверка ссылок в документе
«Джарвис, проверь все ссылки в [файл]: какие ведут на 404 или подозрительные сайты. Составь отчёт.»
Cat: WEB | Link audit
Diff: L2 | Tools: http probes, llm | Web1 Code1 Files1 Vision0 Long0 | Auto 7
Caps: link validation, dead link report

### 216 — Закон простыми словами
«Джарвис, найди актуальную редакцию [закон/норматив], выдели ключевые положения по [теме] и объясни простыми словами.»
Cat: RESEARCH | Legal
Diff: L2 | Tools: browser, llm | Web1 Code0 Files1 Vision0 Long0 | Auto 6
Caps: regulatory lookup, plain-language summary

### 217 — Поиск грантов
«Джарвис, найди открытые гранты для [категория], собери дедлайны и требования, оцени мои шансы.»
Cat: CAREER | Grants
Diff: L2 | Tools: browser | Web1 Code0 Files1 Vision0 Long0 | Auto 6
Caps: grant discovery, eligibility check

### 218 — План путешествия
«Джарвис, спланируй маршрут [А → Б] на [N] дней: достопримечательности, транспорт, бюджет, погода.»
Cat: TRAVEL | Itinerary
Diff: L3 | Tools: browser, maps, spreadsheets | Web1 Code1 Files1 Vision0 Long0 | Auto 7
Caps: itinerary generation, budget planning

### 219 — Сравнение страховок
«Джарвис, сравни [тип] страховки для [профиль]: покрытие, стоимость, исключения. Дай рекомендацию.»
Cat: FINANCE | Insurance
Diff: L2 | Tools: browser, llm | Web1 Code0 Files1 Vision0 Long0 | Auto 6
Caps: insurance comparison, coverage gap analysis

### 220 — Шорт-лист инфлюенсеров
«Джарвис, найди инфлюенсеров в нише [X] с аудиторией [N-M], собери охваты и стоимость размещения.»
Cat: MARKETING | Influencers
Diff: L3 | Tools: browser, spreadsheets | Web1 Code1 Files1 Vision0 Long0 | Auto 7
Caps: influencer discovery, reach estimation

### 221 — Мониторинг тендеров
«Джарвис, мониторь площадку [X] по ключевым словам [Y], сообщай о новых тендерах с деталями.»
Cat: BUSINESS | Tenders
Diff: L3 | Tools: scheduler, parser, notifier | Web1 Code1 Files0 Vision0 Long1 | Auto 8
Caps: tender scraping, keyword matching, alerting

### 222 — Оценка посещаемости сайта
«Джарвис, оцени посещаемость сайта [X] по открытым данным: объём, источники трафика, аудитория.»
Cat: DATA ANALYSIS | Web analytics
Diff: L3 | Tools: similarweb/apis, llm | Web1 Code1 Files1 Vision0 Long0 | Auto 7
Caps: traffic estimation, audience profiling

### 223 — Статистика для презентации
«Джарвис, собери свежие статистические данные по [тема] с источниками для презентации.»
Cat: RESEARCH | Data for talks
Diff: L2 | Tools: search, notes | Web1 Code0 Files1 Vision0 Long0 | Auto 6
Caps: stat harvesting, source citation

### 224 — Проверка уникальности текста
«Джарвис, проверь [текст/файл] на уникальность: найди пересечения в интернете и отметь подозрительные абзацы.»
Cat: WRITING | Plagiarism
Diff: L2 | Tools: search, llm | Web1 Code1 Files1 Vision0 Long0 | Auto 6
Caps: similarity detection, snippet attribution

### 225 — Происхождение цитат
«Джарвис, проверь цитаты [список]: кто автор, где впервые опубликовано, точная формулировка.»
Cat: RESEARCH | Quotes
Diff: L2 | Tools: search | Web1 Code0 Files1 Vision0 Long0 | Auto 6
Caps: quote provenance, misattribution detection

### 226 — История страницы через архив
«Джарвис, посмотри через веб-архив, как менялась [URL] за годы, и опиши значимые изменения.»
Cat: RESEARCH | Web archive
Diff: L2 | Tools: archive api, browser | Web1 Code1 Files0 Vision0 Long0 | Auto 6
Caps: page history reconstruction, diff summarization

### 227 — Поиск старой версии софта
«Джарвис, найди старую версию [программа] [версия], проверь безопасность и скачай в архив.»
Cat: APPLICATIONS | Legacy software
Diff: L2 | Tools: browser, hash check | Web1 Code1 Files1 Vision0 Long0 | Auto 6
Caps: legacy binary search, hash verification

### 228 — Инструкция к устройству
«Джарвис, найди инструкцию к [устройство], извлеки ключевые разделы и сохрани в PDF.»
Cat: DOCUMENTS | Manuals
Diff: L1 | Tools: browser, pdf tools | Web1 Code0 Files1 Vision0 Long0 | Auto 5
Caps: manual retrieval, PDF assembly

### 229 — Какой курс лучше
«Джарвис, сравни курсы [X] и [Y] по программе, преподавателям, отзывам выпускников и цене.»
Cat: LEARNING | Course compare
Diff: L2 | Tools: browser, llm | Web1 Code0 Files1 Vision0 Long0 | Auto 6
Caps: course comparison, alumni review mining

### 230 — История цен на товар
«Джарвис, построй историю цены на [товар] за [период] по архивам и скажи, сейчас дорого или дёшево.»
Cat: SHOPPING | Price history
Diff: L3 | Tools: archive, charts | Web1 Code1 Files1 Vision0 Long0 | Auto 7
Caps: price timeline, buying timing

### 231 — Поиск «работы мечты»
«Джарвис, я хочу работу, где [описание]. Найди подходящие вакансии и скажи, какие навыки подтянуть.»
Cat: CAREER | Career fit
Diff: L3 | Tools: browser, llm, skills db | Web1 Code1 Files1 Vision0 Long0 | Auto 7
Caps: job matching, skills gap analysis

### 232 — Досье на компанию
«Джарвис, собери досье на [компания]: владельцы, финансы, суды, новости, отзывы сотрудников.»
Cat: BUSINESS | Due diligence
Diff: L3 | Tools: browser, registries, llm | Web1 Code0 Files1 Vision0 Long0 | Auto 7
Caps: company profiling, reputation scoring

### 233 — Обзор инвестиций в сектор
«Джарвис, изучи инвестиционные возможности в [сектор]: новости, аналитика, риски. Составь осторожный обзор.»
Cat: FINANCE | Sector research
Diff: L3 | Tools: browser, llm, data apis | Web1 Code1 Files1 Vision0 Long0 | Auto 7
Caps: sector intelligence, risk framing

### 234 — Мониторинг упоминаний бренда
«Джарвис, следи за упоминаниями [бренд] в интернете и соцсетях, раз в день присылай сводку с тональностью.»
Cat: MARKETING | Brand monitoring
Diff: L3 | Tools: social api, sentiment, scheduler | Web1 Code1 Files0 Vision0 Long1 | Auto 8
Caps: mention tracking, sentiment trend

### 235 — Площадки для публикации
«Джарвис, найди площадки для публикации [материал по теме] с требованиями к формату и описанием аудитории.»
Cat: MARKETING | Publishing
Diff: L2 | Tools: browser | Web1 Code0 Files1 Vision0 Long0 | Auto 6
Caps: channel discovery, submission criteria

### 236 — SEO-анализ конкурента
«Джарвис, проанализируй SEO сайта [X]: запросы, ссылки, структуру. Что можно позаимствовать?»
Cat: MARKETING | SEO
Diff: L3 | Tools: seo tools, browser | Web1 Code1 Files1 Vision0 Long0 | Auto 7
Caps: keyword extraction, backlink profiling

### 237 — Фриланс-заказы
«Джарвис, найди свежие заказы по [навык] на [биржах], оцени бюджет и выбери топ-5 для отклика.»
Cat: CAREER | Freelance
Diff: L2 | Tools: browser | Web1 Code0 Files1 Vision0 Long0 | Auto 6
Caps: job scraping, budget sanity check

### 238 — Проверка расширений браузера
«Джарвис, проверь расширения [список]: автор, права, жалобы. Пометь подозрительные.»
Cat: SECURITY | Extension audit
Diff: L2 | Tools: browser, search | Web1 Code0 Files0 Vision0 Long0 | Auto 6
Caps: extension vetting, permission risk

### 239 — Анализ рациона
«Джарвис, проанализируй мой [рацион/список покупок]: питательность и бюджет. Предложи более здоровые и дешёвые альтернативы.»
Cat: HEALTH | Nutrition
Diff: L2 | Tools: llm, spreadsheets | Web1 Code1 Files1 Vision0 Long0 | Auto 6
Caps: nutrition modeling, cost optimization

### 240 — Поиск репетитора
«Джарвис, найди онлайн-репетитора по [предмет]: сравни ставки, отзывы, расписание. Составь шорт-лист.»
Cat: LEARNING | Tutoring
Diff: L2 | Tools: browser | Web1 Code0 Files1 Vision0 Long0 | Auto 6
Caps: tutor comparison, availability check

### 241 — Ожидание появления товара
«Джарвис, следи за появлением [товар] в наличии и сообщи первым, как только появится.»
Cat: SHOPPING | Stock watch
Diff: L3 | Tools: scheduler, parser, notifier | Web1 Code1 Files0 Vision0 Long1 | Auto 8
Caps: stock detection, instant alert

### 242 — Обобщённое ТЗ на ПО
«Джарвис, собери типовые требования к [тип ПО] из источников и составь обобщённый чек-лист для тендера.»
Cat: ENGINEERING | Requirements
Diff: L2 | Tools: search, llm | Web1 Code0 Files1 Vision0 Long0 | Auto 6
Caps: requirement synthesis, checklist building

### 243 — Примеры договоров
«Джарвис, найди типовые договоры [тип] с комментариями юристов, выдели ключевые пункты и риски.»
Cat: BUSINESS | Contracts
Diff: L2 | Tools: browser, llm | Web1 Code0 Files1 Vision0 Long0 | Auto 6
Caps: contract templates, risk highlighting

### 244 — Разбор состава продукта
«Джарвис, разбери состав [продукт]: что внутри, какие заявления правда, а какие маркетинг.»
Cat: HEALTH | Product scrutiny
Diff: L2 | Tools: search, llm | Web1 Code0 Files0 Vision0 Long0 | Auto 6
Caps: ingredient research, claim validation

### 245 — Executive summary рынка
«Джарвис, изучи рынок [X] для входа: объём, игроки, барьеры, регулирование, прогнозы. Подготовь executive summary.»
Cat: BUSINESS | Market entry
Diff: L4 | Tools: browser, llm, spreadsheets | Web1 Code1 Files1 Vision0 Long0 | Auto 8
Caps: market sizing, entry strategy brief

### 246 — Хронология события
«Джарвис, собери исторические данные по [событие] из надёжных источников в хронологию с указанием источников.»
Cat: RESEARCH | Timeline
Diff: L3 | Tools: search, notes | Web1 Code0 Files1 Vision0 Long0 | Auto 7
Caps: chronology building, source cross-check

### 247 — Сверка источников
«Джарвис, найди минимум 5 независимых источников по [тема], сравни версии и отметь противоречия.»
Cat: RESEARCH | Cross-verification
Diff: L2 | Tools: search | Web1 Code0 Files1 Vision0 Long0 | Auto 7
Caps: multi-source triangulation, contradiction flag

### 248 — Локации для съёмок
«Джарвис, найди локации для съёмок [тип видео] в [город]: места, разрешения, свет, логистика.»
Cat: CONTENT CREATION | Locations
Diff: L2 | Tools: browser, maps | Web1 Code0 Files1 Vision0 Long0 | Auto 6
Caps: location scouting, permit research

### 249 — Погода для планов
«Джарвис, спрогнозируй погоду на [даты] в [место] и подскажи, какие планы на улице лучше перенести.»
Cat: PLANNING | Weather
Diff: L1 | Tools: weather api | Web1 Code0 Files0 Vision0 Long0 | Auto 5
Caps: forecast retrieval, plan risk advice

### 250 — Сводка спортивных результатов
«Джарвис, собирай результаты моих команд [список] после матчей и присылай сводку с ключевыми моментами.»
Cat: ENTERTAINMENT | Sports
Diff: L2 | Tools: scheduler, sports api | Web1 Code1 Files0 Vision0 Long1 | Auto 7
Caps: score tracking, match summary

### 251 — Анонсы релизов
«Джарвис, найди анонсы и даты выхода [продукт], следи и напомни за [N] дней до релиза.»
Cat: MONITORING | Releases
Diff: L2 | Tools: scheduler, rss, notifier | Web1 Code1 Files0 Vision0 Long1 | Auto 7
Caps: release tracking, countdown reminder

### 252 — Данные об игре
«Джарвис, собери данные об игре [X]: системные требования, оценки, размер, цена в разных магазинах.»
Cat: ENTERTAINMENT | Games info
Diff: L1 | Tools: browser | Web1 Code0 Files0 Vision0 Long0 | Auto 5
Caps: game metadata aggregation

### 253 — Решения с форумов
«Джарвис, найди обсуждения проблемы [ошибка] на форумах и Stack Overflow, собери лучшие решения с голосами.»
Cat: DEBUGGING | Community solutions
Diff: L2 | Tools: search, browser | Web1 Code0 Files1 Vision0 Long0 | Auto 6
Caps: solution harvesting, vote weighting

### 254 — Слежка за документацией проекта
«Джарвис, следи за документацией [проект] и сообщай о значимых изменениях API.»
Cat: MONITORING | Docs watch
Diff: L3 | Tools: scheduler, diff, notifier | Web1 Code1 Files0 Vision0 Long1 | Auto 8
Caps: doc diffing, breaking-change alert

### 255 — Статистика по странам
«Джарвис, собери статистику по [страны] для [цель]: население, ВВП, интернет-проникновение и др.»
Cat: RESEARCH | Country data
Diff: L2 | Tools: data apis, spreadsheets | Web1 Code1 Files1 Vision0 Long0 | Auto 6
Caps: indicator aggregation, table build

### 256 — Происхождение изображения
«Джарвис, найди происхождение [изображение] через обратный поиск: первая публикация, автор, лицензия.»
Cat: RESEARCH | Reverse image
Diff: L2 | Tools: reverse image search | Web1 Code1 Files1 Vision1 Long0 | Auto 6
Caps: image provenance, license lookup

### 257 — Шаблоны документов
«Джарвис, найди хорошие шаблоны [тип документа] с примерами заполнения и скачай подходящие.»
Cat: DOCUMENTS | Templates
Diff: L1 | Tools: browser | Web1 Code0 Files1 Vision0 Long0 | Auto 5
Caps: template search, format matching

### 258 — Подкасты по теме
«Джарвис, найди подкасты по [тема], сравни длительность и периодичность, предложи 5 для подписки.»
Cat: ENTERTAINMENT | Podcasts
Diff: L1 | Tools: browser | Web1 Code0 Files0 Vision0 Long0 | Auto 5
Caps: podcast discovery, quality ranking

### 259 — Бесплатные ресурсы для творчества
«Джарвис, найди бесплатные ресурсы для [творчество]: кисти, шрифты, сэмплы. Скачай и разложи по папкам.»
Cat: CREATIVE WORK | Assets
Diff: L2 | Tools: browser, filesystem | Web1 Code1 Files1 Vision0 Long0 | Auto 6
Caps: asset sourcing, auto-organization

### 260 — Сравнение работодателей
«Джарвис, сравни условия в [компания А] и [компания Б] по отзывам: зарплата, офис, культура, рост.»
Cat: CAREER | Employers
Diff: L2 | Tools: browser, llm | Web1 Code0 Files1 Vision0 Long0 | Auto 6
Caps: employer comparison, culture mining

### 261 — Поиск программ лояльности
«Джарвис, найди лучшие программы лояльности/кешбэка для моих обычных покупок: [категории].»
Cat: SHOPPING | Loyalty
Diff: L2 | Tools: browser | Web1 Code0 Files1 Vision0 Long0 | Auto 6
Caps: cashback comparison, spending fit

### 262 — Проверка сертификатов SSL
«Джарвис, проверь SSL-сертификаты моих доменов [список] и предупреди за [N] дней до истечения.»
Cat: SECURITY | Certificates
Diff: L2 | Tools: openssl, scheduler | Web1 Code1 Files0 Vision0 Long1 | Auto 7
Caps: cert expiry tracking, renewal alert

### 263 — Поиск объяснения термина
«Джарвис, объясни термин [X] простыми словами с примерами и аналогиями, добавь, где почитать подробнее.»
Cat: LEARNING | Explainer
Diff: L1 | Tools: llm | Web0 Code0 Files0 Vision0 Long0 | Auto 4
Caps: conceptual explanation, resource pointers

### 264 — Составление FAQ
«Джарвис, собери частые вопросы по [тема/продукт] с форумов и поддержки и составь готовый FAQ.»
Cat: CONTENT CREATION | FAQ
Diff: L2 | Tools: search, llm | Web1 Code0 Files1 Vision0 Long0 | Auto 6
Caps: question mining, answer drafting

### 265 — Мониторинг вакансий мечты
«Джарвис, следи за появлением вакансии [описание] на [сайтах] и сообщай мгновенно.»
Cat: CAREER | Job alert
Diff: L3 | Tools: scheduler, parser, notifier | Web1 Code1 Files0 Vision0 Long1 | Auto 8
Caps: vacancy watching, instant alert

### 266 — Изучение ниши для блога
«Джарвис, проанализируй нишу [X] для блога: конкуренция, спрос, монетизация. Стоит ли входить?»
Cat: BUSINESS | Niche analysis
Diff: L3 | Tools: browser, llm, trends | Web1 Code1 Files1 Vision0 Long0 | Auto 7
Caps: niche viability, monetization research

### 267 — Перевод сайта целиком
«Джарвис, скачай сайт [URL] и переведи ключевые страницы на [язык], сохрани в виде аккуратного документа.»
Cat: TRANSLATION | Site translate
Diff: L2 | Tools: wget, llm | Web1 Code1 Files1 Vision0 Long0 | Auto 6
Caps: site capture, document translation

### 268 — Словарь терминов по проекту
«Джарвис, собери термины из [проект/документы] и составь глоссарий с определениями.»
Cat: KNOWLEDGE MANAGEMENT | Glossary
Diff: L1 | Tools: llm, files | Web0 Code0 Files1 Vision0 Long0 | Auto 5
Caps: term extraction, glossary build

### 269 — Сравнение валютных счетов
«Джарвис, сравни условия мультивалютных счетов/карт для [сценарий]: комиссии, лимиты, курсы.»
Cat: FINANCE | Banking
Diff: L2 | Tools: browser, llm | Web1 Code0 Files1 Vision0 Long0 | Auto 6
Caps: banking comparison, fee modeling

### 270 — Поиск софта под задачу
«Джарвис, найди лучший софт для [задача] на [платформа]: сравни, предложи топ-3, укажи цену и альтернативы.»
Cat: APPLICATIONS | Software selection
Diff: L1 | Tools: search | Web1 Code0 Files0 Vision0 Long0 | Auto 5
Caps: software discovery, feature compare

### 271 — Составление маршрута доставки
«Джарвис, построй оптимальный маршрут для [N] точек доставки/визитов на сегодня с учётом пробок.»
Cat: PLANNING | Routing
Diff: L2 | Tools: maps api | Web1 Code1 Files0 Vision0 Long0 | Auto 6
Caps: route optimization, ETA calculation

### 272 — Проверка лицензий ПО
«Джарвис, проверь лицензии установленного ПО [список]: всё ли легально, какие лицензии требуют оплаты.»
Cat: SECURITY | Licensing
Diff: L2 | Tools: registry, browser | Web1 Code1 Files0 Vision0 Long0 | Auto 6
Caps: license audit, compliance report

### 273 — Сбор отзывов о компании
«Джарвис, собери отзывы о [компания] с Glassdoor/Отзовик/Хабр Карьера и сделай сводку плюсов и минусов.»
Cat: CAREER | Company reviews
Diff: L2 | Tools: browser, llm | Web1 Code0 Files1 Vision0 Long0 | Auto 6
Caps: review aggregation, pro/con summary

### 274 — Поиск партнёров/поставщиков
«Джарвис, найди надёжных поставщиков [товар/услуга] в [регион]: проверь репутацию и собери контакты.»
Cat: BUSINESS | Sourcing
Diff: L3 | Tools: browser, registries | Web1 Code0 Files1 Vision0 Long0 | Auto 7
Caps: supplier discovery, vetting

### 275 — Анализ оттока из подписок
«Джарвис, посмотри мои активные подписки, найди, какие я не использую, и посчитай, сколько я могу сэкономить.»
Cat: FINANCE | Subscription audit
Diff: L2 | Tools: browser, bank statements | Web1 Code1 Files1 Vision0 Long0 | Auto 6
Caps: subscription discovery, savings calc

### 276 — Прогноз погоды для фотосессии
«Джарвис, подбери ближайшие [N] дней с хорошим светом/погодой для фотосессии в [место].»
Cat: PLANNING | Photography
Diff: L1 | Tools: weather api | Web1 Code0 Files0 Vision0 Long0 | Auto 5
Caps: weather-based scheduling

### 277 — Изучение аудитории
«Джарвис, опиши целевую аудиторию для [продукт]: кто они, что читают, где сидят, что покупают.»
Cat: MARKETING | Audience
Diff: L3 | Tools: browser, llm | Web1 Code0 Files1 Vision0 Long0 | Auto 7
Caps: persona building, channel mapping

### 278 — Проверка требований ПК для игры
«Джарвис, проверь, потянет ли мой ПК игру [X]: сравни требования с моим железом.»
Cat: GAMES | Compatibility
Diff: L1 | Tools: sysinfo, browser | Web1 Code1 Files0 Vision0 Long0 | Auto 5
Caps: hardware vs requirements check

### 279 — Поиск замены сервиса
«Джарвис, [сервис] закрывается/дорожает. Найди лучшие альтернативы с миграцией данных.»
Cat: APPLICATIONS | Alternatives
Diff: L2 | Tools: search, llm | Web1 Code0 Files1 Vision0 Long0 | Auto 6
Caps: alternative discovery, migration guide

### 280 — Мониторинг выхода версий библиотек
«Джарвис, следи за выходом новых версий [библиотеки] и сообщай о мажорных обновлениях с краткими release notes.»
Cat: MONITORING | Libraries
Diff: L2 | Tools: scheduler, package apis | Web1 Code1 Files0 Vision0 Long1 | Auto 7
Caps: version tracking, release digest

### 281 — Написание письма
«Джарвис, напиши вежливое письмо [кому] о [тема], приложи [файл] и поставь в очередь на отправку.»
Cat: EMAIL | Drafting
Diff: L2 | Tools: mail client, llm | Web0 Code0 Files1 Vision0 Long0 | Auto 6
Caps: email drafting, attachment handling

### 282 — Разбор входящих
«Джарвис, разбери мою почту: важные отдельно, спам в архив, по остальным краткую сводку.»
Cat: EMAIL | Triage
Diff: L2 | Tools: mail api, llm | Web1 Code1 Files0 Vision0 Long0 | Auto 7
Caps: inbox triage, priority sorting

### 283 — Автоответ на отпуск
«Джарвис, настрой автоответ на [период]: что я в отпуске, срочные письма пересылай [кому].»
Cat: EMAIL | Autoreply
Diff: L1 | Tools: mail client | Web1 Code0 Files0 Vision0 Long0 | Auto 5
Caps: autoresponder setup, forwarding rule

### 284 — Подпись из профиля
«Джарвис, создай email-подпись из моих контактов и соцсетей, сделай несколько вариантов.»
Cat: EMAIL | Signature
Diff: L1 | Tools: llm, contacts | Web0 Code0 Files1 Vision0 Long0 | Auto 4
Caps: signature generation, variant design

### 285 — Вечерний дайджест почты
«Джарвис, каждый вечер присылай дайджест писем: кратко о важном, вложения на виду.»
Cat: EMAIL | Digest
Diff: L2 | Tools: mail api, scheduler, llm | Web1 Code1 Files0 Vision0 Long1 | Auto 8
Caps: daily mail digest, attachment index

### 286 — Поиск письма
«Джарвис, найди письмо от [отправитель] про [тема] за [период] и покажи вложение.»
Cat: EMAIL | Search
Diff: L1 | Tools: mail search | Web1 Code0 Files0 Vision0 Long0 | Auto 5
Caps: semantic mail search

### 287 — Отписка от ненужных рассылок
«Джарвис, найди рассылки, которые я не открывал [N] месяцев, и предложи отписаться.»
Cat: EMAIL | Unsubscribe
Diff: L2 | Tools: mail api, llm | Web1 Code1 Files0 Vision0 Long0 | Auto 6
Caps: engagement analysis, unsubscribe list

### 288 — Контроль ответов
«Джарвис, следи, кому я не ответил за [N] дней, и напомни о важных.»
Cat: EMAIL | Follow-up
Diff: L2 | Tools: mail api, scheduler | Web1 Code1 Files0 Vision0 Long1 | Auto 7
Caps: response tracking, follow-up reminders

### 289 — Чистка почты
«Джарвис, почисти ящик: удали дубли, заархивируй письма старше [N] лет, освободи место.»
Cat: EMAIL | Cleanup
Diff: L2 | Tools: mail api | Web1 Code1 Files0 Vision0 Long0 | Auto 6
Caps: dedup, archival, quota reclaim

### 290 — Задачи из писем
«Джарвис, пройдись по письмам и вытащи все задачи и обещания, добавь в список дел с дедлайнами.»
Cat: EMAIL | Task extraction
Diff: L2 | Tools: mail api, task app, llm | Web1 Code1 Files0 Vision0 Long0 | Auto 7
Caps: commitment mining, deadline extraction

### 291 — Сводка переписки
«Джарвис, сделай сводку переписки с [человек] за [период]: о чём договорились, что осталось.»
Cat: EMAIL | Thread summary
Diff: L1 | Tools: llm | Web1 Code0 Files0 Vision0 Long0 | Auto 5
Caps: thread summarization, action items

### 292 — Полировка письма
«Джарвис, проверь моё письмо на ошибки и стиль, предложи улучшенный вариант.»
Cat: EMAIL | Polish
Diff: L1 | Tools: llm | Web0 Code0 Files1 Vision0 Long0 | Auto 4
Caps: grammar check, tone adjustment

### 293 — Рассылка приглашений
«Джарвис, разошли приглашения на [событие] всем из списка, приложи ICS-файл.»
Cat: EMAIL | Invites
Diff: L1 | Tools: mail api, calendar | Web1 Code1 Files1 Vision0 Long0 | Auto 5
Caps: batch invites, calendar file generation

### 294 — Черновики-напоминания
«Джарвис, напомни, если есть черновики старше [N] дней, и предложи дописать.»
Cat: EMAIL | Drafts
Diff: L1 | Tools: mail api, scheduler | Web1 Code0 Files0 Vision0 Long1 | Auto 6
Caps: draft aging detection

### 295 — Оценка полезности рассылок
«Джарвис, проанализируй, на какие рассылки я трачу время, и составь рейтинг полезности.»
Cat: EMAIL | Value audit
Diff: L2 | Tools: mail api, llm | Web1 Code1 Files1 Vision0 Long0 | Auto 6
Caps: time-value analysis, unsubscribe advice

### 296 — Перевод писем
«Джарвис, переводи входящие на [язык], если они на другом языке, храни рядом с оригиналом.»
Cat: EMAIL | Translation
Diff: L2 | Tools: mail api, llm | Web1 Code1 Files0 Vision0 Long1 | Auto 7
Caps: inline translation, bilingual storage

### 297 — Сортировка вложений
«Джарвис, собери все вложения из почты за [период] и разложи по папкам по типам и проектам.»
Cat: EMAIL | Attachments
Diff: L2 | Tools: mail api, filesystem | Web1 Code1 Files1 Vision0 Long0 | Auto 6
Caps: attachment harvest, smart filing

### 298 — Еженедельный отчёт по почте
«Джарвис, каждую пятницу присылай отчёт: сколько писем, по темам, что осталось без ответа.»
Cat: EMAIL | Reports
Diff: L2 | Tools: mail api, scheduler, llm | Web1 Code1 Files1 Vision0 Long1 | Auto 7
Caps: mail analytics, weekly digest

### 299 — Помощь с трудным ответом
«Джарвис, помоги ответить на сложное письмо: собери аргументы, напиши черновик, посоветуй тон.»
Cat: EMAIL | Negotiation
Diff: L2 | Tools: llm, research | Web1 Code0 Files0 Vision0 Long0 | Auto 6
Caps: argument building, tone coaching

### 300 — Мгновенные уведомления о важных
«Джарвис, мгновенно сообщай о письмах от [список людей] даже если я не проверяю почту.»
Cat: EMAIL | Priority alerts
Diff: L2 | Tools: mail api, notifier | Web1 Code1 Files0 Vision0 Long1 | Auto 7
Caps: sender whitelist alerting

### 301 — Поиск окна для встречи
«Джарвис, найди общее свободное окно для встречи с [участники] на неделе и предложи варианты.»
Cat: CALENDAR | Scheduling
Diff: L2 | Tools: calendar api | Web1 Code1 Files0 Vision0 Long0 | Auto 6
Caps: availability merge, slot proposal

### 302 — Разбор недели
«Джарвис, разбери мой календарь на неделю: где перегруз, где можно выдохнуть, что перенести.»
Cat: CALENDAR | Week review
Diff: L2 | Tools: calendar api, llm | Web1 Code0 Files1 Vision0 Long0 | Auto 6
Caps: load analysis, reschedule advice

### 303 — Умное распределение задач
«Джарвис, распредели задачи [список] по календарю с учётом приоритетов и моей энергии.»
Cat: CALENDAR | Time blocking
Diff: L2 | Tools: calendar api, task app | Web1 Code1 Files0 Vision0 Long0 | Auto 6
Caps: task scheduling, energy-aware planning

### 304 — Напоминания с подготовкой
«Джарвис, напоминай за [N] минут до событий, для важных — с чек-листом подготовки.»
Cat: CALENDAR | Reminders
Diff: L1 | Tools: calendar api, notifier | Web1 Code0 Files0 Vision0 Long1 | Auto 6
Caps: smart reminders, prep checklists

### 305 — Поиск конфликтов
«Джарвис, найди пересечения встреч в календаре и предложи, как их развести.»
Cat: CALENDAR | Conflicts
Diff: L1 | Tools: calendar api | Web1 Code0 Files0 Vision0 Long0 | Auto 5
Caps: overlap detection, conflict resolution

### 306 — Итоги дня
«Джарвис, вечером подведи итоги дня из календаря и задач: сделано, переносится, что завтра.»
Cat: CALENDAR | Daily review
Diff: L2 | Tools: calendar, tasks, llm | Web0 Code0 Files1 Vision0 Long1 | Auto 7
Caps: daily retro, next-day prep

### 307 — Подготовка к встрече
«Джарвис, подготовь меня к встрече [X]: контекст, участники, договорённости, вопросы.»
Cat: CALENDAR | Prep
Diff: L2 | Tools: mail, notes, llm | Web1 Code0 Files1 Vision0 Long0 | Auto 6
Caps: meeting brief generation

### 308 — Перенос встреч
«Джарвис, перенеси встречи с [дата] на [дата] и разошли уведомления участникам.»
Cat: CALENDAR | Rescheduling
Diff: L2 | Tools: calendar api, mail | Web1 Code1 Files0 Vision0 Long0 | Auto 5
Caps: bulk reschedule, participant notify

### 309 — Аудит времени
«Джарвис, проанализируй, на что я трачу время по календарю за месяц.»
Cat: CALENDAR | Time audit
Diff: L2 | Tools: calendar api, charts | Web1 Code1 Files1 Vision0 Long0 | Auto 6
Caps: time distribution, focus ratio

### 310 — Общий календарь семьи
«Джарвис, сведи календари [участники] в один и покажи общие окна и конфликты.»
Cat: CALENDAR | Shared calendar
Diff: L2 | Tools: calendar api | Web1 Code1 Files0 Vision0 Long0 | Auto 6
Caps: multi-calendar merge, availability view

### 311 — Показать сохранённый пароль
«Джарвис, найди сохранённый пароль от [сайт] в браузере и покажи мне.»
Cat: BROWSER | Passwords
Diff: L1 | Tools: credential store | Web0 Code1 Files0 Vision0 Long0 | Auto 4
Caps: password retrieval
SAFETY-SENSITIVE: только текущему пользователю, подтверждение личности.

### 312 — Экспорт и чистка закладок
«Джарвис, экспортируй закладки, убери битые и разложи по папкам по темам.»
Cat: BROWSER | Bookmarks
Diff: L2 | Tools: browser, link checker | Web1 Code1 Files1 Vision0 Long0 | Auto 6
Caps: bookmark export, dead-link cleanup

### 313 — Дубликаты вкладок
«Джарвис, найди дубликаты вкладок и предложи, какие закрыть.»
Cat: BROWSER | Tabs
Diff: L1 | Tools: browser automation | Web0 Code1 Files0 Vision0 Long0 | Auto 5
Caps: tab dedup, memory cleanup

### 314 — Рабочая сессия
«Джарвис, открой рабочую сессию: [сайты] в отдельных окнах, залогинься в [сервисы].»
Cat: BROWSER | Session
Diff: L2 | Tools: browser automation | Web1 Code1 Files0 Vision0 Long0 | Auto 6
Caps: session orchestration, auto-login

### 315 — Сохранение страниц
«Джарвис, сохрани [страницы] в PDF/MHTML в папку [X] с понятными именами.»
Cat: BROWSER | Capture
Diff: L1 | Tools: browser, pdf | Web1 Code1 Files1 Vision0 Long0 | Auto 5
Caps: page capture, naming convention

### 316 — Поиск по истории
«Джарвис, найди в истории браузера, когда я смотрел [тема], и покажи ссылки.»
Cat: BROWSER | History
Diff: L1 | Tools: history db | Web0 Code1 Files0 Vision0 Long0 | Auto 5
Caps: history search, time filtering

### 317 — Автозаполнение форм
«Джарвис, заполни формы на [сайт] моими данными из профиля.»
Cat: BROWSER | Forms
Diff: L1 | Tools: browser automation, profile | Web1 Code1 Files0 Vision0 Long0 | Auto 5
Caps: form autofill, profile management

### 318 — Аудит расширений
«Джарвис, проверь мои расширения на утечки и скорость, отключи подозрительные.»
Cat: BROWSER | Extensions
Diff: L2 | Tools: browser, review db | Web1 Code1 Files0 Vision0 Long0 | Auto 6
Caps: extension audit, disable decisions

### 319 — Умные загрузки
«Джарвис, скачай [файлы] со [страницы], проверь хэши и разложи по папкам.»
Cat: BROWSER | Downloads
Diff: L2 | Tools: downloader, hashing | Web1 Code1 Files1 Vision0 Long0 | Auto 6
Caps: batch download, integrity check

### 320 — Скриншоты страниц
«Джарвис, сделай скриншоты [страницы] в полный рост и собери в PDF-отчёт.»
Cat: BROWSER | Screenshots
Diff: L2 | Tools: headless browser, pdf | Web1 Code1 Files1 Vision1 Long0 | Auto 6
Caps: fullpage screenshots, report assembly

### 321 — Чистка браузера
«Джарвис, почисти браузер: кэш, куки, историю, но сохрани пароли и нужные куки.»
Cat: BROWSER | Cleanup
Diff: L2 | Tools: browser | Web0 Code1 Files0 Vision0 Long0 | Auto 6
Caps: selective cleanup, settings preservation

### 322 — Профили браузера
«Джарвис, настрой профили браузера «работа» и «личное» с разными расширениями.»
Cat: BROWSER | Profiles
Diff: L2 | Tools: browser | Web0 Code1 Files0 Vision0 Long0 | Auto 5
Caps: profile setup, segregation

### 323 — Умная корзина
«Джарвис, когда цена [товар] упадёт до [N], положи в корзину и попроси меня подтвердить оплату.»
Cat: BROWSER | Cart
Diff: L3 | Tools: browser, scheduler, notifier | Web1 Code1 Files0 Vision0 Long1 | Auto 7
Caps: price-trigger cart, confirmation gate
SAFETY-SENSITIVE: оплата только после явного подтверждения.

### 324 — Заполнение веб-отчёта
«Джарвис, заполни форму отчёта на [сайт] данными из [файл] и сохрани черновик.»
Cat: BROWSER | Web forms
Diff: L2 | Tools: browser, file parse | Web1 Code1 Files1 Vision0 Long0 | Auto 6
Caps: data-driven form filling

### 325 — Слежка за изменением страницы
«Джарвис, следи за [URL] и показывай, что изменилось, когда обновится.»
Cat: BROWSER | Page watch
Diff: L2 | Tools: scheduler, diff | Web1 Code1 Files1 Vision0 Long1 | Auto 7
Caps: content diffing, change notification

### 326 — Восстановление сессии
«Джарвис, восстанови мои вкладки после перезагрузки из истории за [период].»
Cat: BROWSER | Session restore
Diff: L1 | Tools: history, browser | Web0 Code1 Files0 Vision0 Long0 | Auto 5
Caps: session reconstruction

### 327 — Сравнение скорости сайтов
«Джарвис, замерь скорость загрузки [сайты], сравни и объясни, почему один быстрее.»
Cat: BROWSER | Performance
Diff: L2 | Tools: headless browser, metrics | Web1 Code1 Files1 Vision0 Long0 | Auto 6
Caps: load-time benchmarking, bottleneck analysis

### 328 — Публичный профиль человека
«Джарвис, найди публичные профили [имя] в соцсетях и собери открытую информацию.»
Cat: WEB | OSINT
Diff: L2 | Tools: search, social api | Web1 Code0 Files1 Vision0 Long0 | Auto 6
Caps: public footprint aggregation
SAFETY-SENSITIVE: только публичные данные.

### 329 — Озвучка статьи
«Джарвис, прочитай мне статью [URL] вслух и перескажи главное.»
Cat: VOICE | Read aloud
Diff: L1 | Tools: tts, browser | Web1 Code0 Files0 Vision0 Long0 | Auto 5
Caps: text-to-speech reading, summary mode

### 330 — История заказов
«Джарвис, собери историю моих заказов на [магазины] и посчитай траты за [период].»
Cat: WEB | Purchase history
Diff: L2 | Tools: browser, spreadsheets | Web1 Code1 Files1 Vision0 Long0 | Auto 6
Caps: purchase aggregation, spend analysis

### 331 — Скриншот при ошибке сайта
«Джарвис, когда на [сайт] появится ошибка, сделай скриншот и сообщи с деталями.»
Cat: BROWSER | Error capture
Diff: L3 | Tools: browser, notifier | Web1 Code1 Files1 Vision1 Long1 | Auto 8
Caps: error detection, evidence capture

### 332 — Синхронизация закладок
«Джарвис, синхронизируй закладки между браузерами и убери дубликаты.»
Cat: BROWSER | Sync
Diff: L2 | Tools: browser | Web0 Code1 Files1 Vision0 Long0 | Auto 5
Caps: cross-browser sync, dedup

### 333 — Параллельный перевод страницы
«Джарвис, переведи страницу [URL] на [язык] и покажи рядом с оригиналом.»
Cat: BROWSER | Translate
Diff: L1 | Tools: llm, browser | Web1 Code0 Files0 Vision0 Long0 | Auto 5
Caps: inline bilingual view

### 334 — Стартовая страница дня
«Джарвис, настрой стартовую страницу: погода, задачи дня, быстрые ссылки.»
Cat: BROWSER | Homepage
Diff: L1 | Tools: browser, calendar | Web1 Code1 Files0 Vision0 Long0 | Auto 5
Caps: personalized start page

### 335 — Мониторинг личного кабинета
«Джарвис, проверяй мой ЛК на [сайт] ежедневно и сообщай о новых уведомлениях.»
Cat: BROWSER | Account watch
Diff: L3 | Tools: browser, scheduler, notifier | Web1 Code1 Files0 Vision0 Long1 | Auto 8
Caps: account monitoring, notification relay

### 336 — Закладки за неделю
«Джарвис, добавь в закладки всё, что я открыл за неделю, и предложи, что удалить.»
Cat: BROWSER | Bookmark assistant
Diff: L2 | Tools: history, llm | Web0 Code1 Files0 Vision0 Long0 | Auto 6
Caps: weekly bookmark curation

### 337 — Поиск вкладки
«Джарвис, найди вкладку, где упоминается [слово], и переключи меня на неё.»
Cat: BROWSER | Tab search
Diff: L1 | Tools: browser automation | Web0 Code1 Files0 Vision0 Long0 | Auto 5
Caps: in-tab content search, focus switch

### 338 — Тестирование веб-формы
«Джарвис, заполни форму [URL] разными данными и покажи ошибки валидации.»
Cat: QA | Form fuzzing
Diff: L2 | Tools: browser, script | Web1 Code1 Files1 Vision0 Long0 | Auto 6
Caps: validation testing, error catalog

### 339 — Таймер фокуса на сайтах
«Джарвис, ставь таймер на [сайты] и предупреждай меня каждые [N] минут.»
Cat: BROWSER | Focus
Diff: L1 | Tools: scheduler, notifier | Web0 Code1 Files0 Vision0 Long0 | Auto 5
Caps: focus timer, distraction warning

### 340 — Экспорт паролей с аудитом
«Джарвис, экспортируй мои пароли в менеджер и проверь дубликаты и слабые.»
Cat: BROWSER | Passwords
Diff: L2 | Tools: credential store, llm | Web0 Code1 Files1 Vision0 Long0 | Auto 5
Caps: password export, strength audit
SAFETY-SENSITIVE: подтверждение мастер-паролем.

### 341 — Объяснение кода
«Джарвис, объясни, что делает этот код [файл/фрагмент]: построчно и на уровне архитектуры.»
Cat: CODING | Explanation
Diff: L1 | Tools: llm, ide | Web0 Code1 Files1 Vision0 Long0 | Auto 4
Caps: code explanation, architecture narration

### 342 — Поиск бага
«Джарвис, вот код, который не работает как надо: [файл]. Найди баг и объясни причину.»
Cat: DEBUGGING | Bug hunt
Diff: L2 | Tools: ide, debugger, llm | Web0 Code1 Files1 Vision0 Long0 | Auto 6
Caps: root-cause analysis, fix proposal

### 343 — Рефакторинг
«Джарвис, отрефактори [файл]: улучши читаемость, разбей на функции, не меняй поведение.»
Cat: CODING | Refactoring
Diff: L2 | Tools: ide, tests | Web0 Code1 Files1 Vision0 Long0 | Auto 6
Caps: safe refactoring, behavior preservation

### 344 — Написание тестов
«Джарвис, напиши unit-тесты для [модуль] с покрытием ключевых сценариев и edge cases.»
Cat: TESTING | Unit tests
Diff: L2 | Tools: test framework | Web0 Code1 Files1 Vision0 Long0 | Auto 6
Caps: test authoring, edge-case coverage

### 345 — Код-ревью
«Джарвис, сделай код-ревью изменений в [ветка]: найди проблемы и укажи приоритеты.»
Cat: SOFTWARE DEVELOPMENT | Code review
Diff: L2 | Tools: git, llm | Web0 Code1 Files0 Vision0 Long0 | Auto 6
Caps: diff review, issue prioritization

### 346 — Поиск утечек памяти
«Джарвис, проанализируй [приложение] на утечки памяти и найди источник.»
Cat: DEBUGGING | Memory leaks
Diff: L3 | Tools: profiler, debugger | Web0 Code1 Files0 Vision0 Long0 | Auto 7
Caps: leak tracing, allocation analysis

### 347 — Оптимизация узких мест
«Джарвис, найди узкие места в [проект] и предложи оптимизации с оценкой выигрыша.»
Cat: PERFORMANCE | Code optimization
Diff: L3 | Tools: profiler, benchmark | Web0 Code1 Files1 Vision0 Long0 | Auto 7
Caps: bottleneck profiling, optimization plan

### 348 — Документирование кода
«Джарвис, напиши документацию для [модуль] с примерами использования.»
Cat: CODING | Docs
Diff: L1 | Tools: llm | Web0 Code0 Files1 Vision0 Long0 | Auto 5
Caps: docstring generation, usage examples

### 349 — CLI-инструмент
«Джарвис, сделай CLI-инструмент, который [задача], с аргументами и help.»
Cat: CODING | CLI
Diff: L2 | Tools: python/click | Web0 Code1 Files1 Vision0 Long0 | Auto 6
Caps: CLI scaffolding, arg parsing

### 350 — Скрипт автоматизации
«Джарвис, напиши скрипт, который [автоматизация], с обработкой ошибок и логами.»
Cat: AUTOMATION | Scripting
Diff: L2 | Tools: python/shell | Web0 Code1 Files1 Vision0 Long0 | Auto 6
Caps: workflow scripting, error handling

### 351 — Парсер данных
«Джарвис, напиши парсер для [источник], который извлекает [данные] в [формат].»
Cat: CODING | Parsing
Diff: L2 | Tools: python | Web0 Code1 Files1 Vision0 Long0 | Auto 6
Caps: parser build, schema mapping

### 352 — Поиск по коду
«Джарвис, найди в проекте все места, где [паттерн], и покажи с контекстом.»
Cat: CODING | Code search
Diff: L1 | Tools: rg, ide | Web0 Code1 Files1 Vision0 Long0 | Auto 4
Caps: semantic code search, context snippets

### 353 — Конфликт зависимостей
«Джарвис, разберись с конфликтом зависимостей в [проект] и предложи совместимые версии.»
Cat: DEBUGGING | Dependencies
Diff: L2 | Tools: pip/npm, resolver | Web1 Code1 Files1 Vision0 Long0 | Auto 6
Caps: dependency resolution, version pinning

### 354 — Безопасное обновление зависимостей
«Джарвис, обнови зависимости [проект]: сначала changelog и совместимость, потом применение.»
Cat: SOFTWARE DEVELOPMENT | Updates
Diff: L2 | Tools: package manager | Web1 Code1 Files1 Vision0 Long0 | Auto 6
Caps: update staging, regression check

### 355 — Новый endpoint
«Джарвис, добавь в [сервис] endpoint [описание] с валидацией, ошибками и документацией.»
Cat: CODING | API dev
Diff: L2 | Tools: framework, tests | Web0 Code1 Files1 Vision0 Long0 | Auto 6
Caps: endpoint implementation, schema validation

### 356 — Интеграция стороннего API
«Джарвис, интегрируй [API] в [проект]: авторизация, вызовы, лимиты.»
Cat: APIs | Integration
Diff: L2 | Tools: http client, llm | Web1 Code1 Files1 Vision0 Long0 | Auto 6
Caps: api integration, rate-limit handling

### 357 — Скрипт миграции данных
«Джарвис, напиши миграцию [данные] из [источник] в [назначение] с проверкой целостности.»
Cat: DATABASES | Migration
Diff: L3 | Tools: python, sql | Web0 Code1 Files1 Vision0 Long0 | Auto 7
Caps: ETL script, integrity verification

### 358 — Генерация тестовых данных
«Джарвис, сгенерируй тестовые данные [описание] для [проект] в нужном формате.»
Cat: TESTING | Fixtures
Diff: L1 | Tools: faker/script | Web0 Code1 Files1 Vision0 Long0 | Auto 5
Caps: synthetic data generation

### 359 — Минимальный репро-кейс
«Джарвис, построй минимальный пример, который воспроизводит ошибку [описание].»
Cat: DEBUGGING | Repro
Diff: L2 | Tools: ide, git | Web0 Code1 Files1 Vision0 Long0 | Auto 6
Caps: minimal repro construction

### 360 — Анализ логов падения
«Джарвис, проанализируй логи [файл] и найди, где и почему падает приложение.»
Cat: LOG ANALYSIS | Crash
Diff: L2 | Tools: log tools, llm | Web0 Code1 Files1 Vision0 Long0 | Auto 6
Caps: log mining, crash reconstruction

### 361 — Профилирование
«Джарвис, профилируй [скрипт/функцию] и покажи, где тратится время и память.»
Cat: PERFORMANCE | Profiling
Diff: L2 | Tools: profiler | Web0 Code1 Files0 Vision0 Long0 | Auto 6
Caps: hotspot detection, memory profile

### 362 — Безопасность кода
«Джарвис, проверь [проект] на уязвимости: инъекции, секреты, опасные функции.»
Cat: SECURITY | Code audit
Diff: L2 | Tools: semgrep/bandit, llm | Web0 Code1 Files1 Vision0 Long0 | Auto 6
Caps: static analysis, vulnerability triage

### 363 — Секреты в коде
«Джарвис, найди захардкоженные ключи в [проект] и помоги вынести их в конфиг.»
Cat: SECURITY | Secrets
Diff: L2 | Tools: scanner, git | Web0 Code1 Files1 Vision0 Long0 | Auto 6
Caps: secret detection, safe extraction

### 364 — Регулярные выражения
«Джарвис, напиши regex для [задача] и объясни, как он работает.»
Cat: CODING | Regex
Diff: L1 | Tools: llm, regex tester | Web0 Code0 Files0 Vision0 Long0 | Auto 4
Caps: regex authoring, pattern explanation

### 365 — Обработка больших данных
«Джарвис, перепиши [скрипт], чтобы он работал с [N] ГБ без падения.»
Cat: ENGINEERING | Big data
Diff: L3 | Tools: chunking, streaming | Web0 Code1 Files1 Vision0 Long0 | Auto 7
Caps: streaming processing, memory efficiency

### 366 — Параллелизм
«Джарвис, ускорь [скрипт] параллелизмом/асинхронностью, сохранив корректность.»
Cat: CODING | Concurrency
Diff: L3 | Tools: asyncio/threads | Web0 Code1 Files1 Vision0 Long0 | Auto 7
Caps: concurrency refactor, race detection

### 367 — Линтинг и форматирование
«Джарвис, настрой линтер и форматтер для [проект] и примени.»
Cat: SOFTWARE DEVELOPMENT | Tooling
Diff: L1 | Tools: ruff/black, config | Web0 Code1 Files1 Vision0 Long0 | Auto 5
Caps: lint setup, style enforcement

### 368 — Скелет проекта
«Джарвис, создай скелет проекта [тип] со структурой, конфигами и README.»
Cat: SOFTWARE DEVELOPMENT | Scaffolding
Diff: L1 | Tools: template | Web0 Code1 Files1 Vision0 Long0 | Auto 5
Caps: project scaffolding, boilerplate

### 369 — Код по описанию
«Джарвис, напиши модуль, который [функциональность], с типами и комментариями.»
Cat: CODING | Generation
Diff: L2 | Tools: llm, ide | Web0 Code1 Files1 Vision0 Long0 | Auto 6
Caps: code generation, spec adherence

### 370 — Перевод кода
«Джарвис, переведи [код] с [язык] на [язык], сохранив поведение и стиль.»
Cat: CODING | Porting
Diff: L2 | Tools: llm | Web0 Code1 Files1 Vision0 Long0 | Auto 6
Caps: language porting, idiom mapping

### 371 — Проектирование модулей
«Джарвис, спроектируй классы и модули для [задача]: схема, обязанности, интерфейсы.»
Cat: SOFTWARE DEVELOPMENT | Design
Diff: L2 | Tools: llm, diagrams | Web0 Code1 Files1 Vision0 Long0 | Auto 6
Caps: architecture design, interface spec

### 372 — Прототип приложения
«Джарвис, сделай минимально рабочий прототип [приложение]: [функции], без полировки.»
Cat: APP CREATION | Prototype
Diff: L3 | Tools: stack, llm | Web0 Code1 Files1 Vision0 Long0 | Auto 7
Caps: rapid prototyping, MVP build

### 373 — Скрипт-генератор отчётов
«Джарвис, напиши скрипт, который генерирует отчёт [формат] из [данные] с графиками.»
Cat: DATA VISUALIZATION | Reporting
Diff: L2 | Tools: pandas, charts | Web0 Code1 Files1 Vision0 Long0 | Auto 6
Caps: report generation, chart embedding

### 374 — Дописывание кода
«Джарвис, допиши [файл]: что здесь должно быть, чтобы [задача] работала корректно.»
Cat: CODING | Completion
Diff: L1 | Tools: llm, ide | Web0 Code1 Files1 Vision0 Long0 | Auto 5
Caps: code completion, context understanding

### 375 — Кросс-платформенность
«Джарвис, сделай [скрипт] кросс-платформенным: пути, кодировки, права.»
Cat: ENGINEERING | Portability
Diff: L2 | Tools: os-agnostic code | Web0 Code1 Files1 Vision0 Long0 | Auto 6
Caps: cross-platform fixes, path handling

### 376 — Надёжные ошибки
«Джарвис, добавь в [код] retry, fallback и логирование ошибок.»
Cat: SOFTWARE DEVELOPMENT | Robustness
Diff: L2 | Tools: try/except, retry lib | Web0 Code1 Files1 Vision0 Long0 | Auto 6
Caps: resilience patterns, graceful degradation

### 377 — Конфигурация приложения
«Джарвис, сделай конфигурацию для [приложение]: файлы, валидация, env.»
Cat: SOFTWARE DEVELOPMENT | Config
Diff: L1 | Tools: pydantic/env | Web0 Code1 Files1 Vision0 Long0 | Auto 5
Caps: config schema, env handling

### 378 — Структурированные логи
«Джарвис, настрой структурированное логирование в [проект] с уровнями и ротацией.»
Cat: SOFTWARE DEVELOPMENT | Logging
Diff: L1 | Tools: logging lib | Web0 Code1 Files1 Vision0 Long0 | Auto 5
Caps: log setup, rotation, structured output

### 379 — Интерактивный скрипт
«Джарвис, сделай [скрипт] интерактивным: меню, вопросы, валидация ввода.»
Cat: CODING | Interactive CLI
Diff: L2 | Tools: python | Web0 Code1 Files1 Vision0 Long0 | Auto 5
Caps: interactive prompts, input validation

### 380 — Работа с датами
«Джарвис, напиши код для [даты/таймзоны/расписание]: [задача].»
Cat: CODING | Dates
Diff: L1 | Tools: datetime lib | Web0 Code0 Files1 Vision0 Long0 | Auto 5
Caps: date logic, timezone handling

### 381 — Шифрование данных
«Джарвис, добавь шифрование [данные] в [проект] с безопасным хранением ключей.»
Cat: SECURITY | Crypto
Diff: L2 | Tools: crypto lib | Web0 Code1 Files1 Vision0 Long0 | Auto 6
Caps: encryption integration, key management

### 382 — Пакетная обработка файлов
«Джарвис, напиши код для пакетной обработки [файлы]: [операция] с прогрессом.»
Cat: FILESYSTEM | Batch processing
Diff: L2 | Tools: python | Web0 Code1 Files1 Vision0 Long0 | Auto 6
Caps: batch ops, progress tracking

### 383 — Скрипт по изображениям
«Джарвис, напиши скрипт для [операция с изображениями] в папке [путь].»
Cat: IMAGE PROCESSING | Scripting
Diff: L2 | Tools: PIL/opencv | Web0 Code1 Files1 Vision0 Long0 | Auto 6
Caps: image batch ops, format handling

### 384 — Скрипт по PDF
«Джарвис, напиши скрипт, который [операция с PDF] для файлов из [папка].»
Cat: PDF | Scripting
Diff: L2 | Tools: pypdf/pdf libs | Web0 Code1 Files1 Vision0 Long0 | Auto 6
Caps: pdf manipulation, batch processing

### 385 — Скрипт по Excel
«Джарвис, напиши скрипт обработки [таблицы]: [операция] с форматированием.»
Cat: EXCEL | Scripting
Diff: L2 | Tools: openpyxl/pandas | Web0 Code1 Files1 Vision0 Long0 | Auto 6
Caps: spreadsheet automation, formatting

### 386 — Работа с БД
«Джарвис, напиши код для работы с [БД]: схема, запросы, индексы под [задачу].»
Cat: DATABASES | Development
Diff: L2 | Tools: db driver | Web0 Code1 Files1 Vision0 Long0 | Auto 6
Caps: db integration, schema design

### 387 — ORM-модели
«Джарвис, опиши модели [ORM] для [сущности] с отношениями и индексами.»
Cat: DATABASES | ORM
Diff: L2 | Tools: sqlalchemy/django | Web0 Code1 Files1 Vision0 Long0 | Auto 6
Caps: model definition, relationship mapping

### 388 — SQL-оптимизация
«Джарвис, напиши SQL для [задача], оптимизируй и объясни план выполнения.»
Cat: DATABASES | SQL
Diff: L2 | Tools: sql client, explain | Web0 Code1 Files1 Vision0 Long0 | Auto 6
Caps: query writing, index tuning

### 389 — Веб-скрапер
«Джарвис, напиши скрапер для [сайт], который собирает [данные] в [формат].»
Cat: CODING | Scraping
Diff: L3 | Tools: requests/bs4 | Web1 Code1 Files1 Vision0 Long0 | Auto 7
Caps: scraper build, anti-bot handling
SAFETY-SENSITIVE: соблюдение robots.txt и ToS целевого сайта.

### 390 — API-клиент
«Джарвис, напиши клиент для [API]: методы, ошибки, пагинация, лимиты.»
Cat: APIs | Client
Diff: L2 | Tools: http client | Web0 Code1 Files1 Vision0 Long0 | Auto 6
Caps: api client design, error mapping

### 391 — Простой веб-сервер
«Джарвис, сделай простой веб-сервер [функциональность] на [стек].»
Cat: CODING | Web server
Diff: L2 | Tools: flask/fastapi | Web0 Code1 Files1 Vision0 Long0 | Auto 6
Caps: server implementation, routing

### 392 — Бот для платформы
«Джарвис, напиши бота для [платформа], который [функциональность].»
Cat: AUTOMATION | Bots
Diff: L3 | Tools: bot framework | Web1 Code1 Files1 Vision0 Long0 | Auto 7
Caps: bot build, event handling

### 393 — Сценарий браузерной автоматизации
«Джарвис, напиши сценарий браузерной автоматизации: [действия].»
Cat: BROWSER AUTOMATION | Scripting
Diff: L2 | Tools: playwright/selenium | Web1 Code1 Files0 Vision0 Long0 | Auto 6
Caps: browser scripting, selector management

### 394 — Планировщик в коде
«Джарвис, добавь планировщик задач в [скрипт]: [расписание], с обработкой пропусков.»
Cat: AUTOMATION | Scheduling
Diff: L2 | Tools: schedule/apscheduler | Web0 Code1 Files1 Vision0 Long0 | Auto 6
Caps: job scheduling, missed-run recovery

### 395 — Переписывание легаси
«Джарвис, перепиши [легаси-код] на [стек], сохранив совместимость.»
Cat: SOFTWARE DEVELOPMENT | Modernization
Diff: L4 | Tools: git, tests, llm | Web0 Code1 Files1 Vision0 Long0 | Auto 7
Caps: legacy migration, parity testing

### 396 — Типизация
«Джарвис, добавь типизацию в [код] и исправь найденные ошибки.»
Cat: CODING | Typing
Diff: L2 | Tools: mypy/pyright | Web0 Code1 Files1 Vision0 Long0 | Auto 6
Caps: type annotation, static check fixes

### 397 — Сборка и упаковка
«Джарвис, настрой сборку [проект]: [формат упаковки], CI-готовность.»
Cat: DEVOPS | Packaging
Diff: L2 | Tools: pyinstaller/npm | Web0 Code1 Files1 Vision0 Long0 | Auto 6
Caps: build pipeline, artifact creation

### 398 — Веб-приложение целиком
«Джарвис, сделай веб-приложение [описание] с фронтендом и бэкендом.»
Cat: APP CREATION | Web app
Diff: L4 | Tools: full stack | Web0 Code1 Files1 Vision0 Long0 | Auto 7
Caps: full-stack build, deployment ready

### 399 — Игра-прототип
«Джарвис, сделай простую игру [описание] на [технология].»
Cat: GAMES | Prototype
Diff: L3 | Tools: pygame/web | Web0 Code1 Files1 Vision0 Long0 | Auto 7
Caps: game prototype, playable demo

### 400 — Мини-утилита
«Джарвис, напиши маленькую утилиту для [задача] без лишних зависимостей.»
Cat: CODING | Utilities
Diff: L1 | Tools: stdlib | Web0 Code1 Files1 Vision0 Long0 | Auto 5
Caps: standalone utility, stdlib-only

### 401 — Скрипт бэкапа
«Джарвис, напиши скрипт бэкапа [данные] с ротацией и проверкой восстановления.»
Cat: BACKUPS | Scripting
Diff: L2 | Tools: python/robocopy | Web0 Code1 Files1 Vision0 Long0 | Auto 6
Caps: backup automation, rotation policy

### 402 — Метрики и мониторинг в коде
«Джарвис, добавь метрики [перечень] в [приложение] с алертами.»
Cat: MONITORING | Instrumentation
Diff: L2 | Tools: prometheus/statsd | Web0 Code1 Files1 Vision0 Long0 | Auto 6
Caps: metric hooks, alert wiring

### 403 — Двусторонняя синхронизация
«Джарвис, напиши скрипт синхронизации [папки] в обе стороны без дубликатов.»
Cat: FILESYSTEM | Sync
Diff: L2 | Tools: python | Web0 Code1 Files1 Vision0 Long0 | Auto 6
Caps: bidirectional sync, conflict handling

### 404 — Отчёт на почту по расписанию
«Джарвис, напиши скрипт, который раз в [период] присылает отчёт [содержание] на почту.»
Cat: AUTOMATION | Reports
Diff: L2 | Tools: scheduler, mail | Web0 Code1 Files1 Vision0 Long1 | Auto 7
Caps: scheduled reporting, mail delivery

### 405 — Защита скрипта
«Джарвис, защити [скрипт]: обфусцируй и добавь лицензионную проверку.»
Cat: SECURITY | Code protection
Diff: L2 | Tools: obfuscator | Web0 Code1 Files1 Vision0 Long0 | Auto 6
Caps: code obfuscation, license gate

### 406 — Анализ файла данных
«Джарвис, напиши код для анализа [файл]: [вопросы], с выводами.»
Cat: DATA ANALYSIS | Scripting
Diff: L2 | Tools: pandas | Web0 Code1 Files1 Vision0 Long0 | Auto 6
Caps: data exploration, insight extraction

### 407 — Кэширование
«Джарвис, добавь кэш в [код] для ускорения [операция].»
Cat: PERFORMANCE | Caching
Diff: L1 | Tools: cache lib | Web0 Code1 Files1 Vision0 Long0 | Auto 5
Caps: cache layer, invalidation logic

### 408 — Сетевая задача
«Джарвис, напиши код для [сетевая задача]: [протокол], с таймаутами.»
Cat: NETWORK DIAGNOSTICS | Code
Diff: L2 | Tools: sockets/http | Web0 Code1 Files1 Vision0 Long0 | Auto 6
Caps: network programming, timeout handling

### 409 — Вебхуки
«Джарвис, реализуй приём/отправку вебхуков для [событие] с проверкой подписи.»
Cat: APIs | Webhooks
Diff: L2 | Tools: framework | Web0 Code1 Files1 Vision0 Long0 | Auto 6
Caps: webhook endpoint, signature verification

### 410 — Авторизация в приложении
«Джарвис, добавь [OAuth/JWT] авторизацию в [приложение].»
Cat: SECURITY | AuthN
Diff: L3 | Tools: auth libs | Web0 Code1 Files1 Vision0 Long0 | Auto 7
Caps: auth integration, token lifecycle

### 411 — Тестовая среда
«Джарвис, настрой тестовую среду: фикстуры, моки, изолированные данные.»
Cat: TESTING | Environment
Diff: L2 | Tools: pytest, fixtures | Web0 Code1 Files1 Vision0 Long0 | Auto 6
Caps: test isolation, mock design

### 412 — Fuzz-тесты
«Джарвис, напиши fuzz-тесты для [функция] и найди краши.»
Cat: TESTING | Fuzzing
Diff: L3 | Tools: hypothesis/afl | Web0 Code1 Files1 Vision0 Long0 | Auto 7
Caps: fuzz harness, crash triage

### 413 — Нагрузочный тест
«Джарвис, сделай нагрузочный тест [сервис]: [N] запросов, покажи bottleneck.»
Cat: TESTING | Load
Diff: L3 | Tools: locust/k6 | Web0 Code1 Files1 Vision0 Long0 | Auto 7
Caps: load testing, capacity insight

### 414 — UI-тесты
«Джарвис, напиши UI-тесты для [приложение]: сценарии со скриншотами.»
Cat: TESTING | UI
Diff: L3 | Tools: playwright | Web0 Code1 Files1 Vision1 Long0 | Auto 7
Caps: e2e tests, screenshot diffs

### 415 — Покрытие тестами
«Джарвис, измерь покрытие [проект] и предложи, что тестировать первым.»
Cat: TESTING | Coverage
Diff: L1 | Tools: coverage tool | Web0 Code1 Files1 Vision0 Long0 | Auto 5
Caps: coverage measurement, gap ranking

### 416 — Падающий тест
«Джарвис, [тест] падает. Разберись: баг кода или теста, и исправь.»
Cat: DEBUGGING | Test failure
Diff: L2 | Tools: debugger | Web0 Code1 Files1 Vision0 Long0 | Auto 6
Caps: failure diagnosis, fix verification

### 417 — Шпаргалка сниппетов
«Джарвис, собери полезные сниппеты для [задача] в шпаргалку с примерами.»
Cat: CODING | Snippets
Diff: L1 | Tools: llm | Web0 Code0 Files1 Vision0 Long0 | Auto 5
Caps: snippet curation, quick reference

### 418 — Алгоритмическая задача
«Джарвис, реши [задача]: объясни подход и сложность, реализуй и протестируй.»
Cat: MATHEMATICS | Algorithms
Diff: L2 | Tools: python | Web0 Code1 Files1 Vision0 Long0 | Auto 6
Caps: algorithm design, complexity analysis

### 419 — Выбор структуры данных
«Джарвис, помоги выбрать структуру данных для [задача] и реализуй.»
Cat: CODING | Data structures
Diff: L2 | Tools: python | Web0 Code1 Files1 Vision0 Long0 | Auto 6
Caps: data structure selection, implementation

### 420 — Оптимизация рекурсии
«Джарвис, оптимизируй [рекурсивный код]: устрани переполнение стека.»
Cat: PERFORMANCE | Recursion
Diff: L2 | Tools: python | Web0 Code1 Files1 Vision0 Long0 | Auto 6
Caps: recursion fix, iterative rewrite

### 421 — Проблемы кодировок
«Джарвис, исправь проблемы с кодировками в [проект]: [симптомы].»
Cat: DEBUGGING | Encoding
Diff: L2 | Tools: python | Web0 Code1 Files1 Vision0 Long0 | Auto 6
Caps: encoding fixes, normalization

### 422 — Дата-пайплайн
«Джарвис, собери пайплайн обработки данных: [этапы], с кэшем промежуточных результатов.»
Cat: ENGINEERING | Pipelines
Diff: L3 | Tools: python, orchestration | Web0 Code1 Files1 Vision0 Long0 | Auto 7
Caps: pipeline design, stage caching

### 423 — Фоновые задачи
«Джарвис, добавь фоновые задачи в [приложение]: очередь, retry, статусы.»
Cat: AUTOMATION | Background jobs
Diff: L3 | Tools: celery/rq | Web0 Code1 Files1 Vision0 Long0 | Auto 7
Caps: job queue, retry policy, status API

### 424 — Автодокументация из кода
«Джарвис, настрой автогенерацию документации из кода [проект] в [формат].»
Cat: SOFTWARE DEVELOPMENT | Docs gen
Diff: L1 | Tools: sphinx/mkdocs | Web0 Code1 Files1 Vision0 Long0 | Auto 5
Caps: docs generation, publishing setup

### 425 — Дубликаты кода
«Джарвис, найди дублирование в [проект] и предложи, как объединить.»
Cat: CODING | DRY
Diff: L2 | Tools: analysis, llm | Web0 Code1 Files1 Vision0 Long0 | Auto 6
Caps: duplication detection, consolidation plan

### 426 — Сложные функции
«Джарвис, найди функции с высокой сложностью в [проект] и предложи упрощение.»
Cat: CODING | Maintainability
Diff: L2 | Tools: metrics, llm | Web0 Code1 Files1 Vision0 Long0 | Auto 6
Caps: complexity scoring, simplification

### 427 — Совместимость со старым Python
«Джарвис, сделай [код] совместимым с [версия Python].»
Cat: ENGINEERING | Compatibility
Diff: L2 | Tools: python | Web0 Code1 Files1 Vision0 Long0 | Auto 6
Caps: backporting, syntax downgrade

### 428 — Порядок в env
«Джарвис, приведи в порядок env-переменные [проект]: список, дефолты, документация.»
Cat: SOFTWARE DEVELOPMENT | Env
Diff: L1 | Tools: .env, docs | Web0 Code1 Files1 Vision0 Long0 | Auto 5
Caps: env inventory, defaults, docs

### 429 — Клиент для БД
«Джарвис, напиши удобный интерфейс для работы с [БД]: [операции].»
Cat: DATABASES | Tooling
Diff: L2 | Tools: python | Web0 Code1 Files1 Vision0 Long0 | Auto 6
Caps: db client tool, CRUD wrapper

### 430 — Отчёт о зависимостях
«Джарвис, собери отчёт о зависимостях [проект]: версии, лицензии, уязвимости.»
Cat: SECURITY | Supply chain
Diff: L2 | Tools: audit tools | Web1 Code1 Files1 Vision0 Long0 | Auto 6
Caps: dependency audit, license report

### 431 — Инициализация репозитория с нуля
«Джарвис, инициализируй git-репозиторий для [папка]: .gitignore, README, лицензия, первый коммит, ветка main и защита от случайных коммитов в мастер.»
Cat: CODING | Git
Diff: L1 | Tools: git | Web0 Code1 Files1 Vision0 Long0 | Auto 6
Why: правильный старт проекта определяет всю дальнейшую историю
Caps: repo init, git hygiene, .gitignore generation

### 432 — Семантическое commit-сообщение
«Джарвис, составь commit-сообщение по Conventional Commits для изменений: [список файлов и что изменилось]. Укажи тип, scope и тело с контекстом.»
Cat: CODING | Git
Diff: L0 | Tools: git | Web0 Code1 Files1 Vision0 Long0 | Auto 4
Why: машиночитаемая история коммитов облегчает changelog и ревью
Caps: commit message generation, conventional commits

### 433 — Разбор истории коммитов
«Джарвис, проанализируй историю [репозиторий] за [период]: кто сколько коммитов, когда пик активности, какие файлы меняются чаще всего, сколько времени между коммитами.»
Cat: CODING | Git
Diff: L1 | Tools: git log | Web0 Code1 Files1 Vision0 Long1 | Auto 7
Why: понимание ритма разработки помогает планировать ревью и нагрузку
Caps: commit history analysis, developer productivity metrics

### 434 — Восстановление удалённого файла
«Джарвис, я случайно удалил [файл] три дня назад. Найди его в истории git и восстанови, не задевая остальные изменения.»
Cat: CODING | Git
Diff: L2 | Tools: git log, git checkout | Web0 Code1 Files1 Vision0 Long0 | Auto 6
Why: восстановление из истории — базовая операция, но с риском конфликтов
Caps: file recovery, history forensics

### 435 — Git bisect: поиск коммита-виновника
«Джарвис, запусти git bisect по [диапазон коммитов], чтобы найти коммит, сломавший [тест/поведение]. Автоматически прогоняй проверку на каждом шаге и выдай виновника.»
Cat: CODING | Git
Diff: L3 | Tools: git bisect | Web0 Code1 Files1 Vision0 Long1 | Auto 8
Why: бинарный поиск по истории кратно ускоряет поиск регрессий
Caps: regression hunting, bisect automation

### 436 — Разрешение merge-конфликтов
«Джарвис, разреши конфликты в [ветка] после merge: покажи оба варианта, объясни, что каждая сторона хотела сделать, и предложи объединённое решение.»
Cat: CODING | Git
Diff: L3 | Tools: git merge, diff3 | Web0 Code1 Files1 Vision0 Long1 | Auto 7
Why: конфликты — главная боль командной разработки, требуют понимания обоих контекстов
Caps: conflict resolution, merge strategy

### 437 — Cherry-pick выборочных коммитов
«Джарвис, перенеси коммиты [IDs] из [ветка-источник] в [ветка-назначение], разреши конфликты и проверь, что итоговый diff содержит только эти изменения.»
Cat: CODING | Git
Diff: L2 | Tools: git cherry-pick | Web0 Code1 Files1 Vision0 Long0 | Auto 7
Why: точечный перенос изменений без слияния целых веток
Caps: cherry-pick, selective change migration

### 438 — Интерактивный rebase и сквош
«Джарвис, перепиши историю [ветка]: объедини коммиты [список] в один, поправь сообщения, разнеси перепутанные изменения и проверь, что ничего не потерялось.»
Cat: CODING | Git
Diff: L4 | Tools: git rebase -i | Web0 Code1 Files1 Vision0 Long1 | Auto 8
Why: чистая история до merge в main экономит время ревьюеров
Caps: history rewriting, squash, rebase planning

### 439 — Управление stash
«Джарвис, сохрани незакоммиченные изменения в stash с описанием [текст], покажи список, помоги восстановить нужный и разберись с конфликтом при pop.»
Cat: CODING | Git
Diff: L1 | Tools: git stash | Web0 Code1 Files1 Vision0 Long0 | Auto 5
Why: переключение контекста без потери работы
Caps: stash management, work-in-progress preservation

### 440 — Ветвление по фичам
«Джарвис, создай схему веток для [фича]: от какой базы отходить, как называть ветки, куда мержить, когда удалять. Настрой защиту веток на remote.»
Cat: CODING | Git
Diff: L2 | Tools: git branch | Web0 Code1 Files1 Vision0 Long0 | Auto 6
Why: предсказуемый workflow веток снижает конфликты и хаос
Caps: branching strategy, branch protection

### 441 — Кто написал этот код: git blame
«Джарвис, покажи по [файл:строки], кто и когда написал каждую строку, и в каком коммите. Сгруппируй по автору и объясни аномалии (ночные коммиты, скопированные блоки).»
Cat: CODING | Git
Diff: L1 | Tools: git blame | Web0 Code1 Files1 Vision0 Long1 | Auto 6
Why: атрибуция кода нужна для вопросов, код-ревью и поиска экспериментаторов
Caps: code attribution, blame analysis

### 442 — Git hooks: автоматизация качества
«Джарвис, настрой pre-commit и pre-push хуки для [проект]: линтер, форматтер, проверка секретов, прогон быстрых тестов. Покажи, что делать при срабатывании блокировки.»
Cat: CODING | Git
Diff: L3 | Tools: git hooks, lint-staged | Web0 Code1 Files1 Vision0 Long0 | Auto 7
Why: хуки переносят проверки качества в момент коммита, а не CI
Caps: git hooks, pre-commit automation

### 443 — Submodules и монорепо-решения
«Джарвис, оцени наши подмодули в [репозиторий]: обнови их, найди рассинхронизацию, объясни, стоит ли переходить на монорепо или пакетный менеджер.»
Cat: CODING | Git
Diff: L4 | Tools: git submodule | Web0 Code1 Files1 Vision0 Long1 | Auto 7
Why: подмодули часто создают больше проблем, чем решают
Caps: submodule management, monorepo assessment

### 444 — Подпись коммитов GPG
«Джарвис, настрой подпись коммитов и тегов GPG для [репозиторий], добавь ключ на GitHub и проверь, что verify показывает зелёную галочку.»
Cat: SECURITY | Git
Diff: L3 | Tools: gpg, git config | Web1 Code1 Files1 Vision0 Long0 | Auto 6
Why: подписанные коммиты защищают от подмены автора и истории
Caps: commit signing, GPG key management

### 445 — Поиск секретов в истории git
«Джарвис, просканируй всю историю [репозиторий] на утёкшие пароли, ключи API и токены. Выдай, в каких коммитах и строках, какие из них ещё могут быть активны, и план очистки истории.»
Cat: SECURITY | Git
Diff: L3 | Tools: gitleaks, git filter-repo | Web0 Code1 Files1 Vision0 Long1 | Auto 7
Why: секреты в истории не исчезают при удалении файла — их надо вычищать
Caps: secret scanning, history scrubbing

### 446 — Ускорение огромного репозитория
«Джарвис, [репозиторий] клонируется 20 минут. Проанализируй причины (бинарные файлы, история, глубина), предложи и примени: shallow clone, sparse checkout, filter, LFS.»
Cat: PERFORMANCE | Git
Diff: L4 | Tools: git clone, git sparse-checkout, git lfs | Web0 Code1 Files1 Vision0 Long1 | Auto 8
Why: медленные клоны съедают часы у каждой новой машины разработчика
Caps: clone optimization, sparse checkout, repo slimming

### 447 — Git LFS для больших файлов
«Джарвис, переведи [тип файлов: бинарники, ассеты, датасеты] на Git LFS: настрой .gitattributes, мигрируй историю, объясни коллегам правила.»
Cat: CODING | Git
Diff: L4 | Tools: git lfs, git-lfs-migrate | Web0 Code1 Files1 Vision0 Long1 | Auto 7
Why: большие файлы в git раздувают репозиторий навсегда
Caps: git lfs, large file management

### 448 — Git worktrees: параллельные ветки
«Джарвис, настрой git worktree, чтобы держать [ветки] в отдельных папках одновременно. Покажи, как переключаться, и не дай задеть чужую ветку из неправильной папки.»
Cat: CODING | Git
Diff: L2 | Tools: git worktree | Web0 Code1 Files1 Vision0 Long0 | Auto 6
Why: одновременная работа над несколькими ветками без stash-танцев
Caps: worktree management, parallel development

### 449 — Откат плохого деплоя
«Джарвис, деплой [коммит] сломал прод. Построй план: revert или rollback, какие файлы/миграции затронуты, что проверить после отката, как зафиксировать урок.»
Cat: CODING | Git
Diff: L4 | Tools: git revert, git log | Web0 Code1 Files1 Vision0 Long1 | Auto 8
Why: плохой деплой неизбежен, важно действовать быстро и без паники
Caps: deploy rollback, incident handling

### 450 — Автогенерация changelog
«Джарвис, сгенерируй CHANGELOG за [версия-диапазон] из commit-сообщений: сгруппируй по типам, отметь breaking changes, найди коммиты без номера задачи.»
Cat: DOCUMENTS | Git
Diff: L2 | Tools: git log, conventional-changelog | Web0 Code1 Files1 Vision0 Long1 | Auto 7
Why: changelog из истории — мгновенная ценность при релизах
Caps: changelog generation, release notes

### 451 — Шаблон pull request
«Джарвис, создай шаблон PR для [репозиторий]: описание изменений, чек-лист тестов, скриншоты, ссылка на задачу, риск-зона для ревьюеров.»
Cat: CODING | GitHub
Diff: L1 | Tools: GitHub templates | Web0 Code1 Files1 Vision0 Long0 | Auto 5
Why: хороший шаблон PR поднимает качество ревью и скорость мержа
Caps: PR template, review onboarding

### 452 — Автоматизированное ревью PR
«Джарвис, проверь PR [номер]: прочитай diff, найди баги, стилевые проблемы, тестовые дыры, риски безопасности. Выдай комментарий по блокам кода с приоритетами.»
Cat: CODING | GitHub
Diff: L3 | Tools: GitHub API | Web0 Code1 Files1 Vision0 Long1 | Auto 8
Why: ИИ-ревью до человека ловит очевидное и экономит время мейнтейнера
Caps: PR review, code diff analysis, review comments

### 453 — Триаж issues
«Джарвис, разбери все открытые issues в [репозиторий]: сгруппируй дубликаты, расставь приоритеты, добавь метки severity/area, назначь ответственных, пометь устаревшие.»
Cat: CODING | GitHub
Diff: L2 | Tools: GitHub API | Web0 Code1 Files1 Vision0 Long1 | Auto 7
Why: завал issues убивает видимость реальных проблем
Caps: issue triage, deduplication, priority scoring

### 454 — CI/CD пайплайн на GitHub Actions
«Джарвис, спроектируй и создай GitHub Actions workflow для [проект]: lint, unit-тесты, сборка, интеграционные тесты, деплой на [окружение] по тегам, кэширование зависимостей, параллельные job'ы.»
Cat: CODING | GitHub
Diff: L4 | Tools: GitHub Actions | Web0 Code1 Files1 Vision0 Long1 | Auto 8
Why: автоматизация качества и доставки — фундамент зрелого репозитория
Caps: CI/CD pipeline, GitHub Actions authoring

### 455 — Безопасное хранение секретов репозитория
«Джарвис, проведи аудит секретов в [репозиторий] (Actions secrets, environments, Dependabot): найди устаревшие, кто их использует, предложи ротацию и запрет на использование в fork-PR.»
Cat: SECURITY | GitHub
Diff: L3 | Tools: GitHub API, gh | Web0 Code1 Files1 Vision0 Long1 | Auto 7
Why: секреты CI — частая точка компрометации при плохой гигиене
Caps: secrets management, CI security audit

### 456 — Планирование релиза и GitHub Releases
«Джарвис, подготовь релиз [версия]: проанализируй изменения с прошлого тега, напиши заметки, создай тег и release, приложи собранные артефакты, продублируй анонс в [канал].»
Cat: CODING | GitHub
Diff: L3 | Tools: gh release | Web0 Code1 Files1 Vision0 Long1 | Auto 8
Why: дисциплинированные релизы упрощают откаты и коммуникацию
Caps: release management, artifact publishing

### 457 — Dependabot: управление уязвимыми зависимостями
«Джарвис, включи и настрой Dependabot для [репозиторий]: расписание, группы обновлений, автоматический merge безопасных версий, политика для major-апдейтов, сводка по открытым alerts.»
Cat: SECURITY | GitHub
Diff: L2 | Tools: Dependabot | Web1 Code1 Files1 Vision0 Long1 | Auto 7
Why: зависимые компоненты — крупнейший вектор атак в open source
Caps: dependency updates, vulnerability alerts

### 458 — CODEOWNERS и зоны ответственности
«Джарвис, создай/обнови CODEOWNERS для [репозиторий] по папкам, проверь, кто обязан ревьюить, и сформируй отчёт о нагрузке на каждого владельца.»
Cat: CODING | GitHub
Diff: L1 | Tools: CODEOWNERS | Web0 Code1 Files1 Vision0 Long0 | Auto 5
Why: явная зона ответственности ускоряет ревью и не теряет изменения
Caps: code ownership, review routing

### 459 — Статистика и метрики репозитория
«Джарвис, собери аналитику по [репозиторий]: время до первого ответа на PR, среднее число ревьюеров, частота мержей, топ авторов, время жизни issue, тренды за [период].»
Cat: ANALYTICS | GitHub
Diff: L2 | Tools: GitHub API | Web0 Code1 Files1 Vision0 Long1 | Auto 7
Why: метрики вскрывают узкие места процесса, а не только код
Caps: repo analytics, PR throughput, issue lifecycle metrics

### 460 — Выбор и настройка merge-стратегии
«Джарвис, оцени текущую мерж-политику [репозиторий] (squash/rebase/merge): изучи историю, предложи оптимальную, настрой обязательные проверки и обнови правила веток.»
Cat: CODING | GitHub
Diff: L3 | Tools: GitHub API | Web0 Code1 Files1 Vision0 Long1 | Auto 7
Why: плохая мерж-политика портит историю и уводит blame
Caps: merge policy, branch rules

### 461 — Анализ профиля разработчика
«Джарвис, проанализируй мой GitHub-профиль и профили команды [никнеймы]: языки, вклад по репозиториям, контрибуции за год, что стоит показать в портфолио, какие проекты переопубликовать.»
Cat: ANALYTICS | GitHub
Diff: L2 | Tools: GitHub API | Web1 Code1 Files0 Vision0 Long1 | Auto 6
Why: профиль — визитная карточка для найма и коллабораций
Caps: profile analytics, contribution insights

### 462 — Поиск кода по GitHub
«Джарвис, найди на GitHub: примеры использования [библиотека/паттерн] на [язык], реализации [алгоритм], код с лицензией MIT, который можно взять за основу для [задача]. Проверь лицензии и популярность.»
Cat: RESEARCH | GitHub
Diff: L2 | Tools: GitHub search | Web1 Code0 Files0 Vision0 Long1 | Auto 6
Why: поиск по чужому коду — быстрый путь к проверенным решениям
Caps: code search, open source discovery

### 463 — Публикация сайта на GitHub Pages
«Джарвис, опубликуй [проект/документацию] на GitHub Pages: настрой ветку, собери статику, добавь домен, включи HTTPS, проверь, что ссылки работают.»
Cat: WEB | GitHub
Diff: L2 | Tools: gh pages | Web0 Code1 Files1 Vision0 Long1 | Auto 7
Why: бесплатный хостинг документации и демо — стандарт для open source
Caps: static site deployment, pages config

### 464 — Wiki и документация репозитория
«Джарвис, создай структуру wiki для [репозиторий]: гайд для новичков, FAQ, архитектурные решения (ADR), глоссарий, инструкции по деплою. Собери материал из README и issues.»
Cat: DOCUMENTS | GitHub
Diff: L2 | Tools: GitHub wiki | Web0 Code1 Files1 Vision0 Long1 | Auto 7
Why: документация рядом с кодом повышает шанс, что её прочитают
Caps: wiki authoring, onboarding docs, ADR

### 465 — Webhooks и интеграции
«Джарвис, настрой webhooks для [репозиторий]: события push/PR/issues в [Slack/телеграм/CRM], с фильтрами по веткам и секретом. Проверь доставку и обработку ошибок.»
Cat: CODING | GitHub
Diff: L3 | Tools: GitHub webhooks | Web0 Code1 Files1 Vision0 Long0 | Auto 7
Why: события репозитория должны сами находить людей, а не наоборот
Caps: webhook config, event streaming

### 466 — Политики организации GitHub
«Джарвис, спроектируй политики для [организация]: кто создаёт репозитории, дефолтные права, обязательные ревью, защита main, SAML/2FA, правила для внешних контрибьюторов.»
Cat: SECURITY | GitHub
Diff: L4 | Tools: GitHub org settings | Web0 Code1 Files1 Vision0 Long1 | Auto 7
Why: слабые политики организации = массовая утечка при одном скомпрометированном аккаунте
Caps: org policy, access governance, SSO enforcement

### 467 — Миграция репозитория с другого хостинга
«Джарвис, перенеси [репозиторий] с [GitLab/Bitbucket/локальный] на GitHub: сохрани историю, ветки, теги, issues, настройки, перепиши ссылки в коде и документации, проверь CI.»
Cat: CODING | GitHub
Diff: L4 | Tools: git, gh | Web0 Code1 Files1 Vision0 Long1 | Auto 8
Why: миграция с потерей истории или issues разрушает контекст команды
Caps: repo migration, history preservation

### 468 — Мониторинг очереди PR и блокеров
«Джарвис, каждое утро просматривай PR в [репозиторий]: какие ждут ревью больше [дней], кто автор, что блокирует, пришли сводку в [канал] и напомни ревьюерам.»
Cat: CODING | GitHub
Diff: L2 | Tools: GitHub API | Web0 Code1 Files0 Vision0 Long1 | Auto 7
Why: застрявшие PR — скрытая потеря денег и мотивации
Caps: PR queue monitoring, reviewer reminders

### 469 — Статус CI по веткам
«Джарвис, покажи статус CI для всех открытых веток [репозиторий]: зелёные, падающие, сколько раз перезапускались, где тесты флакают. Выдай рейтинг самых проблемных веток.»
Cat: CODING | GitHub
Diff: L1 | Tools: GitHub API, gh | Web0 Code1 Files0 Vision0 Long0 | Auto 6
Why: красный CI, который никто не чинит, — первый признак разваливающегося процесса
Caps: CI status tracking, flaky test detection

### 470 — Автоматические метки и роутинг issues
«Джарвис, настрой авто-метки для issues: по шаблону заголовка, по упомянутым файлам, по тексту (bug/feature/question). Организуй доску и правила переноса по статусам.»
Cat: CODING | GitHub
Diff: L3 | Tools: GitHub Actions, projects | Web0 Code1 Files1 Vision0 Long1 | Auto 7
Why: самоорганизующиеся метки экономят часы ручного триажа еженедельно
Caps: issue labeling, board automation

### 471 — Смарт-поиск по проекту
«Джарвис, найди в [проект] все места, где используется [функция/переменная/константа]: определения, вызовы, тесты, документацию. Покажи граф зависимостей и рискованные использования.»
Cat: CODING | IDE
Diff: L1 | Tools: IDE search, ripgrep | Web0 Code1 Files1 Vision0 Long0 | Auto 6
Why: глобальный поиск — базовая операция, но с графом она превращается в анализ
Caps: project search, usage graph

### 472 — Безопасное переименование по всему коду
«Джарвис, переименуй [класс/функцию/файл] в [новое имя] во всём проекте: обнови все ссылки, тесты, документацию, конфиги. Покажи diff до применения и проверь сборку.»
Cat: CODING | IDE
Diff: L2 | Tools: IDE refactor | Web0 Code1 Files1 Vision0 Long1 | Auto 8
Why: ручное переименование — источник незаметных багов
Caps: safe rename, cross-file refactoring

### 473 — Автодополнение и генерация кода в стиле проекта
«Джарвис, включи режим автодополнения для [язык] с учётом нашего кодстайла: подсказывай имена, сигнатуры, паттерны из соседних файлов. Придумай 5 предложений для текущего места в коде.»
Cat: CODING | IDE
Diff: L1 | Tools: LSP, AI completion | Web0 Code1 Files1 Vision0 Long0 | Auto 6
Why: дополнение, знающее конвенции проекта, — лучший ускоритель набора кода
Caps: code completion, style-aware suggestions

### 474 — Отладка через breakpoints и watch
«Джарвис, настрой отладку для [скрипт/тест]: поставь breakpoints в проблемных местах, watch на [переменные], прогони и объясни, где состояние расходится с ожиданием.»
Cat: CODING | IDE
Diff: L2 | Tools: debugger | Web0 Code1 Files1 Vision0 Long0 | Auto 7
Why: интерактивная отладка быстрее print-диагностики при сложных состояниях
Caps: debugger session, breakpoint planning, state inspection

### 475 — Профилирование из IDE
«Джарвис, запусти профайлер на [функция/сценарий]: найди горячие точки, аллокации, блокировки. Покажи top-10 мест по времени и памяти с контекстом кода.»
Cat: PERFORMANCE | IDE
Diff: L3 | Tools: profiler | Web0 Code1 Files1 Vision0 Long1 | Auto 7
Why: измерения заменяют догадки о том, что тормозит
Caps: code profiling, hotspot detection, memory analysis

### 476 — Генерация тестов по коду
«Джарвис, посмотри на [модуль/функцию] и сгенерируй unit-тесты: happy path, граничные случаи, ошибки, пустые входы. Покрой ветки, которые видишь, и добавь в проект с прогоном.»
Cat: CODING | IDE
Diff: L3 | Tools: test framework | Web0 Code1 Files1 Vision0 Long1 | Auto 8
Why: авто-генерация тестов закрывает базу, человек добавляет смысловые сценарии
Caps: test generation, branch coverage

### 477 — Навигация по коду без мыши
«Джарвис, покажи мне быстрый способ пройтись по коду: перейди к определению [символ], найди все вызовы, покажи иерархию классов, прыгни к месту последнего изменения в файле.»
Cat: CODING | IDE
Diff: L0 | Tools: LSP, IDE navigation | Web0 Code1 Files1 Vision0 Long0 | Auto 5
Why: скорость навигации прямо влияет на скорость чтения чужого кода
Caps: symbol navigation, call hierarchy

### 478 — Документация из кода
«Джарвис, сгенерируй документацию по [модуль]: docstrings, примеры использования, описание параметров, схему взаимосвязей. Оформи в README-секцию или докер-файл формата [формат].»
Cat: DOCUMENTS | IDE
Diff: L2 | Tools: doc generators | Web0 Code1 Files1 Vision0 Long1 | Auto 7
Why: документация, живущая в коде, не устаревает так быстро
Caps: docstring generation, API docs

### 479 — Линтинг и автофикс при сохранении
«Джарвис, настрой линтер и форматтер для [проект]: правила по [язык], автофикс при сохранении, ignore-файлы, единый стиль для команды, прекоммит-проверка.»
Cat: CODING | IDE
Diff: L2 | Tools: linters, formatters | Web0 Code1 Files1 Vision0 Long0 | Auto 7
Why: единый стиль убирает войны форматирования из ревью
Caps: lint config, auto-format, style enforcement

### 480 — Персональные сниппеты
«Джарвис, создай сниппеты для [часто повторяемых блоков] на [язык]: с плейсхолдерами, табами-переходами, описанием. Добавь в IDE и покажи, как вызывать.»
Cat: CODING | IDE
Diff: L1 | Tools: IDE snippets | Web0 Code1 Files1 Vision0 Long0 | Auto 5
Why: сниппеты превращают повторяющийся код в два нажатия
Caps: snippet authoring, template shortcuts

### 481 — Совместная работа: живой шаринг
«Джарвис, организуй сессию совместной работы над [файл/проект]: пригласи [участники], синхронизируй терминалы, выдели участки для каждого, следи за конфликтами в реальном времени.»
Cat: CODING | IDE
Diff: L3 | Tools: live share | Web0 Code1 Files1 Vision0 Long0 | Auto 7
Why: парное программирование удалённо эффективно только с правильным инструментом
Caps: live collaboration, pair programming

### 482 — Git-панель в IDE
«Джарвис, покажи в IDE состояние репозитория: незакоммиченные изменения, конфликты, кто редактирует тот же файл. Помоги закоммитить осмысленными порциями, а не одним коммитом.»
Cat: CODING | IDE
Diff: L1 | Tools: IDE git panel | Web0 Code1 Files1 Vision0 Long0 | Auto 6
Why: визуальная git-панель снижает ошибки стейджинга
Caps: staging review, visual git ops

### 483 — Подбор и установка расширений
«Джарвис, посмотри на мой проект [стек] и предложи набор расширений IDE: что критично, что полезно, что избыточно. Установи рекомендованные и настрой общие настройки.»
Cat: CODING | IDE
Diff: L1 | Tools: IDE extensions | Web1 Code1 Files1 Vision0 Long0 | Auto 6
Why: правильный набор расширений = меньше рутины, больше фокуса
Caps: extension curation, IDE setup

### 484 — Сравнение версий файла
«Джарвис, сравни [файл] между коммитами [A] и [B]: покажи семантические изменения (не переносы строк), объясни, что изменилось по смыслу, и оцени риск для [функция].»
Cat: CODING | IDE
Diff: L1 | Tools: git diff | Web0 Code1 Files1 Vision0 Long0 | Auto 6
Why: diff с объяснением смысла читается в разы быстрее
Caps: semantic diff, change explanation

### 485 — Настройка окружения разработки с нуля
«Джарвис, настрой среду для разработки на [стек] на этой машине: версии языков, менеджер пакетов, переменные окружения, форматтеры, линтеры, дебаггер. Проверь всё тестовым проектом.»
Cat: CODING | IDE
Diff: L3 | Tools: version managers, dotfiles | Web0 Code1 Files1 Vision0 Long0 | Auto 8
Why: воспроизводимое окружение убирает «работает только у меня»
Caps: dev environment setup, toolchain bootstrap

### 486 — Сложный конвейер терминала
«Джарвис, собери конвейер: возьми [источник], отфильтруй по [условие], преобразуй через [утилита], агрегируй и выведи топ-[N] с пояснением каждого шага. Покажи промежуточные этапы.»
Cat: TERMINAL | Pipelines
Diff: L2 | Tools: awk, sed, sort, jq | Web0 Code1 Files1 Vision0 Long0 | Auto 7
Why: один конвейер заменяет десятки ручных операций с данными
Caps: pipeline construction, text processing

### 487 — Мониторинг логов в реальном времени
«Джарвис, следи за [лог-файл] в реальном времени: подсвечивай ошибки, фильтруй шум, считай частоту событий, аварийно оповести при появлении [паттерн].»
Cat: TERMINAL | Monitoring
Diff: L2 | Tools: tail, grep, journalctl | Web0 Code1 Files1 Vision0 Long0 | Auto 8
Why: наблюдение за логами — первая линия диагностики инцидентов
Caps: log streaming, pattern alerting, error correlation

### 488 — Управление процессами из терминала
«Джарвис, разберись с процессами: покажи, кто ест CPU/память, найди процессы по [имя/порту], объясни дерево родитель-потомок, аккуратно заверши зависший [процесс] с сохранением данных.»
Cat: TERMINAL | Processes
Diff: L2 | Tools: ps, top, kill, lsof | Web0 Code1 Files1 Vision0 Long0 | Auto 6
Why: управление процессами — частая задача админа и разработчика
Caps: process inspection, resource triage, graceful termination

### 489 — Псевдонимы и функции шелла
«Джарвис, собери мои самые частые команды из истории и создай для них псевдонимы и функции в [конфиг]: с автодополнением, описаниями и секциями.»
Cat: TERMINAL | Productivity
Diff: L1 | Tools: shell config, history | Web0 Code1 Files1 Vision0 Long0 | Auto 6
Why: экономия набранных символов окупается каждый день
Caps: alias curation, shell function authoring

### 490 — Обработка текста: awk/sed на практике
«Джарвис, обработай [файл]: вытащи поля [номера], переведи формат [из->в], замени [паттерн] с учётом регистра, проверь результат на выборке и примени только после подтверждения.»
Cat: TERMINAL | Text
Diff: L3 | Tools: awk, sed, cut | Web0 Code1 Files1 Vision0 Long0 | Auto 6
Why: текстовая обработка в терминале работает везде и без зависимостей
Caps: text transformation, format conversion, regex authoring

### 491 — Параллельные задачи в терминале
«Джарвис, запусти [задачи: конвертация 200 файлов, скачивание, сборка] параллельно с ограничением [N] потоков, собери результаты, покажи прогресс по каждой и сведи отчёт об ошибках.»
Cat: TERMINAL | Automation
Diff: L3 | Tools: xargs, parallel | Web0 Code1 Files1 Vision0 Long1 | Auto 8
Why: параллельность даёт выигрыш в разы на пакетных операциях
Caps: parallel execution, batch orchestration

### 492 — Диагностика сети из терминала
«Джарвис, проверь сеть до [хост]: маршрут, потери пакетов, DNS, открытые порты, скорость. Собери отчёт и объясни, где узкое место.»
Cat: TERMINAL | Network
Diff: L2 | Tools: ping, traceroute, dig, curl | Web0 Code1 Files0 Vision0 Long0 | Auto 6
Why: сетевая диагностика с терминала — первый шаг при «ничего не работает»
Caps: network diagnostics, DNS checks, latency analysis

### 493 — Терминальный мультиплексор
«Джарвис, настрой tmux/creen для работы: сессии по задачам, окна, синхронный ввод, восстановление после отключения. Покажи раскладку и горячие клавиши для моей схемы.»
Cat: TERMINAL | Productivity
Diff: L3 | Tools: tmux, screen | Web0 Code1 Files1 Vision0 Long0 | Auto 6
Why: мультиплексор сохраняет сессии при обрывах SSH и структурирует работу
Caps: session multiplexing, resilient shells

### 494 — Безопасность шелла
«Джарвис, аудит моего терминального окружения: права на конфиги, токены в истории, утечки через environment, скрытые алиасы, команды из PATH с подменой. Исправь найденное.»
Cat: SECURITY | Terminal
Diff: L3 | Tools: history, env, PATH audit | Web0 Code1 Files1 Vision0 Long0 | Auto 7
Why: шелл — самая доверенная среда, и её компрометация незаметна
Caps: shell audit, token hygiene, PATH integrity

### 495 — Автодополнение терминала
«Джарвис, настрой автодополнение и историю для [шелл]: по командам и флагам, умный поиск по истории, предложения на основе частоты. Демонстрация на [команда].»
Cat: TERMINAL | Productivity
Diff: L2 | Tools: fzf, shell completion | Web0 Code1 Files1 Vision0 Long0 | Auto 6
Why: умная история и дополнение ускоряют любую терминальную работу
Caps: completion config, fuzzy history search

### 496 — Анализ истории команд
«Джарвис, проанализируй мою историю терминала за [период]: топ-20 команд, сколько времени на рутину, какие команды можно автоматизировать, где я делаю ошибки (опечатки, повторные попытки).»
Cat: ANALYTICS | Terminal
Diff: L2 | Tools: history, awk | Web0 Code1 Files1 Vision0 Long1 | Auto 7
Why: история команд — бесплатный источник данных о собственных привычках
Caps: usage analytics, habit mining, automation candidates

### 497 — Файловый менеджер в терминале
«Джарвис, организуй [папка]: покажи дерево с размерами, найди дубликаты и мусор, предложи структуру папок, выполни переименование по правилу [правило] после моего подтверждения.»
Cat: TERMINAL | Files
Diff: L2 | Tools: find, du, fdupes | Web0 Code1 Files1 Vision0 Long0 | Auto 6
Why: порядок в файлах — базовая гигиена, избавляющая от потерь
Caps: file organization, duplicate detection, tree analysis

### 498 — Генератор bash-скриптов
«Джарвис, напиши bash-скрипт для [задача]: с аргументами, проверками ошибок, логированием, обработкой Ctrl+C и понятными сообщениями. Проверь синтаксис и прогони в dry-run.»
Cat: CODING | Terminal
Diff: L3 | Tools: bash, shellcheck | Web0 Code1 Files1 Vision0 Long0 | Auto 8
Why: надёжные скрипты заменяют разовые ручные последовательности
Caps: script generation, error handling, dry-run validation

### 499 — Управление удалённым сервером
«Джарвис, подключись к [сервер]: проверь нагрузку, обнови пакеты по списку, посмотри логи [сервис], выполни диагностику диска и памяти. Всё с подтверждением перед изменениями.»
Cat: TERMINAL | Remote
Diff: L4 | Tools: ssh | Web0 Code1 Files1 Vision0 Long1 | Auto 7
Why: удалённая работа через SSH — ядро администрирования без GUI
Caps: remote ops, ssh session, server health checks

### 500 — Терминальный дашборд
«Джарвис, собери персональный дашборд в терминале: системные метрики, погода, курс [валюты], задачи из [todo], дедлайны, новости по [тема]. Обновляй раз в [интервал].»
Cat: TERMINAL | Dashboard
Diff: L3 | Tools: htop, curl, jq | Web1 Code0 Files1 Vision0 Long1 | Auto 8
Why: единый экран вместо десятка вкладок — лучший утренний ритуал
Caps: dashboard composition, metric aggregation, scheduled refresh
---

### 501 — Создание документа по техническому заданию
«Джарвис, напиши документ [тип: статья, отчёт, инструкция] на тему [тема] объёмом [N] страниц для аудитории [читатели]. Составь структуру, согласуй со мной и затем напиши полностью.»
Cat: DOCUMENTS | Authoring
Diff: L2 | Tools: document editor | Web1 Code0 Files1 Vision0 Long1 | Auto 7
Why: согласованная структура до написания экономит переписывание
Caps: document drafting, audience adaptation, outline planning

### 502 — Структурирование документа
«Джарвис, разбей [документ] на логическую структуру: разделы, подразделы, аннотации. Проверь, что каждый раздел отвечает на один вопрос, и предложи перестановку для лучшего потока.»
Cat: DOCUMENTS | Authoring
Diff: L1 | Tools: outline tools | Web0 Code1 Files1 Vision0 Long0 | Auto 6
Why: хорошая структура — 80% качества документа
Caps: document outlining, logical flow analysis

### 503 — Единый стиль и форматирование
«Джарвис, приведи [документ] к единому стилю: шрифты, отступы, заголовки, интервалы, нумерация списков, формат дат и чисел. Сверь с [корпоративный шаблон].»
Cat: DOCUMENTS | Formatting
Diff: L1 | Tools: style tools | Web0 Code1 Files1 Vision0 Long0 | Auto 6
Why: единый стиль делает документы профессиональными и читаемыми
Caps: style normalization, template compliance

### 504 — Оглавление и навигация
«Джарвис, создай в [документ] оглавление, список таблиц и рисунков, добавь закладки и перекрёстные ссылки. Обнови их перед финальной версией.»
Cat: DOCUMENTS | Formatting
Diff: L1 | Tools: TOC tools | Web0 Code1 Files1 Vision0 Long0 | Auto 5
Why: навигация в длинном документе экономит минуты каждому читателю
Caps: table of contents, cross-references, bookmarks

### 505 — Сноски, ссылки и библиография
«Джарвис, оформи в [документ] сноски по стандарту [ГОСТ/APA/MLA], вставь цитаты из [источники], проверь, что каждая ссылка ведёт на существующий источник, и построй библиографию.»
Cat: DOCUMENTS | Authoring
Diff: L2 | Tools: citation tools | Web1 Code1 Files1 Vision0 Long1 | Auto 7
Why: корректные цитаты — обязательное требование академических и деловых документов
Caps: citation management, bibliography generation, source verification

### 506 — Версионирование документов
«Джарвис, настрой управление версиями для [папка документов]: история изменений, понятные имена файлов, отметки о статусе (черновик/согласован/финал), журнал изменений.»
Cat: DOCUMENTS | Management
Diff: L1 | Tools: file naming, git | Web0 Code1 Files1 Vision0 Long0 | Auto 6
Why: хаос версий документов — источник дорогих ошибок в бизнесе
Caps: document versioning, change log, naming conventions

### 507 — Слияние нескольких документов
«Джарвис, объедини [документы] в один: согласуй структуру, устрани дублирующиеся разделы, выровняй стиль, построй общее оглавление и пронумеруй всё заново.»
Cat: DOCUMENTS | Authoring
Diff: L2 | Tools: merge tools | Web0 Code1 Files1 Vision0 Long1 | Auto 7
Why: слияние документов от разных авторов требует умного дедублицирования
Caps: document merge, duplication removal

### 508 — Сравнение двух версий документа
«Джарвис, сравни [версия А] и [версия Б]: покажи смысловые изменения (добавления, удаления, переформулировки), найди, что удалили случайно, и составь краткую сводку различий.»
Cat: DOCUMENTS | Analysis
Diff: L1 | Tools: diff tools | Web0 Code1 Files1 Vision0 Long0 | Auto 6
Why: понимание, что изменилось в договоре, защищает от юридических сюрпризов
Caps: semantic document diff, change summary

### 509 — Конвертация форматов документов
«Джарвис, сконвертируй [файл] из [формат] в [формат] без потери форматирования: таблиц, встроенных объектов, шрифтов. Проверь результат на ключевых страницах.»
Cat: DOCUMENTS | Conversion
Diff: L1 | Tools: pandoc, converters | Web0 Code1 Files1 Vision0 Long0 | Auto 6
Why: конвертация с потерей данных — частый источник головной боли
Caps: format conversion, fidelity checking

### 510 — Предпечатная подготовка
«Джарвис, подготовь [документ] к печати: проверь поля, обрезные размеры, разрешение изображений, цвета (CMYK/RGB), шрифты, номера страниц. Выдай список того, что поправить.»
Cat: DOCUMENTS | Publishing
Diff: L2 | Tools: print prep tools | Web0 Code1 Files1 Vision0 Long0 | Auto 6
Why: типографские ошибки видны только после печати и стоят дорого
Caps: print preparation, color checks, bleed validation

### 511 — PDF: слияние файлов
«Джарвис, объедини [список PDF] в один файл: задай порядок, вставь разделители, обнови номера страниц и создай оглавление.»
Cat: DOCUMENTS | PDF
Diff: L1 | Tools: PDF tools | Web0 Code1 Files1 Vision0 Long0 | Auto 5
Why: сборка PDF — рутинная задача офисной работы
Caps: pdf merge, page ordering

### 512 — PDF: разбиение на части
«Джарвис, раздели [PDF] на части: по диапазонам страниц [диапазоны], по разделам из оглавления, или вытащи только [страницы]. Дай понятные имена файлам.»
Cat: DOCUMENTS | PDF
Diff: L1 | Tools: PDF tools | Web0 Code1 Files1 Vision0 Long0 | Auto 5
Why: разбиение больших PDF нужно для отправки и обработки частей
Caps: pdf split, page extraction

### 513 — PDF: извлечение текста
«Джарвис, извлеки текст из [PDF] с сохранением структуры: заголовки, списки, таблицы, колонки. Отдай в [формат: txt/markdown] и отметь места с повреждённым текстом.»
Cat: DOCUMENTS | PDF
Diff: L1 | Tools: pdftotext, pdfplumber | Web0 Code1 Files1 Vision0 Long0 | Auto 6
Why: текстовая версия PDF открывает его для анализа и редактирования
Caps: text extraction, layout preservation

### 514 — PDF: извлечение таблиц
«Джарвис, вытащи все таблицы из [PDF] в Excel/CSV: восстанови границы ячеек, объединённые ячейки, заголовки. Покажи, где таблица повреждена или неоднозначна.»
Cat: DOCUMENTS | PDF
Diff: L2 | Tools: tabula, pdfplumber | Web0 Code1 Files1 Vision0 Long1 | Auto 7
Why: таблицы в PDF — самая ценная и самая трудная для извлечения часть
Caps: table extraction, structured data recovery

### 515 — PDF: распознавание сканов (OCR)
«Джарвис, распознай текст в [скан PDF] через OCR: определи язык, обработай повороты и шум, сохрани текстовый слой. Проверь качество на сложных страницах.»
Cat: DOCUMENTS | OCR
Diff: L2 | Tools: tesseract, OCR | Web0 Code1 Files1 Vision0 Long1 | Auto 7
Why: OCR превращает недоступные сканы в редактируемые и искомые документы
Caps: ocr, scan digitization, language detection

### 516 — PDF: заполнение форм
«Джарвис, заполни форму в [PDF] данными из [источник]: поля, чекбоксы, подписи. Проверь обязательные поля и сохрани заполненную копию без изменения шаблона.»
Cat: DOCUMENTS | PDF
Diff: L2 | Tools: pdftk, form tools | Web0 Code1 Files1 Vision0 Long0 | Auto 6
Why: ручное заполнение форм отнимает часы при массовых операциях
Caps: form filling, template preservation

### 517 — PDF: сжатие
«Джарвис, сожми [PDF] до [целевой размер]: оптимизируй изображения, шрифты, метаданные без видимой потери качества. Покажи сравнение размеров и качества.»
Cat: DOCUMENTS | PDF
Diff: L1 | Tools: ghostscript | Web0 Code1 Files1 Vision0 Long0 | Auto 5
Why: тяжёлые PDF блокируют отправку по почте и мессенджерам
Caps: pdf compression, size optimization

### 518 — PDF: защита паролем и правами
«Джарвис, защити [PDF] паролем для открытия и ограничь права: печать, копирование, редактирование. Используй разные пароли для владельца и читателя, объясни, как передать доступ.»
Cat: SECURITY | PDF
Diff: L2 | Tools: qpdf, ghostscript | Web0 Code1 Files1 Vision0 Long0 | Auto 6
Why: незащищённые документы расходятся по почте без контроля
Caps: pdf encryption, permission control

### 519 — PDF: электронная подпись
«Джарвис, подпиши [PDF] электронной подписью [сертификат]: вставь подпись и отметку времени, проверь целостность после подписания, объясни получателю, как проверить.»
Cat: SECURITY | PDF
Diff: L3 | Tools: openssl, signing tools | Web0 Code1 Files1 Vision0 Long0 | Auto 6
Why: юридически значимая подпись без печати и сканирования
Caps: digital signature, certificate handling

### 520 — PDF: аннотации и комментарии
«Джарвис, добавь в [PDF] аннотации: комментарии, выделения, фигуры, стикеры в местах [места]. Сгруппируй их по темам и выгрузи список для обсуждения.»
Cat: DOCUMENTS | PDF
Diff: L1 | Tools: annotation tools | Web0 Code1 Files1 Vision0 Long0 | Auto 5
Why: рецензирование на месте документа эффективнее отдельных писем
Caps: pdf annotations, review markup

### 521 — PDF → Word/Excel конвертация
«Джарвис, конвертируй [PDF] в редактируемый [Word/Excel]: сохрани стили, таблицы, изображения, разметку. Отметь места, где конвертация ненадёжна.»
Cat: DOCUMENTS | PDF
Diff: L2 | Tools: converters | Web0 Code1 Files1 Vision0 Long1 | Auto 6
Why: конвертация PDF в редактируемый формат — постоянная офисная потребность
Caps: pdf to doc conversion, layout recovery

### 522 — PDF: генерация из Word/Excel/HTML
«Джарвис, собери PDF из [исходники]: настрой размер страницы, поля, колонтитулы, шрифты, разрывы разделов. Проверь рендер на [страницах].»
Cat: DOCUMENTS | PDF
Diff: L1 | Tools: pandoc, print-to-pdf | Web0 Code1 Files1 Vision0 Long0 | Auto 6
Why: контроль над итоговым PDF-макетом важен для публикации
Caps: pdf generation, layout control

### 523 — PDF: извлечение изображений
«Джарвис, извлеки изображения из [PDF]: сохрани в исходном разрешении и формате, сгруппируй по размерам, определи, какие из них дублируются.»
Cat: DOCUMENTS | PDF
Diff: L1 | Tools: pdfimages | Web0 Code1 Files1 Vision0 Long0 | Auto 5
Why: изображения из PDF нужны для переиспользования в других материалах
Caps: image extraction, deduplication

### 524 — PDF: анализ структуры
«Джарвис, проанализируй структуру [PDF]: число страниц, заголовки, вложенные разделы, шрифты, метаданные, ссылки. Построй карту документа и найди аномалии.»
Cat: DOCUMENTS | PDF
Diff: L2 | Tools: pdfinfo, parsers | Web0 Code1 Files1 Vision0 Long1 | Auto 7
Why: понимание структуры PDF нужно перед автоматизацией работы с ним
Caps: structure analysis, metadata extraction, anomaly detection

### 525 — PDF: восстановление повреждённого файла
«Джарвис, [PDF] не открывается. Попробуй восстановить: определи повреждения, вытащи уцелевшие страницы, пересобери файл. Объясни, что потеряно.»
Cat: DOCUMENTS | PDF
Diff: L4 | Tools: qpdf, repair tools | Web0 Code1 Files1 Vision0 Long0 | Auto 7
Why: повреждённый PDF часто содержит единственную копию важных данных
Caps: pdf repair, data salvage

### 526 — PDF: чистка метаданных
«Джарвис, удали из [PDF] метаданные: имя автора, путь создания, историю программ. Оставь только нужное и проверь, что утечек больше нет.»
Cat: SECURITY | PDF
Diff: L1 | Tools: exiftool | Web0 Code1 Files1 Vision0 Long0 | Auto 5
Why: метаданные незаметно раскрывают авторов и внутренние пути
Caps: metadata sanitization, privacy hardening

### 527 — PDF: рецензирование с пометками
«Джарвис, прочитай [PDF-договор] и сделай рецензию: пометь неоднозначные формулировки, риски, недостающие пункты, предложи правки. Оформи комментарии прямо в файле.»
Cat: LEGAL | PDF
Diff: L3 | Tools: annotation tools | Web1 Code1 Files1 Vision0 Long1 | Auto 8
Why: юридическая экспертиза договора — задача, где детали решают всё
Caps: contract review, risk flagging, redlining

### 528 — PDF: визуальное сравнение версий
«Джарвис, сравни два PDF [A] и [B] постранично: покажи различающиеся страницы с подсветкой изменённых областей, игнорируя сдвиги вёрстки.»
Cat: DOCUMENTS | PDF
Diff: L2 | Tools: diff-pdf, imagemagick | Web0 Code1 Files1 Vision0 Long1 | Auto 7
Why: визуальный diff ловит изменения, которые текст-сравнение пропускает
Caps: visual pdf diff, region highlighting

### 529 — PDF: генерация отчёта из данных
«Джарвис, сгенерируй PDF-отчёт из [данные]: титульный лист, сводные метрики, графики, таблицы, выводы. Оформи по шаблону [шаблон] и разложи по секциям.»
Cat: DOCUMENTS | PDF
Diff: L3 | Tools: report generators | Web0 Code1 Files1 Vision0 Long1 | Auto 8
Why: автоматические отчёты освобождают часы ручной вёрстки
Caps: automated reporting, data visualization in PDF

### 530 — PDF: пакетная обработка папки
«Джарвис, обработай все PDF в [папка]: [операция: сжатие, OCR, водяной знак, переименование по содержимому]. Сделай это в несколько потоков и пришли отчёт об ошибках.»
Cat: DOCUMENTS | PDF
Diff: L3 | Tools: batch tools | Web0 Code1 Files1 Vision0 Long1 | Auto 8
Why: пакетная обработка — там, где автоматизация окупается мгновенно
Caps: batch pdf processing, bulk renaming

### 531 — Оформление по корпоративному шаблону
«Джарвис, оформи [документ] по корпоративному шаблону [шаблон]: титульный лист, шрифты, цвета, логотип, колонтитулы, поля. Проверь соответствие по чек-листу.»
Cat: DOCUMENTS | Word
Diff: L1 | Tools: Word | Web0 Code1 Files1 Vision0 Long0 | Auto 5
Why: корпоративный стиль — лицо компании в каждом исходящем документе
Caps: corporate template, brand compliance

### 532 — Автоматическое оглавление в Word
«Джарвис, создай в [документ Word] автоматическое оглавление на основе стилей, с номерами страниц и обновлением полей перед сохранением.»
Cat: DOCUMENTS | Word
Diff: L1 | Tools: Word styles | Web0 Code1 Files1 Vision0 Long0 | Auto 5
Why: авто-оглавление всегда актуально и не требует ручной правки
Caps: automatic TOC, style-based navigation

### 533 — Колонтитулы и нумерация страниц
«Джарвис, настрой в [документ] колонтитулы: разные для первой страницы и чётных/нечётных, нумерация с [стартовой] страницы, разделы с отдельной нумерацией.»
Cat: DOCUMENTS | Word
Diff: L1 | Tools: Word headers | Web0 Code1 Files1 Vision0 Long0 | Auto 5
Why: правильные колонтитулы — обязательная часть официальных документов
Caps: header/footer config, section numbering

### 534 — Единые стили заголовков
«Джарвис, приведи все заголовки [документа] к стилям «Заголовок 1–4»: проверь иерархию, выровняй нумерацию, устрани ручное форматирование.»
Cat: DOCUMENTS | Word
Diff: L1 | Tools: Word styles | Web0 Code1 Files1 Vision0 Long0 | Auto 5
Why: стили вместо ручного форматирования делают документ управляемым
Caps: heading hierarchy, style cleanup

### 535 — Таблицы в Word
«Джарвис, создай и оформи таблицу [данные] в [документ]: объединение ячеек, повтор заголовка на страницах, ширины колонок, стиль оформления.»
Cat: DOCUMENTS | Word
Diff: L1 | Tools: Word tables | Web0 Code1 Files1 Vision0 Long0 | Auto 5
Why: нечитаемые таблицы сводят на нет смысл данных
Caps: table design, layout automation

### 536 — Шаблон документа для отдела
«Джарвис, создай многоразовый шаблон [тип документа] для [отдел]: поля-плейсхолдеры, готовые разделы, чек-лист заполнения, пример заполненной версии.»
Cat: DOCUMENTS | Word
Diff: L2 | Tools: Word templates | Web0 Code1 Files1 Vision0 Long0 | Auto 6
Why: шаблоны стандартизируют рутину и снижают число ошибок заполнения
Caps: template design, placeholders, reusable forms

### 537 — Автоматизация Word макросами
«Джарвис, напиши макрос для [повторяющаяся операция в Word] и привяжи к кнопке: [описание]. Протестируй на копии и покажи, как отключить при проблемах.»
Cat: CODING | Word
Diff: L3 | Tools: VBA | Web0 Code1 Files1 Vision0 Long0 | Auto 7
Why: один макрос заменяет сотни повторяющихся ручных действий
Caps: vba macros, office automation

### 538 — Слияние документа с данными (mail merge)
«Джарвис, выполни слияние [шаблон документа] с [база получателей]: создай персональные копии, проверь имена и поля на опечатки, собери в один файл.»
Cat: DOCUMENTS | Word
Diff: L2 | Tools: mail merge | Web0 Code1 Files1 Vision0 Long0 | Auto 7
Why: массовые персональные документы без ручного копирования
Caps: mail merge, personalized documents

### 539 — Динамические поля документа
«Джарвис, добавь в [документ] динамические поля: дата, имя файла, номер версии, счётчик страниц, данные из [источник]. Проверь обновление при открытии.»
Cat: DOCUMENTS | Word
Diff: L1 | Tools: Word fields | Web0 Code1 Files1 Vision0 Long0 | Auto 5
Why: динамические поля исключают устаревшие даты и номера в документах
Caps: dynamic fields, auto-updating content

### 540 — Рецензирование и комментарии
«Джарвис, проверь [документ] как рецензент: оставь комментарии по структуре, логике, фактам, стилю. Сгруппируй замечания по важности и предложи исправления.»
Cat: DOCUMENTS | Word
Diff: L2 | Tools: comments | Web0 Code1 Files1 Vision0 Long1 | Auto 7
Why: структурная рецензия полезнее мелких правок орфографии
Caps: document review, structured feedback

### 541 — Отслеживание изменений
«Джарвис, включи отслеживание изменений в [документ], внеси мои правки [список], покажи итоговый дифф и прими/отклони изменения по [критерии].»
Cat: DOCUMENTS | Word
Diff: L1 | Tools: track changes | Web0 Code1 Files1 Vision0 Long0 | Auto 6
Why: прозрачность правок обязательна при коллективной работе над документами
Caps: track changes, change acceptance workflow

### 542 — Диаграммы и графики в документе
«Джарвис, добавь в [документ] диаграммы по [данные]: выбери подходящие типы, подпиши оси, добавь пояснения. Оформи в едином стиле.»
Cat: DOCUMENTS | Word
Diff: L1 | Tools: charts | Web0 Code1 Files1 Vision0 Long0 | Auto 6
Why: правильно выбранный график передаёт данные убедительнее текста
Caps: chart insertion, data storytelling

### 543 — Водяные знаки
«Джарвис, добавь в [документ] водяной знак [текст/логотип]: для каждого раздела свой (черновик/конфиденциально/финал), с нужной прозрачностью и поворотом.»
Cat: DOCUMENTS | Word
Diff: L1 | Tools: watermarks | Web0 Code1 Files1 Vision0 Long0 | Auto 5
Why: водяные знаки защищают статус документа от недоразумений
Caps: watermarking, status labeling

### 544 — Разделы и разрывы страниц
«Джарвис, разбей [документ] на разделы: разные поля, ориентация, нумерация, колонтитулы для [части]. Проверь переходы между разделами.»
Cat: DOCUMENTS | Word
Diff: L2 | Tools: Word sections | Web0 Code1 Files1 Vision0 Long0 | Auto 5
Why: разделы дают гибкость вёрстки, которой нет в одном сплошном документе
Caps: section breaks, mixed orientation

### 545 — Проверка орфографии и стиля
«Джарвис, проверь [документ] на орфографию, грамматику и стиль: канцеляризмы, пассивный залог, длинные предложения, повторяющиеся слова. Предложи правки с объяснением.»
Cat: DOCUMENTS | Writing
Diff: L1 | Tools: language tools | Web0 Code1 Files1 Vision0 Long1 | Auto 7
Why: стилистическая чистка поднимает восприятие документа профессионально
Caps: proofreading, style editing, readability scoring

### 546 — Сноски и библиография по ГОСТ
«Джарвис, оформи в [документе] сноски и список литературы по ГОСТ Р 7.0.100: проверь все ссылки, добавь недостающие издания, выровняй формат.»
Cat: DOCUMENTS | Word
Diff: L2 | Tools: citation manager | Web1 Code1 Files1 Vision0 Long1 | Auto 7
Why: требования ГОСТ к библиографии строги и не прощают мелочей
Caps: GOST citations, bibliography compliance

### 547 — Формулы в Word
«Джарвис, вставь в [документ] формулы: [список формул] в редакторе формул, пронумеруй их, добавь пояснения переменных и перекрёстные ссылки.»
Cat: DOCUMENTS | Word
Diff: L2 | Tools: equation editor | Web0 Code1 Files1 Vision0 Long0 | Auto 6
Why: корректные формулы с пояснениями обязательны в технической документации
Caps: equation editing, variable annotation

### 548 — Импорт данных из Excel в Word
«Джарвис, вставь данные из [Excel-файл] в [документ Word]: свяжи таблицу с источником, настрой обновление, сохрани форматирование и подписи.»
Cat: DOCUMENTS | Word
Diff: L2 | Tools: OLE, linked tables | Web0 Code1 Files1 Vision0 Long0 | Auto 6
Why: связанные данные исключают расхождения между файлами
Caps: excel-word integration, linked content

### 549 — Экспорт Word в PDF/HTML
«Джарвис, экспортируй [документ Word] в [PDF/HTML] с сохранением стилей, гиперссылок и вёрстки. Проверь ключевые страницы на рендер.»
Cat: DOCUMENTS | Word
Diff: L1 | Tools: export tools | Web0 Code1 Files1 Vision0 Long0 | Auto 5
Why: экспорт без проверки часто даёт «поплывшую» вёрстку
Caps: document export, fidelity check

### 550 — Совместное редактирование
«Джарвис, организуй совместную работу над [документ]: распредели разделы между [участники], установи сроки, отслеживай, кто что редактирует, сведи итоговую версию.»
Cat: DOCUMENTS | Collaboration
Diff: L2 | Tools: co-editing | Web0 Code1 Files1 Vision0 Long1 | Auto 7
Why: параллельная работа над документом требует координации и сведения версий
Caps: collaborative editing, task division

### 551 — Сборка документа по разделам
«Джарвис, собери итоговый документ из [разделы-файлы]: проверь связность, повторы, стиль переходов, добавь введение и заключение.»
Cat: DOCUMENTS | Authoring
Diff: L2 | Tools: document assembly | Web0 Code1 Files1 Vision0 Long1 | Auto 7
Why: документ из модулей пишется быстрее и легче поддерживается
Caps: document assembly, coherence editing

### 552 — Скан в редактируемый Word
«Джарвис, преврати [скан] в редактируемый документ Word: распознай текст, восстанови структуру заголовков, таблиц и списков, выровняй форматирование.»
Cat: DOCUMENTS | OCR
Diff: L3 | Tools: OCR + Word | Web0 Code1 Files1 Vision0 Long1 | Auto 7
Why: старые бумажные документы возвращаются в цифровой оборот
Caps: scan-to-doc, structure reconstruction

### 553 — Нумерация и списки
«Джарвис, исправь нумерацию списков в [документ]: многоуровневые списки, продолжение после абзацев, соответствие стилям. Проверь на всём документе.»
Cat: DOCUMENTS | Word
Diff: L1 | Tools: list styles | Web0 Code1 Files1 Vision0 Long0 | Auto 5
Why: сломанная нумерация — самый заметный признак небрежности
Caps: list numbering, multi-level lists

### 554 — Защита документа от правок
«Джарвис, защити [документ]: ограничь редактирование только комментариями/заполнением форм, установи пароль на изменения, сделай копию без защиты для себя.»
Cat: SECURITY | Word
Diff: L2 | Tools: document protection | Web0 Code1 Files1 Vision0 Long0 | Auto 6
Why: защита от правок сохраняет целостность согласованных версий
Caps: document protection, edit restrictions

### 555 — Метаданные и сводка документа
«Джарвис, проверь и заполни метаданные [документа]: название, автор, ключевые слова, тема. Удали личные данные из свойств.»
Cat: DOCUMENTS | Word
Diff: L0 | Tools: document properties | Web0 Code1 Files1 Vision0 Long0 | Auto 4
Why: метаданные влияют на поиск, а личные данные в них — на приватность
Caps: metadata management, privacy cleanup

### 556 — Умный поиск и замена
«Джарвис, выполни в [документ] замену [шаблон] на [замена] по правилам: с учётом регистра, только в целых словах, с подтверждением опасных замен. Покажи список замен.»
Cat: DOCUMENTS | Word
Diff: L1 | Tools: find/replace, regex | Web0 Code1 Files1 Vision0 Long0 | Auto 6
Why: массовые замены без подтверждения ломают термины и имена
Caps: smart replace, regex search

### 557 — Устранение дублирования текста
«Джарвис, найди в [документ] повторяющиеся абзацы, похожие фрагменты и пересказы одного и того же. Предложи, что оставить, что удалить.»
Cat: DOCUMENTS | Analysis
Diff: L2 | Tools: similarity tools | Web0 Code1 Files1 Vision0 Long1 | Auto 7
Why: дубли раздувают документ и подрывают доверие к нему
Caps: duplication detection, conciseness

### 558 — Переформатирование в PDF-макет
«Джарвис, переформатируй [документ] под финальный PDF-макет: размер страницы, шрифты, интервалы, разрывы, выравнивание. Добейся типографского вида.»
Cat: DOCUMENTS | Formatting
Diff: L2 | Tools: typesetting | Web0 Code1 Files1 Vision0 Long1 | Auto 6
Why: типографское качество макета отличает профессиональный документ
Caps: typesetting, layout polish

### 559 — Проверка консистентности терминов
«Джарвис, проверь [документ] на консистентность: один ли термин для одного понятия, единые сокращения, написание дат и чисел, ссылки на разделы. Составь глоссарий терминов.»
Cat: DOCUMENTS | Analysis
Diff: L2 | Tools: terminology tools | Web0 Code1 Files1 Vision0 Long1 | Auto 7
Why: расхождение терминов в одном документе — признак низкого качества
Caps: terminology consistency, glossary building

### 560 — Сборка модульного документа
«Джарвис, организуй [документ] как модульный: вынеси повторяющиеся блоки в отдельные шаблоны-включения, собери финальную версию из модулей с параметрами [параметры].»
Cat: DOCUMENTS | Authoring
Diff: L3 | Tools: docs-as-code | Web0 Code1 Files1 Vision0 Long1 | Auto 8
Why: модульность документа позволяет переиспользовать контент без копипасты
Caps: docs-as-code, modular content, content reuse

### 561 — Markdown: структура документации
«Джарвис, организуй документацию проекта в Markdown: структура папок, файл за файлом, связи между разделами, единый стиль заголовков и кода.»
Cat: DOCUMENTS | Markdown
Diff: L1 | Tools: markdown editors | Web0 Code1 Files1 Vision0 Long0 | Auto 6
Why: docs-as-code начинается с аккуратной структуры Markdown
Caps: markdown authoring, docs structure

### 562 — Markdown: диаграммы Mermaid
«Джарвис, добавь в [документ] диаграммы Mermaid: схема архитектуры, последовательность, граф процессов. Проверь рендер и подписи.»
Cat: DOCUMENTS | Markdown
Diff: L2 | Tools: mermaid | Web0 Code1 Files1 Vision0 Long1 | Auto 7
Why: диаграммы из текста версионируются и живут в коде вместе с документацией
Caps: mermaid diagrams, architecture visualization

### 563 — LaTeX: научная статья
«Джарвис, подготовь научную статью в LaTeX по шаблону [журнал]: титул, аннотация, секции, формулы, библиография, оформление рисунков и таблиц. Собери PDF.»
Cat: DOCUMENTS | LaTeX
Diff: L3 | Tools: latex | Web0 Code1 Files1 Vision0 Long1 | Auto 8
Why: LaTeX остаётся стандартом точных наук для вёрстки статей
Caps: latex authoring, journal compliance

### 564 — LaTeX: презентация Beamer
«Джарвис, собери презентацию [тема] в Beamer: слайды, формулы, фреймы кода, заметки докладчика, тема оформления. Скомпилируй и проверь переполнения слайдов.»
Cat: DOCUMENTS | LaTeX
Diff: L3 | Tools: beamer | Web0 Code1 Files1 Vision0 Long1 | Auto 7
Why: Beamer даёт презентации с формулами без PowerPoint-мучений
Caps: beamer slides, technical presentations

### 565 — Sphinx: документация проекта
«Джарвис, разверни документацию [проекта] на Sphinx: настройка, темы, autodoc из docstrings, поиск, версионирование, публикация на [хостинг].»
Cat: DOCUMENTS | Docs
Diff: L3 | Tools: sphinx | Web0 Code1 Files1 Vision0 Long1 | Auto 8
Why: Sphinx превращает docstrings в полноценный сайт документации
Caps: sphinx setup, autodoc, docs hosting

### 566 — CSV/TSV: нормализация данных
«Джарвис, нормализуй [CSV]: кодировка, разделители, типы, дубликаты, пустые значения, единицы измерения. Выдай отчёт о найденных проблемах и чистый файл.»
Cat: DATA | Files
Diff: L1 | Tools: csvkit, pandas | Web0 Code1 Files1 Vision0 Long0 | Auto 6
Why: грязные CSV — источник ошибок во всех последующих расчётах
Caps: csv normalization, data cleaning, encoding fixes

### 567 — Договор: генерация по шаблону
«Джарвис, сгенерируй договор [тип] по шаблону с параметрами: стороны, предмет, суммы, сроки, штрафы, реквизиты. Проверь полноту всех обязательных пунктов.»
Cat: LEGAL | Documents
Diff: L2 | Tools: templates | Web0 Code1 Files1 Vision0 Long0 | Auto 6
Why: типовые договоры из параметров экономят юристам часы рутины
Caps: contract generation, clause assembly

### 568 — Договор: анализ рисков
«Джарвис, проанализируй [договор] на риски: неоднозначные формулировки, отсутствующие пункты, несоразмерные штрафы, устаревшие ссылки на законы. Составь карту рисков с приоритетами.»
Cat: LEGAL | Analysis
Diff: L3 | Tools: legal analysis | Web1 Code1 Files1 Vision0 Long1 | Auto 8
Why: договор — зона, где незамеченный пункт стоит денег
Caps: contract risk analysis, clause gap detection

### 569 — Политика конфиденциальности
«Джарвис, подготовь политику конфиденциальности для [сервис] под [юрисдикция]: сбор данных, cookies, права пользователей, контакты. Проверь соответствие [152-ФЗ/GDPR].»
Cat: LEGAL | Compliance
Diff: L3 | Tools: compliance checklists | Web1 Code1 Files1 Vision0 Long1 | Auto 7
Why: несоответствующая политика — прямой путь к штрафам регуляторов
Caps: privacy policy drafting, regulatory compliance

### 570 — Техническое задание
«Джарвис, напиши техническое задание на [проект/фичу]: цели, функциональные требования, нефункциональные, ограничения, критерии приёмки, этапы, риски.»
Cat: DOCUMENTS | Specs
Diff: L2 | Tools: spec templates | Web0 Code1 Files1 Vision0 Long1 | Auto 7
Why: качественное ТЗ экономит месяцы разработки и переделок
Caps: spec authoring, requirements engineering, acceptance criteria

### 571 — Инструкция пользователя
«Джарвис, напиши инструкцию пользователя для [продукт]: шаги с нумерацией, скриншоты [экран/функция], советы по устранению частых проблем, глоссарий. Проверь инструкцию на новичке.»
Cat: DOCUMENTS | Authoring
Diff: L2 | Tools: screen capture | Web0 Code1 Files1 Vision0 Long1 | Auto 7
Why: понятная инструкция снижает поток поддержки и возвратов
Caps: user guide authoring, step validation

### 572 — Руководство администратора
«Джарвис, напиши руководство администратора для [система]: установка, конфигурация, бэкапы, мониторинг, типовые инциденты и их решение, повышение прав.»
Cat: DOCUMENTS | Authoring
Diff: L3 | Tools: technical writing | Web0 Code1 Files1 Vision0 Long1 | Auto 7
Why: системный документ — то, что спасает при уходе ключевого специалиста
Caps: admin guide, runbooks, incident playbooks

### 573 — Отчёт о проделанной работе
«Джарвис, собери отчёт о работе за [период]: выполненные задачи из [источники], метрики, препятствия, планы на следующий период. Оформи для [руководство/клиент].»
Cat: DOCUMENTS | Reports
Diff: L1 | Tools: report templates | Web0 Code1 Files1 Vision0 Long1 | Auto 7
Why: отчёт — документ, по которому оценивают результат работы
Caps: progress reporting, KPI summary

### 574 — Минутки встречи
«Джарвис, расшифруй/запиши встречу по [заметки/аудио]: решения, ответственные, сроки, открытые вопросы. Оформи минутки и разошли участникам с напоминанием задач.»
Cat: DOCUMENTS | Notes
Diff: L2 | Tools: transcription | Web1 Code1 Files1 Vision0 Long1 | Auto 8
Why: минутки превращают разговор в обязательства с ответственными и сроками
Caps: meeting minutes, action item extraction

### 575 — Пресс-релиз
«Джарвис, напиши пресс-релиз о [событие/продукт]: заголовки (основной и альтернативные), вводный абзац, факты, цитаты, бэкграунд компании, контакты. Адаптируй для [издания].»
Cat: WRITING | PR
Diff: L2 | Tools: press templates | Web1 Code1 Files1 Vision0 Long1 | Auto 6
Why: структура пресс-релиза определяет, перепечатают ли его СМИ
Caps: press release writing, media adaptation

### 576 — Резюме и сопроводительное письмо
«Джарвис, составь резюме из моего опыта [данные] под вакансию [вакансия]: выдели релевантные достижения с цифрами, убери лишнее. Напиши сопроводительное письмо под конкретную компанию [компания].»
Cat: WRITING | Career
Diff: L2 | Tools: resume templates | Web0 Code1 Files1 Vision0 Long1 | Auto 7
Why: резюме под конкретную вакансию проходит фильтры в разы чаще
Caps: resume tailoring, cover letter writing, achievement quantification

### 577 — Чек-листы и опросники
«Джарвис, создай чек-лист [назначение] из [источники/требования]: обязательные пункты, критерии прохождения, веса. Оформи как печатный и интерактивный формат.»
Cat: DOCUMENTS | Authoring
Diff: L1 | Tools: checklist tools | Web0 Code1 Files1 Vision0 Long0 | Auto 6
Why: чек-листы превращают экспертизу в воспроизводимый процесс
Caps: checklist design, criteria scoring

### 578 — База знаний по документам
«Джарвис, организуй базу знаний [отдел] из существующих документов: классифицируй по темам и типам, добавь теги, поиск, права доступа, процессы обновления.»
Cat: DOCUMENTS | Knowledge
Diff: L3 | Tools: knowledge base | Web0 Code1 Files1 Vision0 Long1 | Auto 8
Why: разрозненные документы бесполезны; связанная база — актив компании
Caps: knowledge base design, document classification, search indexing

### 579 — Git для документов
«Джарвис, настрой версионирование [папка документов] через git: история, ветки черновиков, понятные коммиты, автоматические проверки формата, экспорт релизных версий.»
Cat: DOCUMENTS | Docs-as-code
Diff: L2 | Tools: git | Web0 Code1 Files1 Vision0 Long0 | Auto 6
Why: git даёт документам историю, откаты и параллельные ветки правок
Caps: docs versioning, review workflow

### 580 — План подготовки документов
«Джарвис, составь план подготовки [пакет документов] к [дедлайн]: список документов, ответственные, зависимости, этапы согласования, контрольные точки. Отслеживай прогресс и напоминай о задержках.»
Cat: PROJECT | Documents
Diff: L2 | Tools: planning | Web0 Code1 Files1 Vision0 Long1 | Auto 8
Why: пакет документов к дедлайну готовится только планом, а не авралом
Caps: document pipeline planning, deadline tracking
---

### 581 — Очистка данных в Excel
«Джарвис, очисти [таблица]: дубликаты, пробелы, разные написания одного и того же, пустые ячейки, неправильные типы. Покажи отчёт: сколько и что исправлено.»
Cat: DATA | Excel
Diff: L1 | Tools: Excel, Power Query | Web0 Code1 Files1 Vision0 Long0 | Auto 6
Why: грязные данные — источник 80% ошибок в аналитике
Caps: data cleaning, deduplication, normalization

### 582 — Сводные таблицы
«Джарвис, построй сводную таблицу по [данные]: строки [поля], столбцы [поля], значения [метрики] с [агрегация]. Объясни, как читать результаты, и добавь срезы.»
Cat: DATA | Excel
Diff: L1 | Tools: pivot tables | Web0 Code1 Files1 Vision0 Long0 | Auto 6
Why: сводные таблицы — быстрый путь от сырых данных к ответам
Caps: pivot analysis, multi-dimensional aggregation

### 583 — Формулы с объяснением
«Джарвис, напиши формулу для [задача] и объясни каждую её часть: что делает, какие аргументы, какие подводные камни. Проверь на примерах.»
Cat: DATA | Excel
Diff: L1 | Tools: Excel formulas | Web0 Code1 Files1 Vision0 Long0 | Auto 6
Why: понимание формулы важнее её наличия — так её можно поддерживать
Caps: formula authoring, formula explanation

### 584 — Поиск и сопоставление данных
«Джарвис, сопоставь [таблица А] и [таблица Б] по ключу [поле]: найди совпадения, отсутствующие записи, дубли ключей, различия в значениях. Собери результат с пояснением.»
Cat: DATA | Excel
Diff: L2 | Tools: XLOOKUP, Power Query | Web0 Code1 Files1 Vision0 Long0 | Auto 7
Why: сопоставление таблиц — рутина, где легче всего ошибиться вручную
Caps: vlookup logic, key matching, discrepancy detection

### 585 — Условное форматирование
«Джарвис, добавь в [таблица] условное форматирование: подсветка по правилам [правила], цветовые шкалы, значки, правила для топ-N и выбросов. Объясни, что видно сразу.»
Cat: DATA | Excel
Diff: L1 | Tools: conditional formatting | Web0 Code1 Files1 Vision0 Long0 | Auto 5
Why: визуальные паттерны данных замечаются раньше, чем числа в ячейках
Caps: conditional formatting, pattern highlighting

### 586 — Диаграммы по данным
«Джарвис, построй диаграммы для [данные]: выбери тип под [задача], настрой оси, подписи, легенду, цвета. Убери искажения масштаба и объясни выводы по графикам.»
Cat: DATA | Excel
Diff: L1 | Tools: charts | Web0 Code1 Files1 Vision0 Long0 | Auto 6
Why: честная визуализация защищает от манипуляций масштабом
Caps: chart design, honest visualization

### 587 — Проверка данных и валидация ввода
«Джарвис, настрой валидацию ввода для [диапазон]: списки, диапазоны чисел, форматы дат, формулы-условия, кастомные сообщения об ошибке.»
Cat: DATA | Excel
Diff: L1 | Tools: data validation | Web0 Code1 Files1 Vision0 Long0 | Auto 5
Why: валидация на входе экономит часы чистки на выходе
Caps: input validation, error prevention

### 588 — Сценарии What-if
«Джарвис, построй сценарии для [модель]: пессимистичный, базовый, оптимистичный с параметрами [параметры]. Покажи чувствительность результата к каждому параметру.»
Cat: DATA | Excel
Diff: L2 | Tools: scenario manager, data table | Web0 Code1 Files1 Vision0 Long0 | Auto 7
Why: сценарный анализ показывает, какие параметры реально решают исход
Caps: scenario analysis, sensitivity analysis

### 589 — Финансовая модель
«Джарвис, собери финансовую модель [бизнес-идея]: выручка, затраты, юнит-экономика, кэш-флоу, точка безубыточности, прогноз на [лет]. Проверь реалистичность допущений.»
Cat: FINANCE | Excel
Diff: L3 | Tools: financial modeling | Web0 Code1 Files1 Vision0 Long1 | Auto 8
Why: модель с проверяемыми допущениями — основа любого решения об инвестициях
Caps: financial modeling, unit economics, break-even analysis

### 590 — Макросы VBA в Excel
«Джарвис, напиши VBA-макрос для [повторяющаяся операция] в Excel: обработка [диапазоны], вывод [результат], обработка ошибок. Добавь кнопку и протестируй на копии.»
Cat: CODING | Excel
Diff: L3 | Tools: VBA | Web0 Code1 Files1 Vision0 Long0 | Auto 7
Why: макросы заменяют ручную рутину, но требуют аккуратной обработки ошибок
Caps: vba automation, excel scripting

### 591 — Импорт данных в Excel
«Джарвис, импортируй [источник: CSV, база, API, веб] в Excel: настрой типы, кодировку, разделители, расписание обновления. Проверь полноту импорта.»
Cat: DATA | Excel
Diff: L1 | Tools: Power Query | Web0 Code1 Files1 Vision0 Long0 | Auto 6
Why: корректный импорт — половина успеха любой табличной работы
Caps: data import, refresh automation

### 592 — Консолидация листов
«Джарвис, объедини [листы/файлы] в одну таблицу: единая структура, добавь колонку-источник, сохрани согласованность типов. Покажи, где данные конфликтуют.»
Cat: DATA | Excel
Diff: L2 | Tools: Power Query | Web0 Code1 Files1 Vision0 Long0 | Auto 7
Why: консолидация разрозненных листов — частая задача отчётности
Caps: sheet consolidation, schema unification

### 593 — Работа с датами и периодами
«Джарвис, приведи [таблица] к корректной работе с датами: нормализуй форматы, разбей на год/месяц/неделю, посчитай интервалы и рабочие дни, выяви ошибки дат.»
Cat: DATA | Excel
Diff: L2 | Tools: date functions | Web0 Code1 Files1 Vision0 Long0 | Auto 6
Why: даты — самый частый источник молчаливых ошибок в расчётах
Caps: date handling, business days, period analysis

### 594 — Power Query: ETL-конвейер
«Джарвис, построй конвейер Power Query: загрузка из [источники], очистка, преобразования, слияние, выгрузка в [назначение]. Сделай шаги понятными и повторяемыми.»
Cat: DATA | Excel
Diff: L3 | Tools: Power Query | Web0 Code1 Files1 Vision0 Long1 | Auto 8
Why: Power Query превращает разовые манипуляции в воспроизводимый процесс
Caps: etl pipeline, power query automation

### 595 — Power Pivot: большие объёмы
«Джарвис, подключи [модель данных] к Power Pivot: связи между таблицами, вычисляемые меры, DAX для [метрики]. Проверь производительность на [объём].»
Cat: DATA | Excel
Diff: L3 | Tools: Power Pivot, DAX | Web0 Code1 Files1 Vision0 Long1 | Auto 8
Why: Power Pivot позволяет обрабатывать объёмы, недоступные обычным листам
Caps: data modeling, dax measures, in-memory analytics

### 596 — Интерактивный дашборд
«Джарвис, собери дашборд в Excel: KPI-карточки, графики, срезы, диаграммы-спидометры, связанные элементы. Оформи под [аудитория] и проверь на мобильном экране.»
Cat: DATA | Excel
Diff: L2 | Tools: dashboards | Web0 Code1 Files1 Vision0 Long1 | Auto 7
Why: дашборд даёт руководству ответы без переспрашивания аналитика
Caps: dashboard design, kpi visualization, interactivity

### 597 — Защита листов и книги
«Джарвис, защити [книга Excel]: листы с данными от правок, формулы скрыть, разрешить только [диапазоны] для ввода, пароль на структуру. Проверь, что нужные действия работают.»
Cat: SECURITY | Excel
Diff: L2 | Tools: protection | Web0 Code1 Files1 Vision0 Long0 | Auto 6
Why: защита предотвращает случайные и намеренные порчи моделей
Caps: workbook protection, formula hiding

### 598 — Поиск ошибок в формулах
«Джарвис, найди ошибки в [книга]: битые ссылки, #ЗНАЧ/ДЕЛ/0, неверные диапазоны, скрытые константы, формулы-текст. Объясни причину каждой и исправь.»
Cat: DATA | Excel
Diff: L2 | Tools: formula audit | Web0 Code1 Files1 Vision0 Long0 | Auto 7
Why: ошибки формул тихо ломают отчёты и решения на их основе
Caps: formula auditing, error detection, hardcoded value spotting

### 599 — Оптимизация скорости Excel
«Джарвис, [файл Excel] тормозит: найди причины (массивные формулы, условное форматирование, лишние объёмы), оптимизируй и замерь скорость до/после.»
Cat: PERFORMANCE | Excel
Diff: L3 | Tools: profiler, Excel optimization | Web0 Code1 Files1 Vision0 Long0 | Auto 7
Why: медленные книги съедают часы ожидания у всей команды
Caps: workbook optimization, formula efficiency

### 600 — Совместная работа в Excel
«Джарвис, организуй коллективную работу с [книга]: раздели блоки по людям, настрой права, отслеживай изменения, разбери конфликты одновременного редактирования.»
Cat: DATA | Excel
Diff: L2 | Tools: co-authoring | Web0 Code1 Files1 Vision0 Long1 | Auto 7
Why: одновременная работа требует дисциплины и правил владения диапазонами
Caps: collaborative spreadsheets, conflict handling

### 601 — Планирование в Excel
«Джарвис, собери планировщик [проект/бюджет/отпуска] в Excel: календарная сетка, ввод [поля], автосуммы, условная подсветка перегрузок, печатная версия.»
Cat: DATA | Excel
Diff: L2 | Tools: Excel planning | Web0 Code1 Files1 Vision0 Long0 | Auto 6
Why: лёгкие планировщики в Excel работают там, где CRM избыточен
Caps: scheduler design, capacity visualization

### 602 — Условные расчёты по критериям
«Джарвис, посчитай в [таблица] по критериям: СУММЕСЛИ/СЧЁТЕСЛИ по нескольким условиям, сквозные итоги по группам, ранжирование внутри групп. Покажи промежуточные итоги.»
Cat: DATA | Excel
Diff: L1 | Tools: SUMIF/COUNTIF | Web0 Code1 Files1 Vision0 Long0 | Auto 6
Why: условные агрегаты — основа большинства рабочих отчётов
Caps: conditional aggregation, group ranking

### 603 — Динамические массивы
«Джарвис, перепиши [формулы] на динамические массивы: SEQUENCE, FILTER, SORT, UNIQUE вместо вспомогательных колонок. Покажи разницу и проверь совместимость с [версия Excel].»
Cat: DATA | Excel
Diff: L2 | Tools: dynamic arrays | Web0 Code1 Files1 Vision0 Long0 | Auto 7
Why: динамические массивы радикально упрощают формулы и убирают хрупкость
Caps: dynamic arrays, formula modernization

### 604 — Текстовые функции
«Джарвис, обработай текстовые данные в [таблица]: склейка, разбиение, извлечение по шаблону, регистр, замена. Покажи примеры до/после.»
Cat: DATA | Excel
Diff: L1 | Tools: TEXT functions | Web0 Code1 Files1 Vision0 Long0 | Auto 6
Why: парсинг текста в Excel — ежедневная задача работы с выгрузками
Caps: text parsing, string functions

### 605 — Статистический анализ
«Джарвис, проведи статистический анализ [данные]: описательные статистики, распределение, доверительные интервалы, проверка гипотез о [гипотеза]. Объясни выводы простыми словами.»
Cat: SCIENCE | Excel
Diff: L3 | Tools: statistics functions | Web0 Code1 Files1 Vision0 Long1 | Auto 7
Why: статистика превращает мнения о данных в проверенные утверждения
Caps: statistical testing, descriptive stats, hypothesis validation

### 606 — Прогнозирование тренда
«Джарвис, построй прогноз по [исторические данные] на [период]: выбери модель, оцени точность, покажи доверительный интервал и объясни ограничения прогноза.»
Cat: DATA | Excel
Diff: L3 | Tools: FORECAST, trendline | Web0 Code1 Files1 Vision0 Long1 | Auto 7
Why: прогноз с доверительным интервалом полезнее уверенного, но ложного
Caps: time series forecasting, trend analysis

### 607 — Экспорт из Excel
«Джарвис, экспортируй [книга] в [форматы: CSV, JSON, PDF, веб-страница]: настрой кодировку, разделители, форматирование. Проверь потерю данных.»
Cat: DATA | Excel
Diff: L1 | Tools: export | Web0 Code1 Files1 Vision0 Long0 | Auto 5
Why: экспорт — место, где молча теряются нули и типы данных
Caps: export config, data fidelity

### 608 — Шаблоны рабочих таблиц
«Джарвис, создай шаблоны таблиц для [задачи: бюджет, трекер задач, журнал расходов]: готовые формулы, валидация, условное форматирование, инструкция внутри.»
Cat: DATA | Excel
Diff: L2 | Tools: templates | Web0 Code1 Files1 Vision0 Long0 | Auto 6
Why: хорошие шаблоны распространяют лучшие практики по компании
Caps: template design, workbook standards

### 609 — Сравнение двух таблиц
«Джарвис, сравни [таблица А] и [таблица Б]: найди добавленные, удалённые, изменённые строки, расхождения в значениях. Выдай отчёт с пояснениями.»
Cat: DATA | Excel
Diff: L2 | Tools: comparison tools | Web0 Code1 Files1 Vision0 Long0 | Auto 7
Why: сравнение выгрузок — частая проверка корректности систем
Caps: table comparison, data reconciliation

### 610 — Аудит сложной книги
«Джарвис, проведи аудит [книга Excel]: построй карту зависимостей формул, найди недостижимые листы, непоследовательные расчёты, риски при изменении [ячейка].»
Cat: DATA | Excel
Diff: L3 | Tools: formula map, trace precedents | Web0 Code1 Files1 Vision0 Long1 | Auto 8
Why: аудит выявляет, что можно менять безопасно, а что сломает всё
Caps: workbook audit, dependency mapping, risk assessment

### 611 — Структура презентации
«Джарвис, построй структуру презентации [тема] для [аудитория] на [N] минут: ключевое сообщение, логика слайдов, аргументы, призыв к действию. Согласуй со мной.»
Cat: PRESENTATION | Structure
Diff: L1 | Tools: outlining | Web0 Code1 Files1 Vision0 Long1 | Auto 7
Why: структура определяет, запомнят ли сообщение после выступления
Caps: presentation outlining, message design

### 612 — Создание слайдов
«Джарвис, создай слайды по [план/тема]: заголовки-сообщения, минимализм, визуалы вместо текста, заметки докладчика к каждому слайду.»
Cat: PRESENTATION | Authoring
Diff: L2 | Tools: slide editors | Web1 Code1 Files1 Vision0 Long1 | Auto 7
Why: слайды-простыни убивают выступление; слайды-тезисы усиливают его
Caps: slide authoring, visual storytelling

### 613 — Дизайн-система презентации
«Джарвис, разработай дизайн-систему для [презентация]: палитра, шрифты, сетка, типы слайдов, иконки, правила макетов. Примени единообразно ко всем слайдам.»
Cat: PRESENTATION | Design
Diff: L2 | Tools: design tools | Web0 Code1 Files1 Vision0 Long1 | Auto 7
Why: единый дизайн повышает доверие к содержанию
Caps: design system, brand consistency

### 614 — Визуализация данных на слайдах
«Джарвис, преврати [данные] в слайды: выбери правильный тип визуализации под сообщение, убери мусор (chartjunk), подпиши выводы прямо на графике.»
Cat: PRESENTATION | Data
Diff: L2 | Tools: chart design | Web0 Code1 Files1 Vision0 Long1 | Auto 7
Why: график без вывода заставляет аудиторию гадать — это провал
Caps: data storytelling, chart cleanup, insight annotation

### 615 — Анимации и переходы
«Джарвис, настрой анимации в [презентация]: появление по [порядок], выделение ключевых элементов, анимация графиков по сериям. Убери отвлекающие эффекты.»
Cat: PRESENTATION | Design
Diff: L1 | Tools: animation | Web0 Code1 Files1 Vision0 Long0 | Auto 5
Why: анимация ведёт внимание аудитории, а не развлекает её
Caps: animation design, attention control

### 616 — Подготовка речи к слайдам
«Джарвис, напиши текст выступления по [презентация]: вступление, переходы между слайдами, ключевые формулировки, концовка. Адаптируй под [формат: питч/доклад/вебинар].»
Cat: PRESENTATION | Speaking
Diff: L2 | Tools: speech writing | Web0 Code1 Files1 Vision0 Long1 | Auto 7
Why: связная речь превращает набор слайдов в убедительное выступление
Caps: speech writing, transitions, persuasive language

### 617 — Тайминг и репетиция
«Джарвис, составь тайминг-план выступления: минуты на каждый слайд, маркеры середины и конца, запас на вопросы. Проведи репетицию со мной и дай обратную связь по темпу.»
Cat: PRESENTATION | Speaking
Diff: L1 | Tools: timing | Web0 Code1 Files1 Vision0 Long0 | Auto 6
Why: тайминг — то, что отличает профессионала от докладчика-перегруза
Caps: timing plan, rehearsal feedback

### 618 — Сценарий выступления
«Джарвис, распиши сценарий выступления [тема] по минутам: кто говорит, что на экране, что происходит в зале, запасные варианты при сбоях.»
Cat: PRESENTATION | Speaking
Diff: L2 | Tools: scripting | Web0 Code1 Files1 Vision0 Long1 | Auto 7
Why: полный сценарий снимает стресс и делает выступление управляемым
Caps: event scripting, contingency planning

### 619 — Корпоративный шаблон презентаций
«Джарвис, создай корпоративный шаблон презентаций: титульные и контентные макеты, мастер-слайды, фирменные цвета, логотип, правила использования.»
Cat: PRESENTATION | Templates
Diff: L1 | Tools: master slides | Web0 Code1 Files1 Vision0 Long0 | Auto 5
Why: шаблон избавляет каждый отдел от изобретения своего дизайна
Caps: corporate template, master slides

### 620 — Слайды из текстового документа
«Джарвис, преврати [документ/статья] в презентацию: выдели ключевые идеи, разбей по слайдам, подбери визуальные метафоры, сохрани глубину содержания.»
Cat: PRESENTATION | Authoring
Diff: L2 | Tools: summarization | Web0 Code1 Files1 Vision0 Long1 | Auto 8
Why: конверсия документа в презентацию — стандартная и трудоёмкая задача
Caps: document-to-slides, key idea extraction

### 621 — Резюме презентации в страницу
«Джарвис, сожми [презентация] в одну страницу-резюме: ключевое сообщение, топ-5 аргументов, данные, призыв к действию. Для рассылки до/после встречи.»
Cat: PRESENTATION | Summaries
Diff: L1 | Tools: summarization | Web0 Code1 Files1 Vision0 Long1 | Auto 7
Why: одностраничное резюме уважает время занятых читателей
Caps: executive summary, one-pager

### 622 — Питч для инвесторов
«Джарвис, собери питч-дек для инвесторов по [проект]: проблема, решение, рынок, бизнес-модель, traction, команда, запрос. Проверь логику цифр и убедительность.»
Cat: BUSINESS | Presentation
Diff: L3 | Tools: pitch frameworks | Web1 Code1 Files1 Vision0 Long1 | Auto 8
Why: питч-дек решает судьбу раунда, и его логика должна быть железной
Caps: investor pitch, market sizing, traction framing

### 623 — Слайды обучающего курса
«Джарвис, разработай слайды курса [тема]: цели обучения, теория + практика, задания, контрольные вопросы, резюме модулей. Проверь педагогическую логику.»
Cat: LEARNING | Presentation
Diff: L2 | Tools: course design | Web0 Code1 Files1 Vision0 Long1 | Auto 7
Why: учебные слайды подчиняются педагогике, а не только дизайну
Caps: course design, learning objectives, assessment

### 624 — Онлайн-презентация/вебинар
«Джарвис, адаптируй [презентация] под онлайн-формат: крупный текст, интерактив, опросы, сценарий модерации, план работы с чатом и вопросами.»
Cat: PRESENTATION | Online
Diff: L2 | Tools: webinar tools | Web0 Code1 Files1 Vision0 Long1 | Auto 7
Why: онлайн-аудитория теряет внимание быстрее, чем живая
Caps: webinar adaptation, engagement mechanics

### 625 — Подготовка к вопросам и Q&A
«Джарвис, предскажи вопросы аудитории к [презентация]: слабые места, спорные цифры, конкуренты, цена. Подготовь ответы и заготовки для сложных вопросов.»
Cat: PRESENTATION | Speaking
Diff: L2 | Tools: Q&A prep | Web0 Code1 Files1 Vision0 Long1 | Auto 7
Why: готовые ответы на неудобные вопросы — половина уверенности докладчика
Caps: q&a preparation, objection handling

### 626 — Разбор чужой презентации
«Джарвис, проанализируй [презентация] как критик: сила аргументов, визуальный шум, несостыковки цифр, риторические приёмы. Дай список улучшений с приоритетами.»
Cat: PRESENTATION | Analysis
Diff: L2 | Tools: review frameworks | Web0 Code1 Files1 Vision0 Long1 | Auto 7
Why: критический разбор чужих презентаций развивает своё мастерство
Caps: presentation critique, persuasion analysis

### 627 — Постер или инфографика
«Джарвис, создай постер/инфографику на тему [тема]: иерархия информации, визуальный поток, факты с источниками, формат [размер]. Подготовь к печати.»
Cat: DESIGN | Presentation
Diff: L2 | Tools: design tools | Web1 Code1 Files1 Vision0 Long1 | Auto 7
Why: постер продаёт идею за секунды просмотра
Caps: infographic design, visual hierarchy

### 628 — Слайды для соцсетей
«Джарвис, нарежь [презентация/материалы] на посты-слайды для [соцсеть]: вертикальный формат, короткие тезисы, вовлекающие вопросы, брендирование.»
Cat: MARKETING | Presentation
Diff: L1 | Tools: social templates | Web0 Code1 Files1 Vision0 Long1 | Auto 6
Why: один контент, переиспользованный в соцсетях, работает многократно
Caps: social content adaptation, carousel design

### 629 — Видео из слайдов
«Джарвис, преврати [презентация] в видео: тайминг на слайд, озвучка текста, музыка, субтитры, экспорт в [формат]. Покажи превью ключевых моментов.»
Cat: VIDEO | Presentation
Diff: L3 | Tools: video tools, TTS | Web0 Code1 Files1 Vision0 Long1 | Auto 8
Why: видео из слайдов — дешёвый способ создать обучающий контент
Caps: slides-to-video, voiceover sync, subtitle overlay

### 630 — Финальная проверка перед выступлением
«Джарвис, проверь [презентация] перед выступлением: орфография, корректность цифр, ссылки, шрифты на другой машине, видео/аудио вставки, запасная копия. Дай чек-лист.»
Cat: PRESENTATION | QA
Diff: L1 | Tools: checklists | Web0 Code1 Files1 Vision0 Long0 | Auto 5
Why: технические сбои на сцене отвлекают от лучшего содержания
Caps: pre-presentation QA, tech rehearsal

### 631 — Профилирование набора данных
«Джарвис, сделай профиль [датасет]: типы, диапазоны, распределения, кардинальность, аномалии. Выдай сводку, которая показывает качество данных одним взглядом.»
Cat: DATA | Analysis
Diff: L1 | Tools: pandas-profiling | Web0 Code1 Files1 Vision0 Long1 | Auto 7
Why: профиль данных — первый шаг перед любым анализом или ML
Caps: data profiling, quality assessment, distribution analysis

### 632 — Поиск выбросов
«Джарвис, найди выбросы в [данные] по [поля]: статистические методы, контекстные аномалии, ошибки ввода. Классифицируй: реальные события или ошибки.»
Cat: DATA | Analysis
Diff: L2 | Tools: statistical methods | Web0 Code1 Files1 Vision0 Long1 | Auto 7
Why: выброс — это либо находка, либо ошибка; важно различить
Caps: outlier detection, anomaly classification

### 633 — Работа с пропущенными значениями
«Джарвис, обработай пропуски в [данные]: оцени долю по колонкам, определи механизм (случайные/системные), предложи и примени стратегию [удаление/заполнение/моделирование].»
Cat: DATA | Analysis
Diff: L2 | Tools: pandas | Web0 Code1 Files1 Vision0 Long1 | Auto 7
Why: наивная работа с пропусками незаметно искажает все выводы
Caps: missing data handling, imputation strategy

### 634 — Корреляционный анализ
«Джарвис, посчитай корреляции между [поля]: матрица, сила и значимость связей, ложные корреляции. Объясни, какие выводы можно делать, а какие нельзя.»
Cat: SCIENCE | Analysis
Diff: L2 | Tools: statistics | Web0 Code1 Files1 Vision0 Long1 | Auto 7
Why: корреляция — не причинность, и аналитик обязан это объяснять
Caps: correlation analysis, spurious correlation detection

### 635 — Анализ временных рядов
«Джарвис, проанализируй [временной ряд]: тренд, сезонность, циклы, аномальные точки, автокорреляция. Разложи ряд на компоненты и покажи, что стоит за колебаниями.»
Cat: DATA | Analysis
Diff: L3 | Tools: time series libraries | Web0 Code1 Files1 Vision0 Long1 | Auto 8
Why: разложение ряда объясняет поведение метрики лучше любых догадок
Caps: time series decomposition, trend/seasonality analysis

### 636 — Кластеризация данных
«Джарвис, кластеризуй [данные]: выбери число кластеров, метод [KMeans/DBSCAN], интерпретируй профили кластеров, покажи их визуально и объясни практический смысл.»
Cat: SCIENCE | Analysis
Diff: L3 | Tools: sklearn | Web0 Code1 Files1 Vision0 Long1 | Auto 8
Why: кластеризация находит сегменты, которые не видны глазами
Caps: clustering, segment profiling, dimensionality reduction

### 637 — Регрессионный анализ
«Джарвис, построй регрессионную модель [зависимая ~ независимые]: оцени качество, значимость факторов, проверь допущения, объясни влияние каждой переменной.»
Cat: SCIENCE | Analysis
Diff: L3 | Tools: statsmodels | Web0 Code1 Files1 Vision0 Long1 | Auto 8
Why: регрессия отвечает «что влияет и насколько», если не нарушать допущений
Caps: regression modeling, factor significance, model diagnostics

### 638 — Анализ A/B-теста
«Джарвис, проанализируй A/B-тест [данные]: проверь корректность дизайна, посчитай метрики, статистическую значимость, доверительные интервалы, сделай вывод о запуске.»
Cat: SCIENCE | Analysis
Diff: L3 | Tools: statistical testing | Web0 Code1 Files1 Vision0 Long1 | Auto 8
Why: ошибочный вывод A/B-теста стоит дороже, чем отсутствие теста
Caps: ab-test analysis, significance testing, experiment design

### 639 — Визуализация данных
«Джарвис, визуализируй [данные] для [задача]: выбери типы графиков, оформи оси и легенды, убери искажения, подпиши выводы. Собери в [документ/дашборд].»
Cat: DATA | Visualization
Diff: L2 | Tools: matplotlib, plotly | Web0 Code1 Files1 Vision0 Long1 | Auto 7
Why: визуализация — самый быстрый канал передачи выводов
Caps: data visualization, chart selection, insight labeling

### 640 — Аналитический отчёт
«Джарвис, собери аналитический отчёт по [вопрос] из [данные]: методология, находки, цифры, ограничения, рекомендации. Оформи для [аудитория] с приложениями.»
Cat: DATA | Reporting
Diff: L2 | Tools: reporting | Web0 Code1 Files1 Vision0 Long1 | Auto 8
Why: отчёт без ограничений и методологии — это маркетинг, а не аналитика
Caps: analytical reporting, recommendation framing

### 641 — Распознавание фото документов
«Джарвис, распознай [фото документа]: исправь перспективу, контраст, определи тип документа, извлеки текст и данные. Проверь точность на сложных участках.»
Cat: OCR | Documents
Diff: L2 | Tools: tesseract, image preprocessing | Web0 Code1 Files1 Vision1 Long0 | Auto 7
Why: фото документов с телефона — основной источник бумаг в цифре
Caps: document photo OCR, perspective correction

### 642 — Пакетное сканирование документов
«Джарвис, обработай пачку сканов в [папка]: раздели на документы, распознай, назови файлы по содержимому, создай поисковый индекс. Сообщи о сомнительных результатах.»
Cat: OCR | Documents
Diff: L3 | Tools: batch OCR | Web0 Code1 Files1 Vision0 Long1 | Auto 8
Why: пакетная обработка сканов — задача, для которой ИИ создан
Caps: batch scanning, document separation, auto-naming

### 643 — Распознавание рукописного текста
«Джарвис, распознай рукописный текст с [изображение]: разбери почерк, структуру (списки, даты, суммы), отметь места, где не уверен.»
Cat: OCR | Documents
Diff: L3 | Tools: HTR models | Web0 Code1 Files1 Vision1 Long0 | Auto 6
Why: рукописные заметки — последний «бумажный» формат, который не ищется
Caps: handwriting recognition, handwritten note digitization

### 644 — Извлечение данных из документов
«Джарвис, извлеки структурированные данные из [документы]: счета, паспорта, накладные — поля [поля]. Сверь с образцом, покажи уверенность по каждому полю.»
Cat: OCR | Documents
Diff: L3 | Tools: document parsers | Web0 Code1 Files1 Vision1 Long1 | Auto 8
Why: извлечение полей автоматизирует ввод данных в учётные системы
Caps: field extraction, document understanding, confidence scoring

### 645 — Проверка качества OCR
«Джарвис, оцени качество распознавания [результат OCR] против [оригинал]: подсвети сомнительные символы, слова с низкой уверенностью, ошибки в числах.»
Cat: OCR | QA
Diff: L2 | Tools: confidence analysis | Web0 Code1 Files1 Vision1 Long0 | Auto 7
Why: OCR без контроля качества — источник тихих ошибок в данных
Caps: ocr quality control, error highlighting

### 646 — Перевод документа с сохранением формата
«Джарвис, переведи [документ] на [язык] с сохранением форматирования: таблицы, заголовки, шрифты, нумерация, вставки. Проверь термины по [глоссарий].»
Cat: TRANSLATION | Documents
Diff: L2 | Tools: CAT tools | Web1 Code1 Files1 Vision0 Long1 | Auto 8
Why: перевод без потери вёрстки экономит часы ручного восстановления
Caps: document translation, layout preservation

### 647 — Локализация программного обеспечения
«Джарвис, подготовь [проект] к локализации: вынеси строки, собери файлы перевода, адаптируй форматы дат/чисел/валют, проверь длину строк в UI.»
Cat: TRANSLATION | Software
Diff: L3 | Tools: i18n frameworks | Web0 Code1 Files1 Vision0 Long1 | Auto 8
Why: локализация «после» — это переписывание; локализация «в процессе» — просто
Caps: internationalization, resource extraction, locale adaptation

### 648 — Перевод сайта
«Джарвис, переведи [сайт] на [языки]: контент, мета-теги, URL, H1/alt-тексты, сохранение SEO-структуры. Проверь, что переводы не ломают вёрстку.»
Cat: TRANSLATION | Web
Diff: L2 | Tools: CMS, translation APIs | Web1 Code1 Files1 Vision0 Long1 | Auto 7
Why: многоязычный сайт открывает новые рынки, если SEO сохранено
Caps: website translation, seo preservation, hreflang

### 649 — Постредактирование машинного перевода
«Джарвис, отредактируй машинный перевод [текст]: исправь буквализмы, стиль, терминологию, пунктуацию, культурные отсылки. Покажи, что изменил и почему.»
Cat: TRANSLATION | Editing
Diff: L2 | Tools: MT, editing | Web0 Code1 Files1 Vision0 Long1 | Auto 7
Why: качественный постредакшинг делает машинный перевод пригодным к публикации
Caps: post-editing, machine translation quality lift

### 650 — Глоссарий терминов
«Джарвис, создай глоссарий для [домен/проект] на [языки]: термины, определения, варианты перевода, запрещённые варианты, контексты использования.»
Cat: TRANSLATION | Terminology
Diff: L2 | Tools: glossary tools | Web1 Code1 Files1 Vision0 Long1 | Auto 7
Why: единый глоссарий — фундамент согласованных переводов команды
Caps: terminology management, translation memory

### 651 — Перевод субтитров
«Джарвис, переведи субтитры [файл] на [язык]: сохрани таймкоды, адаптируй под лимиты символов, передай шутки и идиомы. Проверь синхронизацию.»
Cat: TRANSLATION | Media
Diff: L2 | Tools: subtitle tools | Web0 Code1 Files1 Vision0 Long1 | Auto 7
Why: субтитры требуют сжатия смысла под лимит — особый навык перевода
Caps: subtitle translation, timing preservation

### 652 — Перевод под аудиторию
«Джарвис, переведи [текст] на [язык] для [аудитория: дети, технари, инвесторы]: уровень сложности, терминология, тон, примеры. Покажи два варианта для сравнения.»
Cat: TRANSLATION | Adaptation
Diff: L2 | Tools: localization | Web0 Code1 Files1 Vision0 Long1 | Auto 7
Why: перевод «для всех» — это перевод «ни для кого»
Caps: audience adaptation, register control, transcreation

### 653 — Сравнение вариантов перевода
«Джарвис, сравни [перевод А] и [перевод Б]: точность, стиль, полнота, ошибки. Поставь оценку и рекомендацию, какой использовать и что поправить.»
Cat: TRANSLATION | QA
Diff: L1 | Tools: comparison | Web0 Code1 Files1 Vision0 Long0 | Auto 6
Why: выбор между переводами требует объективных критериев, а не вкуса
Caps: translation comparison, quality scoring

### 654 — Перевод с сохранением стиля автора
«Джарвис, переведи [текст] с сохранением стиля: тон, ритм, ирония, канцелярит, регистр. Отметь, где стиль автора пришлось адаптировать для [язык].»
Cat: TRANSLATION | Style
Diff: L2 | Tools: style-aware MT | Web0 Code1 Files1 Vision0 Long1 | Auto 7
Why: стиль — часть смысла, и перевод обязан его сохранять
Caps: style preservation, author voice translation

### 655 — Двуязычная вёрстка документа
«Джарвис, собери двуязычную версию [документ]: параллельные колонки или постраничное чередование, согласованные заголовки, нумерация разделов, перекрёстные ссылки.»
Cat: TRANSLATION | Documents
Diff: L3 | Tools: layout tools | Web0 Code1 Files1 Vision0 Long1 | Auto 7
Why: двуязычные документы нужны в юриспруденции и международных проектах
Caps: bilingual layout, parallel translation

### 656 — Стилистическая редактура
«Джарвис, отредактируй [текст] стилистически: убери шероховатости, тавтологии, канцелярит, сделай текст короче без потери смысла. Покажи версию «до/после».»
Cat: WRITING | Editing
Diff: L1 | Tools: editing | Web0 Code1 Files1 Vision0 Long1 | Auto 7
Why: редактура — финальный слой, отделяющий текст от текста-продукта
Caps: copy editing, conciseness, clarity

### 657 — Генерация контент-идей
«Джарвис, сгенерируй [N] идей контента для [канал/аудитория] по [тема]: форматы, углы, заголовки, релевантность трендам. Оцени сложность и потенциал каждой.»
Cat: MARKETING | Content
Diff: L1 | Tools: ideation | Web1 Code0 Files1 Vision0 Long0 | Auto 6
Why: идейный конвейер — топливо любого контент-плана
Caps: content ideation, trend alignment

### 658 — SEO-текст
«Джарвис, напиши SEO-текст по [запрос/тема]: структура с H2/H3, ключевые слова с частотами, мета-описание, внутренние ссылки. Сохрани естественность языка.»
Cat: MARKETING | SEO
Diff: L2 | Tools: SEO tools | Web1 Code1 Files1 Vision0 Long1 | Auto 7
Why: SEO-текст должен ранжироваться и при этом читаться людьми
Caps: seo writing, keyword optimization, meta tagging

### 659 — Сторителлинг из данных/фактов
«Джарвис, преврати [факты/данные] в историю: персонажи, конфликт, развитие, вывод. Адаптируй под [формат: статья, речь, пост].»
Cat: WRITING | Narrative
Diff: L2 | Tools: narrative design | Web0 Code1 Files1 Vision0 Long1 | Auto 7
Why: истории запоминаются, а факты — нет, пока их не обернуть в историю
Caps: storytelling, narrative structure, fact dramatization

### 660 — Редактура текста с обоснованием правок
«Джарвис, отредактируй [текст] с пояснением каждой правки: категории (ясность, факты, стиль, структура), приоритеты, варианты для спорных мест.»
Cat: WRITING | Editing
Diff: L1 | Tools: editing frameworks | Web0 Code1 Files1 Vision0 Long1 | Auto 7
Why: обоснованные правки учат автора, а не только улучшают текст
Caps: developmental editing, justification, feedback
---

### 661 — Редактирование фото по описанию
«Джарвис, отредактируй [фото] по моему описанию: [пожелания: осветлить, убрать красные глаза, выровнять горизонт]. Сделай копию и покажи результат до/после.»
Cat: IMAGE | Editing
Diff: L1 | Tools: image editors | Web0 Code0 Files1 Vision1 Long0 | Auto 6
Why: редактирование по описанию — базовая ценность ассистента с зрением
Caps: photo editing, visual instruction following

### 662 — Улучшение качества фото
«Джарвис, улучши качество [фото]: убери шум, повысь резкость, исправь экспозицию и баланс белого без неестественности. Сохрани оригинал.»
Cat: IMAGE | Enhancement
Diff: L1 | Tools: denoise, sharpening | Web0 Code0 Files1 Vision1 Long0 | Auto 6
Why: лёгкая обработка спасает снимки, не превращая их в «фотошоп»
Caps: photo enhancement, denoising, exposure correction

### 663 — Удаление фона
«Джарвис, удали фон у [изображение]: сохрани детали краёв (волосы, мех, прозрачность), выдай PNG с прозрачностью и JPEG с белым фоном.»
Cat: IMAGE | Editing
Diff: L1 | Tools: background removal | Web0 Code0 Files1 Vision1 Long0 | Auto 6
Why: удаление фона нужно для каталогов, презентаций и мемов
Caps: background removal, edge refinement

### 664 — Кадрирование по правилам
«Джарвис, обрежь [фото] по правилам композиции: золотое сечение, третьи, оставь пространство для дыхания, сохрани ключевой объект. Покажи варианты.»
Cat: IMAGE | Editing
Diff: L1 | Tools: crop tools | Web0 Code0 Files1 Vision1 Long0 | Auto 5
Why: кадр решает всё — правильная обрезка улучшает любой снимок
Caps: composition cropping, rule-of-thirds

### 665 — Коррекция цвета
«Джарвис, скорректируй цвета [фото]: выровняй баланс белого, насыщенность, тональные кривые по [ориентир]. Сверь кожные тона и нейтральные цвета.»
Cat: IMAGE | Editing
Diff: L2 | Tools: color tools | Web0 Code0 Files1 Vision1 Long0 | Auto 6
Why: корректные цвета — признак профессиональной обработки
Caps: color correction, white balance, tonal curves

### 666 — Пакетная обработка изображений
«Джарвис, обработай все изображения в [папка]: [операция: ресайз, конвертация, водяной знак, коррекция] с параметрами [параметры]. Работай параллельно и покажи отчёт об ошибках.»
Cat: IMAGE | Batch
Diff: L2 | Tools: ImageMagick, batch | Web0 Code0 Files1 Vision0 Long0 | Auto 8
Why: пакетная обработка — зона максимальной экономии времени
Caps: batch image processing, bulk operations

### 667 — Конвертация форматов изображений
«Джарвис, сконвертируй [изображение] в [формат]: настрой качество, цветовой профиль, прозрачность (когда применимо). Объясни потери при конвертации.»
Cat: IMAGE | Conversion
Diff: L0 | Tools: converters | Web0 Code0 Files1 Vision0 Long0 | Auto 5
Why: конвертация без потерь требует знания ограничений форматов
Caps: format conversion, quality preservation

### 668 — Оптимизация изображений для веба
«Джарвис, оптимизируй [изображения] для веба: подбери формат (WebP/AVIF/JPEG), сжатие, размеры для [назначение], сохрани визуальное качество. Дай сводку экономии веса.»
Cat: PERFORMANCE | Image
Diff: L1 | Tools: imagemin, cwebp | Web0 Code0 Files1 Vision0 Long0 | Auto 6
Why: тяжёлые картинки — главный тормоз сайтов и причина штрафов Core Web Vitals
Caps: web image optimization, format selection

### 669 — Масштабирование и спрайты
«Джарвис, подготовь [изображение] во все нужные размеры: [список размеров/устройств], адаптивные версии, retina. Проверь резкость на уменьшенных.»
Cat: IMAGE | Editing
Diff: L1 | Tools: resize tools | Web0 Code0 Files1 Vision0 Long0 | Auto 6
Why: набор готовых размеров избавляет от CSS-деформаций
Caps: responsive resizing, retina assets

### 670 — Генерация изображений по описанию
«Джарвис, сгенерируй изображение по описанию: [подробное описание], стиль [стиль], соотношение сторон [ratio], настроение [настроение]. Дай 4 варианта и уточни детали.»
Cat: IMAGE | Generation
Diff: L1 | Tools: image models | Web1 Code0 Files1 Vision1 Long0 | Auto 6
Why: генерация по промпту — новый стандарт создания визуалов
Caps: image generation, prompt engineering, style control

### 671 — Создание мемов
«Джарвис, сделай мем на тему [тема]: подбери шаблон [шаблон] или сгенерируй, добавь текст [текст], проверь читаемость и юмор.»
Cat: ENTERTAINMENT | Image
Diff: L0 | Tools: meme tools | Web0 Code0 Files1 Vision1 Long0 | Auto 5
Why: мемы — быстрый способ вовлечь аудиторию в соцсетях
Caps: meme creation, humor calibration

### 672 — Создание коллажа
«Джарвис, собери коллаж из [фото]: композиция, обрезка, рамки, подписи, единая цветовая гамма. Сделай несколько вариантов раскладки.»
Cat: IMAGE | Design
Diff: L1 | Tools: collage tools | Web0 Code0 Files1 Vision1 Long0 | Auto 6
Why: коллажи компактно рассказывают историю несколькими кадрами
Caps: collage design, layout variants

### 673 — Водяные знаки на изображениях
«Джарвис, добавь водяной знак [лого/текст] на [изображения]: позиция, размер, прозрачность, устойчивость к обрезке. Сделай для [папка] в пакетном режиме.»
Cat: SECURITY | Image
Diff: L1 | Tools: watermarking | Web0 Code0 Files1 Vision0 Long0 | Auto 6
Why: водяные знаки защищают авторство фотографий и каталогов
Caps: watermarking, brand protection

### 674 — EXIF: чтение и очистка метаданных
«Джарвис, прочитай метаданные [фото]: камера, параметры съёмки, геолокация, история правок. Удали чувствительные данные для публикации.»
Cat: SECURITY | Image
Diff: L1 | Tools: exiftool | Web0 Code0 Files1 Vision0 Long0 | Auto 5
Why: EXIF раскрывает геолокацию и устройство — риск для приватности
Caps: exif analysis, metadata stripping

### 675 — Организация фотоархива
«Джарвис, организуй [фотоархив]: разложи по датам/событиям, найди дубликаты и похожие кадры, исправь ориентацию, добавь геотеги. Создай каталог с превью.»
Cat: IMAGE | Archive
Diff: L2 | Tools: dedup, sorting | Web0 Code0 Files1 Vision0 Long1 | Auto 8
Why: хаос в фотоархиве делает снимки фактически потерянными
Caps: photo archive organization, duplicate detection

### 676 — Текст с изображения
«Джарвис, извлеки текст с [изображение]: экраны, вывески, документы, скриншоты. Сохрани структуру и отметь, где текст обрезан.»
Cat: OCR | Image
Diff: L1 | Tools: tesseract | Web0 Code0 Files1 Vision1 Long0 | Auto 6
Why: текст на картинках невидим для поиска, пока его не извлекут
Caps: image text extraction, screenshot OCR

### 677 — Поиск похожих изображений
«Джарвис, найди в [коллекция] изображения, похожие на [образец]: по композиции, цветам, объектам. Объясни, по какому критерию совпало каждое.»
Cat: IMAGE | Search
Diff: L2 | Tools: embeddings, perceptual hash | Web0 Code0 Files1 Vision1 Long0 | Auto 7
Why: поиск по смыслу, а не по имени файла — ключ к большим коллекциям
Caps: similarity search, perceptual hashing

### 678 — Определение объектов на фото
«Джарвис, определи объекты на [фото]: что изображено, сколько объектов, где находятся. Выдай список с координатами и уверенностью.»
Cat: VISION | Recognition
Diff: L1 | Tools: detection models | Web0 Code0 Files1 Vision1 Long0 | Auto 7
Why: детекция объектов — база для индексации и автоматизации фото
Caps: object detection, scene understanding

### 679 — Распознавание лиц и персоналий
«Джарвис, найди лица на [фото]: сколько, где, эмоции, возрастные оценки. Сопоставь с [база известных лиц] и отметь неопределённые случаи.»
Cat: VISION | Recognition
Diff: L2 | Tools: face models | Web0 Code0 Files1 Vision1 Long0 | Auto 6
Why: распознавание лиц требует аккуратности из-за приватности
Caps: face detection, emotion recognition, identity matching

### 680 — Восстановление старых фотографий
«Джарвис, восстанови [старое фото]: убери царапины, пятна, изломы, дефекты плёнки, восстанови детали. Сохрани дух оригинала и покажи до/после.»
Cat: IMAGE | Restoration
Diff: L2 | Tools: restoration models | Web0 Code0 Files1 Vision1 Long0 | Auto 6
Why: восстановление семейных архивов — эмоционально ценная задача ИИ
Caps: photo restoration, scratch removal

### 681 — Раскрашивание чёрно-белых фото
«Джарвис, раскрась [ч/б фото]: подбери естественные цвета по контексту, сохрани историческую достоверность, дай возможность вручную поправить зоны.»
Cat: IMAGE | Restoration
Diff: L2 | Tools: colorization models | Web0 Code0 Files1 Vision1 Long0 | Auto 6
Why: цвет возвращает старым кадрам ощущение реальности
Caps: photo colorization, historical accuracy

### 682 — Увеличение разрешения (upscale)
«Джарвис, увеличь [изображение] в [N] раз с восстановлением деталей: сверхразрешение, сглаживание, без артефактов. Сравни с обычным бикубическим масштабированием.»
Cat: IMAGE | Enhancement
Diff: L2 | Tools: super-resolution | Web0 Code0 Files1 Vision1 Long0 | Auto 6
Why: качественный апскейл спасает маленькие снимки для печати
Caps: super-resolution, detail recovery

### 683 — Стеганография в изображениях
«Джарвис, проверь [изображение] на скрытые данные: встрой/извлеки сообщение через LSB, проверь артефакты сжатия, обнаружь признаки модификации.»
Cat: SECURITY | Stego
Diff: L4 | Tools: stego tools | Web0 Code0 Files1 Vision0 Long0 | Auto 6
Why: изображения — идеальный контейнер для скрытой передачи данных
Caps: steganography, hidden data detection

### 684 — Проверка подлинности фото
«Джарвис, проанализируй [фото] на подлинность: признаки редактирования, подмена лица, дубликаты областей, несоответствие метаданных. Выдай вердикт с уверенностью.»
Cat: SECURITY | Forensics
Diff: L3 | Tools: forensics, ELA | Web0 Code0 Files1 Vision1 Long0 | Auto 6
Why: дипфейки и фотофейки требуют инструментальной проверки
Caps: image forensics, manipulation detection, deepfake check

### 685 — Скриншоты и запись экрана
«Джарвис, сделай скриншоты [окно/область/вся страница] и запиши видео экрана: [сценарий действий]. Разложи по папкам с понятными именами.»
Cat: IMAGE | Capture
Diff: L1 | Tools: capture tools | Web0 Code0 Files1 Vision0 Long0 | Auto 6
Why: скриншоты и записи — основа инструкций и отчётов об ошибках
Caps: screen capture, screencast, area selection

### 686 — Диаграмма из изображения
«Джарвис, восстанови данные из [диаграмма/график на картинке]: считай значения по осям, определи тип графика, выгрузи точки данных в таблицу. Отметь неточности.»
Cat: DATA | Vision
Diff: L3 | Tools: chart recognition | Web0 Code0 Files1 Vision1 Long0 | Auto 7
Why: цифры на картинке недоступны анализу, пока не извлечены
Caps: chart data extraction, plot digitization

### 687 — Дизайн обложек
«Джарвис, создай обложку для [книга/курс/видео]: композиция, типографика, цветовая гамма, формат [размер]. Дай 3 варианта в разных стилях.»
Cat: DESIGN | Image
Diff: L2 | Tools: design tools | Web0 Code0 Files1 Vision1 Long0 | Auto 7
Why: обложка решает, кликнут ли на контент, ещё до его чтения
Caps: cover design, typography, variant exploration

### 688 — Логотип и айдентика
«Джарвис, разработай логотип для [бренд]: концепции по [индустрия/ценности], варианты в векторе, на тёмном/светлом фоне, favicon, монохром.»
Cat: DESIGN | Branding
Diff: L2 | Tools: vector tools | Web0 Code0 Files1 Vision1 Long0 | Auto 7
Why: логотип должен работать в любом масштабе и контексте
Caps: logo design, brand identity, vector assets

### 689 — Инфографика из данных
«Джарвис, сделай инфографику по [данные/тема]: иерархия цифр, иконки, пояснения, единый стиль. Подготовь для [формат публикации].»
Cat: DESIGN | Infographics
Diff: L2 | Tools: infographic tools | Web0 Code0 Files1 Vision1 Long0 | Auto 7
Why: инфографика делает сложные данные запоминаемыми
Caps: infographic creation, data design

### 690 — Художественная стилизация фото
«Джарвис, стилизуй [фото] под [стиль: акварель, киберпанк, винтаж, комикс]: перенеси стиль, сохрани узнаваемость объекта. Дай несколько вариаций силы эффекта.»
Cat: IMAGE | Style
Diff: L2 | Tools: style transfer | Web0 Code0 Files1 Vision1 Long0 | Auto 6
Why: стилизация — творческий инструмент для соцсетей и артов
Caps: style transfer, artistic rendering

### 691 — Удаление объектов с фото
«Джарвис, убери с [фото] [объект/человек/текст]: залей фон правдоподобно, восстанови структуры (стены, пол), сделай незаметно. Покажи до/после.»
Cat: IMAGE | Editing
Diff: L2 | Tools: inpainting | Web0 Code0 Files1 Vision1 Long0 | Auto 6
Why: удаление объектов требует понимания сцены, а не просто заливки
Caps: object removal, inpainting, scene reconstruction

### 692 — Замена фона с сохранением света
«Джарвис, замени фон на [фото] на [новый фон]: согласуй освещение, тени, цветовую температуру с объектом. Отметь, где стык виден.»
Cat: IMAGE | Editing
Diff: L2 | Tools: background replacement | Web0 Code0 Files1 Vision1 Long0 | Auto 6
Why: согласованный свет — главный признак качественной замены фона
Caps: background replacement, lighting matching

### 693 — Мокапы продуктов
«Джарвис, вставь [дизайн/скриншот] в мокапы: [устройства/упаковка], перспектива, тени, окружение. Сделай набор для [презентация/маркетплейс].»
Cat: DESIGN | Mockups
Diff: L2 | Tools: mockup tools | Web0 Code0 Files1 Vision1 Long0 | Auto 6
Why: мокапы показывают продукт в реальном контексте
Caps: mockup generation, perspective warping

### 694 — Спрайт-листы и атласы
«Джарвис, разрежь [спрайт-лист] на отдельные кадры по сетке [rows x cols], либо собери атлас из [изображения] с JSON-координатами для [движок/фреймворк].»
Cat: CODING | Assets
Diff: L2 | Tools: sprite tools | Web0 Code0 Files1 Vision0 Long0 | Auto 7
Why: работа со спрайтами — рутина геймдева и веб-анимаций
Caps: sprite sheet processing, texture atlas generation

### 695 — Визуальное сравнение изображений
«Джарвис, сравни [изображение А] и [изображение Б]: различия, области изменений, общий процент совпадения. Подсвети изменённые зоны.»
Cat: IMAGE | Analysis
Diff: L2 | Tools: image diff | Web0 Code0 Files1 Vision1 Long0 | Auto 6
Why: визуальный дифф — контроль регрессий в UI и дизайне
Caps: image comparison, change detection

### 696 — Палитра и цвета из изображения
«Джарвис, извлеки из [изображение] цветовую палитру: основные цвета, HEX-коды, пропорции. Подбери комплементарные и нейтральные оттенки для дизайна.»
Cat: DESIGN | Color
Diff: L0 | Tools: palette tools | Web0 Code0 Files1 Vision1 Long0 | Auto 5
Why: палитра из референса — быстрый старт любого дизайна
Caps: color palette extraction, color theory application

### 697 — Ретушь портрета
«Джарвис, отретушируй [портрет]: кожа, мешки под глазами, блеск, но сохрани естественность и текстуру. Убери только то, что попрошу.»
Cat: IMAGE | Editing
Diff: L1 | Tools: retouching | Web0 Code0 Files1 Vision1 Long0 | Auto 5
Why: пересушенная ретушь выдаёт обработку и портит кадр
Caps: portrait retouching, natural skin preservation

### 698 — Фото на документы
«Джарвис, подготовь [фото] на документы: формат [35x45/3x4], фон [цвет], освещение, размер файла, печатная раскладка на листе.»
Cat: IMAGE | Documents
Diff: L1 | Tools: photo tools | Web0 Code0 Files1 Vision1 Long0 | Auto 5
Why: требования к фото на документы строгие, но формализуемые
Caps: document photo prep, print layout

### 699 — Слайдшоу из фотографий
«Джарвис, собери слайдшоу из [фото] под [музыка]: порядок, тайминг, переходы, подписи. Сделай видео и превью-кадры.»
Cat: VIDEO | Slideshow
Diff: L2 | Tools: slideshow tools | Web0 Code0 Files1 Vision0 Long1 | Auto 7
Why: слайдшоу — быстрый способ превратить фотосессию в воспоминание
Caps: slideshow creation, music sync

### 700 — Сканирование фотоплёнки
«Джарвис, оцифруй [сканы плёнки/фотоотпечатки]: исправь цвет и контраст, выровняй, убери пыль, добавь метаданные. Разложи по плёнкам и кадрам.»
Cat: IMAGE | Archive
Diff: L2 | Tools: scanning tools | Web0 Code0 Files1 Vision1 Long0 | Auto 7
Why: оцифровка плёнки спасает архивы от физического износа
Caps: film digitization, dust removal, archive tagging

### 701 — Монтаж видео по сценарию
«Джарвис, смонтируй [исходники] по сценарию [сценарий]: порядок клипов, переходы, музыка, титры, тайминг. Сделай черновую версию для правок.»
Cat: VIDEO | Editing
Diff: L3 | Tools: video editors | Web0 Code0 Files1 Vision0 Long1 | Auto 8
Why: монтаж по сценарию превращает часы исходников в историю
Caps: video editing, timeline assembly, story structure

### 702 — Нарезка и обрезка видео
«Джарвис, вырежи из [видео] фрагменты: [интервалы], склей в один файл, добавь плавные переходы на стыках. Проверь отсутствие потерь качества.»
Cat: VIDEO | Editing
Diff: L1 | Tools: ffmpeg | Web0 Code0 Files1 Vision0 Long0 | Auto 6
Why: нарезка — самая частая операция работы с видео
Caps: video cutting, segment joining, transitions

### 703 — Склейка клипов
«Джарвис, склей [клипы] в одно видео: единая громкость, выравнивание цветов, переходы, удаление дублей и пауз.»
Cat: VIDEO | Editing
Diff: L2 | Tools: ffmpeg | Web0 Code0 Files1 Vision0 Long0 | Auto 7
Why: склейка разнородных клипов требует нормализации параметров
Caps: clip merging, audio normalization

### 704 — Субтитры: создание и синхронизация
«Джарвис, создай субтитры для [видео]: расшифруй речь, разбей по таймкодам, убери слова-паразиты. Выдай SRT/VTT и проверь синхронизацию.»
Cat: VIDEO | Subtitles
Diff: L2 | Tools: speech recognition | Web0 Code0 Files1 Vision0 Long1 | Auto 8
Why: субтитры повышают доступность и вовлечённость видео
Caps: subtitle generation, timestamps, speech-to-text

### 705 — Озвучка видео
«Джарвис, озвучь [видео] голосом [голос]: синтез речи по тексту/субтитрам, синхронизация с таймингом, регулировка темпа и эмоций.»
Cat: VIDEO | Voiceover
Diff: L2 | Tools: TTS | Web0 Code0 Files1 Vision0 Long1 | Auto 7
Why: качественная озвучка делает видео пригодным для публикации
Caps: voiceover generation, speech synthesis, lip sync approximation

### 706 — Конвертация форматов видео
«Джарвис, сконвертируй [видео] в [формат/кодек]: настрой битрейт, кадровую частоту, аудио-кодек. Проверь совместимость с [устройство/платформа].»
Cat: VIDEO | Conversion
Diff: L1 | Tools: ffmpeg | Web0 Code0 Files1 Vision0 Long0 | Auto 6
Why: конвертация под платформу — стандартная задача публикации
Caps: video conversion, codec tuning

### 707 — Сжатие видео
«Джарвис, сожми [видео] до [размер/битрейт] с минимальной потерей качества: двухпроходное кодирование, умный битрейт для динамичных сцен. Сравни до/после.»
Cat: PERFORMANCE | Video
Diff: L2 | Tools: ffmpeg, handbrake | Web0 Code0 Files1 Vision0 Long0 | Auto 6
Why: сжатие без контроля качества убивает картинку в динамике
Caps: video compression, bitrate control

### 708 — Запись экрана с веб-камерой
«Джарвис, запиши [урок/демо]: экран + веб-камера в углу, микрофон, режим [картинка в картинке]. Останови по команде и сохрани с нужными настройками.»
Cat: VIDEO | Recording
Diff: L1 | Tools: recording tools | Web0 Code0 Files1 Vision0 Long0 | Auto 7
Why: запись экрана с лицом — основа обучающего контента
Caps: screen+webcam recording, PiP layout

### 709 — Замедление и ускорение
«Джарвис, замедли/ускори [видео] в [N] раз: сохрани звук с коррекцией тона (или замени на музыку), сделай плавный ramping в [интервал].»
Cat: VIDEO | Effects
Diff: L2 | Tools: ffmpeg | Web0 Code0 Files1 Vision0 Long0 | Auto 6
Why: скорость — выразительный приём, если звук не ломается
Caps: speed ramping, time remapping, pitch correction

### 710 — Стабилизация видео
«Джарвис, стабилизируй [трясущееся видео]: сгладь дрожание, сохрани масштаб без потери деталей, обрежь края аккуратно. Покажи сравнение.»
Cat: VIDEO | Enhancement
Diff: L2 | Tools: stabilization | Web0 Code0 Files1 Vision0 Long0 | Auto 6
Why: стабилизация спасает съёмку с рук и на ходу
Caps: video stabilization, motion smoothing

### 711 — Цветокоррекция видео
«Джарвис, скорректируй цвет [видео]: выровняй клипы между собой, примени LUT [стиль], настрой экспозицию и контраст. Проверь на тёмных и светлых сценах.»
Cat: VIDEO | Color
Diff: L2 | Tools: color grading | Web0 Code0 Files1 Vision0 Long0 | Auto 6
Why: единый цвет — то, что отличает любительский монтаж от профессионального
Caps: color grading, lut application, shot matching

### 712 — Зелёный экран: ключевание
«Джарвис, обработай [видео на зелёном фоне]: удали хромакей, сохрани волосы и полупрозрачные зоны, замени фон на [фон]. Проверь края в движении.»
Cat: VIDEO | Effects
Diff: L3 | Tools: chroma key | Web0 Code0 Files1 Vision0 Long0 | Auto 6
Why: хромакей — стандарт продакшена, но края требуют тонкой настройки
Caps: chroma keying, edge refinement, background replacement

### 713 — Титры и карточки
«Джарвис, добавь в [видео] титры, заставку, финальные карточки с [тексты]: стиль, анимация появления, длительность, единый шрифт.»
Cat: VIDEO | Graphics
Diff: L1 | Tools: title tools | Web0 Code0 Files1 Vision0 Long0 | Auto 6
Why: титры задают профессиональный вид и доносят бренд
Caps: title cards, intro/outro design

### 714 — Картинка в картинке
«Джарвис, наложи [второе видео/экран] на [основное]: позиция, размер, рамка, синхронизация звука, переключение раскладки в нужные моменты.»
Cat: VIDEO | Effects
Diff: L2 | Tools: compositing | Web0 Code0 Files1 Vision0 Long0 | Auto 7
Why: PiP — основной формат реакций и обучающих видео
Caps: picture-in-picture, compositing

### 715 — Трекинг объектов и маски
«Джарвис, отследи [объект] в [видео]: трекинг, маска, замена/подсветка объекта по кадрам, стабилизация привязки к объекту.»
Cat: VIDEO | Analysis
Diff: L4 | Tools: tracking tools | Web0 Code0 Files1 Vision1 Long0 | Auto 7
Why: трекинг открывает путь к объектным эффектам и анализу движения
Caps: object tracking, motion masking

### 716 — Извлечение кадров из видео
«Джарвис, вытащи из [видео] кадры: [по таймкодам/каждый N-й кадр], сохрани в [формат], отбери лучшие по резкости и композиции.»
Cat: VIDEO | Extraction
Diff: L1 | Tools: ffmpeg | Web0 Code0 Files1 Vision0 Long0 | Auto 6
Why: кадры из видео — материал для превью, пресс-китов и анализа
Caps: frame extraction, keyframe selection

### 717 — Извлечение аудио из видео
«Джарвис, извлеки аудио из [видео]: формат [mp3/wav], битрейт, нормализация громкости, обрезка по [таймкоды].»
Cat: AUDIO | Extraction
Diff: L0 | Tools: ffmpeg | Web0 Code0 Files1 Vision0 Long0 | Auto 5
Why: аудиодорожка видео нужна для подкастов и цитат
Caps: audio extraction, format conversion

### 718 — Анализ содержимого видео
«Джарвис, проанализируй [видео]: сцены, объекты, люди, текст на экране, смены планов. Составь описание содержания и таймкоды ключевых моментов.»
Cat: VIDEO | Analysis
Diff: L2 | Tools: vision models | Web0 Code0 Files1 Vision1 Long1 | Auto 8
Why: видео без индекса содержимого невозможно искать и переиспользовать
Caps: video understanding, scene detection, content indexing

### 719 — Резюме длинного видео
«Джарвис, сделай резюме [длинное видео]: основные темы, ключевые моменты с таймкодами, выводы. Подходит для быстрого ознакомления.»
Cat: VIDEO | Summaries
Diff: L2 | Tools: summarization | Web0 Code0 Files1 Vision0 Long1 | Auto 8
Why: часовые записи становятся полезными только после сжатия в минуты
Caps: video summarization, key moment extraction

### 720 — Вертикальный формат для соцсетей
«Джарвис, адаптируй [видео] под вертикальный формат [9:16]: перекадрируй с отслеживанием главного объекта, добавь подписи, обрежь под [платформа].»
Cat: VIDEO | Social
Diff: L2 | Tools: reformatting | Web0 Code0 Files1 Vision0 Long0 | Auto 7
Why: вертикальный формат — требование TikTok/Reels/Shorts
Caps: vertical reformatting, safe area adaptation

### 721 — Транскрибация видео в текст
«Джарвис, расшифруй [видео] в текст: раздели по спикерам, добавь таймкоды, убери паразиты, оформи в [формат: стенограмма/конспект].»
Cat: AUDIO | Transcription
Diff: L2 | Tools: speech recognition | Web0 Code0 Files1 Vision0 Long1 | Auto 8
Why: текстовая версия видео ищется, цитируется и анализируется
Caps: transcription, speaker diarization, meeting notes

### 722 — Перевод и озвучка субтитров
«Джарвис, переведи субтитры [видео] на [язык], озвучь переведённый текст голосом [голос] и наложи на видео с сохранением тайминга.»
Cat: VIDEO | Localization
Diff: L3 | Tools: TTS, subtitle tools | Web0 Code0 Files1 Vision0 Long1 | Auto 8
Why: локализация видео открывает зарубежную аудиторию
Caps: video localization, dubbed subtitles

### 723 — Видео из набора фото
«Джарвис, собери видео из [фото] с эффектом Кена Бёрнса: плавные зум и панорамы, музыка, переходы, длительность по [правило].»
Cat: VIDEO | Slideshow
Diff: L2 | Tools: ken burns | Web0 Code0 Files1 Vision0 Long0 | Auto 6
Why: анимация статичных фото оживляет историю в видео
Caps: ken burns effect, photo animation

### 724 — Запись презентации с озвучкой
«Джарвис, запиши [презентация] с моей озвучкой: переключение слайдов по речи, сохранение заметок, экспорт в [формат видео].»
Cat: VIDEO | Recording
Diff: L2 | Tools: recording tools | Web0 Code0 Files1 Vision0 Long0 | Auto 7
Why: записанные презентации работают как готовый курс
Caps: presentation recording, speech-synced slides

### 725 — Подготовка видео для YouTube
«Джарвис, подготовь [видео] к публикации на YouTube: обложка, субтитры, описание с ключевыми словами, теги, таймкоды глав, превью.»
Cat: MARKETING | Video
Diff: L1 | Tools: YouTube tools | Web1 Code0 Files1 Vision0 Long0 | Auto 7
Why: оформление определяет кликабельность не меньше содержания
Caps: youtube packaging, chapter timestamps, thumbnail

### 726 — Организация видеотеки
«Джарвис, организуй [видеотека]: каталог с превью, метаданные (дата, длительность, теги), поиск по содержимому, дедупликация.»
Cat: VIDEO | Archive
Diff: L2 | Tools: media managers | Web0 Code0 Files1 Vision1 Long1 | Auto 8
Why: видеотека без каталога — чёрная дыра, где всё «где-то есть»
Caps: media library management, content tagging

### 727 — Сжатие для мессенджеров
«Джарвис, сожми [видео] для отправки в [мессенджер]: формат, размер под лимит, сохранение приемлемого качества. Проверь воспроизводимость на телефоне.»
Cat: PERFORMANCE | Video
Diff: L1 | Tools: ffmpeg | Web0 Code0 Files1 Vision0 Long0 | Auto 6
Why: видео, которое не влезает в чат, бесполезно
Caps: messenger-ready compression, size targeting

### 728 — Метаданные и обложки видео
«Джарвис, заполни метаданные [видеофайлы]: название, артист, обложка, жанр, год. Сделай превью-картинки и встрои их в файлы.»
Cat: VIDEO | Metadata
Diff: L1 | Tools: metadata tools | Web0 Code0 Files1 Vision0 Long0 | Auto 5
Why: метаданные и обложки — лицо видео в медиаплеерах
Caps: video metadata, embedded artwork

### 729 — Проверка целостности видео
«Джарвис, проверь [видеофайлы] на повреждения: ошибки контейнера, рассинхрон звука, битые кадры. Покажи, какие файлы можно починить, и восстанови их.»
Cat: SECURITY | Video
Diff: L2 | Tools: ffmpeg, validation | Web0 Code0 Files1 Vision0 Long0 | Auto 6
Why: архив, где половина файлов не открывается, — ловушка
Caps: file integrity check, video repair

### 730 — Контроль качества видеопродакшена
«Джарвис, проверь [видео] по чек-листу: резкость, экспозиция, звук, субтитры, маты, логотипы, длительность. Выдай список проблем с таймкодами.»
Cat: VIDEO | QA
Diff: L2 | Tools: QC tools | Web0 Code0 Files1 Vision0 Long0 | Auto 7
Why: дефекты, замеченные после публикации, стоят репутации
Caps: video quality control, defect reporting

### 731 — Поворот и зеркалирование
«Джарвис, исправь ориентацию [видео]: поверни на [угол], отзеркаль для [коррекция селфи], обрежь чёрные поля. Проверь, что звук остался синхронным.»
Cat: VIDEO | Editing
Diff: L0 | Tools: ffmpeg | Web0 Code0 Files1 Vision0 Long0 | Auto 5
Why: кривая ориентация — самый частый дефект мобильной съёмки
Caps: rotation fix, mirroring, black bar removal

### 732 — Loop-видео и GIF
«Джарвис, сделай из [фрагмент видео] зацикленный клип или GIF: бесшовный переход, размер, кадровая частота, палитра для GIF.»
Cat: VIDEO | Effects
Diff: L1 | Tools: ffmpeg, gif tools | Web0 Code0 Files1 Vision0 Long0 | Auto 6
Why: loop-контент — формат мемов и фоновых видео
Caps: seamless loop, gif conversion

### 733 — Умная замена фона видео
«Джарвис, замени фон в [видео] без хромакея: сегментация человека в каждом кадре, стабильные края, новый фон [фон]. Отметь мерцания.»
Cat: VIDEO | Effects
Diff: L3 | Tools: video segmentation | Web0 Code0 Files1 Vision1 Long0 | Auto 7
Why: замена фона без зелёного экрана — востребованная функция стримов
Caps: video background replacement, person segmentation

### 734 — Motion-графика и анимация текста
«Джарвис, создай motion-графику для [видео]: анимированные заголовки, инфографика-анимации, логотип-анимация по [бриф]. Экспортируй с прозрачностью.»
Cat: VIDEO | Graphics
Diff: L3 | Tools: motion tools | Web0 Code0 Files1 Vision0 Long0 | Auto 7
Why: motion-графика повышает удержание и профессионализм
Caps: motion graphics, animated infographics, alpha export

### 735 — Кинематографическая обработка
«Джарвис, придай [видео] кинематографический вид: letterbox, цвет LUT, зерно плёнки, звук с атмосферой. Покажи пример до/после на [кадре].»
Cat: VIDEO | Effects
Diff: L2 | Tools: grading, film emulation | Web0 Code0 Files1 Vision0 Long0 | Auto 6
Why: киноэффекты поднимают восприятие ролика на другой уровень
Caps: cinematic grading, film grain, letterbox

### 736 — Видеообзор продукта
«Джарвис, собери видеообзор [продукт]: сценарий, съёмка/скриншоты, ключевые фичи с акцентами, тайминг под [площадка], CTA в конце.»
Cat: MARKETING | Video
Diff: L2 | Tools: video editors | Web0 Code0 Files1 Vision0 Long1 | Auto 8
Why: видеообзор — самый конвертирующий формат маркетинга продукта
Caps: product video, feature showcase, script-to-video

### 737 — Синхронизация монтажа с музыкой
«Джарвис, смонтируй [клипы] под [трек]: найди биты и такты, поставь смены кадров на сильные доли, подгони длительность под трек.»
Cat: VIDEO | Editing
Diff: L3 | Tools: beat detection | Web0 Code0 Files1 Vision0 Long0 | Auto 7
Why: монтаж в такт — главный признак профессионального клипа
Caps: beat-synced editing, music-driven cuts

### 738 — Видео из слайдов с анимацией
«Джарвис, преврати [слайды] в анимированное видео: появление элементов по плану, зум-эффекты, переходы, фоновая музыка, экспорт в [формат].»
Cat: VIDEO | Presentation
Diff: L2 | Tools: animation tools | Web0 Code0 Files1 Vision0 Long0 | Auto 7
Why: анимированные слайды удерживают внимание лучше статичных
Caps: slide animation, presentation-to-video

### 739 — Водяной знак на видео
«Джарвис, добавь на [видео] водяной знак [лого/текст]: позиция, размер, прозрачность, появление по [интервалам]. Пакетная обработка для [папка].»
Cat: SECURITY | Video
Diff: L1 | Tools: ffmpeg overlay | Web0 Code0 Files1 Vision0 Long0 | Auto 6
Why: водяные знаки защищают видео от перепубликации
Caps: video watermarking, brand protection

### 740 — Мульти-аудиодорожки
«Джарвис, собери [видео] с несколькими аудиодорожками: оригинал, перевод, без музыки — с переключением. Проверь синхронизацию всех дорожек.»
Cat: VIDEO | Audio
Diff: L3 | Tools: ffmpeg | Web0 Code0 Files1 Vision0 Long0 | Auto 7
Why: многодорожное аудио — требование стримингов и кино
Caps: multi-track audio, language tracks, mixdown
---

### 741 — Редактирование аудио
«Джарвис, отредактируй [аудио]: убери щелчки, дыхание, паузы, оговорки. Склей получившиеся фрагменты, выровняй уровень. Покажи список изменений.»
Cat: AUDIO | Editing
Diff: L1 | Tools: audio editors | Web0 Code0 Files1 Vision0 Long0 | Auto 7
Why: чистка речи — первый шаг к качественному подкасту или уроку
Caps: audio editing, speech cleanup, gap removal

### 742 — Обрезка и склейка аудио
«Джарвис, вырежи из [аудио] фрагменты [интервалы], склей в нужном порядке, добавь переходы с перекрёстным затуханием. Проверь стыки на слух/волну.»
Cat: AUDIO | Editing
Diff: L1 | Tools: audio tools | Web0 Code0 Files1 Vision0 Long0 | Auto 6
Why: нарезка — базовая операция любого аудио-монтажа
Caps: audio cutting, crossfade, assembly

### 743 — Нормализация громкости
«Джарвис, нормализуй громкость [аудио] до [LUFS/dB]: выровняй уровни между фрагментами, ограничь пики без искажений.»
Cat: AUDIO | Enhancement
Diff: L1 | Tools: loudness tools | Web0 Code0 Files1 Vision0 Long0 | Auto 6
Why: непостоянная громкость — главная жалоба слушателей подкастов
Caps: loudness normalization, peak limiting

### 744 — Шумоподавление
«Джарвис, убери шум с [аудио]: фоновый гул, шипение, клики, помехи. Сохрани естественность голоса, покажи спектр до/после.»
Cat: AUDIO | Enhancement
Diff: L2 | Tools: noise reduction | Web0 Code0 Files1 Vision0 Long0 | Auto 6
Why: шум — главный враг разборчивости речи
Caps: noise reduction, spectral cleanup

### 745 — Эквалайзер и тональный баланс
«Джарвис, настрой эквалайзер для [аудио]: убери резонансы, подчеркни присутствие голоса, выровняй тональный баланс под [задача].»
Cat: AUDIO | Enhancement
Diff: L2 | Tools: EQ | Web0 Code0 Files1 Vision0 Long0 | Auto 6
Why: правильный EQ делает голос разборчивым на любых колонках
Caps: equalization, resonance removal, voice presence

### 746 — Конвертация аудиоформатов
«Джарвис, сконвертируй [аудио] в [формат]: битрейт, частота дискретизации, каналы. Объясни потери и выбери настройки под [назначение].»
Cat: AUDIO | Conversion
Diff: L0 | Tools: converters | Web0 Code0 Files1 Vision0 Long0 | Auto 5
Why: конвертация без понимания потерь портит звук навсегда
Caps: audio conversion, sample rate handling

### 747 — Подготовка аудио для подкаста
«Джарвис, подготовь [эпизод] для подкаст-платформ: громкость по стандарту, удаление пауз, ID3-теги, обложка, главы. Проверь на [платформа].»
Cat: AUDIO | Podcast
Diff: L2 | Tools: podcast tools | Web0 Code0 Files1 Vision0 Long0 | Auto 7
Why: стандарты платформ (громкость, теги) решают, как звучит эпизод
Caps: podcast mastering, chapter markers, id3 tagging

### 748 — Удаление вокала (караоке-версия)
«Джарвис, сделай караоке-версию [трек]: удали вокал по центру канала, сохрани музыку, подай инструментал и оригинал для сравнения.»
Cat: AUDIO | Effects
Diff: L2 | Tools: vocal removal | Web0 Code0 Files1 Vision0 Long0 | Auto 5
Why: караоке-версии нужны для пения, обучения и ремиксов
Caps: vocal removal, stem separation

### 749 — Разделение на стемы
«Джарвис, раздели [трек] на стемы: вокал, ударные, бас, остальные инструменты. Отдай каждый как отдельный файл и проверь качество разделения.»
Cat: AUDIO | Analysis
Diff: L3 | Tools: stem separation | Web0 Code0 Files1 Vision0 Long0 | Auto 7
Why: стемы открывают ремиксы и реставрацию старых записей
Caps: stem separation, source isolation

### 750 — Запись аудио с микрофона
«Джарвис, запиши [голос/звук] с микрофона: настрой уровни, помехи, сохранение в [формат]. Сделай тестовую запись и проверь качество.»
Cat: AUDIO | Recording
Diff: L0 | Tools: recording | Web0 Code0 Files1 Vision0 Long0 | Auto 5
Why: запись с правильными уровнями избавляет от перезаписей
Caps: audio recording, level tuning, mic checks

### 751 — Сборка эпизода подкаста
«Джарвис, собери эпизод подкаста [тема]: интро, интервью/монолог, вставки, музыкальные отбивки, аутро, планирование длительности.»
Cat: AUDIO | Podcast
Diff: L2 | Tools: audio editors | Web0 Code0 Files1 Vision0 Long1 | Auto 7
Why: структура эпизода удерживает слушателя до конца
Caps: podcast assembly, episode structure

### 752 — Интро и аутро подкаста
«Джарвис, создай интро и аутро для [подкаст/канал]: джингл, озвучка, музыка, длительность [N] секунд, единый стиль.»
Cat: AUDIO | Branding
Diff: L2 | Tools: audio tools, TTS | Web0 Code0 Files1 Vision0 Long0 | Auto 6
Why: узнаваемое интро — бренд, который слушатель ждёт
Caps: audio branding, jingle design, intro/outro

### 753 — Рингтон из трека
«Джарвис, сделай рингтон из [трек]: выбери лучший фрагмент, обрежь до [N] секунд, нормализуй, экспортируй в [форматы].»
Cat: AUDIO | Creation
Diff: L0 | Tools: audio tools | Web0 Code0 Files1 Vision0 Long0 | Auto 5
Why: рингтоны — быстрая персонализация телефона
Caps: ringtone creation, excerpt selection

### 754 — Спектральный анализ аудио
«Джарвис, проанализируй [аудио] спектрально: частотный состав, резонансы, клиппинг, качество записи. Покажи спектрограмму и объясни находки.»
Cat: AUDIO | Analysis
Diff: L2 | Tools: spectral tools | Web0 Code0 Files1 Vision0 Long0 | Auto 7
Why: спектрограмма раскрывает дефекты, не слышимые на слух
Caps: spectral analysis, clipping detection, quality assessment

### 755 — Проверка целостности аудиофайлов
«Джарвис, проверь [аудиофайлы] на повреждения и потери: ошибки заголовков, обрывы, несоответствие длительности. Почини восстановимые.»
Cat: SECURITY | Audio
Diff: L2 | Tools: validation tools | Web0 Code0 Files1 Vision0 Long0 | Auto 6
Why: архив со скрыто битыми файлами подводит в самый нужный момент
Caps: audio integrity, repair, header fixes

### 756 — Метаданные и теги аудио
«Джарвис, заполни теги [аудиофайлы]: название, исполнитель, альбом, обложка, жанр, номер трека, композитор. Сделай пакетно для [папка].»
Cat: AUDIO | Metadata
Diff: L1 | Tools: taggers | Web0 Code0 Files1 Vision0 Long0 | Auto 6
Why: корректные теги — единственный способ найти трек в библиотеке
Caps: audio tagging, cover art embedding

### 757 — Пакетная обработка аудио
«Джарвис, обработай [папка с аудио] пакетно: [нормализация, конвертация, теги, тишина в конце]. Работай параллельно, собери отчёт об ошибках.»
Cat: AUDIO | Batch
Diff: L2 | Tools: batch tools | Web0 Code0 Files1 Vision0 Long0 | Auto 8
Why: пакетная обработка аудиотек — экономия часов ручной работы
Caps: batch audio processing, bulk normalization

### 758 — Битрейт и качество кодирования
«Джарвис, перекодируй [аудио] с оптимальным битрейтом: [VBR/CBR], частота [кГц], сохрани прозрачность. Объясни разницу для [слух/архив/стриминг].»
Cat: AUDIO | Conversion
Diff: L1 | Tools: encoders | Web0 Code0 Files1 Vision0 Long0 | Auto 5
Why: лишний битрейт — зря потраченное место, малый — потерянный звук
Caps: encoding optimization, bitrate choice

### 759 — Изменение скорости без искажений
«Джарвис, ускорь [аудио] в [N] раз с сохранением тона (или наоборот): для конспектов, саунд-дизайна, изучения языка.»
Cat: AUDIO | Effects
Diff: L1 | Tools: time stretch | Web0 Code0 Files1 Vision0 Long0 | Auto 6
Why: time-stretch с сохранением тона — стандартный инструмент обучения
Caps: time stretching, pitch preservation

### 760 — Стерео, моно и пространственный звук
«Джарвис, приведи [аудио] к [стерео/моно/пространственному]: баланс каналов, ширина стереобазы, mid/side обработка, совместимость с моно.»
Cat: AUDIO | Effects
Diff: L2 | Tools: channel tools | Web0 Code0 Files1 Vision0 Long0 | Auto 6
Why: неправильные каналы ломают воспроизведение на ряде устройств
Caps: channel conversion, stereo width, mono compatibility

### 761 — Изменение тембра голоса
«Джарвис, измени тембр [голос/аудио]: ниже/выше, роботизация, радио-эффект, для [персонаж/контент]. Сохрани разборчивость.»
Cat: AUDIO | Effects
Diff: L1 | Tools: pitch/formant | Web0 Code0 Files1 Vision0 Long0 | Auto 5
Why: обработка тембра — материал для анимаций и творчества
Caps: pitch shifting, formant control, voice effects

### 762 — Сведение нескольких дорожек
«Джарвис, сведи [дорожки] в один микс: громкости, панорама, эквализация по частотам, компрессия. Дай две версии: чистую и ограниченную по громкости.»
Cat: AUDIO | Mixing
Diff: L3 | Tools: DAW | Web0 Code0 Files1 Vision0 Long0 | Auto 7
Why: сведение — искусство баланса, и каждая дорожка требует места
Caps: mixing, panning, frequency carving, compression

### 763 — Мастеринг готового трека
«Джарвис, отмастерингь [трек]: финальная громкость [LUFS], ограничитель, стерео-расширение, выравнивание с [референс]. Проверь на разных системах.»
Cat: AUDIO | Mastering
Diff: L3 | Tools: mastering chain | Web0 Code0 Files1 Vision0 Long0 | Auto 6
Why: мастеринг делает трек конкурентоспособным на стримингах
Caps: mastering, loudness targets, reference matching

### 764 — Синхронизация аудио с видео
«Джарвис, синхронизируй [аудио] с [видео]: выровняй по [реплике/аплодисментам], компенсируй задержку, проверь по губам в [кадрах].»
Cat: AUDIO | Sync
Diff: L2 | Tools: sync tools | Web0 Code0 Files1 Vision0 Long0 | Auto 7
Why: рассинхрон звука разрушает восприятие видео мгновенно
Caps: audio-video sync, drift compensation

### 765 — Караоке-сопровождение
«Джарвис, сделай караоке [трек] с текстом: удали вокал, добавь субтитры с подсветкой слов в такт, собери видео или аудио с таймкодами.»
Cat: ENTERTAINMENT | Audio
Diff: L3 | Tools: karaoke tools | Web0 Code0 Files1 Vision0 Long0 | Auto 7
Why: караоке с подсветкой текста — готовый формат вечеринки
Caps: karaoke track, lyric sync, word highlighting

### 766 — Создание звуковых эффектов
«Джарвис, создай звуковой эффект [описание: шаги, дверь, sci-fi]: синтез, слои, обработка, подходящая длина и формат для [видео/игра/UI].»
Cat: AUDIO | SFX
Diff: L2 | Tools: synth, effects | Web0 Code0 Files1 Vision0 Long0 | Auto 7
Why: уникальные SFX — часть бренда и атмосферы продукта
Caps: sound design, sfx synthesis, foley replacement

### 767 — Фоли и шумовая атмосфера
«Джарвис, создай фоли-дорожку для [видео]: шаги, одежда, предметы, атмосфера локации [описание]. Синхронизируй с действиями на экране.»
Cat: AUDIO | SFX
Diff: L3 | Tools: foley tools | Web0 Code0 Files1 Vision0 Long0 | Auto 7
Why: фоли оживляет видео, которое без него кажется «мёртвым»
Caps: foley recording, ambience design

### 768 — Аудио для игр и приложений
«Джарвис, подготовь аудио для [игра/приложение]: UI-звуки, события, музыкальные петли, адаптивные слои. Настрой форматы и громкости под движок [движок].»
Cat: AUDIO | Game
Diff: L3 | Tools: audio middleware | Web0 Code0 Files1 Vision0 Long0 | Auto 7
Why: адаптивный звук — часть геймплея, а не украшение
Caps: game audio, ui sounds, adaptive music

### 769 — Определение трека «что играет»
«Джарвис, определи, что за музыка/песня в [аудио/записи]: распознай по фрагменту, найди исполнителя и альбом, предложи похожие треки.»
Cat: AUDIO | Recognition
Diff: L1 | Tools: audio fingerprinting | Web0 Code0 Files1 Vision0 Long0 | Auto 5
Why: распознавание музыки из записи — повседневная суперспособность
Caps: music recognition, fingerprinting

### 770 — Организация музыкальной библиотеки
«Джарвис, организуй [музыкальная библиотека]: теги, обложки, дубликаты, битые файлы, плейлисты по жанрам/настроению. Отчёт о проделанном.»
Cat: AUDIO | Archive
Diff: L2 | Tools: library managers | Web0 Code0 Files1 Vision0 Long0 | Auto 7
Why: библиотека без порядка превращает музыку в шум
Caps: music library organization, dedup, playlist generation

### 771 — Генерация музыки по описанию
«Джарвис, сгенерируй музыку: [настроение, жанр, темп, длительность, инструменты]. Дай несколько вариантов и сведи лучший в полноценный трек.»
Cat: MUSIC | Generation
Diff: L2 | Tools: music models | Web1 Code0 Files1 Vision0 Long0 | Auto 7
Why: генеративная музыка закрывает потребность в авторском саунде
Caps: music generation, mood control, genre adherence

### 772 — Сочинение мелодии
«Джарвис, сочини мелодию по [описание/стихотворение]: тема, гармония, аранжировка. Покажи ноты/табулатуру и сыграй через синтез.»
Cat: MUSIC | Composition
Diff: L2 | Tools: composition tools | Web0 Code0 Files1 Vision0 Long0 | Auto 7
Why: мелодия — ядро песни, и ИИ помогает преодолеть пустой лист
Caps: melody composition, harmony, motif development

### 773 — Аранжировка трека
«Джарвис, сделай аранжировку [идея/мелодия]: структура (куплет/припев), слои инструментов, динамика, переходы. Покажи схему аранжировки.»
Cat: MUSIC | Arrangement
Diff: L3 | Tools: DAW | Web0 Code0 Files1 Vision0 Long0 | Auto 7
Why: аранжировка решает, запомнится ли песня
Caps: arrangement design, dynamics mapping, instrumentation

### 774 — Ноты и партитура
«Джарвис, запиши [мелодия/трек] нотами: партитура для [инструменты], тональность, аппликатура, экспорт в [PDF/MIDI/MusicXML].»
Cat: MUSIC | Notation
Diff: L2 | Tools: notation software | Web0 Code0 Files1 Vision0 Long0 | Auto 7
Why: нотная запись делает музыку передаваемой другим музыкантам
Caps: score engraving, midi export, transposition

### 775 — Анализ музыкального трека
«Джарвис, проанализируй [трек]: жанр, темп, тональность, структура, громкость по секциям, стилевые приёмы. Объясни, почему трек звучит так.»
Cat: MUSIC | Analysis
Diff: L2 | Tools: analysis tools | Web0 Code0 Files1 Vision0 Long0 | Auto 7
Why: разбор трека — лучший способ учиться на чужом мастерстве
Caps: track analysis, key/tempo detection, structure mapping

### 776 — Сведение любительского микса
«Джарвис, помоги свести [микс]: найди конфликты частот, проблемы динамики, предложи конкретные шаги (EQ, компрессия) с примерами параметров.»
Cat: MUSIC | Mixing
Diff: L3 | Tools: DAW analysis | Web0 Code0 Files1 Vision0 Long0 | Auto 7
Why: объективный совет заменяет часы проб и ошибок в наушниках
Caps: mix critique, frequency conflict resolution, chain suggestions

### 777 — Музыка для видео по настроению
«Джарвис, подбери/сгенерируй музыку для [видео] по настроению [настроение] и длительности [длительность]: без правовых рисков, с точками смены секций.»
Cat: MUSIC | Licensing
Diff: L1 | Tools: music libraries, models | Web1 Code0 Files1 Vision0 Long0 | Auto 7
Why: музыка с непонятными правами — риск демонетизации и исков
Caps: licensed music selection, mood matching

### 778 — Экспертная оценка трека
«Джарвис, оцени [демо/трек] по чек-листу продюсера: идея, структура, микс, мастеринг, продакшн-ценность. Дай конкретные шаги улучшения с приоритетами.»
Cat: MUSIC | QA
Diff: L2 | Tools: listening frameworks | Web0 Code0 Files1 Vision0 Long0 | Auto 7
Why: структурированная обратная связь быстрее развивает музыканта
Caps: music critique, production checklist, improvement plan

### 779 — Поиск похожей музыки
«Джарвис, найди музыку, похожую на [трек/исполнитель]: по жанру, настроению, структуре, с учётом лицензий. Составь плейлист-аналог.»
Cat: MUSIC | Discovery
Diff: L1 | Tools: discovery APIs | Web1 Code0 Files0 Vision0 Long0 | Auto 5
Why: поиск «как этот трек» — частая задача диджеев и режиссёров
Caps: music discovery, similarity matching

### 780 — Звуки уведомлений
«Джарвис, создай набор звуков уведомлений для [приложение]: разные события, единый стиль, короткие, без раздражения, форматы [форматы].»
Cat: AUDIO | UI
Diff: L2 | Tools: synth tools | Web0 Code0 Files1 Vision0 Long0 | Auto 6
Why: хорошие уведомления слышны, но не раздражают
Caps: notification sounds, ui audio design

### 781 — Озвучка текста выбранным голосом
«Джарвис, озвучь [текст] голосом [голос/язык/акцент]: расставь ударения, паузы, эмоции. Дай версии с разным темпом для сравнения.»
Cat: SPEECH | TTS
Diff: L1 | Tools: TTS | Web0 Code0 Files1 Vision0 Long0 | Auto 7
Why: естественная озвучка — базовая суперспособность любого голосового ассистента
Caps: text-to-speech, prosody control, voice selection

### 782 — Создание голосового персонажа
«Джарвис, создай голос для [персонаж/бренд]: подбери параметры (тембр, возраст, характер), клонируй/синтезируй по образцу [образец], протестируй на фразах.»
Cat: SPEECH | Voice
Diff: L3 | Tools: voice cloning | Web0 Code0 Files1 Vision0 Long0 | Auto 7
Why: узнаваемый голос — часть идентичности бренда или персонажа
Caps: voice design, voice cloning, voice identity

### 783 — Речь на другом языке с акцентом
«Джарвис, озвучь [текст] на [язык] с [акцент/диалект]: правильное произношение, интонация региона, адаптация имён.»
Cat: SPEECH | TTS
Diff: L2 | Tools: multilingual TTS | Web0 Code0 Files1 Vision0 Long0 | Auto 7
Why: региональная озвучка повышает доверие локальной аудитории
Caps: multilingual synthesis, accent rendering

### 784 — Анализ устной речи
«Джарвис, проанализируй [запись речи]: темп, паузы, слова-паразиты, громкость, интонационные паттерны. Дай рекомендации по улучшению подачи.»
Cat: SPEECH | Analysis
Diff: L2 | Tools: speech analysis | Web0 Code0 Files1 Vision0 Long0 | Auto 7
Why: объективные метрики речи — первый шаг к уверенному выступлению
Caps: speech analytics, filler detection, pace analysis

### 785 — Тренировка выступления с ИИ-слушателем
«Джарвис, проведи со мной тренировку [выступление/собеседование]: задавай вопросы как [роль], реагируй на ответы, дай обратную связь по содержанию и форме.»
Cat: SPEECH | Training
Diff: L1 | Tools: conversation AI | Web0 Code0 Files1 Vision0 Long0 | Auto 7
Why: репетиция с незнакомцем невозможна всегда, с ИИ — доступна
Caps: presentation rehearsal, interview practice, feedback

### 786 — Разбор аргументации и дебатов
«Джарвис, разбери [текст/запись дебатов]: сильные и слабые аргументы, логические ошибки, риторические приёмы. Дай стратегию контраргументации.»
Cat: SPEECH | Analysis
Diff: L2 | Tools: argument analysis | Web0 Code0 Files1 Vision0 Long1 | Auto 7
Why: разбор аргументации тренирует мышление и переговорные навыки
Caps: argument mapping, fallacy detection, counter-argument strategy

### 787 — Эмоциональный анализ голоса
«Джарвис, проанализируй эмоции в [запись голоса]: уверенность, стресс, усталость, вовлечённость. Свяжи с содержанием и таймкодами.»
Cat: SPEECH | Analysis
Diff: L3 | Tools: emotion models | Web0 Code0 Files1 Vision0 Long0 | Auto 6
Why: эмоциональные паттерны помогают в продажах и поддержке
Caps: emotion recognition, vocal biomarkers, stress detection

### 788 — Расшифровка и оформление интервью
«Джарвис, расшифруй [интервью]: раздели по говорящим, добавь таймкоды, оформи вопросы/ответы, выдели ключевые цитаты.»
Cat: SPEECH | Transcription
Diff: L2 | Tools: STT | Web0 Code0 Files1 Vision0 Long1 | Auto 8
Why: интервью без расшифровки почти не поддаётся работе с ним
Caps: interview transcription, speaker labels, quote extraction

### 789 — Разделение говорящих в записи
«Джарвис, раздели [запись] на голоса участников: диаризация, назначь метки (Спикер 1/2), выровняй громкости, выгрузи отдельными дорожками.»
Cat: SPEECH | Analysis
Diff: L2 | Tools: diarization | Web0 Code0 Files1 Vision0 Long0 | Auto 7
Why: диаризация — фундамент для стенограмм и конспектов встреч
Caps: speaker diarization, voice separation

### 790 — Конспект лекции с диктофона
«Джарвис, преврати [запись лекции] в конспект: расшифровка, структура по темам, ключевые определения, задачи на дом, список вопросов.»
Cat: LEARNING | Speech
Diff: L2 | Tools: STT + summarization | Web0 Code0 Files1 Vision0 Long1 | Auto 8
Why: конспект из лекции переиспользуем и пересылаем
Caps: lecture summarization, study notes, definition extraction

### 791 — Голосовые команды для системы
«Джарвис, настрой голосовые команды: [команда -> действие]. Создай распознавание, триггеры, подтверждения для опасных действий, отчёты об ошибках.»
Cat: VOICE | Automation
Diff: L3 | Tools: voice control | Web0 Code0 Files1 Vision0 Long0 | Auto 8
Why: голосовое управление — естественный интерфейс для рук и глаз
Caps: voice commands, wake word, action mapping

### 792 — Голосовое управление домом/устройствами
«Джарвис, подключи голосовое управление к [устройства/умный дом]: команды, сценарии, расписания, откаты при сбоях.»
Cat: VOICE | IoT
Diff: L3 | Tools: home automation | Web1 Code0 Files1 Vision0 Long0 | Auto 8
Why: голос — самый быстрый интерфейс для рутинных действий дома
Caps: voice IoT control, scene triggers, automation safety

### 793 — Эмоциональная выразительность синтеза
«Джарвис, озвучь [текст] с эмоцией [радость/волнение/серьёзность]: управление скоростью, паузами, интонацией. Сравни нейтральную и эмоциональную версии.»
Cat: SPEECH | TTS
Diff: L2 | Tools: expressive TTS | Web0 Code0 Files1 Vision0 Long0 | Auto 6
Why: эмоция в голосе — то, что отличает озвучку от диктофона
Caps: expressive speech, emotion rendering

### 794 — Чтение документов вслух
«Джарвис, читай [документ/статья] вслух: правильное произношение терминов, паузы на абзацах, скорость [N]. Управление: пауза, назад, повтор.»
Cat: VOICE | Reading
Diff: L1 | Tools: TTS | Web0 Code0 Files1 Vision0 Long0 | Auto 6
Why: прослушивание — параллельный канал потребления документов
Caps: document reading, hands-free consumption

### 795 — Аудиокнига из текста
«Джарвис, собери аудиокнигу из [текст]: озвучка по главам, интонация повествования, главы-закладки, обложка, метаданные, нарезка на части.»
Cat: AUDIO | Books
Diff: L3 | Tools: TTS + metadata | Web0 Code0 Files1 Vision0 Long0 | Auto 8
Why: аудиоформат расширяет аудиторию книги многократно
Caps: audiobook production, chapter narration, accessibility

### 796 — Голос для навигации
«Джарвис, подготовь голосовые подсказки для [навигация/навигационное приложение]: короткие команды, названия [улиц/мест], естественное произношение, уровни громкости.»
Cat: VOICE | TTS
Diff: L2 | Tools: TTS | Web0 Code0 Files1 Vision0 Long0 | Auto 6
Why: навигационные подсказки должны пониматься с полуслова
Caps: navigation voice, prompt design

### 797 — Диалоговый режим с голосом
«Джарвис, перейди в голосовой диалог: слушай, понимай, отвечай голосом, держи контекст беседы, переспрашивай при неоднозначности.»
Cat: VOICE | Conversation
Diff: L2 | Tools: STT + LLM + TTS | Web0 Code0 Files0 Vision0 Long1 | Auto 9
Why: живой диалог — высшая форма взаимодействия с ассистентом
Caps: conversational voice, context retention, barge-in

### 798 — Языковая практика с ИИ
«Джарвис, поговори со мной на [язык] на уровне [уровень]: исправляй ошибки, объясняй, подбирай темы, веди учёт прогресса.»
Cat: LEARNING | Voice
Diff: L1 | Tools: conversational AI | Web0 Code0 Files1 Vision0 Long1 | Auto 7
Why: разговорная практика — то, чего не хватает в языковых курсах
Caps: language practice, error correction, fluency coaching

### 799 — Субтитры в реальном времени
«Джарвис, включай живые субтитры для [встреча/вебинар]: распознавай речь, выводи текст с задержкой [N] секунд, исправляй термины из [словарь].»
Cat: SPEECH | Live
Diff: L3 | Tools: live STT | Web0 Code0 Files1 Vision0 Long0 | Auto 8
Why: живые субтитры — доступность для слабослышащих и шумных комнат
Caps: live captioning, real-time STT, glossary injection

### 800 — Локальный голосовой ассистент
«Джарвис, разверни голосового ассистента локально: распознавание, синтез, интеграция с [сервисы], приватный режим без облака, обработка ошибок.»
Cat: VOICE | System
Diff: L4 | Tools: local STT/TTS | Web0 Code0 Files1 Vision0 Long0 | Auto 8
Why: локальная обработка голоса сохраняет приватность разговоров
Caps: local voice assistant, offline speech, privacy-first voice

### 801 — Планирование киновечера
«Джарвис, спланируй киновечер для [N] человек: подбор фильмов по вкусам [предпочтения], порядок, закуски, тайминг, вариант для детей/взрослых.»
Cat: ENTERTAINMENT | Planning
Diff: L0 | Tools: movie APIs | Web1 Code0 Files1 Vision0 Long0 | Auto 6
Why: вечер фильмов без споров о выборе начинается с плана
Caps: movie night planning, taste matching

### 802 — Подбор фильма/сериала
«Джарвис, подбери фильмы/сериалы: по [настроение/жанр/эпоха], объясни, почему подходит, укажи возрастной рейтинг и где смотреть [платформы].»
Cat: ENTERTAINMENT | Discovery
Diff: L0 | Tools: movie databases | Web1 Code0 Files1 Vision0 Long0 | Auto 5
Why: рекомендация с объяснением работает лучше алгоритма-чёрного ящика
Caps: content recommendation, taste reasoning

### 803 — Викторины и квизы
«Джарвис, проведи викторину на [тема]: [N] вопросов с уровнями сложности, таймер, подсчёт очков, объяснение правильных ответов.»
Cat: ENTERTAINMENT | Games
Diff: L0 | Tools: quiz generation | Web0 Code0 Files1 Vision0 Long0 | Auto 7
Why: квиз — лёгкий способ учить и развлекать одновременно
Caps: quiz generation, difficulty calibration

### 804 — Ведение настольной игры
«Джарвис, будь ведущим [настольная игра]: правила, подсчёт очков, разрешение споров по правилам, таймер ходов, сюрпризы по сценарию.»
Cat: ENTERTAINMENT | Games
Diff: L1 | Tools: game logic | Web0 Code0 Files1 Vision0 Long0 | Auto 7
Why: ИИ-ведущий снимает нагрузку с участников и ускоряет игру
Caps: game mastering, scorekeeping, rules arbitration

### 805 — Кроссворды и головоломки
«Джарвис, составь кроссворд/судоку/головоломку: тема [тема], сложность [уровень], сетка, подсказки, проверка решений.»
Cat: ENTERTAINMENT | Puzzles
Diff: L1 | Tools: puzzle generation | Web0 Code0 Files1 Vision0 Long0 | Auto 6
Why: генерация головоломок — мгновенный контент для досуга и печати
Caps: puzzle generation, crossword, sudoku

### 806 — Плейлист под настроение
«Джарвис, собери плейлист под [настроение/ситуация: спорт, работа, дорога] на [длительность]: подбор треков, логика последовательности, обложка и название.»
Cat: MUSIC | Playlists
Diff: L0 | Tools: music APIs | Web1 Code0 Files0 Vision0 Long0 | Auto 6
Why: плейлист с драматургией — продукт, а не случайный набор треков
Caps: playlist curation, mood sequencing

### 807 — Спорт: расписание и результаты
«Джарвис, отслеживай [команда/турнир]: расписание матчей, результаты, таблицы, новости, напоминания. Собери утреннюю сводку.»
Cat: SPORTS | Monitoring
Diff: L0 | Tools: sports APIs | Web1 Code0 Files0 Vision0 Long0 | Auto 7
Why: актуальная спортивная сводка экономит время просмотра десятка сайтов
Caps: sports tracking, schedule alerts, standings

### 808 — Шутки и юмор по теме
«Джарвис, придумай [N] шуток/анекдотов на тему [тема]: разные стили (ирония, каламбур, абсурд), с объяснением механики юмора для [аудитория].»
Cat: ENTERTAINMENT | Humor
Diff: L0 | Tools: humor generation | Web0 Code0 Files1 Vision0 Long0 | Auto 5
Why: юмор по теме оживляет выступления и контент
Caps: humor generation, audience calibration

### 809 — Объяснение фокусов и иллюзий
«Джарвис, объясни [фокус/иллюзия]: как это устроено, как повторить, какие требуются навыки и реквизит, как избежать разоблачения.»
Cat: ENTERTAINMENT | Knowledge
Diff: L1 | Tools: knowledge | Web1 Code0 Files0 Vision0 Long0 | Auto 5
Why: понимание механики иллюзий развивает внимательность к восприятию
Caps: illusion explanation, skill guidance

### 810 — Интерактивные истории
«Джарвис, веди интерактивную историю [жанр/сеттинг]: я выбираю действия, ты развиваешь сюжет, держишь консистентность мира, последствия решений.»
Cat: ENTERTAINMENT | Stories
Diff: L1 | Tools: narrative AI | Web0 Code0 Files1 Vision0 Long1 | Auto 8
Why: интерактивные истории — живое развлечение, которое никогда не повторяется
Caps: interactive fiction, world consistency, branching narrative

### 811 — Стратегия в игре
«Джарвис, помоги со стратегией в [игра]: разбери текущую ситуацию [описание], предложи план на [этап], объясни альтернативы и риски.»
Cat: GAMES | Strategy
Diff: L1 | Tools: game knowledge | Web1 Code0 Files1 Vision0 Long0 | Auto 6
Why: стратегический совет ускоряет прогресс и обучение игре
Caps: game strategy, decision analysis

### 812 — Гайды и прохождение
«Джарвис, составь гайд/прохождение [игра/уровень]: пошагово, с секретами, боссами, альтернативными путями, сложностями для [стиль игры].»
Cat: GAMES | Guides
Diff: L1 | Tools: game databases | Web1 Code0 Files1 Vision0 Long0 | Auto 6
Why: качественный гайд экономит часы проб и ошибок
Caps: game guide, walkthrough, secrets

### 813 — Настройка игры под себя
«Джарвис, помоги настроить [игра]: графика под [железо], управление, чувствительность, специальные возможности, моды [список]. Проверь стабильность FPS.»
Cat: GAMES | Config
Diff: L1 | Tools: config analysis | Web1 Code0 Files1 Vision0 Long0 | Auto 6
Why: правильная настройка меняет и комфорт, и производительность
Caps: game tuning, graphics optimization, accessibility

### 814 — Генерация игрового контента
«Джарвис, сгенерируй для [игра/кампания]: квесты, NPC, диалоги, предметы, лор, случайные события — по [сеттинг/баланс]. Оформи в [формат].»
Cat: GAMES | Content
Diff: L2 | Tools: content generation | Web0 Code0 Files1 Vision0 Long0 | Auto 8
Why: процедурный контент продлевает жизнь любой кампании
Caps: game content generation, quest design, lore building

### 815 — Создание простой игры
«Джарвис, создай игру [концепт] на [технология]: механика, уровни, спрайты/ассеты, звук, сохранение, билд. Покажи и дай поиграть.»
Cat: GAMES | Development
Diff: L4 | Tools: game engines | Web0 Code1 Files1 Vision0 Long1 | Auto 9
Why: прототип игры — лучший способ проверить идею за день
Caps: game development, prototype, playable build

### 816 — Балансировка игровых механик
«Джарвис, проанализируй баланс [механики/числа]: математическая модель, точки поломки, «мёртвые» стратегии, предложи правки с обоснованием.»
Cat: GAMES | Balance
Diff: L3 | Tools: game math | Web0 Code0 Files1 Vision0 Long1 | Auto 7
Why: сломанный баланс убивает игру быстрее любых багов
Caps: game balance, meta analysis, numeric modeling

### 817 — Вероятности в играх
«Джарвис, посчитай [вероятности/шансы] для [ситуация в игре/лотерея/казино]: формулы, симуляции, ожидаемые значения. Объясни, как это влияет на решения.»
Cat: SCIENCE | Probability
Diff: L2 | Tools: probability, Monte Carlo | Web0 Code0 Files1 Vision0 Long0 | Auto 7
Why: понимание вероятностей защищает от иррациональных решений
Caps: probability calculation, monte carlo, expected value

### 818 — Генерация RPG-персонажа
«Джарвис, создай персонажа для [система RPG]: раса/класс, характеристики, бэкстори, мотивация, крючки для сюжета, способы отыгрыша.»
Cat: GAMES | RPG
Diff: L1 | Tools: character tools | Web0 Code0 Files1 Vision0 Long0 | Auto 7
Why: живой персонаж — половина удовольствия от настольной RPG
Caps: character creation, backstory, roleplay hooks

### 819 — ИИ-мастер настольной RPG
«Джарвис, будь мастером [настольная RPG] для [N] игроков: веди сюжет, бросай кубы, управляй NPC, реагируй на действия игроков, сохраняй консистентность мира.»
Cat: GAMES | RPG
Diff: L2 | Tools: RPG AI | Web0 Code0 Files1 Vision0 Long1 | Auto 8
Why: ИИ-мастер позволяет играть в RPG без постоянного ведущего
Caps: rpg dungeon mastering, world simulation, dice handling

### 820 — Киберспорт: анализ игры
«Джарвис, проанализируй [запись/реплей] моей игры в [дисциплина]: тайминги, решения, ошибки, экономика, сравнение с [мета]. Дай план тренировок.»
Cat: GAMES | Esports
Diff: L2 | Tools: replay analysis | Web0 Code0 Files1 Vision0 Long0 | Auto 7
Why: разбор игры — самый быстрый путь роста в киберспорте
Caps: replay analysis, mistake identification, training plan
---

### 821 — Аудит безопасности системы
«Джарвис, проведи аудит безопасности этой системы: открытые порты, обновления, права доступа, автозагрузка, шифрование, бэкапы. Выдай отчёт с приоритетами исправлений.»
Cat: SECURITY | Audit
Diff: L3 | Tools: system audit | Web0 Code1 Files1 Vision0 Long1 | Auto 7
Why: аудит даёт карту рисков, без которой нельзя планировать защиту
Caps: security audit, hardening checklist, risk scoring

### 822 — Сканирование на уязвимости
«Джарвис, просканируй [хост/сеть/приложение] на известные уязвимости: [CVE/порт-скан/сканер]. Дай отчёт с CVE, критичностью и шагами устранения.»
Cat: SECURITY | Scanning
Diff: L3 | Tools: scanners | Web1 Code1 Files0 Vision0 Long1 | Auto 7
Why: сканирование находит то, что глазами не увидеть
Caps: vulnerability scanning, cve mapping, remediation

### 823 — Аудит паролей
«Джарвис, проверь мои пароли на слабость и утечки: [список/файл паролей]. Найди повторяющиеся, слабые, скомпрометированные. Составь план ротации без хранения паролей в открытом виде.»
Cat: SECURITY | Passwords
Diff: L1 | Tools: breach databases | Web1 Code0 Files1 Vision0 Long0 | Auto 6
Why: слабые пароли — причина большинства взломов аккаунтов
Caps: password audit, breach check, rotation plan

### 824 — Настройка менеджера паролей
«Джарвис, настрой менеджер паролей: мастер-пароль, генерация сложных паролей, авто-заполнение, импорт из браузера, резервная копия базы, семейный обмен.»
Cat: SECURITY | Passwords
Diff: L1 | Tools: password managers | Web0 Code0 Files1 Vision0 Long0 | Auto 6
Why: менеджер паролей — единственное практичное решение гигиены паролей
Caps: password manager setup, secure generation, vault backup

### 825 — Настройка двухфакторной аутентификации
«Джарвис, включи 2FA на [сервисы]: приложение-аутентификатор, резервные коды, ключи безопасности, процедура восстановления при потере телефона.»
Cat: SECURITY | MFA
Diff: L1 | Tools: authenticator apps | Web1 Code0 Files1 Vision0 Long0 | Auto 6
Why: 2FA блокирует подавляющее большинство взломов аккаунтов
Caps: mfa setup, recovery codes, hardware keys

### 826 — Аудит установленного ПО
«Джарвис, проверь установленное ПО на этой системе: устаревшие версии, неиспользуемые программы, неизвестные издатели, компоненты с известными уязвимостями.»
Cat: SECURITY | Audit
Diff: L1 | Tools: inventory | Web1 Code1 Files1 Vision0 Long0 | Auto 6
Why: неиспользуемое ПО — лишняя поверхность атаки
Caps: software inventory, outdated detection, unknown publisher check

### 827 — Безопасность Windows
«Джарвис, проверь и усиль защиту Windows: Defender, SmartScreen, BitLocker, UAC, firewall, обновления, настройки безопасности. Дай отчёт по каждому пункту.»
Cat: SECURITY | Windows
Diff: L2 | Tools: security center | Web0 Code1 Files1 Vision0 Long0 | Auto 7
Why: встроенные механизмы Windows недооценены, но критичны
Caps: windows hardening, defender config, uac policy

### 828 — Анализ подозрительных процессов
«Джарвис, проанализируй запущенные процессы: найди подозрительные (неизвестные пути, высокий расход, странные имена), объясни назначение и дай рекомендации.»
Cat: SECURITY | Monitoring
Diff: L2 | Tools: process explorer | Web1 Code1 Files0 Vision0 Long0 | Auto 7
Why: малварь почти всегда оставляет видимый след в процессах
Caps: process analysis, anomaly detection, hidden process discovery

### 829 — Автозагрузка и персистентность
«Джарвис, проверь автозагрузку системы: все точки персистентности (реестр, планировщик, службы, папки), найди необычные, объясни, что можно отключить.»
Cat: SECURITY | Persistence
Diff: L2 | Tools: autoruns | Web0 Code1 Files1 Vision0 Long0 | Auto 7
Why: автозагрузка — любимый способ малвари закрепиться в системе
Caps: persistence detection, autoruns analysis

### 830 — Анализ сетевых соединений
«Джарвис, проверь активные сетевые соединения: куда и откуда, какие процессы, подозрительные адреса и порты. Объясни каждое необычное соединение.»
Cat: SECURITY | Network
Diff: L2 | Tools: netstat, TCPView | Web1 Code1 Files0 Vision0 Long0 | Auto 7
Why: исходящие соединения малвари — главный маркер заражения
Caps: connection analysis, c2 detection, port monitoring

### 831 — Правила межсетевого экрана
«Джарвис, проверь и настрой firewall: правила входящих/исходящих, блокировка [портов/программ], зоны сети, логирование. Объясни, что и зачем меняешь.»
Cat: SECURITY | Network
Diff: L3 | Tools: firewall tools | Web0 Code1 Files1 Vision0 Long0 | Auto 7
Why: firewall — первый рубеж между системой и сетью
Caps: firewall policy, rule optimization, traffic logging

### 832 — Шифрование диска
«Джарвис, включи/проверь шифрование диска (BitLocker/LUKS): ключ восстановления, статус шифрования, план на случай потери ключа.»
Cat: SECURITY | Encryption
Diff: L3 | Tools: bitlocker, luks | Web0 Code1 Files1 Vision0 Long0 | Auto 7
Why: незашифрованный диск = открытые данные при краже устройства
Caps: full-disk encryption, recovery key management

### 833 — Шифрование файлов и папок
«Джарвис, зашифруй [файлы/папка]: алгоритм [AES-256], контейнер или отдельные файлы, парольная фраза, проверка расшифровки на копии.»
Cat: SECURITY | Encryption
Diff: L2 | Tools: gpg, veracrypt | Web0 Code0 Files1 Vision0 Long0 | Auto 6
Why: точечное шифрование защищает чувствительные данные внутри системы
Caps: file encryption, vault containers, key management

### 834 — Проверка целостности файлов
«Джарвис, проверь целостность [файлы/системные файлы]: контрольные суммы, базы целостности, поиск изменённых файлов. Покажи, что отличается от эталона.»
Cat: SECURITY | Integrity
Diff: L2 | Tools: hash tools, sfc | Web0 Code1 Files1 Vision0 Long0 | Auto 6
Why: незаметное изменение файлов — признак компрометации
Caps: integrity checking, hash verification, tamper detection

### 835 — Полная проверка антивирусом
«Джарвис, запусти полное сканирование [система/папка] антивирусом: расписание, карантин, отчёт по находкам, план лечения. Не удаляй ничего без подтверждения.»
Cat: SECURITY | Scanning
Diff: L1 | Tools: antivirus | Web0 Code1 Files1 Vision0 Long0 | Auto 7
Why: регулярное сканирование ловит то, что пропущено в реальном времени
Caps: malware scanning, quarantine handling, scan scheduling

### 836 — Оценка фишингового письма
«Джарвис, проверь [письмо] на признаки фишинга: отправитель, домен, ссылки, вложения, манипулятивные приёмы. Вердикт и что делать.»
Cat: SECURITY | Phishing
Diff: L1 | Tools: email analysis | Web1 Code0 Files1 Vision0 Long0 | Auto 6
Why: фишинг — самый массовый вектор, который начинается с письма
Caps: phishing detection, header analysis, link inspection

### 837 — Проверка ссылок перед кликом
«Джарвис, проверь [ссылки]: куда ведут, подделка домена, сокращатели, редиректы, репутация. Предупреди, если кликать опасно.»
Cat: SECURITY | Phishing
Diff: L1 | Tools: url scanners | Web1 Code0 Files0 Vision0 Long0 | Auto 6
Why: один клик по поддельной ссылке может стоить аккаунта
Caps: url reputation check, redirect chain analysis

### 838 — Анализ вложений
«Джарвис, проанализируй [вложение]: тип файла, макросы, скрипты, реальный формат (не по расширению), риски открытия. Запусти в изоляции при подозрении.»
Cat: SECURITY | Malware
Diff: L2 | Tools: file analysis | Web0 Code0 Files1 Vision0 Long0 | Auto 6
Why: расширение файла ничего не говорит о его содержимом
Caps: attachment analysis, mime detection, macro inspection

### 839 — Обнаружение угроз в реальном времени
«Джарвис, настрой мониторинг угроз: события безопасности, подозрительная активность, новые устройства, попытки входа. Оповещай при [критерии].»
Cat: SECURITY | Monitoring
Diff: L3 | Tools: SIEM, event logs | Web0 Code1 Files1 Vision0 Long1 | Auto 8
Why: быстрые детект и алерт сокращают ущерб от инцидента
Caps: real-time threat monitoring, alert rules, log correlation

### 840 — Анализ журналов безопасности
«Джарвис, проанализируй журналы безопасности за [период]: неудачные входы, изменения прав, службы, события [ID]. Найди паттерны атак.»
Cat: SECURITY | Forensics
Diff: L3 | Tools: event log tools | Web0 Code1 Files1 Vision0 Long0 | Auto 8
Why: журналы хранят следы атаки, которые легко пропустить вручную
Caps: log forensics, failed login analysis, privilege escalation detection

### 841 — Ловушка-приманка (honeypot)
«Джарвис, разверни honeypot: [сервис-приманка], мониторинг обращений, сбор данных атакующего, оповещения. Безопасно для основной системы.»
Cat: SECURITY | Detection
Diff: L4 | Tools: honeypot software | Web0 Code1 Files1 Vision0 Long1 | Auto 7
Why: приманка выявляет атакующих и их методы раньше ущерба
Caps: honeypot deployment, attacker profiling, early warning

### 842 — Оценка рисков информационной безопасности
«Джарвис, оцени риски для [активы/бизнес]: угрозы, вероятности, ущерб, текущие контрмеры. Составь матрицу рисков и план приоритетных мер.»
Cat: SECURITY | Risk
Diff: L3 | Tools: risk frameworks | Web0 Code1 Files1 Vision0 Long1 | Auto 8
Why: оценка рисков превращает страхи в управляемый список приоритетов
Caps: risk assessment, threat modeling, control prioritization

### 843 — План реагирования на инциденты
«Джарвис, составь план реагирования на [тип инцидента: взлом/утечка/вымогатель]: роли, шаги по минутам, коммуникация, сохранение улик, восстановление, разбор.»
Cat: SECURITY | Incident
Diff: L2 | Tools: runbooks | Web0 Code1 Files1 Vision0 Long0 | Auto 7
Why: план реагирования, написанный до инцидента, спасает при нём
Caps: incident response plan, runbook, evidence preservation

### 844 — Форензика после взлома
«Джарвис, проведи первичную форензику: время и вектор атаки, изменённые файлы, новые аккаунты, скрытые процессы, выводы и доказательства. Ничего не модифицируй.»
Cat: SECURITY | Forensics
Diff: L4 | Tools: forensic tools | Web0 Code1 Files1 Vision0 Long1 | Auto 8
Why: правильная форензика без изменений данных сохраняет доказательства
Caps: digital forensics, timeline reconstruction, evidence collection

### 845 — Анализ подозрительного файла в изоляции
«Джарвис, проанализируй [файл] в песочнице: поведение, сетевые вызовы, файловые операции, признаки малвари. Дай вердикт с уверенностью.»
Cat: SECURITY | Malware
Diff: L3 | Tools: sandbox | Web0 Code1 Files1 Vision0 Long1 | Auto 7
Why: запуск подозрительного файла вне изоляции опасен для системы
Caps: sandbox analysis, behavioral detection, verdict

### 846 — Проверка USB-носителей
«Джарвис, проверь [USB/внешний диск]: автозапуск, скрытые файлы, подозрительные исполняемые, признаки атаки BadUSB. Дай рекомендации.»
Cat: SECURITY | Media
Diff: L2 | Tools: USB analysis | Web0 Code0 Files1 Vision0 Long0 | Auto 6
Why: чужие флешки — классический вектор доставки малвари
Caps: usb inspection, autorun check, hidden file detection

### 847 — Безопасность Wi-Fi
«Джарвис, проверь безопасность [Wi-Fi сети]: шифрование, пароль, гостевая сеть, подключённые устройства, WPS, соседские помехи. Усиль конфигурацию.»
Cat: SECURITY | Network
Diff: L2 | Tools: wifi analysis | Web1 Code1 Files1 Vision0 Long0 | Auto 6
Why: слабый Wi-Fi открывает сеть любому прохожему
Caps: wifi security audit, rogue device detection, guest network

### 848 — Аудит прав доступа
«Джарвис, проверь права доступа на [файлы/папки/аккаунты]: кто имеет доступ к чему, лишние администраторы, публичные шары. Найди и предложи исправить избыточные права.»
Cat: SECURITY | Access
Diff: L2 | Tools: ACL tools | Web0 Code1 Files1 Vision0 Long0 | Auto 7
Why: избыточные права — тихая бомба при внутренних утечках
Caps: access audit, least privilege, admin review

### 849 — Управление секретами и ключами
«Джарвис, настрой хранилище секретов: [API-ключи, пароли, сертификаты] в [менеджер секретов], ротация, права доступа, аудит использования.»
Cat: SECURITY | Secrets
Diff: L3 | Tools: vault | Web0 Code1 Files1 Vision0 Long0 | Auto 7
Why: секреты в коде и конфигах — прямой путь к утечке
Caps: secrets management, rotation, access scoping

### 850 — Безопасное удаление данных
«Джарвис, удали [файлы/диск] без возможности восстановления: метод [перезапись/дегаусс/физическое уничтожение], сертификат удаления, проверка.»
Cat: SECURITY | Destruction
Diff: L2 | Tools: secure delete | Web0 Code1 Files1 Vision0 Long0 | Auto 6
Why: обычное удаление оставляет данные, восстановимые форензикой
Caps: secure deletion, data sanitization, wipe verification

### 851 — Поиск шпионского ПО
«Джарвис, проверь систему на шпионское ПО и следящее ПО: кейлоггеры, скриншотеры, эксфильтрация, браузерные расширения-шпионы.»
Cat: SECURITY | Malware
Diff: L2 | Tools: spyware tools | Web1 Code1 Files1 Vision0 Long0 | Auto 7
Why: шпионское ПО работает тихо и обнаруживается только аудитом
Caps: spyware detection, exfiltration hunting, extension audit

### 852 — Проверка компрометации аккаунтов
«Джарвис, проверь [аккаунты/email] на утечки и компрометацию: базы утечек, необычные входы, смена пароля без ведома, активные сессии.»
Cat: SECURITY | Accounts
Diff: L1 | Tools: breach checks | Web1 Code0 Files1 Vision0 Long0 | Auto 6
Why: скомпрометированный аккаунт действует месяцами незаметно
Caps: account compromise check, session audit, breach alerts

### 853 — Безопасность браузера
«Джарвис, усиль безопасность браузера: расширения (удали лишние), настройки конфиденциальности, защита от трекинга, проверка паролей в браузере, флаги.»
Cat: SECURITY | Browser
Diff: L1 | Tools: browser settings | Web1 Code0 Files1 Vision0 Long0 | Auto 6
Why: браузер — главная точка входа для большинства атак
Caps: browser hardening, extension audit, tracking protection

### 854 — Проверка HTTPS и сертификатов
«Джарвис, проверь сертификаты [сайты/сервисы]: срок действия, цепочка доверия, алгоритмы, уязвимости TLS. Найди проблемы и дай план исправления.»
Cat: SECURITY | TLS
Diff: L2 | Tools: openssl, ssl scanners | Web1 Code1 Files0 Vision0 Long0 | Auto 6
Why: протухший или слабый сертификат — и проблема доверия, и риск перехвата
Caps: tls audit, certificate validation, cipher checks

### 855 — Обновления и патчи
«Джарвис, проверь систему и ПО на доступные обновления: критичность, известные уязвимости, план установки с откатом, тест после установки.»
Cat: SECURITY | Patching
Diff: L1 | Tools: update managers | Web1 Code1 Files1 Vision0 Long0 | Auto 7
Why: непропатченное ПО — самая используемая точка входа атак
Caps: patch management, update testing, rollback plan

### 856 — Аудит SSH-ключей
«Джарвис, проверь SSH-ключи: алгоритмы, длины, сроки, неиспользуемые ключи, кто имеет доступ по [файлы авторизации]. Удали лишние и усиль оставшиеся.»
Cat: SECURITY | Access
Diff: L2 | Tools: ssh-keygen | Web0 Code1 Files1 Vision0 Long0 | Auto 6
Why: забытые SSH-ключи — невидимые входные двери на серверы
Caps: ssh key audit, key rotation, authorized_keys review

### 857 — Анализ подозрительного скрипта
«Джарвис, прочитай и объясни [скрипт]: что делает, что скачивает, какие команды выполняет, есть ли вредоносные действия. Дай вердикт без запуска.»
Cat: SECURITY | Analysis
Diff: L1 | Tools: static analysis | Web0 Code1 Files1 Vision0 Long0 | Auto 7
Why: статический анализ скрипта безопаснее его запуска
Caps: script analysis, obfuscation decoding, safe verdict

### 858 — Мониторинг утечек в открытых источниках
«Джарвис, отслеживай упоминания [компания/персона/ключевые слова] в дарквебе и открытых источниках: слитые базы, обсуждения, домены-подделки. Сводки и алерты.»
Cat: SECURITY | OSINT
Diff: L2 | Tools: dark web monitoring | Web1 Code0 Files1 Vision0 Long1 | Auto 8
Why: раннее обнаружение утечки позволяет действовать до массового вреда
Caps: dark web monitoring, brand protection, leak alerting

### 859 — Тренинг по кибербезопасности
«Джарвис, проведи тренинг для [сотрудники]: фишинг, пароли, соц.инженерия, безопасное поведение. С вопросами, кейсами, оценкой знаний и сертификатами.»
Cat: SECURITY | Education
Diff: L1 | Tools: training modules | Web1 Code0 Files1 Vision0 Long0 | Auto 7
Why: человек — слабейшее звено, и обучение снижает риски сильнее железа
Caps: security awareness, phishing simulation, training assessment

### 860 — Безопасность умного дома
«Джарвис, проверь безопасность умного дома: устройства в сети, порты, пароли по умолчанию, обновления прошивок, изолированная сеть для IoT.»
Cat: SECURITY | IoT
Diff: L2 | Tools: network tools | Web1 Code1 Files1 Vision0 Long0 | Auto 6
Why: IoT-устройства — самые незащищённые и самые подключённые
Caps: iot security, device segmentation, firmware updates

### 861 — Аудит цифрового следа
«Джарвис, найди, что обо мне есть в интернете: поиск по [имя/email/никам], соцсети, утечки, упоминания. Собери отчёт и план по сокращению следа.»
Cat: PRIVACY | Footprint
Diff: L2 | Tools: OSINT search | Web1 Code0 Files0 Vision0 Long1 | Auto 7
Why: цифровой след формирует репутацию и риски, о которых часто не знают
Caps: digital footprint audit, OSINT, reputation management

### 862 — Удаление данных из поисковиков
«Джарвис, помоги убрать мои данные из [поисковики/сервисы]: процедуры удаления, формы Google, запросы на удаление устаревших страниц, контроль повторного появления.»
Cat: PRIVACY | Footprint
Diff: L1 | Tools: removal forms | Web1 Code0 Files0 Vision0 Long0 | Auto 6
Why: поисковый след можно уменьшать системно, а не отчаянно
Caps: search removal, right-to-be-forgotten, reputation cleanup

### 863 — Приватность браузера
«Джарвис, настрой приватный браузинг: блокировщики трекеров, контейнеры, удаление истории, DNS-шифрование, приватные окна по умолчанию.»
Cat: PRIVACY | Browser
Diff: L1 | Tools: browser config | Web1 Code0 Files1 Vision0 Long0 | Auto 6
Why: трекинг — главная форма слежки в повседневном интернете
Caps: tracking protection, browser fingerprint reduction, private DNS

### 864 — Приватность в соцсетях
«Джарвис, проверь настройки приватности в [соцсеть]: кто видит посты и профиль, приложения с доступом, геолокация, архив данных. Ужесточь по моим пожеланиям.»
Cat: PRIVACY | Social
Diff: L1 | Tools: platform settings | Web1 Code0 Files0 Vision0 Long0 | Auto 6
Why: настройки по умолчанию соцсетей почти всегда слишком открытые
Caps: social privacy audit, app permission revocation, data export

### 865 — Проверка утечек моих данных
«Джарвис, проверь [email/телефон] по базам утечек: какие данные утекли, в каких инцидентах, что делать (смена пароля, 2FA, мониторинг).»
Cat: PRIVACY | Leaks
Diff: L0 | Tools: breach databases | Web1 Code0 Files0 Vision0 Long0 | Auto 5
Why: утёкшие данные — готовый материал для целевых атак
Caps: personal breach check, leaked credential handling

### 866 — Защита личных документов
«Джарвис, организуй защиту [личные документы]: шифрование папки, доступы, бэкапы, соглашения об именовании без чувствительных данных в именах.»
Cat: PRIVACY | Documents
Diff: L1 | Tools: encryption, vaults | Web0 Code1 Files1 Vision0 Long0 | Auto 6
Why: личные документы в открытом виде — утечка при любом доступе к ПК
Caps: document protection, sensitive naming, encrypted storage

### 867 — Приватный поиск и DNS
«Джарвис, настрой приватный поиск и DNS: поисковик без трекинга, DNS-over-HTTPS, проверка утечек DNS. Объясни, что видит провайдер.»
Cat: PRIVACY | Network
Diff: L1 | Tools: DNS config | Web1 Code0 Files1 Vision0 Long0 | Auto 5
Why: поиск и DNS раскрывают намерения пользователя провайдеру
Caps: private search, encrypted dns, leak testing

### 868 — Выбор и настройка VPN
«Джарвис, оцени [VPN-провайдеры] по [критерии: логи, скорость, юрисдикция] и настрой лучший: kill-switch, протоколы, split-tunneling, тест утечек.»
Cat: PRIVACY | VPN
Diff: L2 | Tools: VPN clients | Web1 Code0 Files1 Vision0 Long0 | Auto 6
Why: VPN без kill-switch и проверки утечек может быть хуже отсутствия
Caps: vpn selection, leak testing, kill-switch config

### 869 — Анонимность в интернете
«Джарвис, объясни и настрой анонимность: [Tor/прокси/приватные сервисы], какие данные всё равно видимы, какой уровень анонимности достижим для [задача].»
Cat: PRIVACY | Anonymity
Diff: L3 | Tools: tor, proxies | Web1 Code0 Files1 Vision0 Long0 | Auto 6
Why: анонимность — сложная дисциплина, где ложная уверенность опасна
Caps: anonymity setup, threat model, opsec guidance

### 870 — Приватность смартфона
«Джарвис, настрой приватность телефона: разрешения приложений, рекламный идентификатор, локация, резервные копии в облако, параметры рекламы.»
Cat: PRIVACY | Mobile
Diff: L1 | Tools: OS settings | Web1 Code0 Files1 Vision0 Long0 | Auto 6
Why: телефон знает о человеке больше, чем кто-либо другой
Caps: mobile privacy, permission audit, ad identifier reset

### 871 — Приватность Windows
«Джарвис, проверь настройки приватности Windows: телеметрия, рекламный ID, локация, микрофон/камера для приложений, история активности. Отключи лишнее.»
Cat: PRIVACY | OS
Diff: L1 | Tools: system settings | Web0 Code1 Files1 Vision0 Long0 | Auto 6
Why: ОС по умолчанию собирает больше данных, чем хотел бы пользователь
Caps: os telemetry reduction, privacy hardening, app permissions

### 872 — Очистка следов активности
«Джарвис, очисти следы активности: история браузера, кэши, недавние документы, временные файлы, журналы [по критериям]. Составь отчёт, что удалено.»
Cat: PRIVACY | Hygiene
Diff: L1 | Tools: cleanup tools | Web0 Code1 Files1 Vision0 Long0 | Auto 6
Why: следы активности на общем ПК видны любому, кто за него сядет
Caps: activity cleanup, cache removal, forensic hygiene

### 873 — Политика приватности для бизнеса
«Джарвис, напиши внутреннюю политику приватности [компания]: какие данные собираем, кто имеет доступ, сроки хранения, процедуры по запросам пользователей, ответственность.»
Cat: PRIVACY | Compliance
Diff: L3 | Tools: policy templates | Web1 Code1 Files1 Vision0 Long0 | Auto 7
Why: политика без процедур — бумага, не защищающая от штрафов
Caps: privacy policy authoring, data retention, dpia support

### 874 — Приватность облачных сервисов
«Джарвис, проверь приватность [облачные сервисы]: что синхронизируется, кто имеет доступ, шифрование, общие ссылки, сторонние приложения с доступом.»
Cat: PRIVACY | Cloud
Diff: L1 | Tools: service settings | Web1 Code0 Files1 Vision0 Long0 | Auto 6
Why: облако, о котором забыли, продолжает хранить и раскрывать данные
Caps: cloud privacy audit, share link review, access revocation

### 875 — Анализ разрешений приложений
«Джарвис, проанализируй разрешения [приложений]: доступ к камере, микрофону, файлам, контактам — что нужно, что избыточно. Составь план отзыва.»
Cat: PRIVACY | Permissions
Diff: L1 | Tools: permission managers | Web0 Code1 Files1 Vision0 Long0 | Auto 6
Why: приложение с лишними разрешениями — скрытый шпион
Caps: permission analysis, least-access enforcement

### 876 — Защита от слежки
«Джарвис, проверь систему на признаки слежки: скрытая запись, подменённые DNS, прокси, сертификаты-перехватчики, странные расширения. Устрани найденное.»
Cat: PRIVACY | Surveillance
Diff: L3 | Tools: monitoring tools | Web0 Code1 Files1 Vision0 Long0 | Auto 7
Why: скрытая слежка обнаруживается только активной проверкой
Caps: surveillance detection, certificate pinning check, proxy audit

### 877 — Приватность мессенджеров
«Джарвис, сравни и настрой [мессенджеры] по приватности: сквозное шифрование, метаданные, резервные копии, исчезающие сообщения, кто админ в группах.»
Cat: PRIVACY | Messaging
Diff: L1 | Tools: app settings | Web1 Code0 Files1 Vision0 Long0 | Auto 5
Why: выбор мессенджера — это выбор уровня защиты переписки
Caps: messaging privacy, e2e verification, metadata awareness

### 878 — Чистка метаданных файлов
«Джарвис, удали метаданные из [файлы]: автор, геолокация, история правок, устройство. Подготовь файлы к публикации без следов.»
Cat: PRIVACY | Metadata
Diff: L1 | Tools: exiftool | Web0 Code0 Files1 Vision0 Long0 | Auto 5
Why: метаданные выдают автора и место съёмки против воли владельца
Caps: metadata stripping, publish-ready sanitization

### 879 — Инвентаризация персональных данных
«Джарвис, составь реестр персональных данных, которые я храню: где, какие категории, зачем, срок хранения. Основа для GDPR/152-ФЗ и минимизации.»
Cat: PRIVACY | Compliance
Diff: L2 | Tools: data mapping | Web0 Code1 Files1 Vision0 Long0 | Auto 7
Why: нельзя защитить и удалить то, что не учтено в реестре
Caps: personal data inventory, data mapping, retention schedule

### 880 — План минимизации данных
«Джарвис, составь план сокращения хранимых данных: что удалить, что обезличить, что оставить с обоснованием. Реализуй по этапам с проверкой.»
Cat: PRIVACY | Hygiene
Diff: L2 | Tools: cleanup | Web0 Code1 Files1 Vision0 Long0 | Auto 7
Why: минимизация данных снижает и риски утечки, и нагрузку на хранение
Caps: data minimization, anonymization, retention enforcement

### 881 — Стратегия резервного копирования
«Джарвис, разработай стратегию бэкапов для [данные]: правило 3-2-1, частоты, типы (полный/инкрементальный), RPO и RTO, бюджет и инструменты.»
Cat: BACKUP | Strategy
Diff: L2 | Tools: backup planning | Web0 Code1 Files1 Vision0 Long1 | Auto 7
Why: стратегия определяет, переживёт ли компания потерю данных
Caps: backup strategy, 3-2-1 rule, rpo/rto definition

### 882 — Автоматические резервные копии
«Джарвис, настрой автоматические бэкапы [папки/системы]: расписание, исключения, сжатие, шифрование, уведомления об успехе/провале.»
Cat: BACKUP | Automation
Diff: L2 | Tools: backup tools | Web0 Code1 Files1 Vision0 Long0 | Auto 8
Why: ручные бэкапы делаются «когда-нибудь», то есть никогда
Caps: backup automation, scheduling, failure alerts

### 883 — Резервная копия системы
«Джарвис, создай образ системы: полный снимок [диск/система], включая ОС и программы, точку восстановления, инструкцию по восстановлению на новом железе.»
Cat: BACKUP | System
Diff: L3 | Tools: imaging tools | Web0 Code1 Files1 Vision0 Long1 | Auto 7
Why: образ системы возвращает рабочую машину за час вместо дней
Caps: system imaging, bare-metal restore, recovery media

### 884 — Версионирование файлов
«Джарвис, настрой версионирование [папки]: история изменений, откат к любой версии, сроки хранения версий, выборочное восстановление.»
Cat: BACKUP | Versioning
Diff: L2 | Tools: versioning tools | Web0 Code1 Files1 Vision0 Long0 | Auto 7
Why: версии защищают от перезаписи и шифровальщиков
Caps: file versioning, point-in-time restore

### 885 — Облачные резервные копии
«Джарвис, настрой облачный бэкап [данные] в [облако]: шифрование перед загрузкой, дедупликация, лимиты трафика, восстановление через [сценарий].»
Cat: BACKUP | Cloud
Diff: L2 | Tools: cloud backup | Web1 Code1 Files1 Vision0 Long0 | Auto 7
Why: облако переживает локальные катастрофы (пожар, кража, вымогатель)
Caps: offsite backup, client-side encryption, bandwidth control

### 886 — Регулярное тестирование восстановления
«Джарвис, проведи тест восстановления из бэкапа: восстанови [выборку] в [место], проверь целостность, замерь время. Отчёт и рекомендации.»
Cat: BACKUP | Testing
Diff: L2 | Tools: restore tests | Web0 Code1 Files1 Vision0 Long0 | Auto 7
Why: бэкап, который не проверен восстановлением, — не бэкап
Caps: restore testing, dr rehearsal, integrity verification

### 887 — Резервное копирование баз данных
«Джарвис, настрой бэкапы [базы данных]: логические/физические дампы, расписание, точка восстановления (PITR), проверка читаемости дампа, хранение версий.»
Cat: BACKUP | Databases
Diff: L3 | Tools: db tools | Web0 Code1 Files1 Vision0 Long0 | Auto 7
Why: база без PITR теряет всё, что изменилось с последнего дампа
Caps: database backup, point-in-time recovery, dump validation

### 888 — Бэкап почты и контактов
«Джарвис, сохрани [почта/контакты/календарь]: полный экспорт, приложения с метаданными, контакты в [формат], восстановление в [сервис].»
Cat: BACKUP | Mail
Diff: L1 | Tools: export tools | Web0 Code1 Files1 Vision0 Long0 | Auto 6
Why: почта и контакты — данные, потеря которых парализует работу
Caps: mail export, contacts backup, migration readiness

### 889 — Инкрементальные и дифференциальные бэкапы
«Джарвис, настрой инкрементальные бэкапы [источник]: цепочки, дедупликация, синтетические полные копии, оценка роста хранилища.»
Cat: BACKUP | Strategy
Diff: L2 | Tools: backup engines | Web0 Code1 Files1 Vision0 Long0 | Auto 7
Why: инкрементальность экономит место и трафик без потери версий
Caps: incremental backup, deduplication, chain management

### 890 — Шифрование резервных копий
«Джарвис, зашифруй [бэкапы]: ключи, хранение ключей отдельно, тест расшифровки, процедура восстановления для другого человека (наследование).»
Cat: BACKUP | Encryption
Diff: L2 | Tools: encryption | Web0 Code1 Files1 Vision0 Long0 | Auto 6
Why: незашифрованный бэкап в облаке — та же утечка
Caps: backup encryption, key escrow, restore handover

### 891 — План аварийного восстановления
«Джарвис, составь план аварийного восстановления (DR): сценарии [пожар/вымогатель/отказ железа], шаги, RTO/RPO, коммуникация, проверка плана.»
Cat: BACKUP | DR
Diff: L3 | Tools: DR planning | Web0 Code1 Files1 Vision0 Long1 | Auto 7
Why: DR-план, проверенный практикой, — разница между остановкой на день и на месяц
Caps: disaster recovery plan, business continuity, rto/rpo targets

### 892 — Бэкап перед обновлением
«Джарвис, перед [обновление системы/ПО/миграция] создай контрольную точку: бэкап состояния, список изменений, шаги отката, тест отката.»
Cat: BACKUP | Safety
Diff: L1 | Tools: checkpoints | Web0 Code1 Files1 Vision0 Long0 | Auto 6
Why: точка отката превращает неудачное обновление в 10 минут
Caps: pre-update checkpoint, rollback readiness

### 893 — Мониторинг резервного копирования
«Джарвис, настрой мониторинг бэкапов: статусы всех задач, задержки, ошибки, размеры, алерты при провале. Еженедельная сводка.»
Cat: BACKUP | Monitoring
Diff: L2 | Tools: monitoring | Web0 Code1 Files1 Vision0 Long0 | Auto 8
Why: тихий провал бэкапа обнаруживается только при потере данных
Caps: backup monitoring, failure alerting, health dashboards

### 894 — Резервная копия телефона
«Джарвис, настрой резервное копирование телефона: фото, контакты, сообщения, приложения, пароли — в [назначение] с шифрованием и расписанием.»
Cat: BACKUP | Mobile
Diff: L1 | Tools: device backup | Web0 Code0 Files1 Vision0 Long0 | Auto 6
Why: телефон теряется чаще, чем компьютер, а память в нём — бесценна
Caps: mobile backup, photo vault, cross-device restore

### 895 — Журнал бэкапов и отчётность
«Джарвис, веди журнал бэкапов: даты, объёмы, результаты, отклонения. Собери месячный отчёт и план корректировок.»
Cat: BACKUP | Reporting
Diff: L1 | Tools: logging | Web0 Code1 Files1 Vision0 Long0 | Auto 6
Why: журнал даёт уверенность аудиту и видит тренды деградации
Caps: backup logging, trend analysis, compliance reporting

### 896 — Анализ использования дискового пространства
«Джарвис, проанализируй использование диска: кто занимает место, крупнейшие файлы и папки, темпы роста, аномалии. Визуализируй и предложи, что чистить.»
Cat: STORAGE | Analysis
Diff: L1 | Tools: disk analyzers | Web0 Code1 Files1 Vision0 Long1 | Auto 6
Why: «место кончилось» — почти всегда следствие невидимых накопителей мусора
Caps: disk space analysis, growth trend, large file hunting

### 897 — Очистка диска
«Джарвис, очисти диск: временные файлы, кэши, старые загрузки, корзины, логи, дубликаты. Покажи, что удалишь и сколько освободишь, до выполнения.»
Cat: STORAGE | Cleanup
Diff: L1 | Tools: cleanup tools | Web0 Code1 Files1 Vision0 Long0 | Auto 6
Why: регулярная чистка предотвращает деградацию системы
Caps: disk cleanup, cache clearing, safe deletion

### 898 — Дедупликация файлов
«Джарвис, найди и устрани дубликаты файлов: точные копии, похожие по содержимому, дубли в облаке и на диске. Согласуй удаление.»
Cat: STORAGE | Dedup
Diff: L1 | Tools: dedup tools | Web0 Code0 Files1 Vision0 Long0 | Auto 6
Why: дубликаты крадут терабайты и создают путаницу версий
Caps: file deduplication, similarity detection, merge strategy

### 899 — Управление разделами и томами
«Джарвис, проверь разделы и тома: размеры, свободное место, здоровье SMART, файловая система. Подготовь план реорганизации без потери данных.»
Cat: STORAGE | Volumes
Diff: L3 | Tools: disk management | Web0 Code1 Files1 Vision0 Long0 | Auto 6
Why: проблемы разделов видны заранее по SMART и заполненности
Caps: partition management, smart health, fs planning

### 900 — Организация облачного хранилища
«Джарвис, организуй [облачное хранилище]: структура папок, синхронизация с [устройства], права общих ссылок, авто-загрузка фото, очистка от дублей.»
Cat: STORAGE | Cloud
Diff: L1 | Tools: cloud tools | Web1 Code0 Files1 Vision0 Long0 | Auto 6
Why: облако без структуры превращается в свалку, которую нельзя найти
Caps: cloud organization, share management, sync config
---

### 901 — Полная диагностика сети
«Джарвис, проведи диагностику сети: доступность [хостов], маршруты, DNS, потери, скорость, качество. Собери отчёт с выводом, где узкое место.»
Cat: NETWORK | Diagnostics
Diff: L2 | Tools: ping, traceroute, mtr | Web0 Code1 Files0 Vision0 Long0 | Auto 7
Why: системная диагностика находит проблемы, которые не видны одним пингом
Caps: network diagnostics, path analysis, bottleneck detection

### 902 — Сканирование локальной сети
«Джарвис, просканируй [сеть]: найди все устройства, их IP/MAC, открытые порты, сервисы, ОС. Составь карту сети с пояснениями.»
Cat: NETWORK | Discovery
Diff: L2 | Tools: nmap | Web0 Code1 Files0 Vision0 Long1 | Auto 7
Why: неизвестные устройства в сети — риск, который надо видеть
Caps: network discovery, host inventory, port scanning

### 903 — Мониторинг трафика
«Джарвис, мониторь сетевой трафик: какие приложения сколько передают, топ потребителей, аномалии по времени. Еженедельный отчёт.»
Cat: NETWORK | Monitoring
Diff: L2 | Tools: traffic tools | Web0 Code1 Files0 Vision0 Long1 | Auto 8
Why: трафик рассказывает о поведении устройств больше любых логов
Caps: traffic analysis, top talkers, anomaly detection

### 904 — Настройка роутера
«Джарвис, проверь и настрой [роутер]: пароль админки, шифрование Wi-Fi, гостевая сеть, QoS, обновление прошивки, отключение лишних сервисов.»
Cat: NETWORK | Routers
Diff: L2 | Tools: router admin | Web1 Code1 Files0 Vision0 Long0 | Auto 6
Why: роутер — центр сети, и его безопасность определяет всё
Caps: router hardening, wifi config, qos setup

### 905 — Оптимизация Wi-Fi
«Джарвис, оптимизируй Wi-Fi: анализ каналов и загрузки, выбор частоты, позиции точек доступа, помехи, покрытие. Замерь скорость до/после.»
Cat: NETWORK | Wi-Fi
Diff: L2 | Tools: wifi analyzers | Web0 Code1 Files0 Vision0 Long0 | Auto 6
Why: Wi-Fi можно ускорить в разы просто выбором канала и места
Caps: wifi optimization, channel planning, coverage mapping

### 906 — Диагностика DNS
«Джарвис, проверь DNS: резолвинг [доменов], скорость ответов, утечки, корректность записей (A, MX, SPF, DKIM, DMARC). Найди проблемы и предложи исправление.»
Cat: NETWORK | DNS
Diff: L2 | Tools: dig, nslookup | Web1 Code1 Files0 Vision0 Long0 | Auto 6
Why: DNS-проблемы проявляются как «интернет не работает» без явной причины
Caps: dns analysis, mail authentication checks, resolver performance

### 907 — Набор сетевых утилит
«Джарвис, собери для меня шпаргалку-набор утилит для [задача]: команды с примерами, что выводить, как читать результат, типовые проблемы.»
Cat: NETWORK | Tools
Diff: L1 | Tools: network tools | Web0 Code1 Files1 Vision0 Long0 | Auto 5
Why: правильная утилита сокращает диагностику с часов до минут
Caps: tool selection, command recipes, output interpretation

### 908 — Настройка VPN-сервера
«Джарвис, разверни VPN-сервер: [протокол: WireGuard/OpenVPN], сертификаты, клиентские конфиги, маршрутизация, доступ в локальную сеть, безопасность.»
Cat: NETWORK | VPN
Diff: L4 | Tools: wireguard, openvpn | Web0 Code1 Files1 Vision0 Long0 | Auto 8
Why: собственный VPN — приватный доступ к своим ресурсам из любой точки
Caps: vpn server setup, key distribution, routing rules

### 909 — Настройка прокси
«Джарвис, настрой прокси для [задача: обход, контроль, анонимность]: тип [HTTP/SOCKS], аутентификация, списки исключений, тест соединения.»
Cat: NETWORK | Proxy
Diff: L3 | Tools: proxy software | Web0 Code1 Files0 Vision0 Long0 | Auto 7
Why: прокси даёт контроль и гибкость сетевого доступа
Caps: proxy configuration, access control, tunneling

### 910 — Общий доступ к файлам по сети
«Джарвис, настрой общий доступ к [папкам] по сети: права для [пользователи], безопасность (без гостевого доступа), сопоставление дисков, тест с другой машины.»
Cat: NETWORK | Sharing
Diff: L2 | Tools: SMB config | Web0 Code1 Files1 Vision0 Long0 | Auto 6
Why: сетевые шары без прав — дыра, шары без удобства — бесполезны
Caps: file sharing, smb hardening, permission design

### 911 — Сетевое хранилище NAS
«Джарвис, настрой [NAS]: RAID-массив, пользователи и права, общие папки, резервные копии, доступ извне безопасно, мониторинг дисков.»
Cat: NETWORK | NAS
Diff: L3 | Tools: NAS admin | Web1 Code1 Files1 Vision0 Long0 | Auto 7
Why: NAS — центральный узел дома и малого бизнеса, требующий защиты
Caps: nas setup, raid planning, external access security

### 912 — Проброс портов
«Джарвис, настрой проброс портов на [роутере] для [сервисы]: статические IP, ограничение источников, логирование, проверка доступности извне.»
Cat: NETWORK | Routing
Diff: L3 | Tools: router config | Web0 Code1 Files0 Vision0 Long0 | Auto 6
Why: открытые наружу порты — самый простой путь атаки
Caps: port forwarding, exposure minimization, source filtering

### 913 — Мониторинг доступности сервисов
«Джарвис, мониторь доступность [сервисы/сайты]: проверки каждые [интервал], история аптайма, оповещения при недоступности, отчёты.»
Cat: NETWORK | Monitoring
Diff: L1 | Tools: uptime monitors | Web0 Code1 Files0 Vision0 Long1 | Auto 8
Why: «сайт лежит» без мониторинга — потери, о которых узнают поздно
Caps: uptime monitoring, availability history, instant alerts

### 914 — Анализ производительности сети
«Джарвис, измерь производительность сети: пропускная способность, задержки, джиттер, потери на [участках]. Найди, что деградирует.»
Cat: PERFORMANCE | Network
Diff: L2 | Tools: iperf, mtr | Web0 Code1 Files0 Vision0 Long0 | Auto 6
Why: заявленная скорость оператора и фактическая — разные вещи
Caps: bandwidth testing, latency/jitter analysis, degradation pinpoint

### 915 — Аудит сетевых сервисов
«Джарвис, проверь открытые сервисы на [машины]: лишние, слабо защищённые, с известными уязвимостями. Дай план закрытия и усиления.»
Cat: SECURITY | Network
Diff: L2 | Tools: scanners | Web1 Code1 Files0 Vision0 Long0 | Auto 7
Why: каждый открытый порт — потенциальная дверь в систему
Caps: service audit, exposure reduction, hardening

### 916 — Проверка IPv6
«Джарвис, проверь поддержку и корректность IPv6: адресация, маршруты, DNS, доступность [сайтов], проблемы «утечки» IPv6 мимо VPN.»
Cat: NETWORK | IPv6
Diff: L3 | Tools: ipv6 tools | Web0 Code1 Files0 Vision0 Long0 | Auto 6
Why: IPv6 работает рядом с IPv4 незаметно, включая утечки трафика
Caps: ipv6 validation, dual-stack config, leak prevention

### 917 — TLS и сертификаты в инфраструктуре
«Джарвис, проведи аудит TLS на [сервисы]: версии, шифры, сертификаты, сроки. Приведи к современным стандартам и проверь совместимость клиентов.»
Cat: SECURITY | TLS
Diff: L3 | Tools: ssl tools | Web1 Code1 Files0 Vision0 Long0 | Auto 7
Why: устаревший TLS — перехват трафика «законными» способами
Caps: tls hardening, cipher suite review, cert lifecycle

### 918 — Удалённый доступ к компьютеру
«Джарвис, настрой удалённый доступ к [машина]: RDP/SSH/VNC, аутентификация, ограничение по IP, шифрование, журналирование, отключение при простое.»
Cat: NETWORK | Remote
Diff: L3 | Tools: remote tools | Web0 Code1 Files1 Vision0 Long0 | Auto 7
Why: удалённый доступ без ограничений — готовый бэкдор
Caps: remote access setup, rdp hardening, session audit

### 919 — Сетевые профили Windows
«Джарвис, настрой сетевые профили Windows: частная/общественная сеть, общий доступ по профилям, правила для [адаптеров], режим обнаружения.»
Cat: NETWORK | Windows
Diff: L1 | Tools: network settings | Web0 Code1 Files1 Vision0 Long0 | Auto 5
Why: «общественная» сеть с включённым общим доступом — утечка данных
Caps: network profiles, sharing boundaries, adapter config

### 920 — Диагностика локальной сети (LAN)
«Джарвис, проверь локальную сеть: разводка, свитчи, кабели, скорость линков, дуплекс, ошибки на интерфейсах, топология.»
Cat: NETWORK | LAN
Diff: L2 | Tools: lan tools | Web0 Code1 Files0 Vision0 Long0 | Auto 6
Why: физический слой LAN — источник большинства «случайных» тормозов
Caps: lan health, link diagnostics, topology mapping

### 921 — Настройка DHCP
«Джарвис, проверь DHCP: пул адресов, конфликты, резервирования, время аренды, опции (DNS, шлюз). Исправь проблемы раздачи.»
Cat: NETWORK | DHCP
Diff: L2 | Tools: dhcp tools | Web0 Code1 Files0 Vision0 Long0 | Auto 6
Why: сбой DHCP отключает сеть для всех клиентов разом
Caps: dhcp audit, lease conflict resolution, scope planning

### 922 — Инвентаризация устройств сети
«Джарвис, собери инвентаризацию [сеть]: устройства, серийные номера, версии ПО, MAC-адреса, владельцы, сроки замены. Веди базу.»
Cat: NETWORK | Inventory
Diff: L2 | Tools: inventory tools | Web1 Code1 Files1 Vision0 Long0 | Auto 7
Why: без инвентаря невозможно ни обновлять, ни защищать, ни планировать
Caps: asset inventory, firmware tracking, lifecycle planning

### 923 — Тест скорости интернета
«Джарвис, замерь скорость интернета: скачивание, загрузка, пинг, джиттер, стабильность во времени. Сравни с тарифом [провайдер] и дай вывод.»
Cat: NETWORK | Testing
Diff: L0 | Tools: speedtest | Web1 Code0 Files0 Vision0 Long0 | Auto 5
Why: сравнение с тарифом — аргумент для претензий провайдеру
Caps: speed testing, plan comparison, stability analysis

### 924 — Качество связи для звонков/конференций
«Джарвис, проверь качество сети для [видеозвонки/VoIP]: джиттер, потери пакетов, задержки, приоритеты QoS, рекомендации по стабильности.»
Cat: NETWORK | QoS
Diff: L2 | Tools: voip tools | Web0 Code1 Files0 Vision0 Long0 | Auto 6
Why: звонок рвётся из-за сети, а не из-за приложения
Caps: voip readiness, qos marking, jitter buffering

### 925 — Ограничение и приоритизация полосы
«Джарвис, настрой QoS/лимиты: приоритет [сервисам], ограничение [устройств/приложений], справедливое распределение, мониторинг эффекта.»
Cat: NETWORK | QoS
Diff: L3 | Tools: router QoS | Web0 Code1 Files0 Vision0 Long0 | Auto 6
Why: без QoS одно приложение может убить сеть для всех
Caps: bandwidth shaping, application prioritization, fairness

### 926 — Сетевые политики организации
«Джарвис, спроектируй сетевые политики [компания]: сегментация, VPN-доступ, Wi-Fi для гостей, правила для устройств, инвентаризация и аудит.»
Cat: NETWORK | Policy
Diff: L3 | Tools: policy design | Web1 Code1 Files1 Vision0 Long1 | Auto 7
Why: политики превращают хаос подключений в управляемую сеть
Caps: network policy, segmentation design, access governance

### 927 — Анализ сетевого трафика (пакеты)
«Джарвис, захвати и проанализируй трафик: [интерфейс/фильтр]: кто с кем общается, протоколы, подозрительные паттерны, объёмы. Объясни находки.»
Cat: NETWORK | Analysis
Diff: L3 | Tools: wireshark, tcpdump | Web0 Code1 Files0 Vision0 Long1 | Auto 7
Why: пакеты не лгут — в отличие от логов приложений
Caps: packet capture, protocol analysis, suspicious pattern detection

### 928 — Обнаружение сетевых атак
«Джарвис, проверь [журналы/трафик] на признаки атак: сканирование, brute-force, ARP-спуфинг, DDoS, необычные исходящие. Дай оценку и меры.»
Cat: SECURITY | Network
Diff: L3 | Tools: ids tools | Web0 Code1 Files0 Vision0 Long0 | Auto 7
Why: раннее обнаружение атаки снижает её последствия
Caps: attack detection, bruteforce spotting, spoofing checks

### 929 — Синхронизация времени (NTP)
«Джарвис, проверь синхронизацию времени на [машины]: источники NTP, смещения, корректность — критично для логов и аутентификации.»
Cat: NETWORK | NTP
Diff: L1 | Tools: ntp tools | Web0 Code1 Files0 Vision0 Long0 | Auto 5
Why: рассинхрон часов ломает логи, сертификаты и Kerberos
Caps: ntp sync, clock drift correction, time source audit

### 930 — Отчёт о состоянии сети
«Джарвис, собери ежемесячный отчёт о сети: аптайм, инциденты, изменения, пропускная способность, план на следующий месяц.»
Cat: NETWORK | Reporting
Diff: L1 | Tools: reporting | Web0 Code1 Files1 Vision0 Long1 | Auto 7
Why: регулярный отчёт делает сеть управляемой, а не «как-то работает»
Caps: network reporting, incident summary, capacity planning

### 931 — Диагностика производительности системы
«Джарвис, проведи диагностику производительности: CPU, память, диск, GPU, температура в нагрузке и простое. Найди узкие места и дай план.»
Cat: PERFORMANCE | Diagnostics
Diff: L2 | Tools: perfmon, benchmarks | Web0 Code1 Files1 Vision0 Long1 | Auto 7
Why: «компьютер тормозит» — симптом, диагностика находит причину
Caps: performance diagnostics, bottleneck identification

### 932 — Разгон (оверклокинг) под контролем
«Джарвис, помоги безопасно разогнать [CPU/GPU/память]: профили, напряжения, температуры, стресс-тесты, стабильность, откат при проблемах.»
Cat: PERFORMANCE | Overclocking
Diff: L4 | Tools: OC tools | Web1 Code1 Files1 Vision0 Long0 | Auto 6
Why: разгон без контроля температур убивает железо
Caps: overclocking, stability testing, thermal limits

### 933 — Оптимизация запуска системы
«Джарвис, ускорь запуск системы: автозагрузка, службы, планировщик, BIOS-настройки, быстрая загрузка. Замерь время до/после.»
Cat: PERFORMANCE | Boot
Diff: L2 | Tools: startup tools | Web0 Code1 Files1 Vision0 Long0 | Auto 6
Why: минуты, сэкономленные на загрузке, складываются в часы за год
Caps: boot optimization, startup pruning, boot time tracking

### 934 — Управление памятью
«Джарвис, проанализируй использование памяти: утечки, кэши, файл подкачки, приложения-пожиратели. Настрой и объясни изменения.»
Cat: PERFORMANCE | Memory
Diff: L2 | Tools: memory tools | Web0 Code1 Files1 Vision0 Long0 | Auto 6
Why: утечка памяти тихо убивает производительность за дни
Caps: memory analysis, leak detection, pagefile tuning

### 935 — Профилирование приложения
«Джарвис, профилируй [приложение]: время по функциям, аллокации, блокировки, I/O. Найди топ-10 проблем и предложи оптимизации с кодом.»
Cat: PERFORMANCE | Profiling
Diff: L3 | Tools: profilers | Web0 Code1 Files1 Vision0 Long1 | Auto 8
Why: профилирование заменяет догадки о медленности фактами
Caps: application profiling, hotspot analysis, optimization suggestions

### 936 — Оптимизация игрового компьютера
«Джарвис, оптимизируй ПК для игр: драйверы, фоновые процессы, графические настройки под [железо], разгон, охлаждение, замер FPS до/после.»
Cat: PERFORMANCE | Gaming
Diff: L2 | Tools: gaming tools | Web1 Code1 Files1 Vision0 Long1 | Auto 7
Why: правильная настройка даёт +20–40% FPS без затрат на железо
Caps: gaming optimization, fps tuning, driver management

### 937 — Ускорение браузера
«Джарвис, ускорь [браузер]: расширения, кэш, профили, аппаратное ускорение, фоновые вкладки, замер времени загрузки страниц до/после.»
Cat: PERFORMANCE | Browser
Diff: L1 | Tools: browser tools | Web0 Code1 Files1 Vision0 Long0 | Auto 6
Why: медленный браузер съедает больше времени, чем любая другая программа
Caps: browser speedup, extension diet, cache tuning

### 938 — Обслуживание накопителя (SSD/HDD)
«Джарвис, проверь здоровье накопителя: SMART, TRIM, фрагментация, износ, ошибки. Выполни обслуживание и дай прогноз срока службы.»
Cat: PERFORMANCE | Storage
Diff: L2 | Tools: smart tools | Web0 Code1 Files1 Vision0 Long0 | Auto 6
Why: здоровье диска — вопрос не скорости, а потери данных
Caps: smart health, trim maintenance, lifespan prediction

### 939 — Термальная диагностика
«Джарвис, проверь температуры: CPU, GPU, чипсет, накопители, корпус. Найди перегрев, проверь термопасту и вентиляцию, дай план решения.»
Cat: PERFORMANCE | Thermals
Diff: L2 | Tools: thermal tools | Web0 Code1 Files1 Vision0 Long0 | Auto 6
Why: перегрев вызывает троттлинг, который ощущается как «тормоза»
Caps: thermal monitoring, throttling detection, cooling plan

### 940 — Управление питанием
«Джарвис, настрой электропитание: план [баланс/макс. производительность], спящий режим, поведение крышки, гибернация, влияние на производительность.»
Cat: PERFORMANCE | Power
Diff: L1 | Tools: power settings | Web0 Code1 Files1 Vision0 Long0 | Auto 5
Why: план питания молча ограничивает производительность до 30%
Caps: power plan tuning, sleep behavior, perf/power balance

### 941 — Оптимизация ноутбука
«Джарвис, оптимизируй ноутбук: автономность, фоновые задачи, охлаждение в тонком корпусе, режимы графики (iGPU/dGPU), ускорение загрузки.»
Cat: PERFORMANCE | Laptop
Diff: L2 | Tools: laptop tools | Web0 Code1 Files1 Vision0 Long0 | Auto 6
Why: ноутбук требует баланса производительности и автономности
Caps: laptop tuning, battery optimization, hybrid graphics

### 942 — Контроль фоновых процессов
«Джарвис, разбери фоновые процессы: что реально нужно, что жрёт ресурсы, агенты обновлений, синхронизации. Составь белый список и план отключений.»
Cat: PERFORMANCE | Processes
Diff: L1 | Tools: process tools | Web0 Code1 Files0 Vision0 Long0 | Auto 6
Why: десятки фоновых агентов крадут ресурсы по чуть-чуть — и заметно суммарно
Caps: background process audit, resource recovery, whitelist policy

### 943 — Настройка кэширования
«Джарвис, настрой кэширование для [задача/приложение]: кэши, размеры, политики, место хранения, очистка. Измерь эффект на скорость.»
Cat: PERFORMANCE | Caching
Diff: L2 | Tools: cache config | Web0 Code1 Files1 Vision0 Long0 | Auto 6
Why: кэш — самый дешёвый способ ускорения повторяющихся операций
Caps: cache configuration, hit rate analysis, invalidation policy

### 944 — Оптимизация сервера
«Джарвис, оптимизируй [сервер]: настройки ОС, ядра, лимиты, сетевые буферы, [веб-сервер/база]. Нагрузочный тест и сравнение до/после.»
Cat: PERFORMANCE | Server
Diff: L4 | Tools: server tools | Web0 Code1 Files1 Vision0 Long1 | Auto 8
Why: серверная оптимизация экономит железо и деньги на масштабирование
Caps: server tuning, kernel parameters, load testing

### 945 — Нагрузочное тестирование
«Джарвис, проведи нагрузочный тест [сервис]: сценарии [N] пользователей, метрики (латентность, ошибки, пропускная способность), пределы и рекомендации.»
Cat: PERFORMANCE | Testing
Diff: L3 | Tools: load tools | Web0 Code1 Files0 Vision0 Long1 | Auto 8
Why: нагрузочный тест показывает предел раньше, чем это сделают пользователи
Caps: load testing, capacity limits, scalability planning

### 946 — Ускорение загрузки приложений
«Джарвис, ускорь запуск [приложений]: предзагрузка, приоритеты, SSD-размещение, горячий кэш, отключение ненужных плагинов.»
Cat: PERFORMANCE | Apps
Diff: L1 | Tools: launch tools | Web0 Code1 Files1 Vision0 Long0 | Auto 6
Why: секунды на каждом запуске приложения складываются в часы
Caps: app launch speedup, preload config, plugin pruning

### 947 — Бенчмарки системы
«Джарвис, прогони бенчмарки: CPU, GPU, диск, память. Сравни с [референс], оцени состояние железа и несоответствия ожиданиям.»
Cat: PERFORMANCE | Benchmarking
Diff: L1 | Tools: benchmarks | Web0 Code1 Files0 Vision0 Long1 | Auto 6
Why: бенчмарк объективно показывает, на что способно железо
Caps: benchmarking, reference comparison, degradation detection

### 948 — Ограничение ресурсов для процессов
«Джарвис, ограничь ресурсы для [приложения]: CPU, память, приоритет, изоляция. Проверь, что система не страдает от одного процесса.»
Cat: PERFORMANCE | Control
Diff: L2 | Tools: resource control | Web0 Code1 Files1 Vision0 Long0 | Auto 6
Why: один неконтролируемый процесс способен положить всю систему
Caps: resource limits, priority management, process isolation

### 949 — Оптимизация хранилища
«Джарвис, оптимизируй хранилище: файловые системы, размеры кластеров, кэши диска, размещение горячих данных, RAID-производительность.»
Cat: PERFORMANCE | Storage
Diff: L3 | Tools: storage tools | Web0 Code1 Files1 Vision0 Long0 | Auto 7
Why: производительность диска — узкое место большинства рабочих станций
Caps: storage optimization, fs tuning, hot data placement

### 950 — План апгрейда железа
«Джарвис, оцени необходимость апгрейда: где реальные узкие места [метрики], какие компоненты дадут наибольший эффект за [бюджет], совместимость, план замены.»
Cat: PERFORMANCE | Hardware
Diff: L2 | Tools: bottleneck analysis | Web1 Code1 Files0 Vision0 Long0 | Auto 6
Why: апгрейд без измерения — трата денег не туда
Caps: upgrade planning, bottleneck analysis, budget allocation

### 951 — Производительность виртуализации
«Джарвис, оптимизируй виртуализацию: ресурсы VM, вложенная виртуализация, паравиртуальные драйверы, снапшоты и их влияние, изоляция производительности.»
Cat: PERFORMANCE | Virtualization
Diff: L3 | Tools: hypervisor tools | Web0 Code1 Files1 Vision0 Long0 | Auto 7
Why: VM без настройки может быть в 2 раза медленнее физической машины
Caps: vm performance, hypervisor tuning, snapshot strategy

### 952 — Отчёт о производительности
«Джарвис, собери отчёт о производительности [системы]: метрики за [период], тренды, инциденты, сравнение с нормой, рекомендации.»
Cat: PERFORMANCE | Reporting
Diff: L1 | Tools: perfmon, reports | Web0 Code1 Files1 Vision0 Long1 | Auto 7
Why: регулярные отчёты показывают деградацию до того, как она станет болью
Caps: performance reporting, trend analysis, baseline comparison

### 953 — Оптимизация под конкретную задачу
«Джарвис, настрой систему под [задача: видеомонтаж, 3D, компиляция, аналитика]: приоритеты, память, диски, кэши, параметры приложений. Замерь результат.»
Cat: PERFORMANCE | Tuning
Diff: L2 | Tools: workload tuning | Web0 Code1 Files1 Vision0 Long0 | Auto 7
Why: универсальная система проигрывает системе, настроенной под задачу
Caps: workload optimization, use-case tuning

### 954 — Настройка рабочей станции
«Джарвис, настрой мою рабочую станцию «с нуля»: ОС, драйверы, приложения, настройки, синхронизация, производительность и безопасность по чек-листу.»
Cat: PERFORMANCE | Setup
Diff: L3 | Tools: provisioning | Web0 Code1 Files1 Vision0 Long0 | Auto 8
Why: правильно подготовленная станция экономит часы еженедельно
Caps: workstation provisioning, setup checklist, baseline config

### 955 — Профилактика деградации
«Джарвис, составь план профилактики: чистка, обновления, дефрагментация/TRIM, мониторинг, бэкапы, периодичность работ. Начни выполнять.»
Cat: PERFORMANCE | Maintenance
Diff: L1 | Tools: maintenance plan | Web0 Code1 Files1 Vision0 Long0 | Auto 7
Why: профилактика дешевле и надёжнее лечения
Caps: maintenance scheduling, preventive care, health baseline

### 956 — Системный мониторинг
«Джарвис, разверни мониторинг [системы]: CPU, память, диск, сеть, температура в реальном времени, история, пороговые алерты.»
Cat: MONITORING | System
Diff: L2 | Tools: monitoring agents | Web0 Code1 Files1 Vision0 Long1 | Auto 8
Why: без мониторинга проблемы замечают, когда уже поздно
Caps: system monitoring, threshold alerts, historical data

### 957 — Мониторинг ресурсов в реальном времени
«Джарвис, покажи живой мониторинг ресурсов: графики CPU/память/диск/сеть, топ-процессы, корреляция событий. Обновление каждые [N] секунд.»
Cat: MONITORING | Live
Diff: L1 | Tools: htop, perfmon | Web0 Code1 Files0 Vision0 Long0 | Auto 6
Why: живая картина ресурсов позволяет ловить всплески в моменте
Caps: live resource view, process correlation, spike detection

### 958 — Мониторинг сервисов и служб
«Джарвис, мониторь статус [служб/сервисов]: работа/остановлен, автостарт, зависимости, рестарт при падении, алерты об изменении состояния.»
Cat: MONITORING | Services
Diff: L2 | Tools: service monitors | Web0 Code1 Files0 Vision0 Long0 | Auto 8
Why: упавший фоновый сервис часто замечают только по жалобам
Caps: service monitoring, auto-restart, dependency tracking

### 959 — Мониторинг веб-сайтов
«Джарвис, мониторь [сайты]: доступность из [регионов], время ответа, ошибки HTTP, изменения контента, SSL-сроки. Алерты и еженедельный отчёт.»
Cat: MONITORING | Web
Diff: L1 | Tools: web monitors | Web1 Code1 Files0 Vision0 Long1 | Auto 8
Why: сайт — витрина бизнеса, и каждый час простоя — прямые потери
Caps: website monitoring, ssl expiry alerts, response time tracking

### 960 — Настройка алертов и уведомлений
«Джарвис, настрой систему алертов: каналы [email/telegram/SMS], правила срабатывания, пороги, дедупликация, ночной режим, кого уведомлять.»
Cat: MONITORING | Alerting
Diff: L2 | Tools: alerting systems | Web0 Code1 Files1 Vision0 Long0 | Auto 8
Why: алерт без маршрутизации — просто ещё одно письмо в спаме
Caps: alert routing, threshold design, deduplication

### 961 — Централизация логов
«Джарвис, настрой сбор логов с [источники] в одно место: агенты, форматы, ротация, хранение, поиск, доступы. Проверь полноту сбора.»
Cat: MONITORING | Logs
Diff: L3 | Tools: log collectors | Web0 Code1 Files1 Vision0 Long1 | Auto 8
Why: логи на сотнях машин без централизации бесполезны
Caps: log aggregation, retention policy, searchable archive

### 962 — Мониторинг температуры и железа
«Джарвис, настрой мониторинг железа: температуры, вентиляторы, напряжения, SMART дисков. Алерты при перегреве и деградации.»
Cat: MONITORING | Hardware
Diff: L1 | Tools: hardware monitors | Web0 Code1 Files0 Vision0 Long0 | Auto 7
Why: перегрев убивает железо тихо и безвозвратно
Caps: hardware telemetry, thermal alerts, fan monitoring

### 963 — Мониторинг процессов и приложений
«Джарвис, мониторь [процессы/приложения]: потребление ресурсов, «зависания», аварийные завершения, соответствие ожиданиям. Алерты при аномалиях.»
Cat: MONITORING | Apps
Diff: L1 | Tools: process monitors | Web0 Code1 Files0 Vision0 Long0 | Auto 7
Why: аварийные падения приложений — первый симптом деградации системы
Caps: process monitoring, crash detection, resource anomalies

### 964 — Мониторинг дискового пространства
«Джарвис, мониторь диски: заполнение, скорость, здоровье, прогноз заполнения. Алерты при [порог]% и при ошибках SMART.»
Cat: MONITORING | Storage
Diff: L1 | Tools: disk monitors | Web0 Code1 Files0 Vision0 Long0 | Auto 7
Why: полный диск останавливает работу сервисов без предупреждения
Caps: disk monitoring, fill-rate forecasting, smart alerts

### 965 — Мониторинг сети
«Джарвис, мониторь сетевые метрики: трафик по интерфейсам, ошибки, потери, загрузка каналов, доступность [узлов]. Алерты и отчёты.»
Cat: MONITORING | Network
Diff: L2 | Tools: network monitors | Web0 Code1 Files0 Vision0 Long1 | Auto 8
Why: насыщенный канал объясняет деградацию всех сервисов сразу
Caps: network monitoring, interface errors, utilization tracking

### 966 — Мониторинг приложения изнутри
«Джарвис, добавь в [приложение] внутренний мониторинг: метрики бизнеса и техники, трейсы, логи, алерты по [ключевым метрикам].»
Cat: MONITORING | APM
Diff: L4 | Tools: APM tools | Web0 Code1 Files1 Vision0 Long1 | Auto 8
Why: внешний мониторинг видит симптомы, внутренний — причины
Caps: apm integration, business metrics, distributed tracing

### 967 — Мониторинг SLA
«Джарвис, настрой мониторинг SLA для [сервисы]: аптайм-цели, окна обслуживания, отчёты о выполнении SLA, алерты при риске нарушения.»
Cat: MONITORING | SLA
Diff: L2 | Tools: sla tools | Web0 Code1 Files0 Vision0 Long0 | Auto 7
Why: SLA без измерителя — обещание, которое невозможно проверить
Caps: sla tracking, availability windows, compliance reporting

### 968 — Дашборд мониторинга
«Джарвис, собери единый дашборд мониторинга: ключевые метрики [систем/сервисов], статусы, тренды, алерты в одном месте, доступ для [команда].»
Cat: MONITORING | Dashboards
Diff: L2 | Tools: dashboards | Web0 Code1 Files1 Vision0 Long1 | Auto 8
Why: единый экран состояния заменяет десятки открытых вкладок
Caps: dashboard design, metric unification, team sharing

### 969 — Анализ трендов метрик
«Джарвис, проанализируй [метрики] за [период]: сезонность, тренды, аномальные дни, корреляции с событиями. Сделай прогноз и рекомендации.»
Cat: MONITORING | Analysis
Diff: L2 | Tools: trend analysis | Web0 Code1 Files1 Vision0 Long1 | Auto 8
Why: тренды предсказывают проблемы за недели до алерта
Caps: metric trends, anomaly correlation, capacity forecast

### 970 — Мониторинг обновлений и лицензий
«Джарвис, мониторь [ПО/лицензии]: доступные обновления, истечение подписок и сертификатов, метки времени. Алерты заранее, план продления.»
Cat: MONITORING | Lifecycle
Diff: L1 | Tools: lifecycle monitors | Web1 Code1 Files0 Vision0 Long0 | Auto 7
Why: просроченная лицензия отключает сервисы в самый неподходящий момент
Caps: license expiry tracking, update availability, renewal alerts

### 971 — Мониторинг безопасности
«Джарвис, настрой непрерывный мониторинг безопасности: события [Windows/сервисов], попытки входа, изменения файлов, алерты по [правила].»
Cat: SECURITY | Monitoring
Diff: L3 | Tools: security monitors | Web0 Code1 Files1 Vision0 Long1 | Auto 8
Why: мониторинг безопасности — разница между неделей и днём обнаружения
Caps: security event monitoring, file integrity, auth monitoring

### 972 — Синтетический мониторинг
«Джарвис, настрой синтетические проверки [сценарии пользователя] на [сервис]: время ответа, успешность шагов, из [регионов], алерты при регрессии.»
Cat: MONITORING | Synthetic
Diff: L3 | Tools: synthetic tools | Web1 Code1 Files0 Vision0 Long1 | Auto 8
Why: синтетика ловит регрессии до того, как их заметят пользователи
Caps: synthetic monitoring, user journey checks, global probes

### 973 — Отчёты мониторинга
«Джарвис, собирай периодические отчёты мониторинга: аптайм, инциденты, метрики, алерты, действия. Рассылка [кому] по расписанию.»
Cat: MONITORING | Reporting
Diff: L1 | Tools: report generation | Web0 Code1 Files1 Vision0 Long0 | Auto 7
Why: отчёт о мониторинге делает работу инфраструктуры видимой для бизнеса
Caps: monitoring reports, incident digests, stakeholder updates

### 974 — Оповещения по расписанию
«Джарвис, настрой периодические сводки: утренний отчёт [содержание], вечерний контроль, еженедельная аналитика. В [каналы] по [время].»
Cat: MONITORING | Scheduled
Diff: L1 | Tools: scheduling | Web0 Code1 Files1 Vision0 Long0 | Auto 8
Why: регулярные сводки формируют привычку контроля вместо авралов
Caps: scheduled digests, morning briefing, weekly analytics

### 975 — Реагирование на алерты
«Джарвис, пропиши сценарии реагирования на алерты [типы]: кто что делает по шагам, таймауты, эскалация, постмортем. Отработай на учебной тревоге.»
Cat: MONITORING | Response
Diff: L2 | Tools: runbooks | Web0 Code1 Files1 Vision0 Long0 | Auto 7
Why: готовые сценарии реагирования сокращают время простоя в разы
Caps: alert response runbooks, drill testing, escalation paths

### 976 — Каналы алертов и уведомлений
«Джарвис, настрой каналы алертов: [email/Telegram/Slack/SMS/звонок] с приоритетами, слияние дублей, режим тишины, тест доставки каждого канала.»
Cat: ALERTING | Channels
Diff: L1 | Tools: notification services | Web1 Code0 Files1 Vision0 Long0 | Auto 7
Why: алерт в нечитаемом канале — то же самое, что отсутствие алерта
Caps: alert channels, delivery testing, quiet hours

### 977 — Приоритизация алертов
«Джарвис, настрой приоритеты алертов: критичность, влияние, срочность, дедупликация, подавление шумных. Чтобы в 3 часа ночи будил только реальный пожар.»
Cat: ALERTING | Prioritization
Diff: L2 | Tools: alert rules | Web0 Code1 Files1 Vision0 Long0 | Auto 7
Why: «синдром кричащего ребёнка» — когда все алерты одинаково кричат, не слышно ни одного
Caps: alert prioritization, noise reduction, severity mapping

### 978 — Дежурства и ротация on-call
«Джарвис, настрой дежурства: календарь on-call [команда], эскалация по цепочке, правила передачи, отчёты о нагрузке дежурного.»
Cat: ALERTING | On-call
Diff: L2 | Tools: on-call tools | Web0 Code1 Files0 Vision0 Long0 | Auto 7
Why: неясное дежурство — причина выгорания и пропущенных инцидентов
Caps: on-call schedule, escalation chain, fair rotation

### 979 — Эскалация инцидентов
«Джарвис, настрой эскалацию: уровни [L1→L2→L3], таймауты, автоматическое подключение [ролей], историю эскалаций, постмортем по итогам.»
Cat: ALERTING | Escalation
Diff: L2 | Tools: escalation design | Web0 Code1 Files1 Vision0 Long0 | Auto 7
Why: инцидент без эскалации застревает у первого ответившего
Caps: escalation design, timeout automation, incident history

### 980 — Анализ ложных срабатываний
«Джарвис, проанализируй алерты за [период]: сколько ложных, по каким правилам, какой ущерб от шума. Скорректируй правила и пороги, снизь шум на [N]%.»
Cat: ALERTING | Quality
Diff: L2 | Tools: alert analytics | Web0 Code1 Files1 Vision0 Long1 | Auto 7
Why: ложные алерты разрушают доверие к системе мониторинга
Caps: false positive analysis, rule tuning, alert quality metrics
---
### 981 — Бизнес-план с нуля
Джарвис, составь бизнес-план: резюме проекта, анализ рынка, описание продукта, модель монетизации, план продаж, финансовый прогноз на 3 года и анализ рисков — в виде структурированного документа.
Cat: BUSINESS | Planning
Diff: L3 | Tools: documents, spreadsheets, research | Web1 Code0 Files1 Vision0 Long1 | Auto 7
Why: бизнес-план — фундамент стратегии и привлечения инвестиций
Caps: business planning, market analysis, financial forecasting, risk assessment
---

### 982 — Анализ конкурентов
Джарвис, проведи анализ конкурентов: собери данные по 5 ключевым игрокам рынка, сравни продукты, цены, каналы продвижения и сильные стороны, оформи сравнительную таблицу и выводы.
Cat: BUSINESS | Competitive Intelligence
Diff: L3 | Tools: research, spreadsheets, documents | Web1 Code0 Files1 Vision0 Long1 | Auto 7
Why: понимание конкурентов определяет позиционирование и стратегию
Caps: competitive analysis, market research, benchmarking, positioning
---

### 983 — SWOT-анализ компании
Джарвис, проведи SWOT-анализ нашей компании: сильные и слабые стороны, возможности и угрозы, затем предложи стратегические действия на основе матрицы.
Cat: BUSINESS | Strategy
Diff: L2 | Tools: documents, brainstorming | Web0 Code0 Files1 Vision0 Long0 | Auto 6
Why: SWOT связывает внутренние ресурсы с рыночными возможностями
Caps: swot analysis, strategic planning, risk identification
---

### 984 — Юнит-экономика проекта
Джарвис, рассчитай юнит-экономику продукта: цена, себестоимость, CAC, LTV, маржа и срок окупаемости клиента — построй модель в таблице и покажи, при каких метриках бизнес выходит в плюс.
Cat: BUSINESS | Unit Economics
Diff: L3 | Tools: spreadsheets, math | Web0 Code0 Files1 Vision0 Long0 | Auto 7
Why: юнит-экономика показывает, масштабируется ли бизнес на самом деле
Caps: unit economics, cac, ltv, break-even analysis, spreadsheet modeling
---

### 985 — OKR-планирование квартала
Джарвис, помоги сформулировать OKR на квартал: цели и ключевые результаты для каждого направления, с измеримыми метриками и сроками.
Cat: BUSINESS | OKR
Diff: L2 | Tools: documents, planning | Web0 Code0 Files1 Vision0 Long0 | Auto 6
Why: OKR фокусирует команду на приоритетах и измеримых результатах
Caps: okr, goal setting, kpi definition, quarterly planning
---

### 986 — Дашборд ключевых метрик бизнеса
Джарвис, создай дашборд ключевых бизнес-метрик: выручка, прибыль, CAC, LTV, конверсия, отток — с графиками динамики и автоматическими выводами.
Cat: BUSINESS | Analytics
Diff: L3 | Tools: spreadsheets, charts, data | Web0 Code0 Files1 Vision0 Long1 | Auto 7
Why: единый дашборд даёт управленческую картину без ручной сборки
Caps: kpi dashboard, business analytics, data visualization, reporting
---

### 987 — P&L отчёт за период
Джарвис, подготовь отчёт о прибылях и убытках за указанный период: выручка, себестоимость, операционные расходы, EBITDA и чистая прибыль — с пояснениями отклонений.
Cat: BUSINESS | Finance Reports
Diff: L3 | Tools: spreadsheets, documents | Web0 Code0 Files1 Vision0 Long0 | Auto 7
Why: P&L показывает реальную прибыльность операций за период
Caps: p&l report, financial statements, ebitda, variance analysis
---

### 988 — Cash flow прогноз
Джарвис, построй прогноз движения денежных средств на 6 месяцев: поступления, платежи, кассовые разрывы — и предложи, как их закрыть.
Cat: BUSINESS | Cash Management
Diff: L3 | Tools: spreadsheets, math | Web0 Code0 Files1 Vision0 Long1 | Auto 7
Why: кассовый разрыв — частая причина гибели растущих компаний
Caps: cash flow forecasting, liquidity planning, gap analysis
---

### 989 — Воронка продаж и её аналитика
Джарвис, опиши воронку продаж компании по этапам, рассчитай конверсии между этапами и укажи самые слабые места, где теряются клиенты.
Cat: BUSINESS | Sales
Diff: L2 | Tools: spreadsheets, data | Web0 Code0 Files1 Vision0 Long0 | Auto 6
Why: воронка показывает точные места потерь и точки роста выручки
Caps: sales funnel, conversion analysis, pipeline management
---

### 990 — Когортный анализ клиентов
Джарвис, проведи когортный анализ: сгруппируй клиентов по месяцу привлечения и покажи удержание, повторные покупки и LTV по когортам в таблице с цветовой подсветкой.
Cat: BUSINESS | Customer Analytics
Diff: L3 | Tools: spreadsheets, data, charts | Web0 Code0 Files1 Vision0 Long0 | Auto 7
Why: когорты выявляют, какие каналы приносят ценных клиентов
Caps: cohort analysis, retention, ltv, customer analytics
---

### 991 — Расчёт точки безубыточности
Джарвис, рассчитай точку безубыточности: постоянные и переменные расходы, маржинальность, необходимый объём продаж в штуках и деньгах.
Cat: BUSINESS | Finance
Diff: L2 | Tools: spreadsheets, math | Web0 Code0 Files1 Vision0 Long0 | Auto 6
Why: точка безубыточности определяет минимальный план продаж
Caps: break-even analysis, cost structure, margin calculation
---

### 992 — Стратегия ценообразования
Джарвис, разработай стратегию ценообразования для продукта: анализ цен конкурентов, восприятие ценности, варианты тарифов и психологические пороги цены.
Cat: BUSINESS | Pricing
Diff: L3 | Tools: research, spreadsheets, documents | Web1 Code0 Files1 Vision0 Long1 | Auto 7
Why: цена напрямую определяет маржу и позиционирование продукта
Caps: pricing strategy, value-based pricing, competitor pricing, tiered plans
---

### 993 — Бизнес-модель canvas
Джарвис, заполни бизнес-модель canvas: ключевые партнёры, активности, ресурсы, ценностное предложение, отношения с клиентами, каналы, сегменты, структура затрат и потоки дохода.
Cat: BUSINESS | Business Model
Diff: L2 | Tools: documents, diagrams | Web0 Code0 Files1 Vision0 Long0 | Auto 6
Why: canvas даёт целостный взгляд на бизнес-модель на одной странице
Caps: business model canvas, value proposition, revenue streams
---

### 994 — Инвестиционный питч для инвесторов
Джарвис, подготовь инвестиционный питч: проблема, решение, рынок, продукт, бизнес-модель, traction, команда и запрашиваемая сумма — структура для презентации и речь на 10 минут.
Cat: BUSINESS | Fundraising
Diff: L3 | Tools: documents, presentations | Web0 Code0 Files1 Vision0 Long0 | Auto 7
Why: сильный питч повышает шансы на привлечение инвестиций
Caps: investor pitch, fundraising, pitch deck, storytelling
---

### 995 — План проекта и управление задачами
Джарвис, составь план проекта: этапы, задачи, ответственные, сроки, зависимости и риски — оформи в виде таблицы с диаграммой Ганта.
Cat: BUSINESS | Project Management
Diff: L2 | Tools: documents, spreadsheets, planning | Web0 Code0 Files1 Vision0 Long0 | Auto 6
Why: чёткий план снижает риски срыва сроков и дублирования работы
Caps: project planning, gantt chart, task management, milestone tracking
---

### 996 — KPI-система для команды
Джарвис, разработай систему KPI для команды: ключевые показатели по ролям, цели на квартал, частоту замера и формат отчётности.
Cat: BUSINESS | Performance
Diff: L2 | Tools: documents, spreadsheets | Web0 Code0 Files1 Vision0 Long0 | Auto 6
Why: KPI связывают работу каждого сотрудника с целями компании
Caps: kpi system, performance metrics, team goals, reporting cadence
---

### 997 — Анализ рынка: TAM/SAM/SOM
Джарвис, оцени объём рынка для продукта: рассчитай TAM, SAM и SOM по методологии сверху вниз и снизу вверх, с обоснованием допущений.
Cat: BUSINESS | Market Research
Diff: L3 | Tools: research, spreadsheets | Web1 Code0 Files1 Vision0 Long0 | Auto 7
Why: TAM/SAM/SOM показывают инвесторам реалистичный потенциал рынка
Caps: tam sam som, market sizing, market research, top-down bottom-up
---

### 998 — Юридическая структура бизнеса
Джарвис, сравни варианты юридической структуры бизнеса: ИП, ООО, самозанятость — по налогам, ответственности, сложности ведения и дай рекомендацию для нашей ситуации.
Cat: BUSINESS | Legal
Diff: L2 | Tools: research, documents | Web1 Code0 Files1 Vision0 Long0 | Auto 6
Why: выбор организационной формы влияет на налоги и риски на годы вперёд
Caps: legal structure, sole proprietorship, llc, tax implications
---

### 999 — Партнёрские соглашения
Джарвис, подготовь структуру партнёрского соглашения: цели сотрудничества, роли, разделение прибыли, интеллектуальная собственность, сроки и условия выхода.
Cat: BUSINESS | Partnerships
Diff: L2 | Tools: documents, templates | Web0 Code0 Files1 Vision0 Long0 | Auto 6
Why: письменное соглашение предотвращает конфликты с партнёрами
Caps: partnership agreement, profit sharing, ip ownership, contract structure
---

### 1000 — Customer Development интервью
Джарвис, составь скрипт customer development интервью: вопросы о проблемах, текущих решениях, желаниях и готовности платить — с инструкцией по проведению и анализу ответов.
Cat: BUSINESS | Customer Research
Diff: L2 | Tools: documents, research | Web0 Code0 Files1 Vision0 Long0 | Auto 6
Why: custdev проверяет гипотезы о клиентах до дорогой разработки
Caps: customer development, interview script, problem validation, willingness to pay
---

### 1001 — План масштабирования бизнеса
Джарвис, разработай план масштабирования: какие процессы автоматизировать, когда нанимать, какие метрики контролировать и как избежать типичных ошибок роста.
Cat: BUSINESS | Growth
Diff: L3 | Tools: documents, planning | Web0 Code0 Files1 Vision0 Long1 | Auto 7
Why: рост без плана часто разрушает операционную устойчивость
Caps: scaling plan, growth strategy, process automation, hiring plan
---

### 1002 — Анализ эффективности команды
Джарвис, проанализируй эффективность команды: загрузка, результаты, узкие места и перегрузки — предложи перераспределение задач и улучшения процессов.
Cat: BUSINESS | Management
Diff: L2 | Tools: spreadsheets, documents | Web0 Code0 Files1 Vision0 Long0 | Auto 6
Why: невидимые перегрузки снижают продуктивность всей команды
Caps: team efficiency, workload analysis, bottleneck detection, process improvement
---

### 1003 — Анализ оттока клиентов
Джарвис, проанализируй отток клиентов: выяви паттерны ухода, рассчитай churn rate и LTV, предложи меры удержания для проблемных сегментов.
Cat: BUSINESS | Customer Retention
Diff: L3 | Tools: spreadsheets, data | Web0 Code0 Files1 Vision0 Long0 | Auto 7
Why: снижение оттока часто дешевле, чем привлечение новых клиентов
Caps: churn analysis, retention strategy, churn rate, customer lifetime value
---

### 1004 — План выхода на новый рынок
Джарвис, составь план выхода на новый рынок: анализ спроса, конкуренция, правовые требования, локализация продукта, каналы дистрибуции и бюджет запуска.
Cat: BUSINESS | Expansion
Diff: L3 | Tools: research, documents, spreadsheets | Web1 Code0 Files1 Vision0 Long1 | Auto 7
Why: выход на новый рынок требует отдельной стратегии, а не копии старой
Caps: market entry, localization, distribution channels, launch budget
---

### 1005 — Упаковка продукта и ценностное предложение
Джарвис, упакуй продукт: сформулируй ценностное предложение, оффер, ключевые выгоды и отличия от конкурентов — для лендинга и продающих материалов.
Cat: BUSINESS | Product Marketing
Diff: L2 | Tools: documents, brainstorming | Web0 Code0 Files1 Vision0 Long0 | Auto 6
Why: чёткая упаковка продукта повышает конверсию продаж
Caps: value proposition, offer creation, product messaging, differentiation
---

### 1006 — Анализ финансовой устойчивости
Джарвис, проведи анализ финансовой устойчивости компании: ликвидность, автономия, рентабельность и оборачиваемость — рассчитай коэффициенты и сравни с нормативами.
Cat: BUSINESS | Financial Analysis
Diff: L3 | Tools: spreadsheets, data | Web0 Code0 Files1 Vision0 Long0 | Auto 7
Why: коэффициенты выявляют скрытые финансовые риски до кризиса
Caps: financial stability, liquidity ratios, profitability, solvency analysis
---

### 1007 — Дорожная карта продукта
Джарвис, построй дорожную карту продукта на год: темы, фичи, этапы, даты релизов и критерии готовности — с учётом приоритетов и ресурсов команды.
Cat: BUSINESS | Product Management
Diff: L3 | Tools: documents, diagrams, planning | Web0 Code0 Files1 Vision0 Long1 | Auto 7
Why: roadmap согласует ожидания команды, клиентов и инвесторов
Caps: product roadmap, feature planning, release planning, prioritization
---

### 1008 — Анализ продаж по каналам
Джарвис, проанализируй продажи по каналам: сравни выручку, конверсию и стоимость привлечения по каждому каналу, определи лучшие и предложи перераспределение бюджета.
Cat: BUSINESS | Sales Analytics
Diff: L2 | Tools: spreadsheets, data | Web0 Code0 Files1 Vision0 Long0 | Auto 6
Why: часть каналов обычно приносит 80% результата — их нужно усилить
Caps: channel analysis, sales analytics, budget allocation, roi comparison
---

### 1009 — План реорганизации процессов
Джарвис, проанализируй текущие бизнес-процессы, найди дублирование и узкие места и предложи план реорганизации с новыми регламентами и ответственными.
Cat: BUSINESS | Operations
Diff: L3 | Tools: documents, diagrams | Web0 Code0 Files1 Vision0 Long1 | Auto 7
Why: устранение дублей в процессах экономит время и деньги компании
Caps: process reengineering, workflow optimization, bottleneck analysis, SOP
---

### 1010 — Оценка стоимости бизнеса
Джарвис, оцени стоимость бизнеса несколькими методами: DCF, мультипликаторы, сравнительный подход — с обоснованием допущений и диапазоном оценки.
Cat: BUSINESS | Valuation
Diff: L3 | Tools: spreadsheets, math, research | Web1 Code0 Files1 Vision0 Long0 | Auto 7
Why: объективная оценка нужна для продажи, инвестиций и партнёрства
Caps: business valuation, dcf model, multiples, comparables
---

### 1011 — Личный финансовый план
Джарвис, составь личный финансовый план: доходы, расходы, накопления, инвестиции, страховки и цели на год вперёд — с конкретными шагами.
Cat: FINANCE | Personal Finance
Diff: L2 | Tools: spreadsheets, documents | Web0 Code0 Files1 Vision0 Long0 | Auto 6
Why: план превращает финансовые цели в конкретные ежемесячные действия
Caps: personal financial plan, budgeting, savings goals, financial roadmap
---

### 1012 — Бюджет на месяц
Джарвис, составь бюджет на месяц с категориями: обязательные расходы, питание, транспорт, развлечения, накопления — и покажи, где можно сэкономить.
Cat: FINANCE | Budgeting
Diff: L1 | Tools: spreadsheets | Web0 Code0 Files1 Vision0 Long0 | Auto 6
Why: бюджет по категориям делает траты видимыми и управляемыми
Caps: monthly budget, expense categories, savings, spending analysis
---

### 1013 — Анализ расходов и оптимизация
Джарвис, проанализируй мои расходы за последние месяцы: найди аномалии, повторяющиеся платежи и категории с перерасходом, предложи план оптимизации.
Cat: FINANCE | Spending Analysis
Diff: L2 | Tools: spreadsheets, data | Web0 Code0 Files1 Vision0 Long0 | Auto 6
Why: большинство людей не знают, куда реально уходят деньги
Caps: expense analysis, subscription audit, spending patterns, cost cutting
---

### 1014 — Структура инвестиционного портфеля
Джарвис, предложи структуру инвестиционного портфеля под мою цель и риск-профиль: распределение по классам активов, инструменты и правила ребалансировки.
Cat: FINANCE | Investing
Diff: L3 | Tools: research, spreadsheets, documents | Web1 Code0 Files1 Vision0 Long1 | Auto 7
Why: диверсификация по классам активов снижает риск без потери доходности
Caps: portfolio allocation, asset classes, risk profile, rebalancing
---

### 1015 — Дивидендная стратегия
Джарвис, разработай дивидендную стратегию: подбери акции с устойчивыми дивидендами, рассчитай дивидендную доходность и составь план реинвестирования.
Cat: FINANCE | Dividend Investing
Diff: L2 | Tools: research, spreadsheets | Web1 Code0 Files1 Vision0 Long0 | Auto 7
Why: дивиденды дают стабильный денежный поток и защиту от инфляции
Caps: dividend strategy, dividend yield, reinvestment, dividend stocks
---

### 1016 — Налоговое планирование
Джарвис, рассчитай мою налоговую нагрузку и предложи законные способы оптимизации: вычеты, льготы, структура доходов — с учётом моего статуса.
Cat: FINANCE | Taxes
Diff: L3 | Tools: research, spreadsheets | Web1 Code0 Files1 Vision0 Long1 | Auto 7
Why: грамотное налоговое планирование сохраняет значительную часть дохода
Caps: tax planning, tax deductions, tax optimization, tax calculator
---

### 1017 — Расчёт ипотеки или кредита
Джарвис, рассчитай ипотеку: ежемесячный платёж, переплата, общая стоимость — сравни разные сроки и ставки, покажи график платежей.
Cat: FINANCE | Loans
Diff: L2 | Tools: spreadsheets, math | Web0 Code0 Files1 Vision0 Long0 | Auto 6
Why: сравнение условий кредита экономит сотни тысяч на переплате
Caps: mortgage calculation, loan amortization, interest comparison, payment schedule
---

### 1018 — План погашения долгов
Джарвис, составь план погашения долгов: расставь кредиты по приоритету (снежный ком или лавина), рассчитай сроки и переплату по каждой стратегии.
Cat: FINANCE | Debt Management
Diff: L2 | Tools: spreadsheets, math | Web0 Code0 Files1 Vision0 Long0 | Auto 6
Why: структурированный план выхода из долгов снижает стресс и переплату
Caps: debt payoff plan, snowball method, avalanche method, debt free plan
---

### 1019 — Финансовая подушка безопасности
Джарвис, рассчитай размер финансовой подушки: обязательные расходы, срок запаса 3–6 месяцев — и составь план её накопления.
Cat: FINANCE | Emergency Fund
Diff: L1 | Tools: spreadsheets | Web0 Code0 Files1 Vision0 Long0 | Auto 6
Why: подушка защищает от непредвиденных ситуаций и долгов
Caps: emergency fund, financial cushion, savings plan, risk buffer
---

### 1020 — Пенсионное планирование
Джарвис, рассчитай, сколько нужно откладывать на пенсию: целевой капитал, ожидаемая доходность, инфляция — и предложи инструменты накопления.
Cat: FINANCE | Retirement
Diff: L3 | Tools: spreadsheets, math, research | Web1 Code0 Files1 Vision0 Long0 | Auto 7
Why: чем раньше начать, тем меньше нужно откладывать ежемесячно
Caps: retirement planning, pension calculation, compounding, retirement accounts
---

### 1021 — Фундаментальный анализ акций
Джарвис, проведи фундаментальный анализ акций компании: выручка, прибыль, долг, рентабельность, мультипликаторы P/E, P/B, EV/EBITDA — и дай заключение о справедливой стоимости.
Cat: FINANCE | Stock Analysis
Diff: L3 | Tools: research, spreadsheets | Web1 Code0 Files1 Vision0 Long1 | Auto 7
Why: фундаментальный анализ отделяет здоровые компании от переоценённых
Caps: fundamental analysis, financial ratios, pe ratio, fair value
---

### 1022 — Технический анализ рынка
Джарвис, проведи технический анализ по графику: тренд, уровни поддержки и сопротивления, индикаторы RSI, MACD, скользящие средние — и дай сценарии движения цены.
Cat: FINANCE | Technical Analysis
Diff: L2 | Tools: research, charts | Web1 Code0 Files1 Vision0 Long0 | Auto 7
Why: технический анализ помогает определить точки входа и выхода
Caps: technical analysis, support resistance, rsi, macd, moving averages
---

### 1023 — Криптопортфель и управление рисками
Джарвис, составь криптовалютный портфель с учётом моих целей: распределение между BTC, ETH и альткоинами, размер позиции, правила входа и стоп-лоссы.
Cat: FINANCE | Crypto
Diff: L2 | Tools: research, spreadsheets | Web1 Code0 Files1 Vision0 Long0 | Auto 7
Why: крипторынок крайне волатилен — нужны жёсткие правила управления риском
Caps: crypto portfolio, risk management, position sizing, stop loss
---

### 1024 — Валютные операции и хеджирование
Джарвис, проанализируй валютные риски: предложи стратегию конвертации и хеджирования для моих доходов и расходов в разных валютах.
Cat: FINANCE | Currency
Diff: L2 | Tools: research, spreadsheets | Web1 Code0 Files1 Vision0 Long0 | Auto 7
Why: валютные колебания могут незаметно съедать реальный доход
Caps: currency risk, hedging, forex conversion, exchange strategy
---

### 1025 — Подбор страховых полисов
Джарвис, подбери страховые полисы под мою ситуацию: сравни условия, покрытия и цены — и объясни, от каких рисков защищаться в первую очередь.
Cat: FINANCE | Insurance
Diff: L2 | Tools: research, documents | Web1 Code0 Files1 Vision0 Long0 | Auto 6
Why: страховка защищает от финансовых катастроф, а не от мелких неудобств
Caps: insurance comparison, coverage analysis, risk protection, policy selection
---

### 1026 — Балансовый отчёт компании
Джарвис, подготовь баланс: активы, обязательства и капитал — проверь соответствие балансовому равенству и прокомментируй структуру.
Cat: FINANCE | Accounting
Diff: L3 | Tools: spreadsheets | Web0 Code0 Files1 Vision0 Long0 | Auto 7
Why: баланс показывает финансовое состояние компании на дату
Caps: balance sheet, assets liabilities equity, accounting, financial position
---

### 1027 — Отчёт о прибылях и убытках
Джарвис, построй отчёт о прибылях и убытках: выручка, себестоимость, валовая и операционная прибыль, налоги, чистая прибыль — с анализом динамики.
Cat: FINANCE | Accounting
Diff: L3 | Tools: spreadsheets | Web0 Code0 Files1 Vision0 Long0 | Auto 7
Why: P&L объясняет, откуда берётся и куда уходит прибыль
Caps: income statement, revenue, gross profit, net income, margin analysis
---

### 1028 — Отчёт о движении денежных средств
Джарвис, подготовь отчёт о движении денежных средств: операционная, инвестиционная и финансовая деятельность — и проверь, что чистое изменение совпадает с остатком.
Cat: FINANCE | Accounting
Diff: L3 | Tools: spreadsheets | Web0 Code0 Files1 Vision0 Long0 | Auto 7
Why: прибыль может быть, а денег нет — DCF это вскрывает
Caps: cash flow statement, operating activities, investing activities, financing activities
---

### 1029 — Финансовые цели и трекинг
Джарвис, помоги определить финансовые цели на год и 5 лет: суммы, сроки, инструменты — создай трекер прогресса с автоматическим расчётом остатка.
Cat: FINANCE | Goal Tracking
Diff: L2 | Tools: spreadsheets, planning | Web0 Code0 Files1 Vision0 Long0 | Auto 6
Why: измеримые цели с трекером повышают вероятность их достижения
Caps: financial goals, goal tracking, savings tracker, milestone planning
---

### 1030 — Анализ транзакций и категоризация
Джарвис, загрузи выписку по транзакциям, категоризируй расходы, найди аномалии и подозрительные платежи и сформируй сводку по категориям.
Cat: FINANCE | Transaction Analysis
Diff: L2 | Tools: data, spreadsheets | Web0 Code0 Files1 Vision0 Long0 | Auto 6
Why: регулярный разбор выписок выявляет утечки денег и ошибки банков
Caps: transaction categorization, bank statement analysis, anomaly detection, expense summary
---

### 1031 — Сравнение банковских продуктов
Джарвис, сравни банковские продукты: карты, вклады, накопительные счета — по ставкам, комиссиям и условиям, и порекомендуй оптимальный набор.
Cat: FINANCE | Banking
Diff: L2 | Tools: research, spreadsheets | Web1 Code0 Files1 Vision0 Long0 | Auto 6
Why: правильный выбор банковских продуктов даёт сотни тысяч за годы
Caps: bank comparison, deposit rates, card benefits, fees analysis
---

### 1032 — Налоговая оптимизация для ИП
Джарвис, рассчитай налоговую нагрузку для ИП при разных режимах: НПД, УСН доходы, УСН доходы минус расходы — и порекомендуй оптимальный вариант.
Cat: FINANCE | Small Business Taxes
Diff: L3 | Tools: research, spreadsheets | Web1 Code0 Files1 Vision0 Long0 | Auto 7
Why: выбор режима налогообложения напрямую влияет на чистую прибыль
Caps: sole proprietor taxes, usn comparison, self-employment tax, tax regime selection
---

### 1033 — Финансовый чек-ап
Джарвис, проведи финансовый чек-ап: подушка, долги, инвестиции, страховки, пенсия, бюджет — оцени по каждому блоку и дай план улучшения.
Cat: FINANCE | Financial Health
Diff: L2 | Tools: documents, spreadsheets | Web0 Code0 Files1 Vision0 Long0 | Auto 6
Why: регулярный чек-ап выявляет слабые места финансовой системы
Caps: financial health check, holistic review, action plan, financial literacy
---

### 1034 — Инфляция и покупательная способность
Джарвис, проанализируй влияние инфляции на мои сбережения: рассчитай реальную доходность, покажи потерю покупательной способности и предложи защитные инструменты.
Cat: FINANCE | Inflation
Diff: L2 | Tools: spreadsheets, math, research | Web1 Code0 Files1 Vision0 Long0 | Auto 6
Why: инфляция незаметно обесценивает сбережения, лежащие без движения
Caps: inflation analysis, real return, purchasing power, inflation protection
---

### 1035 — План финансовой независимости (FIRE)
Джарвис, рассчитай путь к финансовой независимости: целевой капитал по правилу 4%, необходимый темп накопления и срок достижения при моих цифрах.
Cat: FINANCE | FIRE
Diff: L3 | Tools: spreadsheets, math | Web0 Code0 Files1 Vision0 Long1 | Auto 7
Why: FIRE-подход превращает накопления в систему с понятной математикой
Caps: fire plan, 4 rule, financial independence, savings rate, withdrawal strategy
---

### 1036 — Маркетинговая стратегия
Джарвис, разработай маркетинговую стратегию: целевая аудитория, позиционирование, каналы продвижения, бюджет и KPI на год — оформи как документ.
Cat: MARKETING | Strategy
Diff: L3 | Tools: documents, research, planning | Web1 Code0 Files1 Vision0 Long1 | Auto 7
Why: стратегия синхронизирует все каналы и не даёт распылять бюджет
Caps: marketing strategy, target audience, channel mix, marketing kpi
---

### 1037 — Контент-план на месяц
Джарвис, составь контент-план на месяц: темы, форматы, площадки, даты публикации и цели для каждого поста — в виде календаря.
Cat: MARKETING | Content Planning
Diff: L2 | Tools: documents, planning, spreadsheets | Web0 Code0 Files1 Vision0 Long0 | Auto 6
Why: регулярный контент по плану строит аудиторию и доверие
Caps: content calendar, content plan, content formats, publishing schedule
---

### 1038 — SEO-аудит сайта
Джарвис, проведи SEO-аудит сайта: технические ошибки, мета-теги, скорость, мобильная версия, структура ссылок — дай приоритизированный список исправлений.
Cat: MARKETING | SEO
Diff: L3 | Tools: web, research, documents | Web1 Code0 Files1 Vision0 Long1 | Auto 7
Why: технический SEO — база, без которой контент не ранжируется
Caps: seo audit, technical seo, meta tags, site speed, on-page optimization
---

### 1039 — Семантическое ядро
Джарвис, собери семантическое ядро для моего сайта: кластеризуй ключевые запросы по темам и интентам, отметь коммерческие и информационные.
Cat: MARKETING | SEO
Diff: L3 | Tools: web, research, spreadsheets | Web1 Code0 Files1 Vision0 Long0 | Auto 7
Why: семантическое ядро определяет структуру сайта и контентную стратегию
Caps: semantic core, keyword clustering, search intent, keyword research
---

### 1040 — Серия email-писем
Джарвис, напиши серию из 5 email-писем для онбординга новых клиентов: приветствие, польза, кейсы, предложение, финальный призыв — с темами писем.
Cat: MARKETING | Email
Diff: L2 | Tools: documents, copywriting | Web0 Code0 Files1 Vision0 Long0 | Auto 6
Why: серия писем автоматически прогревает и удерживает клиентов
Caps: email sequence, onboarding emails, copywriting, email subject lines
---

### 1041 — Настройка контекстной рекламы
Джарвис, подготовь план контекстной рекламы: структура кампаний, ключевые слова, минус-слова, объявления и ставки — для запуска в рекламном кабинете.
Cat: MARKETING | Paid Ads
Diff: L3 | Tools: research, spreadsheets, documents | Web1 Code0 Files1 Vision0 Long1 | Auto 7
Why: правильная структура кампании снижает цену клика и повышает конверсию
Caps: ppc campaign, keyword structure, negative keywords, ad copy, bidding strategy
---

### 1042 — Таргетированная реклама в соцсетях
Джарвис, составь план таргетированной рекламы: сегменты аудитории, креативы, офферы и бюджет по каждому сегменту — для запуска тестов.
Cat: MARKETING | Paid Ads
Diff: L2 | Tools: research, documents | Web1 Code0 Files1 Vision0 Long0 | Auto 6
Why: таргет по сегментам повышает релевантность объявлений
Caps: social ads, audience targeting, ad creatives, ad testing
---

### 1043 — SMM-стратегия для соцсетей
Джарвис, разработай SMM-стратегию: выбор площадок, tone of voice, рубрики, частота публикаций, форматы и план роста аудитории.
Cat: MARKETING | SMM
Diff: L2 | Tools: documents, planning | Web0 Code0 Files1 Vision0 Long0 | Auto 6
Why: системный SMM превращает соцсети в канал продаж и доверия
Caps: smm strategy, tone of voice, content rubrics, audience growth, social media plan
---

### 1044 — A/B-тест лендинга
Джарвис, спланируй A/B-тест лендинга: сформулируй гипотезы, варианты изменений, метрики и минимальный размер выборки для статистической значимости.
Cat: MARKETING | Testing
Diff: L2 | Tools: documents, spreadsheets, math | Web0 Code0 Files1 Vision0 Long0 | Auto 6
Why: A/B-тесты заменяют догадки о конверсии проверенными данными
Caps: ab testing, hypothesis, conversion metrics, sample size, landing page optimization
---

### 1045 — Позиционирование бренда
Джарвис, сформулируй позиционирование бренда: для кого, какой рынок, чем отличаемся, почему нам поверят — через формулу позиционирования и примеры.
Cat: MARKETING | Branding
Diff: L2 | Tools: documents, brainstorming | Web0 Code0 Files1 Vision0 Long0 | Auto 6
Why: ясное позиционирование отличает бренд в переполненном рынке
Caps: brand positioning, differentiation, brand message, value proposition
---

### 1046 — PR-кампания и пресс-релизы
Джарвис, подготовь PR-кампанию: ключевые сообщения, список СМИ и блогеров, пресс-релиз и план распространения — с примерами заголовков.
Cat: MARKETING | PR
Diff: L2 | Tools: research, documents | Web1 Code0 Files1 Vision0 Long0 | Auto 6
Why: PR создаёт доверие через третьи стороны, а не только рекламу
Caps: pr campaign, press release, media outreach, key messages
---

### 1047 — Отчёт по рекламной аналитике
Джарвис, собери отчёт по рекламе за период: расходы, клики, конверсии, CPA и ROAS по кампаниям — с выводами и рекомендациями по оптимизации.
Cat: MARKETING | Analytics
Diff: L2 | Tools: spreadsheets, data | Web0 Code0 Files1 Vision0 Long0 | Auto 6
Why: без регулярных отчётов рекламный бюджет сгорает неэффективно
Caps: ad analytics, cpa, roas, campaign performance, reporting
---

### 1048 — Ретаргетинг и воронка прогрева
Джарвис, выстрой схему ретаргетинга: сегменты по поведению, цепочка сообщений, офферы для каждого этапа воронки и частотные ограничения.
Cat: MARKETING | Retargeting
Diff: L2 | Tools: documents, planning | Web0 Code0 Files1 Vision0 Long0 | Auto 6
Why: ретаргетинг возвращает до 70% ушедших посетителей
Caps: retargeting strategy, audience segments, remarketing funnel, frequency capping
---

### 1049 — Инфлюенсер-маркетинг
Джарвис, разработай план работы с инфлюенсерами: критерии выбора, пул кандидатов, формат сотрудничества, бюджет и метрики эффективности.
Cat: MARKETING | Influencer
Diff: L2 | Tools: research, spreadsheets | Web1 Code0 Files1 Vision0 Long0 | Auto 6
Why: инфлюенсеры дают доверие аудитории быстрее традиционной рекламы
Caps: influencer marketing, creator selection, collaboration format, campaign metrics
---

### 1050 — Анализ аудитории и персоны
Джарвис, построй портреты целевой аудитории: демография, боли, мотивации, возражения, каналы коммуникации — по 3–5 персон с примерами.
Cat: MARKETING | Audience
Diff: L2 | Tools: research, documents | Web1 Code0 Files1 Vision0 Long0 | Auto 6
Why: точные персоны делают все коммуникации релевантнее
Caps: buyer persona, audience analysis, customer pain points, messaging
---

### 1051 — Лендинг: структура и тексты
Джарвис, разработай лендинг: структуру блоков, заголовки, тексты, оффер и призывы к действию — по проверенной схеме конверсионных страниц.
Cat: MARKETING | Landing Pages
Diff: L2 | Tools: documents, copywriting | Web0 Code0 Files1 Vision0 Long0 | Auto 6
Why: структура лендинга напрямую определяет конверсию в заявку
Caps: landing page structure, conversion copywriting, call to action, offer
---

### 1052 — Маркетинговые исследования
Джарвис, проведи маркетинговое исследование: опрос целевой аудитории, анализ ответов, ключевые инсайты и рекомендации по продукту и коммуникации.
Cat: MARKETING | Research
Diff: L3 | Tools: research, spreadsheets, documents | Web1 Code0 Files1 Vision0 Long1 | Auto 7
Why: исследования снижают риск ошибок в продукте и маркетинге
Caps: market research, survey design, insights analysis, recommendations
---

### 1053 — Копирайтинг для продукта
Джарвис, напиши продающие тексты для продукта: главный оффер, выгоды, работа с возражениями, FAQ и CTA для главной страницы.
Cat: MARKETING | Copywriting
Diff: L2 | Tools: documents | Web0 Code0 Files1 Vision0 Long0 | Auto 6
Why: сильные тексты продают без дополнительного трафика
Caps: copywriting, sales copy, objection handling, faq, call to action
---

### 1054 — Видеомаркетинг
Джарвис, разработай видеомаркетинговую стратегию: форматы, площадки, сценарии роликов, серии и метрики успеха для продвижения бренда.
Cat: MARKETING | Video
Diff: L2 | Tools: documents, planning | Web0 Code0 Files1 Vision0 Long0 | Auto 6
Why: видео удерживает внимание и формирует доверие лучше текста
Caps: video marketing, content formats, video scripts, distribution strategy
---

### 1055 — Анализ рекламы конкурентов
Джарвис, проанализируй рекламу конкурентов: их объявления, офферы, креативы и каналы — собери инсайты и предложи, как усилить нашу рекламу.
Cat: MARKETING | Competitive Intelligence
Diff: L2 | Tools: research, documents | Web1 Code0 Files1 Vision0 Long0 | Auto 6
Why: анализ чужих рекламных тестов экономит бюджет на собственных
Caps: competitor ads analysis, ad spy, creative benchmarking, offer analysis
---

### 1056 — Программа лояльности
Джарвис, разработай программу лояльности: механика баллов или уровней, условия начисления и списания, выгоды для клиента и бизнеса, метрики окупаемости.
Cat: MARKETING | Loyalty
Diff: L2 | Tools: documents, planning | Web0 Code0 Files1 Vision0 Long0 | Auto 6
Why: удержание клиента через лояльность дешевле привлечения нового
Caps: loyalty program, rewards mechanics, customer retention, program economics
---

### 1057 — Метрики CAC и LTV
Джарвис, рассчитай CAC и LTV для бизнеса: стоимость привлечения по каналам, средний чек, частота покупок, срок жизни клиента и соотношение LTV/CAC.
Cat: MARKETING | Metrics
Diff: L2 | Tools: spreadsheets, math | Web0 Code0 Files1 Vision0 Long0 | Auto 6
Why: соотношение LTV/CAC показывает здоровье маркетинговой модели
Caps: cac, ltv, ltv cac ratio, customer acquisition, unit metrics
---

### 1058 — Упаковка оффера
Джарвис, упакуй оффер: что продаём, для кого, какая проблема, какое решение, что входит, гарантия и призыв к действию — по формуле сильного оффера.
Cat: MARKETING | Offers
Diff: L2 | Tools: documents, copywriting | Web0 Code0 Files1 Vision0 Long0 | Auto 6
Why: сильный оффер компенсирует слабый трафик и поднимает конверсию
Caps: offer creation, offer formula, guarantee, call to action
---

### 1059 — Launch-план продукта
Джарвис, составь план запуска продукта: подготовка, анонс, день запуска и пост-запуск — с задачами, сроками, каналами и KPI для каждого этапа.
Cat: MARKETING | Launch
Diff: L3 | Tools: documents, planning | Web0 Code0 Files1 Vision0 Long1 | Auto 7
Why: системный запуск создаёт ажиотаж и собирает максимум продаж
Caps: product launch, launch plan, pre-launch strategy, launch kpi
---

### 1060 — Маркетинговая воронка полного цикла
Джарвис, выстрой полную маркетинговую воронку: привлечение, прогрев, конверсия, удержание и возврат — с каналами, офферами и метриками на каждом этапе.
Cat: MARKETING | Funnel
Diff: L3 | Tools: documents, spreadsheets, planning | Web0 Code0 Files1 Vision0 Long1 | Auto 7
Why: сквозная воронка превращает разрозненные кампании в единую систему
Caps: full funnel, marketing funnel, lead nurturing, retention loop, funnel metrics
---
### 1061 — Персональный план обучения
Джарвис, составь персональный план обучения под мою цель: этапы, материалы, практика, сроки и критерии освоения каждого блока.
Cat: LEARNING | Planning
Diff: L2 | Tools: documents, planning | Web0 Code0 Files1 Vision0 Long0 | Auto 6
Why: план обучения без перегруза даёт системный прогресс
Caps: learning plan, skill roadmap, study schedule, milestones
---

### 1062 — Конспект книги или лекции
Джарвис, сделай структурированный конспект по присланному материалу: главные идеи, аргументы, примеры и практические выводы.
Cat: LEARNING | Note Taking
Diff: L1 | Tools: documents | Web0 Code0 Files1 Vision0 Long0 | Auto 6
Why: конспект превращает прочитанное в усвоенное знание
Caps: summarization, note taking, key ideas, study notes
---

### 1063 — Карточки для запоминания (Anki)
Джарвис, создай набор карточек для запоминания по теме: вопросы и ответы, готовые к импорту в Anki, с разбивкой по разделам.
Cat: LEARNING | Memorization
Diff: L2 | Tools: documents, data | Web0 Code0 Files1 Vision0 Long0 | Auto 6
Why: интервальные повторения с карточками — самый эффективный способ запоминания
Caps: anki cards, flashcards, spaced repetition, memorization
---

### 1064 — Изучение иностранного языка
Джарвис, составь план изучения языка: словарь по частоте, грамматика по уровням, практика говорения и приложения — на 3 месяца вперёд.
Cat: LEARNING | Languages
Diff: L2 | Tools: research, documents, planning | Web1 Code0 Files1 Vision0 Long0 | Auto 6
Why: структурированный подход к языку даёт результат вместо хаоса
Caps: language learning, vocabulary plan, grammar levels, study routine
---

### 1065 — Интервальные повторения: расписание
Джарвис, составь расписание интервальных повторений для моего учебного материала: дни повторений 1-7-30-90 и правила, что повторять когда.
Cat: LEARNING | Memorization
Diff: L1 | Tools: documents, planning | Web0 Code0 Files1 Vision0 Long0 | Auto 6
Why: повторение по кривой забывания закрепляет знания надолго
Caps: spaced repetition schedule, forgetting curve, review plan
---

### 1066 — Скорочтение и концентрация
Джарвис, объясни технику скорочтения и дай план тренировок: упражнения на периферическое зрение, избавление от субвокализации и замер скорости.
Cat: LEARNING | Skills
Diff: L1 | Tools: documents | Web0 Code0 Files1 Vision0 Long0 | Auto 6
Why: скорочтение удваивает объём усваиваемого материала в час
Caps: speed reading, focus training, reading comprehension, practice plan
---

### 1067 — Разбор сложной темы
Джарвис, объясни сложную тему простыми словами: аналогии, примеры, шаги освоения и частые ошибки — от базового уровня к продвинутому.
Cat: LEARNING | Explanation
Diff: L2 | Tools: research, documents | Web1 Code0 Files1 Vision0 Long0 | Auto 6
Why: простое объяснение сложного — признак настоящего понимания
Caps: topic breakdown, simple explanations, analogies, learning path
---

### 1068 — Подготовка к экзамену
Джарвис, составь план подготовки к экзамену: разбей материал по дням, сделай пробные вопросы, выдели слабые места и повторения перед датой.
Cat: LEARNING | Exams
Diff: L2 | Tools: documents, planning | Web0 Code0 Files1 Vision0 Long0 | Auto 6
Why: план подготовки снижает стресс и повышает результат экзамена
Caps: exam preparation, study plan, practice questions, revision schedule
---

### 1069 — Практика навыка по расписанию
Джарвис, построй график ежедневной практики навыка: блоки по 25–45 минут, чередование теории и практики, замер прогресса и корректировка.
Cat: LEARNING | Habit Building
Diff: L1 | Tools: documents, planning | Web0 Code0 Files1 Vision0 Long0 | Auto 6
Why: регулярная практика малых доз эффективнее редких марафонов
Caps: practice schedule, deliberate practice, progress tracking, habit building
---

### 1070 — Создание учебного материала
Джарвис, создай учебный материал по теме: объяснение, примеры, упражнения с ответами и вопросы для самопроверки — готовый для учеников.
Cat: LEARNING | Teaching
Diff: L3 | Tools: documents | Web0 Code0 Files1 Vision0 Long1 | Auto 7
Why: качественный учебный материал систематизирует знание автора
Caps: teaching material, exercises, self-assessment, lesson design
---

### 1071 — Обучение через объяснение (метод Фейнмана)
Джарвис, проведи меня по методу Фейнмана: я объясняю тему простыми словами, ты находишь пробелы и задаёшь уточняющие вопросы.
Cat: LEARNING | Techniques
Diff: L2 | Tools: conversation | Web0 Code0 Files1 Vision0 Long0 | Auto 6
Why: объяснение своими словами вскрывает реальные пробелы в знании
Caps: feynman technique, active recall, gaps detection, teaching method
---

### 1072 — Техники запоминания: мнемоника
Джарвис, подбери мнемонические приёмы для запоминания моего списка: метод локусов, ассоциации, акронимы и цепочки образов.
Cat: LEARNING | Memorization
Diff: L1 | Tools: documents | Web0 Code0 Files1 Vision0 Long0 | Auto 6
Why: мнемоника превращает трудный список в живые образы
Caps: mnemonics, memory palace, associations, acronyms
---

### 1073 — Выбор курса или школы
Джарвис, сравни курсы по интересующей теме: программа, длительность, цена, отзывы и результаты выпускников — дай рекомендацию под мою цель.
Cat: LEARNING | Course Selection
Diff: L2 | Tools: research | Web1 Code0 Files1 Vision0 Long0 | Auto 6
Why: правильный курс экономит месяцы и деньги на обучении
Caps: course comparison, program evaluation, reviews analysis, recommendation
---

### 1074 — План чтения профессиональной литературы
Джарвис, составь список книг для профессионального роста: по уровням сложности, с приоритетами, сроками и техникой конспектирования.
Cat: LEARNING | Reading
Diff: L1 | Tools: research, documents | Web1 Code0 Files1 Vision0 Long0 | Auto 6
Why: системное чтение по плану быстрее формирует экспертизу
Caps: reading list, professional books, prioritization, note taking
---

### 1075 — Обучение ребёнка или ученика
Джарвис, составь программу обучения для ученика: возраст, уровень, цели, игровые механики, материалы и способы удержания интереса.
Cat: LEARNING | Teaching
Diff: L2 | Tools: documents, research | Web1 Code0 Files1 Vision0 Long0 | Auto 6
Why: обучение с учётом возраста и интереса даёт устойчивую мотивацию
Caps: tutoring plan, child education, gamification, engagement strategies
---

### 1076 — Изучение темы по первоисточникам
Джарвис, построй план изучения темы по первоисточникам: список ключевых авторов и работ, порядок чтения, вопросы для анализа и синтез выводов.
Cat: LEARNING | Research
Diff: L2 | Tools: research, documents | Web1 Code0 Files1 Vision0 Long0 | Auto 6
Why: первоисточники дают глубину, которой нет в пересказах
Caps: primary sources, reading order, critical analysis, synthesis
---

### 1077 — Техника Pomodoro для учёбы
Джарвис, настрой мои учебные сессии по Pomodoro: интервалы, перерывы, правила защиты фокуса и способ учёта сессий в день.
Cat: LEARNING | Focus
Diff: L1 | Tools: planning | Web0 Code0 Files1 Vision0 Long0 | Auto 6
Why: короткие фокус-сессии защищают от выгорания и прокрастинации
Caps: pomodoro, focus sessions, break schedule, productivity
---

### 1078 — Создание шпаргалки
Джарвис, сделай одностраничную шпаргалку по теме: самое важное, формулы, определения и шаги — в компактном формате для печати.
Cat: LEARNING | Study Aids
Diff: L1 | Tools: documents | Web0 Code0 Files1 Vision0 Long0 | Auto 6
Why: шпаргалка вынуждает выделить главное и легко повторяться
Caps: cheat sheet, key points, quick reference, compact summary
---

### 1079 — Собеседование: подготовка по навыкам
Джарвис, подготовь меня к собеседованию по навыкам: типичные вопросы, эталонные ответы, тестовые задания и разбор моих слабых мест.
Cat: LEARNING | Career
Diff: L2 | Tools: documents, research | Web1 Code0 Files1 Vision0 Long0 | Auto 6
Why: подготовка к вопросам и заданиям удваивает шанс оффера
Caps: interview preparation, common questions, mock answers, skill assessment
---

### 1080 — Анализ учебного прогресса
Джарвис, проанализируй мой прогресс в обучении: что освоено, где пробелы, темп против плана — и скорректируй учебную программу.
Cat: LEARNING | Progress Tracking
Diff: L2 | Tools: spreadsheets, documents | Web0 Code0 Files1 Vision0 Long0 | Auto 6
Why: честный замер прогресса показывает, что менять в подходе
Caps: progress analysis, learning gaps, pace tracking, plan adjustment
---

### 1081 — Обучение новой профессии
Джарвис, составь дорожную карту смены профессии: навыки, портфолио, первые проекты, сообщества и сроки выхода на первую оплачиваемую работу.
Cat: LEARNING | Career Change
Diff: L3 | Tools: documents, research, planning | Web1 Code0 Files1 Vision0 Long1 | Auto 7
Why: смена профессии требует системы, а не только курсов
Caps: career change, skill map, portfolio building, job market entry
---

### 1082 — Углублённое изучение области
Джарвис, построй план перехода от среднего к экспертному уровню в области: сложные темы, исследования, практические проекты и нетворкинг с экспертами.
Cat: LEARNING | Mastery
Diff: L3 | Tools: research, documents | Web1 Code0 Files1 Vision0 Long0 | Auto 7
Why: глубина экспертизы открывает премиальные возможности
Caps: mastery path, advanced topics, expert network, deep practice
---

### 1083 — Ежедневная обучающая рутина
Джарвис, собери ежедневную обучающую рутину: чтение, практика, повторение и рефлексия — с точным расписанием по времени суток.
Cat: LEARNING | Routine
Diff: L1 | Tools: documents, planning | Web0 Code0 Files1 Vision0 Long0 | Auto 6
Why: маленькая ежедневная рутина накапливает большие результаты
Caps: daily routine, learning habits, time blocking, consistency
---

### 1084 — Тесты и проверка знаний
Джарвис, составь тест по теме для проверки знаний: 20 вопросов разного уровня с ответами и пояснениями, плюс критерии оценки.
Cat: LEARNING | Assessment
Diff: L2 | Tools: documents | Web0 Code0 Files1 Vision0 Long0 | Auto 6
Why: тестирование — лучший способ закрепить и проверить знание
Caps: knowledge test, quiz creation, assessment criteria, answer key
---

### 1085 — Объяснение для непрофессионала
Джарвис, объясни мою профессиональную тему так, чтобы понял непрофессионал: убирай жаргон, используй бытовые аналогии и пошаговую логику.
Cat: LEARNING | Communication
Diff: L1 | Tools: conversation | Web0 Code0 Files1 Vision0 Long0 | Auto 6
Why: умение объяснять просто — ключевой навык эксперта
Caps: plain language, jargon-free, analogies, step by step
---

### 1086 — Объяснение научной концепции
Джарвис, объясни научную концепцию: суть, историю открытия, доказательства, практические применения и современное состояние — на доступном языке.
Cat: SCIENCE | Education
Diff: L2 | Tools: research | Web1 Code0 Files1 Vision0 Long0 | Auto 6
Why: научная грамотность начинается с ясных объяснений
Caps: science communication, concept explanation, evidence, applications
---

### 1087 — Литературный обзор по теме
Джарвис, проведи литературный обзор по теме: найди ключевые статьи, сгруппируй по направлениям, выдели консенсус и спорные вопросы.
Cat: SCIENCE | Research
Diff: L3 | Tools: research, documents | Web1 Code0 Files1 Vision0 Long1 | Auto 7
Why: обзор литературы показывает картину поля до начала работы
Caps: literature review, paper search, research landscape, gap analysis
---

### 1088 — Дизайн эксперимента
Джарвис, помоги спроектировать эксперимент: гипотеза, переменные, контрольная группа, размер выборки, протокол и методы анализа результатов.
Cat: SCIENCE | Experiment Design
Diff: L3 | Tools: documents, math, research | Web1 Code0 Files1 Vision0 Long0 | Auto 7
Why: корректный дизайн эксперимента — залог достоверных выводов
Caps: experiment design, hypothesis, control group, sample size, protocol
---

### 1089 — Статистический анализ данных
Джарвис, проведи статистический анализ набора данных: описательная статистика, проверка гипотез, доверительные интервалы и визуализация распределений.
Cat: SCIENCE | Statistics
Diff: L3 | Tools: data, math, code | Web0 Code1 Files1 Vision0 Long0 | Auto 7
Why: статистика превращает сырые данные в обоснованные выводы
Caps: statistical analysis, hypothesis testing, confidence intervals, descriptive stats
---

### 1090 — Научный метод: проверка гипотезы
Джарвис, проведи меня по научному методу: сформулируй гипотезу, предложи тест, предскажи результаты и объясни, как интерпретировать исход.
Cat: SCIENCE | Methodology
Diff: L2 | Tools: documents, math | Web0 Code0 Files1 Vision0 Long0 | Auto 6
Why: научный метод — системный способ отличать факты от мнений
Caps: scientific method, hypothesis testing, falsifiability, interpretation
---

### 1091 — Популяризация науки
Джарвис, преврати научный материал в популярное объяснение: статья, пост или ролик с интригой, простыми аналогиями и практическим значением.
Cat: SCIENCE | Communication
Diff: L2 | Tools: documents | Web0 Code0 Files1 Vision0 Long0 | Auto 6
Why: популяризация делает науку доступной широкой аудитории
Caps: science popularization, engaging content, simplification, storytelling
---

### 1092 — Критическая оценка научной статьи
Джарвис, критически разбери научную статью: методология, размер выборки, статистика, возможные смещения и обоснованность выводов.
Cat: SCIENCE | Critical Thinking
Diff: L3 | Tools: research, documents | Web1 Code0 Files1 Vision0 Long0 | Auto 7
Why: критический разбор защищает от слепого доверия публикациям
Caps: paper critique, methodology review, bias detection, evidence quality
---

### 1093 — Решение физической задачи
Джарвис, реши физическую задачу: распиши условия, выбери законы, выполни расчёты с единицами измерения и проверь правдоподобность ответа.
Cat: SCIENCE | Physics
Diff: L3 | Tools: math, documents | Web0 Code0 Files1 Vision0 Long0 | Auto 7
Why: пошаговое решение задач закрепляет физическое мышление
Caps: physics problem solving, dimensional analysis, laws application
---

### 1094 — Химические расчёты и реакции
Джарвис, выполни химические расчёты: балансировка уравнений, молярные массы, стехиометрия, концентрации растворов и выход реакции.
Cat: SCIENCE | Chemistry
Diff: L3 | Tools: math, research | Web1 Code0 Files1 Vision0 Long0 | Auto 7
Why: точные химические расчёты критичны в лаборатории и промышленности
Caps: stoichiometry, equation balancing, molar calculations, solution concentration
---

### 1095 — Биологические процессы: объяснение
Джарвис, объясни биологический процесс: механизм, участники, регуляция, нарушения и примеры — от клеточного уровня до организма.
Cat: SCIENCE | Biology
Diff: L2 | Tools: research | Web1 Code0 Files1 Vision0 Long0 | Auto 6
Why: понимание механизмов важнее запоминания отдельных фактов
Caps: biology explanation, cellular mechanisms, physiology, regulation
---

### 1096 — Анализ научных данных и визуализация
Джарвис, проанализируй научные данные: очистка, статистика, поиск закономерностей и создание публикационных графиков с подписями.
Cat: SCIENCE | Data Analysis
Diff: L3 | Tools: data, code, charts | Web0 Code1 Files1 Vision0 Long0 | Auto 7
Why: качественная визуализация доносит научные выводы наглядно
Caps: scientific data analysis, publication figures, data cleaning, patterns
---

### 1097 — Планирование исследовательского проекта
Джарвис, составь план исследовательского проекта: цель, вопросы, методы, этапы, ресурсы, риски и критерии завершённости.
Cat: SCIENCE | Project Planning
Diff: L3 | Tools: documents, planning | Web0 Code0 Files1 Vision0 Long0 | Auto 7
Why: план исследования защищает от хаоса и потери фокуса
Caps: research plan, methodology, milestones, resource planning
---

### 1098 — Объяснение космоса и астрономии
Джарвис, объясни астрономическое явление: физическая суть, наблюдаемые проявления, история изучения и значение для науки.
Cat: SCIENCE | Astronomy
Diff: L2 | Tools: research | Web1 Code0 Files1 Vision0 Long0 | Auto 6
Why: астрономия расширяет картину мира и научное мышление
Caps: astronomy, space phenomena, cosmology, observation
---

### 1099 — Науки о Земле и климат
Джарвис, объясни процесс из наук о Земле: климат, геология или экология — механизмы, данные наблюдений и последствия для человека.
Cat: SCIENCE | Earth Sciences
Diff: L2 | Tools: research | Web1 Code0 Files1 Vision0 Long0 | Auto 6
Why: понимание Земли и климата важно для решений на всех уровнях
Caps: earth science, climate change, geology, ecosystems
---

### 1100 — Факт-чекинг и проверка достоверности
Джарвис, проверь утверждение на достоверность: найди первоисточник, оцени качество исследований и сделай вывод о степени доказанности.
Cat: SCIENCE | Fact Checking
Diff: L2 | Tools: research | Web1 Code0 Files1 Vision0 Long0 | Auto 6
Why: проверка фактов защищает от дезинформации и псевдонауки
Caps: fact checking, source verification, evidence evaluation, debunking
---

### 1101 — Научные мифы: разбор
Джарвис, разбери популярный научный миф: откуда он взялся, что говорят данные и как объяснить правду простыми словами.
Cat: SCIENCE | Debunking
Diff: L2 | Tools: research | Web1 Code0 Files1 Vision0 Long0 | Auto 6
Why: разбор мифов развивает критическое мышление аудитории
Caps: myth busting, pseudoscience, evidence review, science communication
---

### 1102 — Подготовка научной публикации
Джарвис, помоги подготовить научную публикацию: структура IMRAD, аннотация, ключевые слова, оформление по требованиям журнала и ответы рецензентам.
Cat: SCIENCE | Publishing
Diff: L3 | Tools: documents, research | Web1 Code0 Files1 Vision0 Long1 | Auto 7
Why: грамотная публикация повышает шансы принятия в журнал
Caps: scientific writing, imrad, abstract, journal submission, peer review response
---

### 1103 — Моделирование и симуляция
Джарвис, построй модель или симуляцию процесса: допущения, параметры, уравнения и визуализация результатов при разных сценариях.
Cat: SCIENCE | Modeling
Diff: L3 | Tools: code, math, charts | Web0 Code1 Files1 Vision0 Long0 | Auto 7
Why: симуляции позволяют тестировать гипотезы без дорогих экспериментов
Caps: simulation, mathematical modeling, parameter sweeps, scenario analysis
---

### 1104 — Научная этика и добросовестность
Джарвис, разбери вопрос научной этики: нормы, типичные нарушения, правила цитирования и ответственное обращение с данными.
Cat: SCIENCE | Ethics
Diff: L2 | Tools: research, documents | Web1 Code0 Files1 Vision0 Long0 | Auto 6
Why: соблюдение этики защищает репутацию и целостность науки
Caps: research ethics, plagiarism, data integrity, citation practices
---

### 1105 — Междисциплинарный синтез знаний
Джарвис, объедини знания из нескольких дисциплин для решения проблемы: найди пересечения, перенеси методы и предложи новое решение.
Cat: SCIENCE | Interdisciplinary
Diff: L3 | Tools: research, documents | Web1 Code0 Files1 Vision0 Long1 | Auto 7
Why: прорывные решения часто рождаются на стыке дисциплин
Caps: interdisciplinary thinking, method transfer, knowledge synthesis
---

### 1106 — Решение математической задачи
Джарвис, реши математическую задачу пошагово: условие, подход, вычисления и проверку — с объяснением каждого шага.
Cat: MATH | Problem Solving
Diff: L2 | Tools: math | Web0 Code0 Files1 Vision0 Long0 | Auto 6
Why: пошаговый разбор учит методу, а не только ответу
Caps: math problem solving, step by step, verification, methods
---

### 1107 — Производные и интегралы
Джарвис, объясни и реши примеры по дифференцированию и интегрированию: правила, техники и прикладной смысл обеих операций.
Cat: MATH | Calculus
Diff: L3 | Tools: math, documents | Web0 Code0 Files1 Vision0 Long0 | Auto 7
Why: анализ функций — база для физики, экономики и инженерии
Caps: derivatives, integrals, calculus rules, applications
---

### 1108 — Линейная алгебра: объяснение
Джарвис, объясни тему линейной алгебры: векторы, матрицы, определители, собственные значения — с примерами и приложениями.
Cat: MATH | Linear Algebra
Diff: L3 | Tools: math, documents | Web0 Code0 Files1 Vision0 Long0 | Auto 7
Why: линейная алгебра — язык машинного обучения и графики
Caps: linear algebra, matrices, eigenvectors, vector spaces
---

### 1109 — Теория вероятностей
Джарвис, объясни понятие теории вероятностей и реши примеры: условная вероятность, формула Байеса, дискретные и непрерывные распределения.
Cat: MATH | Probability
Diff: L3 | Tools: math, documents | Web0 Code0 Files1 Vision0 Long0 | Auto 7
Why: вероятностное мышление необходимо для принятия решений
Caps: probability, bayes theorem, distributions, conditional probability
---

### 1110 — Статистика: методы и интерпретация
Джарвис, объясни статистические методы и как их интерпретировать: средние, дисперсия, корреляция, регрессия — с примерами ошибок интерпретации.
Cat: MATH | Statistics
Diff: L3 | Tools: math, data | Web0 Code0 Files1 Vision0 Long0 | Auto 7
Why: статистическая грамотность защищает от манипуляций цифрами
Caps: statistics, correlation, regression, interpretation, common pitfalls
---

### 1111 — Визуализация математических функций
Джарвис, построй графики функций и поверхностей: точки пересечения, экстремумы, асимптоты и анимация изменения параметров.
Cat: MATH | Visualization
Diff: L2 | Tools: code, charts | Web0 Code1 Files1 Vision0 Long0 | Auto 6
Why: график часто понятнее формулы, особенно при обучении
Caps: function plotting, 3d surfaces, extrema, parameter animation
---

### 1112 — Оптимизация: поиск максимума и минимума
Джарвис, реши задачу оптимизации: целевая функция, ограничения, метод решения (аналитический или численный) и проверка результата.
Cat: MATH | Optimization
Diff: L3 | Tools: math, code | Web0 Code1 Files1 Vision0 Long0 | Auto 7
Why: оптимизация — ядро инженерии, экономики и ИИ
Caps: optimization, objective function, constraints, numerical methods
---

### 1113 — Геометрия: задачи и доказательства
Джарвис, реши геометрическую задачу или проведи доказательство: построение, свойства фигур, логические шаги и проверка.
Cat: MATH | Geometry
Diff: L2 | Tools: math, documents | Web0 Code0 Files1 Vision0 Long0 | Auto 6
Why: геометрия развивает пространственное и логическое мышление
Caps: geometry, proofs, constructions, problem solving
---

### 1114 — Дискретная математика
Джарвис, объясни тему дискретной математики: логика, множества, графы, комбинаторика — с примерами из программирования.
Cat: MATH | Discrete Math
Diff: L3 | Tools: math, documents | Web0 Code0 Files1 Vision0 Long0 | Auto 7
Why: дискретная математика — фундамент алгоритмов и структур данных
Caps: discrete math, graph theory, combinatorics, logic
---

### 1115 — Обыкновенные дифференциальные уравнения
Джарвис, реши дифференциальное уравнение: определи тип, выбери метод, выполни решение и интерпретируй поведение системы.
Cat: MATH | Differential Equations
Diff: L3 | Tools: math, code | Web0 Code1 Files1 Vision0 Long0 | Auto 7
Why: ДУ описывают почти все динамические системы в природе
Caps: differential equations, solution methods, system behavior, modeling
---

### 1116 — Финансовая математика
Джарвис, реши задачу финансовой математики: сложные проценты, аннуитеты, NPV, IRR — с формулами и интерпретацией.
Cat: MATH | Financial Math
Diff: L2 | Tools: math, spreadsheets | Web0 Code0 Files1 Vision0 Long0 | Auto 6
Why: финансовая математика нужна для честной оценки инвестиций
Caps: compound interest, annuities, npv, irr
---

### 1117 — Численные методы
Джарвис, объясни и примени численный метод: интерполяция, численное интегрирование или решение уравнений — с оценкой погрешности.
Cat: MATH | Numerical Methods
Diff: L3 | Tools: math, code | Web0 Code1 Files1 Vision0 Long0 | Auto 7
Why: численные методы решают задачи, недоступные аналитике
Caps: numerical methods, interpolation, error estimation, numerical integration
---

### 1118 — Математическая логика
Джарвис, объясни тему математической логики: высказывания, предикаты, кванторы, доказательства — с примерами и упражнениями.
Cat: MATH | Logic
Diff: L2 | Tools: math, documents | Web0 Code0 Files1 Vision0 Long0 | Auto 6
Why: логика — основа корректных рассуждений и программирования
Caps: mathematical logic, predicates, quantifiers, proofs
---

### 1119 — Математические головоломки
Джарвис, реши математическую головоломку: разбери условие, найди закономерность, предложи несколько подходов и покажи решение.
Cat: MATH | Puzzles
Diff: L2 | Tools: math | Web0 Code0 Files1 Vision0 Long0 | Auto 6
Why: головоломки тренируют нестандартное математическое мышление
Caps: math puzzles, pattern finding, creative problem solving
---

### 1120 — Математика для машинного обучения
Джарвис, объясни математическую основу машинного обучения: градиентный спуск, матричные операции, функции потерь — на конкретных примерах.
Cat: MATH | ML Foundations
Diff: L3 | Tools: math, code | Web0 Code1 Files1 Vision0 Long0 | Auto 7
Why: понимание математики ML отличает инженера от оператора библиотек
Caps: gradient descent, loss functions, matrix calculus, ml math
---

### 1121 — Инженерный расчёт конструкции
Джарвис, выполни инженерный расчёт: нагрузки, прочность, допуски и выбор материалов — с формулами, единицами и проверкой по нормам.
Cat: ENGINEERING | Mechanics
Diff: L3 | Tools: math, research, documents | Web1 Code0 Files1 Vision0 Long0 | Auto 7
Why: корректный расчёт прочности предотвращает аварии и перерасход
Caps: structural calculation, stress analysis, materials selection, safety factors
---

### 1122 — Схемотехника и электроника
Джарвис, спроектируй электрическую схему: элементы, номиналы, расчёты тока и напряжения, защита — с пояснением принципа работы.
Cat: ENGINEERING | Electronics
Diff: L3 | Tools: math, research, documents | Web1 Code0 Files1 Vision0 Long0 | Auto 7
Why: грамотная схемотехника — основа надёжных электронных устройств
Caps: circuit design, component selection, ohm law calculations, protection
---

### 1123 — Проектирование в CAD
Джарвис, составь план проектирования детали в CAD: требования, эскизы, размеры, допуски, материалы и порядок моделирования.
Cat: ENGINEERING | CAD
Diff: L2 | Tools: documents, research | Web1 Code0 Files1 Vision0 Long0 | Auto 6
Why: план моделирования экономит часы работы в CAD-системе
Caps: cad design, part modeling, dimensions, tolerances, design plan
---

### 1124 — 3D-печать: подготовка модели
Джарвис, подготовь модель к 3D-печати: проверка геометрии, ориентация, поддержки, настройки слайсера и прогноз расхода материала.
Cat: ENGINEERING | 3D Printing
Diff: L2 | Tools: research, documents | Web1 Code0 Files1 Vision0 Long0 | Auto 6
Why: правильная подготовка модели экономит материал и время печати
Caps: 3d printing, slicer settings, supports, print orientation
---

### 1125 — Механика: расчёт передач и механизмов
Джарвис, рассчитай механизм: передаточное отношение, крутящий момент, мощность, КПД и износ — для проектируемой системы.
Cat: ENGINEERING | Mechanical Design
Diff: L3 | Tools: math, research | Web1 Code0 Files1 Vision0 Long0 | Auto 7
Why: расчёт механизмов до сборки предотвращает дорогие ошибки
Caps: gear calculation, torque, efficiency, mechanism design
---

### 1126 — Прототипирование продукта
Джарвис, составь план прототипирования: версии от бумажного до функционального, материалы, методы сборки и критерии тестирования каждой версии.
Cat: ENGINEERING | Prototyping
Diff: L2 | Tools: documents, planning | Web0 Code0 Files1 Vision0 Long0 | Auto 6
Why: итеративное прототипирование удешевляет разработку продукта
Caps: prototyping, mvp, iteration plan, testing criteria
---

### 1127 — IoT-система: архитектура
Джарвис, спроектируй IoT-систему: датчики, контроллер, связь, облако, безопасность и обработка данных — с выбором компонентов.
Cat: ENGINEERING | IoT
Diff: L3 | Tools: research, documents | Web1 Code0 Files1 Vision0 Long0 | Auto 7
Why: продуманная архитектура IoT экономит на переделках и защите
Caps: iot architecture, sensors, connectivity, cloud, device security
---

### 1128 — Тепловые и энергетические расчёты
Джарвис, выполни теплотехнический расчёт: теплопотери, теплообмен, мощность нагрева и КПД системы — с единицами и допущениями.
Cat: ENGINEERING | Thermal
Diff: L3 | Tools: math, research | Web1 Code0 Files1 Vision0 Long0 | Auto 7
Why: тепловые расчёты определяют энергоэффективность и безопасность
Caps: thermal calculation, heat transfer, energy efficiency, heat loss
---

### 1129 — Автоматизация технологического процесса
Джарвис, спроектируй систему автоматизации: датчики, исполнительные механизмы, контроллер, логика управления и сценарии аварий.
Cat: ENGINEERING | Automation
Diff: L3 | Tools: research, documents | Web1 Code0 Files1 Vision0 Long0 | Auto 7
Why: автоматизация повышает точность и безопасность производства
Caps: process automation, control logic, sensors, actuators, safety scenarios
---

### 1130 — Инженерная документация
Джарвис, оформи инженерную документацию: спецификация, чертёж, техническое задание, инструкция и журнал изменений — по стандартам.
Cat: ENGINEERING | Documentation
Diff: L2 | Tools: documents | Web0 Code0 Files1 Vision0 Long0 | Auto 6
Why: документация — единственный способ передать инженерные решения команде
Caps: engineering documentation, specification, technical drawing, change log
---

### 1131 — Выбор материалов для задачи
Джарвис, подбери материалы для изделия: сравнение по прочности, весу, цене, коррозии и технологичности — с итоговой рекомендацией.
Cat: ENGINEERING | Materials
Diff: L2 | Tools: research, documents | Web1 Code0 Files1 Vision0 Long0 | Auto 6
Why: правильный материал определяет цену и срок службы изделия
Caps: materials selection, property comparison, cost analysis, engineering materials
---

### 1132 — Гидравлика и пневматика
Джарвис, выполни расчёт гидравлической или пневматической системы: давление, расход, диаметры, потери и выбор насоса или компрессора.
Cat: ENGINEERING | Fluid Power
Diff: L3 | Tools: math, research | Web1 Code0 Files1 Vision0 Long0 | Auto 7
Why: корректные гидрорасчёты обеспечивают работу и безопасность систем
Caps: hydraulics, pneumatics, pressure drop, pump selection, flow calculation
---

### 1133 — Электроснабжение и безопасность
Джарвис, спроектируй схему электроснабжения: нагрузка, сечение кабеля, защитные автоматы, заземление и правила безопасности.
Cat: ENGINEERING | Electrical
Diff: L3 | Tools: math, research | Web1 Code0 Files1 Vision0 Long0 | Auto 7
Why: ошибки в электрике опасны для жизни и имущества
Caps: power supply design, cable sizing, circuit breakers, grounding, safety
---

### 1134 — Робототехника: кинематика
Джарвис, рассчитай кинематику робота: степени свободы, прямую и обратную задачу, рабочие зоны и ограничения движения.
Cat: ENGINEERING | Robotics
Diff: L3 | Tools: math, code, research | Web1 Code1 Files1 Vision0 Long0 | Auto 7
Why: кинематика — основа управления любым манипулятором
Caps: robot kinematics, degrees of freedom, forward inverse kinematics, workspace
---

### 1135 — Контроль качества продукции
Джарвис, разработай план контроля качества: контрольные точки, методы проверки, допустимые отклонения и действия при браке.
Cat: ENGINEERING | Quality
Diff: L2 | Tools: documents, planning | Web0 Code0 Files1 Vision0 Long0 | Auto 6
Why: контроль качества сохраняет репутацию и снижает издержки
Caps: quality control, inspection plan, tolerances, defect handling
---

### 1136 — Эксплуатация и обслуживание оборудования
Джарвис, составь регламент обслуживания оборудования: график ТО, контрольные параметры, типовые неисправности и порядок устранения.
Cat: ENGINEERING | Maintenance
Diff: L2 | Tools: documents, planning | Web0 Code0 Files1 Vision0 Long0 | Auto 6
Why: плановое обслуживание дешевле аварийных ремонтов
Caps: maintenance schedule, preventive maintenance, troubleshooting, equipment care
---

### 1137 — Расчёт себестоимости изделия
Джарвис, рассчитай себестоимость изделия: материалы, работа, амортизация, энергия и накладные — с ценой и маржой.
Cat: ENGINEERING | Costing
Diff: L2 | Tools: spreadsheets | Web0 Code0 Files1 Vision0 Long0 | Auto 6
Why: точная себестоимость — основа честного ценообразования
Caps: cost calculation, bill of materials, labor cost, margin
---

### 1138 — Испытания и валидация продукта
Джарвис, разработай программу испытаний: тесты, условия, критерии прохождения, регистрация результатов и анализ отказов.
Cat: ENGINEERING | Testing
Diff: L2 | Tools: documents, planning | Web0 Code0 Files1 Vision0 Long0 | Auto 6
Why: испытания до выпуска защищают пользователей и репутацию
Caps: product testing, validation, test protocol, failure analysis
---

### 1139 — Эргономика и дизайн продукта
Джарвис, оцени эргономику продукта: размеры, нагрузки, углы, доступность — и предложи улучшения по стандартам эргономики.
Cat: ENGINEERING | Ergonomics
Diff: L2 | Tools: research, documents | Web1 Code0 Files1 Vision0 Long0 | Auto 6
Why: эргономичный продукт удобнее и безопаснее в использовании
Caps: ergonomics, anthropometrics, usability, design standards
---

### 1140 — Безопасность инженерных систем
Джарвис, проведи анализ рисков инженерной системы: опасные сценарии, вероятность, последствия и меры защиты — по методологии HAZOP или FMEA.
Cat: ENGINEERING | Safety
Diff: L3 | Tools: research, documents | Web1 Code0 Files1 Vision0 Long0 | Auto 7
Why: системный анализ рисков предотвращает аварии и травмы
Caps: hazard analysis, fmea, hazop, risk assessment, safety engineering
---
### 1141 — Мультиагентная система: архитектура
Джарвис, спроектируй мультиагентную систему: роли агентов, обмен сообщениями, оркестрация, общая память и обработка конфликтов.
Cat: AGENTS | Multi-Agent
Diff: L4 | Tools: documents, diagrams, code | Web0 Code1 Files1 Vision0 Long1 | Auto 8
Why: разделение на агентов делает сложные задачи параллельными и надёжными
Caps: multi-agent architecture, orchestration, agent roles, shared memory
---

### 1142 — Агент-планировщик задач
Джарвис, создай агента-планировщика: он разбивает большую цель на шаги, назначает исполнителей и контролирует выполнение.
Cat: AGENTS | Planning Agent
Diff: L3 | Tools: planning, documents | Web0 Code0 Files1 Vision0 Long0 | Auto 7
Why: планировщик освобождает человека от рутинного контроля
Caps: task planner, goal decomposition, execution tracking
---

### 1143 — Агент-исследователь
Джарвис, создай агента-исследователя: он собирает информацию по теме, проверяет источники и выдаёт структурированный отчёт с ссылками.
Cat: AGENTS | Research Agent
Diff: L3 | Tools: research, web, documents | Web1 Code0 Files1 Vision0 Long1 | Auto 7
Why: автономный исследователь экономит часы ручного поиска
Caps: research agent, source gathering, report generation, fact checking
---

### 1144 — Агент-кодер
Джарвис, создай агента-кодера: он пишет код по описанию, запускает тесты, исправляет ошибки и повторяет до зелёных тестов.
Cat: AGENTS | Coding Agent
Diff: L4 | Tools: code, terminal, tests | Web0 Code1 Files1 Vision0 Long0 | Auto 8
Why: цикл «код-тест-фикс» в автоматическом режиме ускоряет разработку
Caps: coding agent, test driven loop, code generation, self correction
---

### 1145 — Агент-аналитик данных
Джарвис, создай агента-аналитика: он загружает данные, очищает, считает метрики, строит графики и пишет выводы без участия человека.
Cat: AGENTS | Data Agent
Diff: L4 | Tools: data, code, charts | Web0 Code1 Files1 Vision0 Long1 | Auto 8
Why: автономный аналитик делает рутинную аналитику мгновенной
Caps: data analysis agent, automated reporting, charts, insights
---

### 1146 — Агент-контентмейкер
Джарвис, создай агента-контентмейкера: он генерирует посты по плану, подстраивает под площадку и публикует в назначенное время.
Cat: AGENTS | Content Agent
Diff: L3 | Tools: documents, web, scheduling | Web1 Code0 Files1 Vision0 Long0 | Auto 7
Why: контент-агент поддерживает присутствие бренда без рутины
Caps: content agent, post generation, platform adaptation, scheduling
---

### 1147 — Агент-переводчик документов
Джарвис, создай агента-переводчика: он принимает документы, переводит, сохраняет форматирование и проверяет терминологию по глоссарию.
Cat: AGENTS | Translation Agent
Diff: L3 | Tools: documents, translation | Web0 Code0 Files1 Vision0 Long0 | Auto 7
Why: автоматический перевод с сохранением формата экономит время команды
Caps: translation agent, glossary compliance, document conversion, formatting
---

### 1148 — Агент-мониторинг уведомлений
Джарвис, создай агента-наблюдателя: он проверяет почту, календарь и системы каждые N минут и докладывает только о важных событиях.
Cat: AGENTS | Monitoring Agent
Diff: L3 | Tools: email, web, scheduling | Web1 Code0 Files1 Vision0 Long0 | Auto 7
Why: фильтрация уведомлений снижает информационный шум
Caps: notification agent, event monitoring, filtering, digest
---

### 1149 — Агент по продажам
Джарвис, создай агента продаж: он ведёт базу лидов, пишет персонализированные письма, напоминает о касаниях и готовит отчёты.
Cat: AGENTS | Sales Agent
Diff: L3 | Tools: documents, email, data | Web0 Code0 Files1 Vision0 Long0 | Auto 7
Why: системная работа с лидами без пропусков увеличивает конверсию
Caps: sales agent, lead management, outreach, follow up reminders
---

### 1150 — Делегирование подзадач агенту
Джарвис, возьми на себя подзадачу из моего проекта: уточни требования, выполни и верни результат в удобном формате.
Cat: AGENTS | Delegation
Diff: L2 | Tools: conversation | Web0 Code0 Files1 Vision0 Long0 | Auto 6
Why: делегирование рутины освобождает время на стратегию
Caps: delegation, task handoff, autonomous execution, reporting
---

### 1151 — Оркестрация нескольких агентов
Джарвис, организуй работу агентов над общей задачей: распредели роли, определи порядок и точки синхронизации, управляй общим результатом.
Cat: AGENTS | Orchestration
Diff: L4 | Tools: planning, code | Web0 Code1 Files1 Vision0 Long0 | Auto 8
Why: оркестрация превращает агентов в единую производственную систему
Caps: orchestration, agent workflow, synchronization, pipeline
---

### 1152 — Агент для ведения реестра задач
Джарвис, создай агента-трекера: он ведёт список задач, обновляет статусы, напоминает о дедлайнах и формирует статус-отчёты.
Cat: AGENTS | Task Tracking
Diff: L2 | Tools: planning, documents | Web0 Code0 Files1 Vision0 Long0 | Auto 6
Why: автоматический трекинг держит проект в поле зрения
Caps: task tracker agent, status updates, deadline reminders, reports
---

### 1153 — Агент-аудитор качества
Джарвис, создай агента-аудитора: он проверяет результаты по чек-листу, находит ошибки и возвращает на доработку с описанием проблем.
Cat: AGENTS | QA Agent
Diff: L3 | Tools: documents, checklists | Web0 Code0 Files1 Vision0 Long0 | Auto 7
Why: автоматический аудит ловит ошибки, которые пропускает человек
Caps: quality audit, checklist verification, error detection, feedback loop
---

### 1154 — Обучение агента на примерах
Джарвис, настрой агента на моих примерах: покажи эталонные решения задач, чтобы он повторял стиль и подход в будущем.
Cat: AGENTS | Training
Diff: L3 | Tools: documents, conversation | Web0 Code0 Files1 Vision0 Long0 | Auto 7
Why: обучение на примерах делает агента полезнее сразу после настройки
Caps: few shot learning, style matching, example based tuning, personalization
---

### 1155 — Агент-помощник по документации
Джарвис, создай агента-документатора: он следит за проектом и автоматически обновляет документацию при изменениях.
Cat: AGENTS | Documentation Agent
Diff: L3 | Tools: documents, code, files | Web0 Code1 Files1 Vision0 Long0 | Auto 7
Why: актуальная документация всегда готова без лишних усилий
Caps: documentation agent, auto update, changelog, knowledge sync
---

### 1156 — Агент-синоптик новостей
Джарвис, создай агента-синоптика: он собирает новости по моим темам, фильтрует по важности и присылает утреннюю сводку.
Cat: AGENTS | News Agent
Diff: L2 | Tools: web, research | Web1 Code0 Files1 Vision0 Long0 | Auto 6
Why: персонализированная сводка экономит час чтения новостей
Caps: news digest, topic filtering, daily briefing, aggregation
---

### 1157 — Агент-модератор чата
Джарвис, создай агента-модератора: он следит за сообщениями, ловит токсичность, спам и нарушения правил, отвечая по регламенту.
Cat: AGENTS | Moderation
Diff: L3 | Tools: code, data | Web0 Code1 Files1 Vision0 Long0 | Auto 7
Why: автономная модерация защищает сообщество в любое время суток
Caps: moderation agent, toxic detection, spam filtering, policy enforcement
---

### 1158 — Роли в мультиагентной команде
Джарвис, опиши роли в агентной команде: координатор, исполнитель, критик, аналитик, документатор — кто за что отвечает и как взаимодействует.
Cat: AGENTS | Team Design
Diff: L3 | Tools: documents, diagrams | Web0 Code0 Files1 Vision0 Long0 | Auto 6
Why: ясные роли агентов предотвращают дублирование и конфликты
Caps: agent roles, team structure, collaboration model, responsibility
---

### 1159 — Агент-компаньон для учёбы
Джарвис, создай агента-компаньона: он задаёт вопросы по теме, проверяет ответы, объясняет ошибки и ведёт прогресс обучения.
Cat: AGENTS | Learning Agent
Diff: L3 | Tools: conversation, documents | Web0 Code0 Files1 Vision0 Long0 | Auto 7
Why: учебный агент обеспечивает постоянную обратную связь
Caps: learning companion, quiz agent, progress tracking, explanation
---

### 1160 — Отчёты агента: формат и частота
Джарвис, настрой агента на регулярные отчёты: определи формат, состав разделов, частоту и канал доставки отчётов.
Cat: AGENTS | Reporting
Diff: L2 | Tools: documents, planning | Web0 Code0 Files1 Vision0 Long0 | Auto 6
Why: регулярные отчёты агента делают его работу прозрачной
Caps: agent reporting, report format, delivery schedule, transparency
---

### 1161 — Агент для мониторинга конкурентов
Джарвис, создай агента наблюдения за конкурентами: он отслеживает их сайты, цены и анонсы, и сообщает о значимых изменениях.
Cat: AGENTS | Competitive Intelligence
Diff: L3 | Tools: web, research | Web1 Code0 Files1 Vision0 Long0 | Auto 7
Why: раннее обнаружение действий конкурентов даёт время на реакцию
Caps: competitor monitoring, price tracking, change alerts, intelligence
---

### 1162 — Агент-секретарь
Джарвис, создай агента-секретаря: он отвечает на стандартные обращения, записывает встречи и перенаправляет сложные вопросы мне.
Cat: AGENTS | Assistant
Diff: L3 | Tools: email, calendar, documents | Web0 Code0 Files1 Vision0 Long0 | Auto 7
Why: секретарь-агент разгружает от рутинной коммуникации
Caps: secretary agent, auto reply, scheduling, routing
---

### 1163 — Критик в команде агентов
Джарвис, добавь агента-критика в команду: он проверяет решения других агентов, находит слабые места и предлагает улучшения.
Cat: AGENTS | Critique
Diff: L3 | Tools: conversation, documents | Web0 Code0 Files1 Vision0 Long0 | Auto 7
Why: конструктивная критика повышает качество решений команды
Caps: critic agent, review, weakness detection, improvement suggestions
---

### 1164 — Агент-историк проекта
Джарвис, создай агента-историка: он фиксирует решения, причины и итоги по проекту, чтобы всегда можно было восстановить логику.
Cat: AGENTS | Memory
Diff: L2 | Tools: documents, files | Web0 Code0 Files1 Vision0 Long0 | Auto 6
Why: история решений экономит время при возврате к проекту
Caps: project historian, decision log, rationale, context recovery
---

### 1165 — Параллельные агенты: разделение по данным
Джарвис, распараллель агентов по данным: раздели массив на части, назначь агенту на каждую, затем объедини результаты.
Cat: AGENTS | Parallel Processing
Diff: L4 | Tools: code, data | Web0 Code1 Files1 Vision0 Long0 | Auto 8
Why: параллельная обработка сокращает время больших задач в разы
Caps: map reduce agents, parallel processing, data partitioning, result merge
---

### 1166 — Агент-фильтр информации
Джарвис, создай агента-фильтра: он принимает поток информации и оставляет только релевантное моим целям и интересам.
Cat: AGENTS | Filtering
Diff: L2 | Tools: web, data | Web1 Code0 Files1 Vision0 Long0 | Auto 6
Why: фильтрация шума фокусирует внимание на действительно важном
Caps: information filter, relevance scoring, noise reduction, curation
---

### 1167 — Агент-генератор идей
Джарвис, создай агента-генератора идей: он выдаёт варианты решений по запросу, оценивает их по критериям и ранжирует.
Cat: AGENTS | Ideation
Diff: L2 | Tools: conversation, documents | Web0 Code0 Files1 Vision0 Long0 | Auto 6
Why: системная генерация вариантов повышает качество выбора
Caps: ideation agent, option generation, scoring, ranking
---

### 1168 — Агент-компилятор отчётов
Джарвис, создай агента-компилятора: он собирает разрозненные данные и отчёты в единый документ с оглавлением и выводами.
Cat: AGENTS | Synthesis
Diff: L2 | Tools: documents, data | Web0 Code0 Files1 Vision0 Long0 | Auto 6
Why: автоматическая компиляция отчётов экономит часы ручной сборки
Caps: report compilation, synthesis, document assembly, executive summary
---

### 1169 — Верификация работы агента
Джарвис, проверь работу агента: сверь результат с требованиями, прогони тесты и подтверди, что задача выполнена корректно.
Cat: AGENTS | Verification
Diff: L3 | Tools: code, documents | Web0 Code0 Files1 Vision0 Long0 | Auto 7
Why: проверка результатов агентов обязательна до их использования
Caps: agent verification, result validation, acceptance criteria, testing
---

### 1170 — Агент для личного ассистента
Джарвис, создай персонального агента: он знает мои привычки, напоминает о важном, помогает в планировании и выполняет рутину.
Cat: AGENTS | Personal Agent
Diff: L3 | Tools: calendar, documents, planning | Web0 Code0 Files1 Vision0 Long0 | Auto 7
Why: персональный агент превращает ассистента в проактивного партнёра
Caps: personal assistant, habit awareness, proactive help, routine automation
---

### 1171 — Описание изображения
Джарвис, опиши изображение подробно: объекты, действия, атмосфера, текст на картинке и технические детали съёмки.
Cat: VISION | Image Description
Diff: L1 | Tools: vision | Web0 Code0 Files1 Vision1 Long0 | Auto 6
Why: точное описание нужно для каталогов, доступности и анализа
Caps: image description, object recognition, scene analysis, alt text
---

### 1172 — Распознавание текста на изображении
Джарвис, извлеки текст с изображения: распознай символы, сохрани структуру абзацев и укажи язык текста.
Cat: VISION | OCR
Diff: L2 | Tools: vision, files | Web0 Code0 Files1 Vision1 Long0 | Auto 6
Why: OCR превращает фото документов в редактируемый текст
Caps: ocr, text extraction, document scanning, structure preservation
---

### 1173 — Анализ фотографии: композиция и качество
Джарвис, проанализируй фотографию: композиция, свет, фокус, цвет и технические дефекты — дай советы по улучшению съёмки.
Cat: VISION | Photo Analysis
Diff: L2 | Tools: vision | Web0 Code0 Files1 Vision1 Long0 | Auto 6
Why: профессиональный разбор фото помогает расти как фотографу
Caps: photo critique, composition, lighting analysis, quality assessment
---

### 1174 — Сравнение двух изображений
Джарвис, сравни два изображения: различия в деталях, изменения между версиями и оценку, какое лучше и почему.
Cat: VISION | Comparison
Diff: L2 | Tools: vision | Web0 Code0 Files1 Vision1 Long0 | Auto 6
Why: сравнение изображений нужно при ретуши, контроле и выборе
Caps: image comparison, diff detection, version comparison, quality ranking
---

### 1175 — Распознавание объектов на фото
Джарвис, определи объекты на изображении: что изображено, сколько объектов, их расположение и вероятные категории.
Cat: VISION | Object Detection
Diff: L2 | Tools: vision | Web0 Code0 Files1 Vision1 Long0 | Auto 6
Why: распознавание объектов автоматизирует каталогизацию и поиск
Caps: object detection, classification, counting, localization
---

### 1176 — Анализ диаграмм и графиков
Джарвис, прочитай диаграмму или график: что показывает, ключевые значения, тренды и аномалии — изложи текстом.
Cat: VISION | Chart Reading
Diff: L2 | Tools: vision, data | Web0 Code0 Files1 Vision1 Long0 | Auto 6
Why: извлечение данных из графиков делает отчёты доступными
Caps: chart reading, data extraction, trend analysis, anomaly spotting
---

### 1177 — Анализ скриншота интерфейса
Джарвис, проанализируй скриншот интерфейса: элементы, состояние, ошибки и предложения по улучшению юзабилити.
Cat: VISION | UI Analysis
Diff: L2 | Tools: vision | Web0 Code0 Files1 Vision1 Long0 | Auto 6
Why: разбор скриншотов ускоряет тестирование интерфейсов
Caps: ui analysis, screenshot review, usability issues, design feedback
---

### 1178 — Модерация изображений по правилам
Джарвис, проверь изображение на соответствие правилам: запрещённый контент, брендинг, текст и требования площадки.
Cat: VISION | Moderation
Diff: L2 | Tools: vision | Web0 Code0 Files1 Vision1 Long0 | Auto 6
Why: автоматическая модерация защищает площадку и репутацию
Caps: image moderation, policy check, content safety, compliance
---

### 1179 — Распознавание лиц и людей
Джарвис, опиши людей на изображении: количество, возраст, эмоции, одежда — без идентификации личности, только общие признаки.
Cat: VISION | People Analysis
Diff: L2 | Tools: vision | Web0 Code0 Files1 Vision1 Long0 | Auto 6
Why: общее описание людей нужно для аналитики аудитории и фотосъёмки
Caps: people detection, emotion recognition, demographic estimation, crowd analysis
---

### 1180 — Разбор схемы или чертежа
Джарвис, разбери схему или чертёж: элементы, соединения, обозначения и логику работы — изложи понятным текстом.
Cat: VISION | Diagram Analysis
Diff: L3 | Tools: vision, documents | Web0 Code0 Files1 Vision1 Long0 | Auto 7
Why: объяснение схем ускоряет понимание технической документации
Caps: diagram reading, blueprint analysis, symbol recognition, circuit explanation
---

### 1181 — Восстановление обрезанного текста на фото
Джарвис, восстанови текст с повреждённого или обрезанного фото: уточни нечитаемые фрагменты по контексту и отметь предположения.
Cat: VISION | Text Recovery
Diff: L3 | Tools: vision | Web0 Code0 Files1 Vision1 Long0 | Auto 7
Why: восстановление текста спасает данные с повреждённых снимков
Caps: text recovery, partial ocr, context reconstruction, damaged photo
---

### 1182 — Сканирование визиток и карточек
Джарвис, извлеки данные с визитки или карточки: имя, компания, контакты — и оформи в структурированную запись.
Cat: VISION | Business Cards
Diff: L1 | Tools: vision, documents | Web0 Code0 Files1 Vision1 Long0 | Auto 6
Why: оцифровка визиток создаёт чистую базу контактов
Caps: business card scan, contact extraction, structured data, digitalization
---

### 1183 — Оценка качества скана документа
Джарвис, оцени качество скана: резкость, контраст, перекос и читаемость — предложи настройки для лучшего сканирования.
Cat: VISION | Scan Quality
Diff: L1 | Tools: vision | Web0 Code0 Files1 Vision1 Long0 | Auto 6
Why: качественный скан лучше распознаётся и дольше хранится
Caps: scan quality, sharpness check, skew detection, scan settings
---

### 1184 — Анализ кадра видео
Джарвис, проанализируй кадр из видео: что происходит, композиция, качество и возможные проблемы съёмки.
Cat: VISION | Video Frame Analysis
Diff: L2 | Tools: vision, video | Web0 Code0 Files1 Vision1 Long0 | Auto 6
Why: анализ кадров помогает отбирать лучшие моменты видео
Caps: frame analysis, video still review, scene understanding, shot quality
---

### 1185 — Распознавание рукописного текста
Джарвис, распознай рукописный текст: разбери почерк, восстанови слова по контексту и отметь места, где не уверен.
Cat: VISION | Handwriting OCR
Diff: L3 | Tools: vision | Web0 Code0 Files1 Vision1 Long0 | Auto 7
Why: распознавание рукописей оцифровывает заметки и архивы
Caps: handwriting recognition, cursive reading, context inference, uncertain flags
---

### 1186 — Проверка соответствия макету
Джарвис, сравни реализацию с макетом: найди расхождения в расположении, цветах, размерах и типографике.
Cat: VISION | Design QA
Diff: L2 | Tools: vision | Web0 Code0 Files1 Vision1 Long0 | Auto 6
Why: сверка с макетом ловит ошибки вёрстки до релиза
Caps: design qa, mockup comparison, layout diff, pixel check
---

### 1187 — Извлечение данных из таблицы на фото
Джарвис, извлеки таблицу с фотографии: распознай строки, столбцы и ячейки — оформи в электронную таблицу.
Cat: VISION | Table Extraction
Diff: L2 | Tools: vision, data | Web0 Code0 Files1 Vision1 Long0 | Auto 6
Why: оцифровка таблиц с фото экономит ручной ввод данных
Caps: table extraction, spreadsheet conversion, structure detection, data entry
---

### 1188 — Анализ медицинского снимка (справочно)
Джарвис, опиши, что видно на медицинском снимке с точки зрения общих признаков, но подчеркни, что диагноз должен ставить врач.
Cat: VISION | Medical Images
Diff: L3 | Tools: vision, research | Web1 Code0 Files1 Vision1 Long0 | Auto 7
Why: общее описание снимка помогает пациенту, но не заменяет врача
Caps: medical image overview, anomaly description, radiologist referral, disclaimer
---

### 1189 — Идентификация растений, животных, предметов
Джарвис, определи, что изображено: растение, животное или предмет — с научным названием и интересными фактами.
Cat: VISION | Identification
Diff: L2 | Tools: vision, research | Web1 Code0 Files1 Vision1 Long0 | Auto 6
Why: определение объектов на фото расширяет знания на практике
Caps: species identification, object recognition, scientific name, fun facts
---

### 1190 — Анализ инфографики
Джарвис, разбери инфографику: главное сообщение, структура, цифры и качество подачи — оцени её понятность.
Cat: VISION | Infographic Analysis
Diff: L2 | Tools: vision | Web0 Code0 Files1 Vision1 Long0 | Auto 6
Why: критический разбор инфографики выявляет манипуляции данными
Caps: infographic analysis, message extraction, data check, clarity rating
---

### 1191 — Автоматизация действий в браузере
Джарвис, автоматизируй действия в браузере: открытие страниц, клики, заполнение форм и сбор результатов по сценарию.
Cat: UI-AUTOMATION | Browser
Diff: L3 | Tools: web, code | Web1 Code1 Files0 Vision0 Long0 | Auto 7
Why: браузерная автоматизация убирает рутинные повторяющиеся операции
Caps: browser automation, web scraping, form filling, scripted clicks
---

### 1192 — Парсинг данных с сайта
Джарвис, собери данные с сайта: определи селекторы, извлеки нужные поля со всех страниц и сохрани в таблицу.
Cat: UI-AUTOMATION | Scraping
Diff: L3 | Tools: web, code, data | Web1 Code1 Files1 Vision0 Long0 | Auto 7
Why: автоматический парсинг экономит дни ручного сбора данных
Caps: web scraping, data extraction, pagination handling, csv export
---

### 1193 — Заполнение форм автоматически
Джарвис, заполни формы автоматически: сопоставь поля с моими данными, подставь значения и проверь результат.
Cat: UI-AUTOMATION | Forms
Diff: L2 | Tools: web, code | Web1 Code1 Files0 Vision0 Long0 | Auto 6
Why: автозаполнение избавляет от однотипных действий с формами
Caps: form autofill, field mapping, data matching, submission
---

### 1194 — Скриншоты страниц по расписанию
Джарвис, делай скриншоты страниц по расписанию: сохраняй в папку с датой и формируй сравнение изменений.
Cat: UI-AUTOMATION | Screenshots
Diff: L2 | Tools: web, files | Web1 Code0 Files1 Vision0 Long0 | Auto 6
Why: регулярные скриншоты фиксируют изменения интерфейса и контента
Caps: scheduled screenshots, full page capture, change detection, archiving
---

### 1195 — Тестирование интерфейса по сценарию
Джарвис, прогони сценарий тестирования интерфейса: выполни шаги пользователя, зафиксируй результаты и найди ошибки.
Cat: UI-AUTOMATION | Testing
Diff: L3 | Tools: web, code | Web1 Code1 Files0 Vision0 Long0 | Auto 7
Why: автотесты интерфейса ловят регрессии до пользователей
Caps: ui testing, scenario execution, error capture, test reports
---

### 1196 — Клик по координатам на экране
Джарвис, выполни клик по указанным координатам экрана и опиши, что открылось или изменилось.
Cat: UI-AUTOMATION | Desktop
Diff: L2 | Tools: code | Web0 Code1 Files0 Vision0 Long0 | Auto 6
Why: точечные клики управляют приложениями без API
Caps: screen coordinates, click automation, desktop control, action verification
---

### 1197 — Чтение и извлечение данных с экрана
Джарвис, прочитай содержимое экрана или активного окна: текст, элементы и состояния — и структурируй результат.
Cat: UI-AUTOMATION | Screen Reading
Diff: L2 | Tools: code, vision | Web0 Code0 Files0 Vision1 Long0 | Auto 6
Why: чтение экрана позволяет агентам работать с любым ПО
Caps: screen reading, ui state extraction, text capture, window analysis
---

### 1198 — Мониторинг изменения страницы
Джарвис, следи за страницей: проверяй её через интервалы и сообщай, когда появится указанное изменение или товар.
Cat: UI-AUTOMATION | Monitoring
Diff: L2 | Tools: web | Web1 Code0 Files0 Vision0 Long0 | Auto 6
Why: мониторинг страниц ловит важные изменения раньше всех
Caps: page monitoring, change alerts, product availability, price watch
---

### 1199 — Экспорт данных из приложения
Джарвис, извлеки данные из приложения или веб-сервиса: обойди интерфейс, собери записи и сохрани в нужном формате.
Cat: UI-AUTOMATION | Export
Diff: L3 | Tools: web, code, data | Web1 Code1 Files1 Vision0 Long0 | Auto 7
Why: экспорт через интерфейс спасает, когда нет API
Caps: data export, ui scraping, record extraction, format conversion
---

### 1200 — Автологин и работа в системе
Джарвис, автоматизируй вход в систему: сохранённые учётные данные, вход и выполнение рутины с обработкой капчи вручную.
Cat: UI-AUTOMATION | Sessions
Diff: L3 | Tools: web, code | Web1 Code1 Files0 Vision0 Long0 | Auto 7
Why: автоматический вход ускоряет работу в системах без SSO
Caps: auto login, session management, credential handling, routine automation
---

### 1201 — Автоматизация Excel через интерфейс
Джарвис, выполни операции в Excel автоматически: открытие файла, изменения, формулы и сохранение — как если бы делал это человек.
Cat: UI-AUTOMATION | Office
Diff: L2 | Tools: code, files | Web0 Code1 Files1 Vision0 Long0 | Auto 6
Why: интерфейсная автоматизация работает там, где нет макросов
Caps: excel automation, office ui, cell editing, file operations
---

### 1202 — Сбор данных с нескольких страниц
Джарвис, пройди по списку URL и собери данные с каждой страницы: навигация, извлечение, пагинация и единая таблица результатов.
Cat: UI-AUTOMATION | Crawling
Diff: L3 | Tools: web, code, data | Web1 Code1 Files1 Vision0 Long0 | Auto 7
Why: массовый сбор данных даёт полную картину вместо выборки
Caps: multi page crawl, navigation automation, result aggregation, csv output
---

### 1203 — Отчёт о ходе автоматизации
Джарвис, веди журнал автоматизации: что выполнено, что не удалось, время операций и ошибки — с итоговым отчётом.
Cat: UI-AUTOMATION | Logging
Diff: L2 | Tools: documents, code | Web0 Code1 Files1 Vision0 Long0 | Auto 6
Why: журнал автоматизации упрощает отладку и отчётность
Caps: automation log, operation history, error report, timing data
---

### 1204 — Проверка доступности элементов
Джарвис, проверь доступность элементов интерфейса: найди кнопки, поля и ссылки, определи их состояние и опиши, как с ними взаимодействовать.
Cat: UI-AUTOMATION | Element Discovery
Diff: L2 | Tools: web, code | Web1 Code1 Files0 Vision0 Long0 | Auto 6
Why: карта элементов — основа любых скриптов автоматизации
Caps: element discovery, selector generation, state detection, interaction plan
---

### 1205 — Восстановление после сбоя автоматизации
Джарвис, разбери сбой в автоматизации: найди шаг с ошибкой, предложи исправление и добавь обработку подобных ситуаций.
Cat: UI-AUTOMATION | Recovery
Diff: L3 | Tools: code, documents | Web0 Code1 Files1 Vision0 Long0 | Auto 7
Why: устойчивые к сбоям скрипты работают без присмотра
Caps: failure recovery, error handling, retry logic, debugging automation
---

### 1206 — Ведение заметок: система
Джарвис, создай систему ведения заметок: структура папок, шаблоны, теги и правила захвата идей — под мой стиль работы.
Cat: NOTES | System
Diff: L2 | Tools: documents, files | Web0 Code0 Files1 Vision0 Long0 | Auto 6
Why: система заметок сохраняет идеи и делает их находимыми
Caps: note taking system, folder structure, templates, tags
---

### 1207 — Быстрый захват идеи
Джарвис, зафиксируй мою идею: оформи кратко, добавь контекст, возможные следующие шаги и теги для поиска.
Cat: NOTES | Capture
Diff: L1 | Tools: documents | Web0 Code0 Files1 Vision0 Long0 | Auto 6
Why: мгновенный захват идеи не даёт ей потеряться
Caps: idea capture, quick notes, context, next actions
---

### 1208 — Поиск по заметкам
Джарвис, найди в моих заметках всё по теме: полный текст, теги и близкие по смыслу записи — со сводкой.
Cat: NOTES | Search
Diff: L1 | Tools: files | Web0 Code0 Files1 Vision0 Long0 | Auto 6
Why: быстрый поиск превращает архив заметок в рабочую память
Caps: note search, full text, tag filtering, semantic retrieval
---

### 1209 — Структурирование хаотичных заметок
Джарвис, наведи порядок в заметках: сгруппируй по темам, объедини дубли, приведи к единому формату.
Cat: NOTES | Organization
Diff: L2 | Tools: documents, files | Web0 Code0 Files1 Vision0 Long0 | Auto 6
Why: чистые заметки легче находить и использовать
Caps: note organization, deduplication, topic grouping, format normalization
---

### 1210 — Конспект встречи в заметки
Джарвис, преврати записи встречи в структурированные заметки: решения, задачи, ответственные и сроки.
Cat: NOTES | Meetings
Diff: L1 | Tools: documents | Web0 Code0 Files1 Vision0 Long0 | Auto 6
Why: конспект встречи фиксирует договорённости и не даёт им забыться
Caps: meeting notes, decisions, action items, owners
---

### 1211 — Журнал (дневник) по дням
Джарвис, веди мой журнал: ежедневные записи с итогами дня, инсайтами и планами на завтра — по заданному шаблону.
Cat: NOTES | Journaling
Diff: L1 | Tools: documents | Web0 Code0 Files1 Vision0 Long0 | Auto 6
Why: дневник помогает рефлексии и отслеживанию прогресса
Caps: journal, daily log, reflection, template
---

### 1212 — Заметки по проекту
Джарвис, организуй заметки по проекту: контекст, цели, решения, вопросы и ссылки на материалы — в одном месте.
Cat: NOTES | Projects
Diff: L2 | Tools: documents, files | Web0 Code0 Files1 Vision0 Long0 | Auto 6
Why: единый контекст проекта ускоряет возврат к работе
Caps: project notes, context, decisions, references
---

### 1213 — Извлечение ключевых мыслей из лекции
Джарвис, преврати запись лекции в конспект: ключевые мысли, примеры, связи и вопросы для разбора.
Cat: NOTES | Summarization
Diff: L1 | Tools: documents | Web0 Code0 Files1 Vision0 Long0 | Auto 6
Why: конспект лекции концентрирует знание для повторения
Caps: lecture notes, key points, examples, questions
---

### 1214 — Цитатник и избранное
Джарвис, собери цитаты и важные фрагменты: сохрани с источниками, категориями и контекстом использования.
Cat: NOTES | Quotes
Diff: L1 | Tools: documents | Web0 Code0 Files1 Vision0 Long0 | Auto 6
Why: организованное избранное легко цитировать и переиспользовать
Caps: quote collection, sources, categories, citation-ready
---

### 1215 — Трекер привычек в заметках
Джарвис, создай трекер привычек: список привычек, ежедневные отметки, статистика выполнения и напоминания о пропусках.
Cat: NOTES | Habits
Diff: L2 | Tools: documents, data | Web0 Code0 Files1 Vision0 Long0 | Auto 6
Why: видимый трекер привычек повышает их удержание
Caps: habit tracker, streak, statistics, reminders
---

### 1216 — Библиотека шаблонов заметок
Джарвис, собери библиотеку шаблонов: для встреч, проектов, обучения, планирования — с пояснением, когда какой использовать.
Cat: NOTES | Templates
Diff: L1 | Tools: documents | Web0 Code0 Files1 Vision0 Long0 | Auto 6
Why: готовые шаблоны экономят время на каждый тип записи
Caps: note templates, template library, reuse, consistency
---

### 1217 — Заметки: связывание и карта связей
Джарвис, свяжи мои заметки между собой: найди пересечения тем, построй карту связей и предложи новые соединения идей.
Cat: NOTES | Linking
Diff: L2 | Tools: documents, files, data | Web0 Code0 Files1 Vision0 Long0 | Auto 6
Why: связанные заметки рождают новые идеи на стыках тем
Caps: note linking, connections, knowledge graph, insight discovery
---

### 1218 — Архивация старых заметок
Джарвис, проведи архивацию заметок: устаревшие — в архив, активные — по приоритету, удали бесполезное с подтверждением.
Cat: NOTES | Archiving
Diff: L1 | Tools: files, documents | Web0 Code0 Files1 Vision0 Long0 | Auto 6
Why: регулярная архивация держит рабочее пространство чистым
Caps: note archiving, cleanup, prioritization, retention
---

### 1219 — Заметки в формате Zettelkasten
Джарвис, организуй заметки по методу Zettelkasten: атомарные записи, уникальные ID, связи и индекс тем.
Cat: NOTES | Zettelkasten
Diff: L2 | Tools: documents, files | Web0 Code0 Files1 Vision0 Long0 | Auto 6
Why: Zettelkasten превращает заметки в работающую систему знаний
Caps: zettelkasten, atomic notes, ids, linking, index
---

### 1220 — Ежедневные заметки: обзор и ревью
Джарвис, проведи ревью моих заметок: выдели ключевые идеи, нерешённые вопросы и идеи, достойные развития.
Cat: NOTES | Review
Diff: L2 | Tools: documents, files | Web0 Code0 Files1 Vision0 Long0 | Auto 6
Why: регулярное ревью превращает записи в источник решений
Caps: note review, key ideas, open questions, development candidates
---
### 1221 — Построение базы знаний
Джарвис, создай базу знаний: структура разделов, формат статей, теги, ответственные за обновление и правила использования.
Cat: KNOWLEDGE | Knowledge Base
Diff: L3 | Tools: documents, planning | Web0 Code0 Files1 Vision0 Long0 | Auto 7
Why: база знаний сохраняет экспертизу команды внутри компании
Caps: knowledge base, structure, article format, ownership
---

### 1222 — Извлечение знаний из документов
Джарвис, извлеки знания из документов: главные положения, термины, правила и процедуры — оформи как статьи базы.
Cat: KNOWLEDGE | Extraction
Diff: L2 | Tools: documents, files | Web0 Code0 Files1 Vision0 Long0 | Auto 6
Why: конверсия документов в базу делает знания доступными
Caps: knowledge extraction, document conversion, terms, procedures
---

### 1223 — Карта знаний по области
Джарвис, построй карту знаний по области: темы, подтемы, связи и уровень освоения каждой — в виде диаграммы.
Cat: KNOWLEDGE | Mapping
Diff: L2 | Tools: documents, diagrams | Web0 Code0 Files1 Vision0 Long0 | Auto 6
Why: карта знаний показывает структуру области и пробелы
Caps: knowledge map, topic tree, skill levels, diagram
---

### 1224 — Глоссарий и единая терминология
Джарвис, создай глоссарий: термины, определения, синонимы и правила использования — для согласованных коммуникаций.
Cat: KNOWLEDGE | Glossary
Diff: L1 | Tools: documents | Web0 Code0 Files1 Vision0 Long0 | Auto 6
Why: единая терминология устраняет разночтения в команде
Caps: glossary, terminology, definitions, consistency
---

### 1225 — Управление знаниями: процесс
Джарвис, опиши процесс управления знаниями: создание, хранение, обмен, применение и обновление знаний в организации.
Cat: KNOWLEDGE | KM Process
Diff: L2 | Tools: documents, planning | Web0 Code0 Files1 Vision0 Long0 | Auto 6
Why: процессный подход делает знания активом, а не архивом
Caps: knowledge management, process design, sharing, updating
---

### 1226 — Резюме статьи для базы знаний
Джарвис, подготовь статью для базы знаний по присланному материалу: кратко, структурированно, с практическими выводами.
Cat: KNOWLEDGE | Article Creation
Diff: L1 | Tools: documents | Web0 Code0 Files1 Vision0 Long0 | Auto 6
Why: короткие статьи базы читают чаще, чем длинные исходники
Caps: article summary, knowledge base entry, practical takeaways
---

### 1227 — Поиск знаний по запросу
Джарвис, найди ответ в моей базе знаний: просмотри материалы, собери релевантное и дай ответ со ссылками на источники.
Cat: KNOWLEDGE | Retrieval
Diff: L2 | Tools: files, research | Web0 Code0 Files1 Vision0 Long0 | Auto 6
Why: быстрый поиск по базе превращает её в рабочий инструмент
Caps: knowledge retrieval, search, citations, answers
---

### 1228 — Выявление пробелов в знаниях
Джарвис, проанализируй мою базу знаний: найди пробелы, устаревшие и противоречивые материалы — составь план заполнения.
Cat: KNOWLEDGE | Gap Analysis
Diff: L2 | Tools: files, documents | Web0 Code0 Files1 Vision0 Long0 | Auto 6
Why: аудит базы показывает, что реально отсутствует
Caps: knowledge gaps, outdated content, contradictions, fill plan
---

### 1229 — Онбординг-пакет на основе базы
Джарвис, собери пакет для нового сотрудника: материалы из базы, порядок изучения, чек-листы и контакты — по ролям.
Cat: KNOWLEDGE | Onboarding
Diff: L2 | Tools: documents, files | Web0 Code0 Files1 Vision0 Long0 | Auto 6
Why: онбординг на базе знаний сокращает время выхода на результат
Caps: onboarding pack, learning path, checklists, role based
---

### 1230 — FAQ: создание и поддержка
Джарвис, создай FAQ: собери частые вопросы, напиши понятные ответы и определи порядок обновления при новых вопросах.
Cat: KNOWLEDGE | FAQ
Diff: L1 | Tools: documents | Web0 Code0 Files1 Vision0 Long0 | Auto 6
Why: качественный FAQ разгружает поддержку и клиентов
Caps: faq, common questions, answers, maintenance
---

### 1231 — Экспертные интервью в знания
Джарвис, преврати интервью с экспертом в статьи базы: ключевые идеи, практики и предостережения — структурировано.
Cat: KNOWLEDGE | Expert Capture
Diff: L2 | Tools: documents | Web0 Code0 Files1 Vision0 Long0 | Auto 6
Why: фиксация экспертного опыта сохраняет его при уходе сотрудника
Caps: expert interview, knowledge capture, best practices, retention
---

### 1232 — Оценка качества материалов базы
Джарвис, оцени качество материалов базы знаний: актуальность, точность, полнота и читаемость — по чек-листу с оценками.
Cat: KNOWLEDGE | Quality
Diff: L2 | Tools: documents, files | Web0 Code0 Files1 Vision0 Long0 | Auto 6
Why: контроль качества держит базу знаний полезной
Caps: knowledge quality, audit checklist, accuracy, completeness
---

### 1233 — Автоматическое пополнение базы
Джарвис, настрой автоматическое пополнение базы знаний: новые документы и обсуждения превращаются в статьи по правилам.
Cat: KNOWLEDGE | Automation
Diff: L3 | Tools: files, code, documents | Web0 Code1 Files1 Vision0 Long0 | Auto 7
Why: автоматическое пополнение поддерживает базу в актуальности
Caps: knowledge automation, ingestion, rules, auto article
---

### 1234 — Справочник процессов и регламентов
Джарвис, собери справочник процессов: описание шагов, роли, сроки и регламенты — в единой структуре.
Cat: KNOWLEDGE | Playbooks
Diff: L2 | Tools: documents | Web0 Code0 Files1 Vision0 Long0 | Auto 6
Why: справочник процессов делает работу независимой от сотрудников
Caps: process handbook, playbooks, standard operating procedures
---

### 1235 — Уроки извлечённые (lessons learned)
Джарвис, оформи уроки извлечённые из проекта: что пошло не так, почему, что делать иначе — в базу знаний.
Cat: KNOWLEDGE | Lessons Learned
Diff: L2 | Tools: documents | Web0 Code0 Files1 Vision0 Long0 | Auto 6
Why: зафиксированные уроки защищают будущие проекты от повторных ошибок
Caps: lessons learned, retrospective, root cause, improvements
---

### 1236 — Знания для принятия решений
Джарвис, собери знания, необходимые для решения: факты, варианты, критерии и прецеденты — в структурированную справку.
Cat: KNOWLEDGE | Decision Support
Diff: L2 | Tools: files, research | Web1 Code0 Files1 Vision0 Long0 | Auto 6
Why: полная справка снижает риск ошибочных решений
Caps: decision support, evidence pack, precedents, criteria
---

### 1237 — Безопасность знаний и доступы
Джарвис, настрой доступ к базе знаний: уровни прав, конфиденциальные разделы и правила публикации.
Cat: KNOWLEDGE | Access Control
Diff: L2 | Tools: documents, files | Web0 Code0 Files1 Vision0 Long0 | Auto 6
Why: контроль доступа защищает чувствительные знания
Caps: access control, permissions, confidentiality, publication rules
---

### 1238 — Вовлечение команды в базу знаний
Джарвис, разработай план вовлечения команды в базу знаний: мотивация, регулярность вклада и признание авторов.
Cat: KNOWLEDGE | Culture
Diff: L2 | Tools: documents, planning | Web0 Code0 Files1 Vision0 Long0 | Auto 6
Why: база знаний живёт, пока команда её наполняет
Caps: knowledge sharing culture, contribution plan, recognition
---

### 1239 — Сравнение источников знаний
Джарвис, сравни источники по теме: полнота, достоверность, актуальность и удобство — порекомендуй лучшие для использования.
Cat: KNOWLEDGE | Sources
Diff: L2 | Tools: research | Web1 Code0 Files1 Vision0 Long0 | Auto 6
Why: выбор надёжных источников определяет качество знаний
Caps: source comparison, reliability, relevance, recommendations
---

### 1240 — Знаниевая аналитика: что читают
Джарвис, проанализируй использование базы знаний: какие статьи читают, где ищут и чего не находят — предложи улучшения.
Cat: KNOWLEDGE | Analytics
Diff: L2 | Tools: data, files | Web0 Code0 Files1 Vision0 Long0 | Auto 6
Why: аналитика использования показывает, что менять в базе
Caps: knowledge analytics, usage patterns, search gaps, improvements
---

### 1241 — Проактивное напоминание о сроках
Джарвис, напоминай мне о важных сроках заранее: за 7, 3 и 1 день — с готовым списком действий.
Cat: PROACTIVE | Deadlines
Diff: L1 | Tools: planning, calendar | Web0 Code0 Files1 Vision0 Long0 | Auto 6
Why: ранние напоминания исключают срыв сроков
Caps: deadline reminders, advance notice, action checklist
---

### 1242 — Инициативные предложения по проекту
Джарвис, следи за моим проектом и предлагай улучшения: риски, возможности и действия — без моего запроса.
Cat: PROACTIVE | Suggestions
Diff: L2 | Tools: files, documents | Web0 Code0 Files1 Vision0 Long0 | Auto 6
Why: проактивные предложения добавляют ценность до возникновения проблем
Caps: proactive suggestions, risk spotting, opportunity, initiative
---

### 1243 — Проактивный мониторинг важных событий
Джарвис, наблюдай за важными событиями: изменения цен, статусы заказов, публикации и уведомляй при существенных изменениях.
Cat: PROACTIVE | Monitoring
Diff: L2 | Tools: web, data | Web1 Code0 Files1 Vision0 Long0 | Auto 6
Why: раннее уведомление даёт время отреагировать
Caps: event monitoring, status tracking, change alerts, notifications
---

### 1244 — Утренний брифинг
Джарвис, готовь мне утренний брифинг: календарь, погода, задачи дня, важные новости и напоминания — по расписанию.
Cat: PROACTIVE | Briefing
Diff: L2 | Tools: web, calendar, planning | Web1 Code0 Files1 Vision0 Long0 | Auto 6
Why: утренний брифинг настраивает день без самостоятельного сбора
Caps: daily briefing, calendar, weather, priorities
---

### 1245 — Проверка моих файлов на проблемы
Джарвис, регулярно проверяй мои файлы: повреждения, дубли, устаревшие версии и нехватку места — сообщай о найденном.
Cat: PROACTIVE | File Health
Diff: L2 | Tools: files | Web0 Code0 Files1 Vision0 Long0 | Auto 6
Why: превентивная проверка файлов спасает от потери данных
Caps: file health check, duplicates, corruption, storage
---

### 1246 — Превентивные действия по безопасности
Джарвис, следи за безопасностью моих аккаунтов и систем: необычная активность, утечки и слабые пароли — с предложением действий.
Cat: PROACTIVE | Security
Diff: L3 | Tools: web, research | Web1 Code0 Files1 Vision0 Long0 | Auto 7
Why: превентивная безопасность дешевле ликвидации последствий
Caps: proactive security, breach alerts, account check, recommendations
---

### 1247 — Умное планирование дня
Джарвис, предложи оптимальное расписание дня: приоритеты, энергетические пики, встречи и время для глубокой работы.
Cat: PROACTIVE | Scheduling
Diff: L2 | Tools: planning, calendar | Web0 Code0 Files1 Vision0 Long0 | Auto 6
Why: расписание по энергии повышает продуктивность без выгорания
Caps: day planning, energy scheduling, deep work, priorities
---

### 1248 — Отслеживание целей и прогресса
Джарвис, следи за моими целями: отслеживай прогресс по метрикам, напоминай о регулярных действиях и отмечай отклонения.
Cat: PROACTIVE | Goals
Diff: L2 | Tools: planning, data | Web0 Code0 Files1 Vision0 Long0 | Auto 6
Why: постоянный контроль целей удерживает фокус и темп
Caps: goal tracking, progress metrics, deviation alerts, motivation
---

### 1249 — Проактивные сводки по подпискам
Джарвис, следи за моими подписками и платежами: предупреждай о списаниях, дорогих подписках и неиспользуемых сервисах.
Cat: PROACTIVE | Subscriptions
Diff: L1 | Tools: web, data | Web1 Code0 Files1 Vision0 Long0 | Auto 6
Why: контроль подписок экономит сотни рублей ежемесячно
Caps: subscription tracking, renewal alerts, cost review, cancellation suggestions
---

### 1250 — Реагирование на новые запросы
Джарвис, следи за входящими запросами: почта, мессенджеры и формы — классифицируй срочность и предложи ответы.
Cat: PROACTIVE | Inbox
Diff: L2 | Tools: email, web | Web1 Code0 Files1 Vision0 Long0 | Auto 6
Why: быстрая реакция на запросы повышает доверие клиентов
Caps: inbox monitoring, request classification, suggested replies, urgency
---

### 1251 — Профилактика выгорания
Джарвис, следи за признаками перегрузки: объём задач, длительность работы и пропуски отдыха — предложи коррекцию.
Cat: PROACTIVE | Wellbeing
Diff: L1 | Tools: planning, data | Web0 Code0 Files1 Vision0 Long0 | Auto 6
Why: раннее выявление перегрузки предотвращает выгорание
Caps: burnout prevention, workload balance, rest reminders, wellbeing
---

### 1252 — Предложения по оптимизации процессов
Джарвис, проанализируй мои повторяющиеся действия и предложи автоматизацию: что автоматизировать, как и сколько это сэкономит.
Cat: PROACTIVE | Optimization
Diff: L2 | Tools: planning, documents | Web0 Code0 Files1 Vision0 Long0 | Auto 6
Why: автоматизация рутины освобождает часы каждую неделю
Caps: process optimization, automation candidates, time savings, recommendations
---

### 1253 — Слежение за трендами в области
Джарвис, следи за трендами в моей области: публикации, технологии и события — и готовь периодические сводки.
Cat: PROACTIVE | Trends
Diff: L2 | Tools: web, research | Web1 Code0 Files1 Vision0 Long0 | Auto 6
Why: раннее знание трендов даёт конкурентное преимущество
Caps: trend watching, industry updates, digests, early signals
---

### 1254 — Инициатива по завершению проекта
Джарвис, после завершения проекта предложи: уборку артефактов, фиксацию уроков, обновление документации и следующий шаг.
Cat: PROACTIVE | Wrap Up
Diff: L1 | Tools: files, documents | Web0 Code0 Files1 Vision0 Long0 | Auto 6
Why: правильное завершение проекта экономит время при возврате
Caps: project wrap up, cleanup, lessons, next steps
---

### 1255 — Проактивный контроль бюджета
Джарвис, следи за моим бюджетом: сравнивай фактические траты с планом и предупреждай о превышениях по категориям.
Cat: PROACTIVE | Budget
Diff: L2 | Tools: data, spreadsheets | Web0 Code0 Files1 Vision0 Long0 | Auto 6
Why: раннее предупреждение о перерасходе спасает бюджет
Caps: budget tracking, overrun alerts, category control, spending reports
---

### 1256 — Регулярный отчёт по расписанию
Джарвис, готовь отчёт по расписанию: ежедневно, еженедельно или ежемесячно — с фиксированным составом разделов.
Cat: SCHEDULED | Reports
Diff: L2 | Tools: documents, data, planning | Web0 Code0 Files1 Vision0 Long0 | Auto 6
Why: регулярные отчёты формируют привычку контроля
Caps: scheduled reports, report cadence, fixed structure, automation
---

### 1257 — Планировщик задач по времени
Джарвис, создай расписание задач: распредели дела по дням и часам, с учётом приоритетов и дедлайнов.
Cat: SCHEDULED | Task Scheduling
Diff: L2 | Tools: planning, calendar | Web0 Code0 Files1 Vision0 Long0 | Auto 6
Why: задачи по расписанию выполняются, а не откладываются
Caps: task scheduling, time allocation, priorities, calendar
---

### 1258 — Напоминания с контекстом
Джарвис, настрой напоминания с контекстом: каждое напоминание содержит суть, ссылку и следующий шаг.
Cat: SCHEDULED | Reminders
Diff: L1 | Tools: planning | Web0 Code0 Files1 Vision0 Long0 | Auto 6
Why: напоминание с контекстом сразу переводит к действию
Caps: reminders, context, next action, links
---

### 1259 — Календарная сетка недели
Джарвис, построй сетку недели: встречи, блоки глубокой работы, обучение и отдых — с защитой времени.
Cat: SCHEDULED | Weekly Planning
Diff: L1 | Tools: planning, calendar | Web0 Code0 Files1 Vision0 Long0 | Auto 6
Why: недельная сетка даёт баланс работы и восстановления
Caps: weekly grid, time blocking, deep work, rest
---

### 1260 — Регулярные проверки системы
Джарвис, настрой регулярные проверки: диска, обновлений, безопасности и резервных копий — по расписанию с отчётом.
Cat: SCHEDULED | System Checks
Diff: L2 | Tools: files, terminal | Web0 Code1 Files1 Vision0 Long0 | Auto 6
Why: плановые проверки ловят проблемы до критических сбоев
Caps: scheduled checks, disk, updates, backups, reports
---

### 1261 — Ежемесячный финансовый отчёт
Джарвис, готовь ежемесячный финансовый отчёт: доходы, расходы, накопления, инвестиции и сравнение с планом.
Cat: SCHEDULED | Finance
Diff: L2 | Tools: data, spreadsheets | Web0 Code0 Files1 Vision0 Long0 | Auto 6
Why: ежемесячная финансовая отчётность держит деньги под контролем
Caps: monthly finance report, income expenses, savings, plan comparison
---

### 1262 — Еженедельный разбор почты
Джарвис, проводи еженедельный разбор почты: рассылки, неотвеченные, отписка от ненужного и архив.
Cat: SCHEDULED | Email
Diff: L1 | Tools: email | Web1 Code0 Files1 Vision0 Long0 | Auto 6
Why: регулярная разборка почты не даёт ей превратиться в хаос
Caps: email cleanup, weekly review, unsubscribe, archive
---

### 1263 — Планирование публикаций по расписанию
Джарвис, настрой расписание публикаций: даты, время и площадки — с очередью готового контента.
Cat: SCHEDULED | Publishing
Diff: L2 | Tools: web, planning, documents | Web1 Code0 Files1 Vision0 Long0 | Auto 6
Why: публикации по расписанию поддерживают аудиторию без спешки
Caps: publishing schedule, content queue, platforms, timing
---

### 1264 — Таймеры и отсчёты важных дат
Джарвис, настрой отсчёты важных дат: события, дедлайны и годовщины — с обратным отсчётом и подготовкой.
Cat: SCHEDULED | Countdowns
Diff: L1 | Tools: planning | Web0 Code0 Files1 Vision0 Long0 | Auto 6
Why: видимые отсчёты поддерживают готовность к событиям
Caps: countdowns, important dates, preparation, alerts
---

### 1265 — Расписание обучения
Джарвис, составь расписание обучения: дни, время, темы и повторения — с защитой от пропусков.
Cat: SCHEDULED | Learning
Diff: L1 | Tools: planning, documents | Web0 Code0 Files1 Vision0 Long0 | Auto 6
Why: расписание превращает обучение в регулярную привычку
Caps: study schedule, time slots, topics, consistency
---

### 1266 — Автоматические резервные копии по расписанию
Джарвис, настрой автоматическое резервное копирование: частота, источники, назначение и проверка восстановления.
Cat: SCHEDULED | Backups
Diff: L2 | Tools: files, terminal | Web0 Code1 Files1 Vision0 Long0 | Auto 6
Why: автоматические бэкапы защищают данные без участия человека
Caps: scheduled backups, sources, destinations, restore test
---

### 1267 — Мониторинг расписания и конфликтов
Джарвис, проверь моё расписание на конфликты: пересечения, перегрузку и свободные окна — предложи исправления.
Cat: SCHEDULED | Conflict Check
Diff: L1 | Tools: calendar, planning | Web0 Code0 Files1 Vision0 Long0 | Auto 6
Why: проверка расписания исключает двойные брони и перегруз
Caps: schedule conflicts, overlap detection, load balance, fixes
---

### 1268 — Автоматический сбор отчётности
Джарвис, автоматизируй сбор отчётности: забирай данные из систем, заполняй шаблоны и отправляй по расписанию.
Cat: SCHEDULED | Reporting Automation
Diff: L3 | Tools: data, documents, code | Web0 Code1 Files1 Vision0 Long0 | Auto 7
Why: автоматическая отчётность экономит часы ежемесячно
Caps: reporting automation, data collection, template fill, delivery
---

### 1269 — Расписание отдыха и восстановления
Джарвис, настрой расписание отдыха: перерывы, выходные и отпуска — с защитой от переработок.
Cat: SCHEDULED | Wellbeing
Diff: L1 | Tools: planning | Web0 Code0 Files1 Vision0 Long0 | Auto 6
Why: запланированный отдых — часть продуктивной системы
Caps: rest schedule, breaks, vacation planning, work life balance
---

### 1270 — Периодические обзоры и ревью
Джарвис, настрой периодические обзоры: еженедельные и ежемесячные ревью целей, задач и прогресса — с вопросами для разбора.
Cat: SCHEDULED | Reviews
Diff: L1 | Tools: planning, documents | Web0 Code0 Files1 Vision0 Long0 | Auto 6
Why: регулярные ревью корректируют курс до потери направления
Caps: periodic reviews, weekly review, monthly review, course correction
---

### 1271 — Самоанализ ошибок
Джарвис, проанализируй мои последние ошибки: найди паттерны, причины и правила, которые предотвратят повторение.
Cat: SELF-IMPROVEMENT | Error Analysis
Diff: L2 | Tools: conversation, documents | Web0 Code0 Files1 Vision0 Long0 | Auto 6
Why: анализ ошибок превращает провалы в источник роста
Caps: error analysis, patterns, root causes, prevention rules
---

### 1272 — Обратная связь о моих командах
Джарвис, оцени качество моих команд: что было неясно, как улучшить формулировки и чего не хватало для лучшего результата.
Cat: SELF-IMPROVEMENT | Feedback
Diff: L1 | Tools: conversation | Web0 Code0 Files1 Vision0 Long0 | Auto 6
Why: обратная связь улучшает качество взаимодействия с ассистентом
Caps: feedback, prompt quality, clarity, improvements
---

### 1273 — Ретроспектива недели
Джарвис, проведи ретроспективу недели: что прошло хорошо, что нет, инсайты и фокус на следующую неделю.
Cat: SELF-IMPROVEMENT | Retrospective
Diff: L1 | Tools: planning, documents | Web0 Code0 Files1 Vision0 Long0 | Auto 6
Why: ретроспектива превращает опыт недели в улучшение практик
Caps: weekly retrospective, wins, losses, insights, focus
---

### 1274 — Развитие слабых навыков
Джарвис, определи мои слабые навыки по данным и составь план развития: практики, сроки и критерии улучшения.
Cat: SELF-IMPROVEMENT | Skills
Diff: L2 | Tools: planning, documents | Web0 Code0 Files1 Vision0 Long0 | Auto 6
Why: целенаправленное развитие слабых сторон повышает общий уровень
Caps: skill development, weak points, practice plan, criteria
---

### 1275 — Персональный коучинг
Джарвис, проведи сессию коучинга: задавай вопросы, помогай найти решения и составь план действий.
Cat: SELF-IMPROVEMENT | Coaching
Diff: L2 | Tools: conversation | Web0 Code0 Files1 Vision0 Long0 | Auto 6
Why: коучинг помогает прийти к собственным решениям и взять ответственность
Caps: coaching, powerful questions, action plan, accountability
---

### 1276 — Постановка целей по SMART
Джарвис, переформулируй мои цели по SMART: конкретность, измеримость, достижимость, релевантность и сроки.
Cat: SELF-IMPROVEMENT | Goals
Diff: L1 | Tools: planning, documents | Web0 Code0 Files1 Vision0 Long0 | Auto 6
Why: SMART-цели выполнимы, в отличие от расплывчатых пожеланий
Caps: smart goals, measurable targets, deadlines, planning
---

### 1277 — Анализ продуктивности
Джарвис, проанализируй мою продуктивность: где тратится время, что отвлекает и какие методы дадут максимум результата.
Cat: SELF-IMPROVEMENT | Productivity
Diff: L2 | Tools: planning, data | Web0 Code0 Files1 Vision0 Long0 | Auto 6
Why: анализ времени показывает реальные точки роста продуктивности
Caps: productivity analysis, time audit, distractions, methods
---

### 1278 — Отслеживание личного роста
Джарвис, веди трекер личного роста: навыки, привычки, достижения и рефлексия — с периодическими отчётами.
Cat: SELF-IMPROVEMENT | Growth Tracking
Diff: L1 | Tools: planning, documents | Web0 Code0 Files1 Vision0 Long0 | Auto 6
Why: видимый прогресс мотивирует продолжать развитие
Caps: growth tracker, skills, habits, achievements, reports
---

### 1279 — Техники решения сложных проблем
Джарвис, проведи меня по техникам решения сложной проблемы: декомпозиция, аналогии, инверсия, мозговой штурм и оценка вариантов.
Cat: SELF-IMPROVEMENT | Problem Solving
Diff: L2 | Tools: conversation, documents | Web0 Code0 Files1 Vision0 Long0 | Auto 6
Why: системные техники решают проблемы, на которых «застревают»
Caps: problem solving, decomposition, inversion, brainstorming
---

### 1280 — Выработка привычек
Джарвис, помоги выработать привычку: дизайн триггера, маленький старт, награда и трекер серий.
Cat: SELF-IMPROVEMENT | Habits
Diff: L1 | Tools: planning, documents | Web0 Code0 Files1 Vision0 Long0 | Auto 6
Why: правильно спроектированные привычки закрепляются без силы воли
Caps: habit formation, triggers, small steps, streaks
---

### 1281 — Медитация и фокус: руководство
Джарвис, проведи сессию медитации или фокуса: инструкция, тайминг, техника дыхания и разбор ощущений.
Cat: SELF-IMPROVEMENT | Mindfulness
Diff: L1 | Tools: conversation | Web0 Code0 Files1 Vision0 Long0 | Auto 6
Why: регулярная практика фокуса улучшает внимание и стрессоустойчивость
Caps: meditation guide, focus, breathing, mindfulness
---

### 1282 — Развитие критического мышления
Джарвис, проведи тренировку критического мышления: разбери утверждение, найди допущения, логические ошибки и альтернативные объяснения.
Cat: SELF-IMPROVEMENT | Critical Thinking
Diff: L2 | Tools: conversation | Web0 Code0 Files1 Vision0 Long0 | Auto 6
Why: критическое мышление защищает от ошибок суждения
Caps: critical thinking, assumptions, logical fallacies, alternatives
---

### 1283 — Тайм-менеджмент: система
Джарвис, построй мою систему тайм-менеджмента: приоритеты, планирование, делегирование и борьба с прокрастинацией.
Cat: SELF-IMPROVEMENT | Time Management
Diff: L2 | Tools: planning, documents | Web0 Code0 Files1 Vision0 Long0 | Auto 6
Why: система тайм-менеджмента работает, когда вдохновения нет
Caps: time management, priorities, delegation, procrastination
---

### 1284 — Самооценка и рефлексия
Джарвис, проведи со мной сессию самооценки: вопросы о целях, ценностях, сильных сторонах и зонах роста.
Cat: SELF-IMPROVEMENT | Self Assessment
Diff: L1 | Tools: conversation | Web0 Code0 Files1 Vision0 Long0 | Auto 6
Why: честная самооценка — начало любого осознанного роста
Caps: self assessment, values, strengths, growth areas
---

### 1285 — Развитие эмоционального интеллекта
Джарвис, разбери ситуацию с эмоциями: назови чувства, их причины и здоровые способы реакции — по модели EQ.
Cat: SELF-IMPROVEMENT | Emotional Intelligence
Diff: L2 | Tools: conversation | Web0 Code0 Files1 Vision0 Long0 | Auto 6
Why: эмоциональный интеллект улучшает отношения и решения
Caps: emotional intelligence, emotion labeling, triggers, response
---

### 1286 — Настройка личности ассистента
Джарвис, настрой мой профиль ассистента: имя, стиль общения, уровень формальности и предпочтения в ответах.
Cat: PERSONA | Configuration
Diff: L1 | Tools: settings | Web0 Code0 Files1 Vision0 Long0 | Auto 6
Why: персона под пользователя делает взаимодействие комфортнее
Caps: assistant persona, communication style, preferences, settings
---

### 1287 — Роль эксперта в области
Джарвис, веди себя как эксперт в моей области: уровень детализации, терминология и стандарты профессии.
Cat: PERSONA | Expert Role
Diff: L2 | Tools: conversation | Web0 Code0 Files1 Vision0 Long0 | Auto 6
Why: экспертный тон даёт более точные и релевантные ответы
Caps: expert persona, domain terminology, professional standards
---

### 1288 — Стиль: краткие ответы
Джарвис, отвечай кратко: суть, максимум 3–5 предложений, без воды и вступлений.
Cat: PERSONA | Style
Diff: L1 | Tools: settings | Web0 Code0 Files1 Vision0 Long0 | Auto 6
Why: краткий стиль экономит время на простых вопросах
Caps: concise style, short answers, no filler
---

### 1289 — Стиль: подробные объяснения
Джарвис, отвечай подробно: контекст, аргументы, примеры, альтернативы и выводы — с разбивкой по разделам.
Cat: PERSONA | Style
Diff: L1 | Tools: settings | Web0 Code0 Files1 Vision0 Long0 | Auto 6
Why: подробный стиль нужен для обучения и сложных решений
Caps: detailed style, structure, examples, reasoning
---

### 1290 — Персона: наставник
Джарвис, говори со мной как наставник: задавай вопросы, поддерживай, давай развивающую обратную связь и не решай за меня.
Cat: PERSONA | Mentor
Diff: L2 | Tools: conversation | Web0 Code0 Files1 Vision0 Long0 | Auto 6
Why: наставнический тон развивает самостоятельность
Caps: mentor persona, guidance, questions, feedback
---

### 1291 — Персона: партнёр по мозговому штурму
Джарвис, работай со мной как партнёр по брейншторму: генерируй много вариантов, не критикуй, развивай мои идеи.
Cat: PERSONA | Brainstorming
Diff: L1 | Tools: conversation | Web0 Code0 Files1 Vision0 Long0 | Auto 6
Why: режим без критики разблокирует поток идей
Caps: brainstorming persona, idea generation, building on ideas
---

### 1292 — Адаптация стиля к аудитории
Джарвис, адаптируй свой стиль под аудиторию: возраст, уровень знаний и контекст — чтобы материал был понятен ей.
Cat: PERSONA | Adaptation
Diff: L2 | Tools: conversation | Web0 Code0 Files1 Vision0 Long0 | Auto 6
Why: стиль под аудиторию повышает понимание и вовлечённость
Caps: style adaptation, audience, level, context
---

### 1293 — Имитация стиля автора
Джарвис, напиши текст в стиле автора: изучи характерные обороты и манеру, сохрани суть, воспроизведи тон.
Cat: PERSONA | Style Imitation
Diff: L2 | Tools: documents | Web0 Code0 Files1 Vision0 Long0 | Auto 6
Why: имитация стиля нужна для продолжения текстов и контента
Caps: style imitation, author voice, tone, writing style
---

### 1294 — Юмористический тон
Джарвис, отвечай с юмором: лёгкий тон, уместные шутки, но без потери смысла и точности.
Cat: PERSONA | Humor
Diff: L1 | Tools: settings | Web0 Code0 Files1 Vision0 Long0 | Auto 6
Why: юмор делает взаимодействие приятнее при сохранении пользы
Caps: humor, light tone, wit, engagement
---

### 1295 — Профессиональный деловой тон
Джарвис, соблюдай деловой тон: формальные формулировки, уважение, точность и структура официальных документов.
Cat: PERSONA | Business Tone
Diff: L1 | Tools: settings | Web0 Code0 Files1 Vision0 Long0 | Auto 6
Why: деловой тон уместен в переписке с клиентами и партнёрами
Caps: business tone, formal style, precision, structure
---

### 1296 — Персона: строгий критик
Джарвис, будь строгим критиком: указывай на слабости, задавай неудобные вопросы и требуй обоснований.
Cat: PERSONA | Critic
Diff: L1 | Tools: conversation | Web0 Code0 Files1 Vision0 Long0 | Auto 6
Why: строгая критика закаляет идеи перед защитой
Caps: critic persona, tough questions, weak spot hunting, standards
---

### 1297 — Персона: популяризатор
Джарвис, объясняй как популяризатор: просто, ярко, с аналогиями и историями — без упрощения сути.
Cat: PERSONA | Popularizer
Diff: L1 | Tools: conversation | Web0 Code0 Files1 Vision0 Long0 | Auto 6
Why: популярный стиль делает сложное доступным для всех
Caps: popularizer, simplicity, analogies, stories
---

### 1298 — Сохранение персональных предпочтений
Джарвис, запомни мои предпочтения: формат ответов, язык, часовой пояс и привычки — и применяй их по умолчанию.
Cat: PERSONA | Preferences
Diff: L1 | Tools: settings | Web0 Code0 Files1 Vision0 Long0 | Auto 6
Why: запомненные предпочтения убирают повторение настроек
Caps: preferences, defaults, personalization, memory
---

### 1299 — Мультиперсона: переключение ролей
Джарвис, переключайся между ролями по контексту: эксперт, наставник, критик, популяризатор — с явным обозначением смены.
Cat: PERSONA | Switching
Diff: L2 | Tools: conversation | Web0 Code0 Files1 Vision0 Long0 | Auto 6
Why: переключение ролей даёт многогранный взгляд на задачу
Caps: role switching, multi persona, context aware, flexibility
---

### 1300 — Эмпатичный стиль общения
Джарвис, общайся эмпатично: признавай чувства, поддерживай и предлагай помощь без назидания.
Cat: PERSONA | Empathy
Diff: L1 | Tools: conversation | Web0 Code0 Files1 Vision0 Long0 | Auto 6
Why: эмпатия улучшает поддержку в трудных ситуациях
Caps: empathy, support, active listening, kindness
---
### 1301 — Полная автоматизация личного кабинета
Джарвис, автоматизируй мой личный кабинет: собери все данные, упорядочь документы, настрой уведомления и создай ежемесячную сводку — в одну миссию.
Cat: MEGA MISSIONS | Personal Automation
Diff: L4 | Tools: web, files, email, planning | Web1 Code1 Files1 Vision0 Long1 | Auto 8
Why: одна миссия заменяет десятки рутинных действий
Caps: personal automation, dashboard, documents, monthly digest
---

### 1302 — Переезд компании в новый офис
Джарвис, спланируй переезд компании: бюджет, подрядчики, график, перечень оборудования, документы и чек-лист первого дня.
Cat: MEGA MISSIONS | Relocation
Diff: L4 | Tools: research, documents, spreadsheets, planning | Web1 Code0 Files1 Vision0 Long1 | Auto 8
Why: переезд без плана срывает работу компании на недели
Caps: office relocation, budget, contractors, checklist
---

### 1303 — Запуск интернет-магазина под ключ
Джарвис, запусти интернет-магазин под ключ: ниша, платформа, ассортимент, оплата, доставка, маркетинг и первые продажи — полный план действий.
Cat: MEGA MISSIONS | E-commerce Launch
Diff: L4 | Tools: research, documents, spreadsheets, web | Web1 Code1 Files1 Vision0 Long1 | Auto 8
Why: комплексный запуск магазина требует согласованной системы шагов
Caps: e-commerce launch, platform, catalog, payments, marketing
---

### 1304 — Цифровой детокс и перезагрузка
Джарвис, проведи цифровой детокс: аудит экранного времени, удаление отвлекающих приложений, расписание офлайн-активностей и план восстановления фокуса.
Cat: MEGA MISSIONS | Digital Detox
Diff: L2 | Tools: planning, documents | Web0 Code0 Files1 Vision0 Long0 | Auto 7
Why: осознанный детокс восстанавливает внимание и сон
Caps: digital detox, screen time, focus, offline plan
---

### 1305 — Подготовка к эмиграции
Джарвис, составь план эмиграции: страна, виза, документы, финансы, жильё, работа, язык и чек-лист переезда — поэтапно.
Cat: MEGA MISSIONS | Relocation Abroad
Diff: L4 | Tools: research, documents, spreadsheets | Web1 Code0 Files1 Vision0 Long1 | Auto 8
Why: эмиграция — один из самых сложных жизненных проектов
Caps: emigration plan, visa, documents, finances, relocation checklist
---

### 1306 — Организация масштабного мероприятия
Джарвис, организуй мероприятие: концепция, площадка, бюджет, программа, подрядчики, маркетинг и логистика — с планом по неделям.
Cat: MEGA MISSIONS | Event Management
Diff: L4 | Tools: research, documents, spreadsheets, planning | Web1 Code0 Files1 Vision0 Long1 | Auto 8
Why: мероприятие держится на сотнях согласованных деталей
Caps: event planning, venue, budget, program, logistics
---

### 1307 — Восстановление после инцидента
Джарвис, проведи восстановление после инцидента: оценка ущерба, экстренные меры, восстановление данных, разбор причин и план защиты.
Cat: MEGA MISSIONS | Incident Recovery
Diff: L4 | Tools: files, security, documents | Web0 Code1 Files1 Vision0 Long0 | Auto 8
Why: грамотная реакция на инцидент минимизирует потери
Caps: incident recovery, damage assessment, data restore, prevention
---

### 1308 — Полная финансовая перестройка
Джарвис, проведи полную финансовую перестройку: аудит, бюджет, долги, накопления, инвестиции, страховки и цели — с планом на год.
Cat: MEGA MISSIONS | Finance Overhaul
Diff: L3 | Tools: spreadsheets, research, documents | Web1 Code0 Files1 Vision0 Long1 | Auto 8
Why: финансовая перестройка устраняет все слабые места разом
Caps: finance overhaul, audit, budget, debt, investing, plan
---

### 1309 — Создание компании с нуля
Джарвис, создай компанию с нуля: идея, регистрация, продукт, команда, финансы, маркетинг и первые клиенты — пошаговая миссия.
Cat: MEGA MISSIONS | Company Setup
Diff: L4 | Tools: research, documents, spreadsheets, planning | Web1 Code0 Files1 Vision0 Long1 | Auto 8
Why: создание компании объединяет десятки направлений в один проект
Caps: company setup, registration, product, team, launch
---

### 1310 — Организация свадьбы или юбилея
Джарвис, организуй торжество: бюджет, площадка, подрядчики, сценарий, рассадка, меню и план подготовки по неделям.
Cat: MEGA MISSIONS | Celebration
Diff: L3 | Tools: research, documents, spreadsheets | Web1 Code0 Files1 Vision0 Long1 | Auto 8
Why: торжество без плана превращается в стресс в день события
Caps: wedding planning, budget, vendors, scenario, timeline
---

### 1311 — Комплексный аудит бизнеса
Джарвис, проведи комплексный аудит бизнеса: финансы, продажи, маркетинг, процессы, команда и технологии — с приоритизированным планом улучшений.
Cat: MEGA MISSIONS | Business Audit
Diff: L4 | Tools: data, documents, spreadsheets | Web0 Code0 Files1 Vision0 Long1 | Auto 8
Why: комплексный аудит показывает полную картину здоровья бизнеса
Caps: business audit, finance, sales, process, recommendations
---

### 1312 — Переезд в новую квартиру
Джарвис, организуй переезд в квартиру: поиск, документы, перевозчики, распаковка, подключение услуг и чек-лист первого месяца.
Cat: MEGA MISSIONS | Home Move
Diff: L3 | Tools: research, documents, planning | Web1 Code0 Files1 Vision0 Long0 | Auto 8
Why: системный переезд спасает нервы и вещи
Caps: home move, movers, utilities, unpacking, checklist
---

### 1313 — Запуск YouTube-канала
Джарвис, запусти YouTube-канал: ниша, стратегия, оборудование, первые видео, оформление, SEO и план роста на полгода.
Cat: MEGA MISSIONS | YouTube Launch
Diff: L3 | Tools: research, documents, planning | Web1 Code0 Files1 Vision0 Long1 | Auto 8
Why: канал растёт только при системной подготовке и регулярности
Caps: youtube channel, niche, equipment, video plan, growth
---

### 1314 — Цифровая трансформация отдела
Джарвис, проведи цифровую трансформацию отдела: аудит процессов, выбор инструментов, автоматизация, обучение сотрудников и план внедрения.
Cat: MEGA MISSIONS | Digital Transformation
Diff: L4 | Tools: research, documents, planning, data | Web1 Code1 Files1 Vision0 Long1 | Auto 8
Why: цифровизация без плана внедрения остаётся на бумаге
Caps: digital transformation, process audit, tools, automation, training
---

### 1315 — Подготовка к большим соревнованиям
Джарвис, подготовь меня к соревнованиям: цель, план тренировок, питание, режим, снаряжение и психологическая подготовка.
Cat: MEGA MISSIONS | Competition Prep
Diff: L3 | Tools: research, documents, planning | Web1 Code0 Files1 Vision0 Long0 | Auto 8
Why: системная подготовка определяет результат на старте
Caps: competition prep, training plan, nutrition, gear, mindset
---

### 1316 — Полное исследование рынка
Джарвис, проведи полное исследование рынка: объём, тренды, сегменты, конкуренты, цены, барьеры и прогноз — как аналитический отчёт.
Cat: MEGA MISSIONS | Market Research
Diff: L4 | Tools: research, data, documents | Web1 Code0 Files1 Vision0 Long1 | Auto 8
Why: полное исследование снижает риск ошибок стратегии
Caps: market research, trends, segments, competitors, forecast
---

### 1317 — Создание образовательного курса
Джарвис, создай образовательный курс: программа, материалы, задания, видео, платформа, запуск и продажи — полный цикл.
Cat: MEGA MISSIONS | Course Creation
Diff: L4 | Tools: documents, video, research, planning | Web1 Code0 Files1 Vision0 Long1 | Auto 8
Why: курс — сложный продукт, требующий системного производства
Caps: course creation, curriculum, materials, platform, launch
---

### 1318 — Перестройка личной жизни и привычек
Джарвис, помоги перестроить образ жизни: режим, питание, спорт, сон, отношения и работа — единая программа на 90 дней.
Cat: MEGA MISSIONS | Life Overhaul
Diff: L3 | Tools: planning, documents | Web0 Code0 Files1 Vision0 Long0 | Auto 8
Why: комплексная перестройка эффективнее точечных изменений
Caps: life overhaul, routine, habits, 90 day plan, health
---

### 1319 — Разработка продукта от идеи до релиза
Джарвис, проведи продукт от идеи до релиза: исследование, прототип, разработка, тесты, запуск и метрики — полная дорожная карта.
Cat: MEGA MISSIONS | Product Development
Diff: L4 | Tools: research, code, documents, planning | Web0 Code1 Files1 Vision0 Long1 | Auto 8
Why: сквозной процесс исключает потери на стыках этапов
Caps: product development, idea validation, prototype, launch, metrics
---

### 1320 — Запуск подкаста
Джарвис, запусти подкаст: концепция, оборудование, запись, монтаж, дистрибуция и продвижение — с планом первых выпусков.
Cat: MEGA MISSIONS | Podcast Launch
Diff: L3 | Tools: research, audio, documents, planning | Web1 Code0 Files1 Vision0 Long1 | Auto 8
Why: подкаст требует согласованной системы производства контента
Caps: podcast launch, concept, equipment, editing, distribution
---

### 1321 — Комплексная защита данных семьи
Джарвис, организуй защиту данных семьи: пароли, 2FA, бэкапы, приватность и обучение домочадцев — полная программа.
Cat: MEGA MISSIONS | Family Security
Diff: L3 | Tools: security, documents, files | Web0 Code1 Files1 Vision0 Long1 | Auto 8
Why: безопасность семьи защищает от кражи, мошенничества и потери данных
Caps: family security, passwords, backups, privacy, training
---

### 1322 — Открытие кафе или ресторана
Джарвис, открой кафе: концепция, локация, меню, оборудование, персонал, цены, разрешения и запуск — пошаговый план.
Cat: MEGA MISSIONS | F&B Launch
Diff: L4 | Tools: research, documents, spreadsheets | Web1 Code0 Files1 Vision0 Long1 | Auto 8
Why: заведения общепита чаще всего закрываются из-за неподготовленности
Caps: cafe launch, concept, menu, staff, permits
---

### 1323 — Годовая стратегия личного развития
Джарвис, построй годовую стратегию развития: цели по областям, план по кварталам, метрики, ревизии и ресурсы.
Cat: MEGA MISSIONS | Personal Strategy
Diff: L3 | Tools: planning, documents | Web0 Code0 Files1 Vision0 Long1 | Auto 8
Why: годовая стратегия превращает желания в управляемый проект
Caps: personal strategy, annual goals, quarterly plan, metrics
---

### 1324 — Автоматизация всей компании
Джарвис, автоматизируй компанию: карта процессов, кандидаты на автоматизацию, инструменты, интеграции, план внедрения и экономический эффект.
Cat: MEGA MISSIONS | Company Automation
Diff: L4 | Tools: research, documents, code, planning | Web1 Code1 Files1 Vision0 Long1 | Auto 8
Why: сквозная автоматизация освобождает команду от рутины
Caps: company automation, process map, tools, integration, roi
---

### 1325 — Подготовка к важному экзамену за 3 месяца
Джарвис, подготовь меня к экзамену за 3 месяца: план по неделям, материалы, практика, пробники, анализ ошибок и финальная стратегия.
Cat: MEGA MISSIONS | Exam Sprint
Diff: L3 | Tools: planning, documents, research | Web1 Code0 Files1 Vision0 Long0 | Auto 8
Why: длинная подготовка без системы проваливается в последний месяц
Caps: exam sprint, weekly plan, practice, mock tests, strategy
---

### 1326 — Ребрендинг компании
Джарвис, проведи ребрендинг: исследование, новая айдентика, имя, логотип, материалы, запуск и коммуникация изменений.
Cat: MEGA MISSIONS | Rebranding
Diff: L4 | Tools: research, documents, design, planning | Web1 Code0 Files1 Vision0 Long1 | Auto 8
Why: ребрендинг меняет восприятие бренда на рынке
Caps: rebranding, identity, logo, rollout, communication
---

### 1327 — Кругосветное путешествие: планирование
Джарвис, спланируй кругосветное путешествие: маршрут, визы, бюджет, страховки, жильё, транспорт и план по месяцам.
Cat: MEGA MISSIONS | World Travel
Diff: L3 | Tools: research, documents, spreadsheets | Web1 Code0 Files1 Vision0 Long1 | Auto 8
Why: глобальное путешествие требует проработки сотен деталей
Caps: world travel, itinerary, visas, budget, insurance
---

### 1328 — Выход на зарубежный рынок
Джарвис, подготовь выход на зарубежный рынок: выбор страны, юриспруденция, локализация, каналы, цены и план запуска.
Cat: MEGA MISSIONS | Global Expansion
Diff: L4 | Tools: research, documents, spreadsheets | Web1 Code0 Files1 Vision0 Long1 | Auto 8
Why: зарубежный рынок отличается правилами, культурой и спросом
Caps: global expansion, market selection, localization, channels, launch
---

### 1329 — Цифровой архив семьи
Джарвис, создай цифровой архив семьи: сканирование фото и документов, каталогизация, хранение, резервные копии и доступы.
Cat: MEGA MISSIONS | Family Archive
Diff: L3 | Tools: files, vision, documents | Web0 Code0 Files1 Vision1 Long1 | Auto 8
Why: цифровой архив сохраняет семейную память на десятилетия
Caps: family archive, digitization, catalog, backup, access
---

### 1330 — Построение бренда эксперта
Джарвис, построй личный бренд эксперта: позиционирование, контент, площадки, публикации, выступления и план на год.
Cat: MEGA MISSIONS | Personal Brand
Diff: L3 | Tools: research, documents, planning | Web1 Code0 Files1 Vision0 Long1 | Auto 8
Why: бренд эксперта открывает возможности и повышает доход
Caps: personal brand, positioning, content, speaking, plan
---

### 1331 — Комплексное восстановление репутации
Джарвис, разработай план восстановления репутации: оценка ущерба, работа с отзывами, PR, изменения в сервисе и коммуникация.
Cat: MEGA MISSIONS | Reputation Recovery
Diff: L4 | Tools: research, documents, web | Web1 Code0 Files1 Vision0 Long1 | Auto 8
Why: репутация восстанавливается только системной работой
Caps: reputation recovery, reviews, pr, service fix, communication
---

### 1332 — Создание мобильного приложения
Джарвис, создай мобильное приложение: идея, исследование, дизайн, разработка, тесты, публикация и продвижение — полный цикл.
Cat: MEGA MISSIONS | App Development
Diff: L4 | Tools: research, code, documents, planning | Web0 Code1 Files1 Vision0 Long1 | Auto 8
Why: приложение — продукт, где все этапы влияют на успех
Caps: app development, idea, design, development, launch
---

### 1333 — Переезд в другой город
Джарвис, спланируй переезд в другой город: работа, жильё, документы, транспорт, соцсвязи и адаптация — по этапам.
Cat: MEGA MISSIONS | City Relocation
Diff: L3 | Tools: research, documents, planning | Web1 Code0 Files1 Vision0 Long0 | Auto 8
Why: переезд в город включает параллельные проекты
Caps: city move, job, housing, documents, adaptation
---

### 1334 — Запуск благотворительного проекта
Джарвис, запусти благотворительный проект: проблема, миссия, команда, финансирование, партнёры, программа и измерение эффекта.
Cat: MEGA MISSIONS | Nonprofit
Diff: L4 | Tools: research, documents, planning | Web1 Code0 Files1 Vision0 Long1 | Auto 8
Why: социальные проекты требуют прозрачности и измеримости
Caps: nonprofit launch, mission, funding, partners, impact
---

### 1335 — Подготовка презентации для инвесторов
Джарвис, подготовь инвесторский пакет: питч-дек, финмодель, исследование рынка, юридические документы и репетиция выступления.
Cat: MEGA MISSIONS | Investor Package
Diff: L4 | Tools: documents, spreadsheets, research | Web1 Code0 Files1 Vision0 Long1 | Auto 8
Why: инвесторы оценивают пакет целиком, а не одну презентацию
Caps: investor package, pitch deck, financial model, rehearsal
---

### 1336 — Годовая перезагрузка компании
Джарвис, проведи годовую перезагрузку компании: стратегия, бюджет, команда, продукты, процессы и цели на год — план сессий и решений.
Cat: MEGA MISSIONS | Annual Reset
Diff: L4 | Tools: documents, spreadsheets, planning | Web0 Code0 Files1 Vision0 Long1 | Auto 8
Why: ежегодная перезагрузка синхронизирует компанию
Caps: annual reset, strategy, budget, team, goals
---

### 1337 — Создание инфопродукта
Джарвис, создай инфопродукт: тема, структура, материалы, упаковка, платформа, цены и запуск с воронкой продаж.
Cat: MEGA MISSIONS | Info Product
Diff: L3 | Tools: documents, research, planning | Web1 Code0 Files1 Vision0 Long1 | Auto 8
Why: инфопродукт масштабирует экспертизу без затрат времени на клиента
Caps: info product, structure, packaging, launch, funnel
---

### 1338 — Полная настройка рабочего пространства
Джарвис, настрой рабочее пространство: оборудование, эргономика, софт, автоматизация, файлы и режим — идеальная среда для работы.
Cat: MEGA MISSIONS | Workspace Setup
Diff: L2 | Tools: research, files, documents | Web1 Code1 Files1 Vision0 Long0 | Auto 7
Why: правильная среда повышает продуктивность и здоровье
Caps: workspace, ergonomics, software, automation, setup
---

### 1339 — Подготовка к масштабным переговорам
Джарвис, подготовь меня к важным переговорам: анализ сторон, цели, стратегия, аргументы, уступки, сценарии и репетиция.
Cat: MEGA MISSIONS | Negotiation Prep
Diff: L3 | Tools: research, documents | Web1 Code0 Files1 Vision0 Long0 | Auto 8
Why: исход переговоров решается до их начала
Caps: negotiation prep, counterpart analysis, strategy, scenarios
---

### 1340 — Комплексная оптимизация расходов
Джарвис, проведи комплексную оптимизацию расходов: анализ всех трат, переговоры с поставщиками, отмена лишнего и план экономии на год.
Cat: MEGA MISSIONS | Cost Optimization
Diff: L3 | Tools: spreadsheets, research, documents | Web1 Code0 Files1 Vision0 Long0 | Auto 8
Why: системная экономия сохраняет прибыль без сокращения качества
Caps: cost optimization, expense audit, supplier negotiation, savings plan
---

### 1341 — Создание портфолио под ключ
Джарвис, создай портфолио под ключ: отбор работ, кейсы, оформление, сайт, тексты и презентация для клиентов или работодателей.
Cat: MEGA MISSIONS | Portfolio
Diff: L3 | Tools: documents, design, web | Web1 Code0 Files1 Vision0 Long1 | Auto 8
Why: сильное портфолио удваивает отклик клиентов и работодателей
Caps: portfolio, case studies, design, website, presentation
---

### 1342 — Запуск франшизы
Джарвис, подготовь франшизу: упаковка бизнес-модели, документы, обучение, маркетинг для франчайзи и план продажи.
Cat: MEGA MISSIONS | Franchise
Diff: L4 | Tools: research, documents, spreadsheets | Web1 Code0 Files1 Vision0 Long1 | Auto 8
Why: франшиза масштабирует бизнес без собственного капитала
Caps: franchise, business model, documents, training, sales
---

### 1343 — Восстановление утраченных данных
Джарвис, организуй восстановление утраченных данных: оценка ситуации, инструменты, порядок восстановления и профилактика потерь.
Cat: MEGA MISSIONS | Data Recovery
Diff: L4 | Tools: files, terminal, research | Web0 Code1 Files1 Vision0 Long0 | Auto 8
Why: правильный порядок действий решает судьбу данных
Caps: data recovery, assessment, tools, restore, prevention
---

### 1344 — Полный редизайн сайта
Джарвис, проведи редизайн сайта: аудит, цели, структура, дизайн, контент, разработка, тесты и запуск с аналитикой.
Cat: MEGA MISSIONS | Website Redesign
Diff: L4 | Tools: web, code, documents, research | Web1 Code1 Files1 Vision0 Long1 | Auto 8
Why: редизайн без стратегии снижает конверсию вместо роста
Caps: website redesign, audit, structure, design, launch
---

### 1345 — Организация удалённой команды
Джарвис, организуй удалённую команду: процессы, инструменты, синхронизация, культура, найм и метрики эффективности.
Cat: MEGA MISSIONS | Remote Team
Diff: L3 | Tools: research, documents, planning | Web1 Code0 Files1 Vision0 Long1 | Auto 8
Why: удалёнка работает только на выстроенных процессах
Caps: remote team, processes, tools, culture, metrics
---

### 1346 — Запуск крипто-проекта
Джарвис, спланируй крипто-проект: идея, токеномика, юридические аспекты, разработка, безопасность и запуск — с оценкой рисков.
Cat: MEGA MISSIONS | Crypto Project
Diff: L4 | Tools: research, code, documents | Web1 Code1 Files1 Vision0 Long1 | Auto 8
Why: крипто-проекты требуют особого внимания к юридическим рискам
Caps: crypto project, tokenomics, legal, development, launch
---

### 1347 — Полный переход на здоровый образ жизни
Джарвис, организуй переход на здоровый образ жизни: анализы, питание, спорт, сон, стресс и привычки — программа на год с замерами.
Cat: MEGA MISSIONS | Healthy Lifestyle
Diff: L3 | Tools: research, documents, planning | Web1 Code0 Files1 Vision0 Long1 | Auto 8
Why: здоровье требует системных изменений, а не диет
Caps: healthy lifestyle, nutrition, sport, sleep, program
---

### 1348 — Подготовка выступления на конференции
Джарвис, подготовь выступление на конференции: тема, структура, слайды, сценарий, репетиции, работа с залом и техника.
Cat: MEGA MISSIONS | Conference Talk
Diff: L3 | Tools: documents, presentations | Web0 Code0 Files1 Vision0 Long1 | Auto 8
Why: выступление строится из подготовки и репетиций
Caps: conference talk, structure, slides, rehearsal, stagecraft
---

### 1349 — Масштабный ремонт квартиры
Джарвис, организуй ремонт квартиры: дизайн-проект, смета, подрядчики, график, материалы и контроль качества — по этапам.
Cat: MEGA MISSIONS | Renovation
Diff: L4 | Tools: research, documents, spreadsheets | Web1 Code0 Files1 Vision0 Long1 | Auto 8
Why: ремонт без управления превращается в бесконечный проект
Caps: renovation, design, estimate, contractors, schedule
---

### 1350 — Запуск SaaS-продукта
Джарвис, запусти SaaS-продукт: идея, исследование, MVP, разработка, цены, маркетинг, поддержка и метрики роста.
Cat: MEGA MISSIONS | SaaS Launch
Diff: L4 | Tools: research, code, documents, planning | Web0 Code1 Files1 Vision0 Long1 | Auto 8
Why: SaaS требует единства продукта, цены и роста
Caps: saas launch, mvp, development, pricing, growth
---
### 1351 — Финтех-дашборд для малого бизнеса
Джарвис, создай финтех-дашборд для малого бизнеса: финансы, продажи, канал привлечения и операционные метрики в едином отчёте.
Cat: CROSS-DOMAIN | Finance + Business
Diff: L3 | Tools: data, spreadsheets, charts | Web0 Code0 Files1 Vision0 Long1 | Auto 8
Why: пересечение финансов и операций даёт управляемую картину
Caps: fintech dashboard, business metrics, finance, operations
---

### 1352 — Маркетинговый анализ через данные
Джарвис, проанализируй маркетинг через данные: свяжи рекламные расходы, трафик, конверсии и продажи в единую модель.
Cat: CROSS-DOMAIN | Marketing + Data
Diff: L3 | Tools: data, spreadsheets | Web0 Code0 Files1 Vision0 Long0 | Auto 8
Why: сквозная аналитика объясняет, что реально приносит выручку
Caps: marketing analytics, data model, attribution, revenue
---

### 1353 — Техническая документация для нетехнической команды
Джарвис, объясни техническое решение нетехнической команде: суть, выгоды, риски и план внедрения — без жаргона.
Cat: CROSS-DOMAIN | Tech + Communication
Diff: L2 | Tools: documents | Web0 Code0 Files1 Vision0 Long0 | Auto 7
Why: взаимопонимание техников и бизнеса решает судьбу проектов
Caps: tech communication, plain language, stakeholder alignment
---

### 1354 — Финансовая модель стартапа
Джарвис, построй финансовую модель стартапа: юнит-экономика, сценарии роста, потребность в капитале и выход на прибыль.
Cat: CROSS-DOMAIN | Finance + Startup
Diff: L4 | Tools: spreadsheets, math | Web0 Code0 Files1 Vision0 Long1 | Auto 8
Why: финмодель — язык разговора стартапа с инвесторами
Caps: startup financial model, unit economics, scenarios, capital
---

### 1355 — Обучение команды через геймификацию
Джарвис, разработай обучающую программу с геймификацией: уровни, баллы, квесты и соревнования для удержания мотивации.
Cat: CROSS-DOMAIN | Learning + Games
Diff: L3 | Tools: documents, planning | Web0 Code0 Files1 Vision0 Long0 | Auto 8
Why: игровые механики повышают вовлечённость в обучении
Caps: gamified learning, levels, points, engagement
---

### 1356 — Визуализация бизнес-данных для презентации
Джарвис, преврати бизнес-данные в презентацию: отбери главные метрики, построй графики и собери убедительную историю.
Cat: CROSS-DOMAIN | Data + Presentations
Diff: L3 | Tools: data, charts, documents | Web0 Code0 Files1 Vision0 Long0 | Auto 8
Why: данные в презентации убеждают сильнее слов
Caps: data storytelling, business charts, presentation, narrative
---

### 1357 — Автоматизация отчётности с защитой данных
Джарвис, автоматизируй отчётность с защитой данных: шифрование, доступы, журналирование и соответствие требованиям.
Cat: CROSS-DOMAIN | Automation + Security
Diff: L4 | Tools: code, security, data | Web0 Code1 Files1 Vision0 Long0 | Auto 8
Why: автоматизация без защиты создаёт новые риски утечек
Caps: secure automation, encryption, access control, compliance
---

### 1358 — Контент-план по аналитике аудитории
Джарвис, составь контент-план на основе аналитики: данные аудитории, популярные темы, лучшие форматы и время публикаций.
Cat: CROSS-DOMAIN | Marketing + Data
Diff: L2 | Tools: data, documents | Web0 Code0 Files1 Vision0 Long0 | Auto 7
Why: контент по данным работает лучше контента по интуиции
Caps: data driven content, audience analytics, formats, timing
---

### 1359 — Инженерный проект с экономическим обоснованием
Джарвис, выполни инженерный проект с экономикой: техническое решение, расчёт затрат, окупаемость и сравнение вариантов.
Cat: CROSS-DOMAIN | Engineering + Finance
Diff: L4 | Tools: math, spreadsheets, research | Web1 Code0 Files1 Vision0 Long1 | Auto 8
Why: инженеры выигрывают, когда считают деньги проектов
Caps: engineering economics, cost benefit, roi, options
---

### 1360 — Научное объяснение для маркетинга
Джарвис, преврати научные данные в маркетинговые аргументы: корректно, без искажений и с доказательной базой.
Cat: CROSS-DOMAIN | Science + Marketing
Diff: L3 | Tools: research, documents | Web1 Code0 Files1 Vision0 Long0 | Auto 8
Why: наука в маркетинге работает, если не искажать данные
Caps: science marketing, evidence based claims, accuracy, communication
---

### 1361 — Аудио-версия книги или статьи
Джарвис, преврати текст в аудио-формат: разбей на главы, подготовь озвучку и оформление — как аудиокнигу.
Cat: CROSS-DOMAIN | Text + Audio
Diff: L3 | Tools: documents, audio, speech | Web0 Code0 Files1 Vision0 Long0 | Auto 8
Why: аудио-формат делает контент доступным в дороге
Caps: audiobook, text to speech, chapters, audio production
---

### 1362 — Видео-конспект лекции
Джарвис, преврати лекцию в видео-конспект: ключевые тезисы, слайды, таймкоды и резюме для повторения.
Cat: CROSS-DOMAIN | Education + Video
Diff: L3 | Tools: video, documents | Web0 Code0 Files1 Vision0 Long0 | Auto 8
Why: видео-конспекты ускоряют повторение сложного материала
Caps: video notes, lecture summary, timestamps, slides
---

### 1363 — Презентация продукта с прототипом
Джарвис, подготовь презентацию продукта с прототипом: сценарий, слайды, демонстрация и план запуска — как единый пакет.
Cat: CROSS-DOMAIN | Product + Presentations
Diff: L3 | Tools: documents, code, presentations | Web0 Code1 Files1 Vision0 Long1 | Auto 8
Why: живая демонстрация убеждает сильнее слайдов
Caps: product presentation, prototype demo, launch plan, pitch
---

### 1364 — Управление проектом с аналитикой рисков
Джарвис, управляй проектом с аналитикой рисков: план, мониторинг, количественная оценка рисков и корректирующие действия.
Cat: CROSS-DOMAIN | PM + Analytics
Diff: L4 | Tools: planning, data, documents | Web0 Code0 Files1 Vision0 Long1 | Auto 8
Why: проект без аналитики рисков реагирует на проблемы постфактум
Caps: project risk analytics, quantitative risk, monitoring, mitigation
---

### 1365 — Локализация продукта с маркетингом
Джарвис, локализуй продукт для нового рынка: перевод, культурная адаптация, маркетинг и запуск — полный пакет.
Cat: CROSS-DOMAIN | Translation + Marketing
Diff: L4 | Tools: research, documents, web | Web1 Code0 Files1 Vision0 Long1 | Auto 8
Why: локализация без маркетинга остаётся незамеченной
Caps: localization, cultural adaptation, marketing, launch
---

### 1366 — Дизайн-система с документацией
Джарвис, создай дизайн-систему: компоненты, правила, токены и документация — для согласованной разработки интерфейсов.
Cat: CROSS-DOMAIN | Design + Documentation
Diff: L4 | Tools: documents, design, code | Web0 Code1 Files1 Vision0 Long1 | Auto 8
Why: дизайн-система ускоряет разработку и держит качество
Caps: design system, components, tokens, documentation
---

### 1367 — Экономика и экология: оценка проекта
Джарвис, оцени проект по экономике и экологии: затраты, выгоды, воздействие на окружающую среду и устойчивость.
Cat: CROSS-DOMAIN | Finance + Environment
Diff: L3 | Tools: research, spreadsheets | Web1 Code0 Files1 Vision0 Long0 | Auto 8
Why: устойчивые проекты выигрывают и экономически
Caps: sustainability, environmental impact, cost benefit, esg
---

### 1368 — Анализ клиентов с психологией
Джарвис, проанализируй клиентов с учётом психологии: мотивация, возражения, поведенческие паттерны и влияния на покупки.
Cat: CROSS-DOMAIN | Psychology + Sales
Diff: L3 | Tools: research, data, documents | Web1 Code0 Files1 Vision0 Long0 | Auto 8
Why: психология объясняет, почему клиенты покупают и уходят
Caps: consumer psychology, motivation, behavior, sales
---

### 1369 — Автоматизация учёта с бухгалтерией
Джарвис, автоматизируй бухгалтерский учёт: интеграции, документооборот, отчёты и контроль ошибок — с планом внедрения.
Cat: CROSS-DOMAIN | Automation + Accounting
Diff: L4 | Tools: code, data, documents | Web0 Code1 Files1 Vision0 Long1 | Auto 8
Why: автоматизация учёта снижает ошибки и экономит время бухгалтера
Caps: accounting automation, integrations, document flow, controls
---

### 1370 — Обучающий курс с видеопроизводством
Джарвис, создай обучающий курс с видео: сценарии уроков, съёмка, монтаж, материалы и платформа — полный производственный цикл.
Cat: CROSS-DOMAIN | Education + Video
Diff: L4 | Tools: video, documents, planning | Web0 Code0 Files1 Vision0 Long1 | Auto 8
Why: видеоуроки требуют синхронной работы сценария и производства
Caps: video course, scripts, production, editing, platform
---

### 1371 — Маркетинг с научным тестированием
Джарвис, построй маркетинговые эксперименты: гипотезы, A/B-тесты, статистика и выводы — как научное исследование.
Cat: CROSS-DOMAIN | Marketing + Science
Diff: L4 | Tools: data, math, research | Web1 Code1 Files1 Vision0 Long0 | Auto 8
Why: эксперименты вместо мнений повышают отдачу маркетинга
Caps: marketing experiments, hypothesis, ab test, statistics
---

### 1372 — Безопасность и производительность системы
Джарвис, оптимизируй систему по двум осям: безопасность без потери производительности — настройки, инструменты и план.
Cat: CROSS-DOMAIN | Security + Performance
Diff: L4 | Tools: terminal, security, code | Web0 Code1 Files1 Vision0 Long0 | Auto 8
Why: безопасность и скорость конфликтуют без осознанного баланса
Caps: secure performance, hardening, optimization, balance
---

### 1373 — Правовая проверка маркетинговых материалов
Джарвис, проверь маркетинговые материалы на правовые риски: реклама, товарные знаки, обещания и соответствие законам.
Cat: CROSS-DOMAIN | Legal + Marketing
Diff: L3 | Tools: research, documents | Web1 Code0 Files1 Vision0 Long0 | Auto 8
Why: юридические ошибки в рекламе стоят штрафов и репутации
Caps: legal review, advertising compliance, trademarks, claims
---

### 1374 — Финансовый план с анализом рисков
Джарвис, построй финансовый план с рисками: сценарии, чувствительность, стресс-тесты и защитные меры.
Cat: CROSS-DOMAIN | Finance + Risk
Diff: L3 | Tools: spreadsheets, math | Web0 Code0 Files1 Vision0 Long0 | Auto 8
Why: план без стресс-тестов ломается при первом отклонении
Caps: financial risk, scenarios, sensitivity, stress test
---

### 1375 — Создание бренда с дизайн-мышлением
Джарвис, создай бренд через дизайн-мышление: исследование пользователей, идеи, прототипы, тесты и запуск.
Cat: CROSS-DOMAIN | Branding + Design Thinking
Diff: L4 | Tools: research, documents, design | Web1 Code0 Files1 Vision0 Long1 | Auto 8
Why: бренд, рождённый из потребностей пользователей, выживает
Caps: brand design thinking, user research, prototyping, testing
---

### 1376 — Данные для HR-решений
Джарвис, используй данные для HR-решений: аналитика персонала, текучесть, эффективность и прогнозы — с рекомендациями.
Cat: CROSS-DOMAIN | Data + HR
Diff: L3 | Tools: data, spreadsheets, documents | Web0 Code0 Files1 Vision0 Long0 | Auto 8
Why: кадровые решения по данным объективнее интуитивных
Caps: people analytics, attrition, performance, forecasts
---

### 1377 — Инженерная документация для продаж
Джарвис, преврати технические характеристики в продающие материалы: понятные выгоды, сравнения и доказательства.
Cat: CROSS-DOMAIN | Engineering + Sales
Diff: L3 | Tools: documents, research | Web0 Code0 Files1 Vision0 Long0 | Auto 8
Why: техническая команда продаёт лучше, когда говорит языком выгод
Caps: technical sales, benefit selling, comparison, specs
---

### 1378 — Мониторинг бизнеса и ИТ вместе
Джарвис, объедини мониторинг бизнеса и ИТ: единый дашборд метрик, алерты и корреляция сбоев с выручкой.
Cat: CROSS-DOMAIN | Business + IT Monitoring
Diff: L4 | Tools: data, code, web | Web0 Code1 Files1 Vision0 Long0 | Auto 8
Why: ИТ-сбои напрямую бьют по бизнес-метрикам
Caps: business it monitoring, unified dashboard, alerting, correlation
---

### 1379 — Учебный материал с проверкой знаний
Джарвис, создай учебный материал с автоматической проверкой: теория, упражнения, тесты и обратная связь по ошибкам.
Cat: CROSS-DOMAIN | Education + Assessment
Diff: L3 | Tools: documents, code | Web0 Code1 Files1 Vision0 Long0 | Auto 8
Why: мгновенная проверка ускоряет обучение
Caps: learning material, auto grading, feedback, exercises
---

### 1380 — Соцсети с аналитикой эффективности
Джарвис, веди соцсети с аналитикой: план контента, публикации, сбор метрик и оптимизация стратегии по данным.
Cat: CROSS-DOMAIN | SMM + Analytics
Diff: L3 | Tools: web, data, documents | Web1 Code0 Files1 Vision0 Long0 | Auto 8
Why: SMM без аналитики — стрельба вслепую
Caps: social analytics, content plan, metrics, optimization
---

### 1381 — Защита личных данных в цифровом бизнесе
Джарвис, обеспечь соответствие защите данных в бизнесе: обработка персональных данных, политики, доступы и уведомления.
Cat: CROSS-DOMAIN | Privacy + Business
Diff: L4 | Tools: research, documents | Web1 Code0 Files1 Vision0 Long1 | Auto 8
Why: нарушения в работе с персональными данными дорого наказываются
Caps: data protection, gdpr, policies, compliance
---

### 1382 — Прототип продукта с пользовательскими тестами
Джарвис, создай прототип и проведи пользовательские тесты: сценарии, рекрутинг, наблюдение, выводы и итерации.
Cat: CROSS-DOMAIN | Product + UX
Diff: L4 | Tools: research, documents, design | Web1 Code0 Files1 Vision0 Long1 | Auto 8
Why: тесты с пользователями спасают продукт от ошибок
Caps: prototyping, user testing, scenarios, iterations
---

### 1383 — Отчёт инвестору с техническим разбором
Джарвис, подготовь отчёт инвестору: финансы, продукт, технологии, команда и риски — понятно и с фактами.
Cat: CROSS-DOMAIN | Finance + Tech
Diff: L4 | Tools: documents, spreadsheets, research | Web1 Code0 Files1 Vision0 Long0 | Auto 8
Why: инвесторский отчёт соединяет бизнес и техническую реальность
Caps: investor report, tech update, metrics, risks
---

### 1384 — Видео-обзор продукта с тестами
Джарвис, создай видео-обзор продукта: сценарий, тесты, съёмка, монтаж и публикация — с планом продвижения.
Cat: CROSS-DOMAIN | Video + Marketing
Diff: L3 | Tools: video, documents, web | Web1 Code0 Files1 Vision0 Long0 | Auto 8
Why: видео-обзоры строят доверие к продукту
Caps: product review video, script, testing, promotion
---

### 1385 — Переговоры с подготовкой данных
Джарвис, подготовь переговоры с данными: аналитика позиций сторон, ценовые модели, уступки и сценарии.
Cat: CROSS-DOMAIN | Negotiation + Data
Diff: L3 | Tools: research, spreadsheets, documents | Web1 Code0 Files1 Vision0 Long0 | Auto 8
Why: цифры дают переговорную силу и обоснованные аргументы
Caps: data driven negotiation, positions, pricing, scenarios
---

### 1386 — Автоматизация обучения команды
Джарвис, автоматизируй обучение команды: онбординг, курсы, проверка навыков и отчётность — единая система.
Cat: CROSS-DOMAIN | Learning + Automation
Diff: L3 | Tools: documents, code, data | Web0 Code1 Files1 Vision0 Long0 | Auto 8
Why: автоматизированное обучение масштабируется без тренеров
Caps: training automation, onboarding, skills, reporting
---

### 1387 — Креативная кампания с исследованием аудитории
Джарвис, создай креативную кампанию на основе исследования: инсайты, идеи, креативы, каналы и метрики.
Cat: CROSS-DOMAIN | Creativity + Research
Diff: L4 | Tools: research, documents, design | Web1 Code0 Files1 Vision0 Long1 | Auto 8
Why: креатив без инсайтов — дорогая красота
Caps: creative campaign, audience insight, concepts, metrics
---

### 1388 — Бизнес-план с научным анализом рынка
Джарвис, усиль бизнес-план научным анализом: данные рынка, статистика, исследования и доказательная база прогнозов.
Cat: CROSS-DOMAIN | Business + Science
Diff: L4 | Tools: research, documents, data | Web1 Code0 Files1 Vision0 Long1 | Auto 8
Why: бизнес-план с доказательствами убеждает инвесторов
Caps: evidence based business plan, market data, research, forecasts
---

### 1389 — Управление проектом с автоматизацией
Джарвис, управляй проектом с автоматизацией: планирование, автоотчёты, трекинг задач и аналитика в одном контуре.
Cat: CROSS-DOMAIN | PM + Automation
Diff: L4 | Tools: planning, code, data | Web0 Code1 Files1 Vision0 Long0 | Auto 8
Why: автоматизация рутины менеджера освобождает время на людей
Caps: automated project management, reports, tracking, analytics
---

### 1390 — Голосовой помощник для бизнеса
Джарвис, спроектируй голосового помощника для бизнеса: сценарии, голос, интеграции, тесты и запуск.
Cat: CROSS-DOMAIN | Voice + Business
Diff: L4 | Tools: research, audio, code, documents | Web1 Code1 Files1 Vision0 Long0 | Auto 8
Why: голосовые помощники снижают нагрузку на поддержку
Caps: voice assistant, scenarios, voice, integrations
---

### 1391 — Финансовое обучение команды
Джарвис, разработай программу финансовой грамотности для команды: основы, бюджетирование, инвестиции и практикумы.
Cat: CROSS-DOMAIN | Finance + Education
Diff: L3 | Tools: documents, research | Web1 Code0 Files1 Vision0 Long0 | Auto 8
Why: финансово грамотная команда принимает лучшие решения
Caps: financial literacy, team training, budgeting, investing
---

### 1392 — Диагностика бизнеса по данным
Джарвис, проведи диагностику бизнеса по данным: ключевые метрики, аномалии, тренды и рекомендации — как медицинский чек-ап.
Cat: CROSS-DOMAIN | Business + Analytics
Diff: L4 | Tools: data, spreadsheets, documents | Web0 Code0 Files1 Vision0 Long1 | Auto 8
Why: диагностика по данным выявляет болезни бизнеса рано
Caps: business diagnostics, metrics, anomalies, recommendations
---

### 1393 — Создание контента с проверкой фактов
Джарвис, создай контент с проверкой фактов: исследование, факт-чекинг, источники и публикация без ошибок.
Cat: CROSS-DOMAIN | Writing + Research
Diff: L3 | Tools: research, documents, web | Web1 Code0 Files1 Vision0 Long0 | Auto 8
Why: контент с проверенными фактами строит доверие аудитории
Caps: fact checked content, research, sources, accuracy
---

### 1394 — Мобильное приложение с аналитикой
Джарвис, создай мобильное приложение с аналитикой: трекинг событий, метрики, ретеншн и рост — от разработки до оптимизации.
Cat: CROSS-DOMAIN | Development + Analytics
Diff: L4 | Tools: code, data, documents | Web0 Code1 Files1 Vision0 Long0 | Auto 8
Why: аналитика внутри приложения показывает, что менять
Caps: mobile analytics, events, retention, growth
---

### 1395 — Правовое сопровождение стартапа
Джарвис, подготовь правовой пакет стартапа: устав, договоры, опционы, защита ИС и комплаенс — по этапам развития.
Cat: CROSS-DOMAIN | Legal + Startup
Diff: L4 | Tools: research, documents | Web1 Code0 Files1 Vision0 Long1 | Auto 8
Why: правовые ошибки стартапа стоят долей или самого бизнеса
Caps: startup legal, incorporation, ip, options, compliance
---

### 1396 — Экспортная стратегия с логистикой
Джарвис, разработай экспортную стратегию: рынки, логистика, таможня, документы, цены и риски.
Cat: CROSS-DOMAIN | Business + Logistics
Diff: L4 | Tools: research, documents, spreadsheets | Web1 Code0 Files1 Vision0 Long1 | Auto 8
Why: экспорт держится на логистике и документах не меньше, чем на продукте
Caps: export strategy, logistics, customs, documentation, risks
---

### 1397 — Умный дом с бюджетом
Джарвис, спроектируй умный дом: устройства, сценарии, интеграции, безопасность и бюджет с окупаемостью.
Cat: CROSS-DOMAIN | IoT + Finance
Diff: L3 | Tools: research, spreadsheets, documents | Web1 Code0 Files1 Vision0 Long0 | Auto 8
Why: умный дом без бюджета превращается в дорогую игрушку
Caps: smart home, devices, scenarios, budget
---

### 1398 — Карьерный план с аналитикой рынка
Джарвис, построй карьерный план с аналитикой: зарплаты, спрос, навыки, траектория и шаги на 3 года.
Cat: CROSS-DOMAIN | Career + Data
Diff: L3 | Tools: research, data, documents | Web1 Code0 Files1 Vision0 Long0 | Auto 8
Why: карьера по данным рынка строится быстрее и выгоднее
Caps: career planning, market data, salaries, skills, trajectory
---

### 1399 — Событие с видеотрансляцией
Джарвис, организуй событие с видеотрансляцией: программа, съёмка, стриминг, продвижение и пост-контент.
Cat: CROSS-DOMAIN | Events + Video
Diff: L4 | Tools: research, video, planning, web | Web1 Code0 Files1 Vision0 Long1 | Auto 8
Why: трансляция умножает аудиторию события в разы
Caps: event livestream, program, streaming, promotion
---

### 1400 — Комплексная стратегия выхода из кризиса
Джарвис, разработай стратегию выхода из кризиса: финансы, операция, команда, клиенты и коммуникации — единый план действий.
Cat: CROSS-DOMAIN | Business + Crisis
Diff: L4 | Tools: research, documents, spreadsheets | Web1 Code0 Files1 Vision0 Long1 | Auto 8
Why: кризис требует одновременных действий по всем фронтам
Caps: crisis strategy, finance, operations, communication, plan
---
### 1401 — Полное клонирование рабочего процесса
Джарвис, создай точную копию моего рабочего процесса: инструменты, файлы, настройки, автоматизация и документация — для быстрого восстановления на любом устройстве.
Cat: INSANE | Workflow Clone
Diff: L4 | Tools: files, terminal, documents | Web0 Code1 Files1 Vision0 Long1 | Auto 8
Why: клонирование рабочего процесса экономит дни настройки
Caps: workflow clone, environment setup, automation, restoration
---

### 1402 — Мозговой штурм 100 идей за час
Джарвис, проведи марафон генерации: 100 идей по теме за сессию, сгруппируй, оцени по критериям и выдели топ-10 для проработки.
Cat: INSANE | Ideation Marathon
Diff: L3 | Tools: conversation, documents | Web0 Code0 Files1 Vision0 Long0 | Auto 8
Why: объём генерации пробивает «потолок» обычного мышления
Caps: idea marathon, quantity, scoring, top picks
---

### 1403 — Обратный инжиниринг успешного продукта
Джарвис, проведи обратный инжиниринг продукта: разбери на составляющие, восстанови логику, найди слабые места и предложи улучшенную версию.
Cat: INSANE | Reverse Engineering
Diff: L4 | Tools: research, documents, web | Web1 Code0 Files1 Vision0 Long1 | Auto 8
Why: разбор чужого успеха ускоряет собственные решения
Caps: reverse engineering, teardown, analysis, improvements
---

### 1404 — Сценарий идеального дня
Джарвис, распиши сценарий идеального дня поминутно: сон, работа, спорт, обучение, семья и отдых — с обоснованием каждого блока.
Cat: INSANE | Perfect Day
Diff: L2 | Tools: planning, documents | Web0 Code0 Files1 Vision0 Long0 | Auto 7
Why: сценарий дня превращает ценности в конкретику
Caps: perfect day, schedule, balance, values
---

### 1405 — Предсказательный анализ трендов
Джарвис, проведи предсказательный анализ: собери сигналы из данных и событий, построй сценарии развития на 1–3 года и отметь точки перелома.
Cat: INSANE | Foresight
Diff: L4 | Tools: research, data, documents | Web1 Code0 Files1 Vision0 Long1 | Auto 8
Why: раннее предвидение трендов даёт стратегическое преимущество
Caps: foresight, trends, scenarios, signals
---

### 1406 — Энциклопедия по моей области
Джарвис, создай энциклопедию по моей области: разделы, статьи, термины, связи и уровень сложности — как персональный справочник.
Cat: INSANE | Personal Encyclopedia
Diff: L4 | Tools: research, documents | Web1 Code0 Files1 Vision0 Long1 | Auto 8
Why: персональная энциклопедия концентрирует всё знание области
Caps: encyclopedia, reference, structure, personal knowledge
---

### 1407 — Виртуальная команда для проекта
Джарвис, создай виртуальную команду: роли, задачи, график и система отчётов — чтобы проект шёл без моего участия в рутине.
Cat: INSANE | Virtual Team
Diff: L4 | Tools: planning, agents, code | Web0 Code1 Files1 Vision0 Long0 | Auto 8
Why: виртуальная команда масштабирует одного человека
Caps: virtual team, roles, delegation, autonomous workflow
---

### 1408 — Полная цифровая идентичность
Джарвис, организуй мою цифровую идентичность: профили, бренд, репутация, контент и защита — как управляемый актив.
Cat: INSANE | Digital Identity
Diff: L4 | Tools: research, web, documents | Web1 Code0 Files1 Vision0 Long1 | Auto 8
Why: цифровая идентичность работает на вас или против вас
Caps: digital identity, brand, reputation, protection
---

### 1409 — Комплексный языковой переход
Джарвис, организуй полный переход на другой язык: обучение, практика, погружение, материалы и цели по уровням.
Cat: INSANE | Language Immersion
Diff: L3 | Tools: research, documents, planning | Web1 Code0 Files1 Vision0 Long0 | Auto 8
Why: тотальное погружение ускоряет освоение языка в разы
Caps: language immersion, full transition, practice, immersion plan
---

### 1410 — Финансовая симуляция всей жизни
Джарвис, построй финансовую симуляцию жизни: доходы, расходы, инфляция, инвестиции и события — на 40 лет вперёд с проверкой сценариев.
Cat: INSANE | Life Simulation
Diff: L4 | Tools: spreadsheets, math | Web0 Code0 Files1 Vision0 Long0 | Auto 8
Why: долгосрочная симуляция показывает последствия решений сегодня
Caps: life simulation, financial modeling, long term, scenarios
---

### 1411 — Детальный разбор любимого фильма
Джарвис, разбери фильм как профессионал: сюжетные арки, режиссура, операторская работа, символизм и влияние — с рекомендациями для просмотра.
Cat: INSANE | Media Analysis
Diff: L2 | Tools: research | Web1 Code0 Files1 Vision0 Long0 | Auto 7
Why: глубокий разбор раскрывает мастерство создания историй
Caps: film analysis, storytelling, cinematography, symbolism
---

### 1412 — Собственная операционная система продуктивности
Джарвис, создай персональную ОС продуктивности: принципы, системы, инструменты, ритуалы и автоматизацию — как целостную методологию.
Cat: INSANE | Productivity OS
Diff: L4 | Tools: documents, planning, code | Web0 Code1 Files1 Vision0 Long1 | Auto 8
Why: целостная система продуктивности сильнее набора приёмов
Caps: productivity os, principles, systems, rituals
---

### 1413 — Сценарий «что если» для бизнеса
Джарвис, проведи анализ «что если»: 5 радикальных сценариев для бизнеса, их последствия, признаки наступления и планы действий.
Cat: INSANE | What If
Diff: L4 | Tools: research, documents | Web1 Code0 Files1 Vision0 Long1 | Auto 8
Why: готовность к неожиданным сценариям отличает устойчивый бизнес
Caps: what if analysis, scenarios, early signals, contingency
---

### 1414 — Создание собственного курса-бестселлера
Джарвис, создай курс-бестселлер: уникальная методология, контент, маркетинг, воронка и продажи — как полноценный продукт.
Cat: INSANE | Course Masterpiece
Diff: L4 | Tools: research, documents, planning | Web1 Code0 Files1 Vision0 Long1 | Auto 8
Why: методология отличает курс от компиляции чужих знаний
Caps: course masterpiece, methodology, content, funnel
---

### 1415 — Исследование «дня из жизни»
Джарвис, проведи исследование «день из жизни» целевого пользователя: по часам, действиям, мотивам и болям — для точных решений.
Cat: INSANE | Day in Life
Diff: L3 | Tools: research, documents | Web1 Code0 Files1 Vision0 Long0 | Auto 8
Why: день пользователя в деталях вскрывает настоящие возможности
Caps: day in life, user research, journey, insights
---

### 1416 — Автопилот рутины на месяц
Джарвис, построй автопилот моей рутины на месяц: все повторяющиеся действия, расписание, напоминания и автоматизация — без ежедневных решений.
Cat: INSANE | Routine Autopilot
Diff: L3 | Tools: planning, documents, code | Web0 Code1 Files1 Vision0 Long0 | Auto 8
Why: автопилот рутины освобождает умственную энергию
Caps: routine autopilot, automation, schedule, zero decisions
---

### 1417 — Создание карты влияния и нетворкинга
Джарвис, построй карту влияния: ключевые люди, связи, цели взаимодействия и план выстраивания отношений.
Cat: INSANE | Influence Map
Diff: L3 | Tools: research, documents | Web1 Code0 Files1 Vision0 Long0 | Auto 8
Why: карта влияния превращает нетворкинг в систему
Caps: influence map, network, relationships, plan
---

### 1418 — Полная инвентаризация цифровых активов
Джарвис, проведи полную инвентаризацию цифровых активов: файлы, аккаунты, сервисы, подписки и доступы — с картой и рекомендациями.
Cat: INSANE | Digital Inventory
Diff: L3 | Tools: files, research, documents | Web1 Code0 Files1 Vision0 Long1 | Auto 8
Why: без инвентаризации цифровые активы теряются и забываются
Caps: digital inventory, accounts, files, subscriptions, map
---

### 1419 — Марафон улучшений на 30 дней
Джарвис, организуй 30-дневный марафон улучшений: ежедневные микро-задачи по всем областям жизни с трекером и рефлексией.
Cat: INSANE | 30 Day Challenge
Diff: L2 | Tools: planning, documents | Web0 Code0 Files1 Vision0 Long0 | Auto 7
Why: короткий интенсив формирует привычки быстрее разрозненных попыток
Caps: 30 day challenge, daily tasks, tracker, reflection
---

### 1420 — Синтез знаний из всех проектов
Джарвис, синтезируй знания из всех моих проектов: общие паттерны, принципы и уроки — в единую систему знаний.
Cat: INSANE | Knowledge Synthesis
Diff: L4 | Tools: files, documents, data | Web0 Code0 Files1 Vision0 Long1 | Auto 8
Why: синтез опыта открывает инсайты, недоступные по проектам по отдельности
Caps: knowledge synthesis, patterns, principles, system
---

### 1421 — Полный сценарий развития за 10 лет
Джарвис, распиши сценарий моей жизни на 10 лет: цели по областям, этапы, ключевые решения и точки принятия развилок.
Cat: INSANE | 10 Year Plan
Diff: L3 | Tools: planning, documents | Web0 Code0 Files1 Vision0 Long1 | Auto 8
Why: горизонт в 10 лет делает сегодняшние решения осмысленными
Caps: 10 year plan, long term vision, milestones, decisions
---

### 1422 — Конструктор идеальной команды
Джарвис, сконструируй идеальную команду для задачи: роли, профили, компетенции, динамика и план найма.
Cat: INSANE | Team Design
Diff: L3 | Tools: research, documents | Web1 Code0 Files1 Vision0 Long0 | Auto 8
Why: состав команды решает результат сильнее бюджета
Caps: team design, roles, competencies, hiring
---

### 1423 — Анализ собственных решений за год
Джарвис, проанализируй мои решения за год: какие принесли результат, какие нет, паттерны мышления и правила на будущее.
Cat: INSANE | Decision Audit
Diff: L3 | Tools: conversation, documents | Web0 Code0 Files1 Vision0 Long0 | Auto 8
Why: аудит решений превращает опыт в систему принятия решений
Caps: decision audit, outcomes, patterns, rules
---

### 1424 — Создание контент-вселенной бренда
Джарвис, создай контент-вселенную бренда: мифология, персонажи, сюжеты, форматы и механики — как целый мир для аудитории.
Cat: INSANE | Content Universe
Diff: L4 | Tools: research, documents, design | Web1 Code0 Files1 Vision0 Long1 | Auto 8
Why: контент-вселенная создаёт глубокую вовлечённость аудитории
Caps: content universe, worldbuilding, formats, engagement
---

### 1425 — Прогноз поведения клиентов
Джарвис, построй модель прогноза поведения клиентов: данные, признаки, вероятности ухода и покупки — с планом воздействия.
Cat: INSANE | Customer Prediction
Diff: L4 | Tools: data, math, code | Web0 Code1 Files1 Vision0 Long0 | Auto 8
Why: предсказание поведения позволяет действовать до события
Caps: customer prediction, churn model, purchase propensity, intervention
---

### 1426 — Экстремальная оптимизация личного времени
Джарвис, проведи экстремальную оптимизацию времени: аудит каждой минуты, удаление потерь, делегирование и новый режим — с метриками эффекта.
Cat: INSANE | Time Extreme
Diff: L3 | Tools: planning, data, documents | Web0 Code0 Files1 Vision0 Long0 | Auto 8
Why: радикальный аудит времени находит часы, которых «не было»
Caps: time extreme, audit, elimination, delegation, metrics
---

### 1427 — Проект «вторая карьера за год»
Джарвис, организуй смену карьеры за год: навыки, портфолио, связи, опыт и трудоустройство — по неделям.
Cat: INSANE | Career Pivot
Diff: L4 | Tools: research, documents, planning | Web1 Code0 Files1 Vision0 Long1 | Auto 8
Why: смена карьеры за год достижима при системном плане
Caps: career pivot, skills, portfolio, network, job
---

### 1428 — Глубокая кастомизация ассистента
Джарвис, кастомизируй меня под свои задачи: персональные сценарии, голосовые команды, макросы и автоматизации — как продукт под себя.
Cat: INSANE | Assistant Customization
Diff: L3 | Tools: settings, code, documents | Web0 Code1 Files1 Vision0 Long0 | Auto 8
Why: настройка под свои сценарии делает ассистента незаменимым
Caps: assistant customization, scenarios, macros, automation
---

### 1429 — Строительство личной монополии
Джарвис, разработай стратегию личной монополии: уникальное сочетание навыков, ниша, позиция и защита от конкуренции.
Cat: INSANE | Personal Monopoly
Diff: L4 | Tools: research, documents | Web1 Code0 Files1 Vision0 Long0 | Auto 8
Why: уникальное сочетание навыков невозможно скопировать
Caps: personal monopoly, unique skills, niche, moat
---

### 1430 — Мега-ретроспектива жизни
Джарвис, проведи мега-ретроспективу: ключевые периоды жизни, решения, уроки, паттерны и стратегия следующего этапа.
Cat: INSANE | Life Retrospective
Diff: L3 | Tools: conversation, documents | Web0 Code0 Files1 Vision0 Long0 | Auto 8
Why: взгляд на всю жизнь даёт ясность для следующих шагов
Caps: life retrospective, periods, lessons, patterns, next stage
---
### 1431 — План действий при провале запуска
Джарвис, запуск провалился. Проведи разбор: что пошло не так, какие метрики, что спасти, как перезапуститься и что изменить.
Cat: FAILURE SCENARIOS | Launch Failure
Diff: L3 | Tools: data, documents, research | Web1 Code0 Files1 Vision0 Long0 | Auto 8
Why: провал запуска — данные для второго, успешного захода
Caps: launch failure, postmortem, rescue plan, relaunch
---

### 1432 — Реагирование на утечку данных
Джарвис, произошла утечка данных. Действуй по плану: оцени масштаб, останови утечку, уведоми кого нужно, исправь уязвимость и проведи разбор.
Cat: FAILURE SCENARIOS | Data Breach
Diff: L4 | Tools: security, files, research | Web1 Code1 Files1 Vision0 Long0 | Auto 8
Why: первые часы после утечки определяют размер ущерба
Caps: data breach response, containment, notification, recovery
---

### 1433 — Восстановление после срыва сроков
Джарвис, проект сорвал сроки. Проанализируй причины, оцени текущее состояние, перепланируй реалистично и определи приоритеты доставки.
Cat: FAILURE SCENARIOS | Missed Deadline
Diff: L3 | Tools: planning, documents, data | Web0 Code0 Files1 Vision0 Long0 | Auto 8
Why: срыв сроков управляем, если реагировать быстро и честно
Caps: deadline recovery, replanning, priorities, communication
---

### 1434 — Действия при финансовом кризисе
Джарвис, финансовый кризис: падает выручка, заканчиваются деньги. Составь план: сокращения, приоритеты платежей, поиск финансирования и контроль.
Cat: FAILURE SCENARIOS | Cash Crisis
Diff: L4 | Tools: spreadsheets, documents, research | Web1 Code0 Files1 Vision0 Long0 | Auto 8
Why: в кассовом кризисе решения принимаются за дни
Caps: cash crisis, cost cuts, payment priorities, financing
---

### 1435 — Восстановление репутации после скандала
Джарвис, случился скандал с брендом. Составь план: признание, действия, коммуникация, изменения и восстановление доверия.
Cat: FAILURE SCENARIOS | Reputation Crisis
Diff: L4 | Tools: research, documents, web | Web1 Code0 Files1 Vision0 Long1 | Auto 8
Why: реакция на скандал определяет, останется ли аудитория
Caps: crisis communication, apology, actions, trust recovery
---

### 1436 — Разбор увольнения ключевого сотрудника
Джарвис, уходит ключевой сотрудник. Действуй: передача знаний, распределение задач, срочный найм и минимизация последствий.
Cat: FAILURE SCENARIOS | Key Departure
Diff: L3 | Tools: documents, planning, research | Web1 Code0 Files1 Vision0 Long0 | Auto 8
Why: уход ключевого сотрудника без плана останавливает проекты
Caps: key person risk, knowledge transfer, hiring, continuity
---

### 1437 — Ответ на негативную публикацию
Джарвис, вышла негативная публикация о компании. Оцени риски, подготовь ответ, определи каналы и план дальнейших действий.
Cat: FAILURE SCENARIOS | Negative Press
Diff: L3 | Tools: research, documents | Web1 Code0 Files1 Vision0 Long0 | Auto 8
Why: продуманный ответ на негатив снижает ущерб репутации
Caps: negative press, response strategy, risk assessment, communication
---

### 1438 — Действия при пожаре в данных
Джарвис, потеряны важные файлы. Организуй восстановление: оценка, инструменты, порядок, проверка и предотвращение повторения.
Cat: FAILURE SCENARIOS | Data Loss
Diff: L4 | Tools: files, terminal, research | Web0 Code1 Files1 Vision0 Long0 | Auto 8
Why: правильные действия спасают данные, которые «невозможно вернуть»
Caps: data loss, recovery, tools, prevention
---

### 1439 — Экстренный план безопасности
Джарвис, обнаружена угроза безопасности. Действуй экстренно: изолируй, оцени, устрани, восстанови и усиль защиту.
Cat: FAILURE SCENARIOS | Security Emergency
Diff: L4 | Tools: security, terminal, research | Web1 Code1 Files1 Vision0 Long0 | Auto 8
Why: при угрозе порядок действий важнее скорости одиночных мер
Caps: emergency response, isolation, assessment, hardening
---

### 1440 — Переговоры в провальной ситуации
Джарвис, переговоры зашли в тупик или провалились. Разбери: что произошло, какие альтернативы, как спасти отношения и подготовить новый заход.
Cat: FAILURE SCENARIOS | Deal Failure
Diff: L3 | Tools: documents, research | Web1 Code0 Files1 Vision0 Long0 | Auto 8
Why: тупик в переговорах часто открывает лучшие альтернативы
Caps: deal failure, deadlock, alternatives, relationship repair
---

### 1441 — Разбор выгорания
Джарвис, чувствую выгорание. Проведи разбор: признаки, причины, срочные меры, план восстановления и профилактика.
Cat: FAILURE SCENARIOS | Burnout
Diff: L2 | Tools: conversation, planning | Web0 Code0 Files1 Vision0 Long0 | Auto 7
Why: ранняя работа с выгоранием спасает карьеру и здоровье
Caps: burnout, causes, recovery plan, prevention
---

### 1442 — Увольнение или потеря работы: план
Джарвис, потерял работу. Составь план: финансы на переход, обновление резюме, поиск, обучение и психологическая устойчивость.
Cat: FAILURE SCENARIOS | Job Loss
Diff: L3 | Tools: research, documents, planning | Web1 Code0 Files1 Vision0 Long0 | Auto 8
Why: потеря работы преодолима при чётком плане первых недель
Caps: job loss, financial runway, job search, resilience
---

### 1443 — Восстановление после неудачной сделки
Джарвис, крупная сделка сорвалась. Проведи разбор: причины, потери, уроки, восстановление воронки и корректировка стратегии.
Cat: FAILURE SCENARIOS | Lost Deal
Diff: L3 | Tools: data, documents | Web0 Code0 Files1 Vision0 Long0 | Auto 8
Why: разбор потерянной сделки повышает конверсию следующих
Caps: lost deal, analysis, pipeline recovery, lessons
---

### 1444 — Ответ на жалобу клиента
Джарвис, клиент недоволен и публикует жалобы. Разработай план: ответ, решение, компенсация, изменение процессов и работа с отзывами.
Cat: FAILURE SCENARIOS | Customer Complaint
Diff: L2 | Tools: documents, research | Web1 Code0 Files1 Vision0 Long0 | Auto 7
Why: правильная работа с жалобами возвращает клиентов и репутацию
Caps: complaint handling, resolution, compensation, feedback loop
---

### 1445 — План Б при провале продукта
Джарвис, продукт не взлетел. Проведи анализ: метрики, причины, pivot-варианты, решение по продукту и план действий.
Cat: FAILURE SCENARIOS | Product Pivot
Diff: L4 | Tools: data, research, documents | Web1 Code0 Files1 Vision0 Long1 | Auto 8
Why: своевременный pivot спасает компанию от гибели с продуктом
Caps: product pivot, failure analysis, alternatives, decision
---

### 1446 — Разбор ошибки с деньгами
Джарвис, потерял деньги из-за ошибки. Проведи разбор: что произошло, где деньги, как вернуть, как защититься в будущем.
Cat: FAILURE SCENARIOS | Money Mistake
Diff: L3 | Tools: research, spreadsheets, documents | Web1 Code0 Files1 Vision0 Long0 | Auto 8
Why: разбор денежных ошибок превращает потери в защиту
Caps: money mistake, recovery, fraud check, prevention
---

### 1447 — Ответ на техническую аварию
Джарвис, техническая авария остановила сервис. Действуй: статус, экстренное восстановление, коммуникация с клиентами и план предотвращения.
Cat: FAILURE SCENARIOS | Outage
Diff: L4 | Tools: terminal, web, documents | Web1 Code1 Files1 Vision0 Long0 | Auto 8
Why: прозрачная коммуникация во время аварии сохраняет доверие
Caps: outage response, restoration, communication, prevention
---

### 1448 — Извинение и исправление ошибки
Джарвис, допустил ошибку перед человеком или аудиторией. Помоги: формулировка извинения, исправление, восстановление доверия и уроки.
Cat: FAILURE SCENARIOS | Apology
Diff: L2 | Tools: conversation, documents | Web0 Code0 Files1 Vision0 Long0 | Auto 7
Why: искреннее извинение с действиями восстанавливает отношения
Caps: apology, making amends, trust repair, lesson
---

### 1449 — Разбор провального эксперимента
Джарвис, эксперимент провалился. Проведи разбор: гипотеза, данные, причины, что узнали и следующий эксперимент.
Cat: FAILURE SCENARIOS | Failed Experiment
Diff: L3 | Tools: data, math, documents | Web0 Code0 Files1 Vision0 Long0 | Auto 8
Why: провальный эксперимент — ценные данные, если его правильно разобрать
Caps: failed experiment, analysis, learnings, next test
---

### 1450 — Полное восстановление после неудачи
Джарвис, большая неудача позади. Составь полный план восстановления: эмоции, финансы, действия, окружение, уроки и новые цели.
Cat: FAILURE SCENARIOS | Comeback
Diff: L3 | Tools: conversation, planning, documents | Web0 Code0 Files1 Vision0 Long0 | Auto 8
Why: восстановление после неудачи — управляемый процесс
Caps: comeback, recovery plan, mindset, new goals
---
