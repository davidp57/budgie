<script setup lang="ts">
/**
 * EnvelopeManager — Settings panel to create/edit/delete budget envelopes
 * and assign categories to them.
 *
 * Props:
 *   groups — all category groups with their categories (for the multi-select)
 */
import { onMounted, ref } from 'vue'
import { createEnvelope, deleteEnvelope, listEnvelopes, updateEnvelope } from '@/api/envelopes'
import type { CategoryGroupWithCategories, Envelope } from '@/api/types'

defineProps<{
  groups: CategoryGroupWithCategories[]
}>()

const envelopes = ref<Envelope[]>([])
const error = ref('')
const saving = ref(false)

// ── Edit state ────────────────────────────────────────────────────
const editingId = ref<number | null>(null)
const editName = ref('')
const editRollover = ref(false)
const editCategoryIds = ref<number[]>([])
const editTargetAmount = ref<number | null>(null)

// ── New envelope form ─────────────────────────────────────────────
const addingEnvelope = ref(false)
const newName = ref('')
const newRollover = ref(false)
const newCategoryIds = ref<number[]>([])
const newTargetAmount = ref<number | null>(null)

async function load(): Promise<void> {
  envelopes.value = await listEnvelopes()
}

onMounted(load)

function startEdit(env: Envelope): void {
  editingId.value = env.id
  editName.value = env.name
  editRollover.value = env.rollover
  editCategoryIds.value = env.categories.map((c) => c.id)
  editTargetAmount.value = env.target_amount ? env.target_amount / 100 : null
}

function cancelEdit(): void {
  editingId.value = null
}

async function saveEdit(): Promise<void> {
  if (!editingId.value) return
  saving.value = true
  error.value = ''
  try {
    await updateEnvelope(editingId.value, {
      name: editName.value.trim(),
      rollover: editRollover.value,
      category_ids: editCategoryIds.value,
      target_amount: editTargetAmount.value != null ? Math.round(editTargetAmount.value * 100) : null,
    })
    editingId.value = null
    await load()
  } catch {
    error.value = 'Failed to update envelope.'
  } finally {
    saving.value = false
  }
}

async function remove(id: number): Promise<void> {
  if (!confirm('Delete this envelope? Its budget allocations will also be removed.')) return
  error.value = ''
  try {
    await deleteEnvelope(id)
    await load()
  } catch {
    error.value = 'Failed to delete envelope.'
  }
}

async function submitNew(): Promise<void> {
  if (!newName.value.trim()) return
  saving.value = true
  error.value = ''
  try {
    await createEnvelope({
      name: newName.value.trim(),
      rollover: newRollover.value,
      category_ids: newCategoryIds.value,
      target_amount: newTargetAmount.value != null ? Math.round(newTargetAmount.value * 100) : null,
    })
    newName.value = ''
    newRollover.value = false
    newCategoryIds.value = []
    newTargetAmount.value = null
    addingEnvelope.value = false
    await load()
  } catch {
    error.value = 'Failed to create envelope.'
  } finally {
    saving.value = false
  }
}

function toggleId(ids: number[], id: number): void {
  const idx = ids.indexOf(id)
  if (idx >= 0) ids.splice(idx, 1)
  else ids.push(id)
}
</script>

