export type ProfileCardType = 'Card' | 'Blank' | 'Text' | 'Image'
export type ProfileCardSize = '1x1' | '1x2' | '2x1' | '2x2' | '4x1' | '4x2'
export type ProfileImageRendering = 'Cover' | 'Natural' | 'Fit'
/** `field` cards resolve their value from the profile at read time. */
export type ProfileCardSource = 'custom' | 'field'
export type ProfileCardFormat = 'text' | 'html' | 'image'

export interface ProfileBentoCard {
  id: string
  type: ProfileCardType
  size: ProfileCardSize
  title: string
  text?: string
  url?: string
  image?: string
  imageRendering?: ProfileImageRendering
  imagePosition?: number
  source: ProfileCardSource
  /** Bound profile fieldname. Present only when `source === 'field'`. */
  field?: string
  /** How `text`/`image` should render. Omitted for custom cards. */
  format?: ProfileCardFormat
}

/** A write a bound card can ask for. Each one targets a profile (or User) field. */
export type ProfileFieldUpdate =
  | { field: 'bio' | 'readme'; value: string }
  | { field: 'image' | 'cover_image'; value: string }
  | { field: 'cover_image_position'; value: number }
  | { field: 'full_name'; firstName: string; lastName: string }

/**
 * Inline editing of bound cards, supplied by the profile page when the viewer
 * owns the profile. Deliberately separate from the grid's `interactive` prop,
 * which means "customize page" (drag to reorder, card selection).
 */
export interface ProfileFieldEditor {
  /** `User.first_name` / `User.last_name`, for the two-input full-name editor. */
  firstName: string
  lastName: string
  /** Rejects when the write fails; the caller keeps the draft and shows the error. */
  save: (update: ProfileFieldUpdate) => Promise<void>
}

/** Bound fields a card can edit in place. */
export const profileEditableFields = [
  'cover_image',
  'image',
  'full_name',
  'bio',
  'readme',
] as const

export const profileBioLimit = 280

export const profileCardSizes: ProfileCardSize[] = ['1x1', '1x2', '2x1', '2x2', '4x1', '4x2']
export const profileImageRenderingOptions: Array<{
  label: string
  value: ProfileImageRendering
}> = [
  { label: 'Cover', value: 'Cover' },
  { label: 'Natural', value: 'Natural' },
  { label: 'Fit', value: 'Fit' },
]
export const profileTextLimit = 140

export const profileCardTypeOptions: Array<{ type: ProfileCardType; label: string; icon: string }> =
  [
    { type: 'Card', label: 'Card', icon: 'lucide-square' },
    { type: 'Blank', label: 'Spacer', icon: 'lucide-square-dashed' },
  ]
