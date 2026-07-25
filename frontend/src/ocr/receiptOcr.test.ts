import { describe, expect, it } from "vitest";

import {
  extractPurchasedAt,
  extractShopName,
  extractTotalAmount,
} from "./receiptOcr";

describe("receipt OCR field extraction", () => {
  it("removes OCR punctuation before the shop name", () => {
    expect(
      extractShopName([
        { text: "= FamilyMart", confidence: 91 },
        { text: "京都府京都市下京区五条通", confidence: 98 },
      ]),
    ).toBe("FamilyMart");
  });

  it("extracts a spaced Japanese receipt date", () => {
    expect(extractPurchasedAt("2026年 6月12日 (金) 9:10")).toBe("2026-06-12");
  });

  it("uses a repeated tax-inclusive amount when the total label is unreadable", () => {
    const text = [
      "= B01 ¥746",
      "8 % T H ¥746)",
      "内 消費 税 等 ¥55)",
      "51) ¥5,050",
      "koh ¥4,304",
    ].join("\n");

    expect(extractTotalAmount(text)).toBe(746);
  });

  it("handles a misrecognized total label and the following tax-base line", () => {
    const text = [
      "含- 言二 ギ\\7スス",
      "( 8%対象 \\746)",
      "内消費税等 \\55)",
    ].join("\n");

    expect(extractTotalAmount(text)).toBe(746);
  });

  it("does not mistake payment or change for the total", () => {
    const text = [
      "合 計 ¥746",
      "お預り ¥5,050",
      "お釣り ¥4,304",
    ].join("\n");

    expect(extractTotalAmount(text)).toBe(746);
  });
});
