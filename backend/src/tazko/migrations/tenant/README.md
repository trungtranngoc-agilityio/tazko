# Company database migrations (`data/orgs/<slug>/tazko.db`)

Same rules as `migrations/control/`. No `org_id` columns: one file is one company.
When tasks run in parallel (M3, M5), reserve migration numbers up front in the milestone file to avoid collisions.

Tables planned here (build plan, Data model, plus the playbook fixes): people, projects, project_members, boards, board_access, board_stars, lists, cards, labels, card_labels, card_members, card_watchers, card_templates, checklists, checklist_items, comments, comment_reactions, card_links, card_votes, attachments, custom_field_defs, custom_field_values, cards_fts, events, notifications, board_templates, api_tokens, webhooks, webhook_deliveries.
