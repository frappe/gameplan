import type { Editor } from '@tiptap/core'
import type { InjectionKey } from 'vue'
import type { useList } from 'frappe-ui'
import type { GPPoll } from '@/types/doctypes'
import type { Space } from '@/data/spaces'

export interface PollDraft {
  title: string
  options: Array<{ title: string }>
  anonymous: boolean
  multiple_answers: boolean
}

export interface ThreadPolls {
  polls: Pick<ReturnType<typeof useList<GPPoll>>, 'data' | 'loading'> & { reload?: () => unknown }
  embeddedPolls?: Pick<ReturnType<typeof useList<GPPoll>>, 'data' | 'loading'> & {
    reload?: () => unknown
  }
  space: () => Space | null | undefined
  readOnlyMode: () => boolean
}

export const threadPollsKey: InjectionKey<ThreadPolls> = Symbol('threadPolls')

export function emptyPollDraft(): PollDraft {
  return {
    title: '',
    options: [{ title: '' }, { title: '' }],
    anonymous: false,
    multiple_answers: false,
  }
}

export function isPollDraftReady(draft?: PollDraft | null) {
  if (!draft) return false
  const filledOptions = draft.options.filter((option) => option.title.trim())
  return Boolean(draft.title.trim()) && filledOptions.length >= 2
}

export function hasPollBlock(editor: Editor) {
  let found = false
  editor.state.doc.descendants((node) => {
    if (node.type.name === 'pollBlock') found = true
    return !found
  })
  return found
}

export function pollDraftInContent(html?: string | null): PollDraft | null {
  if (!html?.includes('data-poll-draft')) return null
  const block = new DOMParser()
    .parseFromString(html, 'text/html')
    .querySelector('div[data-type="poll"][data-poll-draft]')
  return parseDraft(block?.getAttribute('data-poll-draft') ?? null)
}

export function postedPollInContent(html?: string | null): string | null {
  if (!html?.includes('data-poll=')) return null
  const block = new DOMParser()
    .parseFromString(html, 'text/html')
    .querySelector('div[data-type="poll"][data-poll]')
  return block?.getAttribute('data-poll') ?? null
}

export function parseDraft(value: string | null): PollDraft | null {
  if (!value) return null
  let draft
  try {
    draft = JSON.parse(value)
  } catch {
    return null
  }
  const valid =
    typeof draft?.title === 'string' &&
    Array.isArray(draft.options) &&
    draft.options.every((option: { title?: unknown } | null) => typeof option?.title === 'string')
  return valid ? (draft as PollDraft) : null
}
