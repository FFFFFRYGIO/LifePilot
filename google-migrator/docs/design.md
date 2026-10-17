# Design: schemat, mapowanie pól, straty, idempotencja

Status: **zaakceptowane** 2026-09-18. Decyzje: Django + PostgreSQL, marker w notatkach (opcja A),
migracja jednorazowa bez synchronizacji, MS tylko do odczytu, konto Microsoft osobiste.

## 1. Weryfikacja dokumentacji (2026-09-18)

| Pytanie | Wynik | Źródło |
|---|---|---|
| Czy Google Tasks `due` przyjmuje godzinę? | **Nie.** „Only date information is recorded; the time portion of the timestamp is discarded when setting this field. It isn't possible to read or write the time that a task is scheduled for using the API.” | developers.google.com/workspace/tasks/reference/rest/v1/tasks |
| Limity Google Tasks | `title` ≤ 1024, `notes` ≤ 8192 znaków; `links` i `parent` tylko do odczytu (rodzica ustawia parametr `parent` przy `insert`) | j.w. |
| Uprawnienia Graph | `Tasks.Read` wystarcza do list, zadań, checklist i załączników | learn.microsoft.com/graph/api/resources/todotask |
| ID zadania MS | zmienia się po przeniesieniu zadania do innej listy | j.w. |
| Statusy MS | `notStarted`, `inProgress`, `completed`, `waitingOnOthers`, `deferred` | j.w. |

**Wniosek dla terminów:** `due` = data z `dueDateTime` liczona **w strefie `dueDateTime.timeZone`**
(nie po konwersji do UTC, bo przesunęłoby to dzień), wysyłana jako `YYYY-MM-DDT00:00:00.000Z`.

## 2. Modele Django

```
Connection         provider[microsoft|google] UNIQUE, account_email,
                   access_token (Fernet), refresh_token (Fernet), expires_at, scopes,
                   status[ok|reauth_required], last_error, updated_at

MigrationSettings  singleton: importance_mode[prefix|separate_list|ignore], importance_prefix,
                   categories_mode[tags|ignore], extras_mode[notes|ignore] (przypomnienie/start/linki),
                   include_completed_days (NULL = pomijaj ukończone), add_recovery_marker=True

-- staging: snapshot MS, z niego czyta podgląd; odświeżany na żądanie
MsList             ms_list_id UNIQUE, display_name, wellknown_name, is_shared, fetched_at
MsTask             ms_task_id UNIQUE, ms_list FK, raw JSON, title, status, importance,
                   due_date, is_recurring, has_attachments, ms_last_modified,
                   content_hash, excluded BOOL, gone_from_ms BOOL, fetched_at
MsChecklistItem    ms_item_id UNIQUE, ms_task FK, display_name, is_checked, position

GoogleList         google_list_id UNIQUE, title, fetched_at

ListMapping        ms_list 1:1, mode[create_new|merge_into|skip], google_list_id NULL,
                   target_title

TaskMapping        ms_task_id UNIQUE, ms_list_id, google_list_id, google_task_id NULL,
                   content_hash, recovery_marker UNIQUE,
                   status[in_flight|synced|failed|skipped], attempts, last_error, last_synced_at
SubtaskMapping     ms_item_id UNIQUE, task_mapping FK, google_task_id NULL, status

TransferRun        status[pending|running|paused|completed|failed|cancelled],
                   settings_snapshot JSON, created_at, started_at, finished_at,
                   lease_owner, lease_expires_at, pause_requested,
                   total, done, failed, skipped
RunItem            run FK, ms_task_id, planned_payload JSON, status[pending|in_progress|done|failed|skipped],
                   attempt, error, result JSON, updated_at      UNIQUE(run, ms_task_id)
RunLogEntry        run FK, ts, level, message                  -- „log na żywo”

MigrationException kind[recurrence|error|ambiguous|truncated|attachment|reauth],
                   ms_task_id NULL, run FK NULL, details JSON,
                   status[open|resolved], resolution[skip|force|manual] NULL, created_at, resolved_at

AuditLog           ts, run FK NULL, provider, method, url, request_body, status_code,
                   response_body, duration_ms     -- tylko zapisy do Google; Authorization wycięte
```

## 3. Idempotencja i wznawianie (opcja A)

Google Tasks nie ma kluczy idempotencji, więc crash między `tasks.insert` a commitem w DB zostawiłby zadanie w Google bez śladu w bazie. Dlatego:

