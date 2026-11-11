import type { Locator, Page } from "@playwright/test";
import type { AnyStateMachine, EventObject } from "xstate";
import type { Scene } from "./scene";

/**
 * One flow as an explicit state machine, plus the browser steps that
 * realise it. The machine says which screens exist and how they connect; the
 * capture run walks every path and screenshots each state once.
 *
 * State nodes carry `meta.description` for the canvas. `meta.transient`
 * marks a state too brief to screenshot reliably; it stays in the graph.
 */
export interface Flow<TEvent extends EventObject = EventObject> {
	id: string;
	title: string;
	/** Where the machine lives in the code today, explicit or implied. */
	source: string;
	machine: AnyStateMachine;
	/** What each path's own folder is called, as the breadcrumbs show it. Defaults to the title. */
	folderTitle?: string;
	/** Brings a fresh, signed-in page to the machine's initial state. */
	enter(scene: Scene): Promise<void>;
	events: {
		[K in TEvent["type"]]: (scene: Scene, event: Extract<TEvent, { type: K }>) => Promise<void>;
	};
	/** Waits for a state to be fully on screen before its screenshot. */
	settle?: Partial<Record<string, (scene: Scene) => Promise<void>>>;
	/** A region to screenshot instead of the viewport, for one state. */
	frame?(scene: Scene, state: string): Locator | null;
}

export interface StateMeta {
	description?: string;
	transient?: boolean;
}

/** A flow with its event types erased, as the capture run and the registry see it. */
export type AnyFlow = Flow<EventObject>;

export function defineFlow<TEvent extends EventObject>(flow: Flow<TEvent>): AnyFlow {
	return flow as unknown as AnyFlow;
}

/**
 * Presses the mouse on an empty part of the page's scroll area. When the first
 * mouse press on a page opens a frappe-ui Dropdown, a dialog opened from that
 * menu shows a focus ring on its X. A press that focuses the scroll area first
 * prevents it; a press on a part of the page that takes no focus does not.
 * Call this before opening such a menu.
 */
export async function pressEmpty(page: Page): Promise<void> {
	const point = await page.evaluate(() => {
		const candidates: [number, number][] = [[1400, 600], [1400, 300], [1400, 850]];
		const interactive =
			'a, button, input, textarea, select, label, [contenteditable], ' +
			'[role="button"], [role="link"], [role="menuitem"], [role="tab"], [role="radio"], [role="checkbox"], [role="combobox"]';
		return (
			candidates.find(([x, y]) => {
				const target = document.elementFromPoint(x, y);
				return target?.closest('[data-slot="scroll-area-viewport"]') && !target.closest(interactive);
			}) ?? null
		);
	});
	if (!point) throw new Error("No empty spot in the page's scroll area to press");
	await page.mouse.click(point[0], point[1]);
}
