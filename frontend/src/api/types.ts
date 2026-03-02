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

export interface EnvelopeLine {
  category_id: number
  category_name: string
  group_id: number
  group_name: string
  budgeted: number // centimes
  activity: number // centimes
  available: number // centimes
}

export interface MonthBudget {
  month: string // YYYY-MM
  to_be_budgeted: number // centimes
  envelopes: EnvelopeLine[]
}

export interface BudgetLineInput {
  category_id: number
  budgeted: number // centimes
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
