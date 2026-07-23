# Deployment guide (OpenAlex + RSS + Gemini)

This fork adds an **OpenAlex** journal source, replaces the e-mail delivery with an
**RSS feed** published to **GitHub Pages**, and runs on a daily **GitHub Actions**
cron using **Google Gemini's free API** (OpenAI-compatible endpoint).

The daily flow: Zotero corpus → retrieve (arXiv + OpenAlex) → rerank by similarity
→ Gemini TL;DR → write `public/feed.xml` → deploy to GitHub Pages.

---

## 1. One-time repository setup

### a) Enable GitHub Pages
`Settings → Pages → Build and deployment → Source: **GitHub Actions**`.
(No branch to pick — the workflow deploys the artifact directly.)

Your feed will be served at:

```
https://<username>.github.io/<repo>/feed.xml
```

For this fork: `https://pinecho.github.io/zotero-arxiv-daily/feed.xml`
(already set as `rss.link` in `config/custom.yaml` — change it if you rename the repo).

### b) Add Actions secrets
`Settings → Secrets and variables → Actions → Secrets → New repository secret`:

| Secret | Description | Where to get it |
| :-- | :-- | :-- |
| `ZOTERO_ID` | Your Zotero **numeric** user ID (not the username). | https://www.zotero.org/settings/security |
| `ZOTERO_KEY` | A Zotero API key with read access. | https://www.zotero.org/settings/security |
| `GEMINI_API_KEY` | Google Gemini API key (free tier is enough). | https://aistudio.google.com/apikey |

No e-mail secrets are needed anymore (`SENDER`, `RECEIVER`, `SENDER_PASSWORD`,
`OPENAI_API_KEY`, `OPENAI_API_BASE` can be deleted).

### c) (Optional) Add a variable
`Settings → Secrets and variables → Actions → Variables`:

| Variable | Description |
| :-- | :-- |
| `OPENALEX_MAILTO` | Your e-mail, to use the OpenAlex "polite pool" (faster, more reliable). Optional. |

### d) Let Actions write Pages
`Settings → Actions → General → Workflow permissions`: make sure Actions are
allowed to run. The Pages permissions themselves are declared inside the workflow
(`permissions: pages: write, id-token: write`).

---

## 2. Configuration (`config/custom.yaml`)

Everything user-specific lives in `config/custom.yaml` (already filled in for this
fork). Secrets are pulled from the environment via `${oc.env:VAR}` so nothing
sensitive is committed. Key parts:

```yaml
llm:
  api:
    key: ${oc.env:GEMINI_API_KEY}
    base_url: https://generativelanguage.googleapis.com/v1beta/openai/
  generation_kwargs:
    model: gemini-3.5-flash-lite   # flash-lite: ~1000 req/day free. (flagship gemini-3.6-flash is only ~20/day free.)

source:
  arxiv:
    category: ["eess.AS","cs.SD","cs.LG","eess.SP"]
  openalex:
    filter_type: search            # or "topic"
    search: ["speech health detection", "voice disorder deep learning", ...]
    topic_ids: ["T10863","T10860","T10201"]
    days: 2
    max_results: 200

rss:
  link: https://pinecho.github.io/zotero-arxiv-daily

executor:
  source: ['arxiv','openalex']
```

### arXiv categories
Currently `eess.AS` (audio & speech), `cs.SD` (sound), `cs.LG` (machine learning),
and `eess.SP` (signal processing). `eess.SP` is included because a lot of
audio-biomarker work lands there; drop it if it turns out to be too noisy.

### OpenAlex filtering: keyword vs. topic
- **`filter_type: search`** (current default, "get it working" mode): each phrase
  in `search` is matched with `default.search`; results are unioned and deduped.
  Simple and broad, but can pull in tangential hits (reranking against your Zotero
  library filters most of that out).
- **`filter_type: topic`** (precise mode): filters by `topics.id` (OR-joined).
  Switch by setting `filter_type: topic`; `topic_ids` is already pre-filled with
  the three most relevant topics.

#### Candidate OpenAlex topic IDs (please confirm before switching)
Found via the OpenAlex works API (`group_by=topics.id`) for
"speech/audio-based deep-learning health detection". OpenAlex has **deprecated
Concepts** in favour of **Topics**, so these are Topic IDs.

