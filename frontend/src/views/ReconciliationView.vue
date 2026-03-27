<!--
  ReconciliationView — Pointage bancaire
  Split-pane (desktop + landscape mobile) / tab+swipe (portrait mobile).
  Bank transactions on the left, budget expenses on the right.
  Suggestions are auto-computed from backend scoring (GET /api/reconciliation/view).
-->
<script setup lang="ts">
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from 'vue'
import { listAccounts } from '@/api/accounts'
import { listCategoryGroups } from '@/api/categories'
import {
  cloture as apiCloture,
  createLink,
  deleteLink,
  getReconciliationView,
} from '@/api/reconciliation'
import { listRules } from '@/api/categoryRules'
import { categorizeSingle } from '@/api/categorize'
import { createTransaction, deleteTransaction } from '@/api/transactions'
import ImportModal from '@/components/ImportModal.vue'
import RulesModal from '@/components/RulesModal.vue'
import CategoryPicker from '@/components/CategoryPicker.vue'
import { useToastStore } from '@/stores/toast'
import {
  formatAmount,
  type Account,
  type BankTx,
  type Category,
  type CategoryGroupWithCategories,
  type ClotureResponse,
  type LinkRequest,
  type ReconciliationExpense,
  type ReconciliationLink,
  type ReconciliationSuggestion,
  type ReconciliationView,
  type RuleAmountMode,
  type RuleMatch,
  type RuleTransactionType,
} from '@/api/types'

// ── Responsive ────────────────────────────────────────────────────
const mqlPortrait = window.matchMedia('(max-width: 767px) and (orientation: portrait)')
const isPortrait = ref(mqlPortrait.matches)

// ── Card background colors ────────────────────────────────────────
// Soft pastel palette for expense tiles, cycled by category_id
const EXPENSE_PASTELS = [
  'rgba(254,215,170,0.28)',  // orange
  'rgba(187,247,208,0.28)',  // green
  'rgba(196,181,253,0.28)',  // purple
  'rgba(253,224,160,0.28)',  // amber
  'rgba(167,243,208,0.28)',  // emerald
  'rgba(199,210,254,0.28)',  // indigo
  'rgba(252,165,165,0.28)',  // red
  'rgba(134,239,172,0.28)',  // lime
  'rgba(249,168,212,0.28)',  // pink
  'rgba(103,232,249,0.28)',  // cyan
]
const EXPENSE_DEFAULT_BG = 'rgba(148,163,184,0.18)'
const BANK_BG = 'rgba(125,211,252,0.18)'

function expenseBg(categoryId: number | null): Record<string, string> {
  const bg = categoryId !== null ? (EXPENSE_PASTELS[categoryId % EXPENSE_PASTELS.length] ?? EXPENSE_DEFAULT_BG) : EXPENSE_DEFAULT_BG
  return { backgroundColor: bg }
}
function onPortraitChange(e: MediaQueryListEvent): void {
  isPortrait.value = e.matches
}
onMounted(() => mqlPortrait.addEventListener('change', onPortraitChange))
onUnmounted(() => mqlPortrait.removeEventListener('change', onPortraitChange))

// ── State ─────────────────────────────────────────────────────────
const accounts = ref<Account[]>([])
const selectedAccountId = ref<number | null>(null)
const month = ref<string>(
  `${new Date().getFullYear()}-${String(new Date().getMonth() + 1).padStart(2, '0')}`,
) // YYYY-MM (local time)

const viewData = ref<ReconciliationView | null>(null)
const loading = ref(false)
const error = ref('')

// Local copies of links (modified by link / unlink actions)
const localLinks = ref<ReconciliationLink[]>([])
// Suggestions from backend (can be locally dismissed)
const localSuggestions = ref<ReconciliationSuggestion[]>([])
// Rule matches from backend (bank txs matched by a rule but no existing expense)
const localRuleMatches = ref<RuleMatch[]>([])
// Bank tx IDs whose suggestion/rule-match has been dismissed locally
const dismissed = ref<Set<number>>(new Set())

// Search filter
const filterQuery = ref<string>('')

// Status filter: which rows to show by reconciliation state
type StatusFilter = 'all' | 'linked' | 'suggested' | 'rule_match' | 'unmatched'
const statusFilter = ref<StatusFilter>('all')

// Selection state
const selBankId = ref<number | null>(null)
const selExpId = ref<number | null>(null)

// Animation: bank tx id that just got linked
const animBankId = ref<number | null>(null)

// Mobile tab: 0 = bank, 1 = expenses
const mobileTab = ref(0)
// Rotate banner dismiss state (portrait mobile)
const showRotateBanner = ref(true)
const swipeContainer = ref<HTMLElement | null>(null)
// Get the <main> scroll container (defined in App.vue)
function getScrollContainer(): HTMLElement | null {
  return document.querySelector('main')
}
// Two separate refs for the two possible blueprint positions (one inside v-for, one outside)
const mobileBlueprintInlineRef = ref<HTMLElement[]>([])
const mobileBlueprintEndRef = ref<HTMLElement | null>(null)
const savedBankScrollY = ref(0)

// Expenses and bank txs sorted date-descending for the mobile panels
const sortedExpenses = computed<ReconciliationExpense[]>(() =>
  [...expenses.value].sort((a, b) => {
    const d = b.date.localeCompare(a.date)
    return d !== 0 ? d : a.id - b.id
  }),
)
const sortedBankTxs = computed<BankTx[]>(() =>
  [...bankTxs.value].sort((a, b) => {
    const d = b.date.localeCompare(a.date)
    return d !== 0 ? d : a.id - b.id
  }),
)

// Mobile filtered lists derived from displayedRows
const filteredVisibleBankIds = computed<Set<number>>(
  () => new Set(displayedRows.value.flatMap((r) => (r.bank ? [r.bank.id] : []))),
)
const filteredVisibleExpIds = computed<Set<number>>(
  () => new Set(displayedRows.value.flatMap((r) => (r.expense ? [r.expense.id] : []))),
)
const filteredSortedBankTxs = computed<BankTx[]>(() =>
  sortedBankTxs.value.filter((b) => filteredVisibleBankIds.value.has(b.id)),
)
const filteredSortedExpenses = computed<ReconciliationExpense[]>(() =>
  sortedExpenses.value.filter((e) => filteredVisibleExpIds.value.has(e.id)),
)

// Index in sortedExpenses where the blueprint card should be inserted
const mobileBlueprintInsertIndex = computed<number>(() => {
  if (selBankId.value === null) return -1
  const bank = bankTxs.value.find((b) => b.id === selBankId.value)
  if (!bank) return 0
  // sortedExpenses are date-descending; insert before the first expense with date <= bank.date
  const idx = sortedExpenses.value.findIndex((e) => e.date <= bank.date)
  return idx === -1 ? sortedExpenses.value.length : idx
})

// Cloture modal
const showClotureModal = ref(false)
const clotureResult = ref<ClotureResponse | null>(null)

// Link modal (manual selection)
const showLinkModal = ref(false)
const modalBankId = ref<number | null>(null)
const modalExpId = ref<number | null>(null)
const modalMemo = ref('')
const modalAdjust = ref(true)

// Saving state
const linking = ref(false)
const clotureLoading = ref(false)

// Categories for new expense form
const allCategoryGroups = ref<CategoryGroupWithCategories[]>([])

// New expense modal
const showNewExpenseModal = ref(false)
const newExpLabel = ref('')
const newExpAmount = ref<number>(0)
const newExpCategoryId = ref<number | null>(null)

// Rule options shown in the new expense wizard
const createRuleEnabled = ref<boolean>(true)
const ruleAmountMode = ref<RuleAmountMode>('none')
const ruleAmountTolerancePct = ref<number>(10)
const ruleTransactionType = ref<RuleTransactionType>('any')

// Delete confirmation
const pendingDelete = ref<{ id: number; kind: 'bank' | 'expense'; label: string } | null>(null)

// Import modal
const showImportModal = ref(false)

// Rules modal
const showRulesModal = ref(false)
const rulesCount = ref(0)
const toastStore = useToastStore()

function categoryNameById(id: number): string {
  for (const g of allCategoryGroups.value) {
    const cat = g.categories.find((c) => c.id === id)
    if (cat) return cat.name
  }
  return `(${id})`
}

// ── Computed helpers ──────────────────────────────────────────────
const bankTxs = computed<BankTx[]>(() => viewData.value?.bank_txs ?? [])
const expenses = computed<ReconciliationExpense[]>(() => viewData.value?.expenses ?? [])

const allCategories = computed<Category[]>(() =>
  allCategoryGroups.value.flatMap((g) => g.categories).filter((c) => !c.hidden),
)

const suggestedCategoryName = ref<string>('')

const activeSuggestions = computed<ReconciliationSuggestion[]>(() =>
  localSuggestions.value.filter(
    (s) =>
      !dismissed.value.has(s.bank_tx.id) &&
      !isLinkedBank(s.bank_tx.id) &&
      !isLinkedExpense(s.expense.id),
  ),
)

const activeRuleMatches = computed<RuleMatch[]>(() =>
  localRuleMatches.value.filter(
    (rm) =>
      !dismissed.value.has(rm.bank_tx.id) &&
      !isLinkedBank(rm.bank_tx.id) &&
      !activeSuggestions.value.some((s) => s.bank_tx.id === rm.bank_tx.id),
  ),
)

function isLinkedBank(id: number): boolean {
  return localLinks.value.some((l) => l.bank_tx_id === id)
}

function isLinkedExpense(id: number): boolean {
  return localLinks.value.some((l) => l.expense_id === id)
}

function linkedExpenseFor(bankId: number): ReconciliationExpense | undefined {
  const link = localLinks.value.find((l) => l.bank_tx_id === bankId)
  return link ? expenses.value.find((e) => e.id === link.expense_id) : undefined
}

function linkedBankFor(expId: number): BankTx | undefined {
  const link = localLinks.value.find((l) => l.expense_id === expId)
  return link ? bankTxs.value.find((b) => b.id === link.bank_tx_id) : undefined
}

function suggestionForBank(id: number): ReconciliationSuggestion | undefined {
  return activeSuggestions.value.find((s) => s.bank_tx.id === id)
}

function suggestionForExpense(id: number): ReconciliationSuggestion | undefined {
  return activeSuggestions.value.find((s) => s.expense.id === id)
}

// Rows for split layout: links → suggestions → rule matches → unmatched
interface Row {
  bank: BankTx | null
  expense: ReconciliationExpense | null
  linked: boolean
  suggested: boolean
  ruleMatch: { category_id: number; category_name: string | null } | null
  date: string
}

