# Библиотека графиков

Два переиспользуемых SwiftUI-компонента поверх Apple `Charts` (iOS 17+).
Оба используют общий селектор периода `ChartPeriod` (7д / 30д / 1г) и
работают с одним и тем же типом данных `MetricSample`.

| Файл | Что рендерит |
|------|--------------|
| `BarMetricChart.swift` | Bar-график с раскраской столбцов по значению, опциональной горизонтальной целевой линией (dashed) и блёклыми плейсхолдер-столбцами для пустых дней. |
| `LineMetricChart.swift` | Сглаженная линия (Catmull-Rom) с градиентной заливкой под ней, аннотацией последнего значения в виде капсулы и пунктирной маркер-линией. |
| `ChartPeriodPicker.swift` | Pill-стиль сегментированный пикер периода — общий для обоих графиков. |
| `ChartPeriod.swift` | Enum `ChartPeriod` + структура данных `MetricSample`. |

## Быстрый старт

```swift
import SwiftUI

// Bar-график для трекинга тревожности (1–10, чем меньше тем лучше).
struct AnxietyChartView: View {
    let logs: [DailyLog]   // ваш доменный тип

    var body: some View {
        BarMetricChart(
            samples: logs.map { .init(date: $0.date, value: $0.anxietyScore) },
            yRange: 1...10,
            goal: 4,
            colorProvider: { v in
                v <= 3 ? .green : (v <= 6 ? .yellow : .red)
            }
        )
        .frame(height: 220)
    }
}

// Line-график веса.
struct WeightChartView: View {
    let logs: [WeightLog]

    var body: some View {
        LineMetricChart(
            samples: logs.map { .init(date: $0.date, value: $0.kilograms) },
            valueSuffix: "кг",
            tint: .green
        )
        .frame(height: 240)
    }
}
```

## Кастомизация

Оба графика принимают цвета tint / picker / axis — можно прокинуть токены
вашего дизайна. По умолчанию используются системные `Color.secondary` и
`Color(uiColor: .secondarySystemBackground)` — работает «из коробки».

```swift
BarMetricChart(
    samples: …,
    colorProvider: …,
    pickerTint: Color.brandSurface,
    axisColor: Color.brandMuted,
    placeholderColor: Color.brandBorder.opacity(0.4)
)
```

## Что НЕ входит в библиотеку (специально)

- **Персистентность**: передавайте уже загруженные `samples`. Библиотека
  не знает про SwiftData / Core Data / ваш способ хранения данных.
- **Конвертация единиц измерения**: `LineMetricChart` принимает только
  `valueSuffix` (строка). Если у вас kg ↔ lbs или другие конверсии — делайте
  их до создания `MetricSample`.
- **Локализация подписей периода**: `7d / 30d / 1y` — универсальные, при
  необходимости подменяйте через `ChartPeriod.rawValue`.

## Откуда взято

Извлечено из графиков вкладки «Я» проекта `product_scanner`
(`MetricChart.swift` и `WeightChart.swift`). Доменные цвета и токены
(`.obGreen / .obText / .obMuted` и т.п.) заменены на параметры, чтобы
тот же компонент подключался в любое приложение.
