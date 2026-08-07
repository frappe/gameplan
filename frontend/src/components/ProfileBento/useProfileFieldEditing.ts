import { computed, type ComputedRef } from 'vue'
import { toast, useDoc } from 'frappe-ui'
import { useSessionUser } from '@/data/users'
import type { GPUserProfile } from '@/types/doctypes'
import type { ProfileFieldEditor, ProfileFieldUpdate } from './types'

interface ResourceCall<TParams> {
  submit: (params: TParams) => Promise<unknown>
}

/**
 * The slice of the profile's `useDoc` resource the editors write through. The
 * page owns the resource; this composable only knows how to drive it.
 */
export interface ProfileEditingResource {
  doc: GPUserProfile | null
  setValue: ResourceCall<Partial<GPUserProfile>>
  setImage: ResourceCall<{ image: string | null }>
  setCoverImagePosition: ResourceCall<{ position: number }>
}

interface UserDoc {
  name: string
  first_name?: string
  last_name?: string
  full_name?: string
}

const failureMessages: Record<ProfileFieldUpdate['field'], string> = {
  bio: 'Could not save bio',
  readme: 'Could not save about',
  image: 'Could not save profile picture',
  cover_image: 'Could not save cover image',
  cover_image_position: 'Could not save cover position',
  full_name: 'Could not save name',
}

/**
 * Writing the profile fields the bound cards display.
 *
 * Every write lands on the profile (or `User`) document — never on the bento
 * layout — so `layout_customized` stays 0 and the owner keeps getting the
 * default layout as it evolves. `onSaved` re-reads the cards, because a bound
 * card resolves its value server-side and nothing is patched in place. A caller
 * that writes several fields in one go leaves it out and re-reads once itself.
 */
export function useProfileFieldEditing(options: {
  profile: ProfileEditingResource
  /** The profile owner's `User` name. Empty when the viewer is not the owner. */
  userId: () => string
  enabled: () => boolean
  onSaved?: () => void | Promise<void>
}): ComputedRef<ProfileFieldEditor | undefined> {
  const sessionUser = useSessionUser()
  // `userId` is empty until the profile loads (and stays empty for a visitor),
  // so nothing is fetched until there is a name and the viewer is the owner.
  const userResource = useDoc<UserDoc>({
    doctype: 'User',
    name: options.userId,
  })

  async function save(update: ProfileFieldUpdate) {
    try {
      await write(update)
    } catch (error) {
      toast.error(failureMessages[update.field])
      throw error
    }
    await options.onSaved?.()
  }

  async function write(update: ProfileFieldUpdate) {
    switch (update.field) {
      case 'full_name': {
        let firstName = update.firstName.trim()
        if (!firstName) throw new Error('First name is required')
        await userResource.setValue.submit({
          first_name: firstName,
          last_name: update.lastName.trim(),
        })
        sessionUser.full_name = [firstName, update.lastName.trim()].filter(Boolean).join(' ')
        return
      }
      case 'image':
        await options.profile.setImage.submit({ image: update.value })
        return
      case 'cover_image_position':
        await options.profile.setCoverImagePosition.submit({ position: update.value })
        return
      case 'bio':
        await options.profile.setValue.submit({ bio: update.value })
        sessionUser.bio = update.value
        return
      default:
        await options.profile.setValue.submit({ [update.field]: update.value })
    }
  }

  return computed(() => {
    if (!options.enabled()) return undefined
    return {
      // The `User` document is a second request that cannot start until the
      // profile has named its owner, so the halves below are empty for a moment
      // after the profile is already on screen. This says which it is.
      isNameLoaded: Boolean(userResource.doc),
      firstName: userResource.doc?.first_name || '',
      lastName: userResource.doc?.last_name || '',
      save,
    }
  })
}