const rows = computed<Row[]>(() => {
  const suggBankIds = new Set(activeSuggestions.value.map((s) => s.bank_tx.id))
  const suggExpIds = new Set(activeSuggestions.value.map((s) => s.expense.id))
  const ruleMatchBankIds = new Set(activeRuleMatches.value.map((rm) => rm.bank_tx.id))

  const all: Row[] = []

  // Confirmed links
  for (const lk of localLinks.value) {
    const b = bankTxs.value.find((t) => t.id === lk.bank_tx_id)
    const e = expenses.value.find((x) => x.id === lk.expense_id)
    if (b && e)
      all.push({ bank: b, expense: e, linked: true, suggested: false, ruleMatch: null, date: b.date })
  }

  // Suggestions
  for (const s of activeSuggestions.value) {
    all.push({
      bank: s.bank_tx,
      expense: s.expense,
      linked: false,
      suggested: true,
      ruleMatch: null,
      date: s.bank_tx.date,
    })
  }

  // Rule matches (bank tx matched by rule, no existing expense)
  for (const rm of activeRuleMatches.value) {
    all.push({
      bank: rm.bank_tx,
      expense: null,
      linked: false,
      suggested: false,
      ruleMatch: { category_id: rm.category_id, category_name: rm.category_name },
      date: rm.bank_tx.date,
    })
  }

  // Unmatched bank transactions (not in suggestions or rule matches)
  for (const b of bankTxs.value) {
    if (!isLinkedBank(b.id) && !suggBankIds.has(b.id) && !ruleMatchBankIds.has(b.id)) {
      all.push({ bank: b, expense: null, linked: false, suggested: false, ruleMatch: null, date: b.date })
    }
  }

  // Unmatched expenses
  for (const e of expenses.value) {
    if (!isLinkedExpense(e.id) && !suggExpIds.has(e.id)) {
      all.push({ bank: null, expense: e, linked: false, suggested: false, ruleMatch: null, date: e.date })
    }
  }

  return all.sort((a, b) => {
    const dateDiff = b.date.localeCompare(a.date)
    if (dateDiff !== 0) return dateDiff
    const aId = a.bank?.id ?? a.expense?.id ?? 0
    const bId = b.bank?.id ?? b.expense?.id ?? 0
    return aId - bId
  })
})

// Filter rows by a text query (case-insensitive, active after 3 chars).
// When a bank tx or expense matches, include its paired partner row too.
const filteredRows = computed<Row[]>(() => {
  const q = filterQuery.value.trim().toLowerCase()
  if (q.length < 3) return rows.value

  // Collect IDs that directly match the query
  const matchBankIds = new Set<number>()
  const matchExpIds = new Set<number>()
  for (const row of rows.value) {
    if (row.bank && row.bank.label.toLowerCase().includes(q)) matchBankIds.add(row.bank.id)
    if (row.expense && row.expense.label.toLowerCase().includes(q)) matchExpIds.add(row.expense.id)
  }

  return rows.value.filter((row) => {
    if (row.bank && matchBankIds.has(row.bank.id)) return true
    if (row.expense && matchExpIds.has(row.expense.id)) return true
    // Partner row: keep it if its bank side appears in a row with a matching expense
    if (row.bank) {
      const paired = rows.value.some((r) => r.bank?.id === row.bank!.id && r.expense && matchExpIds.has(r.expense.id))
      if (paired) return true
    }
    // Partner row: keep it if its expense side appears in a row with a matching bank tx
    if (row.expense) {
      const paired = rows.value.some((r) => r.expense?.id === row.expense!.id && r.bank && matchBankIds.has(r.bank.id))
      if (paired) return true
    }
    return false
  })
})

const linkedCount = computed(() => localLinks.value.length)
const unmatchedCount = computed(
  () => rows.value.filter((r) => !r.linked && !r.suggested && r.ruleMatch === null).length,
)

// Counts per status bucket within the current text filter (used by pill buttons)
const filteredTextActive = computed(() => filterQuery.value.trim().length >= 3)
const filteredLinkedCount = computed(() => filteredRows.value.filter((r) => r.linked).length)
const filteredSuggestedCount = computed(() => filteredRows.value.filter((r) => r.suggested).length)
const filteredRuleMatchCount = computed(() => filteredRows.value.filter((r) => r.ruleMatch !== null).length)
const filteredUnmatchedCount = computed(
  () => filteredRows.value.filter((r) => !r.linked && !r.suggested && r.ruleMatch === null).length,
)

// Final displayed rows: text filter → status filter
const displayedRows = computed<Row[]>(() => {
  const f = statusFilter.value
  if (f === 'all') return filteredRows.value
  return filteredRows.value.filter((row) => {
    if (f === 'linked') return row.linked
    if (f === 'suggested') return row.suggested
    if (f === 'rule_match') return row.ruleMatch !== null
    if (f === 'unmatched') return !row.linked && !row.suggested && row.ruleMatch === null
    return true
  })
})
const realExpenses = computed(() => expenses.value.filter((e) => e.status !== 'planned'))
const monthLabel = computed<string>(() => {
  const [y, m] = month.value.split('-')
  return new Date(Number(y), Number(m) - 1, 1).toLocaleDateString('fr-FR', {
    month: 'long',
    year: 'numeric',
  })
})

// ── Load data ─────────────────────────────────────────────────────
async function loadAccounts(): Promise<void> {
  const acc = await listAccounts()
  accounts.value = acc
  if (acc.length > 0 && selectedAccountId.value === null) {
    selectedAccountId.value = acc[0]?.id ?? null
  }
}

async function loadView(preserveScroll = false): Promise<void> {
  if (selectedAccountId.value === null) return
  const savedScroll = preserveScroll ? (getScrollContainer()?.scrollTop ?? 0) : 0
  if (!preserveScroll) loading.value = true
  error.value = ''
  try {
    const data = await getReconciliationView(selectedAccountId.value, month.value)
    viewData.value = data
    localLinks.value = [...data.links]
    localSuggestions.value = [...data.suggestions]
    localRuleMatches.value = [...(data.rule_matches ?? [])]
    dismissed.value = new Set()
    // Only reset filters when doing a full navigation (month/account change),
    // not when refreshing after an action (preserveScroll = true).
    if (!preserveScroll) {
      filterQuery.value = ''
      statusFilter.value = 'all'
    }
    selBankId.value = null
    selExpId.value = null
  } catch {
    error.value = 'Impossible de charger les données de pointage.'
  } finally {
    loading.value = false
    if (preserveScroll && savedScroll > 0) {
      nextTick(() => getScrollContainer()?.scrollTo(0, savedScroll))
    }
  }
}

onMounted(async () => {
  await loadAccounts()
  await loadView()
  try {
    allCategoryGroups.value = await listCategoryGroups()
  } catch {
    // categories are optional — new expense form will show empty select
  }
  try {
    const rules = await listRules()
    rulesCount.value = rules.length
  } catch {
    // rules count is optional
  }
})

watch([selectedAccountId, month], () => loadView())

// ── Month navigation ──────────────────────────────────────────────
function prevMonth(): void {
  const parts = month.value.split('-').map(Number)
  const y = parts[0] ?? new Date().getFullYear()
  const m = parts[1] ?? new Date().getMonth() + 1
  const d = new Date(y, m - 2, 1)
  month.value = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`
}

function nextMonth(): void {
  const parts = month.value.split('-').map(Number)
  const y = parts[0] ?? new Date().getFullYear()
  const m = parts[1] ?? new Date().getMonth() + 1
  const d = new Date(y, m, 1)
  month.value = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`
}

// ── Selection & click handlers ────────────────────────────────────
function clickBank(id: number): void {
  if (isLinkedBank(id)) return
  if (selBankId.value === id) {
    selBankId.value = null
    return
  }
  if (selExpId.value !== null) {
    openLinkModal(id, selExpId.value)
    return
  }
  selBankId.value = id
  selExpId.value = null
  // On portrait mobile, save scroll position, switch to expenses tab and scroll to blueprint
  if (isPortrait.value) {
    savedBankScrollY.value = getScrollContainer()?.scrollTop ?? 0
    switchTab(1)
    // Wait for swipe animation (~350ms) then scroll blueprint into view
    setTimeout(() => {
      const el = mobileBlueprintInlineRef.value[0] ?? mobileBlueprintEndRef.value
      if (el) {
        const sc = getScrollContainer()
        const rect = el.getBoundingClientRect()
        const containerHeight = sc?.clientHeight ?? window.innerHeight
        const scrollTop = sc?.scrollTop ?? 0
        const targetY = scrollTop + rect.top - containerHeight / 2 + rect.height / 2
        sc?.scrollTo({ top: Math.max(0, targetY), behavior: 'smooth' })
      }
    }, 380)
  }
}

function clickExpense(id: number): void {
  if (isLinkedExpense(id)) return
  if (selExpId.value === id) {
    selExpId.value = null
    return
  }
  if (selBankId.value !== null) {
    openLinkModal(selBankId.value, id)
    return
  }
  selExpId.value = id
  selBankId.value = null
  // On portrait mobile, switch to bank tab
  if (isPortrait.value) switchTab(0)
}

function clearSelection(): void {
  selBankId.value = null
  selExpId.value = null
}

// ── Suggestions ───────────────────────────────────────────────────
async function confirmSuggestion(bankId: number, expenseId: number): Promise<void> {
  const bank = bankTxs.value.find((b) => b.id === bankId)
  if (!bank) return
  const req: LinkRequest = {
    bank_tx_id: bankId,
    expense_id: expenseId,
    adjust_amount: true,
    memo: titleCase(bank.label),
  }
  await doLink(req)
}

function dismissSuggestion(bankId: number): void {
  dismissed.value = new Set([...dismissed.value, bankId])
}

// ── Rule match: one-click create + link ───────────────────────────
async function _createAndLink(bankId: number, categoryId: number): Promise<void> {
  const bank = bankTxs.value.find((b) => b.id === bankId)
  if (!bank || selectedAccountId.value === null) return
  const newTx = await createTransaction({
    account_id: selectedAccountId.value,
    date: bank.date,
    category_id: categoryId,
    amount: bank.amount,
    memo: titleCase(bank.label),
    status: 'real',
  })
  const req: LinkRequest = { bank_tx_id: bankId, expense_id: newTx.id, adjust_amount: false, memo: null }
  const link = await createLink(req)
  localLinks.value = [...localLinks.value, link]
  animBankId.value = bankId
  setTimeout(() => { if (animBankId.value === bankId) animBankId.value = null }, 1500)
}

