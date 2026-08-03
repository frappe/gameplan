import { computed, ref, toRaw } from 'vue'
import {
  profileBoundFields,
  profileTextLimit,
  type ProfileBentoCard,
  type ProfileBoundField,
  type ProfileBoundFieldSpec,
  type ProfileCardType,
} from './types'

export interface ProfileBentoCardSource {
  load: () => ProfileBentoCardLoadResult | Promise<ProfileBentoCardLoadResult>
  save: (cards: ProfileBentoCard[]) => void | Promise<void>
}

export type ProfileBentoCardLoadResult =
  | ProfileBentoCard[]
  | {
      cards: ProfileBentoCard[]
      isDefault?: boolean
    }

/** Current value of each bound profile field, so a re-ticked card shows its value. */
export type ProfileBoundValues = Partial<Record<ProfileBoundField, string>>

export function useProfileBentoCustomization(source: ProfileBentoCardSource) {
  const cards = ref<ProfileBentoCard[]>([])
  const selectedCardId = ref('')
  const isSaving = ref(false)
  /** True while the draft mirrors the computed default instead of stored rows. */
  const isDefaultLayout = ref(false)
  const savedSnapshot = ref('')

  const selectedCard = computed(() => {
    return cards.value.find((card) => card.id === selectedCardId.value)
  })

  const selectedTextCharactersLeft = computed(() => {
    return profileTextLimit - (selectedCard.value?.text?.length || 0)
  })

  const isDirty = computed(() => {
    return serializeCards(cards.value) !== savedSnapshot.value
  })

  /**
   * The checklist has no state of its own: a field is ticked exactly when a card
   * bound to it is in the draft, so removing the card in the grid unticks the row.
   */
  const boundFieldsInDraft = computed(() => {
    let fields = new Set<ProfileBoundField>()
    for (let card of cards.value) {
      if (card.source === 'field' && card.field) fields.add(card.field as ProfileBoundField)
    }
    return fields
  })

  async function loadDraft() {
    let loadResult = await source.load()
    // `cards` is the layout either way — the computed default before the first
    // save, the stored rows after it. Only the dirty baseline differs.
    isDefaultLayout.value = isDefaultLoadResult(loadResult)
    cards.value = cloneCards(getLoadedCards(loadResult)).map(stripBoundValue)
    selectedCardId.value = ''
    savedSnapshot.value = serializeCards(cards.value)
  }

  async function saveDraft() {
    isSaving.value = true
    try {
      await source.save(cloneCards(cards.value))
      savedSnapshot.value = serializeCards(cards.value)
      isDefaultLayout.value = false
    } finally {
      isSaving.value = false
    }
  }

  function addCard(type: ProfileCardType) {
    let card = createCard(type)
    cards.value.push(card)
    selectedCardId.value = card.id
  }

  function toggleBoundField(field: ProfileBoundField, ticked: boolean) {
    let existing = cards.value.find((card) => card.source === 'field' && card.field === field)
    if (ticked) {
      if (existing) return
      addBoundCard(field)
      return
    }
    if (existing) removeCard(existing.id)
  }

  function addBoundCard(field: ProfileBoundField) {
    let spec = profileBoundFields.find((boundField) => boundField.field === field)
    if (!spec) return

    let card = createBoundCard(spec)
    cards.value.push(card)
    selectedCardId.value = card.id
  }

  function createBoundCard(spec: ProfileBoundFieldSpec): ProfileBentoCard {
    return {
      id: uniqueCardId(spec.id),
      type: 'Card',
      size: spec.size,
      title: spec.title,
      source: 'field',
      field: spec.field,
      format: spec.format,
      imageRendering: 'Cover',
      imagePosition: 50,
    }
  }

  function uniqueCardId(preferredId: string) {
    if (!cards.value.some((card) => card.id === preferredId)) return preferredId
    return `${preferredId}-${Date.now()}`
  }

  function removeCard(cardId: string) {
    let index = cards.value.findIndex((card) => card.id === cardId)
    if (index === -1) return

    cards.value.splice(index, 1)
    // Keep the selection meaningful: clear it if the removed card was selected,
    // otherwise leave whatever was already selected untouched.
    if (selectedCardId.value === cardId) {
      selectedCardId.value = ''
    }
  }

  function removeSelectedCard() {
    if (!selectedCardId.value) return
    removeCard(selectedCardId.value)
  }

  function reorderCards(cardIds: string[]) {
    let cardsById = new Map(cards.value.map((card) => [card.id, card]))
    let nextCards = cardIds.flatMap((cardId) => cardsById.get(cardId) || [])
    if (nextCards.length !== cards.value.length || sameCardOrder(cards.value, nextCards)) return

    cards.value = nextCards
  }

  function updateSelectedText(value: string) {
    if (!selectedCard.value) return
    selectedCard.value.text = value.slice(0, profileTextLimit)
  }

  function updateSelectedCard(
    updates: Partial<
      Pick<ProfileBentoCard, 'imagePosition' | 'imageRendering' | 'size' | 'title' | 'url'>
    >,
  ) {
    if (!selectedCard.value) return
    Object.assign(selectedCard.value, updates)
  }

  function updateSelectedImage(imageUrl: string) {
    if (!selectedCard.value) return
    selectedCard.value.image = imageUrl
  }

  function setCardImage(cardId: string, imageUrl: string) {
    let card = cards.value.find((card) => card.id === cardId)
    if (!card || !isImageCapableCard(card)) return
    card.image = imageUrl
    selectedCardId.value = cardId
  }

  return {
    cards,
    boundFieldsInDraft,
    selectedCardId,
    selectedCard,
    selectedTextCharactersLeft,
    isDefaultLayout,
    isDirty,
    isSaving,
    loadDraft,
    saveDraft,
    addCard,
    toggleBoundField,
    reorderCards,
    removeCard,
    removeSelectedCard,
    updateSelectedText,
    updateSelectedCard,
    updateSelectedImage,
    setCardImage,
  }
}

