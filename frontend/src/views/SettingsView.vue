<script setup lang="ts">
import { onMounted, ref } from 'vue'
import {
  createAccount,
  deleteAccount,
  listAccounts,
} from '@/api/accounts'
import {
  createCategory,
  createCategoryGroup,
  deleteCategory,
  deleteCategoryGroup,
  listGroupsWithCategories,
} from '@/api/categories'
import { getPreferences, updatePreferences } from '@/api/users'
import EnvelopeManager from '@/components/EnvelopeManager.vue'
import type { Account, CategoryGroupWithCategories } from '@/api/types'

// ── Accounts ───────────────────────────────────────────────────

const accounts = ref<Account[]>([])
const newAccountName = ref('')
const newAccountType = ref<'checking' | 'savings' | 'credit' | 'cash'>('checking')
const newAccountOnBudget = ref(true)
const accountError = ref('')

// ── Category groups & categories ───────────────────────────────

const groups = ref<CategoryGroupWithCategories[]>([])
const newGroupName = ref('')
const newCategoryName = ref('')
const newCategoryGroupId = ref<number | null>(null)
const categoryError = ref('')

async function loadAll(): Promise<void> {
  const [acc, grps] = await Promise.all([listAccounts(), listGroupsWithCategories()])
  accounts.value = acc
  groups.value = grps
  if (grps.length > 0 && !newCategoryGroupId.value) {
    newCategoryGroupId.value = grps[0]?.id ?? null
  }
}

// ── Budgeting preferences ─────────────────────────────────────────────────
const budgetMode = ref<'n1' | 'n'>('n1')
const prefError = ref('')

async function setBudgetMode(mode: 'n1' | 'n'): Promise<void> {
  prefError.value = ''
  try {
    const updated = await updatePreferences({ budget_mode: mode })
    budgetMode.value = updated.budget_mode
  } catch {
    prefError.value = 'Failed to save preference.'
  }
}

onMounted(async () => {
  const prefs = await getPreferences()
  budgetMode.value = prefs.budget_mode
  await loadAll()
})

async function addAccount(): Promise<void> {
  accountError.value = ''
  if (!newAccountName.value.trim()) return
  try {
    await createAccount({
      name: newAccountName.value.trim(),
      account_type: newAccountType.value,
      on_budget: newAccountOnBudget.value,
    })
    newAccountName.value = ''
    await loadAll()
  } catch {
    accountError.value = 'Failed to create account.'
  }
}

async function removeAccount(id: number): Promise<void> {
  await deleteAccount(id)
  await loadAll()
}

async function addGroup(): Promise<void> {
  categoryError.value = ''
  if (!newGroupName.value.trim()) return
  try {
    await createCategoryGroup(newGroupName.value.trim())
    newGroupName.value = ''
    await loadAll()
  } catch {
    categoryError.value = 'Failed to create group.'
  }
}

async function removeGroup(id: number): Promise<void> {
  await deleteCategoryGroup(id)
  await loadAll()
}

async function addCategory(): Promise<void> {
  categoryError.value = ''
  if (!newCategoryName.value.trim() || !newCategoryGroupId.value) return
  try {
    await createCategory(newCategoryGroupId.value, newCategoryName.value.trim())
    newCategoryName.value = ''
    await loadAll()
  } catch {
    categoryError.value = 'Failed to create category.'
  }
}

async function removeCategory(id: number): Promise<void> {
  await deleteCategory(id)
  await loadAll()
}
</script>

