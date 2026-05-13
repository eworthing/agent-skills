---
name: ios-security-hardening
author: eworthing
description: >-
  Applies input-validation and file-handling safeguards for untrusted data including
  path-traversal prevention, URL scheme/domain allowlisting, multi-source image
  reference resolution, CSV/JSON sanitization, AI prompt sanitization, sandbox
  directory usage, and iOS Data Protection levels. Use when importing files,
  restoring backups, handling URLs or user-provided paths, processing CSV/JSON
  from external sources, or reviewing features that accept external input.
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

HTTP is intentionally allowed alongside HTTPS for image CDN references — some
public image CDNs still serve over HTTP. The domain allowlist remains the
primary security boundary; never relax the allowlist to broaden scheme support.

#### URL Source Resolution (multi-source image references)

When an image reference can be an asset catalog name, bundled asset, local file,
or remote URL (e.g., when importing from CSV/JSON where references may take any
form), resolve the source type at the boundary and branch on it. Asset catalog
and bundled-asset references skip URL validation entirely; remote URLs and local
files go through scheme/domain/path validation.

Supported reference formats:

- `asset://image-name` → asset catalog lookup
- `file://bundle/image-name` → bundled asset catalog
- Scheme-less strings (e.g., `"Sun"`) → asset catalog
- `https://...` / `http://...` → remote URL (scheme + domain allowlist)
- `file:///path/...` → local file (validated against trusted roots)

```swift
enum ImageSource {
    case assetCatalog(String)
    case localFile(URL)
    case remoteURL(URL)
}

func imageSource(from reference: String, allowedDomains: [String]) -> ImageSource? {
    // Asset catalog scheme
    if reference.hasPrefix("asset://") {
        let name = String(reference.dropFirst("asset://".count))
        return name.isEmpty ? nil : .assetCatalog(name)
    }

    // Bundled asset
    if reference.hasPrefix("file://bundle/") {
        let name = String(reference.dropFirst("file://bundle/".count))
        return name.isEmpty ? nil : .assetCatalog(name)
    }

    // Scheme-less → treat as asset catalog name
    if URL(string: reference)?.scheme == nil {
        return reference.isEmpty ? nil : .assetCatalog(reference)
    }

    // URL forms — validate scheme + (for remote) domain
    guard let url = URL(string: reference),
          let scheme = url.scheme?.lowercased() else {
        return nil
    }

    if scheme == "file" {
        // Local file: caller must additionally validate against trusted roots
        return .localFile(url)
    }

    guard ["https", "http"].contains(scheme),
          let host = url.host,
          allowedDomains.contains(where: { host.hasSuffix($0) }) else {
        return nil
    }
    return .remoteURL(url)
}
```

Callers branch on the case and load each source type with the appropriate API
(asset catalog name through the platform image loader, remote/local URLs
through `AsyncImage`):

```swift
if let source = imageSource(from: item.imageRef, allowedDomains: ["cdn.example.com"]) {
    switch source {
    case let .assetCatalog(name):
        if let image = loadAssetCatalogImage(named: name) {
            image.resizable().aspectRatio(contentMode: .fill)
        } else {
            placeholder
        }
    case let .localFile(url), let .remoteURL(url):
        AsyncImage(url: url) { phase in
            switch phase {
            case let .success(image): image.resizable()
            case .failure, .empty: placeholder
            @unknown default: placeholder
            }
        }
    }
} else {
    placeholder
}
```

This pattern protects against three classes of mistake: (1) passing
asset-catalog names to `AsyncImage` (silent failure — no network request, no
image), (2) passing remote URLs to the platform's image catalog loader (silent
failure — name not found), (3) accepting a scheme like `javascript:` or
`data:` (would pass an unvalidated `URL(string:)` check).

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

### Example 2: Multi-Source Image Reference Loading

When image references can be any of: asset catalog name, bundled asset, local
file, or remote URL — branch on source type. See "URL Source Resolution"
section above for the full `imageSource(from:allowedDomains:)` helper.

**Before:**
```swift
// WRONG - blindly trusts string is a URL; silently fails for asset names
AsyncImage(url: URL(string: item.imageRef))
```

**After:**
```swift
if let source = imageSource(from: item.imageRef,
                             allowedDomains: ["cdn.example.com"]) {
    switch source {
    case let .assetCatalog(name):
        if let image = loadAssetCatalogImage(named: name) {
            image.resizable().aspectRatio(contentMode: .fill)
        } else {
            placeholder
        }
    case let .localFile(url), let .remoteURL(url):
        AsyncImage(url: url) { phase in
            switch phase {
            case let .success(image): image.resizable()
            case .failure, .empty: placeholder
            @unknown default: placeholder
            }
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
