import SwiftUI
import Charts

/// Smooth interpolated line chart with shaded area under the line, period
/// picker (7d / 30d / 1y), and a pinned annotation on the latest point.
/// Falls back to a single point or an empty-state when the dataset is sparse.
///
/// **Usage**
/// ```swift
/// LineMetricChart(
///     samples: weightLogs.map { .init(date: $0.date, value: $0.weight) },
///     valueSuffix: "kg",
///     tint: .green
/// )
/// .frame(height: 240)
/// ```
public struct LineMetricChart: View {

    // MARK: - Inputs

    public let samples: [MetricSample]

    /// Suffix appended to the latest-value annotation (e.g. "kg", "lbs", "%").
    public let valueSuffix: String

    /// Primary chart color used for the line, area gradient and annotation.
    public let tint: Color

    /// Tint used for the period picker background.
    public let pickerTint: Color

    /// Color of axis labels and grid lines.
    public let axisColor: Color

    /// Empty-state message shown when no samples fall within the period.
    public let emptyTitle: LocalizedStringKey

    public init(
        samples: [MetricSample],
        valueSuffix: String = "",
        tint: Color = .accentColor,
        pickerTint: Color = Color(uiColor: .secondarySystemBackground),
        axisColor: Color = Color.secondary,
        emptyTitle: LocalizedStringKey = "No data yet"
    ) {
        self.samples = samples
        self.valueSuffix = valueSuffix
        self.tint = tint
        self.pickerTint = pickerTint
        self.axisColor = axisColor
        self.emptyTitle = emptyTitle
    }

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

    // MARK: - Domain

    private struct Point: Identifiable {
        let id: Date
        let date: Date
        let value: Double
    }

    private var points: [Point] {
        let cal = Calendar.current
        let cutoff = cal.date(byAdding: .day, value: -(period.days - 1), to: cal.startOfDay(for: .now)) ?? .now
        return samples
            .compactMap { sample -> Point? in
                guard sample.date >= cutoff else { return nil }
                let normalized = cal.startOfDay(for: sample.date)
                return Point(id: normalized, date: normalized, value: sample.value)
            }
            .sorted { $0.date < $1.date }
    }

    private var yDomain: ClosedRange<Double> {
        let values = points.map(\.value)
        guard let mn = values.min(), let mx = values.max() else { return 0...100 }
        let range = mx - mn
        let bottomPad = max(range * 0.15, 0.5)
        // Wide top padding so the latest-value annotation has room above the
        // highest point without being clipped.
        let topPad = max(range * 0.45, 3.0)
        return max(mn - bottomPad, 0)...(mx + topPad)
    }

    private var xDomain: ClosedRange<Date> {
        let end = Calendar.current.startOfDay(for: .now)
        let start = Calendar.current.date(byAdding: .day, value: -(period.days - 1), to: end) ?? end
        let total = end.timeIntervalSince(start)
        let paddedEnd = end.addingTimeInterval(total * 0.1)
        return start...paddedEnd
    }

    // MARK: - Chart routing

    @ViewBuilder
    private var chart: some View {
        if points.count >= 2 {
            multiPointChart
        } else if let single = points.first {
            singlePointChart(single)
        } else {
            emptyChart
        }
    }

    // MARK: - Multi-point

