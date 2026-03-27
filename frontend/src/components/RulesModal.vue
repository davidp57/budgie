<!--
  RulesModal — Manage categorization rules (CRUD).
  Receives the category groups from parent to avoid redundant API calls.
-->
<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { createRule, deleteRule, listRules, updateRule } from '@/api/categoryRules'
import type {
  CategoryGroupWithCategories,
  CategoryRule,
  CategoryRuleCreate,
} from '@/api/types'

const props = defineProps<{
  categoryGroups: CategoryGroupWithCategories[]
}>()

const emit = defineEmits<{
  close: []
  /** Emitted whenever the rules list changes (add/edit/delete). */
  changed: [count: number]
}>()

// ── State ─────────────────────────────────────────────────────────
const rules = ref<CategoryRule[]>([])
const loading = ref(false)
const error = ref('')

// ── Helpers ──────────────────────────────────────────────────────
const allCategories = computed(() => props.categoryGroups.flatMap((g) => g.categories))

function categoryName(id: number): string {
  return allCategories.value.find((c) => c.id === id)?.name ?? `(${id})`
}

const FIELD_LABELS: Record<string, string> = { payee: 'bénéficiaire', memo: 'mémo' }
const TYPE_LABELS: Record<string, string> = { contains: 'contient', exact: 'exact', regex: 'regex' }
const TX_TYPE_LABELS: Record<string, string> = { any: 'toute', debit: 'dépense', credit: 'revenu/avoir' }

// ── Load ──────────────────────────────────────────────────────────
async function load(): Promise<void> {
  loading.value = true
  error.value = ''
  try {
    rules.value = await listRules()
  } catch {
    error.value = 'Impossible de charger les règles.'
  } finally {
    loading.value = false
  }
}

onMounted(load)

// ── Delete ────────────────────────────────────────────────────────
const deletingId = ref<number | null>(null)

async function doDelete(id: number): Promise<void> {
  deletingId.value = id
  try {
    await deleteRule(id)
    rules.value = rules.value.filter((r) => r.id !== id)
    emit('changed', rules.value.length)
  } catch {
    error.value = 'Erreur lors de la suppression.'
  } finally {
    deletingId.value = null
  }
}

// ── Edit ─────────────────────────────────────────────────────────
const editingId = ref<number | null>(null)
const editForm = ref<CategoryRuleCreate>({
  pattern: '',
  match_field: 'memo',
  match_type: 'contains',
  category_id: 0,
  priority: 0,
  transaction_type: 'any',
})
const saving = ref(false)

function eursToCentimes(v: number | null): number | null {
  return v !== null ? Math.round(v * 100) : null
}

function centimesToEurs(v: number | null): number | null {
  return v !== null ? v / 100 : null
}

const editMinEur = ref<number | null>(null)
const editMaxEur = ref<number | null>(null)

function startEdit(rule: CategoryRule): void {
  editingId.value = rule.id
  editForm.value = {
    pattern: rule.pattern,
    match_field: rule.match_field,
    match_type: rule.match_type,
    category_id: rule.category_id,
    priority: rule.priority,
    transaction_type: rule.transaction_type ?? 'any',
  }
  editMinEur.value = centimesToEurs(rule.min_amount)
  editMaxEur.value = centimesToEurs(rule.max_amount)
}

function cancelEdit(): void {
  editingId.value = null
}

async function submitEdit(): Promise<void> {
  if (!editingId.value) return
  saving.value = true
  try {
    const updated = await updateRule(editingId.value, {
      ...editForm.value,
      min_amount: eursToCentimes(editMinEur.value),
      max_amount: eursToCentimes(editMaxEur.value),
      transaction_type: editForm.value.transaction_type ?? 'any',
    })
    rules.value = rules.value.map((r) => (r.id === updated.id ? updated : r))
    editingId.value = null
    emit('changed', rules.value.length)
  } catch {
    error.value = "Erreur lors de la mise à jour."
  } finally {
    saving.value = false
  }
}

