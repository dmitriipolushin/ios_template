import Foundation
import Security

/// Minimal Keychain wrapper for storing secrets (API keys, tokens).
/// Prefer Keychain over UserDefaults/plist for any sensitive data.
enum KeychainHelper {

    @discardableResult
    static func write(_ value: String, key: String) -> Bool {
        guard let data = value.data(using: .utf8) else { return false }
        let query: [CFString: Any] = [
            kSecClass: kSecClassGenericPassword,
            kSecAttrService: key,
            kSecValueData: data
        ]
        SecItemDelete(query as CFDictionary)
        return SecItemAdd(query as CFDictionary, nil) == errSecSuccess
    }

    static func read(key: String) -> String? {
        let query: [CFString: Any] = [
            kSecClass: kSecClassGenericPassword,
            kSecAttrService: key,
            kSecReturnData: true,
            kSecMatchLimit: kSecMatchLimitOne
        ]
        var result: AnyObject?
        guard SecItemCopyMatching(query as CFDictionary, &result) == errSecSuccess,
              let data = result as? Data else { return nil }
        return String(data: data, encoding: .utf8)
    }

    static func delete(key: String) {
        let query: [CFString: Any] = [
            kSecClass: kSecClassGenericPassword,
            kSecAttrService: key
        ]
        SecItemDelete(query as CFDictionary)
    }
}
