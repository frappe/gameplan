<template>
  <div class="flex h-screen bg-surface-sidebar">
    <!--
      Live preview of the app the user is building. Mirrors the post-refactor
      shell — a community rail (AppRail) plus a space sidebar (AppSidebar) — so
      what they see here matches where they land after onboarding. The typed
      community name and first space are reflected in real time. Decorative and
      non-interactive, except the account dropdown.
    -->
    <div class="flex h-full select-none">
      <!-- Community rail -->
      <div
        class="flex w-[50px] shrink-0 flex-col items-center border-r bg-surface-sidebar px-[11px] pb-3 pt-2.5"
      >
        <div class="mb-3 flex shrink-0 items-center justify-center">
          <span
            class="flex size-7 items-center justify-center rounded-[7px] bg-surface-base shadow-sm"
          >
            <GameplanLogo class="size-7 rounded-[7px]" />
          </span>
        </div>
        <div class="flex w-full flex-1 flex-col items-center border-t pt-3">
          <span
            class="relative flex size-7 items-center justify-center rounded-[7px] bg-surface-gray-4"
          >
            <span
              class="absolute -left-[11px] top-1/2 h-7 w-1 -translate-y-1/2 rounded-r-4 bg-surface-gray-8"
            />
            <span class="text-2xs-medium uppercase text-ink-gray-7">{{ communityInitials }}</span>
          </span>
        </div>
        <div
          class="mt-3 flex w-full flex-col items-center gap-0.5 border-t py-3 pointer-events-none"
        >
          <span v-for="icon in railShortcuts" :key="icon" class="grid size-7 place-items-center">
            <span :class="[icon, 'size-4 text-ink-gray-6']" />
          </span>
        </div>
        <UserDropdown>
          <template #trigger="{ open }">
            <button
              type="button"
              class="flex size-7 items-center justify-center rounded-full transition"
              :class="open ? '' : 'hover:opacity-90'"
            >
              <UserAvatar
                v-if="sessionUser.name"
                :user="sessionUser.name"
                size="md"
                class="size-7"
              />
            </button>
          </template>
        </UserDropdown>
      </div>
      <!-- Space sidebar -->
      <div class="pointer-events-none flex w-56 flex-col bg-surface-sidebar">
        <div class="flex shrink-0 items-center gap-2 p-2">
          <span class="flex size-7 items-center justify-center rounded-[7px] bg-surface-gray-3">
            <span class="text-2xs-medium uppercase text-ink-gray-5">{{ communityInitials }}</span>
          </span>
          <span class="flex-1 truncate text-base-medium text-ink-gray-8">
            {{ previewCommunityTitle }}
          </span>
          <span class="lucide-chevron-down size-4 shrink-0 text-ink-gray-5" />
        </div>
        <div class="px-2 pt-0.5">
          <div class="flex h-7 items-center pl-2 text-base text-ink-gray-5">Spaces</div>
          <div class="mt-0.5">
            <div
              class="flex h-7 items-center rounded-4 bg-surface-elevation-3 pl-2 text-ink-gray-8 shadow-sm"
            >
              <SpaceIcon v-if="space.icon" :icon="space.icon" class="size-4 shrink-0" />
              <span v-else class="lucide-hash size-4 shrink-0 text-ink-gray-5" />
              <span class="ml-2 flex-1 truncate text-sm">{{ previewSpaceTitle }}</span>
            </div>
          </div>
        </div>
      </div>
    </div>
    <div class="flex min-w-0 flex-1">
      <div class="flex min-w-0 flex-1 overflow-hidden border-l bg-surface-base">
        <ScrollArea class="block min-h-0 flex-1" viewport-class="isolate bg-surface-base">
          <div class="body-container pt-14 pb-14">
            <div class="max-w-xl mx-auto">
              <div class="text-4xl-semibold text-ink-gray-8">Welcome to Gameplan</div>

              <div class="mt-2 pt-8 border-t">
                <h2 class="text-base-medium text-ink-gray-8 mb-2">Name your community</h2>
                <p class="text-p-sm text-ink-gray-6">
                  A community is the top-level home for your team. All of your spaces and
                  discussions live inside it.
                </p>
                <div class="mt-6">
                  <FormControl
                    type="text"
                    class="w-full"
                    placeholder="Acme Inc, My Company, ..."
                    id="new-community-name"
                    :modelValue="community"
                    @update:modelValue="
                      (value) => (community = value.length <= 50 ? value : value.slice(0, 50))
                    "
                    maxlength="50"
                    description="Give your community a short and descriptive name"
                  >
                    <template #suffix>
                      <span class="text-ink-gray-5 text-sm">{{ 50 - community.length }}</span>
                    </template>
                  </FormControl>
                </div>
              </div>

              <div class="mt-8 border-t pt-8">
                <h2 class="text-base-medium text-ink-gray-8 mb-2">Create your first space</h2>
                <p class="text-p-sm text-ink-gray-6">
                  A space is where your discussions live. Create one for a project, team, or any
                  topic you want to discuss and organize.
                </p>
                <div class="mt-6 space-y-2">
                  <div class="space-x-2 flex items-start w-full">
                    <IconPicker v-model="space.icon" v-slot="{ togglePopover }">
                      <Button @click="togglePopover()">
                        <template #icon>
                          <SpaceIcon v-if="space.icon" :icon="space.icon" class="size-4" />
                          <span v-else class="lucide-plus h-4 w-4" />
                        </template>
                      </Button>
                    </IconPicker>
                    <div class="w-full">
                      <FormControl
                        type="text"
                        class="w-full"
                        placeholder="Townhall, Engineering, Marketing"
                        id="new-space-name"
                        :modelValue="space.title"
                        @update:modelValue="
                          (value) => (space.title = value.length <= 50 ? value : value.slice(0, 50))
                        "
                        maxlength="50"
                        description="Give your space a short and descriptive name"
                      >
                        <template #suffix>
                          <span class="text-ink-gray-5 text-sm">
                            {{ 50 - space.title.length }}
                          </span>
                        </template>
                      </FormControl>
                    </div>
                  </div>
                </div>
              </div>
              <div class="mt-8 border-t pt-8">
                <h3 class="text-base-medium text-ink-gray-8 mb-2">Invite people</h3>
                <p class="text-sm text-ink-gray-6">
                  Add email addresses of people you'd like to invite to this community
                </p>
                <div class="mt-3">
                  <FormControl
                    type="textarea"
                    v-model="emailInput"
                    placeholder="jane@example.com, mary@example.com, ..."
                    :rows="3"
                    class="w-full"
                    @blur="validateEmails(emailInput)"
                    description="Separate multiple email addresses with commas or new lines"
                  />
                  <p v-if="emailError" class="text-xs text-red-600 mt-1">
                    {{ emailError }}
                  </p>
                </div>
              </div>
              <div class="mt-4">
                <ErrorMessage :message="errorMessage" />
              </div>
              <div class="mt-8 flex justify-end">
                <Button
                  variant="solid"
                  :loading="onboarding.loading"
                  :disabled="!community || !space.title"
                  @click="submit"
                >
                  Continue
                </Button>
              </div>
            </div>
          </div>
        </ScrollArea>
      </div>
    </div>
  </div>
