# Graph Report - backend  (2026-11-04)

## Corpus Check
- Corpus is ~39,299 words - fits in a single context window. You may not need a graph.

## Summary
- 1768 nodes · 3173 edges · 124 communities (73 shown, 51 thin omitted)
- Extraction: 83% EXTRACTED · 17% INFERRED · 0% AMBIGUOUS · INFERRED: 538 edges (avg confidence: 0.93)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- Admin Console Module
- Accounts Module
- Catalog Module
- Companies Module
- Admin Console Module 4
- Companies Module 5
- Admin Console Module 6
- Admin Console Module 7
- Accounts Module 8
- Accounts Module 9
- Accounts Module 10
- Admin Console Module 11
- Admin Console Module 12
- Admin Console Module 13
- Companies Module 14
- Companies Module 15
- Accounts Module 16
- Admin Console Module 17
- Admin Console Module 18
- Admin Console Module 19
- Admin Console Module 20
- Admin Console Module 21
- Companies Module 22
- Catalog Module 23
- Admin Console Module 24
- Admin Console Module 25
- Admin Console Module 26
- Admin Console Module 27
- Admin Console Module 28
- Companies Module 29
- Admin Console Module 30
- Admin Console Module 31
- Admin Console Module 32
- Admin Console Module 33
- Accounts Module 34
- Admin Console Module 35
- Accounts Module 36
- Notifications Module
- Admin Console Module 38
- Admin Console Module 39
- Companies Module 40
- Companies Module 41
- Companies Module 42
- Companies Module 43
- Catalog Module 44
- Admin Console Module 45
- Admin Console Module 46
- Companies Module 47
- Notifications Module 48
- Companies Module 49
- Notifications Module 50
- Notifications Module 51
- Companies Module 52
- Admin Console Module 53
- Admin Console Module 54
- Companies Module 55
- Companies Module 56
- Admin Console Module 57
- Admin Console Module 58
- Notifications Module 59
- Accounts Module 60
- Notifications Module 61
- Accounts Module 62
- Admin Console Module 63
- Catalog Module 64
- Companies Module 65
- Accounts Module 66
- Admin Console Module 67
- Companies Module 68
- Companies Module 69
- Accounts Module 70
- Accounts Module 71
- Accounts Module 72
- Admin Console Module 74
- Companies Module 75
- Admin Console Module 76
- Accounts Module 77
- Admin Console Module 78
- Admin Console Module 79
- Companies Module 81
- Notifications Module 82
- Notifications Module 83
- Notifications Module 84
- Accounts Module 87
- Admin Console Module 88
- Companies Module 89
- Admin Console Module 91
- Admin Console Module 92
- Admin Console Module 93
- Admin Console Module 94
- Admin Console Module 95
- Catalog Module 96

## God Nodes (most connected - your core abstractions)
1. `Link` - 76 edges
2. `ApiError` - 57 edges
3. `Company` - 38 edges
4. `OperatorOnlyView` - 30 edges
5. `TimestampedModel` - 29 edges
6. `User` - 25 edges
7. `Site` - 25 edges
8. `PlanRecord` - 24 edges
9. `register_company()` - 24 edges
10. `CaptureSession` - 23 edges

## Surprising Connections (you probably didn't know these)
- `test_request_rejects_blocked_user()` --uses--> `User`  [INFERRED]
  src/accounts/tests/test_contract_otp_request.py → src/accounts/models.py
- `test_verify_blocked_user()` --uses--> `User`  [INFERRED]
  src/accounts/tests/test_contract_otp_verify.py → src/accounts/models.py
- `test_feature_has_no_sitemap_step()` --uses--> `Site`  [INFERRED]
  src/admin_console/tests/test_regression.py → src/admin_console/models.py
- `test_onboard_site_returns_201_with_onboarding_state()` --uses--> `Site`  [INFERRED]
  src/admin_console/tests/test_site_onboarding.py → src/admin_console/models.py
- `rerun_link_stages()` --uses--> `Link`  [INFERRED]
  src/admin_console/services.py → src/admin_console/models.py

## Import Cycles
- None detected.

## Communities (124 total, 51 thin omitted)

### Community 0 - "Admin Console Module"
Cohesion: 0.05
Nodes (54): ApiError, AlertListView, ApprovalQueueView, AuthenticatedView, _capture_payload(), CaptureFailView, CaptureStartView, ClassificationView (+46 more)

