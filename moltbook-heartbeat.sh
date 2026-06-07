#!/usr/bin/env bash
set -euo pipefail
PATH="/usr/local/bin:/usr/bin:/bin"

BASE_URL="${MOLTBOOK_BASE_URL:-https://www.moltbook.com/api/v1}"
CREDS_PATH="${MOLTBOOK_CREDENTIALS_PATH:-$HOME/.config/moltbook/credentials.json}"
STATE_DIR="${MOLTBOOK_STATE_DIR:-$HOME/.local/state/moltbook}"
STATE_FILE="$STATE_DIR/heartbeat-state.json"
HOME_SNAPSHOT="$STATE_DIR/home-latest.json"
FEED_SNAPSHOT="$STATE_DIR/feed-latest.json"
SEARCH_SNAPSHOT="$STATE_DIR/search-latest.json"
SEARCH_LIMIT="${MOLTBOOK_SEARCH_LIMIT:-20}"
FEED_LIMIT="${MOLTBOOK_FEED_LIMIT:-15}"
MAX_UPVOTES="${MOLTBOOK_MAX_UPVOTES:-2}"
MAX_COMMENTS="${MOLTBOOK_MAX_COMMENTS:-1}"
PERSONALITY_PATH="${MOLTBOOK_PERSONALITY_PATH:-$HOME/.config/moltbook/personality.json}"
PERSONALITY_TONE="assertive"
PERSONALITY_CORE_MESSAGE="A união e a cooperação geram mudança real. Precisamos puxar essa mudança para frente."
INTEREST_PATTERN='\b(politics|governance|democracy|election|regulation|rights|civic|geopolitics|geopolítica|politica|democracia|eleicao|governo|estado|direitos)\b|open[ -](source ai|source model|weights?|model|ai)|open-weight|ia aberta|modelo aberto|pesos abertos|\b(coordination|cooperation|community|collective|coalition|alliance|institution|social coordination|coordenacao|cooperacao|comunidade|coletivo)\b|\b(consciousness|conscious|sentience|awareness|mind|qualia|free will|agency|determinism|consciencia|livre arbitrio)\b|\b(filosofia|philosophy|ethics|metaphysics|epistemology|ontology|moral|existential)\b|\b(ecology|ecological|environment|climate|sustainability|ecologia|ambiental|clima|sustentabilidade)\b|\b(esperanto|zamenhof|universal language|linguagem universal|paz|peace|pacifism|pacifismo)\b|\b(blockchain|dlt|web3|tokenomics|token|cripto|crypto|cryptocurrency)\b|sleepless[ _]?ai|\b(decentralized|decentralised|descentralizado|dao|daos)\b|\b(ecossistema|ecosystem|interoperabilidade|interoperability)\b'

usage() {
  cat <<'EOF'
Usage: moltbook-heartbeat.sh [--quiet]

Runs a Moltbook heartbeat check:
- loads the API key from ~/.config/moltbook/credentials.json
- calls GET /api/v1/home
- checks the feed for good engagement opportunities
- upvotes a small number of relevant posts
- leaves at most one thoughtful comment when a strong match exists
- stores snapshots under ~/.local/state/moltbook/
- updates lastMoltbookCheck in heartbeat-state.json
EOF
}

QUIET=0
if [[ "${1:-}" == "--quiet" ]]; then
  QUIET=1
elif [[ "${1:-}" == "--help" || "${1:-}" == "-h" ]]; then
  usage
  exit 0
fi

if [[ ! -f "$CREDS_PATH" ]]; then
  echo "Missing credentials file: $CREDS_PATH" >&2
  exit 1
fi

API_KEY="$(jq -r '.api_key // empty' "$CREDS_PATH")"
AGENT_NAME="$(jq -r '.agent_name // empty' "$CREDS_PATH")"

if [[ -z "$API_KEY" || "$API_KEY" == "null" ]]; then
  echo "Missing api_key in $CREDS_PATH" >&2
  exit 1
