import { dayjsLocal } from 'frappe-ui'

export const dayjs = dayjsLocal

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

export function copyToClipboard(text: string): void {
  let textField = document.createElement('textarea')
  textField.value = text
  document.body.appendChild(textField)
  textField.select()
  document.execCommand('copy')
  textField.remove()
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
  if (dayjs().diff(timestamp, 'day') < 3) {
    return dayjs(timestamp).fromNow()
  }
  if (dayjs().diff(timestamp, 'year') < 1) {
    return dayjs(timestamp).format('D MMM')
  }
  return dayjs(timestamp).format('D MMM YYYY')
}
