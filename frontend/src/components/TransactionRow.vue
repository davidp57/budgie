<script setup lang="ts">
import { ref } from 'vue'
import { deleteTransaction, updateTransaction } from '@/api/transactions'
import {
  formatAmount,
  type Category,
  type CategoryGroupWithCategories,
  type Transaction,
} from '@/api/types'
import CategoryPicker from './CategoryPicker.vue'

const props = defineProps<{
  txn: Transaction
  groups: CategoryGroupWithCategories[]
}>()

const emit = defineEmits<{
  (e: 'category-saved', txn: Transaction, categoryId: number | null): void
  (e: 'error', message: string): void
  (e: 'category-created', category: Category): void
  (e: 'realized', txnId: number): void
  (e: 'deleted', txnId: number): void
}>()

const editing = ref(false)
const editCategoryId = ref<number | null>(null)
const realizing = ref(false)
const deleting = ref(false)

function startEdit(): void {
  editCategoryId.value = props.txn.category_id
  editing.value = true
}

function cancelEdit(): void {
  editing.value = false
}

async function saveEdit(): Promise<void> {
  try {
    await updateTransaction(props.txn.id, { category_id: editCategoryId.value })
    emit('category-saved', props.txn, editCategoryId.value)
    editing.value = false
  } catch {
    emit('error', 'Failed to update category.')
  }
}

function categoryName(id: number | null): string {
  if (id === null) return '—'
  for (const g of props.groups) {
    const cat = g.categories.find((c) => c.id === id)
    if (cat) return cat.name
  }
  return String(id)
}

async function realizeTransaction(): Promise<void> {
  realizing.value = true
  try {
    await updateTransaction(props.txn.id, { status: 'real' })
    emit('realized', props.txn.id)
  } catch {
    emit('error', 'Failed to realize transaction.')
  } finally {
    realizing.value = false
  }
}

async function deleteVirtualTransaction(): Promise<void> {
  deleting.value = true
  try {
    await deleteTransaction(props.txn.id)
    emit('deleted', props.txn.id)
  } catch {
    emit('error', 'Failed to delete transaction.')
  } finally {
    deleting.value = false
  }
}
</script>

<template>
  <tr class="group" :class="txn.status === 'planned' ? 'opacity-60 border-dashed' : ''">
    <td class="tabular-nums">
      <span v-if="txn.status === 'planned'" class="mr-1" title="Forecast">⏳</span>{{ txn.date }}
    </td>
    <td :class="txn.amount < 0 ? 'text-error' : 'text-success'" class="tabular-nums">
      {{ formatAmount(txn.amount) }}
    </td>
    <td class="max-w-xs">
      <div class="flex items-center gap-1.5 min-w-0">
        <span class="truncate text-base-content/70">{{ txn.memo ?? '—' }}</span>
        <a
          v-if="txn.memo"
          :href="`https://duckduckgo.com/?q=${encodeURIComponent(txn.memo)}`"
          target="_blank"
          rel="noopener noreferrer"
          class="flex-shrink-0 opacity-0 group-hover:opacity-100 transition-opacity btn btn-ghost btn-xs p-0.5"
          title="Search on DuckDuckGo"
          @click.stop
        >
          <svg xmlns="http://www.w3.org/2000/svg" class="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
          </svg>
        </a>
      </div>
    </td>

    <!-- Inline category edit -->
    <td>
      <template v-if="editing">
        <div class="flex gap-1 items-center">
          <CategoryPicker
            v-model="editCategoryId"
            :groups="groups"
            @category-created="(cat) => emit('category-created', cat)"
          />
          <button class="btn btn-xs btn-success" @click="saveEdit">✓</button>
          <button class="btn btn-xs btn-ghost" @click="cancelEdit">✕</button>
        </div>
      </template>
      <template v-else>
        <button class="btn btn-ghost btn-xs" @click="startEdit">
          {{ categoryName(txn.category_id) }}
        </button>
      </template>
    </td>

    <td>
      <span
        class="badge badge-sm"
        :class="{
          'badge-ghost': txn.status === 'real',
          'badge-warning': txn.status === 'planned',
          'badge-success': txn.status === 'reconciled',
        }"
      >
        {{ txn.status }}
      </span>
      <span v-if="txn.status === 'planned'" class="inline-flex gap-1 ml-2 opacity-0 group-hover:opacity-100 transition-opacity">
        <button
          class="btn btn-xs btn-success"
          :disabled="realizing || deleting"
          :title="'Mark as real transaction'"
          @click.stop="realizeTransaction"
        >
          <span v-if="realizing" class="loading loading-spinner loading-xs"></span>
          <span v-else>✓ Realize</span>
        </button>
        <button
          class="btn btn-xs btn-error btn-outline"
          :disabled="realizing || deleting"
          :title="'Delete forecast'"
          @click.stop="deleteVirtualTransaction"
        >
          <span v-if="deleting" class="loading loading-spinner loading-xs"></span>
          <span v-else>✕</span>
        </button>
      </span>
    </td>
  </tr>
</template>
