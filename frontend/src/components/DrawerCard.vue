<script setup lang="ts">
/**
 * DrawerCard — Visual budget drawer card component.
 *
 * Spec (validated mockup):
 * - Gradient card with scattered banknotes in "perspective isométrique"
 * - Fill bicolore: coloré = reste (from left), pastel bg = dépensé (right)
 * - Regular: fill starts full, shrinks as budget is spent
 * - Cumulative: fill grows left-to-right + goal bar
 * - Reserve: full fill, no periodic allocation indicators
 * - Calendar strip (regular): bright = remaining (LEFT), gray = past (RIGHT)
 *
 * Layering (bottom → top):
 *   z-0  Pastel gradient background (= "spent" zone)
 *   z-5  Money pile: bills (€5-€100) + coins (€1-€2), stacked en vrac, isometric
 *   z-10 Semi-transparent saturated fill (= remaining budget, ~80% opacity)
 *   z-[15] Goal bar
 *   z-20 Content (text, amounts, calendar)
 *   z-30 Inner shadow pseudo-element
 *
 * Banknotes form a pile on the RIGHT side of the card.
 * The fill is semi-transparent so banknotes peek through everywhere.
 */

import { computed } from 'vue'
import type { EnvelopeLine, EnvelopeType } from '@/api/types'
import { formatAmount } from '@/api/types'

// ── Color palette ────────────────────────────────────────────────
interface CardColors {
  pastel: string // light bg (visible in "spent" zone)
  fill: string   // saturated fill (remaining budget)
  fillEnd: string // gradient end for depth
}

const COLOR_PALETTE: CardColors[] = [
  { pastel: '#6ee7b7', fill: '#059669', fillEnd: '#0d9488' }, // emerald
  { pastel: '#a5b4fc', fill: '#6366f1', fillEnd: '#4f46e5' }, // indigo
  { pastel: '#fdba74', fill: '#ea580c', fillEnd: '#dc2626' }, // orange
  { pastel: '#93c5fd', fill: '#3b82f6', fillEnd: '#2563eb' }, // blue
  { pastel: '#f9a8d4', fill: '#db2777', fillEnd: '#be185d' }, // pink
  { pastel: '#fcd34d', fill: '#d97706', fillEnd: '#b45309' }, // amber
  { pastel: '#c4b5fd', fill: '#8b5cf6', fillEnd: '#7c3aed' }, // violet
  { pastel: '#5eead4', fill: '#14b8a6', fillEnd: '#0d9488' }, // teal
]

const props = withDefaults(defineProps<{
  line: EnvelopeLine
  colorIndex?: number
  showMoney?: boolean
  showCalendar?: boolean
  showSubtitle?: boolean
}>(), {
  showMoney: true,
  showCalendar: true,
  showSubtitle: true,
})

const emit = defineEmits<{
  tap: [line: EnvelopeLine]
}>()

// Pick color from palette based on envelope_id
const colors = computed<CardColors>(() => {
  const idx = props.colorIndex ?? (props.line.envelope_id - 1)
  return COLOR_PALETTE[((idx % COLOR_PALETTE.length) + COLOR_PALETTE.length) % COLOR_PALETTE.length]!
})

const drawerType = computed<EnvelopeType>(() => props.line.envelope_type ?? 'regular')

// Fill % = remaining budget ratio
const fillPercent = computed(() => {
  if (props.line.budgeted === 0) return 0
  const ratio = props.line.available / props.line.budgeted
  return Math.max(0, Math.min(100, Math.round(ratio * 100)))
})

const isOverBudget = computed(() => props.line.available < 0)

// Calendar strip: spec says "lumineux = jours restants (gauche), gris = jours passés (droite)"
// So we put remaining days first (bright), then past days (gray).
const calendarDays = computed(() => {
  const now = new Date()
  const day = now.getDate()
  const total = new Date(now.getFullYear(), now.getMonth() + 1, 0).getDate()
  const remaining = total - day
  const past = day
  // Remaining (bright) on left, past (gray) on right
  return [
    ...Array.from({ length: remaining }, () => true),
    ...Array.from({ length: past }, () => false),
  ]
})

// Money items: bills €5-€100 + coins €1/€2.
// Stacked "en vrac" on the right, isometric perspective.
type MoneyKind = 'bill' | 'coin'
interface MoneyItem { value: number; label: string; color: string; kind: MoneyKind }