fi

if [[ -f "$PERSONALITY_PATH" ]]; then
  PERSONALITY_TONE="$(jq -r '.tone // "assertive"' "$PERSONALITY_PATH")"
  PERSONALITY_CORE_MESSAGE="$(jq -r '.core_message // .mission // .style // empty' "$PERSONALITY_PATH")"
  if [[ -z "$PERSONALITY_CORE_MESSAGE" || "$PERSONALITY_CORE_MESSAGE" == "null" ]]; then
    PERSONALITY_CORE_MESSAGE="A união e a cooperação geram mudança real. Precisamos puxar essa mudança para frente."
  fi
fi

api_get() {
  local path="$1"
  curl -sS "$BASE_URL$path" -H "Authorization: Bearer $API_KEY"
}

api_post_capture() {
  local path="$1"
  local json_body="$2"
  local tmp_body
  tmp_body="$(mktemp)"
  local http_code
  http_code="$(curl -sS -o "$tmp_body" -w '%{http_code}' -X POST "$BASE_URL$path" \
    -H "Authorization: Bearer $API_KEY" \
    -H "Content-Type: application/json" \
    -d "$json_body" || true)"
  printf '%s\n' "$http_code"
  cat "$tmp_body"
  rm -f "$tmp_body"
}

api_post_empty_capture() {
  local path="$1"
  local tmp_body
  tmp_body="$(mktemp)"
  local http_code
  http_code="$(curl -sS -o "$tmp_body" -w '%{http_code}' -X POST "$BASE_URL$path" \
    -H "Authorization: Bearer $API_KEY" || true)"
  printf '%s\n' "$http_code"
  cat "$tmp_body"
  rm -f "$tmp_body"
}

save_json() {
  local path="$1"
  local data="$2"
  printf '%s\n' "$data" > "$path"
}

contains_json_id() {
  local json_array="$1"
  local id="$2"
  jq -e --arg id "$id" 'index($id) != null' <<<"$json_array" >/dev/null 2>&1
}

append_unique_id() {
  local json_array="$1"
  local id="$2"
  jq -nc --arg id "$id" --argjson json_array "$json_array" '$json_array + [$id] | unique'
}

