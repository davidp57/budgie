/**
 * useNearbyPlaces — Composable for detecting nearby shops/places.
 *
 * Uses the browser Geolocation API to get the user's position,
 * then queries the Overpass API (OpenStreetMap) for named
 * shops and amenities within a configurable radius.
 */
import { ref, computed } from 'vue'

export interface NearbyPlace {
  id: number
  name: string
  type: string // e.g. "supermarket", "bakery", "restaurant"
  emoji: string
  distance: number // metres
}

// ── Emoji mapping by OSM tag ──────────────────────────────────────
const AMENITY_EMOJIS: Record<string, string> = {
  restaurant: '🍽️',
  fast_food: '🍔',
  cafe: '☕',
  bar: '🍺',
  pub: '🍺',
  pharmacy: '💊',
  fuel: '⛽',
  bank: '🏦',
  post_office: '📮',
  dentist: '🦷',
  doctors: '🏥',
  hospital: '🏥',
  cinema: '🎬',
  parking: '🅿️',
}

const SHOP_EMOJIS: Record<string, string> = {
  supermarket: '🛒',
  convenience: '🏪',
  bakery: '🥖',
  butcher: '🥩',
  greengrocer: '🥬',
  pastry: '🧁',
  clothes: '👕',
  shoes: '👟',
  electronics: '📱',
  hardware: '🔧',
  florist: '💐',
  hairdresser: '💇',
  beauty: '💅',
  optician: '👓',
  books: '📚',
  toys: '🧸',
  pet: '🐾',
  alcohol: '🍷',
  tobacco: '🚬',
  car_repair: '🔧',
  bicycle: '🚲',
  sports: '⚽',
  kiosk: '📰',
  deli: '🧀',
  seafood: '🐟',
  confectionery: '🍬',
  chemist: '🧴',
  stationery: '📝',
  doityourself: '🔨',
  garden_centre: '🌱',
  furniture: '🪑',
  jewelry: '💍',
}

function getPlaceEmoji(tags: Record<string, string>): string {
  if (tags.shop && SHOP_EMOJIS[tags.shop]) return SHOP_EMOJIS[tags.shop]!
  if (tags.amenity && AMENITY_EMOJIS[tags.amenity]) return AMENITY_EMOJIS[tags.amenity]!
  if (tags.shop) return '🏪'
  if (tags.amenity) return '📍'
  return '📍'
}

function getPlaceType(tags: Record<string, string>): string {
  return tags.shop || tags.amenity || 'place'
}

// ── Haversine distance (metres) ───────────────────────────────────
function haversineMetres(
  lat1: number, lon1: number,
  lat2: number, lon2: number,
): number {
  const R = 6_371_000
  const toRad = (d: number) => (d * Math.PI) / 180
  const dLat = toRad(lat2 - lat1)
  const dLon = toRad(lon2 - lon1)
  const a =
    Math.sin(dLat / 2) ** 2 +
    Math.cos(toRad(lat1)) * Math.cos(toRad(lat2)) * Math.sin(dLon / 2) ** 2
  return R * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a))
}

// ── Overpass query builder ────────────────────────────────────────
function buildOverpassQuery(lat: number, lon: number, radius: number): string {
  return `[out:json][timeout:5];(
  node["name"]["shop"](around:${radius},${lat},${lon});
  node["name"]["amenity"~"restaurant|fast_food|cafe|bar|pub|pharmacy|fuel|bank|post_office|dentist|doctors|cinema"](around:${radius},${lat},${lon});
);out body;`
}

const OVERPASS_URL = 'https://overpass-api.de/api/interpreter'

// ── Composable ────────────────────────────────────────────────────
export function useNearbyPlaces(radius = 500) {
  const places = ref<NearbyPlace[]>([])
  const loading = ref(false)
  const error = ref<string | null>(null)
  const permissionDenied = ref(false)

  /** Readable distance label */
  const formatDistance = (metres: number): string =>
    metres < 1000 ? `${Math.round(metres)} m` : `${(metres / 1000).toFixed(1)} km`

  const hasPlaces = computed(() => places.value.length > 0)

  /** Trigger geolocation + Overpass lookup */
  async function detect(): Promise<void> {
    if (!navigator.geolocation) {
      error.value = 'Géolocalisation non supportée'
      return
    }

    loading.value = true
    error.value = null

    try {
      const position = await new Promise<GeolocationPosition>((resolve, reject) => {
        navigator.geolocation.getCurrentPosition(resolve, reject, {
          enableHighAccuracy: true,
          timeout: 10_000,
          maximumAge: 60_000, // cache 1 min
        })
      })

      const { latitude, longitude } = position.coords
      const query = buildOverpassQuery(latitude, longitude, radius)

      const response = await fetch(OVERPASS_URL, {
        method: 'POST',
        body: `data=${encodeURIComponent(query)}`,
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      })

      if (!response.ok) {
        error.value = 'Erreur de recherche des lieux'
        return
      }

      const data = (await response.json()) as {
        elements: Array<{
          id: number
          lat: number
          lon: number
          tags: Record<string, string>
        }>
      }

      places.value = data.elements
        .filter((el): el is typeof el & { tags: { name: string } } => Boolean(el.tags?.name))
        .map((el) => ({
          id: el.id,
          name: el.tags.name,
          type: getPlaceType(el.tags),
          emoji: getPlaceEmoji(el.tags),
          distance: haversineMetres(latitude, longitude, el.lat, el.lon),
        }))
        .sort((a, b) => a.distance - b.distance)
        .slice(0, 15) // top 15 closest
    } catch (err: unknown) {
      const geoErr = err as { code?: number }
      if (geoErr.code === 1) {
        // PERMISSION_DENIED
        permissionDenied.value = true
        error.value = 'Active la localisation dans Réglages > Confidentialité > Services de localisation > Safari'
      } else if (geoErr.code === 2) {
        // POSITION_UNAVAILABLE
        error.value = 'Position indisponible — vérifie que le GPS est activé'
      } else if (geoErr.code === 3) {
        // TIMEOUT
        error.value = 'Délai dépassé — réessaie dans un endroit avec meilleur signal'
      } else {
        error.value = 'Impossible de détecter la position'
      }
    } finally {
      loading.value = false
    }
  }

  return { places, loading, error, permissionDenied, hasPlaces, formatDistance, detect }
}
