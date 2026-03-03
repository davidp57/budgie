<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import { getMonthBudget, setMonthBudget } from '@/api/budget'
import { createEnvelope } from '@/api/envelopes'
import { listTransactions } from '@/api/transactions'
import { formatAmount, type EnvelopeLine, type MonthBudget, type Transaction } from '@/api/types'
import MonthPicker from '@/components/MonthPicker.vue'
import EnvelopeCard from '@/components/EnvelopeCard.vue'

const today = new Date()
const currentMonth = ref(
  `${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, '0')}`,
)

const budget = ref<MonthBudget | null>(null)
const loading = ref(true)
const saving = ref(false)
const error = ref('')

// Track edits: envelope_id â†’ new budgeted value (centimes)
const edits = ref<Record<number, number>>({})

// New envelope creation
const addingEnvelope = ref(false)
const newEnvelopeName = ref('')
const newEnvelopeRollover = ref(false)
const creatingEnvelope = ref(false)

// â”€â”€ Envelope selection â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
const selectedEnvelopeId = ref<number | null>(null)

function selectEnvelope(id: number): void {
  selectedEnvelopeId.value = selectedEnvelopeId.value === id ? null : id
}

/** Category IDs for the selected envelope (or all categories if none selected) */
const activeCategoryIds = computed<number[] | undefined>(() => {
  if (!budget.value || selectedEnvelopeId.value === null) return undefined
  const env = budget.value.envelopes.find((e) => e.envelope_id === selectedEnvelopeId.value)
  return env ? env.categories.map((c) => c.id) : undefined
})

// â”€â”€ Category name lookup map â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
const categoryMap = computed<Map<number, string>>(() => {
  const m = new Map<number, string>()
  if (!budget.value) return m
  for (const env of budget.value.envelopes) {
    for (const cat of env.categories) m.set(cat.id, cat.name)
  }
  return m
})

// â”€â”€ Transactions panel â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
const transactions = ref<Transaction[]>([])
const txnLoading = ref(false)

async function loadTransactions(): Promise<void> {
  txnLoading.value = true
  try {
    transactions.value = await listTransactions({
      month: currentMonth.value,
      categoryIds: activeCategoryIds.value,
    })
  } finally {
    txnLoading.value = false
  }
}

// â”€â”€ Resizable panel â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
const panelHeight = ref(220)
const isDragging = ref(false)
const dragStartY = ref(0)
const dragStartHeight = ref(0)

function startDrag(e: PointerEvent): void {
  isDragging.value = true
  dragStartY.value = e.clientY
  dragStartHeight.value = panelHeight.value
  ;(e.target as HTMLElement).setPointerCapture(e.pointerId)
}

function onDrag(e: PointerEvent): void {
  if (!isDragging.value) return
  const delta = dragStartY.value - e.clientY
  panelHeight.value = Math.max(80, Math.min(600, dragStartHeight.value + delta))
}

function stopDrag(): void {
  isDragging.value = false
}

// â”€â”€ Data loading â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
async function load(month: string): Promise<void> {
  loading.value = true
  error.value = ''
  edits.value = {}
  selectedEnvelopeId.value = null
  try {
    budget.value = await getMonthBudget(month)
  } catch {
    error.value = 'Failed to load budget.'
  } finally {
    loading.value = false
  }
  await loadTransactions()
}

onMounted(() => load(currentMonth.value))

// Reload transactions when envelope selection or month changes
watch(activeCategoryIds, () => loadTransactions())

function onMonthChange(month: string): void {
  currentMonth.value = month
  load(month)
}

async function saveAll(): Promise<void> {
  if (!budget.value) return
  saving.value = true
  try {
    const lines = Object.entries(edits.value).map(([id, budgeted]) => ({
      envelope_id: Number(id),
      budgeted,
    }))
    if (lines.length > 0) {
      await setMonthBudget(currentMonth.value, lines)
      await load(currentMonth.value)
    }
  } catch {
    error.value = 'Failed to save budget.'
  } finally {
    saving.value = false
  }
}

function onEdit(envelope: EnvelopeLine, value: number): void {
  edits.value[envelope.envelope_id] = value
}

async function submitNewEnvelope(): Promise<void> {
  const name = newEnvelopeName.value.trim()
  if (!name) return
  creatingEnvelope.value = true
  try {
    await createEnvelope({ name, rollover: newEnvelopeRollover.value })
    newEnvelopeName.value = ''
    newEnvelopeRollover.value = false
    addingEnvelope.value = false
    await load(currentMonth.value)
  } catch {
    error.value = 'Failed to create envelope.'
  } finally {
    creatingEnvelope.value = false
  }
}

onUnmounted(() => {
  isDragging.value = false
})
</script>