<template>
  <div class="flex flex-col gap-8 max-w-2xl">
    <h1 class="text-2xl font-bold">Settings</h1>

    <!-- Accounts section -->
    <section class="card bg-base-100 shadow">
      <div class="card-body">
        <h2 class="card-title">Accounts</h2>

        <table class="table table-sm mb-3">
          <tbody>
            <tr v-if="accounts.length === 0">
              <td class="text-base-content/50">No accounts yet.</td>
            </tr>
            <tr v-for="acc in accounts" :key="acc.id">
              <td>{{ acc.name }}</td>
              <td class="text-base-content/60 text-sm">{{ acc.account_type }}</td>
              <td>
                <span v-if="acc.on_budget" class="badge badge-xs badge-success">on-budget</span>
                <span v-else class="badge badge-xs badge-ghost">off-budget</span>
              </td>
              <td class="text-right">
                <button class="btn btn-xs btn-error btn-ghost" @click="removeAccount(acc.id)">
                  Delete
                </button>
              </td>
            </tr>
          </tbody>
        </table>

        <div class="flex gap-2 flex-wrap items-end">
          <input
            v-model="newAccountName"
            type="text"
            placeholder="Account name"
            class="input input-bordered input-sm"
          />
          <select v-model="newAccountType" class="select select-bordered select-sm">
            <option value="checking">Checking</option>
            <option value="savings">Savings</option>
            <option value="credit">Credit</option>
            <option value="cash">Cash</option>
          </select>
          <label class="label cursor-pointer gap-2">
            <span class="label-text text-sm">On budget</span>
            <input type="checkbox" v-model="newAccountOnBudget" class="checkbox checkbox-sm" />
          </label>
          <button class="btn btn-primary btn-sm" @click="addAccount">Add</button>
        </div>

        <div v-if="accountError" class="alert alert-error text-sm py-1">{{ accountError }}</div>
      </div>
    </section>

    <!-- Category groups & categories section -->
    <section class="card bg-base-100 shadow">
      <div class="card-body">
        <h2 class="card-title">Category groups</h2>

        <div v-for="group in groups" :key="group.id" class="mb-3">
          <div class="flex items-center justify-between mb-1">
            <span class="font-medium">{{ group.name }}</span>
            <button class="btn btn-xs btn-error btn-ghost" @click="removeGroup(group.id)">
              Delete group
            </button>
          </div>
          <ul class="ml-4 text-sm text-base-content/70 flex flex-col gap-1">
            <li
              v-for="cat in group.categories"
              :key="cat.id"
              class="flex items-center justify-between"
            >
              <span>{{ cat.name }}</span>
              <button class="btn btn-xs btn-ghost" @click="removeCategory(cat.id)">✕</button>
            </li>
          </ul>
        </div>

        <div v-if="groups.length === 0" class="text-base-content/50 text-sm mb-3">
          No groups yet.
        </div>

        <div class="flex gap-2 flex-wrap items-center mb-2">
          <input
            v-model="newGroupName"
            type="text"
            placeholder="New group name"
            class="input input-bordered input-sm"
          />
          <button class="btn btn-outline btn-sm" @click="addGroup">Add group</button>
        </div>

        <div class="flex gap-2 flex-wrap items-center">
          <select v-model="newCategoryGroupId" class="select select-bordered select-sm">
            <option v-for="g in groups" :key="g.id" :value="g.id">{{ g.name }}</option>
          </select>
          <input
            v-model="newCategoryName"
            type="text"
            placeholder="New category name"
            class="input input-bordered input-sm"
          />
          <button class="btn btn-primary btn-sm" @click="addCategory">Add category</button>
        </div>

        <div v-if="categoryError" class="alert alert-error text-sm py-1">{{ categoryError }}</div>
      </div>
    </section>

    <!-- Envelopes section -->
    <section class="card bg-base-100 shadow">
      <div class="card-body">
        <h2 class="card-title">Envelopes</h2>
        <p class="text-sm text-base-content/60 mb-3">
          Group categories into budget envelopes. Each envelope tracks one spending area with its
          own budgeted and available balance. Enable <strong>Rollover</strong> to carry unspent
          balance forward to the next month.
        </p>
        <EnvelopeManager :groups="groups" />
      </div>
    </section>

    <!-- Budgeting preferences section -->
    <section class="card bg-base-100 shadow">
      <div class="card-body">
        <h2 class="card-title">Budgeting</h2>
        <p class="text-sm text-base-content/60 mb-4">
          Choose how income is planned each month.
        </p>

        <div class="flex flex-col gap-3">
          <label
            class="flex items-start gap-3 p-3 rounded-lg border cursor-pointer transition-colors"
            :class="budgetMode === 'n1' ? 'border-primary bg-primary/5' : 'border-base-300 hover:bg-base-200/50'"
            @click="setBudgetMode('n1')"
          >
            <input
              type="radio"
              name="budget_mode"
              value="n1"
              class="radio radio-sm radio-primary mt-0.5"
              :checked="budgetMode === 'n1'"
              @change="setBudgetMode('n1')"
            />
            <div>
              <div class="font-medium">N+1 <span class="badge badge-xs badge-ghost">défaut</span></div>
              <div class="text-sm text-base-content/60">
                Le salaire de février est budgétisé en mars. Aucune transaction
                virtuelle n’est créée — la transaction réelle existante est
                simplement affectée au mois suivant.
              </div>
            </div>
          </label>

          <label
            class="flex items-start gap-3 p-3 rounded-lg border cursor-pointer transition-colors"
            :class="budgetMode === 'n' ? 'border-primary bg-primary/5' : 'border-base-300 hover:bg-base-200/50'"
            @click="setBudgetMode('n')"
          >
            <input
              type="radio"
              name="budget_mode"
              value="n"
              class="radio radio-sm radio-primary mt-0.5"
              :checked="budgetMode === 'n'"
              @change="setBudgetMode('n')"
            />
            <div>
              <div class="font-medium">Prévisionnel</div>
              <div class="text-sm text-base-content/60">
                Le salaire de mars est budgétisé en mars avant de l’avoir reçu.
                Une transaction virtuelle est créée pour planifier les dépenses
                à l’avance.
              </div>
            </div>
          </label>
        </div>

        <p v-if="prefError" class="text-error text-sm mt-2">{{ prefError }}</p>
      </div>
    </section>
  </div>
</template>