### Community 1 - "Accounts Module"
Cohesion: 0.06
Nodes (23): LogoutView, OtpRequestView, OtpVerifyView, SessionView, _set_refresh_cookie(), TokenRefreshView, ErrorSerializer, OtpRequestInput (+15 more)

### Community 2 - "Catalog Module"
Cohesion: 0.06
Nodes (16): AdminConsoleInterface, PublishedPlansView, RecentCompaniesView, SiteConfigView, _build_dynamic_filter_fields(), _filter_for_field(), _make_number_method(), method() (+8 more)

### Community 3 - "Companies Module"
Cohesion: 0.07
Nodes (27): AdminOnlyView, AuthenticatedView, _company_payload(), CompanyDetailView, CompanyLinksView, CompanyListCreateView, OwnershipTransferView, PanelEntryView (+19 more)

### Community 4 - "Admin Console Module 4"
Cohesion: 0.07
Nodes (20): budget_allows(), budget_exhausted(), current_budget(), extract_plans(), infer_and_extract_plans(), infer_plan_type(), LlmBudget, LlmBudgetExhausted (+12 more)

### Community 5 - "Companies Module 5"
Cohesion: 0.06
Nodes (23): test_filter_preserves_numeric_format_arguments(), test_filter_redacts_secrets_in_record_message_and_args(), test_mask_text_redacts_code_and_token_but_keeps_phone(), domtrack_table_result(), _el(), make_trace(), make_trace_bytes(), company_registered() (+15 more)

### Community 6 - "Admin Console Module 6"
Cohesion: 0.06
Nodes (19): apply_link_policy(), crawl_candidate_links(), LinkDiscoverer, _backend_root(), _imports(), _sources(), test_crawl4ai_is_imported_only_by_discovery(), test_domtrack_is_imported_only_by_its_adapter() (+11 more)

### Community 7 - "Admin Console Module 7"
Cohesion: 0.08
Nodes (23): ChangeRecord, Kind, Meta, ReplayRun, Meta, State, _change(), _classification_for_path() (+15 more)

### Community 8 - "Accounts Module 8"
Cohesion: 0.06
Nodes (14): request_otp(), CapturingSmsGateway, ConsoleSmsGateway, get_gateway(), HttpSmsGateway, SmsGateway, admin_user(), api_client() (+6 more)

### Community 9 - "Accounts Module 9"
Cohesion: 0.07
Nodes (15): AccountsInterface, get_user_role(), is_authenticated(), resolve_current_user(), user_from_request(), issue_tokens(), _register_failed_attempt(), resolve_return_url() (+7 more)

### Community 10 - "Accounts Module 10"
Cohesion: 0.07
Nodes (21): bump_failed_attempts(), bump_source_counter(), clear_lockout(), code_ttl(), delete_code(), _failure_key(), generate_code(), get_code() (+13 more)

### Community 11 - "Admin Console Module 11"
Cohesion: 0.06
Nodes (5): link_deny_extensions(), link_deny_segments(), _list(), step_definitions(), step_keys()

### Community 12 - "Admin Console Module 12"
Cohesion: 0.07
Nodes (6): list_model(), PlanSchema, required_fields(), required_keys(), SchemaField, test_schema_is_immutable_and_code_defined()

### Community 13 - "Admin Console Module 13"
Cohesion: 0.09
Nodes (10): capture_headless(), compare_replay(), diff_traces(), DomtrackCaptureError, DomtrackClient, extract_tables(), is_trace(), label_tables() (+2 more)

### Community 14 - "Companies Module 14"
Cohesion: 0.07
Nodes (9): AccountsConfig, AdminConsoleConfig, AnalyticsConfig, CatalogConfig, CompaniesConfig, CoreConfig, NormalizerConfig, NotificationsConfig (+1 more)

### Community 15 - "Companies Module 15"
Cohesion: 0.11
Nodes (16): CompanyRegistrationDraft, Meta, CompanyStepProgress, Meta, State, abandon_step(), can_manage_plans(), record_verification_decision() (+8 more)

### Community 16 - "Accounts Module 16"
Cohesion: 0.09
Nodes (10): User, Meta, Status, test_first_login_creates_user(), test_implicit_user_has_unusable_password(), test_password_check_never_succeeds_for_otp_user(), test_second_login_reuses_user(), test_admin_wins_over_ops() (+2 more)

