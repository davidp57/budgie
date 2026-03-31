# Budgie 🐦 — Getting Started: Your First Week

🌐 [Version française](../../fr/tutorials/usage.md)

> **Goal**: discover Budgie at your own pace, in two stages.

This tutorial is split into **two parts**:

1. **Quick start (10 min)** — set up your budget without any bank account. Perfect for understanding the core of the app.
2. **Going further** — connect your bank accounts, import transactions and reconcile.

You can use Budgie perfectly well with just part one.

---

## Part 1 — Budget in 10 Minutes

### Step 1 — Create Your Categories

**Categories** describe where your money goes. They are organized in **groups**.

1. Go to **Settings** (⚙️) → **Categories**
2. Click **Add group** and name it — e.g. `Housing`
3. Inside the group, click **Add category** — e.g. `Rent`, `Electricity`, `Internet`
4. Repeat for your main spending areas

> 📸 *Screenshot needed — categories page with one group expanded and a few categories visible*

**Suggested groups to get you started:**

| Group | Example categories |
|---|---|
| 🏠 Housing | Rent, Electricity, Internet, Water |
| 🍎 Food | Groceries, Restaurants |
| 🚗 Transport | Fuel, Public transport, Car insurance |
| 🏥 Health | Pharmacy, Doctor |
| 🎬 Leisure | Streaming, Cinema, Books |
| 💳 Financial | Savings, Loan repayment |

> 💡 Don't over-engineer it. Start with 5–8 categories and refine over time.

---

### Step 2 — Create Your Envelopes

An **envelope** (sometimes called a **drawer** in the interface) groups one or more categories into a single budget area. The envelope is what you budget against — not individual categories.

1. Go to **Settings** → **Envelopes**
2. Click **Add envelope**
3. Fill in:
   - **Name**: e.g. `Housing`
   - **Emoji**: e.g. 🏠 (optional)
   - **Type**: choose according to the use case (see below)
   - **Categories**: assign the categories that belong to this envelope — they can come from different groups (e.g. `Rent` from *Housing* + `Car insurance` from *Transport*)
4. Save and repeat for each area

> 📸 *Screenshot needed — add envelope form with Name, Emoji, Type and Categories fields visible*

> 💡 One envelope can cover multiple categories from different groups. A category can only belong to one envelope. An envelope with no categories is perfectly valid — useful for tracking a manually managed budget without importing transactions.

#### Envelope types — real-life examples

Choosing the right envelope type makes a real difference over time.

**🔁 Monthly (no rollover)**

The default type. The envelope budget resets to zero each month, regardless of what was left over.

> *Example: your **Groceries** envelope is set to £300/month. In January you spend £280. In February, the envelope resets to £300. The unused £20 from January is gone.*

Best for: rent, subscriptions, groceries, restaurants — anything regular and predictable.

**📦 With rollover (progressive saving)**

Unspent balance **accumulates** from month to month. The envelope grows gradually.

> *Example: your **Car** envelope is set to £50/month. In June (month 6), your service bill is £280. You have accumulated 6 × £50 = £300 — the bill is covered, no stress.*
>
> *Another example: a **Summer Holiday** envelope at £100/month from January to July → £700 available in August to travel worry-free.*

Best for: car maintenance, holidays, Christmas gifts, annual insurance — anything irregular or seasonal.

**💵 Manual tracking (no categories)**

For a budget you top up manually and simply want to track spending on, without linking it to imported transactions.

> *Example: your **Cash drawer**. You add £50 at the start of the month (via a manual transaction or an adjustment). You then log each cash purchase directly in this envelope. The **Available** balance reflects what you have left in your pocket.*

This envelope needs no categories: it lives outside the bank import flow.

---

### Step 3 — Set Your Monthly Budget

Now that your envelopes exist, assign how much you want to spend in each one this month.

1. Go to **Budget** (💰)
2. For each envelope card, click the **Budgeted** amount and type your target
3. Watch the **"To be budgeted"** counter at the top — aim for zero: every pound should have a job

> 📸 *Screenshot needed — Budget page with several envelope cards and the "To be budgeted" counter visible at the top*

> 💡 Start with fixed expenses (rent, subscriptions) then allocate the rest to variable ones.

---

### Step 4 — Enter Your First Expense

No bank account needed to record a spending. Use **Quick Expense**:

1. Go to **Budget** (💰) and tap any envelope card
2. The **Quick Expense** sheet opens pre-filled with that envelope
3. Type the amount, add a memo if you like, and submit

The transaction is saved instantly and the envelope's **Available** amount updates immediately.

> 📸 *Screenshot needed — quick expense sheet open on an envelope, amount field in the foreground*

> 💡 For a purchase with no matching envelope, use the **"Off-budget expense"** banner at the bottom of the Budget page.

---

### Day-to-Day Usage (Without Bank Accounts)

Once set up, your routine is simple:

| Task | Where | Frequency |
|---|---|---|
| Record an expense | Budget page → tap envelope | As they happen |
| Check your budget | Budget page | Anytime |
| Review spending | Expenses → Dashboard | Weekly |
| Adjust allocations | Budget page → edit Budgeted | Monthly |

That's it. You can stop here and use Budgie purely as a budget tracker.

---

## Part 2 — Going Further with Your Bank Accounts

Connecting your accounts lets you import statements and automatically compare what you budgeted with what you actually spent.

### Step 5 — Create Your Bank Accounts

An **account** represents a real bank account (checking, savings, credit card…).

1. Go to **Settings** (⚙️) → **Accounts**
2. Click **Add account**
3. Fill in:
   - **Name**: e.g. `Checking`, `Savings`, `Visa`
   - **Type**: checking, savings, credit card, or cash
4. Save

> 📸 *Screenshot needed — accounts list with 2–3 accounts created and their balances*

> 💡 Create one account per real bank account. You can add more later.

---

### Step 6 — Import Your Bank Transactions

1. Export a transaction file from your bank's website:
   - Most banks offer a "Download transactions" or "Export CSV/QIF/OFX" option
   - Supported formats: **CSV**, **Excel (.xlsx)**, **QIF**, **OFX**
2. In Budgie, go to **Settings** → **Import**
3. Drag-and-drop your file (or click to browse)
4. **Preview** the import — check that dates and amounts look correct
5. Click **Confirm import**

> 📸 *Screenshot needed — import preview screen with a transaction table and the "Confirm import" button visible*

Budgie automatically:
- **Deduplicates** — importing the same file twice is safe, no duplicates created
- **Auto-categorizes** — if a payee was categorized before, it's assigned automatically

---

### Step 7 — Categorize Unrecognized Transactions

After import, some transactions may not have a category yet.

1. Go to **Settings** → **Reconciliation** (or open the import results)
2. For each unrecognized transaction, pick a category
3. Budgie asks if you want to **save a rule** — say yes for recurring payees (supermarket, subscription…)

> 📸 *Screenshot needed — reconciliation interface with a transaction selected and the category picker open*

Next import, those payees will be categorized automatically.

---

## Tips

- **The goal is zero** — "To be budgeted" at zero means every pound has a job.
- **Rollover for irregular expenses** — enable rollover on envelopes like "Car" or "Holidays" and let them accumulate over months.
- **Presets for recurring expenses** — create a preset for your daily coffee or weekly market run; one tap fills the form.
- **PWA on mobile** — add Budgie to your home screen for a native app feel (browser → "Add to Home Screen").

---

## Reference

For full details on every feature, see the [User Guide](../user-guide.md).

---

☕ Enjoying Budgie? Consider [buying me a coffee](https://buymeacoffee.com/veaf_zip) — it helps a lot!
