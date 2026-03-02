<script setup lang="ts">
/**
 * CategoryPicker — grouped <select> for picking a category.
 * v-model: category_id (number | null)
 */
import type { CategoryGroupWithCategories } from '@/api/types'

defineProps<{
  modelValue: number | null
  groups: CategoryGroupWithCategories[]
}>()

const emit = defineEmits<{
  'update:modelValue': [value: number | null]
}>()

function onChange(ev: Event): void {
  const val = (ev.target as HTMLSelectElement).value
  emit('update:modelValue', val === '' ? null : Number(val))
}
</script>

<template>
  <select
    class="select select-bordered select-sm"
    :value="modelValue ?? ''"
    @change="onChange"
  >
    <option value="">— No category —</option>
    <optgroup v-for="group in groups" :key="group.id" :label="group.name">
      <option
        v-for="cat in group.categories"
        :key="cat.id"
        :value="cat.id"
      >
        {{ cat.name }}
      </option>
    </optgroup>
  </select>
</template>
