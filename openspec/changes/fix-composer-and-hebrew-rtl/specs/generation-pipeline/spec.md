## ADDED Requirements

### Requirement: Hebrew sales pages are right-to-left

When a generated sales page’s language is Hebrew, the published page SHALL use right-to-left layout: the root document MUST set `lang="he"` and `dir="rtl"`. Headlines, body copy, and section order SHALL follow RTL reading (start/end alignment, not LTR-forced left alignment). Non-Hebrew pages SHALL remain left-to-right with an appropriate `lang` (default `en`).

#### Scenario: Hebrew page is RTL

- **WHEN** the operator requests a Hebrew sales page or the generated page copy is in Hebrew
- **THEN** the published `index.html` has `lang="he"` and `dir="rtl"` and the visible layout reads right-to-left

#### Scenario: English page stays LTR

- **WHEN** the generated page copy is English
- **THEN** the published page is left-to-right and MUST NOT set `dir="rtl"`
