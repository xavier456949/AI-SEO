# ChatGPT and Codex

This fork provides one self-contained `seo` skill with OpenAI UI metadata,
on-demand SEO workflows, shared references, schema templates, data, specialist
procedures, and the existing isolated Python runtime. Claude Code's source
skills and plugin remain available through their existing installation path.

## Install this checkout

With Python 3.10+ (prefer 3.11+):

```sh
python3 install-codex.py --setup
```

The installer reads local files, including your edits; it does not download the
upstream Claude release. It installs into `$CODEX_HOME/skills/seo`, falling back
to `~/.codex/skills/seo`, matching the bundled Codex skill installer. Use
`--dest ~/.agents/skills` for the user skill location documented by current
[OpenAI skill guidance](https://learn.chatgpt.com/docs/build-skills), or
`--dest .agents/skills` for a repository installation. Install in only one
discovery location to avoid duplicate entries.

The skill is available on the next turn. If it is not listed, restart the host.
Invoke it explicitly or use a natural-language request:

```text
$seo audit https://example.com
$seo page https://example.com/pricing
$seo content-brief sustainable packaging
$seo doctor
```

`--setup` creates the runtime's isolated environment and installs Chromium.
Omit it for instructions-only installation, or use `--setup --skip-browser`
when rendered-page checks are unnecessary. The installer does not connect
Google, DataForSEO, or other accounts, and does not edit host settings.

An existing `seo` destination is never overwritten. To update, back up that
directory first, then rerun the installer. Keep any runtime state or audit
baselines you need from the old installation. To uninstall, remove only the
installed `seo` directory; shared credentials in `~/.config/claude-seo/` remain.

## Portable bundle and ChatGPT

```sh
python3 install-codex.py --dest dist/openai --archive dist/seo-openai.zip
```

The ZIP contains one `seo/SKILL.md`. The many upstream skills become
`WORKFLOW.md` reference documents so they are not registered as duplicate skills.
The folder layout is preserved for cross-references and script resource lookups.
It includes no virtual environment, browser download, Claude hooks, or service
configuration. Preserve MIT and FLOW attribution when redistributing it.

Use the bundle with a ChatGPT environment that supports local skills or package
it through that environment's supported plugin workflow. Local Codex installation
does not install anything into a separate ChatGPT cloud account. In an ordinary
ChatGPT conversation, supply the relevant workflow and site evidence as files;
attaching a ZIP alone does not register a skill or grant shell/browser access.
See [OpenAI skills](https://developers.openai.com/plugins/concepts/skills).

## Runtime diagnostics

Replace `<SEO_ROOT>` with the installed skill directory and `python3` with an
available Python 3.10+ executable. On Windows, `python` may be the appropriate
command. All bundled analysis scripts run through the managed dispatcher:

```sh
python3 "<SEO_ROOT>/scripts/runtime.py" doctor --json
python3 "<SEO_ROOT>/scripts/runtime.py" setup
python3 "<SEO_ROOT>/scripts/runtime.py" run fetch_page.py https://example.com
```

Setup failure leaves the skill instructions installed. Retry the second command
after resolving the reported dependency issue. Do not bypass dependency floors
or install packages globally. Legacy `CLAUDE_SEO_*` runtime options and credential
paths are retained for compatibility; Claude Code itself is not required.

## Execution differences

- OpenAI uses available tools by capability, not Claude tool-name aliases.
- Specialist agent Markdown files are procedures, not registered Codex agents;
  the host may execute them inline or delegate within its own limits.
- MCP/provider workflows require an actual connected service. Their inclusion
  supplies instructions, not credentials or paid API access.
- Missing tools lead to explicitly limited analysis using supplied evidence.
  Do not infer live metrics, indexing status, or complete coverage from screenshots.
- Changing SEO policies must be verified against primary sources; bundled
  references are not a guarantee of current search-engine behavior.

## Validate a package

```sh
python3 -m unittest discover -s tests -p 'test_openai_install.py'
```

The installer tests build and relocate the complete bundle, validate workflow
links and resources, exercise runtime diagnosis from outside the package, and
verify that existing installations are preserved.
