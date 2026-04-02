/**
 * TypeScript interfaces mirroring the backend Pydantic schemas.
 * Monetary amounts are always in integer centimes (e.g. 1050 = 10.50€).
 */

// ── Auth ──────────────────────────────────────────────────────────

export interface LoginResponse {
  access_token: string
  token_type: string
  needs_encryption_setup: boolean
  is_encrypted: boolean
  username?: string
}

export interface WebAuthnCredential {
  id: number
  name: string | null
  created_at: string
}

export interface WebAuthnOptions {
  options: Record<string, unknown>
  challenge_token?: string
}

// ── Accounts ─────────────────────────────────────────────────────

export type AccountType = 'checking' | 'savings' | 'credit' | 'cash' | 'wallet'

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

export type TransactionStatus = 'planned' | 'real' | 'reconciled'

export interface TransactionLinked {
  id: number
  memo: string | null
  amount: number // centimes
  date: string // YYYY-MM-DD
}

export interface Transaction {
  id: number
  account_id: number
  date: string // YYYY-MM-DD
  payee_id: number | null
  category_id: number | null
  envelope_id: number | null
  amount: number // centimes
  memo: string | null
  status: TransactionStatus
  income_for_month: string | null // YYYY-MM
  import_hash: string | null
  reconciled_with_id: number | null
  linked_transaction: TransactionLinked | null
  created_at: string
}

export interface TransactionCreate {
  account_id: number
  date: string
  payee_id?: number | null
  category_id?: number | null
  envelope_id?: number | null
  amount: number
  memo?: string | null
  status?: TransactionStatus
}

export interface TransactionUpdate {
  date?: string | null
  category_id?: number | null
  envelope_id?: number | null
  amount?: number | null
  memo?: string | null
  status?: TransactionStatus
  payee_id?: number | null
}

// ── Budget ───────────────────────────────────────────────────────

export interface CategoryRef {
  id: number
  name: string
  group_name: string
}

export type EnvelopeType = 'regular' | 'cumulative' | 'reserve'

export interface EnvelopeLine {
  envelope_id: number
  envelope_name: string
  envelope_type: EnvelopeType
  emoji: string
  color_index: number | null
  rollover: boolean
  target_amount: number | null
  categories: CategoryRef[]
  budgeted: number // centimes
  activity: number // centimes
  available: number // centimes
  expense_count: number
  is_budget_inherited: boolean // true if budgeted comes from previous month (no explicit allocation)
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

export type EnvelopePeriod = 'weekly' | 'monthly' | 'quarterly' | 'yearly'

export interface Envelope {
  id: number
  name: string
  emoji: string
  color_index: number | null
  rollover: boolean
  sort_order: number
  envelope_type: EnvelopeType
  period: EnvelopePeriod
  target_amount: number | null
  stop_on_target: boolean
  categories: CategoryRef[]
}

export interface EnvelopeCreate {
  name: string
  emoji?: string
  color_index?: number | null
  rollover?: boolean
  sort_order?: number
  category_ids?: number[]
  envelope_type?: EnvelopeType
  period?: EnvelopePeriod
  target_amount?: number | null
  stop_on_target?: boolean
}

export interface EnvelopeUpdate {
  name?: string
  emoji?: string
  color_index?: number | null
  rollover?: boolean
  sort_order?: number
  category_ids?: number[]
  envelope_type?: EnvelopeType
  period?: EnvelopePeriod
  target_amount?: number | null
  stop_on_target?: boolean
}

// ── Import ───────────────────────────────────────────────────────

export interface ImportedTransaction {
  date: string        // YYYY-MM-DD
  amount: number      // centimes
  description: string
  payee_name: string | null
  reference: string | null
  import_hash: string
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
  user_id: number
  pattern: string
  match_field: 'payee' | 'memo'
  match_type: 'contains' | 'exact' | 'regex'
  category_id: number
  priority: number
  transaction_type: 'any' | 'debit' | 'credit'
  min_amount: number | null
  max_amount: number | null
}

export interface CategoryRuleCreate {
  pattern: string
  match_field: 'payee' | 'memo'
  match_type: 'contains' | 'exact' | 'regex'
  category_id: number
  priority?: number
  transaction_type?: 'any' | 'debit' | 'credit'
  min_amount?: number | null
  max_amount?: number | null
}

// ── Reconciliation ───────────────────────────────────────────────

export interface BankTx {
  id: number
  date: string // YYYY-MM-DD
  label: string
  amount: number // centimes
  import_hash: string
  rule_pattern: string | null
}

export interface ReconciliationExpense {
  id: number
  date: string // YYYY-MM-DD
  label: string
  amount: number // centimes
  category_id: number | null
  category_name: string | null
  envelope_id: number | null
  envelope_name: string | null
  memo: string | null
  status: TransactionStatus
}

export interface ReconciliationLink {
  bank_tx_id: number
  expense_id: number
  created_rule?: CategoryRule | null
}

export interface ReconciliationSuggestion {
  bank_tx: BankTx
  expense: ReconciliationExpense
  score: number
}

export interface RuleMatch {
  bank_tx: BankTx
  category_id: number
  category_name: string | null
}

export interface ReconciliationView {
  account_id: number
  month: string // YYYY-MM
  bank_txs: BankTx[]
  expenses: ReconciliationExpense[]
  links: ReconciliationLink[]
  suggestions: ReconciliationSuggestion[]
  rule_matches: RuleMatch[]
}

export type RuleAmountMode = 'none' | 'exact' | 'percent'
export type RuleTransactionType = 'any' | 'debit' | 'credit'

export interface LinkRequest {
  bank_tx_id: number
  expense_id: number
  adjust_amount?: boolean
  memo?: string | null
  rule_transaction_type?: RuleTransactionType
  rule_amount_mode?: RuleAmountMode
  rule_amount_tolerance_pct?: number
  skip_rule?: boolean
}

export interface ClotureRequest {
  account_id: number
  month: string // YYYY-MM
}

export interface ClotureResponse {
  linked_count: number
  total_bank_txs: number
  total_expenses: number
  reconciled_count: number
}

// ── Helpers ──────────────────────────────────────────────────────

/** Format centimes to display string (e.g. 10050 → "100,50 €") */
export function formatAmount(centimes: number): string {
  return (centimes / 100).toLocaleString('fr-FR', {
    style: 'currency',
    currency: 'EUR',
  })
}
