import { ref } from 'vue'

interface UseReactionPickerOptions {
  toggleReaction: (emoji: string) => void
  /** Runs after a pick, for a popup that dismisses itself on selection. */
  onPick?: () => void
}

/**
 * Expand/collapse state for the "browse all emoji" mode of the quick reaction
 * popup, shared by the desktop hover card and the mobile bottom sheet so both
 * behave the same. Any emoji picked in that mode reacts straight away: the user
 * does not have to add it to their quick reactions first.
 */
export function useReactionPicker(options: UseReactionPickerOptions) {
  const isBrowsingAllEmojis = ref(false)

  function browseAllEmojis() {
    isBrowsingAllEmojis.value = true
  }

  function collapse() {
    isBrowsingAllEmojis.value = false
  }

  function pickFromAllEmojis(emoji: string) {
    options.toggleReaction(emoji)
    collapse()
    options.onPick?.()
  }

  return { isBrowsingAllEmojis, browseAllEmojis, collapse, pickFromAllEmojis }
}
