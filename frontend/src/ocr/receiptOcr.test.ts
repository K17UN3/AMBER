import { describe, expect, it } from "vitest";

import {
  calculateReceiptImageSize,
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

  it("does not use cash tendered or change when the total label is missing", () => {
    expect(extractTotalAmount("現金 5000\nお釣り 4200")).toBeNull();
    expect(extractTotalAmount("現金 ¥5,000\nお釣り ¥4,200")).toBeNull();
  });

  it("extracts a same-line total without a currency symbol", () => {
    expect(extractTotalAmount("合計 1280")).toBe(1280);
  });

  it("extracts a following-line total without a currency symbol", () => {
    expect(extractTotalAmount("合計\n1280")).toBe(1280);
  });
});

describe("receipt OCR image sizing", () => {
  it("limits both the longest side and total pixel count", () => {
    const size = calculateReceiptImageSize(8000, 6000);

    expect(Math.max(size.width, size.height)).toBeLessThanOrEqual(2200);
    expect(size.width * size.height).toBeLessThanOrEqual(4_000_000);
  });

  it("does not enlarge an image already within the limits", () => {
    expect(calculateReceiptImageSize(1200, 900)).toEqual({
      width: 1200,
      height: 900,
    });
  });
});