</template>
<script setup lang="ts">
import { computed, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useCall, ScrollArea } from 'frappe-ui'
import GameplanLogo from '@/components/GameplanLogo.vue'
import IconPicker from '@/components/IconPicker.vue'
import SpaceIcon from '@/components/SpaceIcon.vue'
import UserAvatar from '@/components/UserAvatar.vue'
import UserDropdown from '@/components/UserDropdown.vue'
import { joinedSpaces, spaces } from '@/data/spaces'
import { communities } from '@/data/communities'
import { communityState } from '@/data/communityState'
import { useSessionUser } from '@/data/users'

const community = ref('')
const space = reactive({
  title: '',
  icon: '',
})
const emailInput = ref('')
const emailError = ref('')

const router = useRouter()
const sessionUser = useSessionUser()

// Live preview labels for the rail/sidebar mock; fall back to neutral
// placeholders so the preview is never blank before the user types.
const previewCommunityTitle = computed(() => community.value.trim() || 'Your community')
const previewSpaceTitle = computed(() => space.title.trim() || 'Your first space')

// Mirror CommunityImage's initials so the rail avatar matches the real app.
const communityInitials = computed(() => {
  const words = previewCommunityTitle.value.split(/\s+/).filter(Boolean)
  if (words.length > 1) {
    return words
      .slice(0, 2)
      .map((word) => word[0])
      .join('')
      .toUpperCase()
  }
  return previewCommunityTitle.value.slice(0, 2).toUpperCase()
})

// Bottom-of-rail shortcuts shown in the real AppRail (Search, People,
// Notifications, Drafts). Decorative only.
const railShortcuts = ['lucide-search', 'lucide-users-2', 'lucide-bell', 'lucide-pencil-line']

const validateEmails = (emails: string) => {
  const emailList = emails
    .split(/[\n,]/)
    .map((e) => e.trim())
    .filter((e) => e)
  const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
  const invalidEmails = emailList.filter((email) => !emailRegex.test(email.trim()))
  if (invalidEmails.length) {
    emailError.value = `Invalid email(s): ${invalidEmails.join(', ')}`
    return false
  }
  emailError.value = ''
  return true
}

type OnboardingParams = {
  community: string
  space: string
  icon: string
  emails: string[]
}

type OnboardingResult = {
  team: string
  space: string
}

const onboarding = useCall<OnboardingResult, OnboardingParams>({
  url: '/api/v2/method/gameplan.api.onboarding',
  method: 'POST',
  immediate: false,
  beforeSubmit() {
    if (!community.value) {
      throw new Error('Please enter a community name')
    }
    if (!space.title) {
      throw new Error('Please enter a space name')
    }
  },
  onSuccess(result) {
    communityState.change(result.team)
    Promise.all([communities.reload(), spaces.reload(), joinedSpaces.reload()]).then(() => {
      router.replace({
        name: 'Discussions',
        params: { communityId: result.team },
      })
    })
  },
})

// A `beforeSubmit` throw only rejects `submit()`; it no longer lands in
// `onboarding.error`. Hold the validation message here so the same
// ErrorMessage can show it.
const validationError = ref('')

// Validation wins while it is set, because no request runs in that case and
// `onboarding.error` would still hold the previous failure.
const errorMessage = computed(() => validationError.value || onboarding.error || undefined)

async function submit() {
  validationError.value = ''
  try {
    await onboarding.submit({
      community: community.value,
      space: space.title,
      icon: space.icon,
      emails: emailInput.value.split(/[\n,]/),
    })
  } catch (error) {
    validationError.value = error instanceof Error ? error.message : String(error)
  }
}
</script>