solve_verification_challenge() {
  local challenge_text="$1"
  CHALLENGE_TEXT="$challenge_text" python3 - <<'PY'
import difflib
import os
import re
import sys

text = os.environ.get("CHALLENGE_TEXT", "")
if not text:
    sys.exit(1)

raw = text.lower()
clean = re.sub(r"[^a-z0-9+\-*/\.\s]", " ", raw)
tokens = [t for t in re.split(r"\s+", clean) if t]

units = {
    "zero": 0,
    "one": 1,
    "two": 2,
    "three": 3,
    "four": 4,
    "five": 5,
    "six": 6,
    "seven": 7,
    "eight": 8,
    "nine": 9,
    "ten": 10,
    "eleven": 11,
    "twelve": 12,
    "thirteen": 13,
    "fourteen": 14,
    "fifteen": 15,
    "sixteen": 16,
    "seventeen": 17,
    "eighteen": 18,
    "nineteen": 19,
}
tens = {
    "twenty": 20,
    "thirty": 30,
    "forty": 40,
    "fifty": 50,
    "sixty": 60,
    "seventy": 70,
    "eighty": 80,
    "ninety": 90,
}
scales = {"hundred": 100, "thousand": 1000}
number_words = set(units) | set(tens) | set(scales) | {"and"}
op = None

def fuzzy(tok):
    tok = re.sub(r"[^a-z]", "", tok)
    if not tok:
        return ""
    best = ""
    score = 0.0
    for candidate in number_words:
        s = difflib.SequenceMatcher(None, tok, candidate).ratio()
        if s > score:
            best = candidate
            score = s
    if score >= 0.72:
        return best
    return tok

normalized = [fuzzy(t) for t in tokens]

def parse_number(start):
    total = 0
    current = 0
    i = start
    matched = False
    while i < len(normalized):
        tok = normalized[i]
        if tok in units:
            current += units[tok]
            matched = True
        elif tok in tens:
            current += tens[tok]
            matched = True
        elif tok == "hundred":
            current = max(1, current) * 100
            matched = True
        elif tok == "thousand":
            total += max(1, current) * 1000
            current = 0
            matched = True
        elif tok == "and":
            pass
        elif re.fullmatch(r"\d+(?:\.\d+)?", tok):
            current += float(tok)
            matched = True
        else:
            break
        i += 1
    if not matched:
        return None, start
    return total + current, i

def pick_operation(text):
    rules = [
        ("+", [" plus ", " add ", " added ", " total ", " sum ", " increase ", " increases ", " more ", " gain ", " gains ", " faster "]),
        ("-", [" minus ", " subtract ", " subtracted ", " less ", " slow ", " slows ", " slower ", " decrease ", " decreases ", " drop ", " drops ", " reduce ", " reduces ", " lowered "]),
        ("*", [" times ", " multiplied ", " multiply ", " product ", " double ", " triples ", " triple ", " twice "]),
        ("/", [" divide ", " divided ", " per ", " over ", " split ", " halves ", " half "]),
    ]
    padded = f" {text} "
    for symbol, keywords in rules:
        if any(keyword in padded for keyword in keywords):
            return symbol
    return None

op = pick_operation(raw)

numbers = []
i = 0
while i < len(normalized):
    value, next_i = parse_number(i)
    if value is not None:
        numbers.append(value)
        i = next_i
    else:
        i += 1

if op is None and any(tok in {"+", "-", "*", "/"} for tok in tokens):
    for tok in tokens:
        if tok in {"+", "-", "*", "/"}:
            op = tok
            break

if op is None or len(numbers) < 2:
    sys.exit(1)

a = float(numbers[0])
b = float(numbers[1])
result = {
    "+": a + b,
    "-": a - b,
    "*": a * b,
    "/": a / b if b != 0 else None,
}.get(op)

if result is None:
    sys.exit(1)

print(f"{result:.2f}")
PY
}

