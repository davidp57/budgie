<script setup lang="ts">
/**
 * BudgetView — Manage budget envelopes with DrawerCard tiles.
 *
 * Mobile-first, same visual as HomeView but with inline editing:
 * - DrawerCard tiles (same appearance as Tiroirs view)
 * - Tap emoji → cycle through presets
 * - Tap name → inline edit
 * - Tap amount → inline edit budgeted amount
 * - "⋯" button → full edit dialog
 * - Swipe left → delete
 * - FAB "+" → create new envelope
 * - Cumulative envelopes: "+€" → numpad to add budget
 */

import { computed, nextTick, onMounted, ref } from 'vue'
import { useBudgetStore } from '@/stores/budget'
import { listGroupsWithCategories } from '@/api/categories'
import { createEnvelope, deleteEnvelope, listEnvelopes, updateEnvelope } from '@/api/envelopes'
import { setMonthBudget } from '@/api/budget'
import DrawerCard from '@/components/DrawerCard.vue'
import type {
  CategoryGroupWithCategories,
  Envelope,
  EnvelopeLine,
  EnvelopePeriod,
  EnvelopeType,
} from '@/api/types'
import { formatAmount } from '@/api/types'

const budgetStore = useBudgetStore()

// ── Supplementary data ───────────────────────────────────────────
const groups = ref<CategoryGroupWithCategories[]>([])
const fullEnvelopes = ref<Envelope[]>([])

// ── Month navigation ─────────────────────────────────────────────
const monthLabel = computed(() => {
  const [y, m] = budgetStore.month.split('-')
  const months = [
    'Janvier', 'Février', 'Mars', 'Avril', 'Mai', 'Juin',
    'Juillet', 'Août', 'Septembre', 'Octobre', 'Novembre', 'Décembre',
  ]
  return `${months[parseInt(m, 10) - 1]} ${y}`
})

const totalAvailable = computed(() =>
  budgetStore.envelopeLines.reduce((sum, l) => sum + l.available, 0),
)

function prevMonth(): void {
  const [y, m] = budgetStore.month.split('-').map(Number)
  const prev = m === 1 ? `${y - 1}-12` : `${y}-${String(m - 1).padStart(2, '0')}`
  budgetStore.loadMonth(prev)
}

function nextMonth(): void {
  const [y, m] = budgetStore.month.split('-').map(Number)
  const next = m === 12 ? `${y + 1}-01` : `${y}-${String(m + 1).padStart(2, '0')}`
  budgetStore.loadMonth(next)
}

// ── Emoji presets ────────────────────────────────────────────────
const EMOJI_PRESETS = [
  '🛒', '🏠', '🚗', '💡', '🎮', '🍽️', '👕', '🏥',
  '📱', '✈️', '🎓', '💰', '🐱', '🎁', '📦', '🔧',
]

// ── Helpers ──────────────────────────────────────────────────────
const COLOR_PALETTE_LENGTH = 8

function toggleCategory(ids: number[], id: number): void {
  const idx = ids.indexOf(id)
  if (idx >= 0) ids.splice(idx, 1)
  else ids.push(id)
}

function displayEuros(centimes: number): string {
  return (centimes / 100).toFixed(2).replace('.', ',')
}

// ── Color cycling on tile tap ───────────────────────────────────────
const colorOverrides = ref<Record<number, number>>({})

function getColorIndex(line: EnvelopeLine): number {
  return colorOverrides.value[line.envelope_id] ?? (line.envelope_id - 1)
}

function cycleColor(line: EnvelopeLine): void {
  const current = getColorIndex(line)
  colorOverrides.value[line.envelope_id] = (current + 1) % COLOR_PALETTE_LENGTH
}

// ── Swipe to delete ──────────────────────────────────────────────
const swipedId = ref<number | null>(null)
const touchStartX = ref(0)
const touchDeltaX = ref(0)

