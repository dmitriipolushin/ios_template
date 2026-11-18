# iOS Anti-Patterns — как НЕ надо делать

Гайд основан на анализе реальных багов из продакшен iOS-приложений. Каждый пункт = повторяющаяся категория проблем.

Перед началом фичи — пройдись по этому списку. Если хоть один пункт релевантен — закладывай решение **до** написания UI, а не после QA.

---

## 1. Layout под длинные локали

### ❌ Не надо

```swift
Text("Continue")
    .font(.system(size: 17))
    .frame(width: 120, height: 44)        // фиксированная ширина → русский «Продолжить» обрежется
    .lineLimit(1)                          // без minimumScaleFactor — обрезание
```

### ✅ Надо

```swift
Text("continue_button")                    // ключ из Localizable.xcstrings, не строка
    .font(.body)                           // системные стили = Dynamic Type из коробки
    .lineLimit(2)
    .minimumScaleFactor(0.8)
    .frame(maxWidth: .infinity, minHeight: 44)
    .fixedSize(horizontal: false, vertical: true)   // дай высоте расти
```

Для адаптивности под разные тексты — `ViewThatFits` (iOS 16+):

```swift
ViewThatFits(in: .horizontal) {
    HStack { icon; Text(longLabel) }
    HStack { icon; Text(shortLabel) }
    icon
}
```

**Запрещено:** хардкод ширин/высот для текста, `lineLimit(1)` без `minimumScaleFactor`, отсутствие preview на длинных локалях.

**Правило:** каждый экран должен иметь preview минимум на двух локалях (например, `en` и `ru`/`de`). Используй `.environment(\.locale, .init(identifier: "de"))` в `#Preview`.

---

## 2. Картинки и тексты, привязанные к языку

### ❌ Не надо

- Запекать локализованный текст в PNG из Figma
- Хранить `Image("onboarding_step_2_ru")` и переключать вручную
- Системные диалоги (`NSCameraUsageDescription`) на одном языке

### ✅ Надо

- В Assets — варианты `Localized` (Xcode умеет хранить локализованные ассеты автоматически)
- Тексты — только через `String(localized:)` / `LocalizedStringKey`
- В `InfoPlist.xcstrings` — все usage-описания permissions, переведённые на все поддерживаемые языки
- Fallback всегда на `en`, не на язык первого продакта

**Проверка:** запусти `xcrun simctl launch booted <bundleID> -AppleLanguages '(ru)'` и пройди весь флоу.

---

## 3. Премиум-gating

### ❌ Не надо

```swift
// в каждом экране отдельно:
if !UserDefaults.standard.bool(forKey: "isPremium") {
    showPaywall = true
}
```

```swift
// @AppStorage напрямую в каждом экране — нет сервисного слоя
@AppStorage("hasPremium") var hasPremium: Bool = false
```

```swift
// lock-icon, который выглядит интерактивным, но без действия:
Image(systemName: "lock.fill")
```

### ✅ Надо

Единый source of truth:

```swift
@Observable
final class SubscriptionStore {
    private(set) var isPremium: Bool = false
    // обновляется из делегата подписки + при scenePhase = .active
}
```

Универсальный gate:

```swift
struct PremiumGate<Content: View>: View {
    let featureID: String
    @ViewBuilder let content: () -> Content
    @Environment(SubscriptionStore.self) private var store
    @Environment(Router.self) private var router

    var body: some View {
        content()
            .disabled(!store.isPremium)
            .overlay(alignment: .topTrailing) {
                if !store.isPremium {
                    Image(systemName: "lock.fill")
                        .padding(8)
                }
            }
            .contentShape(Rectangle())
            .onTapGesture {
                guard !store.isPremium else { return }
                router.presentPaywall(source: featureID)
            }
    }
}
```

**Запрещено:** lock-icon без `onTapGesture` к presentPaywall, проверка подписки через `UserDefaults` напрямую, разная логика «как открывается пейвол» в разных местах.

---

## 4. Adapty / нативный paywall

### ❌ Не надо