<template>
  <div class="flex flex-col" style="min-height: calc(100vh - 6rem)">
    <!-- â”€â”€ Top: scrollable budget content â”€â”€ -->
    <div class="flex-1 overflow-auto pb-2">
      <div class="flex items-center justify-between mb-6">
        <h1 class="text-2xl font-bold">Budget</h1>
        <div class="flex gap-2 items-center">
          <MonthPicker :model-value="currentMonth" @update:model-value="onMonthChange" />
          <button
            v-if="Object.keys(edits).length > 0"
            class="btn btn-primary btn-sm"
            :disabled="saving"
            @click="saveAll"
          >
            <span v-if="saving" class="loading loading-spinner loading-xs"></span>
            Save
          </button>
        </div>
      </div>

      <!-- Summary banner -->
      <div v-if="budget" class="flex flex-wrap gap-2 mb-4">
        <div
          class="alert flex-1 min-w-40"
          :class="budget.total_available >= 0 ? 'alert-success' : 'alert-error'"
        >
          <span class="font-semibold">Available:</span>
          {{ formatAmount(budget.total_available) }}
        </div>
        <div
          class="alert flex-1 min-w-40"
          :class="
            budget.to_be_budgeted > 0
              ? 'alert-warning'
              : budget.to_be_budgeted < 0
                ? 'alert-error'
                : 'alert-success'
          "
        >
          <span class="font-semibold">To budget:</span>
          {{ formatAmount(budget.to_be_budgeted) }}
        </div>
      </div>

      <div v-if="loading" class="flex justify-center py-12">
        <span class="loading loading-spinner loading-lg"></span>
      </div>

      <div v-else-if="error" class="alert alert-error">{{ error }}</div>

      <template v-else-if="budget">
        <!-- Column headers -->
        <div
          v-if="budget.envelopes.length > 0"
          class="hidden sm:grid grid-cols-[1fr_120px_120px_120px] gap-2 px-4 mb-1 text-sm text-base-content/50 font-medium"
        >
          <span>Envelope</span>
          <span class="text-right">Budgeted</span>
          <span class="text-right">Activity</span>
          <span class="text-right">Available</span>
        </div>

        <!-- Envelope list -->
        <div class="card bg-base-100 shadow mb-4">
          <div class="card-body p-3">
            <EnvelopeCard
              v-for="envelope in budget.envelopes"
              :key="envelope.envelope_id"
              :envelope="envelope"
              :edited-value="edits[envelope.envelope_id]"
              :selected="selectedEnvelopeId === envelope.envelope_id"
              @edit="(v) => onEdit(envelope, v)"
              @select="selectEnvelope"
            />
            <div
              v-if="budget.envelopes.length === 0"
              class="text-base-content/50 text-center py-6 text-sm"
            >
              No envelopes yet. Create one to start budgeting.
            </div>
          </div>
        </div>

        <!-- Add envelope -->
        <div v-if="!addingEnvelope" class="flex justify-start">
          <button class="btn btn-ghost btn-sm text-primary" @click="addingEnvelope = true">
            + Add envelope
          </button>
        </div>
        <div v-else class="card bg-base-100 shadow p-3">
          <div class="flex flex-wrap gap-2 items-center">
            <input
              v-model="newEnvelopeName"
              type="text"
              class="input input-bordered input-sm flex-1 min-w-[160px]"
              placeholder="Envelope name"
              autofocus
              @keyup.enter="submitNewEnvelope"
              @keyup.escape="addingEnvelope = false"
            />
            <label class="flex items-center gap-1 text-sm select-none cursor-pointer">
              <input v-model="newEnvelopeRollover" type="checkbox" class="checkbox checkbox-xs" />
              Rollover
            </label>
            <button
              class="btn btn-primary btn-sm"
              :disabled="creatingEnvelope || !newEnvelopeName.trim()"
              @click="submitNewEnvelope"
            >
              <span v-if="creatingEnvelope" class="loading loading-spinner loading-xs"></span>
              Create
            </button>
            <button class="btn btn-ghost btn-sm" @click="addingEnvelope = false">Cancel</button>
          </div>
        </div>
      </template>
    </div>

    <!-- â”€â”€ Drag handle â”€â”€ -->
    <div
      class="flex items-center justify-center h-3 cursor-row-resize bg-base-300/60 hover:bg-primary/30 transition-colors select-none shrink-0"
      :class="isDragging ? 'bg-primary/40' : ''"
      @pointerdown="startDrag"
      @pointermove="onDrag"
      @pointerup="stopDrag"
    >
      <div class="w-10 h-1 rounded-full bg-base-content/20"></div>
    </div>

    <!-- â”€â”€ Bottom: transactions panel â”€â”€ -->
    <div
      class="bg-base-100 border-t border-base-300 overflow-auto shrink-0"
      :style="{ height: panelHeight + 'px' }"
    >
      <div class="sticky top-0 bg-base-100 z-10 px-4 py-2 border-b border-base-300 flex items-center gap-2">
        <span class="text-sm font-semibold text-base-content/70">Transactions</span>
        <span v-if="selectedEnvelopeId !== null" class="badge badge-sm badge-primary">
          {{
            budget?.envelopes.find((e) => e.envelope_id === selectedEnvelopeId)?.envelope_name
          }}
          <button class="ml-1 opacity-60 hover:opacity-100" @click="selectedEnvelopeId = null">âœ•</button>
        </span>
        <span v-else class="text-xs text-base-content/40">â€” click an envelope to filter</span>
        <span v-if="txnLoading" class="loading loading-spinner loading-xs ml-auto"></span>
        <span v-else class="text-xs text-base-content/40 ml-auto">{{ transactions.length }} transactions</span>
      </div>

      <table v-if="transactions.length > 0" class="table table-xs w-full">
        <thead>
          <tr>
            <th>Date</th>
            <th>Memo</th>
            <th class="text-right">Amount</th>
            <th>Category</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="txn in transactions" :key="txn.id" :class="txn.is_virtual ? 'opacity-60' : ''">
            <td class="tabular-nums whitespace-nowrap">{{ txn.date }}</td>
            <td class="max-w-xs truncate">{{ txn.memo ?? 'â€”' }}</td>
            <td
              class="text-right tabular-nums"
              :class="txn.amount < 0 ? 'text-error' : 'text-success'"
            >
              {{ formatAmount(txn.amount) }}
            </td>
            <td class="text-base-content/60 text-xs">
              {{ txn.category_id !== null ? (categoryMap.get(txn.category_id) ?? '?') : 'â€”' }}
            </td>
          </tr>
        </tbody>
      </table>

      <div
        v-else-if="!txnLoading"
        class="text-center text-base-content/40 text-sm py-6"
      >
        No transactions for this period.
      </div>
    </div>
  </div>
</template>
