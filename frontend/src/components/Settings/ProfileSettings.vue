<template>
  <SettingsHeader>
    <h2 class="text-lg-semibold text-ink-gray-8">Profile</h2>
  </SettingsHeader>

  <SettingsBody>
    <div v-if="profile && user" class="space-y-11 pt-6">
      <section class="space-y-6">
        <div class="flex items-center gap-4">
          <div>
            <input
              ref="avatarFileInput"
              type="file"
              class="hidden"
              accept="image/png,image/jpeg"
              @change="selectAvatarFile"
            />
            <Dropdown v-if="hasAvatar" :options="avatarOptions" align="start">
              <button
                type="button"
                class="rounded-full flex focus:outline-none focus:ring-2 focus:ring-outline-gray-3"
                aria-label="Profile picture options"
              >
                <UserAvatar :user="sessionUser.name" size="3xl" class="!h-16 !w-16 rounded-full" />
              </button>
            </Dropdown>
            <button
              v-else
              type="button"
              class="rounded-full focus:outline-none focus:ring-2 focus:ring-outline-gray-3"
              aria-label="Upload profile picture"
              @click="openAvatarFileSelector"
            >
              <UserAvatar :user="sessionUser.name" size="3xl" class="!h-16 !w-16 rounded-full" />
            </button>
          </div>
          <div>
            <div class="text-base-medium text-ink-gray-8">Profile picture</div>
            <p class="text-p-sm text-ink-gray-5">Helps people recognise you</p>
          </div>
        </div>

        <div class="grid gap-6 sm:grid-cols-2">
          <div>
            <TextInput
              label="First name"
              class="w-full"
              v-model="firstName"
              :disabled="savingName"
              @blur="saveName"
            />
          </div>
          <div>
            <TextInput
              label="Last name"
              class="w-full"
              v-model="lastName"
              :disabled="savingName"
              @blur="saveName"
            />
          </div>
        </div>

        <div>
          <Textarea
            label="Bio"
            class="w-full"
            maxlength="280"
            v-model="bio"
            :disabled="savingBio"
            @blur="saveBio"
          />
        </div>
      </section>

      <section>
        <h2 class="text-lg-semibold text-ink-gray-8">Account</h2>

        <div class="mt-2 divide-y divide-outline-gray-1">
          <SettingsRow
            title="Public profile"
            description="View your public page or customize its card layout"
          >
            <div class="flex gap-2">
              <Button icon-left="lucide-user" @click="goToMyProfile">View</Button>
              <Button icon-left="lucide-layout-dashboard" @click="goToProfileCustomize">
                Customize
              </Button>
            </div>
          </SettingsRow>

          <SettingsRow title="Password" description="Manage password and account access">
            <Button link="/update-password">Update Password</Button>
          </SettingsRow>
        </div>
      </section>
    </div>
  </SettingsBody>

  <Dialog v-model:open="showAvatarEditor" title="Edit avatar" @after-leave="clearAvatarFile">
    <ProfileImageEditor
      v-if="profile && selectedAvatarFile"
      :profile="profileChildResource"
      :file="selectedAvatarFile"
      @done="closeAvatarEditor"
      @cancel="closeAvatarEditor"
    />
  </Dialog>
</template>

<script setup lang="ts">
import { computed, ref, useTemplateRef, watch } from 'vue'
import { useRouter } from 'vue-router'
import {
  Button,
  Dialog,
  Dropdown,
  SettingsBody,
  SettingsHeader,
  SettingsRow,
  Textarea,
  TextInput,
  toast,
  useDoc,
} from 'frappe-ui'
import type { DropdownOptions } from 'frappe-ui'
import ProfileImageEditor from '@/components/ProfileImageEditor.vue'
import UserAvatar from '@/components/UserAvatar.vue'
import { useSessionUser } from '@/data/users'
import type { GPUserProfile } from '@/types/doctypes'

interface ProfileMethods {
  setImage: (data: { image: string | null }) => void
}

interface UserDoc {
  name: string
  first_name?: string
  last_name?: string
  full_name?: string
}

// Declared so the parent's @close-dialog isn't treated as a failed attribute
// fallthrough (this component renders a fragment). Route navigation closes Settings.
defineEmits<{ (event: 'close-dialog'): void }>()

const profileAutosaveToastId = 'profile-settings-autosave'

const router = useRouter()
const sessionUser = useSessionUser()
const profileName = computed(() => sessionUser.user_profile || '')

const profileResource = useDoc<GPUserProfile, ProfileMethods>({
  doctype: 'GP User Profile',
  // Pass a getter, not the ComputedRef: useDoc's `name` is MaybeRefOrGetter and a
  // plain getter matches structurally even when frontend/frappe-ui resolve
  // different @vue/reactivity copies (a ComputedRef would not).
  name: () => profileName.value,
  immediate: false,
  methods: {
    setImage: 'set_image',
  },
})

const userResource = useDoc<UserDoc>({
  doctype: 'User',
  name: () => sessionUser.name,
  immediate: false,
})