- Кнопка X в Adapty paywall без обработчика → закрывает экран без аналитики
- Restore Purchases / Terms / Privacy — настроены как «текст», а не actions
- Игнорировать `.cancelled` и `.error` в результате `makePurchase` — пользователь жмёт «отмена» в системном диалоге, а в приложении считаем покупку успешной
- Грузить пейвол при первом показе (нет интернета → пустой экран)
- Hardcoded цена/валюта в UI

### ✅ Надо

- Adapty Visual Builder: каждой кнопке прописать `action` (close, restore, openURL для Terms/Privacy, purchase product)
- Результат покупки — switch на все случаи:

```swift
switch result {
case .success(let profile): // unlock
case .userCancelled:        // analytics: paywall_cancelled, не закрывать пейвол
case .pending:              // ждать
case .failure(let error):   // alert + analytics
}
```

- Прелоад пейвола в фоне сразу после онбординга — экран должен быть готов к моменту показа
- Fallback-бандл (offline paywall config) — обязателен, если приложение продаётся в роуминге / самолёте
- Цена — только из `paywall.products`, никогда не строкой

---

## 5. Permissions — denial и re-check

### ❌ Не надо

```swift
Button("Use Camera") {
    AVCaptureDevice.requestAccess(for: .video) { granted in
        if granted { openCamera() }
        // если denied — кнопка молча ничего не делает
    }
}
```

```swift
@AppStorage("notificationsEnabled") var notifications = false
// тогл остаётся true, даже если пользователь отозвал разрешение в Settings
```

### ✅ Надо

Обработать все три состояния:

```swift
switch await PermissionService.cameraStatus() {
case .authorized: openCamera()
case .notDetermined: await requestCamera()
case .denied, .restricted:
    showSettingsAlert(message: "camera_permission_denied")
    // alert ведёт в UIApplication.openSettingsURLString
}
```

Re-check на foreground:

```swift
.onChange(of: scenePhase) { _, new in
    if new == .active {
        Task { await store.refreshAllPermissionStatuses() }
    }
}
```

---

## 6. Persistence — сохранять рано, не при `dismiss`

### ❌ Не надо

```swift
// сохраняем только при «Save» — если пользователь свернул, всё потеряется
Button("Save") {
    UserDefaults.standard.set(weight, forKey: "weight")
    dismiss()
}
```

```swift
@State private var theme: Theme = .light  // сбросится при перезапуске
```

```swift
// @Published + didSet { UserDefaults.set(...) } — двойная работа,
// которую решает @AppStorage в три раза короче
@Published var notificationsTime: Date? {
    didSet { UserDefaults.standard.set(notificationsTime, forKey: "ntime") }
}
```

### ✅ Надо

```swift
@AppStorage("theme") private var theme: Theme = .system

@State private var weight: Double = 0
.onChange(of: weight) { _, new in
    Task { try await profile.update(weight: new) }   // дебаунсить если нужно
}
```

Для онбординга — **per-step** persistence, не одним блоком в конце:

```swift
@AppStorage("onboarding.lastCompletedStep") var lastStep: Int = 0
@AppStorage("onboarding.profile.birthDate") var birthDate: Date = .distantPast
```

При запуске — резюмим со `lastStep + 1`. Главное правило: если пользователь kill+relaunch на любом шаге — он не должен начинать с нуля.

---

## 7. Аналитика — события и параметры

### ❌ Не надо

```swift
// событие без параметров — невозможно проанализировать поведение
Analytics.track("birthday_continue")
```

```swift
// конкатенация имени события строкой — не найти и не разрефакторить
Analytics.logEvent("\(screenName) screen", parameters: nil)
```

```swift
// параметры собираются ad-hoc в каждой view
Analytics.track("paywall_closed", ["source": "settings"])
// в другом месте
Analytics.track("paywall_closed", ["from": "settings"])  // другой ключ
```

```swift
// событие в onAppear без условий — стреляет дважды при возврате
.onAppear { Analytics.track("paywall_shown") }
```

### ✅ Надо

Типизированные события:

```swift
enum AnalyticsEvent {
    case birthdayContinue(birthDate: Date, age: Int)
    case paywallClosed(source: PaywallSource, isTrial: Bool)
    case paywallProductSelected(productID: String, position: Int)
    case onboardingStepCompleted(step: OnboardingStep, payload: [String: Any])

    var name: String { ... }
    var parameters: [String: Any] { ... }
}

Analytics.track(.birthdayContinue(birthDate: date, age: age))
```

Компилятор не даст забыть параметр. Имя ключа — в одном месте.

`paywall_shown` — стрелять в `.task`, не в `.onAppear`. Или в ViewModel при первом маунте.

**Чеклист перед мерджем фичи с трекингом:**
1. Каждый «continue»/«submit» имеет событие?
2. У события есть все параметры из спеки?
3. На отмену/закрытие тоже шлём событие (paywall_closed, paywall_cancelled)?
4. Не дублируется при возврате на экран?

---

## 8. Lifecycle — холодный старт и возврат из фона

### ❌ Не надо

```swift
struct HomeView: View {
    @State private var data: [Item] = []

    var body: some View {
        List(data) { ... }
            .onAppear {
                Task { data = await loadData() }   // первый кадр — пустой список
            }
    }
}
```

```swift
// .onAppear { loadSettings() } + отдельный .onChange(of: scenePhase) — 
// двойная логика вместо одной .task
```

### ✅ Надо

Три состояния всегда:

```swift
enum LoadState<T> { case loading, empty, loaded(T), failed(Error) }

@MainActor
@Observable
final class HomeViewModel {
    var state: LoadState<[Item]> = .loading

    func load() async {
        state = .loading
        do {
            let items = try await repository.fetch()
            state = items.isEmpty ? .empty : .loaded(items)
        } catch {
            state = .failed(error)
        }
    }
}
```

```swift
.task { await vm.load() }                       // не onAppear + Task
.onChange(of: scenePhase) { _, new in
    if new == .active { Task { await vm.refreshIfStale() } }
}
```

Сразу после онбординга — **прелоадить главные данные** на последнем шаге онбординга, не ждать `HomeView.task`. Иначе пользователь увидит «нули»/замочки/skeleton сразу после радостного «Готово!».

---

## 9. Уведомления — TimeZone и «висящие» расписания

### ❌ Не надо

```swift
var components = DateComponents()
components.hour = 9                              // в каком часовом поясе?
components.minute = 0
let trigger = UNCalendarNotificationTrigger(dateMatching: components, repeats: true)
```

При смене часового пояса / переезде — придёт в неправильное время. Если пользователь обновил время в настройках — старое расписание остаётся.

### ✅ Надо

```swift
var components = Calendar.current.dateComponents([.hour, .minute], from: userTime)
components.timeZone = .current
// при смене userTime / на NSSystemTimeZoneDidChange — вызвать NotificationsService.reschedule()
```

При любом изменении настроек уведомлений:
1. `removeAllPendingNotificationRequests()`
2. Зашедулить заново

---

## 10. Метрика ↔ имперская система

### ❌ Не надо

```swift
@AppStorage("weight") var weightString: String = "70 kg"   // парсить руками
@AppStorage("weightLb") var weightLb: Double = 0           // дублирование
```

### ✅ Надо

Хранить в одной единице, конвертировать на отображении:

```swift
@AppStorage("weightKg") var weightKg: Double = 0
@AppStorage("unitSystem") var unitSystem: UnitSystem = .metric

var displayWeight: Measurement<UnitMass> {
    let m = Measurement(value: weightKg, unit: UnitMass.kilograms)
    return unitSystem == .metric ? m : m.converted(to: .pounds)
}
```

При переключении системы — пересчитать **все** связанные значения (вес, рост, цели, потеря веса), не только то, что на экране.

---

## 11. Граничные значения — даты, нули, дефолты

### ❌ Не надо

```swift
@State private var birthDate: Date = Date()      // возраст = 0 при нажатии continue без выбора
@State private var screenTimeMinutes: Int = 0    // 0 → таймер 30:00
```

### ✅ Надо

- Дефолт = `nil` или sentinel-значение, кнопка `continue` `disabled` пока не выбрано
- Валидация диапазона: возраст 13–100, вес > 0, время > 0
- Edge cases в unit-тестах ViewModel'я (если тесты есть)

