import Foundation

/// Selectable timespan for a metric chart. Used by both `BarMetricChart` and
/// `LineMetricChart` to scope the data window and adapt axis density.
public enum ChartPeriod: String, CaseIterable, Identifiable, Sendable {
    case week = "7d"
    case month = "30d"
    case year = "1y"

    public var id: String { rawValue }

    public var days: Int {
        switch self {
        case .week: return 7
        case .month: return 30
        case .year: return 365
        }
    }
}

/// One observation: a date and a numeric value. Charts work on arrays of these.
public struct MetricSample: Identifiable, Hashable, Sendable {
    public let id: UUID
    public let date: Date
    public let value: Double

    public init(date: Date, value: Double, id: UUID = UUID()) {
        self.id = id
        self.date = date
        self.value = value
    }
}
