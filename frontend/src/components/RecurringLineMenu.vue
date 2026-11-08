<script setup lang="ts">
/**
 * RecurringLineMenu — status and every correction of one service line.
 *
 * One component for every place a line is shown, so that whatever can be
 * done on a line in one tab can be done in the other: a status badge, the
 * line's alerts, and a "⋯" menu (confirm, not a subscription, cancel or undo
 * the cancellation, rename, category, accept a new price, linked labels,
 * ignore, propose again, remove the classification). The editors that need
 * a value (name, date, category) open under the line.
 */

import { computed, nextTick, onBeforeUnmount, onMounted, ref } from 'vue'
import type { CategoryGroupWithCategories, RecurringLine } from '@/api/types'
import { attentionLines, formatDay } from '@/api/recurring'
import type { LineAction } from '@/api/recurring'
import RecurringLabels from '@/components/RecurringLabels.vue'

const props = defineProps<{
  line: RecurringLine
  groups: CategoryGroupWithCategories[]
  /** Default date for a cancellation (YYYY-MM-DD). */
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

const alerts = computed(() =>
  payment.value?.kind === 'subscription' ? attentionLines(payment.value) : [],
)

interface Item {
  label: string
  run: () => void
}

const items = computed<Item[]>(() => {
  const p = payment.value
  const result: Item[] = []
  const act = (action: LineAction) => () => send(action)
  if (p?.kind === 'dismissed') {
    return [{ label: 'Reproposer', run: act({ type: 'forget' }) }]
  }
  if (p?.kind === 'subscription' && p.price_changed && p.status !== 'cancelled') {
    result.push({ label: 'Accepter le nouveau prix', run: act({ type: 'acceptPrice' }) })
  }
  if (p?.kind !== 'subscription') {
    result.push({ label: '✓ Abonnement', run: act({ type: 'kind', kind: 'subscription' }) })
  }
  if (p?.kind !== 'other') {
    result.push({ label: 'Pas un abonnement', run: act({ type: 'kind', kind: 'other' }) })
  }
  if (p?.kind !== 'other') {
    if (p?.cancelled_at) {
      result.push({ label: 'Annuler la résiliation', run: act({ type: 'cancel', date: null }) })
    } else {
      result.push({ label: 'Résilié…', run: () => open('cancel') })
    }
  }
  // A detected line that stopped is renamed once classified (confirm first)
  if (p || props.line.running) {
    result.push({ label: 'Renommer…', run: () => open('rename') })
  }
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
  if (which === 'cancel') dateValue.value = props.today
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
  const date = dateValue.value
  editor.value = null
  if (date) emit('action', { type: 'cancel', date })
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
      <!-- Opens to the right: the line's name sits at the left edge of the page -->
      <details ref="menu" class="dropdown">
        <summary
          class="btn btn-ghost btn-xs px-1.5"
          :class="{ 'btn-disabled': busy }"
          aria-label="Actions sur la ligne"
          title="Actions"
        >⋯</summary>
        <ul class="dropdown-content menu menu-sm bg-base-100 border border-base-300 rounded-box z-20 w-56 p-1 shadow">
          <li v-for="item in items" :key="item.label">
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
      <input
        ref="dateInput"
        v-model="dateValue"
        type="date"
        class="input input-xs input-bordered"
        aria-label="Date de résiliation"
        data-test="cancel-date"
      />
      <button class="btn btn-xs btn-primary" :disabled="busy" data-test="cancel-confirm" @click="saveCancel">
        Confirmer
      </button>
      <button class="btn btn-xs btn-ghost" @click="editor = null">Annuler</button>
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