---

## 12. Бесконечные лоадеры и «нелепые» error-states

### ❌ Не надо

- `ProgressView()` без таймаута
- Сетевые ошибки → пустой экран без объяснения
- Кастомные UIAlertController вместо `Alert` / `ContentUnavailableView`

### ✅ Надо

```swift
.task {
    do {
        try await withTimeout(seconds: 15) { await load() }
    } catch is TimeoutError {
        state = .failed(.timeout)
    }
}
```

Empty state — `ContentUnavailableView` (iOS 17+):

```swift
ContentUnavailableView(
    "no_results_title",
    systemImage: "magnifyingglass",
    description: Text("no_results_description")
)
```

Error state — `ContentUnavailableView` с retry-кнопкой.

---

## 13. Диплинки в стор / share

### ❌ Не надо

```swift
// SKStoreReviewController нельзя дёргать из настроек по кнопке «Оценить» —
// Apple показывает его максимум 3 раза в год, и это не гарантировано.
SKStoreReviewController.requestReview()
```

```swift
// «Поделиться» через пустой URL → пустая страница в Safari
ShareLink(item: URL(string: "")!)
```

### ✅ Надо

Кнопка «Rate the app» — диплинк в форму отзыва:

```swift
let url = URL(string: "https://apps.apple.com/app/id\(appID)?action=write-review")!
UIApplication.shared.open(url)
```

`SKStoreReviewController.requestReview()` — только в моменты успеха (после удачного действия), не по кнопке.

Share — конкретный URL приложения в App Store, не пустой.

---

## 14. Графики

Не пишем с нуля. Используем готовые компоненты из [`App/Components/Charts/`](../App/Components/Charts/):

- `BarMetricChart` — bar-график с goal-линией
- `LineMetricChart` — линия с градиентной заливкой и аннотацией последнего значения
- `ChartPeriodPicker` — pill-сегментированный пикер периода (7д / 30д / 1г)
- `MetricSample` — общий тип данных

См. [`README.md`](../App/Components/Charts/README.md) с примерами использования.

Если макет требует чего-то, чего нет в библиотеке — **сначала** обсудить расширение существующих компонентов, **потом** писать новый.

---

## 15. Vision / ML распознавание (для трекеров движений)

### ❌ Не надо

- Засчитывать повторы сразу, как только модель что-то распознала
- Игнорировать ориентацию устройства
- Засчитывать «планку лёжа на животе» как валидную

### ✅ Надо

- **Armed-state**: трекер начинает считать только после стабильного удержания позы N секунд
- **Debounce**: между двумя засчитанными повторами должно пройти минимум T секунд
- **Стабильность**: не считать, если confidence модели меняется скачками
- **Ориентация**: проверять `UIDevice.orientation` — упражнение требует вертикального телефона?
- **Контр-проверки**: для планки — высота плеч от пола; для приседаний — амплитуда движения колена

---

## Чеклист перед началом фичи

Прогони мысленно. Если хоть один пункт «может быть проблемой» — закладывай решение в спеку, не оставляй на QA.

- [ ] Все строки локализованы? Превью на двух локалях?
- [ ] Есть платный gating? Использую `PremiumGate` модификатор?
- [ ] Есть permissions? Обработаны три состояния (notDetermined / authorized / denied)? Re-check на foreground?
- [ ] Есть форма / настройки? Сохраняю по `onChange`, не по `dismiss`?
- [ ] Есть аналитика? События типизированы? Все параметры из спеки?
- [ ] Есть данные с сети? Три состояния `LoadState`? Таймаут? Empty/error через `ContentUnavailableView`?
- [ ] Есть онбординг-экран? Per-step persistence? Аналитика на свайп?
- [ ] Есть пейвол? Все callback'и обработаны? Прелоадится в фоне? Fallback offline?
- [ ] Есть числовые поля? Дефолт = sentinel, валидация диапазона?
- [ ] Есть уведомления? TimeZone учтён? Reschedule при смене настроек?
- [ ] Есть метрики/имперские? Хранение в одной системе, конвертация на отображении?
- [ ] Есть график? Использую `App/Components/Charts/`?
