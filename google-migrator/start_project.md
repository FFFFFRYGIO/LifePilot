# Projekt: MS To Do → Google Tasks Migrator

Self-hostowany serwis webowy dla jednego użytkownika, który **jednorazowo** przenosi
zadania z Microsoft To Do (konto osobiste) do Google Tasks. Migracja odbywa się pod
nadzorem: ja zatwierdzam, co leci, run przenosi wszystko raz i porządnie, na końcu jest
raport weryfikacyjny. **Nie ma stałej synchronizacji ani monitorowania po migracji.**

Szczegóły projektowe (schemat, mapowanie pól, straty, idempotencja): `docs/design.md`.

## Stack
- Python 3.13, zarządzanie projektem przez **uv**
- **Django 5.2 LTS**, szablony Django + **HTMX**, Tailwind (standalone CLI, bez Node w runtime)
- **PostgreSQL 17** (lokalnie i w testach przez `docker compose`)
- Zadania w tle: **osobny proces workera** (`manage.py run_worker`), który pobiera runy z Postgresa
  (`SELECT … FOR UPDATE SKIP LOCKED`) i trzyma lease z heartbeatem. Bez Redisa i Celery,
  bo przy jednorazowej migracji dla jednej osoby stan runu i tak musi być w DB, żeby dało się go
  wznowić, a broker byłby tylko drugim źródłem prawdy.
- httpx (klient HTTP z retry), cryptography (Fernet do tokenów), django-environ
- Jakość: **pre-commit** (ruff lint + format, mypy z django-stubs, sprawdzenia plików),
  **pytest + pytest-django + respx**, pokrycie mierzone w testach
- Uruchomienie: `docker compose up` stawia `db`, `web` (gunicorn) i `worker`

## Integracje
- **Microsoft Graph, wyłącznie odczyt.** Scope `Tasks.Read offline_access User.Read`.
  Konto **osobiste (MSA)**: aplikacja w Entra ID z „Personal Microsoft accounts only”,
  authority `https://login.microsoftonline.com/consumers`. OAuth2 auth code + PKCE.
  Endpointy: `/me/todo/lists`, `/me/todo/lists/{id}/tasks`, `.../checklistItems`,
  `.../attachments` (tylko metadane), `.../linkedResources`.
  Klient Graph technicznie dopuszcza tylko `GET`; każda inna metoda rzuca wyjątek (test to weryfikuje).
- **Google Tasks API**: `tasklists`, `tasks`. OAuth2 auth code + PKCE, scope `https://www.googleapis.com/auth/tasks`.
- Zweryfikowane w dokumentacji (2026-09-18), szczegóły w `docs/design.md` i README:
  Google Tasks `due` **zapisuje tylko datę**, bo godzina jest odrzucana przez API.

## Model danych (kluczowe)
- `Connection`: tokeny OAuth szyfrowane at rest (klucz `TOKEN_ENCRYPTION_KEY` z ENV, nie w DB)
- `MsList`, `MsTask`, `MsChecklistItem`: snapshot danych z MS (staging), z którego czyta podgląd
- `ListMapping`: lista MS → lista Google, tryb `create_new | merge_into | skip`
- `TaskMapping`: `ms_task_id` (unikalne), `ms_list_id`, `google_task_id`, `google_list_id`,
  `content_hash`, `recovery_marker`, `status`, `last_synced_at`. To jest tabela idempotencji:
  **żadne zadanie nie może zostać przeniesione dwa razy**, nawet po crashu w połowie runu.
- `SubtaskMapping`: idempotencja podzadań (checklist → subtask)
- `TransferRun` + `RunItem`: historia, każdy run da się odtworzyć i wznowić
- `MigrationException`: kolejka rzeczy do decyzji człowieka
- `AuditLog`: każde wywołanie zapisujące do Google, z requestem i odpowiedzią (bez tokenów)

## Mapowanie pól i to, co się nie mapuje
Przenoszą się wprost: `title`, `body` → `notes`, `dueDateTime` → `due` (sama data), `status`,
`checklistItems` → podzadania. Pełna tabela i lista strat: `docs/design.md`.

