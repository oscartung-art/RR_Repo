# Project Notes & Future Ideas

## Hybrid Pipeline Idea (Cloud Vision + Gemini)

**Status:** Deferred — revisit when processing large batches

**Concept:** Use both APIs in sequence to balance speed and richness:

1. **Cloud Vision API first** (~0.5s/image, ~$0.0015/image)
   - Fills: `Tags` (labels), `Brand` (logo detection), `Color` (dominant colour)
   - Fast and structured output

2. **Gemini 2.5 Flash second** (~5s/image, ~$0.00015/image)
   - Fills: `Subcategory`, `Style`, `Description`, `Material`
   - Only needed for fields Cloud Vision cannot provide

**Benefit:** Reduces Gemini calls for images where Cloud Vision already captures enough.
**Trade-off:** Cloud Vision is 10x faster but 10x more expensive per image.
**Net result:** Potentially faster overall pipeline with richer data.

---

## API Comparison Summary (tested Mar 2026)

| API | Speed | Cost/image | Output Quality | Verdict |
|---|---|---|---|---|
| Gemini 2.5 Flash (AI Studio) | ~5s | ~$0.00015 | Excellent — free-form, structured | **Current method** |
| Google Cloud Vision API | ~0.5s | ~$0.0015 | Good — labels/logos only, no descriptions | Faster but limited |
| Vertex AI Gemini | N/A | N/A | Not available on gen-lang-client-* projects | Not usable |

---

## Vertex AI Status

Project `gen-lang-client-0816223034` (created via Google AI Studio) does **not** support Vertex AI generative models. To use Vertex AI, a standard GCP project with Vertex AI API enabled would be required.


## General notes Prompts to be sent to AI

now I want to output what we've talked about and tell manus to help me set up using terminal with AI, together with github of course. I will use the terminal in VS code.