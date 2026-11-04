# Graph Report - frontend  (2026-11-04)

## Corpus Check
- Corpus is ~34,521 words - fits in a single context window. You may not need a graph.

## Summary
- 616 nodes · 1797 edges · 32 communities (23 shown, 9 thin omitted)
- Extraction: 99% EXTRACTED · 1% INFERRED · 0% AMBIGUOUS · INFERRED: 11 edges (avg confidence: 0.85)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- Community 0
- Community 1
- Community 2
- Community 3
- Community 4
- Community 5
- Community 6
- Community 7
- Community 8
- Community 9
- Community 10
- Community 11
- Community 12
- Community 13
- Community 14
- Community 15
- Community 16
- Community 17
- Community 18
- Community 19
- Community 20
- Community 21
- Community 22
- Community 23
- Community 24
- Community 25
- Community 26
- Community 27
- Community 28
- Community 29
- Community 30
- Community 31

## God Nodes (most connected - your core abstractions)
1. `next-intl` - 78 edges
2. `@heroui/react` - 72 edges
3. `react` - 50 edges
4. `getAccessToken()` - 42 edges
5. `request()` - 41 edges
6. `next` - 37 edges
7. `lucide-react` - 28 edges
8. `opsErrorMessage()` - 25 edges
9. `useOpsData()` - 23 edges
10. `vitest` - 21 edges

## Surprising Connections (you probably didn't know these)
- `LoginPage()` --calls--> `useLoginDialog()`  [EXTRACTED]
  app/(auth)/login/page.tsx → src/features/auth/LoginDialog.tsx
- `CompanyPublicPageClient()` --calls--> `PlanCard()`  [EXTRACTED]
  app/companies/[domain]/CompanyPublicPageClient.tsx → src/features/home/planCatalog/PlanCard.tsx
- `RootLayout()` --calls--> `SiteConfigProvider()`  [EXTRACTED]
  app/layout.tsx → src/features/site/SiteConfigProvider.tsx
- `OpsCapturePage()` --calls--> `CapturePanel()`  [EXTRACTED]
  app/ops/links/[linkId]/capture/page.tsx → src/features/ops/capture/CapturePanel.tsx
- `OpsCapturePage()` --indirect_call--> `getActiveCapture()`  [INFERRED]
  app/ops/links/[linkId]/capture/page.tsx → src/lib/api/ops.ts

## Import Cycles
- 3-file cycle: `src/features/home/HomePlanCatalog.tsx -> src/features/home/planCatalog/PlanCard.tsx -> src/lib/api/publicCatalog.ts -> src/features/home/HomePlanCatalog.tsx`

## Communities (32 total, 9 thin omitted)

### Community 0 - "Community 0"
Cohesion: 0.06
Nodes (87): OpsCapturePage(), fail(), loadLocal(), markFailed(), start(), upload(), OpsMappingPage(), save() (+79 more)

### Community 1 - "Community 1"
Cohesion: 0.09
Nodes (40): LoginPage(), geistMono, geistSans, vazirmatn, RootLayout(), NAV, OpsLayout(), OpsShell() (+32 more)

### Community 2 - "Community 2"
Cohesion: 0.09
Nodes (24): NewCompanyPage(), @testing-library/react, @testing-library/user-event, vitest, CompanyRegistrationPage(), ApprovalQueue(), CompanyReviewCard(), Info() (+16 more)

### Community 3 - "Community 3"
Cohesion: 0.12
Nodes (34): CompanyPanelPageClient(), CompanyPanelPage(), instant, PanelPage(), lucide-react, ContinueRegistration(), resolveState(), StepProgress() (+26 more)

### Community 4 - "Community 4"
Cohesion: 0.07
Nodes (26): OpsSitePageClient(), instant, OpsSitePage(), @heroui/react, ORDINALS, CaptureMode, CapturePanel(), REVIEW_LABEL_KEY (+18 more)

### Community 5 - "Community 5"
Cohesion: 0.14
Nodes (21): localizeError(), LoginForm(), handleRequest(), handleVerify(), LoginFormProps, Step, OtpForm(), OtpFormProps (+13 more)

### Community 6 - "Community 6"
Cohesion: 0.15
Nodes (16): CatalogFilterValues, CatalogSearchParams, HomePlanCatalog(), RESOURCE_FIELDS, SERVICE_FOR_PLAN, serviceOf(), ServiceTab, SortOrder (+8 more)

### Community 7 - "Community 7"
Cohesion: 0.09
Nodes (23): dependencies, geist@^1.8.1, handsontable@^18.1.2, @handsontable/react-wrapper@^18.1.2, @heroui/react@3.2.6, @heroui/styles@3.2.6, @internationalized/date@^3.12.4, lucide-react@^1.61.0 (+15 more)

### Community 8 - "Community 8"
Cohesion: 0.09
Nodes (22): devDependencies, jsdom@^25.0.1, tailwindcss@^4, @tailwindcss/turbopack@^4, @testing-library/jest-dom@^6.6.3, @testing-library/react@^16.1.0, @testing-library/user-event@^14.5.2, @types/node@^20 (+14 more)

