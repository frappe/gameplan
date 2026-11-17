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
        <div class="flex w-full flex-col items-center gap-0.5 border-t py-3 pointer-events-none">
          <span v-for="icon in railShortcuts" :key="icon" class="grid size-7 place-items-center">
            <span :class="[icon, 'size-4 text-ink-gray-6']" />
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
          <div class="mt-0.5 space-y-0.5">
            <div
              v-for="previewSpace in previewSpaces"
              :key="previewSpace.key"
              class="flex h-7 items-center rounded-4 pl-2"
              :class="
                previewSpace.isNew
                  ? 'bg-surface-elevation-3 text-ink-gray-8 shadow-sm'
                  : 'text-ink-gray-7'
              "
            >
              <SpaceIcon
                v-if="previewSpace.icon"
                :icon="previewSpace.icon"
                class="size-4 shrink-0"
              />
              <span v-else class="lucide-hash size-4 shrink-0 text-ink-gray-5" />
              <span class="ml-2 flex-1 truncate text-sm">{{ previewSpace.title }}</span>
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
              <div class="text-3xl-semibold text-ink-gray-8">Welcome to Gameplan</div>

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
                    @update:modelValue="(value: string) => (community = value.slice(0, NAME_LIMIT))"
                    :maxlength="NAME_LIMIT"
                  >
                    <template v-if="charactersLeft(community) <= 10" #suffix>
                      <span class="text-ink-gray-5 text-sm">{{ charactersLeft(community) }}</span>
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
                      <Tooltip text="Choose icon">
                        <Button aria-label="Choose icon" @click="togglePopover()">
                          <template #icon>
                            <SpaceIcon v-if="space.icon" :icon="space.icon" class="size-4" />
                            <span v-else class="lucide-smile-plus size-4" />
                          </template>
                        </Button>
                      </Tooltip>
                    </IconPicker>
                    <div class="w-full">
                      <FormControl
                        type="text"
                        class="w-full"
                        placeholder="Townhall, Engineering, Marketing"
                        id="new-space-name"
                        :modelValue="space.title"
                        @update:modelValue="
                          (value: string) => (space.title = value.slice(0, NAME_LIMIT))
                        "
                        :maxlength="NAME_LIMIT"
                      >
                        <template v-if="charactersLeft(space.title) <= 10" #suffix>
                          <span class="text-ink-gray-5 text-sm">
                            {{ charactersLeft(space.title) }}
                          </span>
                        </template>
                      </FormControl>
                    </div>
                  </div>
                </div>
              </div>
              <div class="mt-8 border-t pt-8">
                <h3 class="text-base-medium text-ink-gray-8 mb-2">Invite people</h3>
                <p class="text-p-sm text-ink-gray-6">
                  Add the email addresses of people you'd like to invite to this community.
                </p>
                <div class="mt-6">
                  <EmailListInput ref="emailListInput" v-model="emailInput" />
                </div>
              </div>
              <div class="mt-8 flex items-center justify-end gap-3">
                <ErrorMessage class="mr-auto" role="alert" :message="errorMessage" />
                <Button
                  variant="solid"
                  :loading="onboarding.loading"
                  :disabled="!community.trim() || !space.title.trim()"
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
import { computed, reactive, ref, useTemplateRef } from 'vue'
import { useRouter } from 'vue-router'
import { FormControl, ScrollArea, Tooltip, useCall } from 'frappe-ui'
import EmailListInput, { parseEmailList } from '@/components/EmailListInput.vue'
import GameplanLogo from '@/components/GameplanLogo.vue'
import IconPicker from '@/components/IconPicker.vue'
import SpaceIcon from '@/components/SpaceIcon.vue'
import UserAvatar from '@/components/UserAvatar.vue'
import UserDropdown from '@/components/UserDropdown.vue'
import { joinedSpaces, spaces } from '@/data/spaces'
import { communities } from '@/data/communities'
import { communityState } from '@/data/communityState'
import { useSessionUser } from '@/data/users'
import { errorText } from '@/utils'

const NAME_LIMIT = 50

const community = ref('')
const space = reactive({
  title: '',
  icon: '',
})
const emailInput = ref('')
const emailListInput = useTemplateRef('emailListInput')

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

// The shortcuts at the top of the real rail, under the logo (Search, People,
// Notifications, Drafts). Decorative only.
const railShortcuts = ['lucide-search', 'lucide-users-2', 'lucide-bell', 'lucide-pencil-line']

// Setup also creates a "General" space. The sidebar lists spaces by title.
const previewSpaces = computed(() => {
  const spaces = [
    { key: 'new', title: previewSpaceTitle.value, icon: space.icon, isNew: true },
    { key: 'general', title: 'General', icon: '', isNew: false },
  ]
  if (previewSpaceTitle.value === 'General') spaces.pop()
  return spaces.sort((a, b) => a.title.localeCompare(b.title))
})

function charactersLeft(value: string) {
  return NAME_LIMIT - value.length
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

// The request's own failure, as a sentence. Invalid emails show under the email box.
const errorMessage = computed(() =>
  onboarding.error ? errorText(onboarding.error, 'Could not set up Gameplan. Try again.') : '',
)

function submit() {
  if (!emailListInput.value?.validate()) return
  onboarding
    .submit({
      community: community.value.trim(),
      space: space.title.trim(),
      icon: space.icon,
      emails: parseEmailList(emailInput.value).emails,
    })
    .catch(() => {})
}
</script>
