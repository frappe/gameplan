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

/** A profile field a bento card can bind to. */
export type ProfileBoundField = 'cover_image' | 'image' | 'full_name' | 'bio' | 'readme'

export interface ProfileBoundFieldSpec {
  field: ProfileBoundField
  /** Card id the default layout uses for this field. */
  id: string
  size: ProfileCardSize
  title: string
  format: ProfileCardFormat
}

/**
 * Mirrors `PROFILE_BENTO_BOUND_FIELDS` in `gp_user_profile.py`, in the same
 * order — the order the computed default lays the cards out in. The customize
 * checklist adds a card straight from this table, so the two must stay in step;
 * the server re-derives everything but size, title and url on read anyway.
 */
export const profileBoundFields: ProfileBoundFieldSpec[] = [
  {
    field: 'cover_image',
    id: 'cover',
    size: '4x1',
    title: 'Cover image',
    format: 'image',
  },
  {
    field: 'image',
    id: 'avatar',
    size: '1x1',
    title: 'Avatar',
    format: 'image',
  },
  {
    field: 'full_name',
    id: 'full-name',
    size: '1x1',
    title: 'Full name',
    format: 'text',
  },
  {
    field: 'bio',
    id: 'bio',
    size: '2x1',
    title: 'Bio',
    format: 'text',
  },
  {
    field: 'readme',
    id: 'about',
    size: '4x2',
    title: 'About',
    format: 'html',
  },
]

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
