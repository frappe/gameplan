import { computed, ref, toRaw } from 'vue'
import { profileTextLimit, type ProfileBentoCard, type ProfileCardType } from './types'

export interface ProfileBentoCardSource {
  load: () => ProfileBentoCardLoadResult | Promise<ProfileBentoCardLoadResult>
  save: (cards: ProfileBentoCard[]) => void | Promise<void>
}

export type ProfileBentoCardLoadResult =
  | ProfileBentoCard[]
  | {
      cards: ProfileBentoCard[]
      isDefault?: boolean
      starterCards?: ProfileBentoCard[]
    }

export function useProfileBentoCustomization(source: ProfileBentoCardSource) {
  const cards = ref<ProfileBentoCard[]>([])
  const starterCards = ref<ProfileBentoCard[]>([])
  const selectedCardId = ref('')
  const isNewProfilePage = ref(false)
  const isSaving = ref(false)
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

  async function loadDraft() {
    let loadResult = await source.load()
    isNewProfilePage.value = isDefaultLoadResult(loadResult)
    starterCards.value = cloneCards(getStarterCards(loadResult))
    cards.value = isNewProfilePage.value ? [] : cloneCards(getLoadedCards(loadResult))
    selectedCardId.value = ''
    savedSnapshot.value = serializeCards(cards.value)
  }

  async function saveDraft() {
    isSaving.value = true
    try {
      await source.save(cloneCards(cards.value))
      savedSnapshot.value = serializeCards(cards.value)
      isNewProfilePage.value = false
    } finally {
      isSaving.value = false
    }
  }

  function startWithStarterCards() {
    if (!isNewProfilePage.value) return
    cards.value = cloneCards(starterCards.value)
    selectedCardId.value = cards.value[0]?.id || ''
  }

  function addCard(type: ProfileCardType) {
    let card = createCard(type)
    cards.value.push(card)
    selectedCardId.value = card.id
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
    starterCards,
    selectedCardId,
    selectedCard,
    selectedTextCharactersLeft,
    isNewProfilePage,
    isDirty,
    isSaving,
    loadDraft,
    saveDraft,
    startWithStarterCards,
    addCard,
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
  return card.type === 'Card' || card.type === 'Image' || card.type === 'Text'
}

function cloneCards(cards: ProfileBentoCard[]) {
  return cards.map((card) => ({ ...toRaw(card) }))
}

function getLoadedCards(loadResult: ProfileBentoCardLoadResult) {
  return Array.isArray(loadResult) ? loadResult : loadResult.cards
}

function isDefaultLoadResult(loadResult: ProfileBentoCardLoadResult) {
  return !Array.isArray(loadResult) && Boolean(loadResult.isDefault)
}

function getStarterCards(loadResult: ProfileBentoCardLoadResult) {
  return Array.isArray(loadResult) ? [] : loadResult.starterCards || []
}

function serializeCards(cards: ProfileBentoCard[]) {
  return JSON.stringify(cards)
}

function sameCardOrder(first: ProfileBentoCard[], second: ProfileBentoCard[]) {
  return first.every((card, index) => card.id === second[index]?.id)
}
