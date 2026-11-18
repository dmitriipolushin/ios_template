# Ключи и доступы: что, где взять, куда положить

Все ключи живут вне git. Порядок:

1. Скачанный файл переложить из `~/Downloads` в хранилище:
   общий реестр ключей команды (вне репозитория, например `~/Developer/credentials/`)
   или в `secrets/` проекта (в `.gitignore`).
   ```sh
   mkdir -p secrets && mv ~/Downloads/AuthKey_XXXX.p8 secrets/ && chmod 600 secrets/*
   git check-ignore -v secrets/AuthKey_XXXX.p8      # должно показать правило .gitignore
   ```
2. Записать в `credentials/README.md`: что за ключ, ID, кто выпустил, где ещё
   используется. Сами значения — только в менеджере паролей / Phase.
3. Прод-значения — в Phase (CI). Локально — `App/Resources/Secrets.plist` (gitignored).
4. Никогда: в коммит, в YouTrack/чат, в вывод команд (`cat` ключа, `echo $KEY`).
   Если ключ утёк — отозвать в консоли, выпустить новый, обновить Phase.

## Переменные приложения

| Переменная | Что это | Где взять | Куда |
|---|---|---|---|
| Bundle ID | идентификатор приложения | схема `com.<бренд>.app`, зарегистрировать (см. ниже) | `project.yml` / build settings, на CI — из переменных окружения |
| Team ID | команда подписи | developer.apple.com → Membership details → Team ID | `project.yml` / CI |
| `ADAPTY_API_KEY` | **публичный** SDK-ключ Adapty (`public_live_…`) | Adapty → App settings → General → Public SDK key | `App/Resources/Secrets.plist` (из `Secrets.plist.example`, gitignored), на CI — из Phase |

Порядок чтения ключей в шаблоне: Keychain → `Secrets.plist` → переменная окружения.

Secret key Adapty (`secret_live_…`) в приложение не кладётся никогда — он только
для серверных запросов.

## Apple

### App Store Connect API key (для `asc` и для Adapty)

- **Где:** App Store Connect → Users and Access → Integrations → App Store Connect API →
  Team Keys → «+». Роль: **Admin** (для подписок и цен нужен как минимум App Manager).
- **Что получить:** файл `AuthKey_<KEY_ID>.p8` (скачивается **один раз**), Key ID,
  Issuer ID (вверху страницы).
- **Куда:**
  - `secrets/AuthKey_<KEY_ID>.p8` → `asc auth login` (см. SKILL.md);
  - тот же ключ загрузить в Adapty → App settings → iOS SDK → App Store Connect API
    (Adapty тогда видит цены, группы подписок, может `products push`).

### In-App Purchase key

- **Где:** App Store Connect → Users and Access → Integrations → **In-App Purchase** → «+».
- **Что:** `SubscriptionKey_<KEY_ID>.p8` (один раз), Key ID, Issuer ID.
- **Куда:** Adapty → App settings → iOS SDK → In-App Purchase API (проверка
  покупок, промо-офферы). Тот же ключ нужен `asc storekit …`.

### App Store Server Notifications

- Adapty → App settings → iOS SDK → скопировать URL уведомлений.
- Вставить в App Store Connect → приложение → App Information →
  App Store Server Notifications (Production и Sandbox, версия 2),
  или командой `asc apps update --id APP_ID --subscription-status-url URL --sandbox-subscription-status-url URL`.

### App-Specific Shared Secret

Нужен только старым SDK. Adapty 3.x работает через In-App Purchase key — не делать.

### Bundle ID, App Group, расширения

`asc bundle-ids create`, `asc bundle-ids capabilities add` (см. SKILL.md).
Каждое расширение (Share Extension и т.п.) — свой bundle ID `<APP_BUNDLE_ID>.<Имя>`.

## Чек-лист «всё подключено»

- [ ] `asc auth status` показывает профиль проекта; `adapty auth whoami` — пользователя
- [ ] Adapty iOS SDK: App Store Connect API key и In-App Purchase key загружены
- [ ] App Store Server Notifications указывают на Adapty
- [ ] `ADAPTY_API_KEY` в Phase и в локальном `Secrets.plist`
- [ ] Ни одного ключа в `git status`, YouTrack, чатах
