## Purpose

Limits each signed-in operator to three free sales pages, collects a card through Stripe before a fourth page, and bills each extra page once a year after its first year.

## ADDED Requirements

### Requirement: Three pages need no payment method

A signed-in user with fewer than three pages SHALL be able to create and publish the next page without entering a card. The first three pages belonging to that user MUST remain free (no Stripe charge for those three).

#### Scenario: First three pages

- **WHEN** a user who has zero, one, or two pages creates another page
- **THEN** the studio creates it without asking for a card

#### Scenario: Free pages are never invoiced

- **WHEN** a year has passed since any of the user’s first three pages were published
- **THEN** Stripe MUST NOT invoice those three pages

### Requirement: A fourth page requires a card on file

When the user already has three pages and has no Stripe payment method, the studio SHALL refuse to create a fourth page and SHALL prompt them to enter card details via Stripe. After a payment method is stored, they MAY create further pages. Each page beyond the first three SHALL be an extra page.

#### Scenario: Fourth page blocked without a card

- **WHEN** a user who already has three pages and no payment method tries to create another page
- **THEN** the studio does not create the page and asks them to enter card details via Stripe

#### Scenario: Card unlocks the fourth page

- **WHEN** that user stores a payment method through Stripe and then creates a page
- **THEN** the studio creates the fourth page

### Requirement: Extra pages are free for one year then billed annually

Each extra page SHALL start a twelve-month free period at first successful publish. After that period the user SHALL be charged once per year per extra page, using the configured Stripe price. The studio MUST NOT charge at card collection time.

#### Scenario: Card stored, no immediate charge

- **WHEN** the user submits card details so they can create a fourth page
- **THEN** no charge is made at that moment

#### Scenario: First extra-page invoice

- **WHEN** twelve months have passed since an extra page’s first publish and the subscription is in good standing
- **THEN** Stripe invoices the configured annual price for that page

#### Scenario: Two extra pages are two bills

- **WHEN** a user has five pages (three free and two extra) and both extra pages have passed their free year
- **THEN** they are billed separately for each extra page at the annual price

### Requirement: Failed extra-page renewal unpublishes after grace

If an extra page’s annual invoice is not paid, the studio SHALL keep serving that page through a seven-day grace period, then unpublish it until payment succeeds. Free pages MUST stay published when an extra page’s payment fails.

#### Scenario: Grace then unpublish

- **WHEN** an extra page’s renewal invoice remains unpaid through seven days
- **THEN** visitor requests for that slug no longer receive the sales page

#### Scenario: Payment restores the page

- **WHEN** the overdue invoice for that extra page is later paid
- **THEN** the same slug is served again without regenerating the page

#### Scenario: Free pages survive a failed extra invoice

- **WHEN** an extra page’s invoice fails
- **THEN** the user’s first three pages remain publicly served

### Requirement: Billing status is visible in the studio

A signed-in user SHALL be able to see how many of the three free pages they have used and whether a payment method is on file. When create is blocked for billing, the studio SHALL say that a card is required.

#### Scenario: Quota on the signed-in user

- **WHEN** a user with two pages asks for billing status
- **THEN** the response shows two of three free pages used and that a card is not required yet