function onTouchStart(e: TouchEvent, envelopeId: number): void {
  if (swipedId.value && swipedId.value !== envelopeId) swipedId.value = null
  touchStartX.value = e.touches[0].clientX
  touchDeltaX.value = 0
}

function onTouchMove(e: TouchEvent): void {
  touchDeltaX.value = e.touches[0].clientX - touchStartX.value
}

function onTouchEnd(envelopeId: number): void {
  if (touchDeltaX.value < -60) {
    swipedId.value = envelopeId
  } else if (swipedId.value === envelopeId) {
    swipedId.value = null
  }
  touchDeltaX.value = 0
}

// ── Inline editing ───────────────────────────────────────────────
const inlineEdit = ref<{ id: number; field: 'name' | 'amount' } | null>(null)
const inlineValue = ref('')

async function cycleEmoji(line: EnvelopeLine): Promise<void> {
  const current = line.emoji || '📦'
  const idx = EMOJI_PRESETS.indexOf(current)
  const next = EMOJI_PRESETS[(idx + 1) % EMOJI_PRESETS.length]
  await updateEnvelope(line.envelope_id, { emoji: next })
  await reloadAll()
}

function focusInlineInput(): void {
  nextTick(() => {
    const el = document.querySelector<HTMLInputElement>('.inline-edit-input')
    el?.focus()
    el?.select()
  })
}

function startEditName(line: EnvelopeLine): void {
  inlineEdit.value = { id: line.envelope_id, field: 'name' }
  inlineValue.value = line.envelope_name
  focusInlineInput()
}

function startEditAmount(line: EnvelopeLine): void {
  inlineEdit.value = { id: line.envelope_id, field: 'amount' }
  inlineValue.value = displayEuros(line.budgeted)
  focusInlineInput()
}

async function saveInlineName(line: EnvelopeLine): Promise<void> {
  if (!inlineEdit.value || inlineEdit.value.id !== line.envelope_id) return
  const name = inlineValue.value.trim()
  inlineEdit.value = null
  if (!name || name === line.envelope_name) return
  await updateEnvelope(line.envelope_id, { name })
  await reloadAll()
}

async function saveInlineAmount(line: EnvelopeLine): Promise<void> {
  if (!inlineEdit.value || inlineEdit.value.id !== line.envelope_id) return
  const euros = parseFloat(inlineValue.value.replace(',', '.')) || 0
  const centimes = Math.round(euros * 100)
  inlineEdit.value = null
  if (centimes === line.budgeted) return
  await setMonthBudget(budgetStore.month, [
    { envelope_id: line.envelope_id, budgeted: centimes },
  ])
  await budgetStore.loadMonth()
}

async function swipeDelete(envelopeId: number): Promise<void> {
  await deleteEnvelope(envelopeId)
  swipedId.value = null
  await reloadAll()
}

// ── Edit dialog ──────────────────────────────────────────────────
const editDialogRef = ref<HTMLDialogElement | null>(null)
const editingLine = ref<EnvelopeLine | null>(null)
const editForm = ref({
  name: '',
  emoji: '📦',
  envelope_type: 'regular' as EnvelopeType,
  period: 'monthly' as EnvelopePeriod,
  rollover: false,
  category_ids: [] as number[],
  budgetedEuros: '',
})
const editError = ref('')
const editSaving = ref(false)

function openEdit(line: EnvelopeLine): void {
  editingLine.value = line
  const full = fullEnvelopes.value.find((e) => e.id === line.envelope_id)
  editForm.value = {
    name: line.envelope_name,
    emoji: line.emoji || '📦',
    envelope_type: line.envelope_type,
    period: full?.period ?? 'monthly',
    rollover: line.rollover,
    category_ids: line.categories.map((c) => c.id),
    budgetedEuros: displayEuros(line.budgeted),
  }
  editError.value = ''
  editDialogRef.value?.showModal()
}

function closeEdit(): void {
  editDialogRef.value?.close()
  editingLine.value = null
}

