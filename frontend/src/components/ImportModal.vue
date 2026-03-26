<!--
  ImportModal — Bank file import flow as a modal overlay.
  Emits 'close' when the user cancels or dismisses, and 'imported' after a
  successful import so the parent can reload its data.
-->
<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import axios from 'axios'
import { listAccounts } from '@/api/accounts'
import { confirmImport, parseFile } from '@/api/imports'
import { listPlannedUnlinked } from '@/api/transactions'
import {
  formatAmount,
  type Account,
  type ImportedTransaction,
  type ImportResult,
  type Transaction,
} from '@/api/types'
import FileUploader from '@/components/FileUploader.vue'

type ImportFormat = 'csv' | 'excel' | 'qif' | 'ofx'
type Step = 'setup' | 'preview' | 'done'

const emit = defineEmits<{
  close: []
  imported: [result: ImportResult]
}>()

const props = defineProps<{
  /** Pre-select this account id when the modal opens. */
  initialAccountId?: number | null
}>()

const accounts = ref<Account[]>([])
const selectedAccountId = ref<number | null>(props.initialAccountId ?? null)
const selectedFormat = ref<ImportFormat>('csv')
const step = ref<Step>('setup')
const parsing = ref(false)
const confirming = ref(false)
const preview = ref<ImportedTransaction[]>([])
const result = ref<ImportResult | null>(null)
const error = ref('')

// Virtual matching
const virtualUnlinked = ref<Transaction[]>([])
const linkDecisions = ref<Record<number, number>>({})

// Precomputed suggestion map: preview index → best matching virtual transaction
const suggestionMap = computed<Map<number, Transaction | null>>(() => {
  const map = new Map<number, Transaction | null>()
  for (let i = 0; i < preview.value.length; i++) {
    map.set(i, findSuggestionFor(preview.value[i]!))
  }
  return map
})

onMounted(async () => {
  try {
    accounts.value = await listAccounts()
    if (selectedAccountId.value === null && accounts.value.length > 0) {
      selectedAccountId.value = accounts.value[0]?.id ?? null
    }
  } catch {
    // 401 handled by axios interceptor
  }
})

function extractError(err: unknown, fallback: string): string {
  if (axios.isAxiosError(err)) {
    const detail = err.response?.data?.detail
    if (typeof detail === 'string') return detail
    if (Array.isArray(detail) && detail.length > 0) {
      return detail.map((d: { msg?: string }) => d.msg ?? '').join(' ')
    }
  }
  return fallback
}

function findSuggestionFor(txn: ImportedTransaction): Transaction | null {
  const txnDate = new Date(txn.date).getTime()
  const candidates = virtualUnlinked.value.filter((v) => {
    if (Math.sign(v.amount) !== Math.sign(txn.amount)) return false
    const diff = Math.abs(v.amount - txn.amount)
    const threshold = Math.abs(v.amount) * 0.1
    if (diff > threshold) return false
    const daysDiff = Math.abs(new Date(v.date).getTime() - txnDate) / 86_400_000
    return daysDiff <= 60
  })
  if (candidates.length === 0) return null
  return candidates.sort((a, b) => {
    const dA = Math.abs(a.amount - txn.amount)
    const dB = Math.abs(b.amount - txn.amount)
    if (dA !== dB) return dA - dB
    const dateA = Math.abs(new Date(a.date).getTime() - txnDate)
    const dateB = Math.abs(new Date(b.date).getTime() - txnDate)
    return dateA - dateB
  })[0] ?? null
}

function acceptLink(index: number, virtualId: number): void {
  linkDecisions.value = { ...linkDecisions.value, [index]: virtualId }
}

function dismissLink(index: number): void {
  linkDecisions.value = { ...linkDecisions.value, [index]: -1 }
}

async function onFileSelected(file: File): Promise<void> {
  if (!selectedAccountId.value) {
    error.value = 'Veuillez sélectionner un compte.'
    return
  }
  parsing.value = true
  error.value = ''
  try {
    const [resp, virtuals] = await Promise.all([
      parseFile(file, selectedFormat.value),
      listPlannedUnlinked(),
    ])
    preview.value = resp.transactions
    virtualUnlinked.value = virtuals
    linkDecisions.value = {}
    step.value = 'preview'
  } catch (err) {
    error.value = extractError(err, 'Impossible de lire le fichier. Vérifiez le format.')
  } finally {
    parsing.value = false
  }
}

async function onConfirm(): Promise<void> {
  if (!selectedAccountId.value) return
  confirming.value = true
  error.value = ''
  try {
    const enriched = preview.value.map((txn, i) => {
      const decision = linkDecisions.value[i]
      const suggestion = suggestionMap.value.get(i) ?? null
      const virtualId =
        decision !== undefined && decision > 0
          ? decision
          : decision === undefined && suggestion !== null
            ? suggestion.id
            : null
      return { ...txn, virtual_linked_id: virtualId }
    })
    result.value = await confirmImport(selectedAccountId.value, enriched)
    step.value = 'done'
  } catch (err) {
    error.value = extractError(err, "L'import a échoué.")
  } finally {
    confirming.value = false
  }
}

function reset(): void {
  step.value = 'setup'
  preview.value = []
  virtualUnlinked.value = []
  linkDecisions.value = {}
  result.value = null
  error.value = ''
}

