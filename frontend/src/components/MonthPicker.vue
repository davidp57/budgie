<script setup lang="ts">
/** MonthPicker — prev / current / next month buttons. */

const props = defineProps<{
  modelValue: string // "YYYY-MM"
}>()

const emit = defineEmits<{
  'update:modelValue': [value: string]
}>()

function parseMonth(value: string): { year: number; month: number } {
  const parts = value.split('-')
  return { year: Number(parts[0]), month: Number(parts[1]) }
}

function formatMonth(year: number, month: number): string {
  return `${year}-${String(month).padStart(2, '0')}`
}

function displayLabel(value: string): string {
  const { year, month } = parseMonth(value)
  return new Date(year, month - 1, 1).toLocaleDateString(undefined, {
    year: 'numeric',
    month: 'long',
  })
}

function prev(): void {
  let { year, month } = parseMonth(props.modelValue)
  month -= 1
  if (month < 1) {
    month = 12
    year -= 1
  }
  emit('update:modelValue', formatMonth(year, month))
}

function next(): void {
  let { year, month } = parseMonth(props.modelValue)
  month += 1
  if (month > 12) {
    month = 1
    year += 1
  }
  emit('update:modelValue', formatMonth(year, month))
}

function goToday(): void {
  const now = new Date()
  emit('update:modelValue', formatMonth(now.getFullYear(), now.getMonth() + 1))
}
</script>

<template>
  <div class="flex items-center gap-1">
    <button class="btn btn-ghost btn-sm btn-circle" title="Previous month" @click="prev">‹</button>
    <button class="btn btn-ghost btn-sm font-medium min-w-32 text-center" @click="goToday">
      {{ displayLabel(modelValue) }}
    </button>
    <button class="btn btn-ghost btn-sm btn-circle" title="Next month" @click="next">›</button>
  </div>
</template>
