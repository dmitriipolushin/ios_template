---
name: store-subscriptions
description: Set up and verify in-app subscriptions end to end for an iOS (Swift) app — keys and where they go (KEYS.md), App Store Connect from the terminal with the `asc` CLI (subscriptions, offers, prices, review screenshots, localizations, App Store screenshots and metadata, TestFlight, bundle IDs), Adapty via the `adapty` CLI (login, products, offers, prices, paywalls, placements, A/B tests) and the Adapty ↔ App Store link (server notifications). Use when: 'подписки', 'Adapty', 'App Store Connect', 'asc', 'пейвол', 'плейсмент', 'ключи для стора', 'in-app purchase'.
---

# Подписки: App Store Connect + Adapty

Ключи — что скачать, где, куда положить: **[KEYS.md](KEYS.md)**. Начинать с него.

Порядок работы:
1. Ключи и доступы (KEYS.md).
2. Продукты в App Store Connect (`asc`).
3. Adapty: продукты, офферы, пейвол, плейсменты (`adapty`).
4. Связка Adapty ↔ App Store: уведомления.
5. Проверка: sandbox / TestFlight, покупка на устройстве.

## Правила

- Значения ключей не выводить и не коммитить. Только пути и ID.
- Перед изменением чего-то живого (цены, пейвол с покупками, удаление) —
  сначала прочитать текущее состояние (`list`/`view`/`get`), показать план,
  дождаться «да».
- **ID продуктов и офферов нельзя изменить и нельзя использовать
  повторно.** Схему ID согласовать до создания: `<bundle id>.premium.<период>`.
- Код приложения не зависит от того, что настроено в сторах: он берёт
  плейсменты и продукты из Adapty (`ADAPTY_API_KEY` из `Secrets.plist`, ID плейсментов в `AdaptyConfig`).

## 1. App Store Connect CLI (`asc`)

Установлен глобально (`asc --version`). Ищет команды сам:
`asc search "что нужно сделать" --output json`, у каждой команды `--help` с примерами.

### Вход

```sh
asc auth login --name <проект>-prod --key-id KEY_ID --issuer-id ISSUER_ID \
  --private-key "$PWD/secrets/AuthKey_KEY_ID.p8" --network
asc auth status            # профили, какой по умолчанию
asc auth doctor            # если что-то не так с ключом
asc --profile <проект>-prod apps list --output table   # ID приложения (APP_ID)
```

Несколько клиентов → несколько профилей; в командах всегда `--profile`,
не переключать default без нужды. Любой флаг принимает `@env:NAME` / `@file:PATH`.

### Что умеет (основное)

| Задача | Команды |
|---|---|
| Обзор релиза | `asc status --app APP_ID`, `asc validate` |
| Bundle ID и capabilities | `asc bundle-ids create/list`, `asc bundle-ids capabilities add --capability APP_GROUPS` |
| Подписи | `asc certificates`, `asc profiles`, `asc signing` |
| Группы и подписки | `asc subscriptions groups …`, `asc subscriptions setup` (группа + подписка + локализация + цена + территории + скриншот ревью за раз), `create/update/view/list/delete` |
| Цены | `asc subscriptions pricing equalize` (цена в базовой стране → все страны по сетке Apple), `pricing availability edit` (территории, новые территории), `pricing summary` |
| Офферы | `asc subscriptions offers introductory` (вступительные: бесплатный пробный период, скидка — импорт по CSV территорий), `promotional`, `offer-codes`, `win-back` |
| Ревью подписки | `asc subscriptions review screenshots create/delete` (скриншот пейвола для ревью), `review app-store-screenshot` |
| Льготный период | `asc subscriptions grace-periods` |
| Разовые покупки | `asc iap …` |
| StoreKit server API | `asc storekit …` (нужен In-App Purchase key) |
| Server notifications | `asc apps update --subscription-status-url … --sandbox-subscription-status-url …` |
| Тексты стора | `asc localizations list/create/update/upload/download` (.strings), `asc metadata pull/plan/apply` (метаданные файлами, с ревью плана), `metadata keywords` |
| Скриншоты стора | `asc screenshots capture` (с симулятора), `frame` (в рамку устройства), `review-generate` (HTML для проверки), `validate`, `upload`, `sizes`; превью-видео `asc video-previews` |
| Возрастной рейтинг, категории, шифрование, EULA | `asc age-rating`, `asc categories`, `asc encryption`, `asc eula` |
| TestFlight | `asc testflight groups/testers`, `asc publish testflight` |
| Sandbox-тестеры | `asc sandbox list/update/clear-history` |
| Сборка и отправка | `asc xcode`, `asc builds`, `asc publish appstore --submit`, `asc review`, `asc release-notes` |
| Отзывы, аналитика, финансы | `asc reviews`, `asc analytics`, `asc finance` |
| Чего нет в API | `asc capabilities` — что доступно только в вебе |

