/**
 * TypeScript interfaces mirroring the backend Pydantic schemas.
 * Monetary amounts are always in integer centimes (e.g. 1050 = 10.50€).
 */

// ── Auth ──────────────────────────────────────────────────────────

export interface LoginResponse {
  access_token: string
  token_type: string
}

// ── Accounts ─────────────────────────────────────────────────────

export type AccountType = 'checking' | 'savings' | 'credit' | 'cash'

export interface Account {
  id: number
  name: string
  account_type: AccountType
  on_budget: boolean
  created_at: string
}

export interface AccountCreate {
  name: string
  account_type: AccountType
  on_budget: boolean
}

export interface AccountUpdate {
  name?: string
  account_type?: AccountType
  on_budget?: boolean
}

// ── Category groups & categories ─────────────────────────────────

export interface CategoryGroup {
  id: number
  name: string
  sort_order: number
}

export interface Category {
  id: number
  group_id: number
  name: string
  sort_order: number
  hidden: boolean
}

export interface CategoryGroupWithCategories extends CategoryGroup {
  categories: Category[]
}

// ── Payees ───────────────────────────────────────────────────────

export interface Payee {
  id: number
  name: string
}

// ── Transactions ─────────────────────────────────────────────────

export type ClearedStatus = 'uncleared' | 'cleared' | 'reconciled'

export interface Transaction {
  id: number
  account_id: number
  date: string // YYYY-MM-DD
  payee_id: number | null
  category_id: number | null
  amount: number // centimes
  memo: string | null
  cleared: ClearedStatus
  is_virtual: boolean
  virtual_linked_id: number | null
  income_for_month: string | null // YYYY-MM — N+1 mode: counts income toward this month
  import_hash: string | null
  created_at: string
}

export interface TransactionCreate {
  account_id: number
  date: string
  payee_id?: number | null
  category_id?: number | null
  amount: number
  memo?: string | null
  cleared?: ClearedStatus
  is_virtual?: boolean
  virtual_linked_id?: number | null
}

export interface TransactionUpdate {
  category_id?: number | null
  memo?: string | null
  cleared?: ClearedStatus
  payee_id?: number | null
}

// ── Budget ───────────────────────────────────────────────────────

export interface CategoryRef {
  id: number
  name: string
  group_name: string
}

export interface EnvelopeLine {
  envelope_id: number
  envelope_name: string
  rollover: boolean
  categories: CategoryRef[]
  budgeted: number // centimes
  activity: number // centimes
  available: number // centimes
}

export interface MonthBudget {
  month: string // YYYY-MM
  to_be_budgeted: number // centimes
  total_available: number // centimes — sum of all envelope available amounts
  envelopes: EnvelopeLine[]
}

export interface BudgetLineInput {
  envelope_id: number
  budgeted: number // centimes
}

export interface IncomeProposal {
  transaction_id: number
  date: string // YYYY-MM-DD (from M-1)
  amount: number // centimes (always positive)
  memo: string | null
  account_id: number
}

export interface IncomeProposalsResponse {
  month: string // YYYY-MM
  previous_month: string // YYYY-MM
  threshold_centimes: number
  proposals: IncomeProposal[]
}

export interface UserPreferences {
  /**
   * 'n1' = N+1 (default): income received in M-1 is assigned to current month
   *   without creating virtual transactions.
   * 'n' = Prévisionnel: a virtual income transaction is created in the current
   *   month for income expected before it arrives.
   */
  budget_mode: 'n1' | 'n'
}

// ── Envelopes ────────────────────────────────────────────────────

export interface Envelope {
  id: number
  name: string
  rollover: boolean
  sort_order: number
  categories: CategoryRef[]
}

export interface EnvelopeCreate {
  name: string
  rollover?: boolean
  sort_order?: number
  category_ids?: number[]
}

export interface EnvelopeUpdate {
  name?: string
  rollover?: boolean
  sort_order?: number
  category_ids?: number[]
}

// ── Import ───────────────────────────────────────────────────────

export interface ImportedTransaction {
  date: string        // YYYY-MM-DD
  amount: number      // centimes
  description: string
  payee_name: string | null
  reference: string | null
  import_hash: string
  virtual_linked_id?: number | null   // set by user during preview matching
}

export interface ParsePreviewResponse {
  transactions: ImportedTransaction[]
  total: number
}

export interface ImportResult {
  imported: number
  duplicates: number
}

// ── Category rules ───────────────────────────────────────────────

export interface CategoryRule {
  id: number
  pattern: string
  category_id: number
  priority: number
}

// ── Helpers ──────────────────────────────────────────────────────

/** Format centimes to display string (e.g. 10050 → "100,50 €") */
export function formatAmount(centimes: number): string {
  return (centimes / 100).toLocaleString('fr-FR', {
    style: 'currency',
    currency: 'EUR',
  })
}
