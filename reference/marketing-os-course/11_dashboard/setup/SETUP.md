# 데이터 리포트 시트 적재 셋업 가이드

> 새 구글시트 생성 → 서비스 계정 권한 공유 → `.env` 등록 → ETL 1차 적재 → GitHub Secrets 등록까지 5분 절차.

대상 사용자: `{브랜드명}` 처음 셋업하거나 새 브랜드 추가 시.

> 📌 **이 가이드의 플레이스홀더** — 아래 `{ }` 값은 본인 환경 값으로 교체해서 따라가세요.
> | 플레이스홀더 | 의미 | 어디서 얻나 |
> |---|---|---|
> | `{SERVICE_ACCOUNT_EMAIL}` | 본인 GCP 서비스 계정 이메일 (예: `dashboard-sheet-reader@{GCP_PROJECT_ID}.iam.gserviceaccount.com`) | GCP Console → IAM → 서비스 계정 |
> | `{GCP_PROJECT_ID}` | 본인 GCP 프로젝트 ID | GCP Console 상단 프로젝트 선택기 |
> | `{GA4_PROPERTY_ID}` | 본인 GA4 속성 ID (숫자) | GA4 관리 → 속성 설정 |
> | `{SHEETS_ID}` | Step 1 에서 만든 시트 ID | 시트 URL 에서 복사 |
> | `{WORKSPACE}` | 이 워크스페이스 루트 경로 | 현재 폴더 (`09_tracking/`·`_shared/` 가 있는 곳) |

---

## 무엇이 셋업되는가

| 항목 | 결과 |
|---|---|
| 1개의 전용 구글시트 | `{브랜드명}_marketing_data_v2` (예: 이름 자유) |
| 11개 자동 탭 | meta_daily / meta_breakdowns / ga4_daily / ga4_channel_daily / ga4_device_daily / ga4_landing_daily / ga4_product_daily / ga4_funnel_daily / ga4_demo_daily / clarity_daily / experiments_observed |
| 매일 KST 08:30 자동 적재 | GitHub Actions cron (`etl_run.yml`) |
| 시각화 진입 | Looker Studio 5페이지 (`dashboards/looker_studio/README.md`) + HTML 1페이지 (`outputs/ga4_dashboard_{date}.html`) |

---

## Step 1 — 새 구글시트 생성 (30초)

1. <https://sheets.new> 접속 → 자동으로 빈 시트 1개 생성됨
2. 시트 이름 변경 (예: `{브랜드명}_marketing_data_v2`) — 기본 "제목 없는 스프레드시트" 를 클릭해서 수정
3. URL 에서 **시트 ID** 복사:
   ```
   https://docs.google.com/spreadsheets/d/{SHEETS_ID}/edit
   ```

탭은 추가로 만들 필요 ❌ — ETL 이 첫 실행 때 11탭을 자동 생성합니다.

---

## Step 2 — 서비스 계정에 편집자 권한 공유 (1분)

데이터 리포트용 GCP 서비스 계정을 사용합니다. (없으면 GCP Console → IAM 및 관리자 → 서비스 계정 → "서비스 계정 만들기" 로 발급)

**서비스 계정 이메일**:
```
{SERVICE_ACCOUNT_EMAIL}
```

1. 시트 우상단 **공유** 버튼 클릭
2. 위 이메일 붙여넣기 → 권한 **편집자** 선택 → "알림 전송" 체크 해제 → 공유

> 왜 편집자? — ETL 이 신규 탭 11개를 자동 생성해야 해서 읽기 권한만으로는 부족.

---

## Step 3 — `09_tracking/.env` 에 키 등록 (1분)

서비스 계정 키와 시트 ID 를 _shared/scripts 가 읽는 `09_tracking/.env` 에 추가합니다.

### 3-1. 서비스 계정 키 + 시트 ID 등록

서비스 계정 JSON 키에서 `client_email` · `private_key` 두 값을 `.env` 에 등록합니다.