Rzeczy bez odpowiednika obsługuję jawnie i konfigurowalnie w UI (ekran Ustawienia):
- **`recurrence`**: przenieś najbliższe wystąpienie i dodaj wyjątek z opisem wzorca,
  żebym odtworzył powtarzanie ręcznie w Google.
- **`importance`**: prefiks w tytule, osobna lista albo ignoruj.
- **`categories`**: `#tag` w notatkach albo ignoruj.
- **załączniki**: nazwy plików w notatce i ostrzeżenie w podglądzie.
- **przypomnienia, data startu, linked resources**: linia w notatce albo ignoruj.
- **zadania ukończone**: domyślnie pomijane; przełącznik „przenieś też ukończone z ostatnich N dni”.

## Odzyskiwanie po crashu (opcja A)
Każde zadanie w Google dostaje w notatkach stopkę `⟦mstodo:<hash>⟧`. Po crashu między zapisem
w Google a commitem w DB worker **uzgadnia** stan: szuka markera na liście docelowej,
zamiast wysyłać zadanie ponownie. Na koniec migracji stopki można usunąć (krok „Zakończenie”).

## Ekrany
1. **Połączenia**: status obu kont, ważność tokenów, reconnect, pobrane listy
2. **Ustawienia**: opcje mapowania stratnych pól (wyżej)
3. **Mapowanie list**: po lewej listy MS z licznikami, po prawej cel w Google
4. **Podgląd (dry-run)**: tabela wszystkich zadań do przeniesienia, filtry, checkboxy
   do wykluczania pojedynczych zadań, kolumna „ostrzeżenia”, gotowy payload.
   Dry-run **nie wykonuje żadnego zapisu do Google**. To twardy wymóg, sprawdzany testem.
5. **Run**: postęp, log na żywo, pauza, wznowienie
6. **Wyjątki**: cykliczne, błędy, niejednoznaczne, przycięte; każdy z akcją:
   pomiń / przenieś mimo to / oznacz jako naprawione ręcznie
7. **Zakończenie**: raport weryfikacyjny (liczby MS vs Google per lista, braki, nadmiary),
   opcjonalne usunięcie markerów z notatek
8. **Historia**: poprzednie runy, co dokładnie poszło, audyt zapisów

## Twarde wymagania niefunkcjonalne
- **Nic nie zmieniamy w Microsoft To Do.** Scope tylko do odczytu, klient Graph tylko `GET`.
- Nie usuwamy niczego w Google poza własnymi, jawnie wskazanymi akcjami (brak auto-delete).
- Throttling: Graph zwraca 429 z `Retry-After`, Google zwraca 429/403 `rateLimitExceeded`.
  Exponential backoff z jitterem, respektowany nagłówek `Retry-After`.
- Każdy run jest wznawialny po restarcie procesu (worker podejmuje run z wygasłym lease).
- Tokeny odświeżane automatycznie przed wygaśnięciem. Gdy refresh token wygaśnie lub zostanie
  odwołany, run się pauzuje, a UI pokazuje jasny komunikat „połącz ponownie”.
- Testy na: idempotencję (w tym crash po `insert` przed commitem), obsługę 429, wznawianie
  przerwanego runu, mapowanie pól, brak zapisów w dry-run, brak zapisów do MS.

## Kolejność pracy
1. Szkielet (uv, Django, Postgres, pre-commit, pytest) + OAuth do obu stron, ekran Połączeń.
   Pokaż, że pobierasz listy z MS i Google.
2. Pobieranie i staging zadań do lokalnej DB, Ustawienia, Mapowanie list, ekran Podglądu. Zero zapisu do Google.
3. Transfer z mapowaniem idempotencji, worker, ekran Runu. Odpalany ręcznie.
4. Kolejka wyjątków.
5. Zakończenie: raport weryfikacyjny i sprzątanie markerów.
6. Historia, audyt, dopełnienie testów, README.

Po każdym etapie zatrzymaj się i pokaż, co działa, zanim ruszysz dalej.
Nie uruchamiaj prawdziwej migracji, dopóki etap 3 nie przejdzie testów idempotencji.
