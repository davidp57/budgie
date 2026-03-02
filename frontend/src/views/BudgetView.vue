<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { getMonthBudget, setMonthBudget } from '@/api/budget'
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

// Track edits: category_id → new budgeted value (centimes)
const edits = ref<Record<number, number>>({})

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
      category_id: Number(id),
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
  edits.value[envelope.category_id] = value
}

// Group envelopes by group_id for display
function groupedEnvelopes(): Array<{ group_name: string; envelopes: EnvelopeLine[] }> {
  if (!budget.value) return []
  const map = new Map<string, EnvelopeLine[]>()
  for (const env of budget.value.envelopes) {
    const key = env.group_name
    if (!map.has(key)) map.set(key, [])
    map.get(key)!.push(env)
  }
  return Array.from(map.entries()).map(([group_name, envelopes]) => ({ group_name, envelopes }))
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

    <!-- To be budgeted banner -->
    <div
      v-if="budget"
      class="alert mb-4"
      :class="budget.to_be_budgeted >= 0 ? 'alert-success' : 'alert-error'"
    >
      <span class="font-semibold">To be budgeted:</span>
      {{ formatAmount(budget.to_be_budgeted) }}
    </div>

    <div v-if="loading" class="flex justify-center py-12">
      <span class="loading loading-spinner loading-lg"></span>
    </div>

    <div v-else-if="error" class="alert alert-error">{{ error }}</div>

    <template v-else-if="budget">
      <div v-if="budget.envelopes.length === 0" class="text-base-content/50 text-center py-12">
        No categories yet. Add categories in Settings.
      </div>

      <div v-else class="flex flex-col gap-4">
        <!-- Column headers -->
        <div class="hidden sm:grid grid-cols-[1fr_120px_120px_120px] gap-2 px-4 text-sm text-base-content/50 font-medium">
          <span>Category</span>
          <span class="text-right">Budgeted</span>
          <span class="text-right">Activity</span>
          <span class="text-right">Available</span>
        </div>

        <div v-for="group in groupedEnvelopes()" :key="group.group_name" class="card bg-base-100 shadow">
          <div class="card-body p-3">
            <h3 class="font-semibold text-sm text-base-content/60 uppercase tracking-wide mb-2">
              {{ group.group_name }}
            </h3>
            <EnvelopeCard
              v-for="envelope in group.envelopes"
              :key="envelope.category_id"
              :envelope="envelope"
              :edited-value="edits[envelope.category_id]"
              @edit="(v) => onEdit(envelope, v)"
            />
          </div>
        </div>
      </div>
    </template>
  </div>
</template>