const profile = computed(() => profileResource.doc)
const user = computed(() => userResource.doc)
const profileChildResource = computed(() => ({
  ...profileResource,
  doc: profile.value,
}))
const firstName = ref('')
const lastName = ref('')
const bio = ref('')
const savingName = computed(() => userResource.setValue.loading)
const savingBio = computed(() => profileResource.setValue.loading)
const showAvatarEditor = ref(false)
const selectedAvatarFile = ref<File | null>(null)
const avatarFileInput = useTemplateRef<HTMLInputElement>('avatarFileInput')
const hasAvatar = computed(() => Boolean(profile.value?.image))
const avatarOptions = computed<DropdownOptions>(() => [
  {
    label: 'Change image',
    icon: 'lucide-image-up',
    onClick: openAvatarFileSelector,
  },
  {
    label: 'Remove image',
    icon: 'lucide-trash-2',
    onClick: removeAvatar,
  },
])

watch(
  profileName,
  () => {
    if (profileName.value) {
      profileResource.reload()
    }
  },
  { immediate: true },
)

watch(
  () => sessionUser.name,
  () => {
    if (sessionUser.name) {
      userResource.reload()
    }
  },
  { immediate: true },
)

watch(
  user,
  (currentUser) => {
    let nameParts = getUserNameParts(currentUser)
    firstName.value = nameParts.first_name
    lastName.value = nameParts.last_name
  },
  { immediate: true },
)

watch(
  profile,
  (currentProfile) => {
    bio.value = currentProfile?.bio || ''
  },
  { immediate: true },
)

async function saveName() {
  if (!user.value || savingName.value) return

  let nextFirstName = firstName.value.trim()
  let nextLastName = lastName.value.trim()
  if (!nextFirstName) {
    toast.error('First name is required')
    return
  }

  let currentName = getUserNameParts(user.value)
  if (nextFirstName === currentName.first_name && nextLastName === currentName.last_name) return

  try {
    await userResource.setValue.submit({
      first_name: nextFirstName,
      last_name: nextLastName,
    })
    firstName.value = nextFirstName
    lastName.value = nextLastName
    sessionUser.full_name = getFullNameFromParts(nextFirstName, nextLastName)
    toast.success('Name saved', { id: profileAutosaveToastId })
  } catch {
    toast.error('Could not save name')
  }
}

async function saveBio() {
  if (!profile.value || savingBio.value) return

  if (bio.value === (profile.value.bio || '')) return

  try {
    await profileResource.setValue.submit({ bio: bio.value })
    sessionUser.bio = bio.value
    toast.success('Bio saved', { id: profileAutosaveToastId })
  } catch {
    toast.error('Could not save bio')
  }
}

function openAvatarFileSelector() {
  avatarFileInput.value?.click()
}

function selectAvatarFile(event: Event) {
  let input = event.target as HTMLInputElement
  let file = input.files?.[0]
  input.value = ''
  if (!file) return

  let error = validateAvatarFile(file)
  if (error) {
    toast.error(error)
    return
  }

  selectedAvatarFile.value = file
  showAvatarEditor.value = true
}

function closeAvatarEditor() {
  showAvatarEditor.value = false
}

function clearAvatarFile() {
  selectedAvatarFile.value = null
}

async function removeAvatar() {
  if (!profile.value) return

  try {
    await profileResource.setImage.submit({ image: null })
    profile.value.image = ''
    profile.value.is_image_background_removed = 0
    profile.value.image_background_color = ''
    profile.value.original_image = ''
    sessionUser.user_image = ''
    sessionUser.is_image_background_removed = 0
    sessionUser.image_background_color = ''
  } catch {
    toast.error('Could not remove profile picture')
  }
}

function goToMyProfile() {
  if (!sessionUser.user_profile) return
  router.push({ name: 'PersonProfileProfile', params: { personId: sessionUser.user_profile } })
}

function goToProfileCustomize() {
  router.push({ name: 'ProfileCustomize' })
}

function splitFullName(name: string) {
  let trimmedName = name.trim()
  let [firstName = '', ...lastNameParts] = trimmedName.split(/\s+/)

  return {
    first_name: firstName,
    last_name: lastNameParts.join(' '),
  }
}

function getFullName(currentUser?: UserDoc | null) {
  return (
    currentUser?.full_name ||
    [currentUser?.first_name, currentUser?.last_name].filter(Boolean).join(' ') ||
    sessionUser.full_name ||
    ''
  )
}

function getUserNameParts(currentUser?: UserDoc | null) {
  let fallback = splitFullName(getFullName(currentUser))

  return {
    first_name: (currentUser?.first_name ?? fallback.first_name).trim(),
    last_name: (currentUser?.last_name ?? fallback.last_name).trim(),
  }
}

function getFullNameFromParts(firstName: string, lastName: string) {
  return [firstName, lastName].filter(Boolean).join(' ')
}

function validateAvatarFile(file: File) {
  let extn = file.name.split('.').pop()?.toLowerCase()
  if (!extn || !['png', 'jpg', 'jpeg'].includes(extn)) {
    return 'Only PNG and JPG images are allowed'
  }
}
</script>
