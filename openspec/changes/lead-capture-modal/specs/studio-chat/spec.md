## ADDED Requirements

### Requirement: Operator can set a next URL on the conversation

The studio SHALL accept an optional next URL during intake or a later follow-up (labeled field or a clear “send them to …” request). That value SHALL be stored on the conversation and published onto the page. A follow-up that only changes copy MUST keep the existing next URL unless the operator changes it. The studio MUST reject `javascript:` and other non-http(s) destinations.

#### Scenario: Brief includes a next URL

- **WHEN** the operator’s brief includes a next URL such as `https://cal.example/book`
- **THEN** that conversation stores the URL and the generated page redirects there after a successful lead

#### Scenario: Follow-up changes only the headline

- **WHEN** a next URL is already stored and the operator asks only to punch up the headline
- **THEN** the rebuilt page still uses the same next URL

#### Scenario: Unsafe destination is rejected

- **WHEN** the operator supplies a `javascript:` URL as the next URL
- **THEN** the studio does not publish that value onto the page
