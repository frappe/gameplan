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
 * Left and right step through the list, which is what the layout is made of.
 * Up and down are asked for as they look on screen, and the grid works out
 * which list position that comes to.
 */
export type ProfileCardMove = 'earlier' | 'later' | 'rowUp' | 'rowDown'

/** A write a bound card can ask for. Each one targets a profile (or User) field. */
export type ProfileFieldUpdate =
  | { field: 'bio' | 'readme'; value: string }
  | { field: 'image' | 'cover_image'; value: string }
  | { field: 'cover_image_position'; value: number }
  | { field: 'full_name'; firstName: string; lastName: string }

/**
 * An edit on its way to becoming a write.
 *
 * The same shape as `ProfileFieldUpdate` except for the name, where either half
 * may be left out. The halves live on the `User` document, which is only fetched
 * once the profile has said who owns it, so for a moment after the panel is on
 * screen they are empty because they are unknown rather than because the name is
 * blank. An input stages only the half it edits, and the other one keeps coming
 * from the document until someone types in it too. Staging the pair would pin the
 * untyped half to that empty value and Save would write the real one away.
 */
export type ProfileFieldStage =
  | Exclude<ProfileFieldUpdate, { field: 'full_name' }>
  | { field: 'full_name'; firstName?: string; lastName?: string }

/**
 * Writes a bound card's value back to the profile. Supplied by the profile page
 * for its About dialog, and by the customize page's field draft when its Save is
 * pressed — the one place that knows which document each bound field lives on.
 */
export interface ProfileFieldEditor {
  /**
   * False until the `User` document has arrived. Empty name halves mean nothing
   * until it has, so a caller showing the name has to keep the one it already
   * has rather than treat the pair as a name that is genuinely blank.
   */
  isNameLoaded: boolean
  /** `User.first_name` / `User.last_name`, for the two-input full-name editor. */
  firstName: string
  lastName: string
  /** Rejects when the write fails; the caller keeps the draft and shows the error. */
  save: (update: ProfileFieldUpdate) => Promise<void>
}

/**
 * Every bound field's value, in the shape the panel's controls type it in.
 *
 * A name is one string on the card and two inputs in the panel, so it is carried
 * as two fields here rather than as the profile's joined `full_name`.
 */
export interface ProfileFieldValues {
  bio: string
  readme: string
  image: string
  cover_image: string
  cover_image_position: number
  firstName: string
  lastName: string
}

/**
 * The customize page's staged bound-field edits.
 *
 * The controls in the panel read `values` and write through `stage`. Nothing
 * reaches the server until the page's Save button commits it, which is what puts
 * a bound value on the same footing as the layout: one Save, one set of unsaved
 * changes, one question when you leave with them.
 */
export interface ProfileFieldDraft {
  /** What each field will hold once Save lands: the staged edit, or the stored value. */
  values: ProfileFieldValues
  /** Stages an edit in place of writing it. */
  stage: (update: ProfileFieldStage) => void
  /** Drops the staged edit for one field, back to what the server holds. */
  reset: (field: ProfileFieldUpdate['field']) => void
}

/** A profile field a bento card can bind to. */
export type ProfileBoundField = 'cover_image' | 'image' | 'full_name' | 'bio' | 'readme'

/**
 * Which control the panel edits a bound field with.
 *
 * Named separately from `format` because the two answer different questions:
 * `format` is how the card renders the value, this is how it is typed in. A
 * name is one string on the card and two inputs in the panel.
 */
export type ProfileBoundEditor = 'name' | 'text' | 'richText' | 'image'

export interface ProfileBoundFieldSpec {
  field: ProfileBoundField
  /** Card id the default layout uses for this field. */
  id: string
  size: ProfileCardSize
  title: string
  format: ProfileCardFormat
  editor: ProfileBoundEditor
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
    editor: 'image',
    emptyIcon: 'lucide-image',
    emptyPrompt: 'Add a cover image',
  },
  {
    field: 'image',
    id: 'avatar',
    size: '1x1',
    title: 'Avatar',
    format: 'image',
    editor: 'image',
    emptyIcon: 'lucide-user-round',
    emptyPrompt: 'Add a photo',
  },
  {
    field: 'full_name',
    id: 'full-name',
    size: '1x1',
    title: 'Full name',
    format: 'text',
    editor: 'name',
    emptyIcon: 'lucide-type',
    emptyPrompt: 'Add your name',
  },
  {
    field: 'bio',
    id: 'bio',
    size: '2x1',
    title: 'Bio',
    format: 'text',
    editor: 'text',
    emptyIcon: 'lucide-quote',
    emptyPrompt: 'Add a short bio',
  },
  {
    field: 'readme',
    id: 'about',
    size: '4x2',
    title: 'About',
    format: 'html',
    editor: 'richText',
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
