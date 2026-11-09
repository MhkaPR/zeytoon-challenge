# recommendations — Data Model

## InterestProfile

Table: `recommendations_interestprofile` (Django default)

| Column | Type | Notes |
|---|---|---|
| `user_id` | FK, nullable | account owner |
| `visitor_id` | UUID, nullable | anonymous device owner |
| `position` | JSON | flat vector or list of cluster vectors |
| `uncertainty` | JSON | matching uncertainty vectors |
| `space_version` | varchar(64) | cache version the vectors belong to |
| `signal_count` | int | |
| `last_signal_at` | timestamp | indexed |
| `merged_into` | FK → user, nullable | tombstone for a merged visitor profile |

Constraints:

- exactly one owner: `user` XOR `visitor_id`;
- unique active profile per user;
- unique active profile per visitor.

## InterestSignal

Table: `recommendations_interestsignal` (Django default)

| Column | Type | Notes |
|---|---|---|
| `profile_id` | FK | |
| `kind` | varchar(32) | `destination_visit` / `details_view` / `search_impression` |
| `plan_ids` | JSON | plan ids involved |
| `query` | varchar(255) | search impression query |
| `weight` | float | noise used in the update |

Indexes: `(profile, -created_at)` and `(kind)`.

## Cache keys

| Key | Purpose |
|---|---|
| `recommendations:space:v1:{version}` | fitted plan-space bundle |
| `recommendations:cap:{identity}:{minute}` | per-viewer signal cap |

## Space version

The version string combines:

- latest `published_at`;
- number of plans;
- SHA-1 of plan ids/titles;
- semantic configuration (dimensions, features, n-grams, random state).

Profiles whose `space_version` differs from the current version are treated as cold start
until rebuilt.
