# ntulearn-downloader

Download NTU Singapore NTULearn course materials recursively from the command
line.

## What it does

* reads your existing NTULearn browser session (`BbRouter` cookie)
* finds your available enrolled courses
* recursively walks NTULearn content folders
* downloads Blackboard attachments and supported embedded file links
* preserves the course/folder hierarchy
* skips files that already exist, so rerunning behaves like an incremental sync
* writes via `.part` then atomically renames, avoiding half-downloaded files
* supports filtering by course, dry runs, old/disabled courses, and overwrite mode

## Requirements

* Python 3.12+
* [`uv`](https://docs.astral.sh/uv/)
* an active login to `https://ntulearn.ntu.edu.sg` in Firefox, Chrome, Edge, or Brave

If browser auto-read fails, set `NTULEARN_COOKIE` to your `BbRouter` cookie value manually.

## Install / run

```bash
git clone https://github.com/pitchaya-s/ntulearn-downloader.git
cd ntulearn-downloader
uv sync
```

Log into NTULearn in your browser, then test without downloading:

```bash
uv run ntulearn-download --all --dry-run
```

Download all available courses:

```bash
uv run ntulearn-download --all -o ~/NTULearn
```

Or download a specific course:

```bash
uv run ntulearn-download -c SC2001 -o ~/NTULearn
```

You must specify either `--all` or at least one `-c/--course`.

Rerun the same command later. Existing files are skipped.

## Useful options

Download all available courses:

```bash
uv run ntulearn-download --all
```

Download only one course using a substring match:

```bash
uv run ntulearn-download -c SC2001
```

Download multiple courses:

```bash
uv run ntulearn-download -c SC2001 -c MH2802
```

Preview what would be downloaded without writing any files:

```bash
uv run ntulearn-download --all --dry-run
```

Or preview a specific course:

```bash
uv run ntulearn-download -c SC2001 --dry-run
```

Include old/unavailable enrollments:

```bash
uv run ntulearn-download --all --include-disabled
```

Force redownload of files that already exist:

```bash
uv run ntulearn-download --all --overwrite
```

Choose a different output directory:

```bash
uv run ntulearn-download --all -o ~/NTULearn
```

## Authentication

The downloader follows this order:

1. read a fresh `BbRouter` cookie from a logged-in browser
2. use `NTULEARN_COOKIE` if provided
3. use the last cached cookie saved by `ntulearn-mcp`

If NTULearn returns HTTP 401, open NTULearn in your browser, complete SSO/MFA,
and rerun the command.

**Never commit or share your `BbRouter` cookie.** It represents your authenticated
NTULearn session.

## Folder layout

For example:

```text
NTULearn/
├── #### Course A /
│   ├── Lecture Materials/
│   │   ├── Week 1/
│   │   │   └── lecture-01.pdf
│   │   └── Week 2/
│   │       └── lecture-02.pdf
│   └── Tutorials/
│       └── tutorial-01.pdf
└── #### Course B /
    └── ...
```

The exact hierarchy follows what each NTULearn course exposes through Blackboard.

## Limitations

"Everything" means downloadable files that NTULearn exposes through its Blackboard
content APIs or supported embedded Blackboard links. External websites, LTI tools,
YouTube videos, interactive pages, and other third-party resources are not mirrored.

By default an existing filename is considered already synced. If an instructor
replaces a file while keeping exactly the same filename, use `--overwrite` to fetch
it again.

## Responsible use

This is an unofficial personal-use tool and is not affiliated with NTU Singapore,
Anthology, or Blackboard. Automated LMS access may be subject to NTU policies.
Use it only with your own account and avoid aggressive repeated runs.

## Credits / upstream

This project is built on top of **[`kingdonkatsu/ntulearn-mcp`](https://github.com/kingdonkatsu/ntulearn-mcp)**.
Its NTULearn browser-cookie authentication, Blackboard REST client, and Blackboard
content-link parsing made this standalone downloader possible. This project replaces
the MCP/AI-agent orchestration with a deterministic recursive CLI; it does not claim
the underlying NTULearn integration as original work.

Thanks to kingdonkatsu for publishing the NTULearn integration as open source.
