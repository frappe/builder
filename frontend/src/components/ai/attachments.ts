import { toast } from "frappe-ui";
import { computed, ref } from "vue";

/** Per message. The server's cap is their sum: six images and one video's frames. */
const LIMITS = { image: 6, video: 1 };
const MAX_FRAMES = 8;
const SECONDS_PER_FRAME = 3;
// Past this, eight frames are too far apart to follow what happens between them.
const MAX_VIDEO_SECONDS = 120;
// Claude reads up to 2576px, but an image's tokens grow with its area: this keeps a
// screenshot near 1.8k tokens and a full message well inside one request.
const MAX_EDGE = 1568;
const PASS_THROUGH_BYTES = 1024 * 1024;
const PASS_THROUGH_TYPES = ["image/png", "image/jpeg", "image/webp", "image/gif"];
const LOAD_TIMEOUT = 15000;

type Kind = keyof typeof LIMITS;

/** One image the model sees: a picked image, or a frame of a video at `at` seconds. */
export interface AttachedImage {
	data: string;
	video?: string;
	at?: number;
}

export interface Attachment {
	id: string;
	kind: Kind;
	name: string;
	images: AttachedImage[];
}

/** A sent message's attachments as stored: the server saves `url` as a file. */
interface SentImage {
	url: string;
	video?: string;
}

export interface AttachmentChip {
	key: string;
	kind: Kind;
	thumb: string;
}

/** The images and video attached to the message being written. A video becomes
 * frames here, in the browser: every vision model reads images, few read video. */
export class ChatAttachments {
	readonly items = ref<Attachment[]>([]);
	readonly reading = computed(() => this.items.value.some((a) => !a.images.length));

	/** Attach what fits; one warning per kind of file left out, however many were. */
	add = (files: File[]) => {
		let unsupported = false;
		let over = false;
		for (const file of files) {
			const kind = kindOf(file);
			if (!kind) unsupported = true;
			else if (this.count(kind) >= LIMITS[kind]) over = true;
			else this.start(file, kind);
		}
		if (over) toast.error(`Attach up to ${LIMITS.image} images and ${LIMITS.video} video per message`);
		if (unsupported) toast.error("Only images and videos can be attached");
	};

	remove = (id: string) => {
		this.items.value = this.items.value.filter((a) => a.id !== id);
	};

	/** Everything attached, emptied out for sending. */
	take(): AttachedImage[] {
		const images = this.items.value.flatMap((a) => a.images);
		this.items.value = [];
		return images;
	}

	private count(kind: Kind): number {
		return this.items.value.filter((a) => a.kind === kind).length;
	}

	/** Listed at once, empty, so the chip shows while a video is read. */
	private start(file: File, kind: Kind) {
		const id = `${Date.now()}-${Math.random()}`;
		this.items.value.push({ id, kind, name: file.name || `pasted-${kind}`, images: [] });
		this.read(id, file, kind);
	}

	private async read(id: string, file: File, kind: Kind) {
		try {
			const images = kind === "video" ? await videoFrames(file) : [{ data: await imageData(file) }];
			const item = this.items.value.find((a) => a.id === id);
			if (item) item.images = images;
		} catch (error) {
			this.remove(id);
			toast.error(error instanceof AttachError ? error.message : unreadable(file, kind));
		}
	}
}

/** A file read fine but can't be attached; its message is for the user. */
class AttachError extends Error {}

function unreadable(file: File, kind: Kind): string {
	return kind === "video" ? `Couldn't read ${file.name}. Try an MP4 or WebM.` : `Couldn't read ${file.name}`;
}

/** Chips for a sent message: one per image, one per video. */
export function sentAttachmentChips(metadata?: Record<string, any>): AttachmentChip[] {
	if (metadata?.attachedImageUrl) return [{ key: "image", kind: "image", thumb: metadata.attachedImageUrl }];
	const chips: AttachmentChip[] = [];
	(metadata?.attachedImages as SentImage[] | undefined)?.forEach((image, i) => {
		const key = image.video ? `video:${image.video}` : `image:${i}`;
		if (!chips.some((c) => c.key === key))
			chips.push({ key, kind: image.video ? "video" : "image", thumb: image.url });
	});
	return chips;
}

export function sentImages(images: AttachedImage[]): SentImage[] {
	return images.map(({ data, ...rest }) => ({ url: data, ...rest }));
}

