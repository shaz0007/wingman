import test from "node:test";
import assert from "node:assert";
import { formatSeconds, countWords, truncateToMaxWords, sanitizeText } from "../src/utils/formatters.ts";

test("formatSeconds formats single digit and multi-digit seconds correctly", () => {
  assert.strictEqual(formatSeconds(0), "00:00");
  assert.strictEqual(formatSeconds(9), "00:09");
  assert.strictEqual(formatSeconds(65), "01:05");
  assert.strictEqual(formatSeconds(3600), "60:00");
  assert.strictEqual(formatSeconds(-10), "00:00");
});

test("countWords returns correct word counts", () => {
  assert.strictEqual(countWords(""), 0);
  assert.strictEqual(countWords("   "), 0);
  assert.strictEqual(countWords("hello"), 1);
  assert.strictEqual(countWords("hello world this is wingman"), 5);
  assert.strictEqual(countWords("  multi   spaced   words  "), 3);
});

test("truncateToMaxWords limits words without crashing", () => {
  const sentence = "one two three four five six seven";
  assert.strictEqual(truncateToMaxWords(sentence, 3), "one two three");
  assert.strictEqual(truncateToMaxWords(sentence, 10), sentence);
  assert.strictEqual(truncateToMaxWords("", 5), "");
});

test("sanitizeText strips unicode dashes and extra whitespace", () => {
  const dirty = "hello\u2014world \u2013 test   sentence";
  const clean = sanitizeText(dirty);
  assert.strictEqual(clean, "hello, world , test sentence");
});
