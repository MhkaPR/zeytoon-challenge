# recommendations — API

Base path: `/api/v1/recommendations`

## `POST /signals`

Record one viewer interaction.

```json
{
  "kind": "details_view",
  "plan_ids": [12, 15],
  "query": ""
}
```

Kinds:

| Kind | Meaning |
|---|---|
| `destination_visit` | user visited the provider/destination |
| `details_view` | user opened plan details |
| `search_impression` | user searched and saw these plans; requires `query` |

Response `200`:

```json
{"accepted": 2, "ignored": 0, "profile": "visitor"}
```

`profile` is `user`, `visitor`, or `none` when no identity is available.

Identity:

- authenticated request → user profile;
- otherwise the `visitor_id` cookie identifies an anonymous profile.

Throttle: `recommendation_signal` (default `30/min`), plus the recorder's per-viewer
per-minute cap.

## Ranking

There is no public ranking endpoint. Ranking is applied inside
`GET /api/v1/catalog/plans` for the default sort. Pass `X-Visitor-Id` or the `visitor_id`
cookie to personalize anonymous requests.