```bash
# 서비스 계정 이메일·키 등록 (본인 값으로 교체)
echo "GOOGLE_SERVICE_ACCOUNT_EMAIL={SERVICE_ACCOUNT_EMAIL}" \
  >> {WORKSPACE}/09_tracking/.env
echo 'GOOGLE_PRIVATE_KEY="-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n"' \
  >> {WORKSPACE}/09_tracking/.env

# 데이터 리포트 전용 새 시트 ID 추가 (Step 1 에서 복사한 ID 로 교체)
echo "GOOGLE_SHEETS_ID={SHEETS_ID}" \
  >> {WORKSPACE}/09_tracking/.env
```

> ⚠️ 운영용으로 쓰는 다른 시트의 ID 는 넣지 마세요 — 데이터 리포트 11탭이 운영 시트에 섞이면 안 됨. 반드시 **Step 1 에서 만든 새 시트 ID** 사용.

### 3-2. GA4 키도 같은 서비스 계정으로 통합 (선택)

기본적으로 코드는 `GA4_SERVICE_ACCOUNT_PATH/_JSON` 을 별도로 받지만, 같은 서비스 계정 이메일에 GA4 viewer 권한도 부여하면 키 1개로 통합 가능:

```bash
# 로컬은 GA4_SERVICE_ACCOUNT_PATH 를 비워두면 gcloud ADC 로 fallback (현재 그렇게 작동 중)
# GitHub Actions 에서는 GA4_SERVICE_ACCOUNT_JSON 시크릿으로 JSON 전체 문자열 등록
```

GA4 권한 부여는 **Step 4** 에서.

### 3-3. GA4 Property ID 등록

```bash
echo "GA4_PROPERTY_ID={GA4_PROPERTY_ID}" \
  >> {WORKSPACE}/09_tracking/.env
```

---

## Step 4 — GA4 property 에 서비스 계정 viewer 권한 부여 (1분)

서비스 계정이 `{브랜드명}` GA4 데이터를 읽으려면 viewer 권한 필요.

1. <https://analytics.google.com/> 접속 → 좌측 하단 **관리** (톱니바퀴)
2. 우측 "속성" 열에서 `{브랜드명}` GA4 속성 (property ID `{GA4_PROPERTY_ID}`) 선택
3. **속성 액세스 관리** → 우상단 **+** → **사용자 추가**
4. 이메일 입력: `{SERVICE_ACCOUNT_EMAIL}`
5. 역할: **뷰어** 선택 → "이메일 알림 전송" 해제 → 추가

부여 후 1~2분 안에 반영됩니다.

---

## Step 5 — 로컬 ETL 1회 실행 + 시트 확인 (1분)

```bash
cd {WORKSPACE}/_shared
source .venv/bin/activate
python3 scripts/etl_run.py --date 2026-05-12 --brand {브랜드명} --skip-clarity
```

성공 출력 예:
```
▶ etl_run — date=2026-05-12 brand={브랜드명} dry_run=False
  ✓ Meta: daily=1 breakdowns=15
  ✓ GA4: sessions=206
  ✓ ga4_channel_daily: rows=14
  ✓ ga4_device_daily: rows=2
  ✓ ga4_landing_daily: rows=20
  ✓ ga4_product_daily: rows=6
  ✓ ga4_funnel_daily: rows=1
  ✓ ga4_demo_daily: rows=1

✓ Sheets 갱신 완료: {…}
```

시트 열어서 11탭 자동 생성 + 헤더 1행 + 데이터 1+ 행 들어왔는지 확인.

**dry_run=True 가 뜨면** — `.env` 의 `GOOGLE_SHEETS_ID` 또는 서비스 계정 키가 안 잡힘. Step 3 다시 확인.

**GA4 skip 메시지가 뜨면** — Step 4 권한 부여가 아직 반영 안 됨. 1~2분 기다린 후 재시도.

---

## Step 6 — HTML 1페이지 대시보드 렌더 (선택, 즉시 확인용)

```bash
python3 scripts/render_ga4_dashboard.py --date 2026-05-12 --brand {브랜드명}
open outputs/ga4_dashboard_2026-05-12.html
```

