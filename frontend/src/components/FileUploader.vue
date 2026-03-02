<script setup lang="ts">
/**
 * FileUploader — drag-and-drop zone + click-to-browse.
 *
 * Props:
 *   accept   — file accept string (e.g. ".csv")
 *   loading  — show spinner instead of drop zone
 *
 * Emits:
 *   file-selected(file: File) — when a file has been selected
 */
import { ref } from 'vue'

const props = defineProps<{
  accept?: string
  loading?: boolean
}>()

const emit = defineEmits<{
  'file-selected': [file: File]
}>()

const dragging = ref(false)

function onDrop(ev: DragEvent): void {
  dragging.value = false
  const file = ev.dataTransfer?.files?.[0]
  if (file) emit('file-selected', file)
}

function onFileInput(ev: Event): void {
  const file = (ev.target as HTMLInputElement).files?.[0]
  if (file) emit('file-selected', file)
}
</script>

<template>
  <div
    class="border-2 border-dashed rounded-lg p-8 text-center transition-colors cursor-pointer"
    :class="dragging ? 'border-primary bg-primary/5' : 'border-base-300 hover:border-primary/50'"
    @dragover.prevent="dragging = true"
    @dragleave="dragging = false"
    @drop.prevent="onDrop"
  >
    <div v-if="loading" class="flex flex-col items-center gap-2">
      <span class="loading loading-spinner loading-md"></span>
      <span class="text-sm text-base-content/60">Importing…</span>
    </div>

    <label v-else class="flex flex-col items-center gap-2 cursor-pointer">
      <svg xmlns="http://www.w3.org/2000/svg" class="h-8 w-8 text-base-content/40" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12" />
      </svg>
      <span class="text-sm text-base-content/60">
        Drop file here or <span class="text-primary underline">browse</span>
      </span>
      <input
        type="file"
        class="hidden"
        :accept="props.accept"
        @change="onFileInput"
      />
    </label>
  </div>
</template>