// ── Bulk actions ──────────────────────────────────────────────────
async function confirmAllSuggestions(): Promise<void> {
  linking.value = true
  try {
    for (const s of [...activeSuggestions.value]) {
      const req: LinkRequest = {
        bank_tx_id: s.bank_tx.id,
        expense_id: s.expense.id,
        adjust_amount: true,
        memo: titleCase(s.bank_tx.label),
      }
      const link = await createLink(req)
      localLinks.value = [...localLinks.value, link]
      if (link.created_rule) {
        rulesCount.value += 1
        toastStore.success(`Règle créée pour « ${categoryNameById(link.created_rule.category_id)} »`)
      }
    }
    selBankId.value = null
    selExpId.value = null
  } catch {
    error.value = 'Erreur lors de la liaison en masse.'
  } finally {
    linking.value = false
  }
}

async function confirmAllRuleMatches(): Promise<void> {
  if (selectedAccountId.value === null) return
  linking.value = true
  try {
    for (const rm of [...activeRuleMatches.value]) {
      await _createAndLink(rm.bank_tx.id, rm.category_id)
    }
    selBankId.value = null
    await loadView(true)
  } catch {
    error.value = 'Erreur lors de la création en masse.'
  } finally {
    linking.value = false
  }
}

async function confirmAll(): Promise<void> {
  if (selectedAccountId.value === null) return
  linking.value = true
  try {
    for (const s of [...activeSuggestions.value]) {
      const req: LinkRequest = {
        bank_tx_id: s.bank_tx.id,
        expense_id: s.expense.id,
        adjust_amount: true,
        memo: titleCase(s.bank_tx.label),
      }
      const link = await createLink(req)
      localLinks.value = [...localLinks.value, link]
      if (link.created_rule) {
        rulesCount.value += 1
        toastStore.success(`Règle créée pour « ${categoryNameById(link.created_rule.category_id)} »`)
      }
    }
    for (const rm of [...activeRuleMatches.value]) {
      await _createAndLink(rm.bank_tx.id, rm.category_id)
    }
    selBankId.value = null
    selExpId.value = null
    if (activeRuleMatches.value.length > 0) {
      await loadView(true)
    }
  } catch {
    error.value = 'Erreur lors de la liaison en masse.'
  } finally {
    linking.value = false
  }
}


async function openNewExpenseModal(preselectedCategoryId?: number): Promise<void> {
  if (selBankId.value === null) return
  const bank = bankTxs.value.find((b) => b.id === selBankId.value)
  if (!bank) return
  newExpLabel.value = titleCase(bank.label)
  newExpAmount.value = Math.abs(bank.amount) / 100
  suggestedCategoryName.value = ''
  // Pre-select transaction type from the bank tx sign
  ruleTransactionType.value = bank.amount < 0 ? 'debit' : bank.amount > 0 ? 'credit' : 'any'
  ruleAmountMode.value = 'none'
  ruleAmountTolerancePct.value = 10

  if (preselectedCategoryId !== undefined) {
    // Category already known from rule match — no need to call the categorize API
    newExpCategoryId.value = preselectedCategoryId
    const cat = allCategories.value.find((c) => c.id === preselectedCategoryId)
    suggestedCategoryName.value = cat?.name ?? ''
    showNewExpenseModal.value = true
  } else {
    // Show modal immediately; resolve category asynchronously
    newExpCategoryId.value = null
    showNewExpenseModal.value = true
    // Apply rules-based categorization
    // Pass bank.label as both payeeName and memo: bank transactions have a single
    // label field, so both "payee" and "memo" rules should be able to match it.
    // Pass bank.amount so amount-range constraints are properly evaluated.
    try {
      const result = await categorizeSingle(bank.label, bank.label, bank.amount)
      if (result.category_id !== null) {
        newExpCategoryId.value = result.category_id
        const cat = allCategories.value.find((c) => c.id === result.category_id)
        suggestedCategoryName.value = cat?.name ?? ''
      }
    } catch {
      // Silently ignore — user can select manually
    }
  }
}

function openRuleMatchWizard(bankId: number, categoryId: number): void {
  selBankId.value = bankId
  openNewExpenseModal(categoryId)
}

function closeNewExpenseModal(): void {
  showNewExpenseModal.value = false
  suggestedCategoryName.value = ''
  createRuleEnabled.value = true
  ruleAmountMode.value = 'none'
  ruleAmountTolerancePct.value = 10
  ruleTransactionType.value = 'any'
}

async function onCategoryCreated(cat: Category): Promise<void> {
  // Reload category groups so the new category appears in the picker
  allCategoryGroups.value = await listCategoryGroups()
  newExpCategoryId.value = cat.id
}

async function confirmNewExpense(): Promise<void> {
  if (selectedAccountId.value === null || selBankId.value === null) return
  if (newExpCategoryId.value === null) return  // category is mandatory
  const bank = bankTxs.value.find((b) => b.id === selBankId.value)
  if (!bank) return
  linking.value = true
  try {
    const sign = bank.amount < 0 ? -1 : 1
    // Capture rule options before closeNewExpenseModal() resets them
    const capturedCreateRule = createRuleEnabled.value
    const capturedRuleTransactionType = ruleTransactionType.value
    const capturedRuleAmountMode = ruleAmountMode.value
    const capturedRuleAmountTolerancePct = ruleAmountTolerancePct.value
    const newTx = await createTransaction({
      account_id: selectedAccountId.value,
      date: bank.date,
      category_id: newExpCategoryId.value ?? null,
      amount: sign * Math.round(newExpAmount.value * 100),
      memo: newExpLabel.value.trim() || null,
      status: 'real',
    })
    closeNewExpenseModal()
    const req: LinkRequest = {
      bank_tx_id: bank.id,
      expense_id: newTx.id,
      adjust_amount: false,
      memo: null,
      skip_rule: !capturedCreateRule,
      rule_transaction_type: capturedRuleTransactionType,
      rule_amount_mode: capturedRuleAmountMode,
      rule_amount_tolerance_pct: capturedRuleAmountTolerancePct,
    }
    await doLink(req)
    await loadView(true)
  } catch {
    error.value = 'Erreur lors de la création de la dépense.'
  } finally {
    linking.value = false
  }
}

// ── Delete ───────────────────────────────────────────────────────
function requestDelete(id: number, kind: 'bank' | 'expense', label: string): void {
  pendingDelete.value = { id, kind, label }
}

async function executeDelete(): Promise<void> {
  if (!pendingDelete.value) return
  linking.value = true
  try {
    await deleteTransaction(pendingDelete.value.id)
    pendingDelete.value = null
    await loadView(true)
  } catch {
    error.value = 'Erreur lors de la suppression.'
  } finally {
    linking.value = false
  }
}

// ── Link modal ────────────────────────────────────────────────────
function openLinkModal(bankId: number, expenseId: number): void {
  const bank = bankTxs.value.find((b) => b.id === bankId)
  modalBankId.value = bankId
  modalExpId.value = expenseId
  modalMemo.value = bank ? titleCase(bank.label) : ''
  modalAdjust.value = true
  showLinkModal.value = true
}

function closeLinkModal(): void {
  showLinkModal.value = false
  modalBankId.value = null
  modalExpId.value = null
}

async function confirmLinkModal(): Promise<void> {
  if (modalBankId.value === null || modalExpId.value === null) return
  const req: LinkRequest = {
    bank_tx_id: modalBankId.value,
    expense_id: modalExpId.value,
    adjust_amount: modalAdjust.value,
    memo: modalMemo.value.trim() || null,
  }
  closeLinkModal()
  await doLink(req)
}

async function doLink(req: LinkRequest): Promise<void> {
  linking.value = true
  try {
    const link = await createLink(req)
    localLinks.value = [...localLinks.value, link]
    animBankId.value = req.bank_tx_id
    selBankId.value = null
    selExpId.value = null
    // Update local expense memo/amount to reflect backend change
    if (viewData.value) {
      const exp = viewData.value.expenses.find((e) => e.id === req.expense_id)
      if (exp) {
        if (req.memo !== undefined && req.memo !== null) exp.memo = req.memo
        if (req.adjust_amount) {
          const bank = bankTxs.value.find((b) => b.id === req.bank_tx_id)
          if (bank) exp.amount = bank.amount
        }
      }
    }
    // Toast + badge when a new rule was auto-created
    if (link.created_rule) {
      rulesCount.value += 1
      toastStore.success(`Règle créée pour « ${categoryNameById(link.created_rule.category_id)} »`)
    }
    setTimeout(() => {
      animBankId.value = null
    }, 1500)
    // On portrait mobile, return to bank tab and restore scroll position
    if (isPortrait.value) {
      switchTab(0)
      const savedY = savedBankScrollY.value
      setTimeout(() => getScrollContainer()?.scrollTo({ top: savedY, behavior: 'smooth' }), 380)
    }
  } catch {
    error.value = 'Erreur lors de la création du lien.'
  } finally {
    linking.value = false
  }
}

async function doUnlink(bankId: number): Promise<void> {
  try {
    await deleteLink(bankId)
    localLinks.value = localLinks.value.filter((l) => l.bank_tx_id !== bankId)
  } catch {
    error.value = 'Erreur lors de la suppression du lien.'
  }
}

// ── Clôture ───────────────────────────────────────────────────────
async function doCloture(): Promise<void> {
  if (selectedAccountId.value === null) return
  clotureLoading.value = true
  try {
    const result = await apiCloture({ account_id: selectedAccountId.value, month: month.value })
    clotureResult.value = result
    showClotureModal.value = true
    await loadView()
  } catch {
    error.value = 'Erreur lors de la clôture.'
  } finally {
    clotureLoading.value = false
  }
}

// ── Mobile tab / swipe ────────────────────────────────────────────
function switchTab(idx: number): void {
  mobileTab.value = idx
  nextTick(() => {
    if (swipeContainer.value) {
      swipeContainer.value.scrollTo({ left: idx * swipeContainer.value.clientWidth, behavior: 'smooth' })
    }
  })
}

function onSwipeScroll(): void {
  if (!swipeContainer.value) return
  const idx = Math.round(swipeContainer.value.scrollLeft / Math.max(swipeContainer.value.clientWidth, 1))
  if (idx !== mobileTab.value) mobileTab.value = idx
}

