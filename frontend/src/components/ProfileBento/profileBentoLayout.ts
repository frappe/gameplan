import type { ProfileCardSize } from './types'

export interface ProfileBentoLayoutItem {
  id: string
  size: ProfileCardSize
  /**
   * Row span override, used by cards that grow beyond their declared size
   * (the expandable About card). Never shrinks a card below its declared rows.
   */
  rows?: number
}

export interface ProfileBentoLayoutRect {
  id: string
  left: number
  top: number
  width: number
  height: number
}

export interface ProfileBentoLayout {
  height: number
  rects: Map<string, ProfileBentoLayoutRect>
}

interface ProfileBentoUnits {
  columns: number
  rows: number
}

export const defaultProfileBentoColumns = 4

/**
 * Collapsed height of an expandable HTML card in the single-column flow layout,
 * where there is no packed cell height to collapse to.
 */
export const profileBentoFlowCollapsedHeight = 240

/**
 * Ceiling for an image card in the flow layout. A full-width square (1x1) is
 * inside the portrait aspect cap but still fills a phone screen, so the height
 * needs its own limit.
 */
export const profileBentoFlowImageMaxHeight = 320

export function createProfileBentoLayout(
  items: ProfileBentoLayoutItem[],
  containerWidth: number,
  gap: number,
  columns: number = defaultProfileBentoColumns,
): ProfileBentoLayout {
  let columnCount = normalizeColumns(columns)
  let cellSize = profileBentoCellSize(containerWidth, gap, columnCount)
  let occupied: boolean[][] = []
  let rects = new Map<string, ProfileBentoLayoutRect>()
  let rows = 0

  for (let item of items) {
    let units = cardUnits(item.size, columnCount, item.rows)
    let position = findOpenPosition(occupied, units, columnCount)
    occupyCells(occupied, position, units)
    rows = Math.max(rows, position.row + units.rows)
    rects.set(item.id, rectForItem(item.id, position, units, cellSize, gap))
  }

  return {
    height: rows ? rows * cellSize + (rows - 1) * gap : 0,
    rects,
  }
}

export function profileBentoCellSize(containerWidth: number, gap: number, columns: number) {
  let columnCount = normalizeColumns(columns)
  return Math.max(1, (containerWidth - gap * (columnCount - 1)) / columnCount)
}

/** Smallest whole row span whose packed height covers `height` pixels. */
export function profileBentoRowsForHeight(height: number, cellSize: number, gap: number) {
  if (height <= 0) return 1
  return Math.max(1, Math.ceil((height + gap) / (cellSize + gap)))
}

export function profileBentoHeightForRows(rows: number, cellSize: number, gap: number) {
  return rows > 0 ? rows * cellSize + (rows - 1) * gap : 0
}

export function profileBentoCardRows(size: ProfileCardSize) {
  return cardUnits(size, defaultProfileBentoColumns).rows
}

function normalizeColumns(columns: number) {
  return Math.max(1, Math.floor(columns) || 1)
}

function findOpenPosition(occupied: boolean[][], units: ProfileBentoUnits, columnCount: number) {
  for (let row = 0; ; row++) {
    for (let column = 0; column <= columnCount - units.columns; column++) {
      if (hasOpenCells(occupied, row, column, units)) {
        return { row, column }
      }
    }
  }
}

function hasOpenCells(
  occupied: boolean[][],
  row: number,
  column: number,
  units: ProfileBentoUnits,
) {
  for (let rowOffset = 0; rowOffset < units.rows; rowOffset++) {
    for (let columnOffset = 0; columnOffset < units.columns; columnOffset++) {
      if (occupied[row + rowOffset]?.[column + columnOffset]) {
        return false
      }
    }
  }
  return true
}

function occupyCells(
  occupied: boolean[][],
  position: { row: number; column: number },
  units: ProfileBentoUnits,
) {
  for (let rowOffset = 0; rowOffset < units.rows; rowOffset++) {
    let row = (occupied[position.row + rowOffset] ||= [])
    for (let columnOffset = 0; columnOffset < units.columns; columnOffset++) {
      row[position.column + columnOffset] = true
    }
  }
}

function rectForItem(
  id: string,
  position: { row: number; column: number },
  units: ProfileBentoUnits,
  cellSize: number,
  gap: number,
): ProfileBentoLayoutRect {
  return {
    id,
    left: position.column * (cellSize + gap),
    top: position.row * (cellSize + gap),
    width: units.columns * cellSize + (units.columns - 1) * gap,
    height: units.rows * cellSize + (units.rows - 1) * gap,
  }
}

function cardUnits(
  size: ProfileCardSize,
  columnCount: number,
  rowsOverride?: number,
): ProfileBentoUnits {
  let units = {
    '1x1': { columns: 1, rows: 1 },
    '1x2': { columns: 1, rows: 2 },
    '2x1': { columns: 2, rows: 1 },
    '2x2': { columns: 2, rows: 2 },
    '4x1': { columns: 4, rows: 1 },
    '4x2': { columns: 4, rows: 2 },
  }[size]

  return {
    // A card wider than the grid would make `findOpenPosition`'s column bound
    // negative, so its inner loop never runs and the unbounded row loop spins
    // forever. Clamping keeps every card placeable at any column count.
    columns: Math.min(units.columns, columnCount),
    rows: rowsOverride ? Math.max(units.rows, Math.floor(rowsOverride)) : units.rows,
  }
}
