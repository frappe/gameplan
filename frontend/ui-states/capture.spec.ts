import { mkdirSync, writeFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { test } from '@playwright/test'
import { createTestModel } from '@xstate/graph'
import type { EventObject } from 'xstate'
import type { AnyFlow as Flow, StateMeta } from './flow'
import { flows } from './flows'
import { describeMachine, writeManifest, type EdgeRecord, type FlowManifest } from './manifest'
import { OUT_DIR } from './playwright.config'
import { openScene, type Scene } from './scene'

const only = process.env.UI_STATES_FLOWS?.split(',').filter(Boolean)

// The canvas lays flows out in this order, whichever subset this run captures.
mkdirSync(OUT_DIR, { recursive: true })
writeFileSync(resolve(OUT_DIR, 'index.json'), JSON.stringify(flows.map((flow) => flow.id)))

for (const flow of flows) {
  if (only && !only.includes(flow.id)) continue
  test(flow.id, async ({ browser, baseURL }) => {
    if (!baseURL) throw new Error('baseURL is required')
    const manifest: FlowManifest = {
      id: flow.id,
      title: flow.title,
      source: flow.source,
      ...describeMachine(flow.machine),
      edges: [],
    }
    const paths = createTestModel(flow.machine).getShortestPaths()
    mkdirSync(resolve(OUT_DIR, flow.id), { recursive: true })
    for (const path of paths) {
      const scene = await openScene(browser, baseURL, flow.folderTitle ?? flow.title)
      try {
        await flow.enter(scene)
        let previous: string | null = null
        for (const step of path.steps) {
          const state = stateId(step.state.value)
          if (step.event.type !== 'xstate.init') {
            await runEvent(flow, scene, step.event)
            recordEdge(manifest.edges, previous as string, step.event.type, state)
          }
          await capture(flow, scene, manifest, state, previous, step.event.type)
          previous = state
        }
      } finally {
        await scene.close()
      }
    }
    writeManifest(OUT_DIR, manifest)
  })
}

function stateId(value: unknown): string {
  return typeof value === 'string' ? value : JSON.stringify(value)
}

async function runEvent(flow: Flow, scene: Scene, event: EventObject): Promise<void> {
  const run = flow.events[event.type as keyof typeof flow.events] as
    | ((scene: Scene, event: EventObject) => Promise<void>)
    | undefined
  if (!run) throw new Error(`${flow.id} has no step for event ${event.type}`)
  await run(scene, event)
}

function recordEdge(edges: EdgeRecord[], from: string, event: string, to: string): void {
  if (!edges.some((edge) => edge.from === from && edge.event === event && edge.to === to)) {
    edges.push({ from, event, to })
  }
}

/** Screenshots a state the first time a path reaches it. */
async function capture(
  flow: Flow,
  scene: Scene,
  manifest: FlowManifest,
  state: string,
  parent: string | null,
  via: string,
): Promise<void> {
  const record = manifest.states.find((candidate) => candidate.id === state)
  if (!record) throw new Error(`${flow.id} reached unknown state ${state}`)
  if (record.screenshot) return
  const meta = (flow.machine.states[state]?.meta ?? {}) as StateMeta
  await flow.settle?.[state]?.(scene)
  await scene.settle()
  record.parent = parent
  record.via = parent ? via : null
  if (meta.transient) return
  const file = `${flow.id}/${state}.png`
  const frame = flow.frame?.(scene, state) ?? null
  const options = {
    path: resolve(OUT_DIR, file),
    animations: 'disabled' as const,
    caret: 'hide' as const,
  }
  if (frame) await frame.screenshot(options)
  else await scene.page.screenshot(options)
  record.screenshot = file
}