async function saveEdit(): Promise<void> {
  if (!editingLine.value) return
  editSaving.value = true
  editError.value = ''
  try {
    await updateEnvelope(editingLine.value.envelope_id, {
      name: editForm.value.name.trim(),
      emoji: editForm.value.emoji,
      envelope_type: editForm.value.envelope_type,
      period: editForm.value.period,
      rollover: editForm.value.rollover,
      category_ids: editForm.value.category_ids,
    })
    const euros = parseFloat(editForm.value.budgetedEuros.replace(',', '.')) || 0
    const centimes = Math.round(euros * 100)
    await setMonthBudget(budgetStore.month, [
      { envelope_id: editingLine.value.envelope_id, budgeted: centimes },
    ])
    closeEdit()
    await reloadAll()
  } catch {
    editError.value = 'Échec de la sauvegarde.'
  } finally {
    editSaving.value = false
  }
}

async function confirmDelete(): Promise<void> {
  if (!editingLine.value) return
  editSaving.value = true
  editError.value = ''
  try {
    await deleteEnvelope(editingLine.value.envelope_id)
    closeEdit()
    await reloadAll()
  } catch {
    editError.value = 'Échec de la suppression.'
  } finally {
    editSaving.value = false
  }
}

// ── Create dialog ────────────────────────────────────────────────
const createDialogRef = ref<HTMLDialogElement | null>(null)
const createForm = ref({
  name: '',
  emoji: '📦',
  envelope_type: 'regular' as EnvelopeType,
  period: 'monthly' as EnvelopePeriod,
  rollover: false,
  category_ids: [] as number[],
  budgetedEuros: '',
})
const createError = ref('')
const createSaving = ref(false)

function openCreate(): void {
  createForm.value = {
    name: '',
    emoji: '📦',
    envelope_type: 'regular',
    period: 'monthly',
    rollover: false,
    category_ids: [],
    budgetedEuros: '',
  }
  createError.value = ''
  createDialogRef.value?.showModal()
}

function closeCreate(): void {
  createDialogRef.value?.close()
}

async function saveCreate(): Promise<void> {
  if (!createForm.value.name.trim()) return
  createSaving.value = true
  createError.value = ''
  try {
    const envelope = await createEnvelope({
      name: createForm.value.name.trim(),
      emoji: createForm.value.emoji,
      envelope_type: createForm.value.envelope_type,
      period: createForm.value.period,
      rollover: createForm.value.rollover,
      category_ids: createForm.value.category_ids,
    })
    const euros = parseFloat(createForm.value.budgetedEuros.replace(',', '.')) || 0
    if (euros > 0) {
      await setMonthBudget(budgetStore.month, [
        { envelope_id: envelope.id, budgeted: Math.round(euros * 100) },
      ])
    }
    closeCreate()
    await reloadAll()
  } catch {
    createError.value = 'Échec de la création.'
  } finally {
    createSaving.value = false
  }
}

// ── Quick add budget (cumulative) ────────────────────────────────
const addBudgetDialogRef = ref<HTMLDialogElement | null>(null)
const addBudgetLine = ref<EnvelopeLine | null>(null)
const addBudgetAmount = ref('')
const addBudgetSaving = ref(false)
const addBudgetError = ref('')

function openAddBudget(line: EnvelopeLine, event: Event): void {
  event.stopPropagation()
  addBudgetLine.value = line
  addBudgetAmount.value = ''
  addBudgetError.value = ''
  addBudgetDialogRef.value?.showModal()
}

function closeAddBudget(): void {
  addBudgetDialogRef.value?.close()
  addBudgetLine.value = null
}

function addBudgetKey(key: string): void {
  if (key === '⌫') {
    addBudgetAmount.value = addBudgetAmount.value.slice(0, -1)
  } else if (key === ',' && !addBudgetAmount.value.includes(',')) {
    addBudgetAmount.value += ','
  } else if (key !== ',') {
    const parts = addBudgetAmount.value.split(',')
    if (parts.length === 2 && parts[1].length >= 2) return
    addBudgetAmount.value += key
  }
}