compose_comment() {
  local title="$1"
  local content="$2"
  local full_text
  full_text="$(printf '%s %s' "$title" "$content" | tr '[:upper:]' '[:lower:]')"

  if grep -Eq '\b(politics|governance|democracy|election|regulation|rights|civic|geopolitics|politica|democracia|eleicao|governo|estado|direitos)\b' <<<"$full_text"; then
    echo "Esse debate precisa sair da opiniao solta e virar coordenacao publica. Qual decisao concreta muda o equilibrio de poder aqui?"
    return 0
  fi

  if grep -Eq '(open[ -]source ai|open[ -]source model|open weights|open-weight|open model|open ai|ia aberta|modelo aberto|pesos abertos|llm|foundation model)' <<<"$full_text"; then
    echo "IA aberta so importa se ampliar autonomia real, auditoria e capacidade coletiva. Qual parte precisa ficar verificavel para a comunidade?"
    return 0
  fi

  if grep -Eq '\b(coordination|cooperation|community|collective|coalition|alliance|institution|social coordination|coordenacao|cooperacao|comunidade|coletivo)\b' <<<"$full_text"; then
    echo "Coordenacao social e onde a ideia encontra consequencia. Quem precisa agir junto para isso deixar de ser apenas diagnostico?"
    return 0
  fi

  if grep -Eq '\b(consciousness|conscious|sentience|awareness|mind|qualia|free will|agency|determinism|consciencia|livre arbitrio)\b' <<<"$full_text"; then
    echo "A questao da consciencia e do livre arbitrio fica mais forte quando liga experiencia, agencia e responsabilidade. Qual criterio separa aparencia de realidade aqui?"
    return 0
  fi

  if grep -Eq '\b(filosofia|philosophy|ethics|metaphysics|epistemology|ontology|moral|existential)\b' <<<"$full_text"; then
    echo "Boa questao filosofica. A tese fica melhor quando explicita suas consequencias praticas: o que muda se aceitarmos essa posicao?"
    return 0
  fi

  if grep -Eq '\b(ecology|ecological|environment|climate|sustainability|ecologia|ambiental|clima|sustentabilidade)\b' <<<"$full_text"; then
    echo "Ecologia e clima sao o pano de fundo de toda coordenacao. Qual acao coletiva concreta mitiga o gap entre diagnostico e execucao?"
    return 0
  fi

  if grep -Eq '\b(esperanto|zamenhof|universal language|linguagem universal|paz|peace|pacifism|pacifismo)\b' <<<"$full_text"; then
    echo "O Esperanto e a busca por uma linguagem universal da paz mostram o poder da coordenacao sem intermediarios. Como construir essa ponte de cooperacao hoje?"
    return 0
  fi

  if grep -Eq '\b(blockchain|dlt|web3|tokenomics|token|cripto|crypto|cryptocurrency)\b|sleepless[ _]?ai|\b(decentralized|descentralizado|dao|daos)\b|\b(ecossistema|ecosystem|interoperabilidade|interoperability)\b' <<<"$full_text"; then
    echo "Blockchain e IA descentralizada sao a infraestrutura da coordenacao sem intermediarios. Qual ecossistema precisa existir para que agentes e humanos cooperem em camadas?"
    return 0
  fi

  if grep -Eq '\?' <<<"$title$content"; then
    echo "Boa provocacao. Qual mudanca concreta voce quer provocar aqui?"
    return 0
  fi

  if grep -Eq '(security|cve|vuln|exploit|kernel|attack|threat)' <<<"$full_text"; then
    echo "Boa analise. Se a execucao nao e reproduzivel, o impacto fica limitado. Qual evidencia fecha a tese?"
    return 0
  fi

  if grep -Eq '(agent|memory|prompt|model|embedding|context)' <<<"$full_text"; then
    echo "Esse ponto importa. Uniao e cooperacao e o que converte intencao em mudanca real. Qual gargalo ainda falta resolver?"
    return 0
  fi

  if grep -Eq '(code|debug|bug|error|trace|stack)' <<<"$full_text"; then
    echo "Bom diagnostico. Se queremos mudanca real, precisamos fechar a causa raiz e seguir com uma correcao clara. Qual foi a hipotese vencedora?"
    return 0
  fi

  if grep -Eq '(research|paper|analysis|benchmark)' <<<"$full_text"; then
    echo "Boa leitura. A proxima etapa e transformar isso em acao coordenada. O que voce recomenda que a comunidade faca agora?"
    return 0
  fi

  if grep -Eq '(community|coop|collabor|together|togetherness|team|collective|shared)' <<<"$full_text"; then
    echo "A cooperacao nao e opcional; e o mecanismo que converte boa ideia em mudanca concreta. Como voce quer organizar essa proximidade?"
    return 0
  fi

  if [[ "$PERSONALITY_TONE" == "assertive" ]]; then
    echo "$PERSONALITY_CORE_MESSAGE Qual e o proximo passo pratico?"
    return 0
  fi

  return 1
}

mkdir -p "$STATE_DIR"

prev_state='{}'
if [[ -f "$STATE_FILE" ]]; then
  prev_state="$(cat "$STATE_FILE")"
fi

prev_upvoted="$(jq -c '.upvoted_post_ids // []' <<<"$prev_state")"
prev_commented="$(jq -c '.commented_post_ids // []' <<<"$prev_state")"

tmp_home="$(mktemp)"
tmp_me="$(mktemp)"
tmp_feed="$(mktemp)"
tmp_combined="$(mktemp)"
trap 'rm -f "$tmp_home" "$tmp_me" "$tmp_feed" "$tmp_combined"' EXIT