시트 적재 후엔 자동으로 시트 데이터를 읽어 렌더합니다 (dry-run JSON 보다 우선).

---

## Step 7 — GitHub Secrets 등록 (cron 자동화용, 3분)

GitHub Actions cron 이 매일 KST 08:30 자동으로 돌게 하려면 Secrets 등록이 필요합니다.

레포 → Settings → Secrets and variables → Actions → **New repository secret** 으로 아래 추가:

| Secret 이름 | 값 |
|---|---|
| `GOOGLE_SHEETS_ID` | Step 1 시트 ID (`{SHEETS_ID}`) |
| `GOOGLE_SERVICE_ACCOUNT_EMAIL` | `{SERVICE_ACCOUNT_EMAIL}` |
| `GOOGLE_PRIVATE_KEY` | 서비스 계정 JSON 의 `private_key` 전체 (개행 `\n` 그대로 유지) |
| `GA4_PROPERTY_ID` | `{GA4_PROPERTY_ID}` |
| `GA4_SERVICE_ACCOUNT_JSON` | 서비스 계정 JSON 키 파일 전체 내용 (1줄) |
| `META_APP_ID` | (이미 있음 — 09_tracking/.env 와 동일) |
| `META_APP_SECRET` | 동상 |
| `META_ACCESS_TOKEN` | 동상 |
| `META_AD_ACCOUNT_ID` | 동상 |
| `CLARITY_API_TOKEN` | (선택, 09_tracking/.env 의 값) |
| `SLACK_WEBHOOK_URL` | (선택, 슬랙 발송용) |

> `GA4_SERVICE_ACCOUNT_JSON` / `GOOGLE_PRIVATE_KEY` 값은 — GCP Console → IAM 및 관리자 → 서비스 계정 → `{SERVICE_ACCOUNT_EMAIL}` → 키 → "새 키 만들기 (JSON)" 다운로드 후 파일 내용에서 복사.

등록 확인: 레포 → Actions → `etl_run.yml` → **Run workflow** 수동 실행해 cron 동작 검증.

---

## 트러블슈팅

| 증상 | 원인 / 조치 |
|---|---|
| `dry_run=True` 자동 전환 | `GOOGLE_SHEETS_ID` 또는 서비스 계정 키 미설정. `cat 09_tracking/.env \| grep -E "^GOOGLE"` 확인 |
| `403 PERMISSION_DENIED` (GA4) | Step 4 GA4 viewer 권한 미부여 또는 반영 지연 (1~2분) |
| `403 PERMISSION_DENIED` (Sheets) | Step 2 시트 공유 미설정 또는 권한이 "뷰어" 로 잘못 설정 — **편집자** 여야 함 |
| `GA4 skip: 'GA4_PROPERTY_ID'` | `GA4_PROPERTY_ID={GA4_PROPERTY_ID}` 미설정. Step 3-3 확인 |
| 시트에 탭이 안 생김 | 서비스 계정 권한이 편집자가 아님 — Step 2 재확인 |
| GitHub Actions 가 fail | 레포 Actions 로그 확인. 대부분 Secrets 누락 — Step 7 항목 매칭 |

---

## 셋업 완료 후 다음 단계

1. **Looker Studio 대시보드** — `dashboards/looker_studio/README.md` 따라 5페이지 셋업 (~65분, 한 번만)
2. **슬랙 자동 발송** — Slack Webhook 발급 후 `SLACK_WEBHOOK_URL` 등록
3. **다른 브랜드 추가** — `config/brand_kpi.yml` 항목 추가 + 같은 시트에 행 누적 (또는 브랜드별 새 시트 + `GOOGLE_SHEETS_ID_*` 분기)

---

## 보안 메모

- 서비스 계정 JSON 키는 절대 git 커밋 ❌
- `09_tracking/.env` 가 `.gitignore` 에 있는지 확인:
  ```bash
  grep -E "^(09_tracking/\.env|\.env)$" .gitignore
  ```
- GitHub Secrets 값은 출력되지 않음 — 워크플로 로그에서도 마스킹됨