<template>
  <div class="flex flex-col gap-2">
    <div v-if="envelopes.length === 0 && !addingEnvelope" class="text-base-content/50 text-sm">
      No envelopes yet.
    </div>

    <!-- Envelope rows -->
    <div
      v-for="env in envelopes"
      :key="env.id"
      class="border border-base-300 rounded-lg overflow-hidden"
    >
      <!-- Collapsed row -->
      <template v-if="editingId !== env.id">
        <div class="flex items-center gap-2 px-3 py-2 flex-wrap">
          <span class="font-medium">{{ env.name }}</span>
          <span v-if="env.rollover" class="badge badge-xs badge-info" title="Rollover: balance carries forward">↻</span>
          <span v-if="env.target_amount" class="badge badge-xs badge-accent" title="Target amount">🎯 {{ env.target_amount / 100 }} €</span>
          <span
            v-for="cat in env.categories"
            :key="cat.id"
            class="badge badge-xs badge-ghost"
          >{{ cat.name }}</span>
          <div class="ml-auto flex gap-1">
            <button class="btn btn-ghost btn-xs" @click="startEdit(env)">Edit</button>
            <button class="btn btn-ghost btn-xs text-error" @click="remove(env.id)">Delete</button>
          </div>
        </div>
      </template>

      <!-- Expanded editor -->
      <template v-else>
        <div class="p-3 bg-base-200/50 flex flex-col gap-3">
          <!-- Name + rollover -->
          <div class="flex gap-2 items-center flex-wrap">
            <input
              v-model="editName"
              type="text"
              class="input input-bordered input-sm flex-1 min-w-[160px]"
              placeholder="Envelope name"
            />
            <label class="flex items-center gap-1.5 text-sm cursor-pointer select-none">
              <input v-model="editRollover" type="checkbox" class="checkbox checkbox-xs" />
              Rollover (carry unspent balance)
            </label>
          </div>

          <!-- Target amount (goal) -->
          <div class="flex gap-2 items-center">
            <input
              v-model.number="editTargetAmount"
              type="number"
              min="0"
              step="1"
              class="input input-bordered input-sm w-32"
              placeholder="Goal (€)"
            />
            <span class="text-xs text-base-content/50">Target amount (€) — leave empty for no goal</span>
          </div>

          <!-- Category assignment -->
          <div v-if="groups.length > 0">
            <div class="text-xs text-base-content/50 uppercase tracking-wide mb-1">Assign categories</div>
            <div class="flex flex-wrap gap-x-6 gap-y-1 text-sm">
              <div v-for="group in groups" :key="group.id">
                <div class="text-base-content/40 text-xs mb-0.5">{{ group.name }}</div>
                <label
                  v-for="cat in group.categories"
                  :key="cat.id"
                  class="flex items-center gap-1 cursor-pointer"
                >
                  <input
                    type="checkbox"
                    class="checkbox checkbox-xs"
                    :checked="editCategoryIds.includes(cat.id)"
                    @change="toggleId(editCategoryIds, cat.id)"
                  />
                  {{ cat.name }}
                </label>
              </div>
            </div>
          </div>

          <div class="flex gap-2">
            <button class="btn btn-primary btn-xs" :disabled="saving" @click="saveEdit">
              <span v-if="saving" class="loading loading-spinner loading-xs"></span>
              Save
            </button>
            <button class="btn btn-ghost btn-xs" @click="cancelEdit">Cancel</button>
          </div>
        </div>
      </template>
    </div>

    <!-- Add envelope inline form -->
    <div
      v-if="addingEnvelope"
      class="border border-primary/30 border-dashed rounded-lg p-3 flex flex-col gap-3 bg-base-200/30"
    >
      <div class="flex gap-2 items-center flex-wrap">
        <input
          v-model="newName"
          type="text"
          class="input input-bordered input-sm flex-1 min-w-[160px]"
          placeholder="Envelope name"
          autofocus
          @keyup.enter="submitNew"
          @keyup.escape="addingEnvelope = false"
        />
        <label class="flex items-center gap-1.5 text-sm cursor-pointer select-none">
          <input v-model="newRollover" type="checkbox" class="checkbox checkbox-xs" />
          Rollover
        </label>
      </div>

      <!-- Target amount (goal) -->
      <div class="flex gap-2 items-center">
        <input
          v-model.number="newTargetAmount"
          type="number"
          min="0"
          step="1"
          class="input input-bordered input-sm w-32"
          placeholder="Goal (€)"
        />
        <span class="text-xs text-base-content/50">Target amount (€)</span>
      </div>

      <div v-if="groups.length > 0">
        <div class="text-xs text-base-content/50 uppercase tracking-wide mb-1">Assign categories (optional)</div>
        <div class="flex flex-wrap gap-x-6 gap-y-1 text-sm">
          <div v-for="group in groups" :key="group.id">
            <div class="text-base-content/40 text-xs mb-0.5">{{ group.name }}</div>
            <label
              v-for="cat in group.categories"
              :key="cat.id"
              class="flex items-center gap-1 cursor-pointer"
            >
              <input
                type="checkbox"
                class="checkbox checkbox-xs"
                :checked="newCategoryIds.includes(cat.id)"
                @change="toggleId(newCategoryIds, cat.id)"
              />
              {{ cat.name }}
            </label>
          </div>
        </div>
      </div>

      <div class="flex gap-2">
        <button
          class="btn btn-primary btn-xs"
          :disabled="saving || !newName.trim()"
          @click="submitNew"
        >
          <span v-if="saving" class="loading loading-spinner loading-xs"></span>
          Create
        </button>
        <button class="btn btn-ghost btn-xs" @click="addingEnvelope = false">Cancel</button>
      </div>
    </div>

    <div v-if="!addingEnvelope" class="mt-1">
      <button class="btn btn-ghost btn-sm text-primary" @click="addingEnvelope = true">
        + Add envelope
      </button>
    </div>

    <div v-if="error" class="alert alert-error text-sm py-1 mt-1">{{ error }}</div>
  </div>
</template>
