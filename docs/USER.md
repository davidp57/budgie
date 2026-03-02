# Budgie 🐦 — User Guide

## Table of Contents

1. [What is Budgie?](#what-is-budgie)
2. [Features](#features)
3. [First Steps](#first-steps)
4. [Managing Accounts](#managing-accounts)
5. [Managing Categories](#managing-categories)
6. [Importing Bank Transactions](#importing-bank-transactions)
7. [Reviewing & Categorizing Transactions](#reviewing--categorizing-transactions)
8. [The Budget (Envelopes)](#the-budget-envelopes)
9. [Virtual Transactions (Forecasts)](#virtual-transactions-forecasts)
10. [Theme & Mobile Installation](#theme--mobile-installation)

---

## What is Budgie?

Budgie is a **self-hosted personal budget management application** that runs entirely on your own server — no third-party cloud service, no subscription fees.

It follows the **envelope budgeting** method: every centime of income is assigned to a spending category before you spend it. When you look at any category, you know immediately how much is left to spend.

---

## Features

| Feature | Description |
|---|---|
| Bank import | Upload CSV, Excel, QIF or OFX files exported from your bank |
| Auto-categorization | Transactions are categorized automatically based on payee history and rules you define |
| Envelope budgeting | Assign a budget to each category each month; track what's available |
| Virtual transactions | Plan future purchases to see their impact on your budget before they happen |
| Transaction history | Filter by account, type (real / forecast) and search |
| Dark / light theme | Switches automatically based on your system preference, or toggle manually |
| Mobile-friendly | Can be added to the home screen of your phone (PWA) |

---

## First Steps

### Accessing the app

Open `http://YOUR_SERVER:8080` in your browser (or `http://localhost:5173` in development mode).

On your first visit, click **Register** to create your account.

### Recommended setup order

1. **Create accounts** — your bank accounts, savings, etc.
2. **Create category groups and categories** — e.g. group *Housing* with categories *Rent*, *Electricity*, *Internet*
3. **Import your first bank file**
4. **Assign your budget** for the current month

---

## Managing Accounts

Go to **Settings → Accounts**.

Each account has:
- A **name** (e.g. "Checking", "Savings")
- An **account type** (checking, savings, credit card…)

Account balances are calculated from the sum of all non-virtual transactions.

> **Tip**: Create one account per real bank account. Do not merge different banks into a single account.

---

## Managing Categories

Go to **Settings → Categories**.

Categories are organized in **groups** (e.g. *Housing*, *Food*, *Transport*).

| Term | Meaning |
|---|---|
| Group | A logical collection of categories (e.g. "Housing") |
| Category | A single spending area (e.g. "Rent") |

### Auto-categorization rules

In **Settings → Rules**, you can define rules to automatically assign a category when a transaction matches a pattern.

Each rule has:
- **Field**: search in the payee name or the memo/description
- **Match type**: contains a word, exact match, or regular expression
- **Category**: the category to assign when the rule matches
- **Priority**: rules with higher priority are evaluated first

Once a transaction is categorized, the payee name is remembered — future transactions from the same payee are categorized automatically.

---

## Importing Bank Transactions

Go to **Import**.

### Step 1 — Upload a file

Select your bank file. Supported formats:
- **CSV** — most banks offer CSV export; columns are detected automatically
- **Excel** (.xlsx / .xls)
- **QIF** — older format, widely supported
- **OFX / OFC** — open exchange format used by many European banks

### Step 2 — Preview

After upload, you see a preview of all detected transactions. Check that:
- Dates, amounts and descriptions look correct
- Categories have been auto-assigned where possible (you can correct them here)

### Deduplication

Budgie computes a unique fingerprint for each transaction (based on date, amount, description). If you import the same file twice, no duplicates are created.

### Forecast matching

If you have created **virtual transactions** (forecasts) that correspond to real transactions in the file, Budgie will suggest linking them automatically. A suggestion appears when:
- The amounts are within 10% of each other
- The dates are within 60 days of each other

Accept the suggestion to mark the forecast as **realized**.

### Step 3 — Confirm

Click **Confirm import**. All transactions are saved; linked forecasts are marked as reconciled.

---

## Reviewing & Categorizing Transactions

Go to **Transactions**.

### Filters

| Filter | Options |
|---|---|
| Account | All accounts or a specific one |
| Type | All / Real only / Forecasts only |

### Assigning a category

Click on the category cell of any transaction to open the category picker. Select the correct category and save.

---

## The Budget (Envelopes)

Go to **Budget**.

### How it works

Each category has three values for the current month:

| Value | Meaning |
|---|---|
| **Budgeted** | The amount you decided to assign to this category this month |
| **Activity** | The total of all transactions (including forecasts) in this category this month |
| **Available** | Budgeted − Activity, carried forward from previous months |

A **positive** Available means you have money left to spend. A **negative** Available means you have overspent.

### To be budgeted

At the top of the budget page, **To be budgeted** shows your total income minus everything you have already assigned to categories. The goal is **zero** — every centime should be assigned somewhere.

### Monthly allocations

Click on the **Budgeted** cell of any category to enter the amount you want to allocate for that month. Changes are saved automatically.

> **Tip**: Forecasts (virtual transactions) reduce the Available amount even before the real transaction happens. This is intentional — it lets you see the true impact of planned spending.

---

## Virtual Transactions (Forecasts)

A **virtual transaction** (or forecast) lets you plan a future purchase and immediately see its impact on your budget.

### Creating a forecast

In the **Transactions** view, click the ⏳ **New forecast** button.

Fill in:
- **Amount** (in euros, e.g. `49.99`)
- **Estimated date**
- **Category**
- **Memo** (optional description)
- **Account** (the account that will be debited)

The forecast appears in your transaction list with an ⏳ icon and a dashed style. Your budget's **Available** amount for that category is immediately reduced.

### When the real transaction arrives

When you import your bank statement and the corresponding real transaction is found, Budgie suggests linking it to the forecast. Accept the suggestion to:
- Mark the forecast as **reconciled** (it disappears from the unlinked list)
- Keep your budget accurate

### Unlinked forecasts

In the Transactions view, filter on **Forecasts** to see all pending (unrealized) forecasts.

---

## Theme & Mobile Installation

### Dark / light theme

Click the ☀️ / 🌙 button in the top-left sidebar to toggle between light and dark themes. Your choice is saved and applied on your next visit.

The theme is also set automatically on first load based on your operating system's preference (dark mode or light mode).

### Add to home screen (PWA)

On mobile (Android / iOS), open Budgie in your browser and use the **Add to Home Screen** option in the browser menu. The app will then open in full-screen mode just like a native app.
