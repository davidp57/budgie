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
 *   z-20 Content (text, amounts, calendar, goal bar)
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
  { pastel: '#fca5a5', fill: '#ef4444', fillEnd: '#dc2626' }, // red
  { pastel: '#bae6fd', fill: '#0ea5e9', fillEnd: '#0284c7' }, // sky
  { pastel: '#bef264', fill: '#84cc16', fillEnd: '#65a30d' }, // lime
  { pastel: '#a5f3fc', fill: '#06b6d4', fillEnd: '#0891b2' }, // cyan
  { pastel: '#f0abfc', fill: '#d946ef', fillEnd: '#c026d3' }, // fuchsia
  { pastel: '#fef08a', fill: '#eab308', fillEnd: '#ca8a04' }, // yellow
  { pastel: '#86efac', fill: '#22c55e', fillEnd: '#16a34a' }, // green
]

const props = withDefaults(defineProps<{
  line: EnvelopeLine
  colorIndex?: number
  showMoney?: boolean
  showCalendar?: boolean
  showSubtitle?: boolean
  showGoalBar?: boolean
  /** Force fill to 100% regardless of available/budgeted ratio (use in definition/config screens). */
  fullFill?: boolean
  /** Show the amber expense-count triangle badge. Disable in config/editing screens. */
  showBadge?: boolean
}>(), {
  showMoney: true,
  showCalendar: true,
  showSubtitle: true,
  showGoalBar: true,
  showBadge: true,
})

const emit = defineEmits<{
  tap: [line: EnvelopeLine]
  badgeTap: [line: EnvelopeLine]
}>()

// Pick color from palette based on envelope_id
const colors = computed<CardColors>(() => {
  const idx = props.colorIndex ?? (props.line.envelope_id - 1)
  return COLOR_PALETTE[((idx % COLOR_PALETTE.length) + COLOR_PALETTE.length) % COLOR_PALETTE.length]!
})

const drawerType = computed<EnvelopeType>(() => props.line.envelope_type ?? 'regular')

// Fill % = remaining budget ratio (or 100% in definition/config mode)
const fillPercent = computed(() => {
  if (props.fullFill) return 100
  if (props.line.budgeted === 0) return 0
  const ratio = props.line.available / props.line.budgeted
  return Math.max(0, Math.min(100, Math.round(ratio * 100)))
})

const isOverBudget = computed(() => !props.fullFill && props.line.available < 0)

// Calendar strip: spec says "lumineux = jours restants (gauche), gris = jours passés (droite)"
// So we put remaining days first (bright), then past days (gray).
// The last bright day = today, gets special glow styling.
const calendarDays = computed(() => {
  const now = new Date()
  const day = now.getDate()
  const total = new Date(now.getFullYear(), now.getMonth() + 1, 0).getDate()
  const remaining = total - day
  // Remaining (bright) on left, today marker, past (gray) on right
  return [
    ...Array.from({ length: remaining }, () => 'future' as const),
    'today' as const,
    ...Array.from({ length: day - 1 }, () => 'past' as const),
  ]
})

// Money items: bills €5-€100 + coins €1/€2.
// Stacked "en vrac" inside a dedicated .money-pile container.
type MoneyKind = 'bill' | 'coin'
interface MoneyItem { value: number; label: string; cssClass: string; kind: MoneyKind }