### Community 17 - "Admin Console Module 17"
Cohesion: 0.12
Nodes (19): api_client(), approved_company(), _artifact_storage(), _auth(), auth_client(), _clear_throttle_cache(), company(), extracted_link() (+11 more)

### Community 18 - "Admin Console Module 18"
Cohesion: 0.09
Nodes (13): ClassificationRegex, Kind, Meta, ExtractedTableRow, Meta, PlanExclusion, Meta, SemanticLabel (+5 more)

### Community 19 - "Admin Console Module 19"
Cohesion: 0.11
Nodes (12): Site, MaintenanceState, Meta, approval_queue(), record_decision(), _pending_company(), test_approval_creates_site_in_onboarding_and_verifies_company(), test_approval_enqueues_automatic_site_pipeline_after_commit() (+4 more)

### Community 20 - "Admin Console Module 20"
Cohesion: 0.11
Nodes (16): add_links_manually(), due_links(), due_links_for_site(), extract_link_tables(), _materialize(), models_q_last_replay(), onboard_site(), _persist_table() (+8 more)

### Community 21 - "Admin Console Module 21"
Cohesion: 0.11
Nodes (19): Link, Meta, PipelineStage, ReviewState, Source, test_discovery_stores_candidate_links(), test_empty_crawl_keeps_site_in_onboarding_and_notifies(), test_manual_links_are_stored() (+11 more)

### Community 22 - "Companies Module 22"
Cohesion: 0.09
Nodes (14): _AppendOnlyMixin, Meta, CreditLedgerEntry, Direction, Meta, Reason, VerificationDecision, Meta (+6 more)

### Community 23 - "Catalog Module 23"
Cohesion: 0.12
Nodes (13): _classified_link(), test_ignored_plan_is_retired_and_stays_excluded_after_reextraction(), test_incomplete_plan_is_not_published(), test_kept_plan_is_not_retired(), test_publish_upserts_by_source_site_natural_key(), test_publish_writes_a_record_with_provenance(), test_removal_retires_the_published_record(), PublishedRecord (+5 more)

### Community 24 - "Admin Console Module 24"
Cohesion: 0.11
Nodes (8): Command, recover_site_pipeline_tasks(), run_capture_task(), run_classification_task(), run_extraction_task(), run_labeling_task(), run_replay_task(), run_site_pipeline_task()

### Community 25 - "Admin Console Module 25"
Cohesion: 0.12
Nodes (15): ExtractedTable, Meta, TableClassification, Meta, test_a_page_may_hold_several_plans_tables(), test_budget_exhaustion_parks_the_link(), test_classification_then_extraction_runs_per_table(), test_classifier_accepts_only_classification_fields() (+7 more)

### Community 26 - "Admin Console Module 26"
Cohesion: 0.09
Nodes (7): test_classification_endpoint_returns_verdicts(), test_classification_returns_202_on_budget_exhaustion(), test_labeling_writes_semantic_labels(), test_operator_can_toggle_a_plan_exclusion(), test_plan_endpoint_extracts_and_lists(), test_plan_endpoint_requires_a_plans_table(), test_publish_endpoint_publishes_plan_records()

### Community 27 - "Admin Console Module 27"
Cohesion: 0.12
Nodes (7): materialize(), open_trace(), read_trace(), save_trace(), _trace_key(), test_save_trace_writes_under_a_uuid_key_and_round_trips(), test_trace_model_has_no_body_column()

### Community 28 - "Admin Console Module 28"
Cohesion: 0.12
Nodes (13): CaptureSession, Meta, Mode, State, candidate_link(), test_capture_failure_is_dead_lettered(), test_capture_refuses_a_non_kept_link(), test_capture_stores_a_headless_trace() (+5 more)

### Community 29 - "Companies Module 29"
Cohesion: 0.17
Nodes (16): _Capture, _mark_charged(), _operator_client(), _payload(), test_v10_ownership_refused_and_archival(), test_v11_owner_scoping_returns_not_found(), test_v12_runtime_config_and_log_masking(), test_v1_register_company() (+8 more)

### Community 30 - "Admin Console Module 30"
Cohesion: 0.19
Nodes (18): alert_raised(), capture_failed(), capture_started(), _emit(), extraction_completed(), extraction_empty(), labeling_run(), labeling_skipped() (+10 more)

