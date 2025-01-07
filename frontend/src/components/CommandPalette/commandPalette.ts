import { ref } from 'vue'

export const show = ref(false)

export function showCommandPalette() {
  show.value = true
}

export function hideCommandPalette() {
  show.value = false
}

export function toggleCommandPalette() {
  show.value = !show.value
}