// ── Formatting helpers ────────────────────────────────────────────
function fmtDate(s: string): string {
  const [, m, d] = s.split('-')
  return `${d}/${m}`
}

function fmtAmt(centimes: number): string {
  return formatAmount(centimes)
}

function labelFontSize(label: string): Record<string, string> {
  const len = label.length
  if (len > 40) return { fontSize: '0.6rem' }
  if (len > 32) return { fontSize: '0.68rem' }
  if (len > 24) return { fontSize: '0.78rem' }
  return {}
}

function titleCase(s: string): string {
  return s.toLowerCase().replace(/\b\w/g, (c) => c.toUpperCase())
}

// ── Modal computed helpers ────────────────────────────────────────
const modalBank = computed<BankTx | undefined>(() =>
  modalBankId.value !== null ? bankTxs.value.find((b) => b.id === modalBankId.value) : undefined,
)

// The bank transaction currently selected in the new-expense wizard
const wizardBank = computed<BankTx | undefined>(() =>
  selBankId.value !== null ? bankTxs.value.find((b) => b.id === selBankId.value) : undefined,
)

const modalExpense = computed<ReconciliationExpense | undefined>(() =>
  modalExpId.value !== null ? expenses.value.find((e) => e.id === modalExpId.value) : undefined,
)

const modalHasDelta = computed<boolean>(() => {
  if (!modalBank.value || !modalExpense.value) return false
  return Math.abs(Math.abs(modalBank.value.amount) - Math.abs(modalExpense.value.amount)) > 0
})
</script>

