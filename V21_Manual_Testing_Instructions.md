# V21 STAGE 1 — MANUAL TESTING ON POE

Written so someone new to the project can run a full testing round without further explanation.

---

## PART 1 — WHAT YOU ARE DOING

### The engine

`engine_v21_stage1.md` is a long instruction document. You paste it into a chat with Claude Sonnet 5, attach six images of one painting, add a short briefing, and the model produces a structured record of what it observes. It never rates the painting and never sees a score. It only reports findings in a fixed vocabulary.

### The harness

"Harness" just means **the same painting is analysed twice, independently, and the two records are compared.**

Independently is the important word. Two runs in the same chat are not independent — the second one can see the first and will tend to agree with it. So each pass gets **its own fresh chat**, with no memory of the other.

Then you diff the two records. Where they agree, the finding is probably solid. Where they disagree, you have found something: either a condition in the engine that is ambiguous, or a feature of the painting that is genuinely hard to read. Both are worth knowing, and disagreement is the single most useful signal this whole process produces. **Do not treat disagreement as a failure.** It is the point.

The engine is built to make those diffs informative. Every classification carries the observation it rests on, and where the model judged a call to be close it also records which value it *nearly* chose and what decided it. So a diff tells you not just *that* two runs split, but *where*.

### What you need per painting

- The six image files, renamed as below
- The painting's substrate code, ink code, dimensions and orientation
- Its sizing family (looked up from the substrate code)
- Its `mass_displacement` value (computed by script — see Part 2)

---

## PART 2 — PREPARE ONE PAINTING

### 2.1 Rename the six images

Exactly this, in this order. `NNN` is the work number.

```
t_NNN_1_analysis
t_NNN_2_bw
t_NNN_3_crop
t_NNN_4_posterized
t_NNN_5_inverted
t_NNN_6_lowpass
```

### 2.2 Compute mass_displacement

The engine expects a value telling it where the ink mass sits. This is measured by script, not by the model, so the model cannot talk itself into a different answer.

```
python mass_displacement.py t_NNN_2_bw.jpg
```

It prints something like:

```
t_369_bw.jpg    SE_MARKED    16.2%   dx=+138 dy=+192 px
```

**The value you need is the first field** — `SE_MARKED`. The percentage and pixel offsets are for your records only; do not put them in the briefing.

Possible values: `CENTRED`, or a compass point (`N` `NE` `E` `SE` `S` `SW` `W` `NW`) joined to `SLIGHT` or `MARKED` — for example `W_SLIGHT`, `NE_MARKED`.

### 2.3 Look up the sizing family

From the substrate code, in the material reference. One of exactly three values:

`RAW` · `SEMI_SIZED` · `SIZED`

**A note on why you supply this.** The engine is written so the model describes what it sees in Blocks 2 and 3 before opening any material reference in Block 4. That ordering shapes the record, which is worth having. But it is not a real information barrier — the model reads the whole engine before it starts writing, so it knows the family from the outset regardless. Supplying the family directly removes a failure mode (the model inventing one) without giving anything away that was actually protected.

---

## PART 3 — RUN PASS A

1. Open Poe. Start a **new chat** with the Claude Sonnet 5 bot.

2. Attach the six images **in the numbered order above**. Do them one at a time if the interface reorders batch uploads.

3. Paste this into the message box, in this order:

   **(a) The full contents of `engine_v21_stage1.md`.**

   **(b) Then this block, filled in:**

   ```
   ---

   BRIEFING FOR THIS WORK

   work_id: t_NNN
   substrate_code: S__
   ink_code: MB__
   sheet_dimensions: 000 x 000 cm
   sheet_orientation: LANDSCAPE
   mass_displacement: __________

   Material reference for this substrate:
   sizing_family: __________

   ---

   OUTPUT FORMAT

   Emit one JSON object conforming to the schema below. Nothing before it,
   nothing after it.

   [paste the full contents of v21_stage1_schema.json here]
   ```

4. Send. Let it finish. Sonnet 5 will show its thinking — that is what you want documented.

5. Save three things to a file named `t_NNN_passA`:
   - the full reasoning/thinking text
   - the JSON record
   - anything the model said outside the JSON (there should be nothing; if there is, note it)

---

## PART 4 — RUN PASS B

**Start a completely new chat.** Not a new message in the same chat.

