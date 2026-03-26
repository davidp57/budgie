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
import type { Account, CategoryGroupWithCategories } from '@/api/types'
import { useAuthStore } from '@/stores/auth'
import { useRouter } from 'vue-router'
import { createPasskey, isWebAuthnSupported } from '@/composables/useWebAuthn'
import { usePinStorage } from '@/composables/usePinStorage'
import { useTheme } from '@/composables/useTheme'

const auth = useAuthStore()
const router = useRouter()
const pinStorage = usePinStorage()
const { theme, toggle: toggleTheme } = useTheme()

function logout(): void {
  auth.logout()
  router.push({ name: 'login' })
}

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

// ── Passkey management ────────────────────────────────────────────────────────
const webAuthnSupported = isWebAuthnSupported()
const pinAvailable = typeof window !== 'undefined' && !!window.crypto?.subtle
const passkeyError = ref('')
const passkeyLoading = ref(false)
const newPasskeyName = ref('')
const pinHasStored = ref(false)

async function registerPasskey(): Promise<void> {
  passkeyError.value = ''
  passkeyLoading.value = true
  try {
    const options = await auth.webauthnRegisterBegin()
    const credential = await createPasskey(options)
    await auth.webauthnRegisterComplete(credential, newPasskeyName.value || undefined)
    newPasskeyName.value = ''
  } catch (err: unknown) {
    passkeyError.value =
      err instanceof Error ? err.message : 'Failed to register passkey.'
  } finally {
    passkeyLoading.value = false
  }
}

async function removePasskey(id: number): Promise<void> {
  passkeyError.value = ''
  try {
    await auth.deleteWebAuthnCredential(id)
  } catch {
    passkeyError.value = 'Failed to delete passkey.'
  }
}

async function clearPin(): Promise<void> {
  await pinStorage.clearStoredPassphrase()
  pinHasStored.value = false
}

onMounted(async () => {
  try {
    const prefs = await getPreferences()
    budgetMode.value = prefs.budget_mode
    await loadAll()
    await auth.loadWebAuthnCredentials()
    pinHasStored.value = await pinStorage.hasStoredPassphrase()
  } catch {
    // 401 errors are handled by the client interceptor (redirect to login)
  }
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

    <!-- Theme section -->
    <section class="card bg-base-100 shadow">
      <div class="card-body">
        <h2 class="card-title">Apparence</h2>
        <div class="flex items-center gap-4">
          <span class="text-sm">☀️ Clair</span>
          <input
            type="checkbox"
            class="toggle toggle-primary"
            :checked="theme === 'dark'"
            @change="toggleTheme"
          />
          <span class="text-sm">🌙 Sombre</span>
        </div>
      </div>
    </section>

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

    <!-- Passkeys & PIN ──────────────────────────────────────────── -->
    <section v-if="webAuthnSupported" class="card bg-base-100 shadow">
      <div class="card-body gap-4">
        <h2 class="card-title text-lg">🔑 Passkeys & PIN</h2>

        <!-- Registered passkeys list -->
        <div v-if="auth.webauthnCredentials.length > 0" class="flex flex-col gap-2">
          <div
            v-for="cred in auth.webauthnCredentials"
            :key="cred.id"
            class="flex items-center justify-between bg-base-200 rounded-box px-4 py-2"
          >
            <div>
              <p class="font-medium">{{ cred.name ?? 'Passkey' }}</p>
              <p class="text-xs text-base-content/50">Added {{ new Date(cred.created_at).toLocaleDateString() }}</p>
            </div>
            <button class="btn btn-ghost btn-sm text-error" @click="removePasskey(cred.id)">
              🗑
            </button>
          </div>
        </div>
        <p v-else class="text-base-content/50 text-sm">No passkeys registered on this account.</p>

        <!-- Register new passkey -->
        <div class="flex gap-2">
          <input
            v-model="newPasskeyName"
            type="text"
            placeholder="Passkey name (e.g. iPhone 15)"
            class="input input-bordered input-sm flex-1"
            maxlength="50"
          />
          <button
            class="btn btn-outline btn-sm gap-1"
            :disabled="passkeyLoading"
            @click="registerPasskey"
          >
            <span v-if="passkeyLoading" class="loading loading-spinner loading-xs"></span>
            + Register Passkey
          </button>
        </div>

        <p v-if="passkeyError" class="text-error text-sm">{{ passkeyError }}</p>

        <!-- PIN management -->
        <div class="divider text-xs">PIN</div>
        <template v-if="pinAvailable">
          <div v-if="pinHasStored" class="flex items-center justify-between">
            <p class="text-sm">Your passphrase is saved on this device with a PIN.</p>
            <button class="btn btn-ghost btn-sm text-error" @click="clearPin">Remove</button>
          </div>
          <p v-else class="text-base-content/50 text-sm">
            No PIN set up. Unlock your encryption with your passphrase to be offered a PIN.
          </p>
        </template>
        <p v-else class="text-base-content/50 text-sm">
          ⚠️ PIN requires HTTPS. Connect securely to use this feature.
        </p>
      </div>
    </section>

    <!-- Logout (visible on mobile where sidebar is hidden) -->
    <section class="card bg-base-100 shadow lg:hidden">
      <div class="card-body">
        <button class="btn btn-outline btn-error w-full gap-2" @click="logout">
          <svg xmlns="http://www.w3.org/2000/svg" class="size-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" />
          </svg>
          Déconnexion
        </button>
      </div>
    </section>
  </div>
</template>
