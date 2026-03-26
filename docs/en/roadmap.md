# Budgie 🐦 — Roadmap

🌐 [Version française](../fr/roadmap.md)

This document outlines planned future improvements for Budgie.
Items are grouped by priority and may change as the project evolves.

---

## Short Term

### Bug Fixes & Small Improvements

- [ ] **Envelope color picker** — let users assign a custom color to each envelope directly from the budget view
- [ ] **Amount range in category rules** — add optional min/max amount conditions when creating or editing auto-categorization rules (e.g. only match transactions between −50 € and −5 €)

### Category Spending View

- [ ] New dedicated view showing reconciled ("pointed") spending per category and per group for a selected month
- [ ] Display budget vs. actual breakdown alongside envelope totals
- [ ] Filter by account or date range

### Passive Learning

Improve categorization accuracy over time by learning from user behavior.

- [ ] Propose updating `Payee.auto_category_id` on manual categorization
- [ ] Propose creating a `CategoryRule` from repeated manual assignments
- [ ] Track categorization accuracy metrics

### UX Improvements

- [ ] Transaction search (full-text on payee, memo)
- [ ] Bulk transaction editing (multi-select + assign category)
- [ ] Keyboard shortcuts for common actions

---

## Medium Term

### Transaction View Overhaul

The current transaction list view has become less useful since reconciliation covers most day-to-day workflows. Redesign it around what's still needed:

- [ ] Repurpose as a global search / audit log (full-text, date range, category, account filters)
- [ ] Inline editing of category, memo, and amount directly in the list
- [ ] Bulk actions: assign category, delete, export selection
- [ ] Clear visual distinction between reconciled and unreconciled transactions

### Category Management Improvements

- [ ] Reorder category groups and categories via drag-and-drop
- [ ] Edit category or group name inline
- [ ] Move a category from one group to another
- [ ] **Split** a category into two (redistribute past transactions)
- [ ] **Merge** two categories into one (reassign all transactions)

### Reporting

- [ ] Monthly spending breakdown by category (charts)
- [ ] Income vs. expenses trend over time
- [ ] Budget adherence history (% of envelopes staying positive)
- [ ] Export reports to CSV/PDF

### Multi-currency

- [ ] Support multiple currencies per account
- [ ] Exchange rate management

### Recurring Transactions

- [ ] Define recurring transaction templates (rent, subscriptions, etc.)
- [ ] Auto-generate virtual transactions from recurring schedules
- [ ] Notifications for upcoming recurring transactions

---

## Long Term

### Data & Sync

- [ ] PostgreSQL support as an alternative to SQLite
- [ ] Multi-device sync improvements
- [ ] Data export/import (full backup as JSON/ZIP)

### Advanced Budgeting

- [ ] Savings goals with progress tracking
- [ ] Rollover rules per envelope (capped vs. unlimited)
- [ ] Credit card payment tracking (separate debt envelopes)

### Integrations

- [ ] Bank API integration (Open Banking / PSD2) for automatic imports
- [ ] Notification system (email/push for budget alerts)

---

## Completed

See [CHANGELOG.md](../../CHANGELOG.md) for delivered features.