1. **Faza 1 (commit):** `TaskMapping(status=in_flight, recovery_marker=<16 hex>)`. `UNIQUE(ms_task_id)` blokuje drugie mapowanie.
2. **Zapis:** `tasks.insert`, w notatkach stopka `⟦mstodo:<marker>⟧`.
3. **Faza 2 (commit):** `google_task_id`, `status=synced`, `RunItem.done`.
4. **Wznowienie:** każde mapowanie `in_flight` jest najpierw uzgadniane. Listujemy docelową listę Google (z `showCompleted` i `showHidden`) i szukamy markera:
   jedno trafienie oznacza dopisanie ID, zero trafień bezpieczne ponowienie, więcej niż jedno wyjątek `ambiguous`.
5. Zadania `synced` są zawsze pomijane, niezależnie od runu.
6. Podzadania przechodzą tę samą procedurę przez `SubtaskMapping`, z markerem w notatkach podzadania.
7. W kroku „Zakończenie” stopki można usunąć (`tasks.patch` notes), ale dopiero gdy nie ma otwartych runów.

Worker: `run_worker` co kilka sekund bierze run `pending`/`running`, którego lease wygasł (`SELECT … FOR UPDATE SKIP LOCKED`), odnawia lease heartbeatem i przetwarza `RunItem` po kolei. Pauza to flaga sprawdzana między pozycjami.

## 4. Mapowanie pól

| MS To Do | Google Tasks | Sposób | Stratne? |
|---|---|---|---|
| `title` | `title` | wprost; >1024 → przycięcie + wyjątek `truncated` | przy >1024 |
| `body` (`text`/`html`) | `notes` | HTML → tekst; >8192 → przycięcie + wyjątek | **tak** |
| `dueDateTime` + `timeZone` | `due` | data w strefie zadania, `T00:00:00.000Z` | **tak**: godzina, strefa |
| `status` | `status` | `completed` → `completed`, reszta → `needsAction` | **tak** |
| `completedDateTime` | `completed` | wprost (etap 3 zweryfikuje, czy Google go przyjmuje) | możliwe |
| `checklistItems[]` | podzadania (`insert?parent=`) | `displayName` → `title`, `isChecked` → `status`, kolejność przez `previous` | **tak**: daty zaznaczenia |
| `recurrence` | – | najbliższe wystąpienie jako `due` + wyjątek z opisem wzorca | **tak** |
| `importance=high` | – | prefiks / osobna lista / ignoruj (Ustawienia) | **tak** |
| `categories` | – | `#tag` w notatkach / ignoruj | **tak** |
| `attachments` | – | nazwy plików w notatce + ostrzeżenie | **tak**: pliki |
| `linkedResources` | – | URL w notatce / ignoruj | **tak** |
| `reminderDateTime`, `isReminderOn` | – | linia w notatce / ignoruj | **tak** |
| `startDateTime` | – | linia w notatce / ignoruj | **tak** |
| `createdDateTime`, `lastModifiedDateTime` | – | pomijane | **tak** |
| kolejność w liście | pozycja | best-effort (kolejność z Graph) | **tak** |
| `extensions` | – | pomijane | **tak** |
| lista `flaggedEmails` | – | domyślnie `skip` (to maile z Outlooka) | – |

## 5. Straty: pełna lista

1. Godzina terminu: Google zapisuje tylko datę.
2. Strefa czasowa terminu: ginie. Dzień jest liczony w strefie zadania, żeby się nie przesunął.
3. Przypomnienia.
4. Data rozpoczęcia.
5. Powtarzalność: zostaje jedno wystąpienie i wyjątek do ręcznego odtworzenia.
6. Ważność / flaga.
7. Kategorie.
8. Załączniki: przenoszone są tylko nazwy plików.
9. Linked resources: tylko jako tekst w notatce.
10. Formatowanie treści: HTML zamieniany na tekst.
11. Przycięcie notatek >8192 i tytułów >1024 (z wyjątkiem w kolejce).
12. Statusy pośrednie: 5 stanów MS → 2 w Google.
13. Daty zaznaczenia pozycji checklisty.
14. Daty utworzenia i modyfikacji.
15. Kolejność zadań: tylko best-effort.
16. Rozszerzenia (`extensions`).
17. Zadanie przeniesione między listami w MS **pomiędzy** odświeżeniami snapshotu dostaje nowe ID.
    Podgląd oznacza je ostrzeżeniem „możliwy duplikat” (ten sam `content_hash` co zadanie już przeniesione).
