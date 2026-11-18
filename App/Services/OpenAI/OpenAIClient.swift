import Foundation

// MARK: - Configuration

enum OpenAIConfig {
    /// Default model for all completions
    static let model = "gpt-4o-mini"

    /// Direct OpenAI endpoint. Replace with proxy URL if using Cloudflare Worker or similar.
    static let endpoint = "https://api.openai.com/v1/chat/completions"

    /// Keychain key where the API key is stored.
    /// Seed it on first launch: `KeychainHelper.write("sk-...", key: OpenAIConfig.keychainKey)`
    /// Or load from Secrets.plist / environment variable — see `resolveAPIKey()`.
    static let keychainKey = "openai.api.key"

    /// Resolves API key with fallback chain: Keychain → Secrets.plist → Environment variable.
    static func resolveAPIKey() -> String? {
        // 1. Keychain (most secure, preferred for production)
        if let key = KeychainHelper.read(key: keychainKey), !key.isEmpty {
            return key
        }

        // 2. Secrets.plist (convenient for development, gitignored)
        if let path = Bundle.main.path(forResource: "Secrets", ofType: "plist"),
           let dict = NSDictionary(contentsOfFile: path),
           let key = dict["OPENAI_API_KEY"] as? String, !key.isEmpty {
            return key
        }

        // 3. Environment variable (CI / Xcode scheme)
        if let key = ProcessInfo.processInfo.environment["OPENAI_API_KEY"], !key.isEmpty {
            return key
        }

        return nil
    }
}

// MARK: - Error Types

enum OpenAIError: LocalizedError {
    case missingAPIKey
    case rateLimited
    case unauthorized
    case serverError(Int)
    case decodingFailed
    case networkUnavailable(Error)

    var errorDescription: String? {
        switch self {
        case .missingAPIKey: "API key not configured"
        case .rateLimited: "Rate limited — try again later"
        case .unauthorized: "Invalid API key"
        case .serverError(let code): "Server error (\(code))"
        case .decodingFailed: "Failed to parse response"
        case .networkUnavailable(let error): "Network error: \(error.localizedDescription)"
        }
    }
}

// MARK: - Message

struct ChatMessage: Encodable {
    let role: String
    let content: String

    static func system(_ content: String) -> ChatMessage { .init(role: "system", content: content) }
    static func user(_ content: String) -> ChatMessage { .init(role: "user", content: content) }
}

// MARK: - Protocol

protocol OpenAIClientProtocol: Sendable {
    func complete(
        messages: [ChatMessage],
        temperature: Double,
        maxTokens: Int,
        jsonMode: Bool
    ) async throws -> String

    func completeStreaming(
        messages: [ChatMessage],
        temperature: Double,
        maxTokens: Int,
        jsonMode: Bool
    ) -> AsyncThrowingStream<String, Error>
}

// MARK: - Implementation

final class OpenAIClient: OpenAIClientProtocol {

    private let session: URLSession

    init(session: URLSession = .shared) {
        self.session = session
    }

    // MARK: - Non-streaming

    func complete(
        messages: [ChatMessage],
        temperature: Double = 0.7,
        maxTokens: Int = 1000,
        jsonMode: Bool = false
    ) async throws -> String {
        let request = try buildRequest(
            messages: messages,
            temperature: temperature,
            maxTokens: maxTokens,
            jsonMode: jsonMode,
            stream: false
        )

        let data: Data
        let response: URLResponse
        do {
            (data, response) = try await session.data(for: request)
        } catch {
            throw OpenAIError.networkUnavailable(error)
        }

        try validateHTTPResponse(response)

        guard
            let json = try? JSONSerialization.jsonObject(with: data) as? [String: Any],
            let choices = json["choices"] as? [[String: Any]],
            let message = choices.first?["message"] as? [String: Any],
            let content = message["content"] as? String
        else {
            throw OpenAIError.decodingFailed
        }

        return content.trimmingCharacters(in: .whitespacesAndNewlines)
    }

    // MARK: - Streaming

