---
name: ios-security-hardening
author: eworthing
description: >-
  Applies input-validation and file-handling safeguards for untrusted data. Relevant
  when importing files, restoring backups, handling URLs or user-provided paths, or
  reviewing features that accept external input.
allowed-tools:
  - Read
  - Write
  - Edit
  - Glob
  - Grep
  - Bash
---

# Security Hardening

## Purpose

Apply security best practices when handling user input, file operations, URLs, and external data.

## When to Use This Skill

Use this skill when:
- Handling user-provided file paths or URLs
- Importing data from external sources (CSV, JSON)
- Writing files to disk
- Processing user input for AI prompts
- User says "security review", "validate input", "check for vulnerabilities"

Do NOT use this skill when:
- Working with hardcoded internal data only
- Pure UI layout changes
- Test fixtures with controlled data

## Workflow

### Step 1: Identify Attack Surfaces

```bash
# Find file write operations
grep -rn "write\|FileManager\|Data.*write" --include="*.swift" Sources/

# Find URL handling
grep -rn "URL(string\|URLSession\|URLRequest" --include="*.swift" Sources/

# Find user input processing
grep -rn "TextField\|textField\|userInput" --include="*.swift" Sources/

# Find import/parsing code
grep -rn "JSONDecoder\|CSV\|parse" --include="*.swift" Sources/
```

### Step 2: Apply Security Patterns

#### Path Traversal Prevention

```swift
// WRONG - vulnerable to path traversal
func writeFile(name: String, data: Data) throws {
    let path = documentsDirectory.appendingPathComponent(name)
    try data.write(to: path)
}

// CORRECT - validate path containment
func writeFile(name: String, data: Data) throws {
    let sanitizedName = name
        .replacingOccurrences(of: "..", with: "")
        .replacingOccurrences(of: "/", with: "_")

    let path = documentsDirectory.appendingPathComponent(sanitizedName)

    // Verify path is within allowed directory
    guard path.standardizedFileURL.path.hasPrefix(documentsDirectory.path) else {
        throw SecurityError.pathTraversal
    }

    try data.write(to: path)
}
```

#### URL Validation

```swift
// WRONG - accepts any URL
func loadImage(from urlString: String) async throws -> Image {
    guard let url = URL(string: urlString) else { throw URLError.invalid }
    // ...
}

// CORRECT - enforce scheme allowlist and domain allowlist
func loadImage(from urlString: String) async throws -> Image {
    guard let url = URL(string: urlString),
          let scheme = url.scheme?.lowercased(),
          ["https", "http"].contains(scheme),
          isAllowedDomain(url.host) else {
        throw SecurityError.invalidURL
    }
    // ...
}

private func isAllowedDomain(_ host: String?) -> Bool {
    guard let host = host else { return false }
    let allowedDomains = ["example.com", "cdn.example.com"]
    return allowedDomains.contains { host.hasSuffix($0) }
}
```

#### CSV/Input Sanitization

```swift
// WRONG - direct use of CSV values
func importCSV(_ data: String) -> [Item] {
    let rows = data.components(separatedBy: "\n")
    return rows.map { Item(name: $0) }
}

// CORRECT - sanitize input
func importCSV(_ data: String) -> [Item] {
    let rows = data.components(separatedBy: "\n")
    return rows.compactMap { row in
        let sanitized = sanitizeCSVField(row)
        guard !sanitized.isEmpty else { return nil }
        return Item(name: sanitized)
    }
}

private func sanitizeCSVField(_ field: String) -> String {
    field
        .trimmingCharacters(in: .whitespacesAndNewlines)
        .replacingOccurrences(of: "\"", with: "'")
        .prefix(1000)  // Length limit
        .description
}
```

#### File Format Defense

```swift
// CSV imports: Strip UTF-8 BOM (U+FEFF) that Excel prepends
// Applied at BOTH file-read level and parser level for defense-in-depth
let cleaned = csvString.hasPrefix("\u{FEFF}") ? String(csvString.dropFirst()) : csvString
```

**Checklist for file format parsing:**
- [ ] Strip UTF-8 BOM before parsing
- [ ] Normalize line endings (`\r\n` -> `\n`)
- [ ] Validate encoding is UTF-8

#### AI Prompt Sanitization

When passing user input to AI/LLM APIs, constrain length and strip
control-like sequences. This isn't bulletproof (prompt injection is an
open problem), but it raises the bar:

```swift
// WRONG - user input directly in prompt
func generatePrompt(userInput: String) -> String {
    "Generate items about: \(userInput)"
}

// BETTER - sanitize and constrain
func generatePrompt(userInput: String) -> String {
    let sanitized = userInput
        .prefix(500)
        .description
        .trimmingCharacters(in: .whitespacesAndNewlines)

    return "Generate items about: \(sanitized)"
}
```