const MONEY_DEFS: MoneyItem[] = [
  { value: 10000, label: '100',  color: '#6db86a', kind: 'bill' },  // green
  { value: 5000,  label: '50',   color: '#e89030', kind: 'bill' },  // orange
  { value: 2000,  label: '20',   color: '#4da6d8', kind: 'bill' },  // blue
  { value: 1000,  label: '10',   color: '#e87080', kind: 'bill' },  // pink/red
  { value: 500,   label: '5',    color: '#9a9a9a', kind: 'bill' },  // grey
  { value: 200,   label: '2',    color: '#c0a860', kind: 'coin' },  // gold rim
  { value: 100,   label: '1',    color: '#b8b8b8', kind: 'coin' },  // silver
]

const moneyItems = computed(() => {
  if (props.line.available <= 0) return []
  const items: MoneyItem[] = []
  // Greedy decomposition: break the available amount into real denominations
  let remaining = props.line.available  // in centimes
  for (const def of MONEY_DEFS) {
    while (remaining >= def.value && items.length < 8) {
      items.push(def)
      remaining -= def.value
    }
    if (items.length >= 8) break
  }
  return items
})

// Pseudo-random helper: deterministic per envelope + index
function prng(envelopeId: number, index: number, salt: number): number {
  return ((envelopeId * 71 + index * 37 + salt * 13) % 997) / 997
}

// Position & rotation for each money item in the pile
function moneyStyle(index: number, item: MoneyItem): Record<string, string> {
  const r1 = prng(props.line.envelope_id, index, 1)
  const r2 = prng(props.line.envelope_id, index, 2)
  const r3 = prng(props.line.envelope_id, index, 3)
  // Pile in bottom-right corner, flush against right edge
  const x = 62 + r1 * 30                    // 62-92%
  const y = 35 + r2 * 50                    // 35-85%
  const rotation = (r3 * 44) - 22           // ±22°
  return {
    transform: `perspective(300px) rotateX(12deg) rotateY(-8deg) rotate(${rotation.toFixed(1)}deg)`,
    left: `${x.toFixed(1)}%`,
    top: `${y.toFixed(1)}%`,
    backgroundColor: item.color,
  }
}
</script>

<template>
  <button
    class="drawer-card relative overflow-hidden rounded-2xl w-full text-left
           transition-transform active:scale-[0.97]"
    :style="{
      background: `linear-gradient(145deg, ${colors.pastel}, ${colors.pastel}e0)`,
      boxShadow: `0 2px 8px rgba(0,0,0,0.1)`,
    }"
    @click="emit('tap', line)"
  >
    <!-- Money pile: bills + coins stacked on the right (z-5) -->
    <div
      v-for="(item, i) in (props.showMoney ? moneyItems : [])"
      :key="i"
      :class="item.kind === 'coin' ? 'coin' : 'bill'"
      :style="moneyStyle(i, item)"
    >
      <span :class="item.kind === 'coin' ? 'coin-value' : 'bill-value'">{{ item.label }}</span>
    </div>

    <!-- Saturated fill = remaining budget (z-10) -->
    <div class="absolute inset-0 z-10 pointer-events-none">
      <!-- Regular / Cumulative: fill from left -->
      <div
        v-if="drawerType !== 'reserve'"
        class="absolute inset-y-0 left-0 transition-all duration-700 ease-out rounded-l-2xl"
        :class="{ 'rounded-r-2xl': fillPercent >= 100 }"
        :style="{
          width: `${fillPercent}%`,
          background: isOverBudget
            ? 'linear-gradient(135deg, rgba(239,68,68,0.88), rgba(220,38,38,0.88))'
            : `linear-gradient(135deg, ${colors.fill}e0, ${colors.fillEnd}e0)`,
        }"
      />
      <!-- Reserve: full solid fill -->
      <div
        v-else
        class="absolute inset-0 rounded-2xl"
        :style="{ background: `linear-gradient(135deg, ${colors.fill}e0, ${colors.fillEnd}e0)` }"
      />
    </div>

    <!-- Goal bar (cumulative only) — thin vertical line at target -->
    <div
      v-if="drawerType === 'cumulative' && line.budgeted > 0"
      class="absolute top-1 bottom-1 w-0.5 bg-white/50 pointer-events-none z-[15]"
      style="left: 100%"
    >
      <div class="absolute -top-0.5 -left-1 text-[8px] text-white/70 font-bold whitespace-nowrap">
        🎯
      </div>
    </div>

    <!-- Content (z-20) -->
    <div class="relative z-20 flex flex-col justify-between p-4 min-h-[150px] text-white">
      <!-- Header: emoji + name + type badge + actions -->
      <div class="flex items-center gap-2.5">
        <slot name="emoji">
          <span class="text-3xl drop-shadow-md">{{ line.emoji || '📦' }}</span>
        </slot>
        <slot name="name">
          <span class="font-bold text-base tracking-wide drop-shadow-sm">
            {{ line.envelope_name }}
          </span>
        </slot>
        <span
          v-if="drawerType === 'cumulative'"
          class="ml-auto text-[10px] uppercase tracking-widest bg-white/20 px-2 py-0.5 rounded-full backdrop-blur-sm"
        >cumulatif</span>
        <span
          v-else-if="drawerType === 'reserve'"
          class="ml-auto text-[10px] uppercase tracking-widest bg-white/20 px-2 py-0.5 rounded-full backdrop-blur-sm"
        >réserve</span>
        <slot name="actions" />
      </div>

      <!-- Big amount -->
      <div class="mt-3">
        <slot name="amount">
          <span
            class="text-[42px] leading-none font-extrabold tabular-nums tracking-tight drop-shadow-lg"
            :class="isOverBudget ? 'text-red-200' : ''"
          >{{ formatAmount(line.available) }}</span>
        </slot>
      </div>

      <!-- Budget info -->
      <div v-if="props.showSubtitle" class="text-sm text-white/80 mt-1.5 drop-shadow-sm font-medium">
        <template v-if="drawerType !== 'reserve'">
          {{ formatAmount(Math.abs(line.activity)) }} dépensé sur {{ formatAmount(line.budgeted) }}
        </template>
        <template v-else>
          {{ formatAmount(Math.abs(line.activity)) }} dépensé
        </template>
      </div>

      <!-- Calendar strip (regular only) -->
      <!-- Spec: lumineux = jours restants (gauche), gris = jours passés (droite) -->
      <div v-if="props.showCalendar && drawerType === 'regular' && line.budgeted > 0" class="flex gap-[2px] mt-3">
        <div
          v-for="(isBright, i) in calendarDays"
          :key="i"
          class="h-[7px] flex-1 rounded-[2px] transition-colors"
          :class="isBright ? 'bg-white/75' : 'bg-white/20'"
        />
      </div>
    </div>
  </button>
