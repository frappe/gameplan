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