<template>
  <div class="bg-base-200">

  <!-- PAGE HEADER sticky -->
  <div class="@container bg-base-100 border-b border-base-200 sticky top-0 z-30">
      <div class="max-w-[120rem] mx-auto px-3 py-2 flex items-center gap-x-2 gap-y-1 flex-wrap">
        <h1 class="text-base font-bold text-base-content hidden sm:block">↔ Pointage</h1>

        <!-- Account selector -->
        <select
          v-if="accounts.length > 1"
          v-model="selectedAccountId"
          class="select select-bordered select-xs sm:select-sm"
        >
          <option v-for="acc in accounts" :key="acc.id" :value="acc.id">{{ acc.name }}</option>
        </select>

        <!-- Month navigation -->
        <div class="flex items-center gap-1">
          <button class="btn btn-ghost btn-xs" @click="prevMonth">◀</button>
          <span class="font-semibold text-base-content/80 px-1 text-sm capitalize">{{ monthLabel }}</span>
          <button class="btn btn-ghost btn-xs" @click="nextMonth">▶</button>
        </div>

        <!-- Search filter + status pills
             Container wide enough → inline between month-nav and actions (1 row)
             Container too narrow  → order-last + full width → own row at bottom -->
        <div class="order-last w-full flex items-center gap-1 @min-[1200px]:order-none @min-[1200px]:w-auto">
          <div class="relative flex items-center shrink-0">
            <input
              v-model="filterQuery"
              type="text"
              placeholder="🔍 Filtrer…"
              class="input input-bordered input-xs sm:input-sm w-36 sm:w-48"
              :class="filterQuery ? 'pr-6' : ''"
            >
            <button
              v-if="filterQuery"
              class="absolute right-1.5 text-base-content/40 hover:text-base-content transition-colors"
              tabindex="-1"
              @click="filterQuery = ''"
            >✕</button>
          </div>
          <span v-if="filteredTextActive" class="badge badge-neutral badge-sm font-mono shrink-0">{{ filteredRows.length }}</span>
          <button
            class="btn btn-xs rounded-full shrink-0"
            :class="statusFilter === 'all' ? 'btn-neutral' : 'btn-ghost text-base-content/60'"
            @click="statusFilter = 'all'"
          >Toutes</button>
          <button
            class="btn btn-xs rounded-full shrink-0"
            :class="statusFilter === 'linked' ? 'btn-success text-white' : 'btn-ghost text-base-content/60'"
            @click="statusFilter = 'linked'"
          >✅ Liées <span class="badge badge-xs ml-0.5">{{ filteredTextActive ? filteredLinkedCount : linkedCount }}</span></button>
          <button
            class="btn btn-xs rounded-full shrink-0"
            :class="statusFilter === 'suggested' ? 'btn-primary' : 'btn-ghost text-base-content/60'"
            @click="statusFilter = 'suggested'"
          >💡 Suggestions <span class="badge badge-xs ml-0.5">{{ filteredTextActive ? filteredSuggestedCount : activeSuggestions.length }}</span></button>
          <button
            class="btn btn-xs rounded-full shrink-0"
            :class="statusFilter === 'rule_match' ? 'btn-warning' : 'btn-ghost text-base-content/60'"
            @click="statusFilter = 'rule_match'"
          >✨ À créer <span class="badge badge-xs ml-0.5">{{ filteredTextActive ? filteredRuleMatchCount : activeRuleMatches.length }}</span></button>
          <button
            class="btn btn-xs rounded-full shrink-0"
            :class="statusFilter === 'unmatched' ? 'btn-ghost border border-base-content/30 text-base-content' : 'btn-ghost text-base-content/60'"
            @click="statusFilter = 'unmatched'"
          >⚪ Non liées <span class="badge badge-xs ml-0.5">{{ filteredTextActive ? filteredUnmatchedCount : unmatchedCount }}</span></button>
        </div>

        <!-- Actions
             < sm : w-full → own line (3-row layout)
             sm+  : ml-auto → pushed to the right of its line -->
        <div class="w-full flex gap-1.5 justify-end shrink-0 sm:w-auto sm:ml-auto">
          <button
            class="btn btn-outline btn-xs sm:btn-sm gap-1"
            @click="showRulesModal = true"
          >
            🏷️ <span class="hidden sm:inline">Règles</span>
            <span v-if="rulesCount > 0" class="badge badge-neutral badge-sm">{{ rulesCount }}</span>
          </button>
          <button
            class="btn btn-outline btn-xs sm:btn-sm gap-1"
            @click="showImportModal = true"
          >
            📤 <span class="hidden sm:inline">Importer</span>
          </button>
          <button
            class="btn btn-success btn-xs sm:btn-sm gap-1 text-white"
            :disabled="clotureLoading"
            @click="doCloture"
          >
            <span v-if="clotureLoading" class="loading loading-spinner loading-xs" />
            <template v-else>✅</template>
            <span class="hidden sm:inline">Clôturer</span>
          </button>
        </div>
      </div>
      <!-- Rotate banner (portrait mobile only, dismissable) -->
      <div
        v-if="isPortrait && showRotateBanner"
        class="flex items-center gap-2 bg-info/10 border-t border-info/20 px-4 py-2 text-sm text-info"
      >
        <span class="text-lg">🔄</span>
        <span>Tournez votre écran en <strong>mode paysage</strong> pour voir les deux colonnes côte à côte</span>
        <button class="btn btn-ghost btn-xs ml-auto shrink-0 text-info" @click="showRotateBanner = false">✕</button>
      </div>
      <!-- Tab bar (portrait mobile only) -->
      <div v-if="isPortrait && viewData" class="flex border-t border-base-200 bg-base-100">
        <button
          class="flex-1 py-3 text-sm font-semibold border-b-2 flex items-center justify-center gap-1.5"
          :class="mobileTab === 0
            ? 'text-primary border-primary bg-primary/10'
            : 'text-base-content/60 border-transparent'"
          @click="switchTab(0)"
        >
          🏦 Bancaire
          <span class="badge badge-ghost badge-sm font-mono ml-1">{{ linkedCount }}/{{ bankTxs.length }}</span>
        </button>
        <button
          class="flex-1 py-3 text-sm border-b-2 flex items-center justify-center gap-1.5"
          :class="mobileTab === 1
            ? 'text-primary border-primary bg-primary/10 font-semibold'
            : 'text-base-content/60 border-transparent font-medium'"
          @click="switchTab(1)"
        >
          💸 Dépenses
          <span class="badge badge-ghost badge-sm font-mono ml-1">{{ expenses.length }}</span>
        </button>
      </div>
      <p v-if="isPortrait && viewData" class="text-center text-xs text-base-content/50 py-1 bg-base-100 border-t border-base-200">← glissez pour changer d'onglet →</p>
    </div>

  <!-- Content wrapper — pas de min-h-full pour ne pas casser le sticky ci-dessus -->
  <div class="flex flex-col bg-base-200">

    <!-- Instruction bar (selection active) -->
    <transition name="slide-down">
      <div
        v-if="selBankId !== null || selExpId !== null"
        class="alert alert-info text-xs sm:text-sm py-2 px-4 gap-2 rounded-none border-x-0"
      >
        <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" class="stroke-current shrink-0 w-4 h-4">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
        <span v-if="selBankId !== null">
          Transaction sélectionnée (bleue). Cliquez une dépense pour créer le lien — ou « Créer une nouvelle dépense ».
        </span>
        <span v-else>
          Dépense sélectionnée (jaune). Cliquez une transaction bancaire pour créer le lien.
        </span>
        <button class="btn btn-ghost btn-xs ml-auto shrink-0" @click="clearSelection">✕</button>
      </div>
    </transition>

    <!-- Error bar -->
    <div v-if="error" class="alert alert-error text-sm py-2 px-4 rounded-none border-x-0">
      {{ error }}
      <button class="btn btn-ghost btn-xs ml-auto" @click="error = ''">✕</button>
    </div>

    <!-- Loading skeleton -->
    <div v-if="loading" class="flex justify-center py-16">
      <span class="loading loading-spinner loading-lg text-primary" />
    </div>

    <template v-else-if="viewData">

      <!-- ── CONTENT ───────────────────────────────────────────── -->
      <div class="max-w-7xl mx-auto w-full px-0 sm:px-4 py-0 sm:py-5">

        <!-- SPLIT LAYOUT (desktop + landscape mobile) -->
        <div v-if="!isPortrait" class="bg-base-100 sm:rounded-2xl sm:shadow-sm sm:border sm:border-base-200 overflow-hidden">

          <!-- Column headers -->
          <div
            class="bg-base-200 border-b border-base-200"
            style="display:grid;grid-template-columns:1fr 48px 1fr;"
          >
            <div class="px-4 py-3 flex items-center gap-2">
              <span class="font-semibold text-sm text-base-content/80">🏦 Relevé bancaire</span>
              <span class="badge badge-ghost badge-sm font-mono">{{ linkedCount }}/{{ bankTxs.length }}</span>
            </div>
            <div />
            <div class="px-4 py-3 flex items-center gap-2 flex-wrap">
              <span class="font-semibold text-sm text-base-content/80">💸 Dépenses</span>
              <span class="badge badge-ghost badge-sm font-mono">{{ expenses.length }}</span>
              <div class="ml-auto flex items-center gap-1 flex-wrap">
                <button
                  v-if="selBankId !== null"
                  class="btn btn-primary btn-xs"
                  @click="() => openNewExpenseModal()"
                >+ Nouvelle</button>
                <template v-if="activeSuggestions.length > 0 || activeRuleMatches.length > 0">
                  <div class="divider divider-horizontal mx-0" />
                  <button
                    v-if="activeSuggestions.length > 0"
                    class="btn btn-outline btn-xs gap-1"
                    :disabled="linking"
                    :title="`Valider les ${activeSuggestions.length} suggestion(s)`"
                    @click="confirmAllSuggestions"
                  >⇢ Sugg. <span class="badge badge-xs badge-neutral">{{ activeSuggestions.length }}</span></button>
                  <button
                    v-if="activeRuleMatches.length > 0"
                    class="btn btn-outline btn-xs gap-1"
                    :disabled="linking"
                    :title="`Créer et lier les ${activeRuleMatches.length} correspondance(s)`"
                    @click="confirmAllRuleMatches"
                  >✨ Créer <span class="badge badge-xs badge-neutral">{{ activeRuleMatches.length }}</span></button>
                  <button
                    v-if="activeSuggestions.length + activeRuleMatches.length > 1"
                    class="btn btn-primary btn-xs"
                    :disabled="linking"
                    title="Tout pointer automatiquement"
                    @click="confirmAll"
                  >✅ Tout</button>
                </template>
              </div>
            </div>
          </div>

          <!-- Rows -->
          <div>
            <div
              v-for="row in displayedRows"
              :key="`${row.bank?.id ?? 'x'}-${row.expense?.id ?? 'x'}-${row.linked ? 'L' : row.suggested ? 'S' : row.ruleMatch ? 'R' : 'U'}`"
              class="border-b border-base-200 transition-colors"
              :class="{
                'match-anim': animBankId !== null && row.linked && row.bank?.id === animBankId,
                'bg-purple-50/30': row.suggested,
                'bg-amber-50/20': row.ruleMatch !== null,
              }"
              style="display:grid;grid-template-columns:1fr 48px 1fr;"
            >
              <!-- Bank cell -->
              <div class="recon-cell px-4 py-3 grid" style="min-height:72px;">
                <template v-if="row.bank">
                  <div
                    class="bank-card w-full"
                    :class="{
                      'is-linked': row.linked,
                      'is-selected': selBankId === row.bank.id && !row.linked,
                      'is-suggested': row.suggested && selBankId !== row.bank.id && !row.linked,
                      'is-rule-match': row.ruleMatch !== null && !row.linked,
                    }"
                    :style="{ backgroundColor: BANK_BG }"
                    @click="!row.linked && clickBank(row.bank.id)"
                  >
                    <div class="flex justify-between items-start gap-2">
                      <div class="flex-1 min-w-0">
                        <p class="font-medium text-sm text-base-content truncate" :style="labelFontSize(row.bank.label)">{{ row.bank.label }}</p>
                        <p class="card-sub text-xs text-base-content/50 mt-0.5 flex flex-wrap gap-1">
                          {{ fmtDate(row.bank.date) }}
                          <span v-if="row.suggested" class="badge badge-sm" style="background:#ede9fe;color:#7c3aed;border-color:#c4b5fd;">💡 suggestion</span>
                          <span v-else-if="row.ruleMatch !== null" class="badge badge-sm" style="background:#fef3c7;color:#d97706;border-color:#fde68a;">✨ correspondance</span>
                          <span v-else-if="!row.linked" class="badge badge-ghost badge-sm text-base-content/50">⚪ non pointée</span>
                        </p>
                      </div>
                      <div class="flex flex-col items-end gap-0.5 shrink-0">
                        <span
                          class="font-bold text-sm"
                          :class="row.bank.amount >= 0 ? 'text-green-400' : 'text-red-400'"
                        >
                          {{ fmtAmt(row.bank.amount) }}
                        </span>
                        <button
                          v-if="row.linked"
                          class="btn btn-ghost btn-xs text-base-content/40 hover:text-red-500 px-1 h-auto min-h-0 py-0"
                          @click.stop="doUnlink(row.bank!.id)"
                        >✕ délier</button>
                        <button
                          v-else-if="row.suggested"
                          class="btn btn-ghost btn-xs text-base-content/40 hover:text-red-500 px-1 h-auto min-h-0 py-0"
                          @click.stop="dismissSuggestion(row.bank!.id)"
                        >✕ ignorer</button>
                        <button
                          v-if="!row.linked"
                          class="btn btn-ghost btn-xs text-base-content/25 hover:text-red-500 px-1 h-auto min-h-0 py-0"
                          @click.stop="requestDelete(row.bank!.id, 'bank', row.bank!.label)"
                        >🗑</button>
                      </div>
                    </div>
                  </div>
                </template>
              </div>

              <!-- Center arrow/link column -->
              <div class="flex items-center justify-center font-bold select-none" style="font-size:20px;">
                <template v-if="row.linked">
                  <span class="text-green-500">⇔</span>
                </template>
                <template v-else-if="row.suggested">
                  <button
                    class="sugg-col"
                    :disabled="linking"
                    title="Cliquer pour valider la suggestion"
                    @click="confirmSuggestion(row.bank!.id, row.expense!.id)"
                  >
                    <span class="sugg-icon" style="color:#a78bfa;font-size:22px;line-height:1;">⇢</span>
                    <span class="sugg-lbl" style="font-size:9px;color:#a78bfa;font-weight:700;text-transform:uppercase;letter-spacing:.05em;">valider</span>
                  </button>
                </template>
                <template v-else-if="selBankId !== null && row.bank?.id === selBankId && !row.linked">
                  <span class="text-blue-300 font-bold" style="font-size:20px;">→</span>
                </template>
                <template v-else>
                  <span class="text-base-content/20">·</span>
                </template>
              </div>

              <!-- Expense cell -->
              <div class="recon-cell px-4 py-3 grid" style="min-height:72px;">
                <template v-if="row.ruleMatch !== null && !row.linked">
                  <!-- Virtual blueprint expense: pre-filled from bank tx + matched rule category -->
                  <div
                    class="rule-match-blueprint w-full"
                    :style="expenseBg(row.ruleMatch.category_id)"
                    @click="openRuleMatchWizard(row.bank!.id, row.ruleMatch.category_id)"
                  >
                    <div class="flex justify-between items-start gap-2">
                      <div class="flex-1 min-w-0">
                        <p class="font-medium text-sm text-base-content/75 truncate italic" :style="labelFontSize(row.bank!.label)">
                          {{ titleCase(row.bank!.label) }}
                        </p>
                        <p class="card-sub text-xs text-base-content/50 mt-0.5">
                          <template v-if="row.ruleMatch.category_name">{{ row.ruleMatch.category_name }} · </template>
                          {{ fmtDate(row.bank!.date) }}
                          <span class="badge badge-sm ml-1" style="background:#fef3c7;color:#d97706;border-color:#fde68a;">✨ à créer</span>
                        </p>
                      </div>
                      <span
                        class="font-bold text-sm shrink-0"
                        :class="row.bank!.amount >= 0 ? 'text-green-400' : 'text-red-400'"
                      >
                        {{ fmtAmt(row.bank!.amount) }}
                      </span>
                    </div>
                  </div>
                </template>
                <template v-else-if="selBankId !== null && row.bank?.id === selBankId && !row.linked && !row.expense">
                  <div class="blueprint-card slide-in" @click="() => openNewExpenseModal()">
                    <span class="bp-icon text-3xl leading-none opacity-80">+</span>
                    <span class="bp-label text-xs font-semibold tracking-wide opacity-70">Créer une dépense liée</span>
                  </div>
                </template>
                <template v-else-if="row.expense">
                  <div
                    class="expense-card w-full"
                    :class="{
                      'is-linked': row.linked,
                      'is-selected': selExpId === row.expense.id && !row.linked,
                      'is-suggested': row.suggested && selExpId !== row.expense.id && !row.linked,
                      'is-planned': row.expense.status === 'planned' && !row.linked,
                    }"
                    :style="expenseBg(row.expense.category_id)"
                    @click="!row.linked && clickExpense(row.expense.id)"
                  >
                    <div class="flex justify-between items-start gap-2">
                      <div class="flex-1 min-w-0">
                        <p
                          class="font-medium text-sm truncate"
                          :class="row.expense.status === 'planned' ? 'italic text-base-content/60' : 'text-base-content'"
                          :style="labelFontSize(row.expense.label)"
                        >
                          {{ row.expense.label }}
                        </p>
                        <p class="card-sub text-xs text-base-content/50 mt-0.5">
                          <template v-if="row.expense.category_name">{{ row.expense.category_name }} · </template>
                          {{ fmtDate(row.expense.date) }}
                          <span v-if="row.expense.status === 'planned'" class="badge badge-warning badge-sm ml-1">🗓 prévu</span>
                          <span v-else-if="row.suggested" class="badge badge-sm ml-1" style="background:#ede9fe;color:#7c3aed;border-color:#c4b5fd;">💡</span>
                          <span v-else-if="!row.linked" class="badge badge-ghost badge-sm ml-1 text-base-content/50">⚪ non liée</span>
                        </p>
                        <p
                          v-if="row.expense.memo"
                          class="card-memo text-xs text-base-content/50 mt-0.5 italic truncate"
                          :title="row.expense.memo"
                        >
                          📝 {{ row.expense.memo }}
                        </p>
                      </div>
                      <div class="flex flex-col items-end gap-0.5 shrink-0">
                        <span
                          class="font-bold text-sm"
                          :class="row.expense.amount >= 0 ? 'text-green-400' : 'text-red-400'"
                        >
                          {{ fmtAmt(row.expense.amount) }}
                        </span>
                        <button
                          v-if="row.linked"
                          class="btn btn-ghost btn-xs text-base-content/40 hover:text-red-500 px-1 h-auto min-h-0 py-0"
                          @click.stop="doUnlink(row.bank!.id)"
                        >✕ délier</button>
                        <button
                          v-if="!row.linked"
                          class="btn btn-ghost btn-xs text-base-content/25 hover:text-red-500 px-1 h-auto min-h-0 py-0"
                          @click.stop="requestDelete(row.expense!.id, 'expense', row.expense!.label)"
                        >🗑</button>
                      </div>
                    </div>
                  </div>
                </template>
              </div>
            </div>
          </div>

          <!-- Footer stats -->
          <div class="border-t border-base-200 bg-base-200 px-4 py-2 flex gap-4 flex-wrap">
            <span class="stat-pill text-xs text-base-content/60 flex items-center gap-1">
              ✅ {{ linkedCount }} / {{ bankTxs.length }} pointées
            </span>
            <span class="stat-pill text-xs text-base-content/60 flex items-center gap-1">
              🔗 {{ linkedCount }} / {{ realExpenses.length }} liées
            </span>
          </div>
        </div>

        <!-- MOBILE PORTRAIT LAYOUT -->
        <div v-else>
          <!-- Swipe panels -->
          <div ref="swipeContainer" class="flex overflow-x-scroll scroll-snap-x-mandatory bg-base-100" @scroll="onSwipeScroll">

            <!-- Bank panel -->
            <div class="scroll-snap-start flex-none w-full">
              <div
                v-for="b in filteredSortedBankTxs"
                :key="b.id"
                class="mobile-card"
                :class="{
                  'bank-sel': selBankId === b.id && !isLinkedBank(b.id),
                  'is-linked': isLinkedBank(b.id),
                  'is-suggested': !!suggestionForBank(b.id) && !isLinkedBank(b.id),
                }"
                :style="{ backgroundColor: BANK_BG }"
                @click="!isLinkedBank(b.id) && clickBank(b.id)"
              >
                <div class="flex justify-between items-start gap-2">
                  <div class="flex-1 min-w-0">
                    <p class="text-sm font-medium text-base-content truncate">{{ b.label }}</p>
                    <p class="text-xs text-base-content/50 flex flex-wrap gap-1 mt-0.5">
                      {{ fmtDate(b.date) }}
                      <span v-if="isLinkedBank(b.id)" class="badge badge-success badge-xs">✅ pointée</span>
                      <span v-else-if="suggestionForBank(b.id)" class="badge badge-xs" style="background:#ede9fe;color:#7c3aed;">💡 suggestion</span>
                      <span v-else class="badge badge-ghost badge-xs text-base-content/50">⚪ non pointée</span>
                    </p>
                    <p v-if="isLinkedBank(b.id) && linkedExpenseFor(b.id)" class="text-xs text-green-600 mt-0.5">
                      ↔ {{ linkedExpenseFor(b.id)!.label }}
                    </p>
                    <p v-else-if="suggestionForBank(b.id)" class="text-xs mt-0.5" style="color:#7c3aed;">
                      → {{ suggestionForBank(b.id)!.expense.label }}
                    </p>
                  </div>
                  <div class="flex flex-col items-end gap-0.5 shrink-0">
                    <span
                      class="font-bold text-sm"
                      :class="b.amount >= 0 ? 'text-green-400' : 'text-red-400'"
                    >
                      {{ fmtAmt(b.amount) }}
                    </span>
                    <template v-if="isLinkedBank(b.id)">
                      <button
                        class="text-xs text-base-content/40 hover:text-red-500"
                        @click.stop="doUnlink(b.id)"
                      >✕ délier</button>
                    </template>
                    <template v-else-if="suggestionForBank(b.id)">
                      <button
                        class="text-xs font-semibold"
                        style="color:#7c3aed;"
                        @click.stop="confirmSuggestion(b.id, suggestionForBank(b.id)!.expense.id)"
                      >✓ valider</button>
                      <button
                        class="text-xs text-base-content/40 hover:text-red-500"
                        @click.stop="dismissSuggestion(b.id)"
                      >✕ ignorer</button>
                    </template>
                    <template v-if="!isLinkedBank(b.id)">
                      <button
                        class="text-xs text-base-content/25 hover:text-red-500"
                        @click.stop="requestDelete(b.id, 'bank', b.label)"
                      >🗑</button>
                    </template>
                  </div>
                </div>
              </div>
              <div class="border-t border-base-200 bg-base-200 px-4 py-2 text-xs text-base-content/60">
                ✅ {{ linkedCount }} / {{ bankTxs.length }} pointées
              </div>
            </div>

            <!-- Expenses panel -->
            <div class="scroll-snap-start flex-none w-full">
              <template v-for="(e, i) in filteredSortedExpenses" :key="e.id">
                <!-- Blueprint card: inline at the right date position -->
                <div
                  v-if="selBankId !== null && i === mobileBlueprintInsertIndex"
                  ref="mobileBlueprintInlineRef"
                  class="px-3 py-1.5"
                >
                  <button class="blueprint-card slide-in" @click="() => openNewExpenseModal()">
                    <span class="text-4xl leading-none opacity-80">+</span>
                    <span class="text-xs font-semibold tracking-wide opacity-70">Nouvelle dépense liée</span>
                  </button>
                </div>
                <div
                  class="mobile-card"
                  :class="{
                    'exp-sel': selExpId === e.id && !isLinkedExpense(e.id),
                    'is-linked': isLinkedExpense(e.id),
                    'is-suggested': !!suggestionForExpense(e.id) && !isLinkedExpense(e.id),
                    'is-planned': e.status === 'planned' && !isLinkedExpense(e.id),
                  }"
                  :style="expenseBg(e.category_id)"
                  @click="!isLinkedExpense(e.id) && clickExpense(e.id)"
                >
                <div class="flex justify-between items-start gap-2">
                  <div class="flex-1 min-w-0">
                    <p
                      class="text-sm font-medium truncate"
                      :class="e.status === 'planned' ? 'italic text-base-content/60' : 'text-base-content'"
                    >
                      {{ e.label }}
                    </p>
                    <p class="text-xs text-base-content/50 flex flex-wrap gap-1 mt-0.5">
                      <template v-if="e.category_name">{{ e.category_name }} · </template>
                      {{ fmtDate(e.date) }}
                      <span v-if="e.status === 'planned'" class="badge badge-warning badge-xs">🗓 prévu</span>
                      <span v-else-if="isLinkedExpense(e.id)" class="badge badge-success badge-xs">🔗 liée</span>
                      <span v-else-if="suggestionForExpense(e.id)" class="badge badge-xs" style="background:#ede9fe;color:#7c3aed;">💡 suggestion</span>
                      <span v-else class="badge badge-ghost badge-xs text-base-content/50">⚪ non liée</span>
                    </p>
                    <p v-if="e.memo" class="text-xs text-base-content/50 mt-0.5 italic truncate">📝 {{ e.memo }}</p>
                    <p v-if="isLinkedExpense(e.id) && linkedBankFor(e.id)" class="text-xs text-green-600 mt-0.5">
                      ↔ {{ linkedBankFor(e.id)!.label }}
                    </p>
                    <p v-else-if="suggestionForExpense(e.id)" class="text-xs mt-0.5" style="color:#7c3aed;">
                      ← {{ suggestionForExpense(e.id)!.bank_tx.label }}
                    </p>
                  </div>
                  <div class="flex flex-col items-end gap-0.5 shrink-0">
                    <span
                      class="font-bold text-sm"
                      :class="e.amount >= 0 ? 'text-green-400' : 'text-red-400'"
                    >
                      {{ fmtAmt(e.amount) }}
                    </span>
                    <button
                      v-if="isLinkedExpense(e.id)"
                      class="text-xs text-base-content/40 hover:text-red-500"
                      @click.stop="doUnlink(linkedBankFor(e.id)!.id)"
                    >✕ délier</button>
                    <button
                      v-if="!isLinkedExpense(e.id)"
                      class="text-xs text-base-content/25 hover:text-red-500"
                      @click.stop="requestDelete(e.id, 'expense', e.label)"
                    >🗑</button>
                  </div>
                </div>
              </div>
              </template>
              <!-- Blueprint at end if selected bank tx date is older than all expenses -->
              <div
                v-if="selBankId !== null && mobileBlueprintInsertIndex >= filteredSortedExpenses.length"
                ref="mobileBlueprintEndRef"
                class="px-3 py-1.5"
              >
                <button class="blueprint-card slide-in" @click="() => openNewExpenseModal()">
                  <span class="text-4xl leading-none opacity-80">+</span>
                  <span class="text-xs font-semibold tracking-wide opacity-70">Nouvelle dépense liée</span>
                </button>
              </div>
              <div class="border-t border-base-200 bg-base-200 px-4 py-2 text-xs text-base-content/60">
                🔗 {{ linkedCount }} / {{ realExpenses.length }} liées
              </div>
            </div>
          </div>
        </div>

      </div>

      <!-- Legend (desktop) -->
      <div class="hidden sm:flex max-w-7xl mx-auto px-5 mt-2 gap-4 flex-wrap text-xs text-base-content/50">
        <span>💡 Cliquez une transaction bancaire <strong>puis</strong> une dépense pour créer le lien</span>
        <span>·</span>
        <span>✕ Délier = supprimer le lien</span>
      </div>

    </template>

    <!-- ── DELETE CONFIRMATION MODAL ────────────────────────────── -->
    <Teleport to="body">
      <div
        v-if="pendingDelete !== null"
        class="fixed inset-0 z-50 flex items-center justify-center"
        style="background:rgba(0,0,0,.45);backdrop-filter:blur(5px);"
        @click.self="pendingDelete = null"
      >
        <div class="bg-base-100 rounded-2xl shadow-2xl p-7 w-full max-w-sm mx-4">
          <h2 class="text-lg font-bold text-base-content mb-1">🗑 Supprimer ?</h2>
          <p class="text-sm text-base-content/60 mb-1">
            {{ pendingDelete?.kind === 'bank' ? 'Transaction bancaire' : 'Dépense budget' }}
          </p>
          <p class="text-sm font-semibold text-base-content mb-5 truncate">
            {{ pendingDelete?.label }}
          </p>
          <p class="text-xs text-error mb-5">⚠️ Cette action est irréversible.</p>
          <div class="flex gap-2 justify-end">
            <button class="btn btn-ghost btn-sm" @click="pendingDelete = null">Annuler</button>
            <button class="btn btn-error btn-sm" :disabled="linking" @click="executeDelete">
              <span v-if="linking" class="loading loading-spinner loading-xs" />
              Supprimer
            </button>
          </div>
        </div>
      </div>
    </Teleport>

    <!-- ── LINK CONFIRMATION MODAL ───────────────────────────────── -->
    <Teleport to="body">
      <div
        v-if="showLinkModal"
        class="fixed inset-0 z-50 flex items-center justify-center"
        style="background:rgba(0,0,0,.45);backdrop-filter:blur(5px);"
        @click.self="closeLinkModal"
      >
        <div class="bg-base-100 rounded-2xl shadow-2xl p-7 w-full max-w-md mx-4 max-h-[90vh] overflow-y-auto">
          <h2 class="text-xl font-bold text-base-content mb-1">🔗 Confirmer le pointage</h2>
          <p class="text-sm text-base-content/60 mb-4">Vérifiez les informations avant de confirmer.</p>

          <!-- Bank tx -->
          <div v-if="modalBank" class="rounded-xl bg-info/10 border border-info/20 p-4 mb-3">
            <p class="text-xs font-bold text-info uppercase tracking-wide mb-2">🏦 Transaction bancaire</p>
            <div class="flex justify-between items-start gap-2">
              <div>
                <p class="font-semibold text-sm text-base-content">{{ modalBank.label }}</p>
                <p class="text-xs text-base-content/50 mt-0.5">{{ fmtDate(modalBank.date) }}</p>
              </div>
              <span
                class="font-bold text-base shrink-0"
                :class="modalBank.amount >= 0 ? 'text-green-600' : 'text-red-600'"
              >
                {{ fmtAmt(modalBank.amount) }}
              </span>
            </div>
          </div>

          <!-- Expense -->
          <div v-if="modalExpense" class="rounded-xl bg-success/10 border border-success/20 p-4 mb-3">
            <p class="text-xs font-bold text-success uppercase tracking-wide mb-2">💸 Dépense budget</p>
            <div class="flex justify-between items-start gap-2">
              <div>
                <p class="font-semibold text-sm text-base-content">{{ modalExpense.label }}</p>
                <p class="text-xs text-base-content/50 mt-0.5">
                  <template v-if="modalExpense.category_name">{{ modalExpense.category_name }} · </template>
                  {{ fmtDate(modalExpense.date) }}
                </p>
              </div>
              <span
                class="font-bold text-sm shrink-0"
                :class="modalExpense.amount >= 0 ? 'text-green-600' : 'text-red-600'"
              >
                {{ fmtAmt(modalExpense.amount) }}
              </span>
            </div>
          </div>

          <!-- Amount delta warning -->
          <div v-if="modalHasDelta" class="rounded-xl border border-warning/30 bg-warning/10 p-4 mb-3">
            <p class="text-sm font-semibold text-warning mb-3">⚠️ Écart de montant détecté</p>
            <label class="flex items-start gap-3 cursor-pointer mb-2">
              <input v-model="modalAdjust" type="radio" :value="false" class="radio radio-sm radio-warning mt-0.5">
              <span class="text-sm text-base-content/80">
                Conserver le montant de la dépense <strong class="text-base-content">{{ modalExpense ? fmtAmt(modalExpense.amount) : '' }}</strong>
              </span>
            </label>
            <label class="flex items-start gap-3 cursor-pointer">
              <input v-model="modalAdjust" type="radio" :value="true" class="radio radio-sm radio-warning mt-0.5">
              <span class="text-sm text-base-content/80">
                Mettre à jour avec le montant bancaire <strong class="text-base-content">{{ modalBank ? fmtAmt(modalBank.amount) : '' }}</strong>
                <span class="text-xs text-warning/80 ml-1">(recommandé — la banque fait foi)</span>
              </span>
            </label>
          </div>

          <!-- Memo -->
          <div class="form-control mb-4">
            <label class="label py-1">
              <span class="label-text text-sm font-medium">Mémo (optionnel)</span>
            </label>
            <input
              v-model="modalMemo"
              type="text"
              placeholder="Note sur ce pointage…"
              class="input input-bordered input-sm w-full"
            >
          </div>

          <!-- Actions -->
          <div class="flex gap-2 justify-end">
            <button class="btn btn-ghost btn-sm" @click="closeLinkModal">Annuler</button>
            <button class="btn btn-primary btn-sm" :disabled="linking" @click="confirmLinkModal">
              <span v-if="linking" class="loading loading-spinner loading-xs" />
              ✅ Confirmer
            </button>
          </div>
        </div>
      </div>
    </Teleport>

    <!-- ── NEW EXPENSE MODAL ─────────────────────────────────────── -->
    <Teleport to="body">
      <div
        v-if="showNewExpenseModal"
        class="fixed inset-0 z-50 flex items-center justify-center"
        style="background:rgba(0,0,0,.45);backdrop-filter:blur(5px);"
        @click.self="closeNewExpenseModal"
      >
        <div class="bg-base-100 rounded-2xl shadow-2xl w-full mx-4 overflow-y-auto new-expense-modal-box" style="max-height:92vh;max-width:28rem;padding:1.75rem;">
          <h2 class="text-xl font-bold text-base-content mb-0.5">✨ Nouvelle dépense</h2>
          <p v-if="wizardBank" class="text-sm text-base-content/60 mb-4">
            Créer et lier à "{{ titleCase(wizardBank.label) }}"
          </p>

          <!-- Bank tx info + expense form (side by side in landscape) -->
          <div class="new-expense-cols">
            <!-- Bank tx info -->
            <div
              v-if="wizardBank"
              class="rounded-xl bg-info/10 border border-info/20 p-4 mb-3"
            >
              <p class="text-xs font-bold text-info uppercase tracking-wide mb-2">🏦 Transaction bancaire</p>
              <div class="flex justify-between items-start gap-2">
                <div>
                  <p class="font-semibold text-sm text-base-content">
                    {{ wizardBank.label }}
                  </p>
                  <p class="text-xs text-base-content/50 mt-0.5">
                    {{ fmtDate(wizardBank.date) }}
                  </p>
                </div>
                <span
                  class="font-bold text-base shrink-0"
                  :class="wizardBank.amount >= 0 ? 'text-green-600' : 'text-red-600'"
                >
                  {{ fmtAmt(wizardBank.amount) }}
                </span>
              </div>
            </div>

            <!-- New expense form -->
            <div class="rounded-xl bg-success/10 border border-success/20 p-4 mb-3">
              <p class="text-xs font-bold text-success uppercase tracking-wide mb-2">💸 Dépense budget</p>
              <div class="flex flex-col gap-2">
                <input
                  v-model="newExpLabel"
                  type="text"
                  placeholder="Libellé…"
                  class="input input-bordered input-sm w-full"
                >
                <div class="flex gap-2 items-center">
                  <div class="flex-1">
                    <CategoryPicker
                      v-model="newExpCategoryId"
                      :groups="allCategoryGroups"
                      @category-created="onCategoryCreated"
                    />
                  </div>
                  <input
                    v-model.number="newExpAmount"
                    type="number"
                    step="0.01"
                    min="0"
                    placeholder="Montant"
                    class="input input-bordered input-sm w-28"
                  >
                </div>
                <p v-if="suggestedCategoryName" class="text-xs text-info flex items-center gap-1">
                  💡 Catégorie suggérée : <strong>{{ suggestedCategoryName }}</strong>
                </p>
              </div>
            </div>
          </div><!-- end .new-expense-cols -->

          <!-- Rule preview: shown when the bank label yields a usable pattern -->
          <div
            v-if="wizardBank?.rule_pattern"
            class="rounded-xl p-3 mb-3"
            style="background:oklch(var(--wa)/0.07);border:1px solid oklch(var(--wa)/0.3);"
          >
            <div class="flex items-center justify-between mb-1">
              <p class="text-xs font-bold uppercase tracking-wide" style="color:oklch(var(--wa));">
                🏷️ Règle de catégorisation
              </p>
              <label class="flex items-center gap-1.5 cursor-pointer">
                <span class="text-xs text-base-content/60">{{ createRuleEnabled ? 'Créer' : 'Ne pas créer' }}</span>
                <input v-model="createRuleEnabled" type="checkbox" class="toggle toggle-xs toggle-warning" />
              </label>
            </div>
            <p class="text-xs font-mono text-base-content/80 mb-3 truncate">
              contient <strong>« {{ wizardBank.rule_pattern }} »</strong>
            </p>

            <!-- Options (only when rule creation is enabled) -->
            <template v-if="createRuleEnabled">
            <!-- Transaction type -->
            <p class="text-xs font-semibold text-base-content/60 mb-1">Type de transaction :</p>
            <div class="flex flex-wrap gap-x-3 gap-y-1 mb-2">
              <label class="flex items-center gap-1 cursor-pointer">
                <input v-model="ruleTransactionType" type="radio" value="any" class="radio radio-xs" />
                <span class="text-xs">Toutes</span>
              </label>
              <label class="flex items-center gap-1 cursor-pointer">
                <input v-model="ruleTransactionType" type="radio" value="debit" class="radio radio-xs" />
                <span class="text-xs">Dépenses (négatives)</span>
              </label>
              <label class="flex items-center gap-1 cursor-pointer">
                <input v-model="ruleTransactionType" type="radio" value="credit" class="radio radio-xs" />
                <span class="text-xs">Revenus (positifs)</span>
              </label>
            </div>

            <!-- Amount constraint -->
            <p class="text-xs font-semibold text-base-content/60 mb-1">Contrainte de montant :</p>
            <div class="flex flex-col gap-1">
              <label class="flex items-center gap-1 cursor-pointer">
                <input v-model="ruleAmountMode" type="radio" value="none" class="radio radio-xs" />
                <span class="text-xs">Sans contrainte</span>
              </label>
              <label class="flex items-center gap-1 cursor-pointer">
                <input v-model="ruleAmountMode" type="radio" value="exact" class="radio radio-xs" />
                <span class="text-xs">Ce montant exactement ({{ fmtAmt(Math.abs(wizardBank.amount)) }})</span>
              </label>
              <label class="flex items-center gap-1.5 cursor-pointer">
                <input v-model="ruleAmountMode" type="radio" value="percent" class="radio radio-xs" />
                <span class="text-xs">±</span>
                <input
                  v-model.number="ruleAmountTolerancePct"
                  type="number"
                  min="1"
                  max="99"
                  class="input input-xs input-bordered w-14"
                  :disabled="ruleAmountMode !== 'percent'"
                  @click.stop
                />
                <span class="text-xs">%</span>
              </label>
            </div>
            </template>
          </div>

          <p v-if="newExpCategoryId === null" class="text-xs text-error mt-1 mb-2">
            ⚠️ La catégorie est obligatoire.
          </p>
          <div class="flex gap-2 justify-end">
            <button class="btn btn-ghost btn-sm" @click="closeNewExpenseModal">Annuler</button>
            <button
              class="btn btn-primary btn-sm"
              :disabled="linking || newExpCategoryId === null"
              @click="confirmNewExpense"
            >
              <span v-if="linking" class="loading loading-spinner loading-xs" />
              ✅ Confirmer
            </button>
          </div>
        </div>
      </div>
    </Teleport>

    <!-- ── CLÔTURE SUCCESS MODAL ─────────────────────────────────── -->
    <Teleport to="body">
      <div
        v-if="showClotureModal"
        class="fixed inset-0 z-50 flex items-center justify-center"
        style="background:rgba(0,0,0,.45);backdrop-filter:blur(5px);"
        @click.self="showClotureModal = false"
      >
        <div class="bg-base-100 rounded-2xl shadow-2xl p-7 w-full max-w-sm mx-4 text-center">
          <div class="text-6xl mb-4">🎉</div>
          <h2 class="text-xl font-bold text-base-content mb-2">Pointage clôturé !</h2>
          <p class="text-sm text-base-content/60 mb-6">
            Le mois de <span class="font-semibold capitalize">{{ monthLabel }}</span> a été marqué comme clôturé.
          </p>
          <div v-if="clotureResult" class="bg-base-200 rounded-xl p-3 text-left mb-4">
            <p class="text-xs text-base-content/60 mb-2">Résumé du pointage</p>
            <div class="flex justify-between text-sm text-base-content/80">
              <span>✅ {{ clotureResult.linked_count }}/{{ clotureResult.total_bank_txs }} pointées</span>
              <span>🔗 {{ clotureResult.linked_count }}/{{ clotureResult.total_expenses }} liées</span>
            </div>
          </div>
          <button class="btn btn-primary w-full" @click="showClotureModal = false">Fermer</button>
        </div>
      </div>
    </Teleport>

    <!-- Rules modal -->
    <RulesModal
      v-if="showRulesModal"
      :category-groups="allCategoryGroups"
      @close="showRulesModal = false"
      @changed="rulesCount = $event; loadView(true)"
    />

    <!-- Import modal -->
    <ImportModal
      :initial-account-id="selectedAccountId"
      v-if="showImportModal"
      @close="showImportModal = false"
      @imported="loadView()"
    />

  </div>
  </div>
