<script setup lang="ts">
/**
 * RecurringLineMenu — status and every correction of one service line.
 *
 * A status badge, the line's alerts, the usual corrections as visible
 * buttons (confirm, not a subscription, cancelled or undo, rename, accept a
 * new price, propose again) and the rest in a "⋯" menu (category, linked
 * labels, ignore, remove the classification). The editors that need a value
 * (name, date, category) open under the line.
 */

import { computed, nextTick, onBeforeUnmount, onMounted, ref } from 'vue'
import type { CategoryGroupWithCategories, RecurringLine } from '@/api/types'
import { attentionLines, formatDay, parseFrenchDate } from '@/api/recurring'
import type { LineAction } from '@/api/recurring'
import RecurringLabels from '@/components/RecurringLabels.vue'

const props = defineProps<{
  line: RecurringLine
  groups: CategoryGroupWithCategories[]
  /** Fallback date for a cancellation when the line has no debit (YYYY-MM-DD). */
  today: string
  busy: boolean
}>()

const emit = defineEmits<{
  action: [action: LineAction]
}>()

type Editor = 'rename' | 'cancel' | 'category' | 'labels' | null
const editor = ref<Editor>(null)
const nameValue = ref('')
const dateValue = ref('')
const dateError = ref(false)
const menu = ref<HTMLDetailsElement | null>(null)
const nameInput = ref<HTMLInputElement | null>(null)
const dateInput = ref<HTMLInputElement | null>(null)

const payment = computed(() => props.line.payment)

const status = computed(() => {
  const p = payment.value
  if (p?.kind === 'dismissed') return 'ignoré'
  if (p?.kind === 'other') return 'pas un abonnement'
  if (p?.kind === 'subscription') {
    return p.cancelled_at ? `résilié le ${formatDay(p.cancelled_at)}` : 'abonnement'
  }
  if (props.line.likely_other) return 'pas un abonnement ?'
  return props.line.running ? 'à confirmer' : 'détecté'
})

const statusClass = computed(() => {
  const p = payment.value
  if (p?.kind === 'subscription') return p.cancelled_at ? 'badge-ghost' : 'badge-primary'
  if (!p && props.line.running && !props.line.likely_other) return 'badge-outline'
  return 'badge-ghost'
})

const primaryItems = computed(() => items.value.filter((i) => i.primary))
const menuItems = computed(() => items.value.filter((i) => !i.primary))

const alerts = computed(() =>
  payment.value?.kind === 'subscription' ? attentionLines(payment.value) : [],
)

interface Item {
  label: string
  run: () => void
  /** Shown as a button on the line; otherwise in the "⋯" menu. */
  primary?: boolean
}

const items = computed<Item[]>(() => {
  const p = payment.value
  const result: Item[] = []
  const act = (action: LineAction) => () => send(action)
  if (p?.kind === 'dismissed') {
    return [{ label: 'Reproposer', run: act({ type: 'forget' }), primary: true }]
  }
  if (p?.kind === 'subscription' && p.price_changed && p.status !== 'cancelled') {
    result.push({
      label: 'Accepter le nouveau prix',
      run: act({ type: 'acceptPrice' }),
      primary: true,
    })
  }
  if (p?.kind !== 'subscription') {
    result.push({
      label: '✓ Abonnement',
      run: act({ type: 'kind', kind: 'subscription' }),
      primary: true,
    })
  }
  if (p?.kind !== 'other') {
    result.push({
      label: 'Pas un abonnement',
      run: act({ type: 'kind', kind: 'other' }),
      primary: true,
    })
  }
  if (p?.kind !== 'other') {
    if (p?.cancelled_at) {
      result.push({
        label: 'Annuler la résiliation',
        run: act({ type: 'cancel', date: null }),
        primary: true,
      })
    } else {
      result.push({ label: 'Résilié…', run: () => open('cancel'), primary: true })
    }
  }
  result.push({ label: 'Renommer…', run: () => open('rename'), primary: true })
  if (p) {
    result.push({ label: 'Catégorie…', run: () => open('category') })
    if (p.aliases.length > 0) {
      result.push({ label: 'Libellés reliés…', run: () => open('labels') })
    }
    result.push({ label: 'Retirer le classement', run: act({ type: 'forget' }) })
  } else {
    result.push({ label: 'Ignorer', run: act({ type: 'kind', kind: 'dismissed' }) })
  }
  return result
})

function closeMenu(): void {
  if (menu.value) menu.value.open = false
}

function send(action: LineAction): void {
  closeMenu()
  editor.value = null
  emit('action', action)
}

async function open(which: Exclude<Editor, null>): Promise<void> {
  closeMenu()
  editor.value = which
  if (which === 'rename') nameValue.value = props.line.name
  // The useful date is the last debit, not today; typed and shown the French way
  if (which === 'cancel') {
    dateValue.value = formatDay(props.line.last_date ?? props.today)
    dateError.value = false
  }
  await nextTick()
  if (which === 'rename') nameInput.value?.focus()
  if (which === 'cancel') dateInput.value?.focus()
}

function cancelRename(): void {
  editor.value = null
}

