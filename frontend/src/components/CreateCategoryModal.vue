<script setup lang="ts">
/**
 * CreateCategoryModal — modal dialog to create a new category.
 *
 * Props:
 *   initialName — pre-filled category name (from the picker's search query)
 *   groups      — existing category groups for the group selector
 *
 * Emits:
 *   confirm(category) — when the category was successfully created
 *   cancel            — when the user dismisses the dialog
 */
import { ref, computed } from 'vue'
import type { Category, CategoryGroupWithCategories } from '@/api/types'
import { createCategory, createCategoryGroup } from '@/api/categories'

const props = defineProps<{
  initialName: string
  groups: CategoryGroupWithCategories[]
}>()

const emit = defineEmits<{
  confirm: [category: Category]
  cancel: []
}>()

const categoryName = ref(props.initialName)
const selectedGroupId = ref<number | 'new' | null>(
  props.groups.length ? props.groups[0]!.id : 'new',
)
const newGroupName = ref('')
const saving = ref(false)
const error = ref('')

const isNewGroup = computed(() => selectedGroupId.value === 'new')

async function confirm(): Promise<void> {
  const name = categoryName.value.trim()
  if (!name) {
    error.value = 'Category name is required.'
    return
  }

  saving.value = true
  error.value = ''
  try {
    let groupId: number

    if (isNewGroup.value) {
      const gName = newGroupName.value.trim()
      if (!gName) {
        error.value = 'Group name is required.'
        saving.value = false
        return
      }
      const group = await createCategoryGroup(gName)
      groupId = group.id
    } else {
      groupId = selectedGroupId.value as number
    }

    const category = await createCategory(groupId, name)
    emit('confirm', category)
  } catch {
    error.value = 'Failed to create category.'
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <!-- DaisyUI modal backdrop -->
  <div class="modal modal-open">
    <div class="modal-box max-w-sm">
      <h3 class="font-bold text-lg mb-4">New Category</h3>

      <!-- Category name -->
      <div class="form-control mb-3">
        <label class="label"><span class="label-text">Name</span></label>
        <input
          v-model="categoryName"
          type="text"
          class="input input-bordered input-sm"
          placeholder="e.g. Groceries"
          autofocus
          @keyup.enter="confirm"
          @keyup.escape="emit('cancel')"
        />
      </div>

      <!-- Group selector -->
      <div class="form-control mb-3">
        <label class="label"><span class="label-text">Group</span></label>
        <select
          v-model="selectedGroupId"
          class="select select-bordered select-sm"
        >
          <option v-for="g in groups" :key="g.id" :value="g.id">{{ g.name }}</option>
          <option value="new">— New group… —</option>
        </select>
      </div>

      <!-- New group name (shown when "New group…" is selected) -->
      <div v-if="isNewGroup" class="form-control mb-3">
        <label class="label"><span class="label-text">Group name</span></label>
        <input
          v-model="newGroupName"
          type="text"
          class="input input-bordered input-sm"
          placeholder="e.g. Household"
          @keyup.enter="confirm"
        />
      </div>

      <!-- Error -->
      <p v-if="error" class="text-error text-sm mb-2">{{ error }}</p>

      <!-- Actions -->
      <div class="modal-action">
        <button class="btn btn-ghost btn-sm" @click="emit('cancel')">Cancel</button>
        <button class="btn btn-primary btn-sm" :disabled="saving" @click="confirm">
          <span v-if="saving" class="loading loading-spinner loading-xs"></span>
          Create
        </button>
      </div>
    </div>
    <!-- Close on backdrop click -->
    <div class="modal-backdrop" @click="emit('cancel')" />
  </div>
</template>
