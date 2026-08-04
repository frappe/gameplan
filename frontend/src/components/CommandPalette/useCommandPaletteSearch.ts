import { computed, ref, toValue, watch } from 'vue'
import type { Component, MaybeRefOrGetter, Ref } from 'vue'
import fuzzysort from 'fuzzysort'
import type { CommandPaletteGroup, CommandPaletteItem } from './registry'

interface ResultGroupConfig {
  id?: string
  title: string
  component?: Component
}

interface CommandPaletteSearchOptions {
  query: Ref<string>
  commandGroups: MaybeRefOrGetter<CommandPaletteGroup[]>
  localItems: MaybeRefOrGetter<CommandPaletteItem[]>
  localGroups: MaybeRefOrGetter<ResultGroupConfig[]>
  serverGroups: MaybeRefOrGetter<CommandPaletteGroup[]>
}

export function useCommandPaletteSearch(options: CommandPaletteSearchOptions) {
  const filteredOptions = ref<CommandPaletteItem[]>([])
  const groupedSearchResults = ref<CommandPaletteGroup[]>([])

  const activeItem = computed(() => getActiveItem())
  const activeItemId = computed(() =>
    activeItem.value ? getCommandPaletteItemElementId(activeItem.value) : undefined,
  )

  function updateLocalResults() {
    if (!options.query.value) {
      filteredOptions.value = []
      return
    }

    const localItems = toValue(options.localItems)
    const ranked = fuzzysort
      .go(options.query.value, localItems, {
        key: 'search',
        limit: 100,
        threshold: -10000,
      })
      .map((result) => result.obj)

    filteredOptions.value = clusterRelatedItems(ranked, localItems)
  }

  function generateSearchResults({ preserveActive = true } = {}) {
    const activeItemKey = preserveActive ? getActiveItemKey() : null
    const localResults = getLocalResultGroups()
    const commandGroups = getFilteredCommandGroups(options.query.value)
    const serverGroups =
      options.query.value.length > 2 ? cloneGroups(toValue(options.serverGroups)) : []

    const fullTextSearchItem: CommandPaletteItem = {
      title: `Search for "${options.query.value}"`,
      name: 'search-full-text',
      doctype: 'Search',
      icon: 'lucide-file-search',
      route: { name: 'Search', query: { q: options.query.value } },
    }

    const realResults = [...commandGroups, ...localResults, ...serverGroups].filter(
      (group) => group.items.length > 0,
    )
    const allResults = appendFullTextSearchResult(realResults, fullTextSearchItem)

    setActiveItem(allResults, activeItemKey)
    groupedSearchResults.value = allResults
  }

  function getActiveItem() {
    return groupedSearchResults.value.flatMap((group) => group.items).find((item) => item.isActive)
  }

  function navigateList(direction: number) {
    const allItems = getSelectableItems()
    if (!allItems.length) return

    const currentIndex = allItems.findIndex((item) => item.isActive)
    if (currentIndex !== -1) {
      allItems[currentIndex].isActive = false
    }

    let newIndex = currentIndex + direction
    if (newIndex < 0) newIndex = allItems.length - 1
    if (newIndex >= allItems.length) newIndex = 0

    allItems[newIndex].isActive = true
  }

  function activateItem(itemToActivate: CommandPaletteItem) {
    for (let item of getSelectableItems()) {
      item.isActive = false
    }
    itemToActivate.isActive = true
  }

  let previousQuery = options.query.value

  watch(
    () => [
      options.query.value,
      filteredOptions.value,
      toValue(options.commandGroups),
      toValue(options.serverGroups),
    ],
    () => {
      const queryChanged = options.query.value !== previousQuery
      previousQuery = options.query.value
      generateSearchResults({ preserveActive: !queryChanged })
    },
    { immediate: true },
  )

  function getLocalResultGroups() {
    const itemsByGroup: Record<string, CommandPaletteItem[]> = {}
    const localGroups = toValue(options.localGroups)

    for (const group of localGroups) {
      itemsByGroup[getCommandPaletteGroupKey(group)] = []
    }

    for (const item of filteredOptions.value) {
      itemsByGroup[item.group || '']?.push(item)
    }

    return localGroups
      .map((group) => ({
        ...group,
        items: (itemsByGroup[getCommandPaletteGroupKey(group)] || []).map((item) => ({ ...item })),
      }))
      .filter((group) => group.items.length > 0)
  }

  function getActiveItemKey() {
    const activeItem = getActiveItem()
    return activeItem ? getCommandPaletteItemKey(activeItem) : null
  }

  function setActiveItem(groups: CommandPaletteGroup[], activeItemKey: string | null) {
    let nextActiveItem: CommandPaletteItem | null = null

    for (let group of groups) {
      for (let item of group.items) {
        item.isActive = false
        if (!item.disabled && activeItemKey && getCommandPaletteItemKey(item) === activeItemKey) {
          nextActiveItem = item
        }
      }
    }

    if (!nextActiveItem) {
      nextActiveItem = groups.flatMap((group) => group.items).find((item) => !item.disabled) || null
    }

    if (nextActiveItem) {
      nextActiveItem.isActive = true
    }
  }

  function getSelectableItems() {
    return groupedSearchResults.value
      .flatMap((group) => group.items)
      .filter((item) => !item.disabled)
  }

  function getFilteredCommandGroups(searchQuery: string) {
    return toValue(options.commandGroups)
      .map((group) => ({
        ...group,
        items: getMatchingCommands(group.items, searchQuery),
      }))
      .filter((group) => group.items.length > 0)
  }

  function appendFullTextSearchResult(
    groups: CommandPaletteGroup[],
    fullTextSearchItem: CommandPaletteItem,
  ) {
    if (options.query.value.length <= 2) return groups

    if (groups.length === 0) {
      return [{ title: 'Jump to', items: [fullTextSearchItem] }]
    }

    return [...groups, { title: 'Search', items: [fullTextSearchItem] }]
  }

  return {
    activeItem,
    activeItemId,
    activateItem,
    filteredOptions,
    generateSearchResults,
    getCommandPaletteGroupId,
    getCommandPaletteGroupKey,
    getCommandPaletteItemElementId,
    getCommandPaletteItemKey,
    groupedSearchResults,
    navigateList,
    updateLocalResults,
  }
}