// ── Add ───────────────────────────────────────────────────────────
const showAddForm = ref(false)
const addForm = ref<CategoryRuleCreate>({
  pattern: '',
  match_field: 'memo',
  match_type: 'contains',
  category_id: 0,
  priority: 0,
  transaction_type: 'any',
})
const adding = ref(false)

const addMinEur = ref<number | null>(null)
const addMaxEur = ref<number | null>(null)

function openAdd(): void {
  showAddForm.value = true
  addForm.value = { pattern: '', match_field: 'memo', match_type: 'contains', category_id: 0, priority: 0, transaction_type: 'any' }
  addMinEur.value = null
  addMaxEur.value = null
}

async function submitAdd(): Promise<void> {
  if (!addForm.value.pattern.trim() || !addForm.value.category_id) return
  adding.value = true
  try {
    const rule = await createRule({
      ...addForm.value,
      min_amount: eursToCentimes(addMinEur.value),
      max_amount: eursToCentimes(addMaxEur.value),
      transaction_type: addForm.value.transaction_type ?? 'any',
    })
    rules.value = [...rules.value, rule]
    showAddForm.value = false
    emit('changed', rules.value.length)
  } catch {
    error.value = "Erreur lors de la création de la règle."
  } finally {
    adding.value = false
  }
}
</script>