</template>

<style scoped>
/* ── Bills: euro banknote rectangles ── */
.bill {
  position: absolute;
  width: 72px;
  height: 38px;
  border-radius: 4px;
  opacity: 0.9;
  pointer-events: none;
  display: flex;
  align-items: center;
  justify-content: center;
  border: 1.5px solid rgba(255, 255, 255, 0.6);
  box-shadow:
    1px 2px 6px rgba(0, 0, 0, 0.3),
    inset 0 1px 0 rgba(255, 255, 255, 0.3);
  z-index: 15;
}

.bill-value {
  font-size: 16px;
  font-weight: 900;
  color: rgba(255, 255, 255, 0.95);
  text-shadow: 0 1px 3px rgba(0, 0, 0, 0.5);
}

/* Euro symbol after bill value */
.bill-value::after {
  content: '€';
  font-size: 10px;
  margin-left: 1px;
  opacity: 0.7;
}

/* ── Coins: circular with metallic look ── */
.coin {
  position: absolute;
  width: 30px;
  height: 30px;
  border-radius: 50%;
  opacity: 0.9;
  pointer-events: none;
  display: flex;
  align-items: center;
  justify-content: center;
  border: 2px solid rgba(255, 255, 255, 0.5);
  box-shadow:
    1px 2px 5px rgba(0, 0, 0, 0.35),
    inset 0 1px 2px rgba(255, 255, 255, 0.4),
    inset 0 -1px 2px rgba(0, 0, 0, 0.15);
  z-index: 15;
}

.coin-value {
  font-size: 12px;
  font-weight: 900;
  color: rgba(255, 255, 255, 0.95);
  text-shadow: 0 1px 2px rgba(0, 0, 0, 0.4);
}

.coin-value::after {
  content: '€';
  font-size: 8px;
  margin-left: 0.5px;
  opacity: 0.7;
}

/* Inner shadow + glossy highlight for depth */
.drawer-card::after {
  content: '';
  position: absolute;
  inset: 0;
  border-radius: inherit;
  box-shadow:
    inset 0 1px 0 rgba(255, 255, 255, 0.25),
    inset 0 -2px 8px rgba(0, 0, 0, 0.08);
  pointer-events: none;
  z-index: 30;
}
</style>