### Community 9 - "Community 9"
Cohesion: 0.17
Nodes (15): CompanyCard(), RESOURCE_KEYS, RESOURCE_LABELS, RESOURCE_VALUES, ResultKind, searchIndexFrom(), SearchResult, SERVER_LOCATIONS (+7 more)

### Community 10 - "Community 10"
Cohesion: 0.19
Nodes (15): emptyBinding(), FieldBindingPanel(), resolveColumnBinding(), initialBindings(), MappingWorkspace(), changePlan(), TableSwitcher(), ExtractedTable (+7 more)

### Community 11 - "Community 11"
Cohesion: 0.22
Nodes (11): MainContent(), MainPage(), AboutTorb(), FaqSection(), HowItWorks(), MainBody(), RecentlyApproved(), getRecentCompanies() (+3 more)

### Community 12 - "Community 12"
Cohesion: 0.11
Nodes (18): compilerOptions, allowJs, esModuleInterop, incremental, isolatedModules, jsx, lib, module (+10 more)

### Community 13 - "Community 13"
Cohesion: 0.19
Nodes (12): CompanyPublicPageClient(), CompanyPublicPage(), instant, Props, CompaniesPage(), instant, SearchPage(), SearchPageClient() (+4 more)

### Community 14 - "Community 14"
Cohesion: 0.23
Nodes (13): FooterLinkGroup, HomeFooter(), SiteConfigContext, SiteConfigProvider(), asNumber(), asNumberList(), asRecord(), asString() (+5 more)

### Community 15 - "Community 15"
Cohesion: 0.13
Nodes (14): @fontsource-variable/vazirmatn@^5.3.0, react-aria@^3.52.1, @react-aria/utils@^3.34.1, tailwind-variants@^3.3.1, @testing-library/dom@^10.4.0, name, packageManager, private (+6 more)

### Community 16 - "Community 16"
Cohesion: 0.18
Nodes (13): blocks, desc, extra, name, position, blocks, position, components (+5 more)

### Community 17 - "Community 17"
Cohesion: 0.24
Nodes (12): PlanPagination(), SORT_OPTIONS, SortAndPageSizeControls(), SortOrder, CatalogFilters(), CheckboxList(), CheckboxOption, CompanyFilterSection() (+4 more)

### Community 18 - "Community 18"
Cohesion: 0.20
Nodes (9): RESOURCE_LABELS, RESOURCE_OPTIONS, ResourceKey, RESOURCES_BY_TYPE, SERVER_LOCATIONS, SERVICE_TYPES, ServiceType, ServiceTypeKey (+1 more)

### Community 19 - "Community 19"
Cohesion: 0.29
Nodes (4): EMPTY_PRICE, PriceRange, PriceRangeBox(), summarize()

### Community 20 - "Community 20"
Cohesion: 0.33
Nodes (5): eslintConfig, eslint@^9, eslint-config-next@16.4.2, eslint, eslint-config-next

### Community 21 - "Community 21"
Cohesion: 0.33
Nodes (4): nextConfig, withNextIntl, dotenv@^18.0.9, dotenv

### Community 22 - "Community 22"
Cohesion: 0.33
Nodes (6): scripts, build, dev, lint, start, test

## Knowledge Gaps
- **7 isolated node(s):** `Frontend Agent Rules`, `Frontend Project Guide`, `File Icon`, `Globe Icon`, `Next.js Logo` (+2 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 139 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **9 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `next-intl` connect `Community 1` to `Community 0`, `Community 2`, `Community 3`, `Community 4`, `Community 5`, `Community 6`, `Community 7`, `Community 9`, `Community 10`, `Community 11`, `Community 13`, `Community 14`, `Community 15`, `Community 17`, `Community 18`, `Community 19`, `Community 21`?**
  _High betweenness centrality (0.189) - this node is a cross-community bridge._
- **What connects `Frontend Agent Rules`, `Frontend Project Guide`, `File Icon` to the rest of the system?**
  _7 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Community 0` be split into smaller, more focused modules?**
  _Cohesion score 0.06318681318681318 - nodes in this community are weakly interconnected._
- **Why does `@heroui/react` connect `Community 4` to `Community 0`, `Community 1`, `Community 2`, `Community 3`, `Community 5`, `Community 6`, `Community 7`, `Community 9`, `Community 10`, `Community 11`, `Community 13`, `Community 14`, `Community 15`, `Community 17`, `Community 18`, `Community 19`?**
  _High betweenness centrality (0.157) - this node is a cross-community bridge._
- **Should `Community 1` be split into smaller, more focused modules?**
  _Cohesion score 0.08691834942932397 - nodes in this community are weakly interconnected._
- **Why does `react` connect `Community 0` to `Community 1`, `Community 2`, `Community 3`, `Community 4`, `Community 5`, `Community 6`, `Community 7`, `Community 9`, `Community 10`, `Community 11`, `Community 13`, `Community 14`, `Community 15`, `Community 17`, `Community 18`, `Community 19`?**
  _High betweenness centrality (0.127) - this node is a cross-community bridge._
- **Should `Community 2` be split into smaller, more focused modules?**
  _Cohesion score 0.08928571428571429 - nodes in this community are weakly interconnected._