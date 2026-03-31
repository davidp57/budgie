<script setup lang="ts">
/**
 * CategoryPicker — combobox for picking (or creating) a category.
 *
 * v-model: category_id (number | null)
 *
 * Emits 'create' with the typed name when the user selects "Create …".
 * The parent should POST the new category and call back via v-model.
 */
import { computed, onMounted, onUnmounted, ref, watch, nextTick } from 'vue'
import type { CategoryGroupWithCategories, Category } from '@/api/types'
import CreateCategoryModal from './CreateCategoryModal.vue'

const props = defineProps<{
  modelValue: number | null
  groups: CategoryGroupWithCategories[]
}>()

const emit = defineEmits<{
  'update:modelValue': [value: number | null]
  'category-created': [category: Category]
}>()

// ── flat list of all categories ───────────────────────────────────
const allCategories = computed<Category[]>(() =>
  props.groups.flatMap((g) => g.categories),
)

// ── search text shown in the input ───────────────────────────────
const query = ref('')
const open = ref(false)
const showModal = ref(false)
const pendingName = ref('')

// ── dropdown positioning (fixed, escapes overflow containers) ─────
const inputWrapperRef = ref<HTMLElement | null>(null)
const dropdownStyle = ref<Record<string, string>>({})

function updateDropdownPosition(): void {
  if (!inputWrapperRef.value) return
  const rect = inputWrapperRef.value.getBoundingClientRect()
  const spaceBelow = window.innerHeight - rect.bottom - 4
  const spaceAbove = rect.top - 4
  const base = {
    position: 'fixed',
    left: `${rect.left}px`,
    width: `${rect.width}px`,
    zIndex: '9999',
  }
  if (spaceBelow >= 150 || spaceBelow >= spaceAbove) {
    // Enough space below — normal position
    dropdownStyle.value = { ...base, top: `${rect.bottom + 4}px`, maxHeight: `${Math.min(288, spaceBelow - 4)}px` }
  } else {
    // Not enough space below — flip above
    dropdownStyle.value = { ...base, bottom: `${window.innerHeight - rect.top + 4}px`, maxHeight: `${Math.min(288, spaceAbove - 4)}px` }
  }
}

// Set the display text from the current modelValue
watch(
  () => props.modelValue,
  (id) => {
    if (id === null) {
      query.value = ''
      return
    }
    const cat = allCategories.value.find((c) => c.id === id)
    if (cat) query.value = cat.name
  },
  { immediate: true },
)

// ── filtered list ────────────────────────────────────────────────
const filtered = computed<Category[]>(() => {
  const q = query.value.trim().toLowerCase()
  if (!q) return allCategories.value
  return allCategories.value.filter((c) => c.name.toLowerCase().includes(q))
})

/** True when the query doesn't match any existing category name exactly */
const canCreate = computed<boolean>(() => {
  const q = query.value.trim()
  if (!q) return false
  return !allCategories.value.some((c) => c.name.toLowerCase() === q.toLowerCase())
})

// ── interaction ───────────────────────────────────────────────────
function onInput(ev: Event): void {
  query.value = (ev.target as HTMLInputElement).value
  open.value = true
  nextTick(updateDropdownPosition)
}

function onFocus(): void {
  open.value = true
  nextTick(updateDropdownPosition)
}

function onBlur(): void {
  // Delay so click on option is registered first
  setTimeout(() => {
    open.value = false
    // Restore display text for current selection
    const cat = allCategories.value.find((c) => c.id === props.modelValue)
    query.value = cat ? cat.name : ''
  }, 150)
}

// Close and reposition when the viewport scrolls or resizes
function _handleScrollResize(): void {
  if (open.value) {
    updateDropdownPosition()
  }
}

onMounted(() => {
  window.addEventListener('scroll', _handleScrollResize, true)
  window.addEventListener('resize', _handleScrollResize)
})

onUnmounted(() => {
  window.removeEventListener('scroll', _handleScrollResize, true)
  window.removeEventListener('resize', _handleScrollResize)
})

function select(cat: Category): void {
  emit('update:modelValue', cat.id)
  query.value = cat.name
  open.value = false
}

function clear(): void {
  emit('update:modelValue', null)
  query.value = ''
  open.value = false
}

function openCreate(): void {
  pendingName.value = query.value.trim()
  showModal.value = true
  open.value = false
}

function onCategoryCreated(cat: Category): void {
  emit('category-created', cat)
  emit('update:modelValue', cat.id)
  query.value = cat.name
  showModal.value = false
}
</script>

<template>
  <div class="relative" ref="inputWrapperRef">
    <div class="flex gap-1 items-center">
      <input
        type="text"
        class="input input-bordered input-sm flex-1"
        placeholder="Search category…"
        :value="query"
        @input="onInput"
        @focus="onFocus"
        @blur="onBlur"
        autocomplete="off"
      />
      <button
        v-if="modelValue !== null"
        class="btn btn-ghost btn-xs"
        tabindex="-1"
        @mousedown.prevent="clear"
        title="Clear"
      >✕</button>
    </div>

    <!-- Dropdown rendered at body level to escape overflow containers -->
    <Teleport to="body">
      <ul
        v-if="open"
        :style="dropdownStyle"
        class="bg-base-100 border border-base-300 rounded-box shadow-lg overflow-y-auto text-sm"
      >
        <li
          v-for="cat in filtered"
          :key="cat.id"
          class="px-3 py-1.5 cursor-pointer hover:bg-base-200"
          :class="{ 'bg-primary/10 font-medium': cat.id === modelValue }"
          @mousedown.prevent="select(cat)"
        >
          {{ cat.name }}
        </li>

        <!-- "Create …" option -->
        <li
          v-if="canCreate"
          class="px-3 py-1.5 cursor-pointer hover:bg-base-200 text-primary italic border-t border-base-300"
          @mousedown.prevent="openCreate"
        >
          Create "{{ query.trim() }}"…
        </li>

        <li v-if="filtered.length === 0 && !canCreate" class="px-3 py-1.5 text-base-content/40 italic">
          No categories
        </li>
      </ul>
    </Teleport>
  </div>

  <!-- Inline category creation modal -->
  <CreateCategoryModal
    v-if="showModal"
    :initial-name="pendingName"
    :groups="groups"
    @confirm="onCategoryCreated"
    @cancel="showModal = false"
  />
</template>