</template>

<style scoped>
/* ── Cards ────────────────────────────────────────────────────────── */
.bank-card, .expense-card {
  border: 2px solid transparent;
  border-radius: 10px;
  padding: 10px 14px;
  cursor: pointer;
  transition: border-color .15s, background-color .15s, box-shadow .15s;
}
.bank-card:hover:not(.is-linked)    { border-color: oklch(var(--in) / 0.5); background-color: oklch(var(--in) / 0.1); }
.expense-card:hover:not(.is-linked) { border-color: oklch(var(--wa) / 0.5); background-color: oklch(var(--wa) / 0.1); }
.bank-card.is-selected              { border-color: #38bdf8 !important; background-color: rgba(56,189,248,0.12) !important; box-shadow: 0 0 0 3px rgba(56,189,248,0.25); }
.expense-card.is-selected           { border-color: oklch(var(--wa)) !important; background-color: oklch(var(--wa) / 0.18) !important; box-shadow: 0 0 0 3px oklch(var(--wa) / 0.25); }
.bank-card.is-linked,
.expense-card.is-linked             { border-color: oklch(var(--su) / 0.55); cursor: default; opacity: 0.9; }
.bank-card.is-linked:hover,
.expense-card.is-linked:hover       { border-color: oklch(var(--su) / 0.55); }
.expense-card.is-planned            { border-style: dashed; border-color: oklch(var(--bc) / 0.2); background-color: oklch(var(--bc) / 0.04); }
.expense-card.is-planned:hover:not(.is-linked) { border-color: oklch(var(--wa) / 0.5); background-color: oklch(var(--wa) / 0.1); }

/* ── Rule match bank card ────────────────────────────────────────── */
.bank-card.is-rule-match {
  border-color: oklch(var(--wa) / 0.4);
  border-style: dashed;
}
.bank-card.is-rule-match:hover { border-color: oklch(var(--wa) / 0.9) !important; }

/* ── Rule match virtual expense card ────────────────────────────── */
.rule-match-blueprint {
  border: 2px dashed oklch(var(--wa) / 0.6);
  border-radius: 10px;
  padding: 10px 14px;
  cursor: pointer;
  opacity: 0.82;
  transition: border-color .15s, opacity .15s;
}
.rule-match-blueprint:hover {
  border-color: oklch(var(--wa) / 1);
  opacity: 1;
}

/* ── Suggestions ─────────────────────────────────────────────────── */
.bank-card.is-suggested,
.expense-card.is-suggested {
  border-color: oklch(var(--p) / 0.5);
  border-style: dashed;
}
.bank-card.is-suggested:hover   { border-color: oklch(var(--p) / 0.9) !important; }
.expense-card.is-suggested:hover { border-color: oklch(var(--p) / 0.9) !important; }

.sugg-col {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  gap: 1px;
  user-select: none;
  background: none;
  border: none;
  padding: 4px;
  border-radius: 6px;
  transition: background-color .12s;
}
.sugg-col:hover { background-color: #ede9fe; }
.sugg-col:hover .sugg-icon { color: #6d28d9 !important; }
.sugg-col:hover .sugg-lbl  { color: #6d28d9 !important; }

/* ── Mobile cards ────────────────────────────────────────────────── */
.mobile-card {
  border: 2px solid rgba(255,255,255,0.07);
  border-radius: 10px;
  margin: 6px 12px;
  padding: 10px 14px;
  cursor: pointer;
  transition: background-color .12s, border-color .12s, box-shadow .12s;
}
.mobile-card:hover:not(.is-linked) { border-color: rgba(255,255,255,0.18); }
.mobile-card.bank-sel  { border-color: oklch(var(--in)); box-shadow: 0 0 0 2px oklch(var(--in)/0.2); }
.mobile-card.exp-sel   { border-color: oklch(var(--wa)); box-shadow: 0 0 0 2px oklch(var(--wa)/0.2); }
.mobile-card.is-linked { border-color: oklch(var(--su)); cursor: default; opacity: 0.9; }
.mobile-card.is-planned   { opacity: .75; }
.mobile-card.is-suggested { border-color: oklch(var(--p)); border-style: dashed; }

/* ── Blueprint row background ─────────────────────────────────────── */
.blueprint-row { background-color: oklch(var(--in) / 0.08); }

/* ── Blueprint card (architectural blueprint look, same as budget page) ─── */
.blueprint-card {
  background:
    linear-gradient(rgba(255, 255, 255, 0.08) 1px, transparent 1px),
    linear-gradient(90deg, rgba(255, 255, 255, 0.08) 1px, transparent 1px),
    linear-gradient(135deg, #1e3a5f, #1a2f4a);
  background-size: 20px 20px, 20px 20px, 100% 100%;
  border: 2px dashed rgba(100, 160, 230, 0.5);
  border-radius: 10px;
  color: rgba(140, 190, 255, 0.9);
  box-shadow: inset 0 0 30px rgba(0, 0, 0, 0.15);
  cursor: pointer;
  width: 100%;
  min-height: 72px;
  padding: 14px 16px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 4px;
  transition: border-color 0.15s;
}
.blueprint-card:hover {
  border-color: rgba(100, 160, 230, 0.9);
}

/* ── Slide-in animation ───────────────────────────────────────────── */
@keyframes slideDown {
  from {
    opacity: 0;
    transform: translateY(-10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}
.slide-in {
  animation: slideDown 0.3s ease-out;
}

/* ── Link animation ──────────────────────────────────────────────── */
@keyframes matchGlow {
  0%   { box-shadow: inset 0 0 0 2px #4ade80, 0 0 12px #bbf7d0; background-color: #dcfce7 !important; }
  70%  { box-shadow: inset 0 0 0 2px #4ade80, 0 0 6px #bbf7d0;  background-color: #f0fdf4 !important; }
  100% { box-shadow: none; background-color: transparent !important; }
}
.match-anim { animation: matchGlow 1.4s ease-out forwards; }

/* ── Slide-down transition ───────────────────────────────────────── */
.slide-down-enter-active, .slide-down-leave-active { transition: all .2s ease; }
.slide-down-enter-from, .slide-down-leave-to { opacity: 0; transform: translateY(-8px); }

/* ── Mobile swipe scroll ─────────────────────────────────────────── */
.scroll-snap-x-mandatory { scroll-snap-type: x mandatory; -webkit-overflow-scrolling: touch; }
.scroll-snap-x-mandatory::-webkit-scrollbar { display: none; }
.scroll-snap-x-mandatory { scrollbar-width: none; }
.scroll-snap-start { scroll-snap-align: start; }

/* ── New expense modal — landscape layout ────────────────────────── */
/* Portrait default: single column, compact */
.new-expense-cols { display: flex; flex-direction: column; }

/* Landscape on small screen (mobile): 2 columns side by side */
@media (orientation: landscape) and (max-height: 600px) {
  /* Cell wrapper: reduce vertical padding so cards stay compact */
  .recon-cell { padding-top: 3px !important; padding-bottom: 3px !important; min-height: 0 !important; }
  /* Blueprint: same fixed height as cards */
  .blueprint-card { height: 52px; min-height: 0; padding: 6px 10px; gap: 2px; }
  .blueprint-card .bp-icon { font-size: 1.2rem; }
  .blueprint-card .bp-label { font-size: 0.6rem; }
  /* Cards: fixed height, overflow hidden — font scales via Vue */
  .bank-card, .expense-card { padding: 6px 10px; height: 52px; overflow: hidden; }
  /* Sub-text smaller */
  .bank-card .card-sub,
  .expense-card .card-sub { font-size: 0.6rem; line-height: 1.2; margin-top: 1px; }
  .card-memo { font-size: 0.6rem; line-height: 1.2; margin-top: 1px; }
}
@media (orientation: landscape) and (max-height: 600px) {
  .new-expense-modal-box {
    max-width: min(90vw, 680px) !important;
    max-height: 96vh !important;
    padding: 16px 20px !important;
  }
  .new-expense-cols {
    flex-direction: row;
    gap: 12px;
    align-items: flex-start;
  }
  .new-expense-cols > * {
    flex: 1;
    min-width: 0;
    margin-bottom: 0 !important;
  }
}
</style>
