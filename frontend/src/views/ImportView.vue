<script setup lang="ts">
import { onMounted, ref } from 'vue'
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

const accounts = ref<Account[]>([])
const selectedAccountId = ref<number | null>(null)
const selectedFormat = ref<ImportFormat>('csv')
const step = ref<Step>('setup')
const parsing = ref(false)
const confirming = ref(false)
const preview = ref<ImportedTransaction[]>([])
const result = ref<ImportResult | null>(null)
const error = ref('')

// Virtual matching
const virtualUnlinked = ref<Transaction[]>([])
// Keyed by row index: undefined = suggestion pending, -1 = dismissed, >0 = accepted virtual id
const linkDecisions = ref<Record<number, number>>({})

onMounted(async () => {
  accounts.value = await listAccounts()
  if (accounts.value.length > 0) {
    selectedAccountId.value = accounts.value[0]?.id ?? null
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

/** Find the best matching pending virtual transaction for an imported row. */
function findSuggestion(txn: ImportedTransaction): Transaction | null {
  const txnDate = new Date(txn.date).getTime()
  const candidates = virtualUnlinked.value.filter((v) => {
    // Amount must be within 10% (same sign)
    if (Math.sign(v.amount) !== Math.sign(txn.amount)) return false
    const diff = Math.abs(v.amount - txn.amount)
    const threshold = Math.abs(v.amount) * 0.1
    if (diff > threshold) return false
    // Date must be within 60 days
    const daysDiff = Math.abs(new Date(v.date).getTime() - txnDate) / 86_400_000
    return daysDiff <= 60
  })
  if (candidates.length === 0) return null
  // Best match: smallest absolute amount difference, then closest date
  return candidates.sort((a, b) => {
    const dA = Math.abs(a.amount - txn.amount)
    const dB = Math.abs(b.amount - txn.amount)
    if (dA !== dB) return dA - dB
    const dateA = Math.abs(new Date(a.date).getTime() - txnDate)
    const dateB = Math.abs(new Date(b.date).getTime() - txnDate)
    return dateA - dateB
  })[0] ?? null
}

async function onFileSelected(file: File): Promise<void> {
  if (!selectedAccountId.value) {
    error.value = 'Please select an account first.'
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
    error.value = extractError(err, 'Failed to parse file. Check the format and try again.')
  } finally {
    parsing.value = false
  }
}

function acceptLink(index: number, virtualId: number): void {
  linkDecisions.value = { ...linkDecisions.value, [index]: virtualId }
}

function dismissLink(index: number): void {
  linkDecisions.value = { ...linkDecisions.value, [index]: -1 }
}

async function onConfirm(): Promise<void> {
  if (!selectedAccountId.value) return
  confirming.value = true
  error.value = ''
  try {
    // Embed accepted virtual links before sending
    const enriched = preview.value.map((txn, i) => {
      const decision = linkDecisions.value[i]
      const suggestion = findSuggestion(txn)
      // If user accepted the suggestion (or suggestion exists and not dismissed)
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
    error.value = extractError(err, 'Import failed.')
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
</script>

<template>
  <div>
    <h1 class="text-2xl font-bold mb-6">Import transactions</h1>

    <!-- Step 1: setup + file drop -->
    <div v-if="step === 'setup'" class="card bg-base-100 shadow max-w-xl">
      <div class="card-body gap-4">
        <!-- Account selector -->
        <label class="form-control">
          <div class="label"><span class="label-text font-medium">Target account</span></div>
          <select v-model="selectedAccountId" class="select select-bordered">
            <option v-if="accounts.length === 0" :value="null" disabled>No accounts — create one in Settings</option>
            <option v-for="acc in accounts" :key="acc.id" :value="acc.id">{{ acc.name }}</option>
          </select>
        </label>

        <!-- Format selector -->
        <div class="form-control">
          <div class="label"><span class="label-text font-medium">File format</span></div>
          <div class="flex gap-4 flex-wrap">
            <label
              v-for="fmt in (['csv', 'excel', 'qif', 'ofx'] as ImportFormat[])"
              :key="fmt"
              class="label cursor-pointer gap-2"
            >
              <input type="radio" class="radio radio-sm" :value="fmt" v-model="selectedFormat" />
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
    </div>

    <!-- Step 2: preview table -->
    <div v-else-if="step === 'preview'">
      <div class="flex items-center justify-between mb-4">
        <span class="text-base-content/70">
          <strong>{{ preview.length }}</strong> transaction{{ preview.length !== 1 ? 's' : '' }} parsed — verify before importing
        </span>
        <button class="btn btn-ghost btn-sm" @click="reset">← Back</button>
      </div>

      <div class="card bg-base-100 shadow overflow-x-auto mb-4">
        <table class="table table-sm">
          <thead>
            <tr>
              <th>Date</th>
              <th>Description</th>
              <th>Payee</th>
              <th class="text-right">Amount</th>
              <th v-if="virtualUnlinked.length > 0">Forecast match ⏳</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(txn, i) in preview" :key="i">
              <td class="tabular-nums">{{ txn.date }}</td>
              <td class="max-w-xs truncate text-base-content/70">{{ txn.description }}</td>
              <td class="text-base-content/60">{{ txn.payee_name ?? '—' }}</td>
              <td
                class="text-right tabular-nums"
                :class="txn.amount < 0 ? 'text-error' : 'text-success'"
              >
                {{ formatAmount(txn.amount) }}
              </td>
              <!-- Virtual match suggestion column -->
              <td v-if="virtualUnlinked.length > 0">
                <template v-if="linkDecisions[i] === -1">
                  <span class="text-base-content/30 text-xs italic">dismissed</span>
                </template>
                <template v-else-if="(linkDecisions[i] ?? 0) > 0">
                  <span class="badge badge-success badge-sm gap-1">
                    ✓ linked
                    <button
                      class="ml-1 opacity-60 hover:opacity-100"
                      @click="dismissLink(i)"
                    >✕</button>
                  </span>
                </template>
                <template v-else-if="findSuggestion(txn)">
                  <div class="flex flex-col gap-1">
                    <span class="text-xs text-base-content/60">
                      {{ findSuggestion(txn)?.memo ?? '—' }}
                      ({{ formatAmount(findSuggestion(txn)!.amount) }},
                      {{ findSuggestion(txn)?.date }})
                    </span>
                    <div class="flex gap-1">
                      <button
                        class="btn btn-xs btn-success"
                        @click="acceptLink(i, findSuggestion(txn)!.id)"
                      >✓ Link</button>
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
          <span v-if="confirming" class="loading loading-spinner loading-sm"></span>
          Import {{ preview.length }} transaction{{ preview.length !== 1 ? 's' : '' }}
        </button>
        <button class="btn btn-ghost" @click="reset">Cancel</button>
      </div>
    </div>

    <!-- Step 3: result -->
    <div v-else-if="step === 'done'" class="card bg-base-100 shadow max-w-md">
      <div class="card-body gap-3">
        <div class="alert alert-success">
          ✓ Imported <strong>{{ result?.imported }}</strong> transaction{{ result?.imported !== 1 ? 's' : '' }}
          <span v-if="result && result.duplicates > 0" class="text-sm ml-1">
            ({{ result.duplicates }} duplicate{{ result.duplicates !== 1 ? 's' : '' }} skipped)
          </span>
        </div>
        <button class="btn btn-ghost btn-sm" @click="reset">Import another file</button>
      </div>
    </div>
  </div>
</template>
