/** Fan-out batch tracking for the chat: the durable source of truth is the
 * Builder AI Batch doc (polled), nudged live by ai_chat_progress task events.
 * Used by the editor chat to render the task-group card for a
 * spawn_parallel_agents turn. */

import { createResource } from "frappe-ui";
import { ref, type Ref } from "vue";

export interface BatchState {
	batchId: string;
	status: string;
	projectFolder: string | null;
	total: number;
	completed: number;
	failed: number;
	tasks: Array<{
		row: string;
		title: string;
		page: string | null;
		status: string;
		error?: string;
		preview?: string | null;
	}>;
}

const POLL_MS = 2500;

export class BatchTracker {
	batches: Ref<Record<string, BatchState>> = ref({});
	private pollTimers: Record<string, ReturnType<typeof setInterval>> = {};

	/** Start (or resume after a reload) tracking a batch. Safe to call repeatedly. */
	track(batchId: string, seed?: Partial<BatchState>) {
		if (!batchId) return;
		if (seed && !this.batches.value[batchId]) {
			this.batches.value[batchId] = {
				batchId,
				status: "running",
				projectFolder: null,
				total: 0,
				completed: 0,
				failed: 0,
				tasks: [],
				...seed,
			};
		}
		this.poll(batchId);
	}

	private poll(batchId: string) {
		if (this.pollTimers[batchId]) return;
		const tick = async () => {
			try {
				const res: any = await createResource({ url: "builder.ai.api.get_ai_batch_status" }).submit({
					batch_id: batchId,
				});
				this.batches.value[batchId] = {
					batchId,
					status: res.status,
					projectFolder: res.project_folder || null,
					total: res.total_tasks,
					completed: res.completed_tasks,
					failed: res.failed_tasks,
					tasks: res.tasks || [],
				};
				if (["done", "failed", "cancelled"].includes(res.status)) this.stop(batchId);
			} catch {
				/* transient */
			}
		};
		tick();
		this.pollTimers[batchId] = setInterval(tick, POLL_MS);
	}

	async cancel(batchId: string) {
		await createResource({ url: "builder.ai.api.cancel_ai_batch", method: "POST" })
			.submit({ batch_id: batchId })
			.catch(() => null);
	}

	async publish(batchId: string): Promise<any> {
		return createResource({ url: "builder.ai.api.publish_site_batch", method: "POST" }).submit({
			batch_id: batchId,
		});
	}

	private stop(batchId: string) {
		if (!this.pollTimers[batchId]) return;
		clearInterval(this.pollTimers[batchId]);
		delete this.pollTimers[batchId];
	}

	stopAll() {
		Object.keys(this.pollTimers).forEach((id) => this.stop(id));
	}
}
