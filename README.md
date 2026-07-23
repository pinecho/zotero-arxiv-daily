<p align="center">
  <a href="" rel="noopener">
 <img width=200px height=200px src="assets/logo.svg" alt="logo"></a>
</p>

<h3 align="center">Zotero-arXiv-Daily</h3>

<div align="center">

  [![Status](https://img.shields.io/badge/status-active-success.svg)]()
  ![Stars](https://img.shields.io/github/stars/TideDra/zotero-arxiv-daily?style=flat)
  [![GitHub Issues](https://img.shields.io/github/issues/TideDra/zotero-arxiv-daily)](https://github.com/TideDra/zotero-arxiv-daily/issues)
  [![GitHub Pull Requests](https://img.shields.io/github/issues-pr/TideDra/zotero-arxiv-daily)](https://github.com/TideDra/zotero-arxiv-daily/pulls)
  [![License](https://img.shields.io/github/license/TideDra/zotero-arxiv-daily)](/LICENSE)
  [<img src="https://api.gitsponsors.com/api/badge/img?id=893025857" height="20">](https://api.gitsponsors.com/api/badge/link?p=PKMtRut1dWWuC1oFdJweyDSvJg454/GkdIx4IinvBblaX2AY4rQ7FYKAK1ZjApoiNhYEeduIEhfeZVIwoIVlvcwdJXVFD2nV2EE5j6lYXaT/RHrcsQbFl3aKe1F3hliP26OMayXOoZVDidl05wj+yg==)

</div>

---

<p align="center"> Recommend new papers of your interest daily according to your Zotero library, delivered as an RSS feed.
    <br> 
</p>

> [!NOTE]
> **This fork** adds an [OpenAlex](https://openalex.org) journal source, replaces e-mail delivery with an **RSS feed** published to **GitHub Pages**, and runs on **Google Gemini's free API**. See [`DEPLOYMENT.md`](./DEPLOYMENT.md) for the full setup guide.

> [!IMPORTANT]
> Please keep an eye on this repo, and merge your forked repo in time when there is any update of this upstream, in order to enjoy new features and fix found bugs.

## 🧐 About <a name = "about"></a>

> Track new scientific researches of your interest by just forking (and staring) this repo!😊

*Zotero-arXiv-Daily* finds new papers that may attract you based on the context of your Zotero library, and then publishes the result as an **RSS feed** on GitHub Pages📡 that you subscribe to in any RSS reader (or in Zotero itself). It can be deployed as a Github Action Workflow with **zero cost**, **no installation**, and **few configuration** of Github Action environment variables for daily **automatic** delivery.

## ✨ Features
- Totally free! All the calculation can be done in the Github Action runner locally within its quota (for public repo).
- Delivered as a standard **RSS feed** published to GitHub Pages — read it in any RSS reader or subscribe in Zotero.
- AI-generated TL;DR for you to quickly pick up target papers.
- Affiliations of the paper are resolved and presented.
- Links of PDF / landing page presented in each feed item.
- List of papers sorted by relevance with your recent research interest.
- Fast deployment via fork this repo and set environment variables in the Github Action Page.
- Support LLM API for generating TL;DR of papers (e.g. Google Gemini's free API).
- Ignore unwanted Zotero papers using a list of glob patterns.
- Support multiple sources of papers to retrieve:
  - arxiv
  - biorxiv
  - medrxiv
  - **openalex** (formally published journal / conference papers, not only preprints)

## 📷 Screenshot
![screenshot](./assets/screenshot.png)

## 🚀 Usage
### Quick Start

**👉 The full, step-by-step setup lives in [`DEPLOYMENT.md`](./DEPLOYMENT.md).** In short:

1. **Fork** (and star😘) this repo.
2. **Enable GitHub Pages**: `Settings → Pages → Source: GitHub Actions`.
3. **Add three Actions secrets** (`Settings → Secrets and variables → Actions`):

   | Secret | Description | Example |
   | :--- | :--- | :--- |
   | `ZOTERO_ID` | User ID of your Zotero account (**a number, not your username**). Get it from [here](https://www.zotero.org/settings/security). | `12345678` |
   | `ZOTERO_KEY` | A Zotero API key with read access. Get it from [here](https://www.zotero.org/settings/security). | `AB5tZ877P2j7Sm2Mragq041H` |
   | `GEMINI_API_KEY` | A Google Gemini API key — the free tier is enough. Get it from [Google AI Studio](https://aistudio.google.com/apikey). | `AIza...` |

   *(Optional variable `OPENALEX_MAILTO` — your e-mail, for OpenAlex's faster "polite pool".)*

4. **Edit [`config/custom.yaml`](./config/custom.yaml)** — set `rss.link` to your Pages URL
   (`https://<username>.github.io/<repo>`), pick your `source.arxiv.category` and
   `source.openalex.search` keywords. Secrets are read from the environment via
   `${oc.env:VAR}`, so nothing sensitive is committed.

5. **Run it**: `Actions → Build RSS feed daily → Run workflow`. When it finishes,
   subscribe to `https://<username>.github.io/<repo>/feed.xml` in your RSS reader
   or in Zotero (**New Feed → From URL**).

> [!NOTE]
> Scheduled workflows only run from the repository's **default branch**, so make
> sure this lands on `main`. The daily cron is `0 22 * * *` (22:00 UTC) — edit it
> in `.github/workflows/main.yml`.

The `Test` workflow is a debug run (few papers, no Pages deploy) that uploads the
generated `feed.xml` as an artifact so you can inspect it.

The full config schema is documented inline in [`config/base.yaml`](./config/base.yaml).

### Local Running
Supported by [uv](https://github.com/astral-sh/uv), this workflow can easily run on your local device if uv is installed:
```bash
# set the required environment variables
export ZOTERO_ID=xxxx ZOTERO_KEY=xxxx GEMINI_API_KEY=xxxx
export DEBUG=true   # optional: retrieve only a few papers
cd zotero-arxiv-daily
uv run src/zotero_arxiv_daily/main.py
cat public/feed.xml
```

## 🚀 Sync with the latest version
This project is in active development. You can subscribe this repo via `Watch` so that you can be notified once we publish new release.

![Watch](./assets/subscribe_release.png)


## 📖 How it works
*Zotero-arXiv-Daily* firstly retrieves all the papers in your Zotero library and all the papers released in the previous day (from arXiv, OpenAlex, bioRxiv, medRxiv), via corresponding API. Then it calculates the embedding of each paper's abstract via an embedding model. The score of a paper is its weighted average similarity over all your Zotero papers (newer paper added to the library has higher weight). The TLDR of each paper is generated by LLM. Finally the ranked papers are rendered as an RSS feed (`public/feed.xml`) and published to GitHub Pages.

## 📌 Limitations
- The recommendation algorithm is very simple, it may not accurately reflect your interest. Welcome better ideas for improving the algorithm!
- High `executor.max_paper_num` can lead the execution time exceed the limitation of Github Action runner (6h per execution for public repo, and 2000 mins per month for private repo). Adding the OpenAlex source enlarges the candidate pool, so keep `max_paper_num` reasonable (default `50`). If you have special requirements, you can deploy the workflow in your own server, or use a self-hosted Github Action runner, or pay for the exceeded execution time.


## 📃 License
Distributed under the AGPLv3 License. See `LICENSE` for detail.

## ❤️ Acknowledgement
- [pyzotero](https://github.com/urschrei/pyzotero)
- [arxiv](https://github.com/lukasschwab/arxiv.py)
- [sentence_transformers](https://github.com/UKPLab/sentence-transformers)

## ☕ Buy Me A Coffee
If you find this project helpful, welcome to sponsor me via WeChat or via [ko-fi](https://ko-fi.com/tidedra).
![wechat_qr](assets/wechat_sponsor.JPG)


## 🌟 Star History

[![Star History Chart](https://api.star-history.com/svg?repos=TideDra/zotero-arxiv-daily&type=Date)](https://star-history.com/#TideDra/zotero-arxiv-daily&Date)