### Community 31 - "Admin Console Module 31"
Cohesion: 0.13
Nodes (13): LlmCostLedger, Meta, Period, Scope, Stage, _exhaust_budget(), _fake_chat_response(), test_a_restored_budget_resumes_the_stage() (+5 more)

### Community 32 - "Admin Console Module 32"
Cohesion: 0.16
Nodes (12): PlanRecord, Meta, _add_classified_table(), test_duplicate_plan_names_across_tables_get_unique_link_keys(), test_extraction_accepts_name_price_without_server_specs(), test_extraction_output_contains_no_selector_or_formula(), test_extraction_rejects_missing_or_zero_price(), test_low_confidence_plans_pause_and_preserve_existing_records() (+4 more)

### Community 33 - "Admin Console Module 33"
Cohesion: 0.13
Nodes (6): Migration, _kept_link(), test_due_links_excludes_suspended_sites_and_non_kept_links(), test_due_links_skips_suspended_sites(), test_scheduler_command_enqueues_one_task_per_due_link(), test_distinct_link_retries_are_enqueued_independently()

### Community 34 - "Accounts Module 34"
Cohesion: 0.12
Nodes (6): Migration, ensure_role_groups(), test_request_rejects_blocked_user(), role_groups(), test_events_never_log_the_unmasked_phone(), test_trace_content_is_never_logged()

### Community 35 - "Admin Console Module 35"
Cohesion: 0.13
Nodes (10): _column_label(), _domtrack_table(), extract_link_plans(), label_link_tables(), _natural_key(), _normalize_price_scale(), _plan_is_complete(), _plan_values_identity() (+2 more)

### Community 36 - "Accounts Module 36"
Cohesion: 0.17
Nodes (6): test_lockout_after_threshold_blocks_request_and_verify(), test_attempts_increment_and_invalidate(), test_correct_code_after_failed_attempts_still_works(), test_absent_code_is_incorrect(), test_expired_code_is_incorrect_not_expired(), test_unknown_outcome_is_rejected()

### Community 37 - "Notifications Module"
Cohesion: 0.22
Nodes (6): _AdminOnlyView, NotificationInboxView, NotificationRecipientDeactivateView, NotificationRecipientListCreateView, RecipientSerializer, Meta

### Community 38 - "Admin Console Module 38"
Cohesion: 0.12
Nodes (6): Migration, Migration, Migration, Migration, Migration, Migration

### Community 39 - "Admin Console Module 39"
Cohesion: 0.23
Nodes (13): CaptureSessionAdmin, ChangeRecordAdmin, ClassificationRegexAdmin, ExtractedTableAdmin, FailureAlertAdmin, LinkAdmin, LlmCostLedgerAdmin, PlanRecordAdmin (+5 more)

### Community 40 - "Companies Module 40"
Cohesion: 0.13
Nodes (7): companies_awaiting_verification(), company_or_error(), current_step(), list_owned_companies(), owned_company_or_error(), step_progress(), step_progress_payload()

### Community 41 - "Companies Module 41"
Cohesion: 0.18
Nodes (7): api_exception_handler(), error_body(), _register(), test_approval_unlocks_verification_step(), test_locked_verification_step_is_refused(), test_step_one_is_enterable(), test_unknown_step_is_not_found()

### Community 42 - "Companies Module 42"
Cohesion: 0.14
Nodes (5): canonical_domain(), normalize_domain(), duplicate_domain_ids(), pending_approval_payload(), validate_company_fields()

### Community 43 - "Companies Module 43"
Cohesion: 0.21
Nodes (9): Company, Meta, VerificationStatus, _register(), test_charged_but_unverified_names_verified(), test_gate_endpoint(), test_unverified_and_uncharged_names_both(), test_verified_and_charged_is_allowed() (+1 more)

### Community 44 - "Catalog Module 44"
Cohesion: 0.20
Nodes (5): metrics_snapshot(), publish_link_plans(), retire_missing_plans(), set_plan_excluded(), CatalogInterface

### Community 45 - "Admin Console Module 45"
Cohesion: 0.21
Nodes (10): FailureAlert, Meta, State, alerts(), link_failure_payload(), _runs(), test_a_fall_resolves_the_alert(), test_a_later_rise_opens_a_new_alert() (+2 more)

### Community 46 - "Admin Console Module 46"
Cohesion: 0.18
Nodes (3): classify_tables_for_link(), _numeric_cell(), TableClassifier

