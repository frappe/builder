import { describe, expect, it } from "vitest";
import { typedCardAnswers } from "./cardAnswers";

describe("typed card answers", () => {
	it("retains colons, newlines and qualifications independent of the label", () => {
		const answer = "Poster, but change this: keep all prices in euros\nKeep my real logo.";
		expect(
			typedCardAnswers([{ id: "business", kind: "input", label: "Name: 品牌" }], {
				cardId: "card",
				answers: [{ fieldId: "business", value: answer }],
			}),
		).toEqual([{ question: "Name: 品牌", answer }]);
	});
	it("never guesses a structured answer from unrelated free text", () => {
		expect(typedCardAnswers([{ kind: "choices", label: "Direction" }])).toEqual([]);
	});
});
