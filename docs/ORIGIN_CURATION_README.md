# Origin Curation Documentation

This directory contains comprehensive documentation for ScanCode.io's origin curation system.

## Documents

### For Users

#### 1. Origin Curation Tutorial (`tutorial_origin_curation.rst`)
**Best for**: Complete learning from scratch

The main tutorial covering:
- Understanding origin determination
- Using the Web UI for review
- Amending and verifying origins
- Origin propagation (detailed guide)
- Exporting and importing curations via FederatedCode
- Best practices for large codebases
- Example workflows (vendored code, copied snippets, large monorepos)

**Start here if**: You're new to origin curation or want comprehensive coverage.

#### 2. Origin Curation Workflows (`origin-curation-workflows.rst`)
**Best for**: Following structured processes

Visual ASCII workflows for:
- Initial review (first-time setup)
- Vendor libraries (vendored dependencies)
- Copied code snippets (online sources)
- Large codebases (10,000+ files, 5-week plan)
- Team collaboration (multi-person workflows)
- Compliance audits (6-week process)

**Use this when**: You need a step-by-step checklist for a specific scenario.

#### 3. Origin Curation Quick Reference (`origin-curation-quick-reference.rst`)
**Best for**: Fast lookups during work

Quick reference including:
- Common task steps (verify, amend, propagate, export, import)
- Origin type reference with examples
- Confidence scoring guide
- Bulk operation examples
- API endpoint reference
- Troubleshooting quick fixes
- CLI patterns

**Use this when**: You know what you want to do and just need the command/steps.

### For Developers

#### 4. FederatedCode Curation Integration (`federatedcode-curation-integration.rst`)
**Best for**: Technical understanding and API development

Technical reference covering:
- System architecture
- Curation schema specification (complete JSON)
- Database models
- Export/import mechanisms
- Conflict resolution strategies
- API reference with request/response examples
- Best practices for integration

**Use this when**: Building integrations, understanding internals, or troubleshooting.

## Documentation Flow

```
┌──────────────────────────────────────────────────────┐
│  Are you new to origin curation?                    │
│  ┌──────┐                    ┌──────────┐          │
│  │ YES  │ ──────────────────>│ Tutorial │          │
│  └──────┘                    └──────────┘          │
│     │                              │                 │
│  ┌──────┐                    ┌──────────┐          │
│  │  NO  │ ──────────────────>│ Workflow │          │
│  └──────┘                    └──────────┘          │
│                                    │                 │
│                              ┌──────────┐          │
│                              │Quick Ref │<─────┐   │
│                              └──────────┘      │   │
│                                                  │   │
│  Need technical details?                       │   │
│  ┌──────────────────┐                          │   │
│  │ FederatedCode    │                          │   │
│  │ Integration Doc  │ ─────────────────────────┘   │
│  └──────────────────┘                              │
└──────────────────────────────────────────────────────┘
```

## Quick Start

```bash
# 1. Read the overview
docs/tutorial_origin_curation.rst (sections 1-2)

# 2. Follow initial workflow
docs/origin-curation-workflows.rst (Initial Review)

# 3. During work, reference
docs/origin-curation-quick-reference.rst (as needed)

# 4. For advanced features
docs/federatedcode-curation-integration.rst
```

## Key Topics Index

### UI and Navigation
- **Tutorial**: "Accessing Origin Determinations" section
- **Quick Ref**: "Filter and Search" section
- **Workflow**: Shown in context in each workflow

### Amending Origins
- **Tutorial**: "Amending Origin Determinations" (7-step process)
- **Quick Ref**: "Amend an Origin" (condensed steps)
- **Workflow**: Applied throughout all workflows

### Propagation
- **Tutorial**: "Origin Propagation" (comprehensive guide)
- **Quick Ref**: "Propagate Origins" (command examples)
- **Workflow**: "Large Codebase Workflow" (week 3-4)
- **FederatedCode**: "Provenance Tracking" section

### Export and Import
- **Tutorial**: "Exporting and Sharing Curations" + "Importing Curations"
- **Quick Ref**: "Export Curations" + "Import Curations"
- **Workflow**: "Compliance Audit Workflow" (phase 4-5)
- **FederatedCode**: Complete technical documentation