function closeAndReload(): void {
  if (result.value) {
    emit('imported', result.value)
  }
  emit('close')
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
          <h2 class="text-lg font-bold text-base-content">📤 Importer des transactions</h2>
          <button class="btn btn-ghost btn-sm btn-circle" @click="emit('close')">✕</button>
        </div>

        <div class="p-6">

          <!-- Step 1: setup + file drop -->
          <div v-if="step === 'setup'" class="flex flex-col gap-4 max-w-xl">
            <!-- Account selector -->
            <label class="form-control">
              <div class="label"><span class="label-text font-medium">Compte cible</span></div>
              <select v-model="selectedAccountId" class="select select-bordered">
                <option v-if="accounts.length === 0" :value="null" disabled>
                  Aucun compte — créez-en un dans les Réglages
                </option>
                <option v-for="acc in accounts" :key="acc.id" :value="acc.id">{{ acc.name }}</option>
              </select>
            </label>

            <!-- Format selector -->
            <div class="form-control">
              <div class="label"><span class="label-text font-medium">Format du fichier</span></div>
              <div class="flex gap-4 flex-wrap">
                <label
                  v-for="fmt in (['csv', 'excel', 'qif', 'ofx'] as ImportFormat[])"
                  :key="fmt"
                  class="label cursor-pointer gap-2"
                >
                  <input v-model="selectedFormat" type="radio" class="radio radio-sm" :value="fmt">
                  <span class="label-text uppercase text-sm font-mono">{{ fmt }}</span>
                </label>
              </div>
            </div>

            <!-- File drop zone -->
            <FileUploader
              :accept="selectedFormat === 'excel' ? '.xlsx,.xls' : `.${selectedFormat}`"
              :loading="parsing"
              @file-selected="onFileSelected"
            />

            <div v-if="error" class="alert alert-error text-sm">{{ error }}</div>
          </div>

          <!-- Step 2: preview table -->
          <div v-else-if="step === 'preview'">
            <div class="flex items-center justify-between mb-4">
              <span class="text-base-content/70">
                <strong>{{ preview.length }}</strong> transaction{{ preview.length !== 1 ? 's' : '' }} — vérifiez avant d'importer
              </span>
              <button class="btn btn-ghost btn-sm" @click="reset">← Retour</button>
            </div>

            <div class="overflow-x-auto mb-4 rounded-xl border border-base-200">
              <table class="table table-sm">
                <thead>
                  <tr>
                    <th>Date</th>
                    <th>Description</th>
                    <th>Bénéficiaire</th>
                    <th class="text-right">Montant</th>
                    <th v-if="virtualUnlinked.length > 0">Prévu ⏳</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="(txn, i) in preview" :key="i">
                    <td class="tabular-nums">{{ txn.date }}</td>
                    <td class="max-w-xs truncate text-base-content/70">{{ txn.description }}</td>
                    <td class="text-base-content/60">{{ txn.payee_name ?? '—' }}</td>
                    <td
                      class="text-right tabular-nums font-semibold"
                      :class="txn.amount < 0 ? 'text-error' : 'text-success'"
                    >
                      {{ formatAmount(txn.amount) }}
                    </td>
                    <td v-if="virtualUnlinked.length > 0">
                      <template v-if="linkDecisions[i] === -1">
                        <span class="text-base-content/30 text-xs italic">ignoré</span>
                      </template>
                      <template v-else-if="(linkDecisions[i] ?? 0) > 0">
                        <span class="badge badge-success badge-sm gap-1">
                          ✓ lié
                          <button class="ml-1 opacity-60 hover:opacity-100" @click="dismissLink(i)">✕</button>
                        </span>
                      </template>
                      <template v-else-if="suggestionMap.get(i)"><!-- computed index -->
                        <div class="flex flex-col gap-1">
                          <span class="text-xs text-base-content/60">
                            {{ suggestionMap.get(i)?.memo ?? '\u2014' }}
                            ({{ formatAmount(suggestionMap.get(i)!.amount) }},
                            {{ suggestionMap.get(i)?.date }})
                          </span>
                          <div class="flex gap-1">
                            <button
                              class="btn btn-xs btn-success"
                              @click="acceptLink(i, suggestionMap.get(i)!.id)"
                            >✓ Lier</button>
                            <button class="btn btn-xs btn-ghost" @click="dismissLink(i)">✕</button>
                          </div>
                        </div>
                      </template>
                      <template v-else>
                        <span class="text-base-content/30 text-xs">—</span>
                      </template>
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>

            <div v-if="error" class="alert alert-error text-sm mb-4">{{ error }}</div>

            <div class="flex gap-2">
              <button class="btn btn-primary" :disabled="confirming" @click="onConfirm">
                <span v-if="confirming" class="loading loading-spinner loading-sm" />
                Importer {{ preview.length }} transaction{{ preview.length !== 1 ? 's' : '' }}
              </button>
              <button class="btn btn-ghost" @click="reset">Annuler</button>
            </div>
          </div>

          <!-- Step 3: result -->
          <div v-else-if="step === 'done'" class="flex flex-col gap-4 max-w-md">
            <div class="alert alert-success">
              ✓ <strong>{{ result?.imported }}</strong> transaction{{ result?.imported !== 1 ? 's' : '' }} importée{{ result?.imported !== 1 ? 's' : '' }}
              <span v-if="result && result.duplicates > 0" class="text-sm ml-1">
                ({{ result.duplicates }} doublon{{ result.duplicates !== 1 ? 's' : '' }} ignoré{{ result.duplicates !== 1 ? 's' : '' }})
              </span>
            </div>
            <div class="flex gap-2">
              <button class="btn btn-ghost btn-sm" @click="reset">Importer un autre fichier</button>
              <button class="btn btn-primary btn-sm" @click="closeAndReload">Fermer et actualiser</button>
            </div>
          </div>

        </div>
      </div>
    </div>
  </Teleport>
</template>
