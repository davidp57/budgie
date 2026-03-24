# Budgie 🐦 — Roadmap

🌐 [Version française](../fr/roadmap.md)

This document outlines planned future improvements for Budgie.
Items are grouped by priority and may change as the project evolves.

---

## Short Term

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