#### Size Limits

```swift
// WRONG - unbounded input
func parseJSON(_ data: Data) throws -> Model {
    try JSONDecoder().decode(Model.self, from: data)
}

// CORRECT - enforce size limit
func parseJSON(_ data: Data) throws -> Model {
    let maxSize = 50 * 1024 * 1024  // 50MB
    guard data.count <= maxSize else {
        throw SecurityError.payloadTooLarge
    }
    return try JSONDecoder().decode(Model.self, from: data)
}
```

#### Secret & Credential Handling

```swift
// WRONG -- API key persisted in model object
struct Beacon {
    let url: URL  // Contains ?key=SECRET -- persisted to disk
}

// CORRECT -- build authenticated URL at request time
struct Beacon {
    let gifId: String  // Only store resource identifier
}

func sendBeacon(_ beacon: Beacon) async throws {
    var components = URLComponents()
    components.scheme = "https"
    components.host = "api.example.com"
    components.path = "/v1/gifs/\(beacon.gifId)"
    components.queryItems = [URLQueryItem(name: "key", value: apiKey)]
    guard let url = components.url else { throw SecurityError.invalidURL }
    // ...
}
```

**Rules:**
- Never persist API keys or tokens in model/state objects
- Build authenticated URLs at request time using `URLComponents` (Apple's RFC 3986-compliant URL builder)
- Store only resource identifiers -- resolve to full URL at send time
- Use `URLComponents` instead of string interpolation to prevent injection

### Step 3: Use Sandbox Directories

```swift
// WRONG - writing to /tmp
let tempPath = "/tmp/myfile.txt"

// CORRECT - use sandbox temp directory
let tempURL = FileManager.default.temporaryDirectory
    .appendingPathComponent(UUID().uuidString)
    .appendingPathExtension("txt")
```

### Step 4: iOS Data Protection

For iOS apps, ensure sensitive files use appropriate data protection levels:

```swift
// Write with data protection
try data.write(to: fileURL, options: .completeFileProtection)
```

Available protection levels:
- `.completeFileProtection` -- accessible only when device is unlocked
- `.completeFileProtectionUnlessOpen` -- accessible once opened while unlocked
- `.completeFileProtectionUntilFirstUserAuthentication` -- accessible after first unlock (default)

### Step 5: Security Audit Checklist

Before merging code that handles external data:

- [ ] Path traversal prevented (no `..` in paths)
- [ ] URLs validated (scheme allowlisted, domains allowlisted)
- [ ] Input length constrained
- [ ] Special characters sanitized
- [ ] Size limits enforced
- [ ] Sandbox directories used for temp files
- [ ] No secrets in logs or error messages

## Common Mistakes to Avoid

1. **Trusting file paths from user** -- Always validate containment
2. **Accepting unvalidated URLs** -- Enforce scheme + domain allowlists
3. **Unbounded input** -- Add length/size limits
4. **Direct string interpolation** -- Sanitize first
5. **Broad entitlements** -- Request minimum needed

## Examples

### Example 1: Export File Write

**Before:**
```swift
func export(to filename: String) throws {
    let url = documentsDir.appendingPathComponent(filename)
    try data.write(to: url)
}
```

**After:**
```swift
func export(to filename: String) throws {
    // Sanitize filename
    let safe = filename
        .replacingOccurrences(of: "..", with: "")
        .replacingOccurrences(of: "/", with: "_")
        .replacingOccurrences(of: "\\", with: "_")

    let url = documentsDir.appendingPathComponent(safe)

    // Verify containment
    let resolved = url.standardizedFileURL
    guard resolved.path.hasPrefix(documentsDir.path) else {
        throw ExportError.invalidPath
    }

    try data.write(to: url)
}
```

### Example 2: Generic Image URL Loading

**Before:**
```swift
// WRONG - doesn't validate URL source
AsyncImage(url: URL(string: item.imageUrl))
```

**After:**
```swift
// CORRECT - validate URL scheme and domain before loading
func validatedImageURL(from urlString: String) -> URL? {
    guard let url = URL(string: urlString),
          let scheme = url.scheme?.lowercased(),
          ["https", "http"].contains(scheme),
          isAllowedDomain(url.host) else {
        return nil
    }
    return url
}

if let url = validatedImageURL(from: item.imageUrl) {
    AsyncImage(url: url) { phase in
        switch phase {
        case let .success(image): image.resizable()
        case .failure, .empty: placeholder
        @unknown default: placeholder
        }
    }
} else {
    placeholder
}
```

## References

- OWASP Mobile Security Testing Guide
- Apple App Sandbox documentation

## Constraints

- Always sanitize user-provided paths
- Always validate URLs before loading
- Always use sandbox temp directories
- Never log sensitive data
- Size limits on all external data
