<script setup lang="ts">
import axios from 'axios'
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

// ~256 common, easy-to-type English words for passphrase generation
const WORDS = [
  'apple','arrow','atlas','badge','bench','birch','black','blade','blank','bloom',
  'board','boots','brain','brave','bread','brick','bridge','brief','bright','broad',
  'brook','brown','brush','cabin','camel','candy','cargo','cedar','chair','chalk',
  'charm','chase','chest','chief','child','chord','civic','civil','claim','clamp',
  'clasp','clean','clear','cliff','cloak','close','cloud','clover','coast','cobalt',
  'coral','craft','crane','crate','creek','crisp','cross','crown','crush','curve',
  'daisy','dance','diner','drift','drive','drums','dusky','early','earth','ember',
  'empty','fence','fern','field','finch','first','flame','flask','fleet','float',
  'floor','flute','focus','forge','forth','forum','frame','fresh','front','frost',
  'fruit','glass','globe','gloom','gloss','glyph','grace','grain','grand','grant',
  'grape','grasp','grass','gravel','green','grove','guess','guest','guide','guild',
  'habit','happy','hatch','hazel','hedge','helix','herbs','heron','hills','honey',
  'horse','hound','house','hulk','hunch','ideal','inert','inner','input','ivory',
  'jaunt','jewel','joust','judge','jumbo','karma','kayak','knack','kneel','knife',
  'label','lance','latch','layer','leash','ledge','lemon','lever','light','lilac',
  'limit','liner','logic','lotus','lunar','lusty','maple','march','marsh','match',
  'merit','metal','metro','might','mills','mirth','model','money','moose','mossy',
  'motto','mound','mount','mourn','music','names','naval','nerve','noble','north',
  'notch','novel','nurse','nymph','oaken','ocean','olive','onion','orbit','otter',
  'outer','ovoid','oxide','ozone','paint','panel','paper','party','pasta','peach',
  'pearl','pedal','penny','perch','petal','phase','piano','pilot','pinch','pixel',
  'plain','plane','plant','plate','plaza','plumb','plume','polar','polka',
  'poppy','pouch','power','press','pride','prime','prize','probe','prune','pulse',
  'quail','quart','queen','quest','queue','quiet','quota','quill','radar','radix',
  'rally','ranch','range','rapid','raven','reach','realm','resin','ridge','risky',
  'rivet','robin','rocky','roman','roost','rouge','rough','round','royal','rugby',
  'ruler','runic','rusty','safer','satin','scale','scene','scout','screw','sedan',
  'shade','shaft','shale','shark','sharp','shelf','shell','shift','shine','shire',
  'shirt','shore','short','shout','shrub','sigma','sight','silky','sinew',
  'sixth','skimp','slate','sleek','sleet','slick','slope','sloth','smart',
  'smoke','snail','snake','solar','solid','space','spark','speed','spell','spice',
  'spine','spoke','spoon','sport','spray','squad','stack','staff','stage','stain',
  'staple','stark','start','steel','steep','stern','stick','still','stock','stoic',
  'stone','storm','story','stout','stove','strap','straw','strip','strut','study',
  'sugar','sunny','super','surge','swamp','swarm','sweet','swept','swift','swirl',
  'sword','table','taunt','tawny','tempo','tepid','terms','tiger','tidal','tiled',
  'timer','titan','toast','token','tonic','torch','tower','track','trait','tramp',
  'tread','trend','trial','tribe','trick','trout','truck','trump','trunk','truth',
  'tulip','tuner','tunic','tutor','twirl','twist','ultra','umbra','uncle','under',
  'unity','upper','urban','usage','usher','vague','valid','valor','valve','vault',
  'vigor','viola','viral','visor','vista','vital','vivid','vocal','voice','voter',
  'waltz','watch','water','weave','wedge','wheat','wheel','where','which','white',
  'whisk','width','willow','witty','world','worth','wrath','writhe','yacht','yearn',
]

function generatePassphrase(): string {
  const array = new Uint32Array(4)
  crypto.getRandomValues(array)
  return Array.from(array)
    .map((n) => WORDS[n % WORDS.length])
    .join('-')
}

function extractError(err: unknown, fallback: string): string {
  if (axios.isAxiosError(err)) {
    const detail = err.response?.data?.detail
    if (typeof detail === 'string') return detail
  }
  return fallback
}

const auth = useAuthStore()
const router = useRouter()

const passphrase = ref('')
const passphraseConfirm = ref('')
const showPassphrase = ref(true)
const copied = ref(false)
const error = ref('')
const loading = ref(false)

function regenerate(): void {
  const p = generatePassphrase()
  passphrase.value = p
  passphraseConfirm.value = p
  copied.value = false
}

async function copyToClipboard(): Promise<void> {
  try {
    await navigator.clipboard.writeText(passphrase.value)
    copied.value = true
    setTimeout(() => { copied.value = false }, 2000)
  } catch {
    error.value = 'Could not copy to clipboard. Please copy the passphrase manually.'
  }
}

onMounted(() => {
  regenerate()
})

const setupDone = ref(false)
const savedPassphrase = ref('')
const setupDate = ref('')

async function submit(): Promise<void> {
  error.value = ''
  if (passphrase.value !== passphraseConfirm.value) {
    error.value = 'Passphrases do not match.'
    return
  }
  loading.value = true
  try {
    await auth.setupEncryption(passphrase.value)
    savedPassphrase.value = passphrase.value
    setupDate.value = new Date().toLocaleString()
    setupDone.value = true
  } catch (err) {
    error.value = extractError(err, 'Failed to set up encryption. Please try again.')
  } finally {
    loading.value = false
  }
}

function printRecovery(): void {
  window.print()
}

async function done(): Promise<void> {
  await router.push('/')
}
</script>

