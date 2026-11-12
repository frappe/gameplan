import type { Scene } from './scene'

/**
 * Lookups into the demo world (`gameplan/demo/world.md`), for flows that
 * need a record's name rather than its title.
 */

interface Row {
  name: string | number
}

/** The names of a community's spaces that are not archived. */
export async function spacesOf(scene: Scene, community: string): Promise<string[]> {
  const params = new URLSearchParams({
    filters: JSON.stringify({ team: community, archived_at: ['is', 'not set'] }),
    fields: '["name"]',
    limit_page_length: '0',
  })
  const response = await scene.admin.get(`/api/resource/GP%20Project?${params}`)
  if (!response.ok()) throw new Error(`Listing spaces of ${community} failed: ${response.status()}`)
  return ((await response.json()) as { data: Row[] }).data.map((row) => String(row.name))
}

/** Writes a reply as `as`, so it reaches the discussion's participants like a real one. */
export async function reply(
  scene: Scene,
  as: Parameters<Scene['insert']>[0],
  discussion: string,
  paragraphs: string[],
): Promise<{ name: string }> {
  return scene.insert(as, 'GP Comment', {
    reference_doctype: 'GP Discussion',
    reference_name: discussion,
    content: paragraphs.map((text) => `<p>${text}</p>`).join(''),
  })
}