| ID | Topic | Field › Subfield | Relevance |
| :-- | :-- | :-- | :-- |
| **T10863** | Voice and Speech Disorders | Medicine › Physiology | Core: dysphonia, Parkinson's, dysarthria, acoustic analysis |
| **T10860** | Speech and Audio Processing | CS › Signal Processing | Core: audio deep learning, enhancement, separation |
| **T10201** | Speech Recognition and Synthesis | CS › Artificial Intelligence | Core: DNN acoustic modeling, speaker verification |
| T12419 | Phonocardiography & Auscultation | Medicine › Pulmonary & Respiratory | Heart/lung sound classification |
| T12418 | Respiratory & Cough-Related Research | Medicine › Pulmonary & Respiratory | Cough audio (e.g. COVID) |
| T10009 | Dementia & Cognitive Impairment | Medicine › Psychiatry & Mental health | Speech-based cognitive decline |
| T10667 | Emotion and Mood Recognition | Psychology | Speech emotion / mental-health signals |

Recommended starting set for topic mode: **T10863, T10860, T10201**
(add T12419 / T12418 / T10009 if you want to widen into physiological audio).

You can inspect any topic in the browser, e.g.
`https://api.openalex.org/topics/T10863`.

---

## 3. Local validation (recommended before the first cron)

Requires [uv](https://github.com/astral-sh/uv).

**Step 1 — verify the OpenAlex source returns papers** (no credentials needed):

```bash
uv run python - <<'PY'
from omegaconf import OmegaConf
from zotero_arxiv_daily.retriever.openalex_retriever import OpenAlexRetriever
cfg = OmegaConf.create({
  "source": {"openalex": {"filter_type": "search",
    "search": ["voice disorder deep learning"], "days": 30,
    "mailto": "you@example.com", "max_results": 50}},
  "executor": {"debug": True}})
r = OpenAlexRetriever(cfg)
papers = [p for p in (r.convert_to_paper(x) for x in r._retrieve_raw_papers()) if p]
print("papers:", len(papers))
for p in papers[:3]: print("-", p.title[:80])
PY
```

**Step 2 — run the whole pipeline in debug mode** (writes `public/feed.xml`):

```bash
export ZOTERO_ID=... ZOTERO_KEY=... GEMINI_API_KEY=...
export DEBUG=true
uv run src/zotero_arxiv_daily/main.py
cat public/feed.xml            # inspect the generated RSS
```

Debug mode caps each source to ~10 papers, so it finishes quickly and uses little
Gemini quota.

**Step 3 — run the test suite:**

```bash
uv run pytest            # fast tests
uv run pytest -m ""      # include slow tests (downloads the embedding model)
```

---

## 4. First real run & subscribing

1. Push to `main` (scheduled workflows only fire from the **default branch**).
2. `Actions → Build RSS feed daily → Run workflow` to trigger it manually once.
3. When it finishes, open `https://<username>.github.io/<repo>/feed.xml`.
   Opening it in a browser shows a simple rendered page (via `rss.xsl`); RSS
   readers and Zotero read the raw XML.
4. Add that URL to your RSS reader, or in Zotero: **New Feed → From URL**.

The workflow is scheduled at `0 22 * * *` (22:00 UTC). Edit the `cron` in
`.github/workflows/main.yml` to change it. There is also a manual **Test**
workflow that builds a debug feed and uploads it as an artifact (no Pages deploy).

---

## 5. Notes on limits

- **Gemini free tier** limits matter a lot here. The binding limits are per-**day**
  (RPD) and per-**minute** (RPM), and they differ hugely by model:
  - Flagship flash (`gemini-3.6-flash`) free tier ≈ **20 requests/day** — far too
    few for a 50-paper digest. Do **not** use it here.
  - **flash-lite** (`gemini-3.5-flash-lite`) free tier ≈ **1000 requests/day** —
    the right choice, and fine quality for one-sentence TL;DRs.
  - Exact current numbers: <https://ai.google.dev/gemini-api/docs/rate-limits>
    (they change; a model's free RPD can even shift for a given project).
  Only the TL;DR uses the LLM for every paper; affiliation extraction runs *only*
  for papers with full text (arXiv), and OpenAlex affiliations come from its API
  (no LLM). `llm.max_requests_per_minute` paces calls under the RPM limit.
  `max_paper_num` is `50`; lower it if you hit quota.
- **GitHub Actions** public-repo runs are capped at 6h each; the current settings
  finish in minutes.
- The feed is regenerated in full each run (it is not an append-only archive);
  RSS readers dedupe by `guid`, which is the paper's DOI/landing URL.