// The menu closes on a click elsewhere and on Escape, like any menu
function onPointerDown(event: Event): void {
  if (menu.value?.open && !menu.value.contains(event.target as Node)) closeMenu()
}

function onKeyDown(event: KeyboardEvent): void {
  if (event.key === 'Escape') closeMenu()
}

onMounted(() => {
  document.addEventListener('pointerdown', onPointerDown)
  document.addEventListener('keydown', onKeyDown)
})

onBeforeUnmount(() => {
  document.removeEventListener('pointerdown', onPointerDown)
  document.removeEventListener('keydown', onKeyDown)
})

function saveName(): void {
  // Enter then blur both call this: only the first one saves
  if (editor.value !== 'rename') return
  const name = nameValue.value.trim()
  editor.value = null
  if (name && name !== props.line.name) emit('action', { type: 'rename', name })
}

function saveCancel(): void {
  const date = parseFrenchDate(dateValue.value)
  if (!date) {
    dateError.value = true
    return
  }
  editor.value = null
  emit('action', { type: 'cancel', date })
}

function onCategory(event: Event): void {
  const value = (event.target as HTMLSelectElement).value
  editor.value = null
  emit('action', { type: 'category', categoryId: value ? Number(value) : null })
}
</script>

<template>
  <div class="flex flex-col gap-1 min-w-0">
    <div class="flex flex-wrap items-center gap-1">
      <span class="badge badge-sm" :class="statusClass" data-test="line-status">{{ status }}</span>
      <button
        v-for="item in primaryItems"
        :key="item.label"
        class="btn btn-xs"
        :class="item.label === '✓ Abonnement' ? 'btn-primary' : 'btn-ghost border-base-300'"
        :disabled="busy"
        data-test="menu-item"
        @click="item.run"
      >{{ item.label }}</button>
      <details v-if="menuItems.length > 0" ref="menu" class="dropdown dropdown-end">
        <summary
          class="btn btn-ghost btn-xs px-1.5"
          :class="{ 'btn-disabled': busy }"
          aria-label="Actions sur la ligne"
          title="Actions"
        >⋯</summary>
        <ul class="dropdown-content menu menu-sm bg-base-100 border border-base-300 rounded-box z-20 w-56 p-1 shadow">
          <li v-for="item in menuItems" :key="item.label">
            <button data-test="menu-item" :disabled="busy" @click="item.run">{{ item.label }}</button>
          </li>
        </ul>
      </details>
    </div>

    <p v-for="a in alerts" :key="a" class="text-xs text-warning">{{ a }}</p>

    <div v-if="editor === 'rename'" class="flex items-center gap-1">
      <input
        ref="nameInput"
        v-model="nameValue"
        class="input input-xs input-bordered flex-1 min-w-0"
        maxlength="200"
        aria-label="Nouveau nom"
        data-test="rename-input"
        @keydown.enter="saveName"
        @keydown.esc.prevent="cancelRename"
        @blur="saveName"
      />
      <button class="btn btn-xs btn-ghost" @pointerdown.prevent @click="cancelRename">Annuler</button>
    </div>

    <div v-if="editor === 'cancel'" class="flex flex-wrap items-center gap-1">
      <span class="text-xs">Résilié le</span>
      <!-- Text, not type="date": a native date field follows the browser's
           language (mm/dd/yyyy in an English browser), not the page's -->
      <input
        ref="dateInput"
        v-model="dateValue"
        type="text"
        inputmode="numeric"
        placeholder="jj/mm/aaaa"
        maxlength="10"
        class="input input-xs input-bordered w-28"
        :class="{ 'input-error': dateError }"
        aria-label="Date de résiliation (jj/mm/aaaa)"
        data-test="cancel-date"
        @input="dateError = false"
        @keydown.enter="saveCancel"
      />
      <button class="btn btn-xs btn-primary" :disabled="busy" data-test="cancel-confirm" @click="saveCancel">
        Confirmer
      </button>
      <button class="btn btn-xs btn-ghost" @click="editor = null">Annuler</button>
      <span v-if="dateError" class="text-xs text-error w-full" data-test="cancel-error">
        Date invalide : saisis-la au format jj/mm/aaaa.
      </span>
    </div>

    <div v-if="editor === 'category' && payment" class="flex items-center gap-1">
      <select
        class="select select-xs select-bordered max-w-48"
        :value="payment.category_id ?? ''"
        :disabled="busy"
        @change="onCategory"
      >
        <option value="">Sans catégorie</option>
        <optgroup v-for="g in groups" :key="g.id" :label="g.name">
          <option v-for="c in g.categories" :key="c.id" :value="c.id">{{ c.name }}</option>
        </optgroup>
      </select>
      <button class="btn btn-xs btn-ghost" @click="editor = null">Fermer</button>
    </div>

    <div v-if="editor === 'labels' && payment" class="flex items-center gap-1">
      <RecurringLabels
        :payment="payment"
        :busy="busy"
        @detach="(id) => send({ type: 'detach', aliasId: id })"
      />
      <button class="btn btn-xs btn-ghost" @click="editor = null">Fermer</button>
    </div>
  </div>
</template>
