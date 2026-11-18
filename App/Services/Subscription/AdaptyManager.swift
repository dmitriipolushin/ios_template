import Foundation
import Adapty

// MARK: - Configuration

enum AdaptyConfig {
    /// Replace with your Adapty public SDK key (Dashboard → App settings → General)
    static let apiKey = "YOUR_ADAPTY_PUBLIC_KEY"

    /// Placement ID configured in Adapty dashboard
    static let placementId = "onboarding.paywall"

    /// Access level name configured in Adapty dashboard
    static let accessLevel = "premium"
}

// MARK: - AdaptyManager

@MainActor
@Observable
final class AdaptyManager: AdaptyDelegate {
    static let shared = AdaptyManager()

    private(set) var isPremium = false
    private(set) var products: [AdaptyPaywallProduct] = []
    var isLoading = false
    var errorMessage: String?

    private var paywall: AdaptyPaywall?

    private init() {}

    // MARK: - Activation

    /// Call once in App.init(). Uses AdaptyConfiguration builder per official docs.
    func activate() async {
        guard !AdaptyConfig.apiKey.hasPrefix("YOUR_") else {
            assertionFailure("[AdaptyManager] Replace YOUR_ADAPTY_PUBLIC_KEY with a real key.")
            return
        }

        do {
            let config = AdaptyConfiguration
                .builder(withAPIKey: AdaptyConfig.apiKey)
                .with(idfaCollectionDisabled: true)
                .build()

            #if DEBUG
            Adapty.logLevel = .verbose
            #else
            Adapty.logLevel = .error
            #endif

            try await Adapty.activate(with: config)
            Adapty.delegate = self
            await refreshProfile()
        } catch {
            logError("Activation failed", error)
        }
    }

    // MARK: - AdaptyDelegate

    /// Called by SDK when profile updates (purchase from another device, subscription renewal, etc.)
    nonisolated func didLoadLatestProfile(_ profile: AdaptyProfile) {
        Task { @MainActor in
            isPremium = Self.isSubscriptionActive(profile)
        }
    }

    // MARK: - Profile & Status

    func refreshProfile() async {
        do {
            let profile = try await Adapty.getProfile()
            isPremium = Self.isSubscriptionActive(profile)
        } catch {
            logError("Failed to get profile", error)
        }
    }

    // MARK: - Fetch Products

    func fetchProducts() async {
        isLoading = true
        errorMessage = nil
        defer { isLoading = false }

        do {
            let fetchedPaywall = try await Adapty.getPaywall(placementId: AdaptyConfig.placementId)
            paywall = fetchedPaywall
            products = try await Adapty.getPaywallProducts(paywall: fetchedPaywall)
            try? await Adapty.logShowPaywall(fetchedPaywall)
        } catch {
            errorMessage = error.localizedDescription
            logError("Failed to fetch products", error)
        }
    }

    // MARK: - Purchase

    func purchase(_ product: AdaptyPaywallProduct) async -> Bool {
        isLoading = true
        errorMessage = nil
        defer { isLoading = false }

        do {
            let result = try await Adapty.makePurchase(product: product)

            switch result {
            case .userCancelled:
                return false
            case .pending:
                return false
            case let .success(profile, _):
                var active = Self.isSubscriptionActive(profile)

                // Sandbox may delay activation — retry once after 2s
                if !active {
                    try? await Task.sleep(for: .seconds(2))
                    if let refreshed = try? await Adapty.getProfile() {
                        active = Self.isSubscriptionActive(refreshed)
                    }
                }

                isPremium = active
                return active
            }
        } catch {
            if let adaptyError = error as? AdaptyError,
               adaptyError.adaptyErrorCode == .paymentCancelled {
                return false
            }
            errorMessage = error.localizedDescription
            logError("Purchase failed", error)
            return false
        }
    }

    // MARK: - Restore

    func restore() async -> Bool {
        isLoading = true
        errorMessage = nil
        defer { isLoading = false }

        do {
            let profile = try await Adapty.restorePurchases()
            let active = Self.isSubscriptionActive(profile)
            isPremium = active
            return active
        } catch {
            errorMessage = error.localizedDescription
            logError("Restore failed", error)
            return false
        }
    }

    // MARK: - Product Helpers

    func product(containing keyword: String) -> AdaptyPaywallProduct? {
        products.first { $0.vendorProductId.localizedCaseInsensitiveContains(keyword) }
    }

    var weeklyProduct: AdaptyPaywallProduct? { product(containing: "weekly") }
    var monthlyProduct: AdaptyPaywallProduct? { product(containing: "monthly") }
    var yearlyProduct: AdaptyPaywallProduct? { product(containing: "yearly") }

    // MARK: - User Identification
    //
    // Раскомментировать когда в приложении появляется авторизация (Supabase, Firebase Auth и т.д.).
    // Без identify() подписка привязана к устройству — если пользователь сменит телефон,
    // подписка не перенесётся. С identify() подписка привязывается к аккаунту.
    //
    // func identify(userID: String) async {
    //     do {
    //         try await Adapty.identify(userID)
    //     } catch {
    //         logError("Identify failed", error)
    //     }
    // }
    //
    // func logout() async {
    //     do {
    //         try await Adapty.logout()
    //         isPremium = false
    //     } catch {
    //         logError("Logout failed", error)
    //     }
    // }
    //
    // Если используется Amplitude / Mixpanel — связать device ID для сквозной аналитики
    // (revenue-события из Adapty будут видны в аналитике):
    //
    // func linkAnalytics(amplitudeDeviceId: String) async {
    //     do {
    //         try await Adapty.setIntegrationIdentifier(
    //             key: "amplitude_device_id",
    //             value: amplitudeDeviceId
    //         )
    //     } catch {
    //         logError("Analytics link failed", error)
    //     }
    // }

    // MARK: - Premium Gating
    //
    // Раскомментировать и заполнить кейсами конкретного приложения.
    // Позволяет в одном месте перечислить все действия за пейволом,
    // вместо размазывания `if isPremium` по всему коду.
    //
    // enum PremiumAction {
    //     case someFeature
    //     case anotherFeature
    // }
    //
    // func requirePremium(for action: PremiumAction) -> Bool {
    //     isPremium
    // }

    // MARK: - Private

    private static func isSubscriptionActive(_ profile: AdaptyProfile?) -> Bool {
        guard let profile else { return false }

        // 1. Check access level (primary, covers most cases)
        if profile.accessLevels[AdaptyConfig.accessLevel]?.isActive == true {
            return true
        }

        // 2. Fallback: check subscriptions directly (handles grace period & auto-renewal delays)
        return profile.subscriptions.values.contains { subscription in
            subscription.isActive
                || subscription.isInGracePeriod
                || (subscription.willRenew && subscription.expiresAt.map { $0 > Date() } ?? false)
        }
    }

    private func logError(_ message: String, _ error: Error) {
        #if DEBUG
        print("[AdaptyManager] \(message): \(error.localizedDescription)")
        #endif
    }
}
