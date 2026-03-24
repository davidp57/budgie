import { createRouter, createWebHistory } from 'vue-router'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/login',
      name: 'login',
      component: () => import('@/views/LoginView.vue'),
      meta: { public: true },
    },
    {
      path: '/setup-encryption',
      name: 'setup-encryption',
      component: () => import('@/views/SetupEncryptionView.vue'),
      meta: { requiresAuth: true },
    },
    {
      path: '/unlock',
      name: 'unlock',
      component: () => import('@/views/UnlockEncryptionView.vue'),
      meta: { requiresAuth: true },
    },
    {
      path: '/',
      name: 'home',
      component: () => import('@/views/HomeView.vue'),
    },
    {
      path: '/budget',
      name: 'budget',
      component: () => import('@/views/BudgetView.vue'),
    },
    {
      path: '/transactions',
      name: 'transactions',
      component: () => import('@/views/TransactionsView.vue'),
    },
    {
      path: '/settings',
      name: 'settings',
      component: () => import('@/views/SettingsView.vue'),
    },
  ],
})

router.beforeEach((to) => {
  const token = localStorage.getItem('access_token')

  // Unauthenticated → login
  if (!to.meta.public && !token) {
    return { name: 'login' }
  }

  if (token) {
    const needsSetup = localStorage.getItem('needs_encryption_setup') === 'true'
    const isEncrypted = localStorage.getItem('is_encrypted') === 'true'
    const isEncryptionRoute =
      to.name === 'setup-encryption' || to.name === 'unlock' || to.name === 'login'

    // First-time encryption setup required
    if (needsSetup && !isEncryptionRoute) {
      return { name: 'setup-encryption' }
    }

    // Returning user with encryption, not yet unlocked this session
    if (isEncrypted && !needsSetup && !isEncryptionRoute) {
      // Check in-memory store via sessionStorage flag set by auth store
      const unlocked = sessionStorage.getItem('encryption_unlocked') === 'true'
      if (!unlocked) {
        return { name: 'unlock' }
      }
    }
  }
})

export default router