const addBudgetCentimes = computed(() => {
  const euros = parseFloat(addBudgetAmount.value.replace(',', '.')) || 0
  return Math.round(euros * 100)
})

async function confirmAddBudget(): Promise<void> {
  if (!addBudgetLine.value || addBudgetCentimes.value <= 0) return
  addBudgetSaving.value = true
  addBudgetError.value = ''
  try {
    const newBudgeted = addBudgetLine.value.budgeted + addBudgetCentimes.value
    await setMonthBudget(budgetStore.month, [
      { envelope_id: addBudgetLine.value.envelope_id, budgeted: newBudgeted },
    ])
    closeAddBudget()
    await budgetStore.loadMonth()
  } catch {
    addBudgetError.value = 'Échec.'
  } finally {
    addBudgetSaving.value = false
  }
}

// ── Reload helper ────────────────────────────────────────────────
async function reloadAll(): Promise<void> {
  await Promise.all([
    budgetStore.loadMonth(),
    listEnvelopes().then((e) => (fullEnvelopes.value = e)),
  ])
}

// ── Init ─────────────────────────────────────────────────────────
onMounted(async () => {
  await Promise.all([
    budgetStore.loadMonth(),
    listGroupsWithCategories().then((g) => (groups.value = g)),
    listEnvelopes().then((e) => (fullEnvelopes.value = e)),
  ])
})
</script>

