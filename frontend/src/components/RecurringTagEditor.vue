<script setup lang="ts">
/**
 * RecurringTagEditor — the tags of one recurring payment: every tag of the
 * user as a chip to put on or take off, a field to create one, and a cross
 * to delete a tag no payment carries any more.
 */

import { ref } from 'vue'
import type { RecurringTag } from '@/api/types'
import { TAG_NAME_MAX_LENGTH } from '@/api/recurring'

const props = defineProps<{
  tags: RecurringTag[]
  /** Tags carried by this payment. */
  selected: number[]
  /** Tags carried by at least one payment: only the others can be deleted. */
  usedTagIds: number[]
  busy: boolean
}>()

const emit = defineEmits<{
  tag: [tagId: number]
  untag: [tagId: number]
  create: [name: string]
  delete: [tagId: number]
}>()

const newName = ref('')

function toggle(tag: RecurringTag): void {
  if (props.selected.includes(tag.id)) emit('untag', tag.id)
  else emit('tag', tag.id)
}

/** Create the typed tag, or put the existing one of that name on. */
function submit(): void {
  const name = newName.value.trim()
  if (!name) return
  newName.value = ''
  const existing = props.tags.find((t) => t.name.toLocaleLowerCase() === name.toLocaleLowerCase())
  if (!existing) emit('create', name)
  else if (!props.selected.includes(existing.id)) emit('tag', existing.id)
}
</script>

<template>
  <div class="flex flex-col gap-2">
    <div v-if="tags.length > 0" class="flex flex-wrap gap-1.5">
      <span v-for="tag in tags" :key="tag.id" class="inline-flex items-center">
        <button
          type="button"
          class="badge badge-lg gap-1 cursor-pointer"
          :class="selected.includes(tag.id) ? 'badge-primary' : 'badge-outline'"
          :disabled="busy"
          :aria-pressed="selected.includes(tag.id)"
          data-test="tag-toggle"
          @click="toggle(tag)"
        >
          <span v-if="selected.includes(tag.id)" aria-hidden="true">✓</span>{{ tag.name }}
        </button>
        <button
          v-if="!usedTagIds.includes(tag.id)"
          type="button"
          class="btn btn-ghost btn-xs btn-circle text-base-content/40"
          :disabled="busy"
          :title="`Supprimer l'étiquette « ${tag.name} »`"
          :aria-label="`Supprimer l'étiquette « ${tag.name} »`"
          data-test="tag-delete"
          @click="emit('delete', tag.id)"
        >×</button>
      </span>
    </div>
    <form class="join w-full max-w-xs" @submit.prevent="submit">
      <input
        v-model="newName"
        type="text"
        :maxlength="TAG_NAME_MAX_LENGTH"
        class="input input-bordered input-sm join-item flex-1 min-w-0"
        placeholder="Nouvelle étiquette"
        aria-label="Nouvelle étiquette"
        data-test="tag-new"
      >
      <button type="submit" class="btn btn-sm join-item" :disabled="busy || !newName.trim()">
        Ajouter
      </button>
    </form>
  </div>
</template>
