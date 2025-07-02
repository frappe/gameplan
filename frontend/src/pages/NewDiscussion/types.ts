import type { Ref, ComputedRef } from 'vue'
import type { Editor } from '@tiptap/core'
import type { GPDraft } from '@/types/doctypes'

// Core data interfaces
export interface DraftData {
  title: string
  content: string
  project: string | null
}

// Document-related types
export interface DraftMethods {
  publish: () => string
}

export type DraftDocument = ReturnType<
  typeof import('frappe-ui/src/data-fetching').useDoc<GPDraft, DraftMethods>
> | null

// Callback parameter types
export interface DraftDocumentCallback {
  name: string
  [key: string]: any
}

// Editor-related types
export interface TextEditorInstance {
  editor: Editor
}

export type TextEditorRef = Ref<TextEditorInstance | null>

// Space options types
export interface SpaceOption {
  value: string
  label: string
  description?: string
}

export interface SpaceGroup {
  group: string
  options: SpaceOption[]
}

export type FormattedSpaceOption = SpaceOption | SpaceGroup

// Validation function types
export type ValidateDraftFunction = (checkProject?: boolean) => boolean

// Action function types
export type ResetValuesFunction = () => void
export type SaveDraftFunction = () => Promise<void>
export type FetchDraftDocFunction = (draftId: string) => any

// Error message type
export type ErrorMessage = Ref<string | null>

// Computed and ref types for composables
export type IsDraftChangedComputed = ComputedRef<boolean>
export type PublishingRef = Ref<boolean>
export type SavingDraftRef = Ref<boolean>
export type IsPublishingSuccessfullyRef = Ref<boolean>
export type IsDeletingDraftRef = Ref<boolean>

// Keyboard event handler type
export type KeyboardEventHandler = (event: KeyboardEvent) => void

// Before unload event handler type
export type BeforeUnloadEventHandler = (event: BeforeUnloadEvent) => void
