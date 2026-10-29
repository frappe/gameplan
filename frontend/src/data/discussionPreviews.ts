import { call } from 'frappe-ui'

export interface DiscussionPreview {
  title: string
  project: string
  creation: string
  snippet: string
}

const cache = new Map<string, Promise<DiscussionPreview | null>>()

export function loadDiscussionPreview(name: string) {
  if (!cache.has(name)) {
    cache.set(
      name,
      call('frappe.client.get_value', {
        doctype: 'GP Discussion',
        filters: { name },
        fieldname: ['title', 'project', 'creation', 'content'],
      })
        .then((doc: (Omit<DiscussionPreview, 'snippet'> & { content?: string }) | null) =>
          doc?.title
            ? {
                ...doc,
                snippet:
                  new DOMParser()
                    .parseFromString(doc.content || '', 'text/html')
                    .body.textContent?.trim() || '',
              }
            : null,
        )
        .catch(() => null),
    )
  }
  return cache.get(name)!
}
