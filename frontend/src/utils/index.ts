import { dayjsLocal, toast } from 'frappe-ui'

export function getImgDimensions(
  imgSrc: string,
): Promise<{ width: number; height: number; ratio: number }> {
  return new Promise((resolve) => {
    let img = new Image()
    img.onload = function () {
      let { width, height } = img
      resolve({ width, height, ratio: width / height })
    }
    img.src = imgSrc
  })
}

export function htmlToText(html: string): string {
  let tmp = document.createElement('div')
  tmp.innerHTML = html
  return tmp.textContent || tmp.innerText || ''
}

export async function copyToClipboard(text: string): Promise<void> {
  try {
    // Use modern Clipboard API if available
    if (navigator.clipboard && window.isSecureContext) {
      await navigator.clipboard.writeText(text)
      toast.success('Copied to clipboard')
      return
    }

    // Fallback for older browsers or non-secure contexts
    let textField = document.createElement('textarea')
    textField.value = text
    document.body.appendChild(textField)
    textField.focus()
    textField.select()
    document.execCommand('copy')
    textField.remove()
    toast.success('Copied to clipboard')
  } catch (error) {
    toast.error('Failed to copy to clipboard')
    console.error('Failed to copy text to clipboard:', error)
    throw error
  }
}

export function getScrollParent(node: HTMLElement | null): HTMLElement | null {
  if (node == null) {
    return null
  }

  if (node.scrollHeight > node.clientHeight) {
    return node
  } else {
    return getScrollParent(node.parentNode as HTMLElement)
  }
}

export function getRandomNumber(min: number, max: number): number {
  return Math.floor(Math.random() * (max - min + 1)) + min
}

export function getPlatform(): 'win' | 'mac' | 'linux' | undefined {
  let ua = navigator.userAgent.toLowerCase()
  if (ua.indexOf('win') > -1) {
    return 'win'
  } else if (ua.indexOf('mac') > -1) {
    return 'mac'
  } else if (ua.indexOf('x11') > -1 || ua.indexOf('linux') > -1) {
    return 'linux'
  }
}

export function relativeTimestamp(timestamp: string): string {
  if (dayjsLocal().diff(timestamp, 'day') < 3) {
    return dayjsLocal(timestamp).fromNow()
  }
  if (dayjsLocal().diff(timestamp, 'year') < 1) {
    return dayjsLocal(timestamp).format('D MMM')
  }
  return dayjsLocal(timestamp).format('D MMM YYYY')
}
