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

/**
 * A keyboard reorder step.
 *
 * Steps through the list rather than around the grid, because a packed wall of
 * five tile sizes has no dependable "the card above this one" — but "the card
 * before this one" is exactly what the layout is made of.
 */
export type ProfileCardMove = 'earlier' | 'later' | 'start' | 'end'

/** A write a bound card can ask for. Each one targets a profile (or User) field. */
export type ProfileFieldUpdate =
  | { field: 'bio' | 'readme'; value: string }
  | { field: 'image' | 'cover_image'; value: string }
  | { field: 'cover_image_position'; value: number }
  | { field: 'full_name'; firstName: string; lastName: string }

/**
 * Writes a bound card's value back to the profile. Supplied by the customize
 * page's panel, and by the profile page for its About dialog — the one place
 * that knows which document each bound field actually lives on.
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
  /**
   * What the card shows on the customize canvas while the field has no value.
   *
   * The prompt names the thing to add rather than restating the title, because
   * the title is already on the checklist beside it. Icon classes must appear
   * as literals somewhere Tailwind scans, and this table is that place.
   */
  emptyIcon: string
  emptyPrompt: string
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
    emptyIcon: 'lucide-image',
    emptyPrompt: 'Add a cover image',
  },
  {
    field: 'image',
    id: 'avatar',
    size: '1x1',
    title: 'Avatar',
    format: 'image',
    emptyIcon: 'lucide-user-round',
    emptyPrompt: 'Add a photo',
  },
  {
    field: 'full_name',
    id: 'full-name',
    size: '1x1',
    title: 'Full name',
    format: 'text',
    emptyIcon: 'lucide-type',
    emptyPrompt: 'Add your name',
  },
  {
    field: 'bio',
    id: 'bio',
    size: '2x1',
    title: 'Bio',
    format: 'text',
    emptyIcon: 'lucide-quote',
    emptyPrompt: 'Add a short bio',
  },
  {
    field: 'readme',
    id: 'about',
    size: '4x2',
    title: 'About',
    format: 'html',
    emptyIcon: 'lucide-file-text',
    emptyPrompt: 'Write about yourself',
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