<template>
  <Teleport to="body">
    <div
      class="fixed inset-0 z-50 flex items-start justify-center overflow-y-auto py-6 px-4"
      style="background:rgba(0,0,0,.55);backdrop-filter:blur(4px);"
      @click.self="emit('close')"
    >
      <div class="bg-base-100 rounded-2xl shadow-2xl w-full max-w-3xl mx-auto my-auto">
        <!-- Header -->
        <div class="flex items-center justify-between px-6 py-4 border-b border-base-200">
          <h2 class="text-lg font-bold text-base-content">
            🏷️ Règles de catégorisation
            <span class="badge badge-neutral ml-2">{{ rules.length }}</span>
          </h2>
          <button class="btn btn-ghost btn-sm btn-circle" @click="emit('close')">✕</button>
        </div>

        <div class="p-6 flex flex-col gap-4">
          <!-- Error -->
          <div v-if="error" class="alert alert-error text-sm">{{ error }}</div>

          <!-- Loading skeleton -->
          <div v-if="loading" class="flex flex-col gap-2">
            <div v-for="i in 3" :key="i" class="skeleton h-10 rounded-lg" />
          </div>

          <!-- Empty state -->
          <div v-else-if="rules.length === 0 && !showAddForm" class="text-base-content/50 text-sm text-center py-6">
            Aucune règle — créez-en une pour automatiser la catégorisation.
          </div>

          <!-- Rules list -->
          <div v-else-if="!loading" class="flex flex-col gap-2">
            <div
              v-for="rule in rules"
              :key="rule.id"
              class="border border-base-200 rounded-xl overflow-hidden"
            >
              <!-- Edit form row -->
              <div v-if="editingId === rule.id" class="p-4 bg-base-200/50 flex flex-col gap-3">
                <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  <label class="form-control">
                    <div class="label py-0"><span class="label-text text-xs">Motif</span></div>
                    <input
                      v-model="editForm.pattern"
                      type="text"
                      class="input input-bordered input-sm"
                      placeholder="Motif à rechercher"
                    >
                  </label>
                  <label class="form-control">
                    <div class="label py-0"><span class="label-text text-xs">Catégorie</span></div>
                    <select v-model="editForm.category_id" class="select select-bordered select-sm">
                      <optgroup
                        v-for="group in categoryGroups"
                        :key="group.id"
                        :label="group.name"
                      >
                        <option
                          v-for="cat in group.categories"
                          :key="cat.id"
                          :value="cat.id"
                        >{{ cat.name }}</option>
                      </optgroup>
                    </select>
                  </label>
                  <label class="form-control">
                    <div class="label py-0"><span class="label-text text-xs">Champ</span></div>
                    <select v-model="editForm.match_field" class="select select-bordered select-sm">
                      <option value="memo">Mémo / description</option>
                      <option value="payee">Bénéficiaire</option>
                    </select>
                  </label>
                  <label class="form-control">
                    <div class="label py-0"><span class="label-text text-xs">Type</span></div>
                    <select v-model="editForm.match_type" class="select select-bordered select-sm">
                      <option value="contains">Contient</option>
                      <option value="exact">Exact</option>
                      <option value="regex">Regex</option>
                    </select>
                  </label>
                  <label class="form-control">
                    <div class="label py-0"><span class="label-text text-xs">Priorité</span></div>
                    <input
                      v-model.number="editForm.priority"
                      type="number"
                      class="input input-bordered input-sm"
                    >
                  </label>
                  <label class="form-control sm:col-span-2">
                    <div class="label py-0"><span class="label-text text-xs">Type de transaction</span></div>
                    <select v-model="editForm.transaction_type" class="select select-bordered select-sm">
                      <option value="any">Toute transaction (±)</option>
                      <option value="debit">Dépense uniquement (débit −)</option>
                      <option value="credit">Revenu / avoir uniquement (crédit +)</option>
                    </select>
                  </label>
                  <label class="form-control">
                    <div class="label py-0"><span class="label-text text-xs">Montant min (€)</span></div>
                    <input
                      v-model.number="editMinEur"
                      type="number"
                      step="0.01"
                      class="input input-bordered input-sm"
                      placeholder="ex&nbsp;: -50"
                    >
                  </label>
                  <label class="form-control">
                    <div class="label py-0"><span class="label-text text-xs">Montant max (€)</span></div>
                    <input
                      v-model.number="editMaxEur"
                      type="number"
                      step="0.01"
                      class="input input-bordered input-sm"
                      placeholder="ex&nbsp;: -5"
                    >
                  </label>
                </div>
                <div class="flex gap-2">
                  <button class="btn btn-primary btn-sm" :disabled="saving" @click="submitEdit">
                    <span v-if="saving" class="loading loading-spinner loading-xs" />
                    Enregistrer
                  </button>
                  <button class="btn btn-ghost btn-sm" @click="cancelEdit">Annuler</button>
                </div>
              </div>

              <!-- Display row -->
              <div v-else class="flex items-center gap-3 px-4 py-3">
                <div class="flex-1 min-w-0">
                  <span class="font-mono text-sm font-semibold text-base-content truncate block">{{ rule.pattern }}</span>
                  <span class="text-xs text-base-content/50">
                    <span class="badge badge-ghost badge-xs">{{ FIELD_LABELS[rule.match_field] ?? rule.match_field }}</span>
                    <span class="badge badge-ghost badge-xs ml-1">{{ TYPE_LABELS[rule.match_type] ?? rule.match_type }}</span>
                    → <span class="font-medium">{{ categoryName(rule.category_id) }}</span>
                    <span v-if="rule.priority !== 0" class="ml-2 opacity-50">prio&nbsp;{{ rule.priority }}</span>
                    <span v-if="rule.transaction_type && rule.transaction_type !== 'any'" class="ml-2 opacity-50">
                      {{ TX_TYPE_LABELS[rule.transaction_type] ?? rule.transaction_type }}
                    </span>
                    <span v-if="rule.min_amount !== null || rule.max_amount !== null" class="ml-2 opacity-50">
                      [{{ rule.min_amount !== null ? (rule.min_amount / 100).toFixed(2) + '€' : '-∞' }}
                      —
                      {{ rule.max_amount !== null ? (rule.max_amount / 100).toFixed(2) + '€' : '+∞' }}]
                    </span>
                  </span>
                </div>
                <div class="flex gap-1 shrink-0">
                  <button class="btn btn-ghost btn-xs" title="Modifier" @click="startEdit(rule)">✏️</button>
                  <button
                    class="btn btn-ghost btn-xs text-error"
                    title="Supprimer"
                    :disabled="deletingId === rule.id"
                    @click="doDelete(rule.id)"
                  >
                    <span v-if="deletingId === rule.id" class="loading loading-spinner loading-xs" />
                    <template v-else>🗑</template>
                  </button>
                </div>
              </div>
            </div>
          </div>

          <!-- Add form -->
          <div v-if="showAddForm" class="border border-primary/30 rounded-xl p-4 bg-primary/5 flex flex-col gap-3">
            <h3 class="font-semibold text-sm">Nouvelle règle</h3>
            <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <label class="form-control">
                <div class="label py-0"><span class="label-text text-xs">Motif *</span></div>
                <input
                  v-model="addForm.pattern"
                  type="text"
                  class="input input-bordered input-sm"
                  placeholder="Ex: NETFLIX, CARTE TOTAL, …"
                  autofocus
                >
              </label>
              <label class="form-control">
                <div class="label py-0"><span class="label-text text-xs">Catégorie *</span></div>
                <select v-model="addForm.category_id" class="select select-bordered select-sm">
                  <option :value="0" disabled>— choisir —</option>
                  <optgroup
                    v-for="group in categoryGroups"
                    :key="group.id"
                    :label="group.name"
                  >
                    <option
                      v-for="cat in group.categories"
                      :key="cat.id"
                      :value="cat.id"
                    >{{ cat.name }}</option>
                  </optgroup>
                </select>
              </label>
              <label class="form-control">
                <div class="label py-0"><span class="label-text text-xs">Champ</span></div>
                <select v-model="addForm.match_field" class="select select-bordered select-sm">
                  <option value="memo">Mémo / description</option>
                  <option value="payee">Bénéficiaire</option>
                </select>
              </label>
              <label class="form-control">
                <div class="label py-0"><span class="label-text text-xs">Type</span></div>
                <select v-model="addForm.match_type" class="select select-bordered select-sm">
                  <option value="contains">Contient</option>
                  <option value="exact">Exact</option>
                  <option value="regex">Regex</option>
                </select>
              </label>
              <label class="form-control">
                <div class="label py-0"><span class="label-text text-xs">Priorité</span></div>
                <input
                  v-model.number="addForm.priority"
                  type="number"
                  class="input input-bordered input-sm"
                >
              </label>
              <label class="form-control sm:col-span-2">
                <div class="label py-0"><span class="label-text text-xs">Type de transaction</span></div>
                <select v-model="addForm.transaction_type" class="select select-bordered select-sm">
                  <option value="any">Toute transaction (±)</option>
                  <option value="debit">Dépense uniquement (débit −)</option>
                  <option value="credit">Revenu / avoir uniquement (crédit +)</option>
                </select>
              </label>
              <label class="form-control">
                <div class="label py-0"><span class="label-text text-xs">Montant min (€)</span></div>
                <input
                  v-model.number="addMinEur"
                  type="number"
                  step="0.01"
                  class="input input-bordered input-sm"
                  placeholder="ex&nbsp;: -50"
                >
              </label>
              <label class="form-control">
                <div class="label py-0"><span class="label-text text-xs">Montant max (€)</span></div>
                <input
                  v-model.number="addMaxEur"
                  type="number"
                  step="0.01"
                  class="input input-bordered input-sm"
                  placeholder="ex&nbsp;: -5"
                >
              </label>
            </div>
            <div class="flex gap-2">
              <button
                class="btn btn-primary btn-sm"
                :disabled="adding || !addForm.pattern.trim() || !addForm.category_id"
                @click="submitAdd"
              >
                <span v-if="adding" class="loading loading-spinner loading-xs" />
                Créer la règle
              </button>
              <button class="btn btn-ghost btn-sm" @click="showAddForm = false">Annuler</button>
            </div>
          </div>

          <!-- Add button -->
          <div v-if="!showAddForm">
            <button class="btn btn-outline btn-sm gap-1" @click="openAdd">
              ➕ Nouvelle règle
            </button>
          </div>
        </div>
      </div>
    </div>
  </Teleport>
</template>