### Community 47 - "Companies Module 47"
Cohesion: 0.27
Nodes (10): register_company(), _payload(), test_create_company_pending_unverified(), test_create_company_without_trailing_slash(), test_domain_is_normalized_and_preserves_www_for_site_crawling(), test_internal_number_is_optional(), test_list_is_owner_scoped(), test_mandatory_field_missing_names_field_and_creates_nothing() (+2 more)

### Community 48 - "Notifications Module 48"
Cohesion: 0.17
Nodes (6): Notification, Meta, Severity, NotificationRecipient, Meta, inbox_for_user()

### Community 49 - "Companies Module 49"
Cohesion: 0.21
Nodes (5): CompanyAdmin, CompanyRegistrationDraftAdmin, CompanyStepProgressInline, CreditLedgerEntryAdmin, VerificationDecisionAdmin

### Community 50 - "Notifications Module 50"
Cohesion: 0.21
Nodes (5): active_recipients(), deactivate_recipient(), deliver(), notify(), resolve_notifications()

### Community 51 - "Notifications Module 51"
Cohesion: 0.27
Nodes (7): _auth(), _clear_throttle_cache(), operator(), operator_client(), other_user(), role_groups(), user_client()

### Community 52 - "Companies Module 52"
Cohesion: 0.27
Nodes (7): archive_companies_for_user(), _register(), test_abuse_state_is_readable(), test_archival_sets_flags_and_keeps_records(), test_company_is_never_hard_deleted(), test_in_product_ownership_transfer_is_refused(), test_ownership_never_changes()

### Community 53 - "Admin Console Module 53"
Cohesion: 0.18
Nodes (6): Trace, Meta, Origin, fail_capture(), _run_with_retries(), start_capture()

### Community 54 - "Admin Console Module 54"
Cohesion: 0.24
Nodes (7): _failing_then_ok(), capture_headless(), test_a_transient_failure_is_retried_and_then_succeeds(), test_exhausted_retries_dead_letter_the_link(), test_one_link_failing_does_not_block_another(), test_rerunning_dead_lettered_capture_resumes_at_capture(), test_rerunning_dead_lettered_link_with_saved_trace_skips_capture()

### Community 55 - "Companies Module 55"
Cohesion: 0.29
Nodes (7): api_client(), auth_client(), company(), operator(), other_owner(), owner(), role_groups()

### Community 56 - "Companies Module 56"
Cohesion: 0.33
Nodes (9): _register(), test_amount_must_be_positive(), test_charge_then_decharge_projection(), test_credit_endpoint(), test_credit_is_per_company(), test_entries_are_immutable(), test_projection_equals_running_total(), test_projection_starts_at_zero() (+1 more)

### Community 57 - "Admin Console Module 57"
Cohesion: 0.24
Nodes (4): Migration, Migration, Migration, Migration

### Community 58 - "Admin Console Module 58"
Cohesion: 0.24
Nodes (5): discover_and_store_links(), evaluate_failure_alert(), _notify_empty_discovery(), recompute_failure_rate(), NotificationsInterface

### Community 59 - "Notifications Module 59"
Cohesion: 0.27
Nodes (6): add_recipient(), test_dedup_key_prevents_duplicates(), test_failed_delivery_is_recorded_without_blocking_others(), test_inbox_reaches_active_recipients_only(), test_notify_creates_one_delivery_per_active_recipient(), test_recipients_are_admin_managed()

### Community 61 - "Notifications Module 61"
Cohesion: 0.22
Nodes (4): NotificationRecipientInput, NotificationSerializer, Meta, parse_input()

### Community 62 - "Accounts Module 62"
Cohesion: 0.25
Nodes (3): test_regression_protocol_relative_url_is_rejected(), test_regression_root_allowlist_does_not_match_every_path(), test_regression_superuser_is_an_admin()

### Community 63 - "Admin Console Module 63"
Cohesion: 0.22
Nodes (4): ExtractedTableColumn, Meta, test_empty_extraction_records_no_tables_and_flags(), test_extraction_persists_tables_with_domtrack_metadata()

### Community 66 - "Accounts Module 66"
Cohesion: 0.32
Nodes (3): _login(), test_logout_clears_cookie_and_revokes(), test_refresh_rotates_access_token()

### Community 68 - "Companies Module 68"
Cohesion: 0.39
Nodes (5): _register(), test_direct_full_panel_redirects_when_unverified(), test_full_panel_renders_when_verified(), test_panel_entry_continue_view_for_pending(), test_panel_entry_full_panel_for_verified()

