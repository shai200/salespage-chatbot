## Purpose

Defines local publishing of generated sales pages: site folders, Node processes, and sequential localhost ports starting at 3000.

## ADDED Requirements

### Requirement: Sequential local ports for pages

The first published sales page in a studio session SHALL be available at `http://localhost:3000`. Each additional distinct sales page SHALL receive the next unused port (3001, 3002, …). The studio itself MUST remain on port 8080 and MUST NOT share a port with a generated page.

#### Scenario: First page

- **WHEN** the first conversation publishes a page
- **THEN** that page is reachable at `http://localhost:3000`

#### Scenario: Second page

- **WHEN** a second conversation publishes a page while the first remains hosted
- **THEN** the second page is reachable at `http://localhost:3001` and the first remains at `http://localhost:3000`

### Requirement: Stable port per conversation

Rebuilding or iterating on an existing conversation’s page SHALL keep the same port unless that port cannot be rebound, in which case the operator SHALL be shown the new URL in the thread.

#### Scenario: Rebuild keeps the URL

- **WHEN** the operator iterates on a page already hosted at port 3000
- **THEN** the preview and the chat URL continue to use port 3000

### Requirement: Site files on disk

Each published sales page SHALL have its own directory on the local filesystem, isolated from other pages and from the studio application code.

#### Scenario: Two pages are isolated

- **WHEN** two conversations have published pages
- **THEN** each page’s files live in a distinct directory and changing one does not overwrite the other

### Requirement: Pages served independently of the studio UI

Each published page SHALL be served by its own local Node process (or equivalent Node-based static server). An already-running page MUST keep serving without a studio restart. After a studio restart, the studio SHALL restore or respawn page servers from the local registry.

#### Scenario: Open in a new tab

- **WHEN** the operator clicks the chat URL
- **THEN** the sales page loads from its page port even though the studio remains on 8080

#### Scenario: Studio restart

- **WHEN** the studio restarts after pages were published
- **THEN** previously published conversations can be previewed again without the operator manually starting Node

### Requirement: Registry of hosted pages

The system SHALL persist a registry of conversation-to-port and conversation-to-directory mappings on the local machine so the studio can reconnect previews after restart.

#### Scenario: Registry survives restart

- **WHEN** a page was published on port 3001 and the studio restarts
- **THEN** that conversation still maps to port 3001 (or the operator is given an updated URL if the port had to change)