<template>
  <!-- ── Recovery sheet (shown after successful setup) ── -->
  <div v-if="setupDone" class="no-print min-h-screen bg-base-200 flex items-center justify-center p-4">
    <div class="card bg-base-100 w-full max-w-md shadow-xl">
      <div class="card-body gap-4">
        <h1 class="card-title text-xl justify-center">🔐 Save your recovery sheet</h1>
        <div class="alert alert-warning text-sm">
          <span>⚠️ This passphrase is shown <strong>only once</strong>. Print or save the recovery sheet now before continuing.</span>
        </div>

        <!-- Recovery sheet preview -->
        <div id="recovery-sheet" class="border-2 border-base-300 rounded-box p-5 flex flex-col gap-3 text-sm print:border-0 print:p-0">
          <div class="flex items-center justify-between border-b border-base-300 pb-3">
            <span class="text-lg font-bold">🐦 Budgie — Encryption Recovery Sheet</span>
          </div>
          <div class="flex flex-col gap-1">
            <span class="text-base-content/60 text-xs uppercase tracking-wide">Account</span>
            <span class="font-semibold">{{ auth.username }}</span>
          </div>
          <div class="flex flex-col gap-1">
            <span class="text-base-content/60 text-xs uppercase tracking-wide">Date</span>
            <span>{{ setupDate }}</span>
          </div>
          <div class="flex flex-col gap-2">
            <span class="text-base-content/60 text-xs uppercase tracking-wide">Encryption passphrase</span>
            <div class="bg-base-200 rounded-lg p-4 print:bg-gray-100">
              <code class="text-xl font-mono font-bold tracking-wider break-all select-all">{{ savedPassphrase }}</code>
            </div>
          </div>
          <div class="text-xs text-base-content/60 border-t border-base-300 pt-3 flex flex-col gap-1">
            <p>⚠️ Store this document in a secure physical location (e.g. safe, locked drawer).</p>
            <p>🔑 You will need this passphrase every time you log in to Budgie.</p>
            <p>🚫 If you lose this passphrase, your encrypted data cannot be recovered.</p>
          </div>
        </div>

        <div class="flex flex-col gap-2">
          <button class="btn btn-primary gap-2" @click="printRecovery">
            🖨️ Print / Save as PDF
          </button>
          <button class="btn btn-ghost" @click="done">
            I've saved it — Continue →
          </button>
        </div>
      </div>
    </div>
  </div>

  <!-- ── Setup form ── -->
  <div v-else class="min-h-screen bg-base-200 flex items-center justify-center p-4">
    <div class="card bg-base-100 w-full max-w-sm shadow-xl">
      <div class="card-body">
        <h1 class="card-title text-2xl justify-center mb-1">🔐 Encryption Setup</h1>
        <p class="text-center text-base-content/60 text-sm mb-4">
          Your data will be encrypted with this passphrase. Store it safely — it
          cannot be recovered if lost.
        </p>

        <form @submit.prevent="submit" class="flex flex-col gap-3">
          <!-- Suggested passphrase banner -->
          <div class="bg-base-200 rounded-box p-3 flex flex-col gap-2">
            <div class="flex items-center justify-between">
              <span class="text-xs font-semibold text-base-content/60 uppercase tracking-wide">Suggested passphrase</span>
              <button type="button" class="btn btn-ghost btn-xs gap-1" @click="regenerate" title="Generate a new one">
                🔄 New
              </button>
            </div>
            <div class="flex items-center gap-2">
              <code class="flex-1 text-sm font-mono break-all select-all bg-base-100 rounded p-2">{{ passphrase }}</code>
              <button
                type="button"
                class="btn btn-ghost btn-sm"
                :title="copied ? 'Copied!' : 'Copy to clipboard'"
                @click="copyToClipboard"
              >
                {{ copied ? '✅' : '📋' }}
              </button>
            </div>
            <p class="text-xs text-base-content/50">You can use it as-is or type your own below.</p>
          </div>

          <label class="form-control">
            <div class="label">
              <span class="label-text">Passphrase</span>
              <span class="label-text-alt text-base-content/50">min. 8 characters</span>
            </div>
            <div class="relative">
              <input
                v-model="passphrase"
                :type="showPassphrase ? 'text' : 'password'"
                class="input input-bordered w-full pr-10 font-mono"
                autocomplete="new-password"
                minlength="8"
                required
              />
              <button
                type="button"
                class="absolute right-2 top-1/2 -translate-y-1/2 btn btn-ghost btn-xs"
                @click="showPassphrase = !showPassphrase"
                :title="showPassphrase ? 'Hide' : 'Show'"
              >
                {{ showPassphrase ? '🙈' : '👁️' }}
              </button>
            </div>
          </label>

          <label class="form-control">
            <div class="label"><span class="label-text">Confirm passphrase</span></div>
            <input
              v-model="passphraseConfirm"
              :type="showPassphrase ? 'text' : 'password'"
              class="input input-bordered font-mono"
              autocomplete="new-password"
              required
            />
          </label>

          <div v-if="error" class="alert alert-error text-sm py-2">{{ error }}</div>

          <button type="submit" class="btn btn-primary mt-2" :disabled="loading">
            <span v-if="loading" class="loading loading-spinner loading-sm"></span>
            Encrypt my data
          </button>
        </form>
      </div>
    </div>
  </div>
</template>

<style>
@media print {
  body * {
    visibility: hidden;
  }
  #recovery-sheet,
  #recovery-sheet * {
    visibility: visible;
  }
  #recovery-sheet {
    position: fixed;
    top: 0;
    left: 0;
    width: 100%;
    padding: 2cm;
    font-family: serif;
    background: white;
    color: black;
  }
}
</style>
