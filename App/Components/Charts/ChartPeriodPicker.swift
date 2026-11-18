import SwiftUI

/// Compact pill-style segmented picker for `ChartPeriod`. Shared by all chart
/// components in the library so chart "headers" stay visually consistent.
public struct ChartPeriodPicker: View {
    @Binding var period: ChartPeriod
    let tint: Color
    let accentColor: Color

    public init(
        period: Binding<ChartPeriod>,
        tint: Color = Color(uiColor: .secondarySystemBackground),
        accentColor: Color = Color.secondary
    ) {
        self._period = period
        self.tint = tint
        self.accentColor = accentColor
    }

    public var body: some View {
        HStack(spacing: 6) {
            ForEach(ChartPeriod.allCases) { p in
                Button {
                    withAnimation(.spring(duration: 0.25)) { period = p }
                } label: {
                    Text(p.rawValue)
                        .font(.system(size: 13, weight: .semibold))
                        .foregroundStyle(period == p ? Color.primary : accentColor)
                        .padding(.horizontal, 12)
                        .padding(.vertical, 6)
                        .background(
                            Capsule().fill(period == p ? tint : Color.clear)
                        )
                        .overlay(
                            Capsule().stroke(
                                period == p ? accentColor.opacity(0.25) : Color.clear,
                                lineWidth: 1
                            )
                        )
                }
                .buttonStyle(.plain)
            }
            Spacer()
        }
    }
}
