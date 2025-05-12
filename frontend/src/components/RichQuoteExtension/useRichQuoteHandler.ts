import { nextTick, Ref } from 'vue'
import { Editor } from '@tiptap/core'

interface CommentsAreaInstance {
  editorObject?: Editor
  openCommentBox?: () => void
  getCommentContentElement?: (id: string) => HTMLElement | null | undefined
  highlightComment?: (id: string) => void
  scrollToCommentById?: (id: string) => void
}

export function useRichQuoteHandler(
  commentsArea: Ref<CommentsAreaInstance | null>,
  mainPostContentEl: Ref<HTMLElement | null>,
) {
  const handleRichQuote = async (html: string, { id, author }: { id: string; author: string }) => {
    if (!html || typeof html !== 'string' || html.trim() === '') {
      console.warn('HTML content for rich quote is empty or invalid.')
      return
    }

    const openCommentBox = commentsArea.value?.openCommentBox
    if (openCommentBox) {
      openCommentBox()
    }

    await nextTick()

    const editor = commentsArea.value?.editorObject
    if (!editor) {
      console.error('Editor instance (commentsArea.value.editorObject) not found.')
      return
    }

    let html_ = `<blockquote data-rich-quote-id="${id}" data-author="${author}">${html}</blockquote><p></p>`
    editor.chain().focus().insertContent(html_).run()
  }

  const handleRichQuoteClick = (payload: { quoteId: string; content: string; author: string }) => {
    if (!payload || !payload.quoteId || !payload.content) {
      console.warn('Rich quote click payload, id, or content is missing.')
      return
    }

    const [type, idValue] = payload.quoteId.split(':')

    if (type === 'comment') {
      const commentContentElement = commentsArea.value?.getCommentContentElement?.(idValue)

      if (commentContentElement instanceof HTMLElement) {
        if (findElementByContentAndScroll(commentContentElement, payload.content)) {
          commentsArea.value?.highlightComment?.(idValue)
          return
        }
        console.warn(
          `Could not find specific content matching "${payload.content.substring(0, 50)}..." in comment ${idValue}. Scrolling to comment container.`,
        )
      } else if (commentContentElement === null) {
        console.warn(
          `Comment element for ID ${idValue} not found. Scrolling to comment by ID as fallback.`,
        )
      } else {
        console.warn(
          'commentsArea.value.getCommentContentElement is not available. Scrolling to comment by ID as fallback.',
        )
      }
      if (commentsArea.value && typeof commentsArea.value.scrollToCommentById === 'function') {
        commentsArea.value.scrollToCommentById(idValue)
      } else {
        console.warn(
          'commentsArea ref or scrollToCommentById method is not available. Cannot scroll to comment.',
          idValue,
        )
      }
    } else if (type === 'discussion') {
      if (mainPostContentEl.value) {
        if (findElementByContentAndScroll(mainPostContentEl.value, payload.content)) {
          return
        }
        console.warn(
          `Could not find specific content matching "${payload.content.substring(0, 50)}..." in main post. Scrolling to post container.`,
        )
        mainPostContentEl.value.scrollIntoView({ behavior: 'smooth', block: 'start' })
      } else {
        console.warn('mainPostContentEl ref is not available. Cannot scroll to discussion post.')
      }
    } else {
      console.warn('Unknown rich quote type:', type)
    }
  }

  return {
    handleRichQuote,
    handleRichQuoteClick,
  }
}

function scrollAndHighlight(element: HTMLElement) {
  element.scrollIntoView({ behavior: 'smooth', block: 'center' })
  element.classList.add('highlighted-quote-target')
  setTimeout(() => {
    element.classList.remove('highlighted-quote-target')
  }, 2500)
}

function findElementByContentAndScroll(container: HTMLElement, targetContent: string): boolean {
  const trimmedTarget = targetContent.trim()
  if (!trimmedTarget) return false

  // Strategy 1: Match exact outerHTML
  const elements = Array.from(container.getElementsByTagName('*')) as HTMLElement[]
  for (const el of elements) {
    if (el.outerHTML.trim() === trimmedTarget) {
      scrollAndHighlight(el)
      return true
    }
  }

  // Strategy 2: Match plain text within a text node
  const isPlainText = !/<[a-z][\s\S]*>/i.test(trimmedTarget)
  if (isPlainText) {
    const walker = document.createTreeWalker(container, NodeFilter.SHOW_TEXT, {
      acceptNode: (node) => {
        if (node.nodeType === Node.TEXT_NODE && node.textContent?.trim().includes(trimmedTarget)) {
          return NodeFilter.FILTER_ACCEPT
        }
        return NodeFilter.FILTER_REJECT
      },
    })

    let bestTextNodeParent: HTMLElement | null = null
    let currentNode
    while ((currentNode = walker.nextNode())) {
      if (currentNode.parentElement) {
        if (!bestTextNodeParent || bestTextNodeParent.contains(currentNode.parentElement)) {
          bestTextNodeParent = currentNode.parentElement
          if (currentNode.textContent?.trim() === trimmedTarget) {
            break // Exact text match found
          }
        }
      }
    }
    if (bestTextNodeParent) {
      scrollAndHighlight(bestTextNodeParent)
      return true
    }
  }

  // Strategy 3: Match HTML string within innerHTML
  if (!isPlainText) {
    // Find deepest element containing the target HTML
    let deepestMatch: HTMLElement | null = null
    let maxDepth = -1

    function findRecursive(currentElement: HTMLElement, depth: number) {
      if (currentElement.innerHTML.includes(trimmedTarget)) {
        if (depth > maxDepth) {
          maxDepth = depth
          deepestMatch = currentElement
        }
      }
      for (let i = 0; i < currentElement.children.length; i++) {
        findRecursive(currentElement.children[i] as HTMLElement, depth + 1)
      }
    }
    findRecursive(container, 0)

    if (deepestMatch) {
      scrollAndHighlight(deepestMatch)
      return true
    }
  }

  return false
}