Repeat Part 3 exactly — same images, same order, same engine, same briefing, same schema. Change nothing.

Save as `t_NNN_passB`.

---

## PART 5 — WHAT TO RECORD

One row per painting.

| Field | Notes |
|---|---|
| work_id | |
| substrate_code / ink_code / sizing_family | |
| mass_displacement | plus the raw percentage, for calibration |
| Pass A: all 13 axis values | |
| Pass B: all 13 axis values | |
| **Axes that disagree** | the important column |
| Axes marked `NOT_ESTABLISHED` | either pass |
| Axes with confidence below HIGH | either pass |
| Did both JSONs validate against the schema | |
| Anything the model refused, queried, or got stuck on | |

---

## PART 6 — WHAT TO LOOK FOR

Nine things the first round is meant to settle. Note them as you go rather than analysing at the end.

1. **Does the middle level dominate?** Most axes should land on their second value — `SOUND`, `HOLDS`, `PHASES_SOUND`, `SEPARATED`, `COHERENT`, `AT_SUBSTRATE`. If runs cluster on the third or fourth values instead, the engine is running generous and the conditions need tightening.

2. **Does anything ever reach the bottom value?** `BREACHED`, `BREAKS_DOWN`, `PHASE_FAILURE`, `SINGLE_BAND`, `DISPERSED`, `GROUND_INERT`, `UNACCOUNTED`, `CONTROL_LOST`. If none of these is ever selected across the whole round, the floors are unreachable and that is a design fault, not a compliment to the work.

3. **Does anything ever reach the top value?** Same logic in reverse.

4. **`DISPERSED` on t_200 specifically.** This painting has three separate dark regions connected by a very pale sweep. It should come back `COHERENT`, because a pale connection is still a connection. If either pass returns `DISPERSED`, the engine's Axis 10 wording is not doing its job. **This is the single most informative test in the round.**

5. **`SINGLE_BAND` ever selected.** It should fire on a flat, single-pass work.

6. **`POOLED_RING` and `MECHANICALLY_DISTURBED`** ever selected as boundary traits.

7. **Element counts.** The engine calls something an element if it reaches half a grid cell. Check the inventory looks sane on both a sparse single-gesture sheet and a dense layered one. Too many tiny elements, or a large mass missed entirely, means the threshold is wrong.

8. **Which axes attract decision notes.** An axis that repeatedly records a close call has an underspecified condition. This is the most direct route to knowing what to fix.

9. **Second pigment.** On a work carrying red — t_317, t_318, t_369 — check the model flagged it at 1.4 and excluded it from the ink bands at 3.1. If red is counted as an ink band, the exclusion is not working.

---

## PART 7 — TROUBLESHOOTING

**The model writes prose before or after the JSON.** Note it and keep the run. It means the output instruction needs strengthening; it does not invalidate the record.

**The JSON fails schema validation.** Save the error. This is useful — it usually means a required field the model skipped, which points at an instruction that is not landing.

**The model asks a question instead of producing a record.** Note what it asked. Do not answer and continue in that chat — the answer contaminates the run. Start over in a fresh chat, and log the question as a gap in the briefing.

**Only some images upload, or Poe reorders them.** Note which and in what order. Image order was chosen deliberately (direct views before derived ones), so a scrambled upload is worth recording rather than ignoring.

**The model says it cannot see an image.** Stop, fix the upload, start a fresh chat. A run with a missing image is not comparable to one without.

**A run takes very long or is cut off.** Note where it stopped. If it stopped mid-record, discard and rerun in a fresh chat.

---

## PART 8 — SUGGESTED FIRST ROUND

Eight to twelve paintings, chosen deliberately rather than at random. The reachability questions in Part 6 cannot be answered by a random sample, because the extreme values are meant to be rare.

Include:

- **t_200** — the pale-connection case for Axis 10 (item 4 above)
- **t_369** — dense, layered, carries red
- **t_317** and **t_318** — also carry red
- **t_333** — clean discrete tonal steps
- **t_158** — heavy bleed, fused passes
- At least one **single-gesture** work, to test the sparse-sheet path
- At least one work you consider **genuinely weak**, to test whether the floors are reachable
- At least one you consider **among your strongest**, to test whether the tops are
- Spread across **RAW, SEMI_SIZED and SIZED** substrates

Two passes each. Sixteen to twenty-four runs total.
