import blockController from "@/utils/blockController";
import stylePreset from "@/data/stylePreset";

export const getPresetMap = () => {
    const presetName = blockController.getPresetStyle();
    const preset = stylePreset.data?.find((s: any) => s.style_name === presetName);
    return preset
        ? (typeof preset.style_map === "string" ? JSON.parse(preset.style_map) : preset.style_map)
        : null;
};