    private var multiPointChart: some View {
        let lower = yDomain.lowerBound
        let latest = points.last!

        return Chart {
            // Gradient fill under the line.
            ForEach(points) { p in
                AreaMark(
                    x: .value("Date", p.date),
                    yStart: .value("Min", lower),
                    yEnd: .value("Value", p.value)
                )
                .foregroundStyle(
                    LinearGradient(
                        colors: [tint.opacity(0.30), tint.opacity(0.0)],
                        startPoint: .top,
                        endPoint: .bottom
                    )
                )
                .interpolationMethod(.catmullRom)
            }

            // Line.
            ForEach(points) { p in
                LineMark(
                    x: .value("Date", p.date),
                    y: .value("Value", p.value)
                )
                .foregroundStyle(tint)
                .lineStyle(StrokeStyle(lineWidth: 3))
                .interpolationMethod(.catmullRom)
            }

            // Latest value: white halo with annotation pill.
            PointMark(
                x: .value("Date", latest.date),
                y: .value("Value", latest.value)
            )
            .foregroundStyle(.white)
            .symbolSize(110)
            .annotation(
                position: .top,
                spacing: 6,
                overflowResolution: .init(x: .fit, y: .disabled)
            ) {
                Text(annotation(latest.value))
                    .font(.system(size: 11, weight: .bold))
                    .foregroundStyle(.white)
                    .padding(.horizontal, 6)
                    .padding(.vertical, 3)
                    .background(RoundedRectangle(cornerRadius: 6).fill(tint))
            }

            PointMark(
                x: .value("Date", latest.date),
                y: .value("Value", latest.value)
            )
            .foregroundStyle(tint)
            .symbolSize(50)

            RuleMark(x: .value("Date", latest.date))
                .foregroundStyle(axisColor.opacity(0.3))
                .lineStyle(StrokeStyle(lineWidth: 1, dash: [4, 4]))
        }
        .chartXScale(domain: xDomain, range: .plotDimension(padding: 0))
        .chartYScale(domain: yDomain, range: .plotDimension(padding: 0))
        .chartXAxis { xAxis }
        .chartYAxis { yAxis }
    }

    // MARK: - Single point

    private func singlePointChart(_ single: Point) -> some View {
        Chart {
            PointMark(
                x: .value("Date", single.date),
                y: .value("Value", single.value)
            )
            .foregroundStyle(tint)
            .symbolSize(80)
            .annotation(position: .top, spacing: 8) {
                Text(annotation(single.value))
                    .font(.system(size: 11, weight: .bold))
                    .foregroundStyle(tint)
            }
        }
        .chartXScale(domain: xDomain, range: .plotDimension(padding: 0))
        .chartYScale(domain: (single.value - 5)...(single.value + 5))
        .chartXAxis { xAxis }
    }

    private var emptyChart: some View {
        Text(emptyTitle)
            .font(.system(size: 13))
            .foregroundStyle(axisColor)
            .frame(maxWidth: .infinity, alignment: .center)
    }

    // MARK: - Axes

    private var xAxis: some AxisContent {
        AxisMarks(values: .stride(by: strideComponent, count: strideCount)) { _ in
            AxisGridLine(stroke: StrokeStyle(lineWidth: 0.5, dash: [4, 4]))
                .foregroundStyle(axisColor.opacity(0.5))
            AxisTick().foregroundStyle(.clear)
            AxisValueLabel(format: dateFormat, anchor: .top, collisionResolution: .disabled)
                .font(.system(size: 11, weight: .medium))
                .foregroundStyle(axisColor)
        }
    }

    private var yAxis: some AxisContent {
        AxisMarks(position: .trailing, values: .automatic(desiredCount: 4)) { v in
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

    private var strideComponent: Calendar.Component {
        switch period {
        case .week, .month: return .day
        case .year: return .month
        }
    }

    private var strideCount: Int {
        switch period {
        case .week: return 1
        case .month: return 5
        case .year: return 2
        }
    }

    private var dateFormat: Date.FormatStyle {
        switch period {
        case .week: return .dateTime.weekday(.short)
        case .month: return .dateTime.day()
        case .year: return .dateTime.month(.abbreviated)
        }
    }

    // MARK: - Formatting

    private func yLabel(_ v: Double) -> String {
        v == v.rounded() ? String(format: "%.0f", v) : String(format: "%.1f", v)
    }

    private func annotation(_ v: Double) -> String {
        let formatted = v == v.rounded() ? String(format: "%.0f", v) : String(format: "%.1f", v)
        return valueSuffix.isEmpty ? formatted : "\(formatted) \(valueSuffix)"
    }
}

// MARK: - Preview

#Preview {
    let now = Date()
    let cal = Calendar.current
    let samples: [MetricSample] = (0..<7).compactMap { offset in
        guard let date = cal.date(byAdding: .day, value: -offset, to: now) else { return nil }
        return MetricSample(date: date, value: 70 + Double.random(in: -2...2))
    }

    return VStack {
        LineMetricChart(
            samples: samples,
            valueSuffix: "kg",
            tint: .green
        )
        .frame(height: 240)
        .padding()
    }
}