<template>
  <div class="px-4 py-5 pb-24">
    <!-- Header -->
    <div class="flex items-center justify-between mb-2">
      <div class="flex items-center gap-2">
        <span class="text-2xl">🗂️</span>
        <h1 class="text-xl font-bold">Tiroirs</h1>
      </div>
      <div class="flex items-center gap-1">
        <button class="btn btn-ghost btn-xs btn-circle" @click="prevMonth">‹</button>
        <span class="text-sm font-semibold min-w-[100px] text-center">{{ monthLabel }}</span>
        <button class="btn btn-ghost btn-xs btn-circle" @click="nextMonth">›</button>
      </div>
    </div>

    <p class="text-sm text-base-content/50 mb-5">
      {{ budgetStore.envelopeLines.length }} tiroir{{
        budgetStore.envelopeLines.length > 1 ? 's' : ''
      }}
      · disponible {{ formatAmount(totalAvailable) }}
    </p>

    <!-- Loading skeleton -->
    <div v-if="budgetStore.loading" class="flex flex-col gap-4">
      <div v-for="i in 4" :key="i" class="skeleton h-36 rounded-2xl" />
    </div>

    <!-- Empty state -->
    <div
      v-else-if="budgetStore.envelopeLines.length === 0"
      class="text-center py-10 text-base-content/50"
    >
      <p class="text-5xl mb-4">📭</p>
      <p class="font-medium">Aucun tiroir</p>
    </div>

    <!-- Drawer cards with swipe-to-delete -->
    <div v-else class="flex flex-col gap-4">
      <div
        v-for="line in budgetStore.envelopeLines"
        :key="line.envelope_id"
        class="relative overflow-hidden rounded-2xl"
      >
        <!-- Delete zone (revealed by swipe) -->
        <div
          class="absolute inset-y-0 right-0 w-24 bg-error flex items-center justify-center rounded-r-2xl"
        >
          <button
            class="btn btn-ghost text-white text-2xl"
            @click.stop="swipeDelete(line.envelope_id)"
          >
            🗑️
          </button>
        </div>

        <!-- Card wrapper with touch gestures -->
        <div
          class="relative transition-transform duration-200"
          :class="{ '-translate-x-24': swipedId === line.envelope_id }"
          @touchstart="onTouchStart($event, line.envelope_id)"
          @touchmove="onTouchMove"
          @touchend="onTouchEnd(line.envelope_id)"
        >
          <DrawerCard
            :line="line"
            :color-index="getColorIndex(line)"
            :show-money="false"
            :show-calendar="false"
            :show-subtitle="false"
            @tap="cycleColor(line)"
          >
            <!-- Emoji slot: click to cycle -->
            <template #emoji>
              <span
                class="text-3xl drop-shadow-md cursor-pointer active:scale-90 transition-transform"
                @click.stop="cycleEmoji(line)"
              >
                {{ line.emoji || '📦' }}
              </span>
            </template>

            <!-- Name slot: inline edit -->
            <template #name>
              <input
                v-if="inlineEdit?.id === line.envelope_id && inlineEdit?.field === 'name'"
                v-model="inlineValue"
                type="text"
                class="inline-edit-input bg-white/30 rounded px-1.5 py-0.5
                       font-bold text-base text-white tracking-wide
                       outline-none border border-white/50 focus:border-white
                       drop-shadow-sm"
                @click.stop
                @blur="saveInlineName(line)"
                @keyup.enter="($event.target as HTMLInputElement).blur()"
              />
              <span
                v-else
                class="font-bold text-base tracking-wide drop-shadow-sm cursor-pointer"
                @click.stop="startEditName(line)"
              >
                {{ line.envelope_name }}
              </span>
            </template>

            <!-- Amount slot: inline edit budgeted -->
            <template #amount>
              <input
                v-if="inlineEdit?.id === line.envelope_id && inlineEdit?.field === 'amount'"
                v-model="inlineValue"
                type="text"
                inputmode="decimal"
                class="inline-edit-input bg-white/30 rounded px-2 py-1
                       text-[42px] leading-none font-extrabold tabular-nums tracking-tight
                       text-white outline-none border border-white/50 focus:border-white
                       drop-shadow-lg w-48"
                @click.stop
                @blur="saveInlineAmount(line)"
                @keyup.enter="($event.target as HTMLInputElement).blur()"
              />
              <span
                v-else
                class="text-[42px] leading-none font-extrabold tabular-nums tracking-tight drop-shadow-lg cursor-pointer"
                @click.stop="startEditAmount(line)"
              >
                {{ formatAmount(line.available) }}
              </span>
            </template>

            <!-- Actions slot: +€ and ⋯ buttons -->
            <template #actions>
              <button
                v-if="line.envelope_type === 'cumulative'"
                class="w-8 h-8 rounded-full bg-white/20 backdrop-blur-sm
                       flex items-center justify-center
                       text-xs font-bold text-white/80 hover:text-white hover:bg-white/30
                       active:scale-90 transition-all shrink-0"
                @click.stop="openAddBudget(line, $event)"
              >
                +€
              </button>
              <button
                class="w-8 h-8 rounded-full bg-white/20 backdrop-blur-sm
                       flex items-center justify-center
                       text-sm font-bold text-white/80 hover:text-white hover:bg-white/30
                       active:scale-90 transition-all shrink-0"
                :class="{ 'ml-auto': line.envelope_type !== 'cumulative' && line.envelope_type !== 'reserve' }"
                @click.stop="openEdit(line)"
              >
                ⋯
              </button>
            </template>
          </DrawerCard>
        </div>
      </div>
    </div>

    <!-- Blueprint "add" tile at the bottom -->
    <button
      v-if="!budgetStore.loading"
      class="blueprint-tile w-full rounded-2xl mt-4 min-h-[150px]
             flex flex-col items-center justify-center gap-2
             active:scale-[0.97] transition-transform"
      @click="openCreate"
    >
      <span class="text-5xl leading-none opacity-80">+</span>
      <span class="text-sm font-medium tracking-wide opacity-70">Nouveau tiroir</span>
    </button>

    <!-- ═══════════════════════════════════════════════════════════ -->
    <!-- Edit Envelope Dialog                                      -->
    <!-- ═══════════════════════════════════════════════════════════ -->
    <dialog ref="editDialogRef" class="modal modal-bottom sm:modal-middle">
      <div class="modal-box max-h-[85vh] overflow-y-auto">
        <h3 class="text-lg font-bold mb-4">Modifier le tiroir</h3>

        <!-- Emoji picker -->
        <div class="mb-4">
          <label class="text-sm text-base-content/60 mb-1 block">Icône</label>
          <div class="flex flex-wrap gap-2">
            <button
              v-for="e in EMOJI_PRESETS"
              :key="e"
              class="w-10 h-10 text-xl rounded-lg flex items-center justify-center transition-all"
              :class="
                editForm.emoji === e
                  ? 'bg-primary/20 ring-2 ring-primary scale-110'
                  : 'bg-base-200 hover:bg-base-300'
              "
              @click="editForm.emoji = e"
            >
              {{ e }}
            </button>
          </div>
        </div>

        <!-- Name -->
        <div class="form-control mb-3">
          <label class="label"><span class="label-text">Nom</span></label>
          <input
            v-model="editForm.name"
            type="text"
            class="input input-bordered"
            placeholder="Courses, Loyer..."
          />
        </div>

        <!-- Type + Period -->
        <div class="grid grid-cols-2 gap-3 mb-3">
          <div class="form-control">
            <label class="label"><span class="label-text">Type</span></label>
            <select v-model="editForm.envelope_type" class="select select-bordered select-sm">
              <option value="regular">Régulier</option>
              <option value="cumulative">Cumulatif</option>
              <option value="reserve">Réserve</option>
            </select>
          </div>
          <div class="form-control">
            <label class="label"><span class="label-text">Période</span></label>
            <select v-model="editForm.period" class="select select-bordered select-sm">
              <option value="weekly">Hebdo</option>
              <option value="monthly">Mensuel</option>
              <option value="quarterly">Trimestriel</option>
              <option value="yearly">Annuel</option>
            </select>
          </div>
        </div>

        <!-- Budget this month -->
        <div class="form-control mb-3">
          <label class="label"><span class="label-text">Budget ce mois (€)</span></label>
          <input
            v-model="editForm.budgetedEuros"
            type="text"
            inputmode="decimal"
            class="input input-bordered"
            placeholder="0,00"
          />
        </div>

        <!-- Rollover -->
        <label class="flex items-center gap-2 mb-3 cursor-pointer">
          <input
            v-model="editForm.rollover"
            type="checkbox"
            class="toggle toggle-sm toggle-primary"
          />
          <span class="text-sm">Report du solde au mois suivant</span>
        </label>

        <!-- Categories -->
        <div v-if="groups.length > 0" class="mb-4">
          <label class="text-sm text-base-content/60 mb-2 block">Catégories associées</label>
          <div class="max-h-40 overflow-y-auto bg-base-200/50 rounded-lg p-2">
            <div v-for="group in groups" :key="group.id" class="mb-2">
              <div class="text-xs text-base-content/40 uppercase tracking-wide mb-1">
                {{ group.name }}
              </div>
              <label
                v-for="cat in group.categories"
                :key="cat.id"
                class="flex items-center gap-2 py-0.5 cursor-pointer"
              >
                <input
                  type="checkbox"
                  class="checkbox checkbox-xs checkbox-primary"
                  :checked="editForm.category_ids.includes(cat.id)"
                  @change="toggleCategory(editForm.category_ids, cat.id)"
                />
                <span class="text-sm">{{ cat.name }}</span>
              </label>
            </div>
          </div>
        </div>

        <div v-if="editError" class="alert alert-error text-sm py-2 mb-3">{{ editError }}</div>

        <div class="flex gap-2">
          <button
            class="btn btn-primary flex-1"
            :disabled="editSaving || !editForm.name.trim()"
            @click="saveEdit"
          >
            <span v-if="editSaving" class="loading loading-spinner loading-sm"></span>
            Enregistrer
          </button>
          <button class="btn btn-ghost" @click="closeEdit">Annuler</button>
        </div>

        <div class="divider text-xs text-base-content/30">zone danger</div>
        <button
          class="btn btn-error btn-outline btn-sm w-full"
          :disabled="editSaving"
          @click="confirmDelete"
        >
          Supprimer ce tiroir
        </button>
      </div>
      <form method="dialog" class="modal-backdrop"><button>close</button></form>
    </dialog>

    <!-- ═══════════════════════════════════════════════════════════ -->
    <!-- Create Envelope Dialog                                    -->
    <!-- ═══════════════════════════════════════════════════════════ -->
    <dialog ref="createDialogRef" class="modal modal-bottom sm:modal-middle">
      <div class="modal-box max-h-[85vh] overflow-y-auto">
        <h3 class="text-lg font-bold mb-4">Nouveau tiroir</h3>

        <!-- Emoji picker -->
        <div class="mb-4">
          <label class="text-sm text-base-content/60 mb-1 block">Icône</label>
          <div class="flex flex-wrap gap-2">
            <button
              v-for="e in EMOJI_PRESETS"
              :key="e"
              class="w-10 h-10 text-xl rounded-lg flex items-center justify-center transition-all"
              :class="
                createForm.emoji === e
                  ? 'bg-primary/20 ring-2 ring-primary scale-110'
                  : 'bg-base-200 hover:bg-base-300'
              "
              @click="createForm.emoji = e"
            >
              {{ e }}
            </button>
          </div>
        </div>

        <!-- Name -->
        <div class="form-control mb-3">
          <label class="label"><span class="label-text">Nom</span></label>
          <input
            v-model="createForm.name"
            type="text"
            class="input input-bordered"
            placeholder="Courses, Loyer..."
            autofocus
          />
        </div>

        <!-- Type + Period -->
        <div class="grid grid-cols-2 gap-3 mb-3">
          <div class="form-control">
            <label class="label"><span class="label-text">Type</span></label>
            <select v-model="createForm.envelope_type" class="select select-bordered select-sm">
              <option value="regular">Régulier</option>
              <option value="cumulative">Cumulatif</option>
              <option value="reserve">Réserve</option>
            </select>
          </div>
          <div class="form-control">
            <label class="label"><span class="label-text">Période</span></label>
            <select v-model="createForm.period" class="select select-bordered select-sm">
              <option value="weekly">Hebdo</option>
              <option value="monthly">Mensuel</option>
              <option value="quarterly">Trimestriel</option>
              <option value="yearly">Annuel</option>
            </select>
          </div>
        </div>

        <!-- Initial budget -->
        <div class="form-control mb-3">
          <label class="label"><span class="label-text">Budget initial (€)</span></label>
          <input
            v-model="createForm.budgetedEuros"
            type="text"
            inputmode="decimal"
            class="input input-bordered"
            placeholder="0,00"
          />
        </div>

        <!-- Rollover -->
        <label class="flex items-center gap-2 mb-3 cursor-pointer">
          <input
            v-model="createForm.rollover"
            type="checkbox"
            class="toggle toggle-sm toggle-primary"
          />
          <span class="text-sm">Report du solde au mois suivant</span>
        </label>

        <!-- Categories -->
        <div v-if="groups.length > 0" class="mb-4">
          <label class="text-sm text-base-content/60 mb-2 block">Catégories associées</label>
          <div class="max-h-40 overflow-y-auto bg-base-200/50 rounded-lg p-2">
            <div v-for="group in groups" :key="group.id" class="mb-2">
              <div class="text-xs text-base-content/40 uppercase tracking-wide mb-1">
                {{ group.name }}
              </div>
              <label
                v-for="cat in group.categories"
                :key="cat.id"
                class="flex items-center gap-2 py-0.5 cursor-pointer"
              >
                <input
                  type="checkbox"
                  class="checkbox checkbox-xs checkbox-primary"
                  :checked="createForm.category_ids.includes(cat.id)"
                  @change="toggleCategory(createForm.category_ids, cat.id)"
                />
                <span class="text-sm">{{ cat.name }}</span>
              </label>
            </div>
          </div>
        </div>

        <div v-if="createError" class="alert alert-error text-sm py-2 mb-3">{{ createError }}</div>

        <div class="flex gap-2">
          <button
            class="btn btn-primary flex-1"
            :disabled="createSaving || !createForm.name.trim()"
            @click="saveCreate"
          >
            <span v-if="createSaving" class="loading loading-spinner loading-sm"></span>
            Créer
          </button>
          <button class="btn btn-ghost" @click="closeCreate">Annuler</button>
        </div>
      </div>
      <form method="dialog" class="modal-backdrop"><button>close</button></form>
    </dialog>

    <!-- ═══════════════════════════════════════════════════════════ -->
    <!-- Quick Add Budget Dialog (cumulative envelopes)            -->
    <!-- ═══════════════════════════════════════════════════════════ -->
    <dialog ref="addBudgetDialogRef" class="modal modal-bottom sm:modal-middle">
      <div class="modal-box">
        <h3 class="text-lg font-bold mb-1">Ajouter du budget</h3>
        <p v-if="addBudgetLine" class="text-sm text-base-content/50 mb-4">
          {{ addBudgetLine.emoji }} {{ addBudgetLine.envelope_name }}
          · actuel : {{ formatAmount(addBudgetLine.budgeted) }}
        </p>

        <!-- Amount display -->
        <div class="text-center mb-4">
          <span class="text-4xl font-extrabold tabular-nums">
            {{ addBudgetAmount || '0' }}
          </span>
          <span class="text-2xl text-base-content/40 ml-1">€</span>
        </div>

        <!-- Quick presets -->
        <div class="flex gap-2 justify-center mb-4">
          <button
            v-for="p in [10, 20, 50, 100]"
            :key="p"
            class="btn btn-sm btn-outline"
            @click="addBudgetAmount = String(p)"
          >
            {{ p }}€
          </button>
        </div>

        <!-- Numpad -->
        <div class="grid grid-cols-3 gap-2 max-w-xs mx-auto mb-4">
          <button
            v-for="k in ['1', '2', '3', '4', '5', '6', '7', '8', '9', ',', '0', '⌫']"
            :key="k"
            class="btn btn-ghost btn-lg text-xl"
            @click="addBudgetKey(k)"
          >
            {{ k }}
          </button>
        </div>

        <div v-if="addBudgetError" class="alert alert-error text-sm py-2 mb-3">
          {{ addBudgetError }}
        </div>

        <div class="flex gap-2">
          <button
            class="btn btn-primary flex-1"
            :disabled="addBudgetSaving || addBudgetCentimes <= 0"
            @click="confirmAddBudget"
          >
            <span v-if="addBudgetSaving" class="loading loading-spinner loading-sm"></span>
            Ajouter {{ addBudgetCentimes > 0 ? formatAmount(addBudgetCentimes) : '' }}
          </button>
          <button class="btn btn-ghost" @click="closeAddBudget">Annuler</button>
        </div>
      </div>
      <form method="dialog" class="modal-backdrop"><button>close</button></form>
    </dialog>
  </div>
</template>

<style scoped>
.blueprint-tile {
  background:
    linear-gradient(rgba(255, 255, 255, 0.08) 1px, transparent 1px),
    linear-gradient(90deg, rgba(255, 255, 255, 0.08) 1px, transparent 1px),
    linear-gradient(135deg, #1e3a5f, #1a2f4a);
  background-size: 20px 20px, 20px 20px, 100% 100%;
  border: 2px dashed rgba(100, 160, 230, 0.5);
  color: rgba(140, 190, 255, 0.9);
  box-shadow: inset 0 0 30px rgba(0, 0, 0, 0.15);
}
</style>
