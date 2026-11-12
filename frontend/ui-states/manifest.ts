import { mkdirSync, writeFileSync } from 'node:fs'
import { dirname, resolve } from 'node:path'
import type { AnyStateMachine } from 'xstate'
import type { StateMeta } from './flow'

/** What the canvas needs about one flow: its states, how they connect, and a screenshot per state. */
export interface FlowManifest {
  id: string
  title: string
  source: string
  initial: string
  states: StateRecord[]
  edges: EdgeRecord[]
}

export interface StateRecord {
  id: string
  description: string
  transient: boolean
  /** Path relative to the out dir, or null when the state was never captured. */
  screenshot: string | null
  /** The state the shortest path reached this one from, null for the initial state. */
  parent: string | null
  /** The event on that shortest path. */
  via: string | null
}

export interface EdgeRecord {
  from: string
  event: string
  to: string
}

export function describeMachine(
  machine: AnyStateMachine,
): Pick<FlowManifest, 'initial' | 'states'> {
  const states = Object.entries(machine.states).map(([id, node]) => {
    const meta = (node.meta ?? {}) as StateMeta
    return {
      id,
      description: meta.description ?? '',
      transient: meta.transient ?? false,
      screenshot: null,
      parent: null,
      via: null,
    }
  })
  return { initial: String(machine.config.initial ?? states[0]?.id ?? ''), states }
}

export function writeManifest(outDir: string, manifest: FlowManifest): void {
  const path = resolve(outDir, `${manifest.id}.json`)
  mkdirSync(dirname(path), { recursive: true })
  writeFileSync(path, JSON.stringify(manifest, null, '\t'))
}
