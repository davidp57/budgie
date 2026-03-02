<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { listAccounts } from '@/api/accounts'
import { confirmImport } from '@/api/imports'
import { type Account, type ImportResult } from '@/api/types'
import FileUploader from '@/components/FileUploader.vue'

type ImportFormat = 'csv' | 'excel' | 'qif' | 'ofx'

const accounts = ref<Account[]>([])
const selectedAccountId = ref<number | null>(null)
const selectedFormat = ref<ImportFormat>('csv')
const loading = ref(false)
const result = ref<ImportResult | null>(null)
const error = ref('')

onMounted(async () => {
  accounts.value = await listAccounts()
  if (accounts.value.length > 0) {
    selectedAccountId.value = accounts.value[0]?.id ?? null
  }
})

async function onFileSelected(file: File): Promise<void> {
  if (!selectedAccountId.value) {
    error.value = 'Please select an account first.'
    return
  }
  loading.value = true
  error.value = ''
  result.value = null
  try {
    result.value = await confirmImport(selectedAccountId.value, file, selectedFormat.value)
  } catch {
    error.value = 'Import failed. Check the file format and try again.'
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div>
    <h1 class="text-2xl font-bold mb-6">Import transactions</h1>

    <div class="card bg-base-100 shadow max-w-xl">
      <div class="card-body gap-4">
        <!-- Account selector -->
        <label class="form-control">
          <div class="label"><span class="label-text font-medium">Target account</span></div>
          <select v-model="selectedAccountId" class="select select-bordered">
            <option v-for="acc in accounts" :key="acc.id" :value="acc.id">
              {{ acc.name }}
            </option>
          </select>
        </label>

        <!-- Format selector -->
        <label class="form-control">
          <div class="label"><span class="label-text font-medium">File format</span></div>
          <div class="flex gap-2 flex-wrap">
            <label
              v-for="fmt in (['csv', 'excel', 'qif', 'ofx'] as ImportFormat[])"
              :key="fmt"
              class="label cursor-pointer gap-2"
            >
              <input
                type="radio"
                class="radio radio-sm"
                :value="fmt"
                v-model="selectedFormat"
              />
              <span class="label-text uppercase text-sm">{{ fmt }}</span>
            </label>
          </div>
        </label>

        <!-- File drop zone -->
        <FileUploader
          :accept="selectedFormat === 'excel' ? '.xlsx,.xls' : `.${selectedFormat}`"
          :loading="loading"
          @file-selected="onFileSelected"
        />

        <!-- Result -->
        <div v-if="result" class="alert alert-success">
          <span>✓ Imported <strong>{{ result.imported }}</strong> transaction{{ result.imported !== 1 ? 's' : '' }}</span>
          <span v-if="result.skipped > 0" class="ml-2 text-sm">({{ result.skipped }} duplicate{{ result.skipped !== 1 ? 's' : '' }} skipped)</span>
        </div>

        <div v-if="error" class="alert alert-error">{{ error }}</div>
      </div>
    </div>
  </div>
</template>
