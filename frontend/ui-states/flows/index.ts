import type { AnyFlow } from '../flow'
import { discussion } from './discussion'
import { feed } from './feed'
import { members } from './members'
import { newDiscussion } from './newDiscussion'
import { notifications } from './notifications'
import { onboarding } from './onboarding'
import { saved } from './saved'
import { search } from './search'
import { space } from './space'

/** Every flow, in the order the canvas lays them out. */
export const flows: AnyFlow[] = [
  feed,
  space,
  discussion,
  newDiscussion,
  search,
  notifications,
  saved,
  members,
  onboarding,
]
