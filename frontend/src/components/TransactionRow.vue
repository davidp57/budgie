<script setup lang="ts">
import { ref } from 'vue'
import { updateTransaction } from '@/api/transactions'
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
}>()

const editing = ref(false)
const editCategoryId = ref<number | null>(null)

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
</script>

<template>
  <tr :class="txn.is_virtual ? 'opacity-60 border-dashed' : ''">
    <td class="tabular-nums">
      <span v-if="txn.is_virtual" class="mr-1" title="Forecast">⏳</span>{{ txn.date }}
    </td>
    <td :class="txn.amount < 0 ? 'text-error' : 'text-success'" class="tabular-nums">
      {{ formatAmount(txn.amount) }}
    </td>
    <td class="text-base-content/70 max-w-xs truncate">{{ txn.memo ?? '—' }}</td>

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
          'badge-ghost': txn.cleared === 'uncleared',
          'badge-info': txn.cleared === 'cleared',
          'badge-success': txn.cleared === 'reconciled',
        }"
      >
        {{ txn.cleared }}
      </span>
      <span v-if="txn.is_virtual" class="badge badge-sm badge-warning ml-1">forecast</span>
    </td>
  </tr>
</template>
