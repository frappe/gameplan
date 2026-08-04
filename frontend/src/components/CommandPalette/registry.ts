import { computed, onBeforeUnmount, shallowReactive, toValue, watch } from 'vue'
import type { Component, MaybeRefOrGetter } from 'vue'
import type { RouteLocationRaw } from 'vue-router'

export interface CommandPaletteItem extends Partial<
  Omit<SearchResultItem, 'modified' | 'name' | 'title'>
> {
  title: string
  name: string
  search?: string
  aliases?: string[]
  subtitle?: string
  suffix?: string
  doctype?: string
  route?: RouteLocationRaw
  isActive?: boolean
  group?: string
  /**
   * Items sharing this key stay adjacent in the results, at the rank of whichever one
   * matched best — e.g. the Profile/Posts/Replies rows for one person.
   */
  cluster?: string
  type?: string
  icon?: Component | string
  onClick?: () => void
  condition?: () => boolean | undefined
  disabled?: boolean
  defaultScore?: number
  scoreScale?: number
  modified?: string
  hideCommunity?: boolean
}

export interface CommandPaletteGroup {
  id?: string
  title: string
  items: CommandPaletteItem[]
  component?: Component
  hideTitle?: boolean
}

export interface SearchResult {
  title: string
  items: SearchResultItem[]
}

export interface SearchResultItem {
  author: string
  content: string
  doctype: string
  id: string
  name: string
  project: string
  team?: string
  reference_doctype?: string
  reference_name?: string
  score: number
  modified: number
  title: string
}

const commandSets = shallowReactive(new Map<symbol, CommandPaletteItem[]>())

export const registeredCommands = computed(() => {
  return [...commandSets.values()].flat()
})

export function useCommandPaletteCommands(commands: MaybeRefOrGetter<CommandPaletteItem[]>) {
  const key = Symbol('command-palette-commands')
  const stop = watch(
    () => toValue(commands),
    (items) => {
      commandSets.set(key, items)
    },
    { immediate: true },
  )

  onBeforeUnmount(() => {
    stop()
    commandSets.delete(key)
  })
}