/**
 * Keep the rows that describe one thing together.
 *
 * Fuzzysort scores every row on its own, so a person's Profile/Posts/Replies can end up
 * split by another person who happened to score between them. Rows sharing a `cluster`
 * move as a unit to the rank of their best match, in the order they were declared.
 */
function clusterRelatedItems(ranked: CommandPaletteItem[], source: CommandPaletteItem[]) {
  const sourceIndex = new Map(source.map((item, index) => [item, index]))
  const members = new Map<string, CommandPaletteItem[]>()

  for (const item of ranked) {
    if (!item.cluster) continue
    const existing = members.get(item.cluster)
    if (existing) existing.push(item)
    else members.set(item.cluster, [item])
  }
  if (!members.size) return ranked

  for (const group of members.values()) {
    group.sort((a, b) => (sourceIndex.get(a) ?? 0) - (sourceIndex.get(b) ?? 0))
  }

  const placed = new Set<string>()
  const result: CommandPaletteItem[] = []
  for (const item of ranked) {
    if (!item.cluster) {
      result.push(item)
      continue
    }
    if (placed.has(item.cluster)) continue
    placed.add(item.cluster)
    result.push(...(members.get(item.cluster) ?? []))
  }
  return result
}

function getMatchingCommands(items: CommandPaletteItem[], searchQuery: string) {
  const visibleItems = items.filter((item) => !item.condition || item.condition())
  if (!searchQuery) {
    return visibleItems
      .filter((item) => (item.defaultScore ?? 1) > 0)
      .sort((a, b) => (b.defaultScore ?? 1) - (a.defaultScore ?? 1))
      .map((item) => ({ ...item }))
  }

  return visibleItems
    .map((item) => getScoredCommand(item, searchQuery))
    .filter((result): result is { item: CommandPaletteItem; score: number } => Boolean(result))
    .sort((a, b) => b.score - a.score)
    .map((result) => result.item)
}

function getScoredCommand(item: CommandPaletteItem, searchQuery: string) {
  const candidates = [item.title, item.search, ...(item.aliases || [])].filter(Boolean) as string[]
  let bestMatch: { score: number; candidate: string } | null = null

  for (const candidate of candidates) {
    const result = fuzzysort.single(searchQuery, candidate)
    if (!result) continue

    const aliasPenalty = item.aliases?.includes(candidate) ? 50 : 0
    const score = result.score - aliasPenalty
    if (!bestMatch || score > bestMatch.score) {
      bestMatch = { score, candidate }
    }
  }

  if (!bestMatch || bestMatch.score < -10000) return null

  const scoreScale = item.scoreScale ?? 1
  const matchedAlias =
    bestMatch.candidate !== item.title && item.aliases?.includes(bestMatch.candidate)
      ? bestMatch.candidate
      : null

  return {
    item: {
      ...item,
      subtitle: matchedAlias ? `Matches "${matchedAlias}"` : item.subtitle,
    },
    score: bestMatch.score * scoreScale,
  }
}

function cloneGroups(groups: CommandPaletteGroup[]) {
  return groups
    .map((group) => ({
      ...group,
      items: group.items.map((item) => ({ ...item })),
    }))
    .filter((group) => group.items.length > 0)
}

function getCommandPaletteItemKey(item: CommandPaletteItem) {
  return `${item.group || ''}:${item.doctype || ''}:${item.name}`
}

function getCommandPaletteItemElementId(item: CommandPaletteItem) {
  return `command-palette-item-${slugifyId(getCommandPaletteItemKey(item))}`
}

function getCommandPaletteGroupKey(group: Pick<CommandPaletteGroup, 'id' | 'title'>) {
  return group.id || group.title
}

function getCommandPaletteGroupId(group: Pick<CommandPaletteGroup, 'id' | 'title'>) {
  return `command-palette-group-${slugifyId(getCommandPaletteGroupKey(group))}`
}

function slugifyId(value: string) {
  return value.replace(/[^A-Za-z0-9_-]/g, '-')
}