const MONEY_DEFS: MoneyItem[] = [
  { value: 10000, label: '100', cssClass: 'bill-100', kind: 'bill' },
  { value: 5000,  label: '50',  cssClass: 'bill-50',  kind: 'bill' },
  { value: 2000,  label: '20',  cssClass: 'bill-20',  kind: 'bill' },
  { value: 1000,  label: '10',  cssClass: 'bill-10',  kind: 'bill' },
  { value: 500,   label: '5',   cssClass: 'bill-5',   kind: 'bill' },
  { value: 200,   label: '2',   cssClass: 'coin-2',   kind: 'coin' },
  { value: 100,   label: '1',   cssClass: 'coin-1',   kind: 'coin' },
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

// Goal progress for cumulative envelopes with a target
const goalPercent = computed(() => {
  const target = props.line.target_amount
  if (!target || target <= 0) return null
  return Math.max(0, Math.min(100, Math.round((props.line.available / target) * 100)))
})

// Better pseudo-random: xorshift-inspired, much more chaotic distribution
function prng(envelopeId: number, index: number, salt: number): number {
  let h = (envelopeId * 2654435761 + index * 340573321 + salt * 1013904223) >>> 0
  h ^= h >>> 16; h = Math.imul(h, 0x45d9f3b); h ^= h >>> 16
  return (h >>> 0) / 4294967296
}

// Position & rotation for each money item inside the .money-pile container.
// Mockup: bills thrown "en vrac" — chaotic overlapping pile across the full area.
function moneyStyle(index: number): Record<string, string> {
  const bottom = Math.round(prng(props.line.envelope_id, index, 1) * 48)
  const left = Math.round(prng(props.line.envelope_id, index, 2) * 58)
  const rotation = prng(props.line.envelope_id, index, 3) * 40 - 20   // ±20°
  return {
    bottom: `${bottom}px`,
    left: `${left}px`,
    transform: `rotate(${rotation.toFixed(1)}deg)`,
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
  >    <!-- Saturated fill = remaining budget (z-10) -->
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

      <!-- Card body: text left + money pile right (like mockup) -->
      <div class="flex items-end gap-4 mt-3">
        <div class="flex-1">
          <!-- Big amount -->
          <div>
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
        </div>

        <!-- Money pile: relative flex child with isometric perspective (like mockup) -->
        <div
          v-if="props.showMoney && moneyItems.length > 0"
          class="money-pile"
        >
          <div
            v-for="(item, i) in moneyItems"
            :key="i"
            :class="[item.kind === 'coin' ? 'coin' : 'bill', item.cssClass]"
            :style="moneyStyle(i)"
          >{{ item.label }}</div>
        </div>
        <!-- Empty pile: show hole emoji when overspent -->
        <div
          v-else-if="props.showMoney && isOverBudget"
          class="money-pile empty"
        >
          <div class="empty-indicator">🕳️</div>
        </div>
      </div>

      <!-- Calendar strip (regular only) -->
      <!-- Spec: lumineux = jours restants (gauche), today = glow, gris = jours passés (droite) -->
      <div v-if="props.showCalendar && drawerType === 'regular' && line.budgeted > 0" class="flex gap-[2px] mt-3">
        <div
          v-for="(dayType, i) in calendarDays"
          :key="i"
          class="h-[7px] flex-1 rounded-[2px] transition-colors"
          :class="{
            'bg-white/75': dayType === 'future',
            'bg-white/90 shadow-[0_0_4px_rgba(255,255,255,0.5)]': dayType === 'today',
            'bg-white/20': dayType === 'past',
          }"
        />
      </div>

      <!-- Goal bar (cumulative with target_amount) — inside content flow -->
      <div
        v-if="props.showGoalBar && drawerType === 'cumulative' && goalPercent !== null"
        class="flex items-center gap-2 mt-3"
      >
        <div class="flex-1 h-[6px] rounded-full bg-white/15 overflow-hidden">
          <div
            class="h-full rounded-full bg-gradient-to-r from-white/60 to-white/90 transition-all duration-700"
            :style="{ width: `${goalPercent}%` }"
          />
        </div>
        <span class="text-[11px] text-white/55 whitespace-nowrap font-medium">
          {{ formatAmount(line.available) }}/{{ formatAmount(line.target_amount!) }}
        </span>
      </div>
    </div>

    <!-- Expense count badge — diagonal triangle top-right corner (z-30) -->
    <div
      v-if="props.showBadge && line.expense_count > 0"
      class="badge-tri"
      :class="{ 'three-digits': line.expense_count >= 100 }"
      @click.stop="emit('badgeTap', line)"
    >
      <span class="badge-num">{{ line.expense_count }}</span>
    </div>
  </button>
</template>

<style scoped>
/* ══════════════════════════════════════════════════════════ */
/* BILLS — Euro banknotes (Europa series)                        */
/* Real bills grow with denomination; colors match actual notes  */
/* ══════════════════════════════════════════════════════════ */
.bill {
  position: absolute;
  border-radius: 2px;
  font-weight: 800;
  display: flex;
  align-items: flex-end;
  justify-content: flex-start;
  padding: 0 0 1px 4px;
  color: rgba(255, 255, 255, 0.9);
  text-shadow: 0 1px 1px rgba(0, 0, 0, 0.3);
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.3);
  overflow: hidden;
}

/* "€" watermark top-right */
.bill::before {
  content: '€';
  position: absolute;
  top: 2px;
  right: 4px;
  font-size: 8px;
  font-weight: 900;
  opacity: 0.25;
}

/* Holographic band — wide silver stripe on the right (Europa series) */
.bill::after {
  content: '';
  position: absolute;
  top: 0;
  right: 8px;
  width: 7px;
  height: 100%;
  background: linear-gradient(
    180deg,
    rgba(220, 230, 245, 0.30) 0%,
    rgba(255, 255, 255, 0.18) 30%,
    rgba(200, 215, 240, 0.30) 50%,
    rgba(255, 255, 255, 0.12) 70%,
    rgba(210, 225, 245, 0.25) 100%
  );
  border-left: 1px solid rgba(255, 255, 255, 0.15);
  border-right: 1px solid rgba(255, 255, 255, 0.08);
}

/* ── Per-denomination: colors + sizes matching real Europa series ── */

/* €5 — grey / sage green (120×62mm → 44×23px) */
.bill-5 {
  width: 44px;
  height: 23px;
  font-size: 8px;
  background: linear-gradient(160deg, #9aa89c 0%, #7d8d7f 35%, #8a9a8c 70%, #7a8a7c 100%);
  color: #d8e8da;
  border-bottom: 1.5px solid #6a7a6c;
}

/* €10 — red / rose-carmine (127×67mm → 46×25px) */
.bill-10 {
  width: 46px;
  height: 25px;
  font-size: 8px;
  background: linear-gradient(160deg, #d4696a 0%, #c04855 35%, #b84050 70%, #c85060 100%);
  color: #f5dde0;
  border-bottom: 1.5px solid #a03845;
}

/* €20 — blue / azure (133×72mm → 49×26px) */
.bill-20 {
  width: 49px;
  height: 26px;
  font-size: 9px;
  background: linear-gradient(160deg, #5a90d0 0%, #3570b5 35%, #2e65a8 70%, #4080c0 100%);
  color: #d0e0f5;
  border-bottom: 1.5px solid #2558a0;
}

/* €50 — orange / warm amber (140×77mm → 52×28px) */
.bill-50 {
  width: 52px;
  height: 28px;
  font-size: 9px;
  background: linear-gradient(160deg, #e8a050 0%, #d08030 35%, #c87528 70%, #d89040 100%);
  color: #fff2e0;
  border-bottom: 2px solid #b06820;
}

/* €100 — bright green / spring green (147×82mm → 55×30px) */
.bill-100 {
  width: 55px;
  height: 30px;
  font-size: 10px;
  background: linear-gradient(160deg, #60b870 0%, #40a058 35%, #359050 70%, #50a865 100%);
  color: #d8f5e0;
  border-bottom: 2px solid #2e8048;
}

/* ══════════════════════════════════════════════════════════ */
/* COINS — circular with realistic metallic look                 */
/* ══════════════════════════════════════════════════════════ */
.coin {
  position: absolute;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 800;
  text-shadow: 0 1px 1px rgba(0, 0, 0, 0.2);
  box-shadow: 0 2px 3px rgba(0, 0, 0, 0.4), inset 0 1px 0 rgba(255, 255, 255, 0.3);
}

/* €2 coin: silver center, gold rim */
.coin-2 {
  width: 20px;
  height: 20px;
  background: linear-gradient(180deg, #e8e8e8, #b0b0b0);
  border: 2.5px solid #d4a530;
  font-size: 8px;
  color: #555;
}

/* €1 coin: gold center, silver rim */
.coin-1 {
  width: 19px;
  height: 19px;
  background: linear-gradient(180deg, #d4a530, #b8882a);
  border: 2.5px solid #c0c0c0;
  font-size: 8px;
  color: #6b4c1a;
}

/* ══════════════════════════════════════════════════════════ */
/* MONEY PILE — relative flex child with isometric perspective */
/* Exactly like the mockup: position relative, in the flow    */
/* ══════════════════════════════════════════════════════════ */
.money-pile {
  position: relative;
  width: 110px;
  height: 80px;
  flex-shrink: 0;
  transform: perspective(300px) rotateX(35deg) rotateZ(-8deg);
  transform-origin: center bottom;
  filter: drop-shadow(0 4px 8px rgba(0, 0, 0, 0.4));
  pointer-events: none;
}

.money-pile.empty {
  opacity: 0.4;
}

.empty-indicator {
  position: absolute;
  font-size: 32px;
  opacity: 0.6;
  bottom: 16px;
  left: 50%;
  transform: translateX(-50%);
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

/* ── Expense count badge — diagonal triangle top-right ── */
.badge-tri {
  position: absolute;
  top: 0;
  right: 0;
  width: 42px;
  height: 42px;
  background: #f59e0b;
  clip-path: polygon(0 0, 100% 0, 100% 100%);
  z-index: 40;
  cursor: pointer;
}

.badge-tri.three-digits {
  width: 54px;
  height: 54px;
}

.badge-num {
  position: absolute;
  top: 5px;
  right: 4px;
  font-size: 13px;
  font-weight: 800;
  color: white;
  text-shadow: 0 1px 2px rgba(0, 0, 0, 0.3);
  line-height: 1;
}
</style>