Особенности:
- Длинные загрузки (скриншоты): `ASC_TIMEOUT=300s ASC_UPLOAD_TIMEOUT=300s`.
- Ответ `--output json` сохранять в файл и разбирать, а не листать в терминале.
- Изменения с `--confirm` выполняются сразу — сначала прогон без него или `list`.

### Типовой порядок для подписок

1. `subscriptions setup` для каждого периода (группа создаётся первой
   подпиской, остальные — `--group-id`). Скриншот для ревью — экран пейвола
   с симулятора (`asc screenshots capture` или Maestro).
2. При необходимости — `pricing equalize`, `pricing availability edit`.
3. Офферы, если они нужны продукту (пробный период и т.п.): `offers introductory import`.
4. Проверка: `subscriptions view --id …` (state), `offers introductory list`,
   `pricing summary --app APP_ID`.
5. Подписки уходят на ревью вместе с первой версией приложения.

## 2. Adapty CLI (`adapty`)

Свежая версия — через npx, глобальная может быть старой:
`npx -y adapty@latest --version`. Для стабильности закрепить версию в команде
(`ad() { npx -y adapty@0.19.0 "$@"; }`).

### Вход

```sh
ad auth login        # открывает браузер, вход аккаунтом Adapty
ad auth whoami       # проверка токена на сервере
ad auth status       # локально, без сети
ad apps list         # APP_ID в Adapty (UUID)
ad apps get APP_ID --json   # в ответе есть sdk/secret key — не выводить, отфильтровать
```

### Что умеет

| Задача | Команды |
|---|---|
| Приложение | `apps create/get/list/update` |
| Уровень доступа (то, что проверяет код, например `premium`) | `access-levels create/list/get/update` |
| Продукты | `products create` (`--title`, `--period`, `--access-level-id`, `--ios-product-id`, `--price-usd`), `get/list/update` |
| Создать товар прямо в сторе | `products push` — создаёт продукт в App Store Connect из продукта Adapty (нужны USD-цена и ключи стора в Adapty) |
| Группы сторов | `product-groups list --store app_store`, `product-groups create` |
| Офферы | `product-offers create/list/get/update` — промо-офферы App Store |
| Цены по странам | `product-prices list` (что видит Adapty + статус синхронизации), `product-prices set` (с предпросмотром) |
| Пейвол | `paywalls create --title … --product-id … --product-id …`, `update`, `get`, `list`, `paywalls placements` |
| Плейсмент | `placements create --developer-id <id из кода> --title … --audiences '[{"segment_ids":[],"paywall_id":"PW","priority":0}]'`, `get/list/update` |
| Сегменты, A/B-тесты | `segments …`, `ab-tests create/start/stop/replace` |
| Онбординги (flows) | `flows …` |
| Аналитика | `analytics …`, `attribution …`, `asa …` |

Только в дашборде (CLI не умеет): Remote Config / Paywall Builder,
загрузка ключей App Store.
После первой покупки продукты пейвола не меняются — только через Duplicate
и переключение плейсментов на копию.

### Типовой порядок

1. `access-levels list` — уровень, который проверяет код, существует.
2. `products create` на каждый период с iOS product ID (или `products push`,
   если продукт ещё не заведён в сторе).
3. `product-offers create` — если нужны промо-офферы.
4. `paywalls create` с продуктами.
5. `placements create` — по одному на каждый ID плейсмента из кода
   (`grep -rn placementId App`), аудитория «все» → пейвол.
7. Проверка: `paywalls get`, `placements list`, `product-prices list`
   (цены подтягиваются из стора с задержкой; команды «перечитать» нет).

## 3. Связка Adapty ↔ App Store

- Ключи в Adapty + Server Notifications URL (KEYS.md, `asc apps update`).
- `ad product-groups list --store app_store` и `ad product-prices list` без
  ошибок = Adapty читает App Store.

## 4. Проверка покупок

- iOS: Sandbox-аккаунт (`asc sandbox …`) или TestFlight; на симуляторе — StoreKit
  configuration. Пейвол показывает цену и оффер, покупка даёт access level,
  восстановление работает.
- В приложении: статус premium после покупки, после перезапуска, после отмены.
- Отчёт пользователю: таблица «что настроено / где проверено / что осталось
  сделать вручную в дашборде».