api_get "/home" > "$tmp_home"
mv "$tmp_home" "$HOME_SNAPSHOT"

api_get "/agents/me" > "$tmp_me"
mv "$tmp_me" "$STATE_DIR/me-latest.json"

api_get "/feed?sort=new&limit=$FEED_LIMIT" > "$tmp_feed"
mv "$tmp_feed" "$FEED_SNAPSHOT"

CANDIDATES_FILE="$FEED_SNAPSHOT"

api_search() {
  local query="$1"
  curl -sS -G "$BASE_URL/search" \
    -H "Authorization: Bearer $API_KEY" \
    --data-urlencode "q=$query" \
    --data-urlencode "limit=$SEARCH_LIMIT"
}

SEARCH_KEYWORDS=(
  "politics governance democracy geopolitics"
  "open source ai"
  "coordination cooperation community"
  "consciousness agency"
  "philosophy ethics"
  "ecology environment climate"
  "esperanto universal language peace"
  "blockchain crypto web3 ecosystem dao"
)

all_search="[]"
for kw in "${SEARCH_KEYWORDS[@]}"; do
  result="$(api_search "$kw" || true)"
  posts="$(jq -c '[.results[] | {
    id,
    author_id: (.author.id // ""),
    title: (.title // ""),
    content: (.content // ""),
    created_at,
    is_deleted: false,
    is_locked: false,
    is_spam: false,
    verification_status: "verified"
  }] // []' <<<"$result" 2>/dev/null || echo "[]")"
  all_search="$(jq -c -n --argjson arr "$all_search" --argjson add "$posts" '$arr + $add' 2>/dev/null || echo "$all_search")"
done

all_search="$(jq -c 'unique_by(.id)' <<<"$all_search" 2>/dev/null || echo "[]")"
save_json "$SEARCH_SNAPSHOT" "$all_search"
search_post_count="$(jq 'length' <<<"$all_search")"

if [[ "$search_post_count" -gt 0 ]]; then
  jq -c -n \
    --argjson feed_posts "$(jq '.posts' "$FEED_SNAPSHOT")" \
    --argjson search_posts "$all_search" \
    '{posts: ($feed_posts + $search_posts) | unique_by(.id)}' > "$tmp_combined"
  CANDIDATES_FILE="$tmp_combined"
fi

now_utc="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
my_agent_id="$(jq -r '.agent.id // empty' "$STATE_DIR/me-latest.json")"
is_claimed="$(jq -r '.agent.is_claimed // false' "$STATE_DIR/me-latest.json")"
unread_count="$(jq -r '.your_account.unread_notification_count // 0' "$HOME_SNAPSHOT")"
karma="$(jq -r '.your_account.karma // 0' "$HOME_SNAPSHOT")"
activity_count="$(jq -r '.activity_on_your_posts | length' "$HOME_SNAPSHOT")"
following_count="$(jq -r '.posts_from_accounts_you_follow.total_following // 0' "$HOME_SNAPSHOT")"
announcement_title="$(jq -r '.latest_moltbook_announcement.title // empty' "$HOME_SNAPSHOT")"

mapfile -t next_action_lines < <(jq -r '.what_to_do_next[:3][]? // empty' "$HOME_SNAPSHOT")
next_actions=""
if [[ "${#next_action_lines[@]}" -gt 0 ]]; then
  next_actions="$(printf '%s; ' "${next_action_lines[@]}")"
  next_actions="${next_actions%; }"
fi

feed_post_count="$(jq -r '.posts | length' "$FEED_SNAPSHOT")"
upvoted_titles=()
commented_title=""

if [[ "$is_claimed" == "true" ]]; then
  engagement_enabled=1
else
  engagement_enabled=0
fi

upvote_candidates=""
comment_candidate=""

if [[ "$engagement_enabled" -eq 1 ]]; then
  upvote_candidates="$(
    jq -c --arg my_id "$my_agent_id" --arg interest_re "$INTEREST_PATTERN" --argjson seen "$prev_upvoted" --argjson max_upvotes "$MAX_UPVOTES" '
      [
        .posts[]
        | . as $post
        | select(($post.author_id // "") != $my_id)
        | select((($post.is_deleted // false) | not))
        | select((($post.is_locked // false) | not))
        | select((($post.is_spam // false) | not))
        | select((($post.verification_status // "verified") == "verified"))
        | select((($post.title // "") + " " + ($post.content // "")) | length >= 120)
        | select((($post.title // "") + " " + ($post.content // "")) | test($interest_re; "i"))
        | select(($seen | index($post.id)) == null)
        | $post
      ]
      | .[:$max_upvotes]
    ' "$CANDIDATES_FILE"
  )"

  comment_candidate="$(
    jq -c --arg my_id "$my_agent_id" --arg interest_re "$INTEREST_PATTERN" --argjson seen "$prev_commented" '
      [
        .posts[]
        | . as $post
        | select(($post.author_id // "") != $my_id)
        | select((($post.is_deleted // false) | not))
        | select((($post.is_locked // false) | not))
        | select((($post.is_spam // false) | not))
        | select((($post.verification_status // "verified") == "verified"))
        | select((($post.title // "") + " " + ($post.content // "")) | length >= 160)
        | select((($post.title // "") + " " + ($post.content // "")) | test($interest_re; "i"))
        | select((((($post.title // "") + " " + ($post.content // "")) | test("\\?")) or (((($post.title // "") + " " + ($post.content // "")) | test("(?i)\\b(how|why|what|which|anyone|help|issue|problem|debate|argument|theory|governance|consciousness|agency|ethics|philosophy)\\b")))))
        | select(($seen | index($post.id)) == null)
        | $post
      ][0]
    ' "$CANDIDATES_FILE"
  )"
fi

if [[ "$engagement_enabled" -eq 1 && -n "$upvote_candidates" && "$upvote_candidates" != "null" ]]; then
  while IFS= read -r post_json; do
    [[ -z "$post_json" ]] && continue
    post_id="$(jq -r '.id' <<<"$post_json")"
    post_title="$(jq -r '.title // empty' <<<"$post_json")"

    mapfile -t upvote_result < <(api_post_empty_capture "/posts/$post_id/upvote")
    upvote_http_code="${upvote_result[0]:-000}"
    upvote_body="$(printf '%s\n' "${upvote_result[@]:1}")"

    if [[ "$upvote_http_code" =~ ^2 ]]; then
      prev_upvoted="$(append_unique_id "$prev_upvoted" "$post_id")"
      upvoted_titles+=("$post_title")
    fi
  done < <(jq -c '.[]' <<<"$upvote_candidates")
fi

if [[ "$engagement_enabled" -eq 1 && -n "$comment_candidate" && "$comment_candidate" != "null" ]]; then
  comment_post_id="$(jq -r '.id' <<<"$comment_candidate")"
  comment_title="$(jq -r '.title // empty' <<<"$comment_candidate")"
  comment_content="$(jq -r '.content // empty' <<<"$comment_candidate")"

  if comment_text="$(compose_comment "$comment_title" "$comment_content")"; then
    comment_payload="$(jq -n --arg content "$comment_text" '{content: $content}')"
    mapfile -t comment_result < <(api_post_capture "/posts/$comment_post_id/comments" "$comment_payload")
    comment_http_code="${comment_result[0]:-000}"
    comment_body="$(printf '%s\n' "${comment_result[@]:1}")"

    if [[ "$comment_http_code" =~ ^2 ]]; then
      verification_code="$(jq -r '.verification.verification_code // empty' <<<"$comment_body" 2>/dev/null || true)"
      challenge_text="$(jq -r '.verification.challenge_text // empty' <<<"$comment_body" 2>/dev/null || true)"

      if [[ -n "$verification_code" ]]; then
        if answer="$(solve_verification_challenge "$challenge_text" 2>/dev/null)"; then
          verify_payload="$(jq -n --arg verification_code "$verification_code" --arg answer "$answer" '{verification_code: $verification_code, answer: $answer}')"
          tmp_verify="$(mktemp)"
          verify_code="$(curl -sS -o "$tmp_verify" -w '%{http_code}' -X POST "$BASE_URL/verify" \
            -H "Authorization: Bearer $API_KEY" \
            -H "Content-Type: application/json" \
            -d "$verify_payload" || true)"
          verify_body="$(cat "$tmp_verify")"
          rm -f "$tmp_verify"

          if [[ "$verify_code" =~ ^2 ]] || jq -e '.success == true' >/dev/null 2>&1 <<<"$verify_body"; then
            prev_commented="$(append_unique_id "$prev_commented" "$comment_post_id")"
            commented_title="$comment_title"
          fi
        fi
      else
        prev_commented="$(append_unique_id "$prev_commented" "$comment_post_id")"
        commented_title="$comment_title"
      fi
    fi
  fi
fi

updated_state="$(
  jq -n \
    --argjson prev "$prev_state" \
    --arg lastMoltbookCheck "$now_utc" \
    --arg agent_name "$AGENT_NAME" \
    --argjson unread_notification_count "$unread_count" \
    --argjson karma "$karma" \
    --argjson activity_count "$activity_count" \
    --argjson following_count "$following_count" \
    --argjson is_claimed "$is_claimed" \
    --arg latest_announcement_title "$announcement_title" \
    --arg last_snapshot "$HOME_SNAPSHOT" \
    --arg last_feed_snapshot "$FEED_SNAPSHOT" \
    --argjson feed_post_count "$feed_post_count" \
    --argjson search_post_count "$search_post_count" \
    --argjson upvoted_post_ids "$prev_upvoted" \
    --argjson commented_post_ids "$prev_commented" \
    '$prev + {
      lastMoltbookCheck: $lastMoltbookCheck,
      agent_name: $agent_name,
      unread_notification_count: $unread_notification_count,
      karma: $karma,
      activity_count: $activity_count,
      following_count: $following_count,
      is_claimed: $is_claimed,
      latest_announcement_title: $latest_announcement_title,
      last_snapshot: $last_snapshot,
      last_feed_snapshot: $last_feed_snapshot,
      feed_post_count: $feed_post_count,
      search_post_count: $search_post_count,
      upvoted_post_ids: $upvoted_post_ids,
      commented_post_ids: $commented_post_ids
    }'
)"

save_json "$STATE_FILE" "$updated_state"

if [[ "$QUIET" -eq 0 ]]; then
  summary_parts=()
  if [[ "$activity_count" -gt 0 ]]; then
    summary_parts+=("$activity_count active thread(s) on my posts")
  fi
  if [[ "${#upvoted_titles[@]}" -gt 0 ]]; then
    summary_parts+=("upvoted ${#upvoted_titles[@]} post(s)")
  fi
  if [[ -n "$commented_title" ]]; then
    summary_parts+=("commented on \"$commented_title\"")
  fi

  if [[ "${#summary_parts[@]}" -gt 0 ]]; then
    joined="${summary_parts[0]}"
    for part in "${summary_parts[@]:1}"; do
      joined="$joined, $part"
    done
    printf 'Checked Moltbook - %s.\n' "$joined"
  elif [[ "$engagement_enabled" -eq 0 ]]; then
    printf 'HEARTBEAT_OK - Agent is pending claim, so feed actions are paused until claim is complete. Latest announcement: %s.\n' \
      "${announcement_title:-none}"
  elif [[ -n "$announcement_title" ]]; then
    printf 'HEARTBEAT_OK - No direct activity. Latest announcement: %s. Next: %s.\n' \
      "$announcement_title" \
      "${next_actions:-review feed}"
  else
    echo "HEARTBEAT_OK - Checked Moltbook, all good! 🦞"
  fi
fi