function kindOf(file: File): Kind | null {
	if (file.type.startsWith("image/")) return "image";
	if (file.type.startsWith("video/")) return "video";
	return null;
}

async function imageData(file: File): Promise<string> {
	const url = URL.createObjectURL(file);
	try {
		const img = new Image();
		img.src = url;
		await loaded(img, "load");
		const small = Math.max(img.naturalWidth, img.naturalHeight) <= MAX_EDGE;
		if (small && file.size <= PASS_THROUGH_BYTES && PASS_THROUGH_TYPES.includes(file.type)) {
			return await fileData(file);
		}
		return encode(img, img.naturalWidth, img.naturalHeight, "image/webp");
	} finally {
		URL.revokeObjectURL(url);
	}
}

/** Evenly spaced frames, a frame for every few seconds up to MAX_FRAMES, each
 * taken mid-span so neither a black first frame nor the last one is picked. */
async function videoFrames(file: File): Promise<AttachedImage[]> {
	const url = URL.createObjectURL(file);
	const video = document.createElement("video");
	video.muted = true;
	video.preload = "auto";
	try {
		video.src = url;
		await loaded(video, "loadeddata");
		const duration = await durationOf(video);
		if (duration > MAX_VIDEO_SECONDS) {
			const limit = `${MAX_VIDEO_SECONDS / 60} minutes`;
			throw new AttachError(`${file.name} is ${clock(duration)} long. Attach a video up to ${limit}.`);
		}
		const count =
			duration > 0 ? Math.min(MAX_FRAMES, Math.max(3, Math.ceil(duration / SECONDS_PER_FRAME))) : 1;
		const frames: AttachedImage[] = [];
		for (let i = 0; i < count; i++) {
			const at = duration > 0 ? ((i + 0.5) * duration) / count : 0;
			video.currentTime = at;
			await loaded(video, "seeked");
			const data = encode(video, video.videoWidth, video.videoHeight, "image/jpeg");
			frames.push({ data, video: file.name || "video", at: Math.round(at * 10) / 10 });
		}
		return frames;
	} finally {
		video.removeAttribute("src");
		URL.revokeObjectURL(url);
	}
}

/** A MediaRecorder webm (most screen recordings) reports no duration until the
 * browser has seeked to its end. */
async function durationOf(video: HTMLVideoElement): Promise<number> {
	if (Number.isFinite(video.duration)) return video.duration;
	video.currentTime = Number.MAX_SAFE_INTEGER;
	await loaded(video, "seeked");
	return Number.isFinite(video.duration) ? video.duration : 0;
}

function clock(seconds: number): string {
	const whole = Math.round(seconds);
	return `${Math.floor(whole / 60)}:${String(whole % 60).padStart(2, "0")}`;
}

function encode(source: CanvasImageSource, width: number, height: number, type: string): string {
	const scale = Math.min(1, MAX_EDGE / Math.max(width, height, 1));
	const canvas = document.createElement("canvas");
	canvas.width = Math.max(1, Math.round(width * scale));
	canvas.height = Math.max(1, Math.round(height * scale));
	canvas.getContext("2d")!.drawImage(source, 0, 0, canvas.width, canvas.height);
	const data = canvas.toDataURL(type, 0.85);
	// Safari can't encode WebP and hands back a far larger PNG
	return data.startsWith(`data:${type}`) ? data : canvas.toDataURL("image/jpeg", 0.85);
}

function loaded(el: HTMLElement, event: string): Promise<void> {
	return new Promise((resolve, reject) => {
		const timer = setTimeout(() => done(new Error(`${event} timed out`)), LOAD_TIMEOUT);
		const ok = () => done();
		const fail = () => done(new Error(`${event} failed`));
		function done(error?: Error) {
			clearTimeout(timer);
			el.removeEventListener(event, ok);
			el.removeEventListener("error", fail);
			if (error) reject(error);
			else resolve();
		}
		el.addEventListener(event, ok);
		el.addEventListener("error", fail);
	});
}

function fileData(file: File): Promise<string> {
	return new Promise((resolve, reject) => {
		const reader = new FileReader();
		reader.onload = () => resolve(reader.result as string);
		reader.onerror = () => reject(reader.error);
		reader.readAsDataURL(file);
	});
}
