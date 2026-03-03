<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { getMonthBudget, setMonthBudget } from '@/api/budget'
import { createEnvelope } from '@/api/envelopes'
import { formatAmount, type EnvelopeLine, type MonthBudget } from '@/api/types'
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

// Track edits: envelope_id → new budgeted value (centimes)
const edits = ref<Record<number, number>>({})

// New envelope creation
const addingEnvelope = ref(false)
const newEnvelopeName = ref('')
const newEnvelopeRollover = ref(false)
const creatingEnvelope = ref(false)

async function load(month: string): Promise<void> {
  loading.value = true
  error.value = ''
  edits.value = {}
  try {
    budget.value = await getMonthBudget(month)
  } catch {
    error.value = 'Failed to load budget.'
  } finally {
    loading.value = false
  }
}

onMounted(() => load(currentMonth.value))

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
</script>

<template>
  <div>
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
      <!-- Total available across all envelopes -->
      <div
        class="alert flex-1 min-w-40"
        :class="budget.total_available >= 0 ? 'alert-success' : 'alert-error'"
      >
        <span class="font-semibold">Available:</span>
        {{ formatAmount(budget.total_available) }}
      </div>
      <!-- To be budgeted (income vs allocated) -->
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

      <!-- Envelope list (flat, ordered by sort_order from backend) -->
      <div class="card bg-base-100 shadow mb-4">
        <div class="card-body p-3">
          <EnvelopeCard
            v-for="envelope in budget.envelopes"
            :key="envelope.envelope_id"
            :envelope="envelope"
            :edited-value="edits[envelope.envelope_id]"
            @edit="(v) => onEdit(envelope, v)"
          />

          <div
            v-if="budget.envelopes.length === 0"
            class="text-base-content/50 text-center py-6 text-sm"
          >
            No envelopes yet. Create one to start budgeting.
          </div>
        </div>
      </div>

      <!-- Add envelope row -->
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
            <input
              v-model="newEnvelopeRollover"
              type="checkbox"
              class="checkbox checkbox-xs"
            />
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
</template>