### Best Practices
- **Tutorial**: Three sections (large codebases, teams, compliance)
- **Quick Ref**: "Best Practice Checklist" section
- **Workflow**: Applied in "Large Codebase" and "Team Collaboration"
- **FederatedCode**: "Best Practices" section

### API and Automation
- **Tutorial**: "Advanced Topics" section
- **Quick Ref**: "Automation Examples" + "API Endpoints Reference"
- **FederatedCode**: "API Reference" section

## Building the Documentation

```bash
# Navigate to docs directory
cd docs/

# Build HTML
make html

# View
# Open docs/_build/html/index.html in browser

# Or on Windows
make.bat html
```

## Documentation Standards

All origin curation documentation follows:

- **Format**: reStructuredText (RST) for Sphinx
- **Style**: ScanCode.io conventions
- **Cross-references**: Use `:ref:` for internal links
- **Code blocks**: Proper syntax highlighting
- **Examples**: Real, tested examples
- **Images**: Placeholders in `images/` directory

## Image Placeholders

The following images should be created for visual completeness:

1. `images/origin-determination-list.png` - List view screenshot
2. `images/origin-determination-detail.png` - Detail page screenshot
3. `images/origin-amendment-form.png` - Amendment form screenshot
4. `images/origin-propagation-preview.png` - Propagation preview screenshot
5. `images/origin-export-dialog.png` - Export dialog screenshot
6. `images/origin-import-dialog.png` - Import dialog screenshot
7. `images/origin-conflict-resolution.png` - Conflict resolution screenshot

## Search Tips

### Find by Task

**"How do I verify origins?"**
- Tutorial § "Verifying Origins"
- Quick Ref § "Verify an Origin"

**"How does propagation work?"**
- Tutorial § "Origin Propagation" (start here)
- Quick Ref § "Propagate Origins" (commands)
- Workflow § "Large Codebase Workflow" week 3

**"How do I export curations?"**
- Tutorial § "Exporting and Sharing Curations"
- Quick Ref § "Export Curations"
- FederatedCode § "Export/Import Utilities"

**"How do I handle conflicts?"**
- Tutorial § "Handling Import Conflicts"
- Quick Ref § "Resolve Conflicts"
- FederatedCode § "Conflict Resolution Strategies"

### Find by Scenario

**"I'm reviewing my first scan"**
→ Workflow: "Initial Review Workflow"

**"I have vendored libraries"**
→ Workflow: "Vendor Libraries Workflow"

**"My codebase has 10,000+ files"**
→ Workflow: "Large Codebase Workflow"
→ Tutorial: "Best Practices" § "For Large Codebases"

**"I'm working with a team"**
→ Workflow: "Team Collaboration Workflow"
→ Tutorial: "Best Practices" § "For Collaborative Teams"

**"I'm preparing for an audit"**
→ Workflow: "Compliance Audit Workflow"
→ Tutorial: "Best Practices" § "For Compliance and Auditing"

### Find by Feature

**Propagation**
- Tutorial § "Origin Propagation" (comprehensive)
- Quick Ref § "Propagate Origins" (commands)
- FederatedCode § "Provenance Tracking"

**FederatedCode Integration**
- Tutorial § "Exporting and Sharing Curations"
- FederatedCode § Complete documentation

**API Usage**
- Tutorial § "Advanced Topics" § "Using the REST API"
- Quick Ref § "API Endpoints Reference"
- FederatedCode § "API Reference"

**Bulk Operations**
- Quick Ref § "Bulk Operations"
- Tutorial § "Best Practices" § "For Large Codebases"

## Documentation Size

- **tutorial_origin_curation.rst**: 1,100 lines
- **origin-curation-workflows.rst**: 650 lines
- **origin-curation-quick-reference.rst**: 700 lines
- **federatedcode-curation-integration.rst**: 1,080 lines
- **Total**: 3,530 lines of documentation

## Related Documentation

- `user-interface.rst` - General UI documentation
- `rest-api.rst` - API documentation
- `command-line-interface.rst` - CLI reference
- `custom-pipelines.rst` - Pipeline development

## Feedback and Contributions

Documentation improvements welcome! See `CONTRIBUTING.md` in the repository root.

## License

Documentation is part of ScanCode.io and follows the same license (Apache-2.0).

---

**Last Updated**: March 4, 2026  
**Version**: 1.0  
**ScanCode.io Version**: 36.1.0+
