<template>
  <div class="space-y-10">
    <section v-for="release in changelogReleases" :key="release.version ?? 'unreleased'">
      <div class="mb-4 flex items-baseline gap-2 text-sm text-ink-gray-5">
        <span class="text-sm-medium text-ink-gray-7">
          {{ release.version ? `v${release.version}` : 'Next release' }}
        </span>
        <span v-if="release.date">{{ formatDate(release.date) }}</span>
      </div>

      <article v-for="entry in release.entries" :key="entry.id" class="mb-8 last:mb-0">
        <h3 class="mb-3 text-lg-semibold text-ink-gray-9">{{ entry.title }}</h3>
        <video
          v-if="entry.media?.kind === 'video'"
          :src="mediaUrl(entry.media)"
          class="mb-4 w-full rounded-lg border bg-surface-gray-1"
          autoplay
          loop
          muted
          playsinline
          :aria-label="entry.title"
        />
        <img
          v-else-if="entry.media"
          :src="mediaUrl(entry.media)"
          :alt="entry.title"
          class="mb-4 w-full rounded-lg border bg-surface-gray-1"
          loading="lazy"
        />
        <!-- The HTML comes from Markdown files in this repository, not from users. -->
        <div class="prose prose-v3 max-w-none text-ink-gray-7 prose-p:my-3" v-html="entry.html" />
      </article>
    </section>
  </div>
</template>

<script setup lang="ts">
import { dayjsLocal } from 'frappe-ui'
import { changelogReleases, type ChangelogEntry } from '@/data/changelog'
import { useTheme } from '@/utils/useTheme'

const { resolvedTheme } = useTheme()

function mediaUrl(media: NonNullable<ChangelogEntry['media']>) {
  return resolvedTheme.value === 'dark' && media.darkUrl ? media.darkUrl : media.url
}

function formatDate(date: string) {
  return dayjsLocal(date).format('D MMM YYYY')
}
</script>
