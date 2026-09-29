import type Block from "@/block";
import { getDataForKey, getParentProps, getPropValue } from "@/utils/helpers";

type ValueMap = Record<string, any>;

interface BlockValueContext {
	block: () => Block;
	data: () => ValueMap | null;
	componentData: () => ValueMap | null;
	defaultProps: () => BlockProps | null;
}

class BlockValueResolver {
	constructor(private context: BlockValueContext) {}

	private get block() {
		return this.context.block();
	}

	get hasValues() {
		return Boolean(
			this.context.data() ||
				this.context.defaultProps() ||
				Object.keys(this.block.getBlockProps()).length ||
				Object.keys(this.context.componentData() || {}).length,
		);
	}

	getDataValue(path: string) {
		return getDataForKey(this.context.data() || {}, path);
	}

	getComponentDataValue(path: string) {
		return getDataForKey(this.context.componentData() || {}, path);
	}

	getPropValue(name: string, block = this.block) {
		return getPropValue(
			name,
			block,
			(path) => this.getDataValue(path),
			this.context.defaultProps(),
			(path) => this.getComponentDataValue(path),
		);
	}	

	getResolvedProps() {
		const defaultProps = Object.fromEntries(
			Object.entries(this.context.defaultProps() || {}).map(([key, value]) => [key, value.value]),
		);
		const blockProps = Object.fromEntries(
			Object.keys(this.block.getBlockProps()).map((key) => [key, this.getPropValue(key)]),
		);
		const parentProps = Object.fromEntries(
			Object.entries(getParentProps(this.block)).map(([key, value]) => [
				key,
				this.getPropValue(key, value.block!),
			]),
		);

		return { ...parentProps, ...blockProps, ...defaultProps };
	}

	resolve(dataKey: BlockDataKey) {
		if (!dataKey.key) return undefined;
		if (dataKey.comesFrom === "props") {
			return this.getPropValue(dataKey.key);
		}
		if (dataKey.comesFrom === "componentData") {
			return this.getComponentDataValue(dataKey.key);
		}
		return this.getDataValue(dataKey.key);
	}

	applyDynamicValues(type: BlockDataKeyType, values: ValueMap) {
		if (!this.hasValues) return values;

		const dataKey = this.getPrimaryDataKey();
		if (dataKey.type === type && dataKey.property) {
			values[dataKey.property] = this.resolve(dataKey) ?? values[dataKey.property];
		}

		this.block
			.getDynamicValues()
			.filter((value) => value.type === type && value.property)
			.forEach((value) => {
				values[value.property!] = this.resolve(value) ?? values[value.property!];
			});

		return values;
	}

	isHiddenByVisibilityCondition() {
		const condition = this.block.getVisibilityCondition();
		if (!condition?.key) return false;
		return !Boolean(this.resolve(condition));
	}

	private getPrimaryDataKey(): BlockDataKey {
		const property = this.block.getDataKey("property");
		const type = this.block.getDataKey("type") || (property === "innerHTML" ? "key" : undefined);
		return {
			key: this.block.getDataKey("key"),
			type: type as BlockDataKey["type"],
			comesFrom: (this.block.getDataKey("comesFrom") || "dataScript") as BlockDataKey["comesFrom"],
			property,
		};
	}
}

export { BlockValueResolver };
export type { BlockValueContext };
