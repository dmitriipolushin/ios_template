import SwiftUI
import Charts

/// Bar chart with a period picker (7d / 30d / 1y), optional dashed goal line,
/// and per-bar coloring driven by the supplied `colorProvider`. Missing days
/// in the period render as faint placeholder bars to keep the timeline dense.
///
/// **Usage**
/// ```swift
/// BarMetricChart(
///     samples: anxietyLogs.map { .init(date: $0.date, value: $0.score) },
///     yRange: 1...10,
///     goal: 4,
///     colorProvider: { v in v <= 3 ? .green : (v <= 6 ? .yellow : .red) }
/// )
/// .frame(height: 200)
/// ```
public struct BarMetricChart: View {

    // MARK: - Inputs

    /// Observations to render. Multiple samples on the same day are coalesced
    /// (last write wins) so the chart shows one bar per day.
    public let samples: [MetricSample]

    /// Optional fixed Y range. When nil the chart auto-scales to the data.
    public let yRange: ClosedRange<Double>?

    /// Optional dashed horizontal goal line.
    public let goal: Double?

    /// Returns the bar color for a value (e.g. red/yellow/green buckets).
    public let colorProvider: (Double) -> Color

    /// Tint used for the period picker chip background.
    public let pickerTint: Color

    /// Color of axis labels and grid lines.
    public let axisColor: Color

    /// Color of the placeholder bar shown for days without data.
    public let placeholderColor: Color

    public init(
        samples: [MetricSample],
        yRange: ClosedRange<Double>? = nil,
        goal: Double? = nil,
        colorProvider: @escaping (Double) -> Color,
        pickerTint: Color = Color(uiColor: .secondarySystemBackground),
        axisColor: Color = Color.secondary,
        placeholderColor: Color = Color.secondary.opacity(0.25)
    ) {
        self.samples = samples
        self.yRange = yRange
        self.goal = goal
        self.colorProvider = colorProvider
        self.pickerTint = pickerTint
        self.axisColor = axisColor
        self.placeholderColor = placeholderColor
    }

    // MARK: - State

    @State private var period: ChartPeriod = .week

    // MARK: - Body

    public var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            ChartPeriodPicker(
                period: $period,
                tint: pickerTint,
                accentColor: axisColor
            )
            chart
        }
    }

    // MARK: - Bars

    private struct Bar: Identifiable {
        let id: String
        let date: Date
        let value: Double?
    }

    private var bars: [Bar] {
        let calendar = Calendar.current
        let today = calendar.startOfDay(for: .now)
        let formatter = DateFormatter()
        formatter.dateFormat = "yyyy-MM-dd"
        formatter.timeZone = .current

        var byKey: [String: Double] = [:]
        for sample in samples {
            byKey[formatter.string(from: sample.date)] = sample.value
        }

        return (0..<period.days).reversed().map { offset -> Bar in
            let date = calendar.date(byAdding: .day, value: -offset, to: today) ?? today
            let key = formatter.string(from: date)
            return Bar(id: key, date: date, value: byKey[key])
        }
    }

    private var values: [Double] { bars.compactMap { $0.value } }

    private var maxScale: Double {
        if let yRange { return yRange.upperBound }
        return max((values.max() ?? 10) * 1.15, 1)
    }
    private var minScale: Double { yRange?.lowerBound ?? 0 }

    // MARK: - Chart

    private var chart: some View {
        Chart {
            if let goal {
                RuleMark(y: .value("Goal", goal))
                    .foregroundStyle(axisColor.opacity(0.5))
                    .lineStyle(StrokeStyle(lineWidth: 1, dash: [4, 4]))
            }

            ForEach(bars) { bar in
                if let v = bar.value {
                    BarMark(
                        x: .value("Date", bar.date, unit: .day),
                        y: .value("Value", v),
                        width: .fixed(barWidth)
                    )
                    .clipShape(RoundedRectangle(cornerRadius: 3))
                    .foregroundStyle(colorProvider(v))
                } else {
                    BarMark(
                        x: .value("Date", bar.date, unit: .day),
                        y: .value("Value", maxScale * 0.03),
                        width: .fixed(barWidth)
                    )
                    .clipShape(RoundedRectangle(cornerRadius: 3))
                    .foregroundStyle(placeholderColor)
                }
            }
        }
        .chartYScale(domain: minScale...maxScale)
        .chartXAxis {
            AxisMarks(values: xAxisValues) { _ in
                AxisValueLabel(format: xAxisFormat, centered: true)
                    .font(.system(size: 11, weight: .medium))
                    .foregroundStyle(axisColor)
            }
        }
        .chartYAxis {
            AxisMarks(position: .trailing, values: yAxisValues) { v in
                AxisGridLine(stroke: StrokeStyle(lineWidth: 0.5, dash: [3, 3]))
                    .foregroundStyle(axisColor.opacity(0.5))
                AxisValueLabel {
                    if let val = v.as(Double.self) {
                        Text(yLabel(val))
                            .font(.system(size: 11, weight: .medium))
                            .foregroundStyle(axisColor)
                    }
                }
            }
        }
    }

    private var barWidth: CGFloat {
        switch period {
        case .week: return 24
        case .month: return 7
        case .year: return 2
        }
    }

    private var xAxisValues: AxisMarkValues {
        switch period {
        case .week: return .stride(by: .day, count: 1)
        case .month: return .stride(by: .day, count: 5)
        case .year: return .stride(by: .month, count: 2)
        }
    }

    private var xAxisFormat: Date.FormatStyle {
        switch period {
        case .week: return .dateTime.weekday(.abbreviated)
        case .month: return .dateTime.day().month(.abbreviated)
        case .year: return .dateTime.month(.abbreviated)
        }
    }

    private var yAxisValues: [Double] {
        if let range = yRange {
            let lo = range.lowerBound
            let hi = range.upperBound
            let step = (hi - lo) / 4
            return stride(from: lo, through: hi, by: step).map { $0 }
        }
        let step = maxScale / 4
        return stride(from: 0, through: maxScale, by: step).map { $0 }
    }

    private func yLabel(_ v: Double) -> String {
        if v.truncatingRemainder(dividingBy: 1) == 0 {
            return String(format: "%.0f", v)
        }
        return String(format: "%.1f", v)
    }
}

// MARK: - Preview

#Preview {
    let now = Date()
    let cal = Calendar.current
    let samples: [MetricSample] = (0..<7).compactMap { offset in
        guard let date = cal.date(byAdding: .day, value: -offset, to: now) else { return nil }
        return MetricSample(date: date, value: Double.random(in: 1...10))
    }

    return VStack {
        BarMetricChart(
            samples: samples,
            yRange: 1...10,
            goal: 4,
            colorProvider: { v in
                v <= 3 ? .green : (v <= 6 ? .yellow : .red)
            }
        )
        .frame(height: 220)
        .padding()
    }
}