### Community 71 - "Accounts Module 71"
Cohesion: 0.29
Nodes (3): backfill_unusable_passwords(), Migration, noop()

### Community 75 - "Companies Module 75"
Cohesion: 0.48
Nodes (5): _register(), test_crawl_endpoint_blocked_when_uncharged(), test_crawl_endpoint_enabled_when_charged(), test_enabling_crawl_costs_nothing(), test_enabling_crawl_requires_charged()

### Community 77 - "Accounts Module 77"
Cohesion: 0.47
Nodes (3): _FakeRequest, test_blocked_user_is_treated_as_guest(), test_invalid_token_is_guest()

### Community 78 - "Admin Console Module 78"
Cohesion: 0.53
Nodes (5): stub_llm(), classify_extract_tables(), classify_tables(), extract_plans(), _raise_if_exhausted()

### Community 81 - "Companies Module 81"
Cohesion: 0.53
Nodes (4): _register(), test_credit_is_scoped_per_company(), test_entry_payload_reflects_selected_company_only(), test_switcher_lists_only_selected_fields_per_company()

### Community 82 - "Notifications Module 82"
Cohesion: 0.47
Nodes (3): NotificationAdmin, NotificationDeliveryAdmin, NotificationRecipientAdmin

### Community 84 - "Notifications Module 84"
Cohesion: 0.33
Nodes (4): NotificationDelivery, Channel, Meta, State

### Community 89 - "Companies Module 89"
Cohesion: 0.60
Nodes (3): _register(), test_anonymous_requests_are_refused(), test_other_owners_company_is_not_found_on_every_endpoint()

## Knowledge Gaps
- **51 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `ApiError` connect `Admin Console Module` to `Accounts Module`, `Companies Module`, `Accounts Module 36`, `Companies Module 69`, `Notifications Module`, `Accounts Module 8`, `Accounts Module 9`, `Companies Module 41`, `Companies Module 40`, `Companies Module 42`, `Companies Module 75`, `Companies Module 15`, `Companies Module 22`, `Companies Module 56`, `Notifications Module 61`?**
  _High betweenness centrality (0.070) - this node is a cross-community bridge._
- **Are the 68 inferred relationships involving `Link` (e.g. with `get_link_or_error()` and `LinkRerunView`) actually correct?**
  _`Link` has 68 INFERRED edges - model-reasoned connections that need verification._
- **Should `Admin Console Module` be split into smaller, more focused modules?**
  _Cohesion score 0.0516404581634634 - nodes in this community are weakly interconnected._
- **Why does `Link` connect `Admin Console Module 21` to `Admin Console Module`, `Catalog Module`, `Admin Console Module 4`, `Admin Console Module 17`, `Admin Console Module 18`, `Admin Console Module 20`, `Catalog Module 23`, `Admin Console Module 24`, `Admin Console Module 25`, `Admin Console Module 26`, `Admin Console Module 28`, `Admin Console Module 31`, `Admin Console Module 32`, `Admin Console Module 33`, `Admin Console Module 35`, `Catalog Module 44`, `Admin Console Module 46`, `Admin Console Module 53`, `Admin Console Module 54`, `Admin Console Module 58`, `Admin Console Module 63`?**
  _High betweenness centrality (0.065) - this node is a cross-community bridge._
- **Are the 53 inferred relationships involving `ApiError` (e.g. with `TokenRefreshView` and `.post()`) actually correct?**
  _`ApiError` has 53 INFERRED edges - model-reasoned connections that need verification._
- **Should `Accounts Module` be split into smaller, more focused modules?**
  _Cohesion score 0.05639097744360902 - nodes in this community are weakly interconnected._
- **Why does `TimestampedModel` connect `Admin Console Module 18` to `Admin Console Module 32`, `Admin Console Module 7`, `Companies Module 43`, `Admin Console Module 45`, `Admin Console Module 31`, `Companies Module 15`, `Accounts Module 16`, `Notifications Module 48`, `Admin Console Module 19`, `Notifications Module 84`, `Admin Console Module 21`, `Admin Console Module 53`, `Catalog Module 23`, `Companies Module 22`, `Admin Console Module 25`, `Admin Console Module 28`, `Admin Console Module 63`?**
  _High betweenness centrality (0.057) - this node is a cross-community bridge._