function createCard(type: ProfileCardType): ProfileBentoCard {
  let id = `${type}-${Date.now()}`
  if (type === 'Blank') {
    return {
      id,
      type,
      size: '1x1',
      title: 'Blank',
      source: 'custom',
    }
  }
  return {
    id,
    type: 'Card',
    size: '2x1',
    title: 'New card',
    source: 'custom',
    text: 'Share a short introduction, link, or image.',
    imageRendering: 'Cover',
    imagePosition: 50,
  }
}

function isImageCapableCard(card: ProfileBentoCard) {
  // A bound card's image comes from the profile; an uploaded one would be
  // dropped on save.
  return card.source === 'custom' && card.type !== 'Blank'
}

function cloneCards(cards: ProfileBentoCard[]) {
  return cards.map((card) => ({ ...toRaw(card) }))
}

/**
 * The draft is the layout and nothing else. A bound card's value lives on the
 * profile and is resolved for display (see `applyProfileBoundValues`), so the
 * copy the read path sends along is dropped here rather than being carried
 * around as a stale duplicate that the save path would discard anyway.
 */
function stripBoundValue(card: ProfileBentoCard): ProfileBentoCard {
  if (card.source !== 'field') return card
  return { ...card, text: undefined, image: undefined }
}

function getLoadedCards(loadResult: ProfileBentoCardLoadResult) {
  return Array.isArray(loadResult) ? loadResult : loadResult.cards
}

function isDefaultLoadResult(loadResult: ProfileBentoCardLoadResult) {
  return !Array.isArray(loadResult) && Boolean(loadResult.isDefault)
}

function serializeCards(cards: ProfileBentoCard[]) {
  return JSON.stringify(cards)
}

function sameCardOrder(first: ProfileBentoCard[], second: ProfileBentoCard[]) {
  return first.every((card, index) => card.id === second[index]?.id)
}