    func completeStreaming(
        messages: [ChatMessage],
        temperature: Double = 0.7,
        maxTokens: Int = 1000,
        jsonMode: Bool = false
    ) -> AsyncThrowingStream<String, Error> {
        AsyncThrowingStream { continuation in
            Task {
                do {
                    let request = try buildRequest(
                        messages: messages,
                        temperature: temperature,
                        maxTokens: maxTokens,
                        jsonMode: jsonMode,
                        stream: true
                    )

                    let (bytes, response): (URLSession.AsyncBytes, URLResponse)
                    do {
                        (bytes, response) = try await session.bytes(for: request)
                    } catch {
                        throw OpenAIError.networkUnavailable(error)
                    }

                    try validateHTTPResponse(response)

                    for try await line in bytes.lines {
                        guard line.hasPrefix("data: ") else { continue }
                        let payload = String(line.dropFirst(6))
                        if payload == "[DONE]" { break }

                        guard
                            let data = payload.data(using: .utf8),
                            let json = try? JSONSerialization.jsonObject(with: data) as? [String: Any],
                            let choices = json["choices"] as? [[String: Any]],
                            let delta = choices.first?["delta"] as? [String: Any],
                            let content = delta["content"] as? String
                        else { continue }

                        continuation.yield(content)
                    }

                    continuation.finish()
                } catch {
                    continuation.finish(throwing: error)
                }
            }
        }
    }

    // MARK: - Convenience

    /// Simple one-shot: system prompt + user message → response string.
    func complete(
        system: String,
        user: String,
        temperature: Double = 0.7,
        maxTokens: Int = 1000,
        jsonMode: Bool = false
    ) async throws -> String {
        try await complete(
            messages: [.system(system), .user(user)],
            temperature: temperature,
            maxTokens: maxTokens,
            jsonMode: jsonMode
        )
    }

    // MARK: - Private

    private func buildRequest(
        messages: [ChatMessage],
        temperature: Double,
        maxTokens: Int,
        jsonMode: Bool,
        stream: Bool
    ) throws -> URLRequest {
        guard let apiKey = OpenAIConfig.resolveAPIKey() else {
            throw OpenAIError.missingAPIKey
        }

        guard let url = URL(string: OpenAIConfig.endpoint) else {
            throw OpenAIError.decodingFailed
        }

        var body: [String: Any] = [
            "model": OpenAIConfig.model,
            "messages": messages.map { ["role": $0.role, "content": $0.content] },
            "temperature": temperature,
            "max_tokens": maxTokens
        ]

        if jsonMode {
            body["response_format"] = ["type": "json_object"]
        }

        if stream {
            body["stream"] = true
        }

        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.setValue("Bearer \(apiKey)", forHTTPHeaderField: "Authorization")
        request.timeoutInterval = stream ? 60 : 30
        request.httpBody = try JSONSerialization.data(withJSONObject: body)

        // Uncomment if using a proxy with custom auth header instead of Bearer token:
        // request.setValue(apiKey, forHTTPHeaderField: "X-Proxy-Secret")

        return request
    }

    private func validateHTTPResponse(_ response: URLResponse) throws {
        guard let http = response as? HTTPURLResponse else {
            throw OpenAIError.decodingFailed
        }

        switch http.statusCode {
        case 200: return
        case 401: throw OpenAIError.unauthorized
        case 429: throw OpenAIError.rateLimited
        default: throw OpenAIError.serverError(http.statusCode)
        }
    }
}

// MARK: - JSON Response Helper

extension String {
    /// Strips markdown code fences that models sometimes wrap around JSON responses.
    var strippingCodeFences: String {
        replacingOccurrences(of: "```json", with: "")
            .replacingOccurrences(of: "```", with: "")
            .trimmingCharacters(in: .whitespacesAndNewlines)
    }

    /// Decode this string as JSON into a Decodable type. Handles code fence stripping.
    func decodeJSON<T: Decodable>(as type: T.Type) -> T? {
        guard let data = strippingCodeFences.data(using: .utf8) else { return nil }
        return try? JSONDecoder().decode(type, from: data)
    }
}
