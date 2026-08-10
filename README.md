# 강원특별자치도 학교 현황 대시보드

순수 HTML/CSS/JS로 만든 정적 웹페이지입니다. 별도의 서버나 데이터베이스 없이 깃허브 페이지(GitHub Pages)에서 바로 호스팅할 수 있습니다.

## 폴더 구성

- `index.html` — 대시보드 페이지 (기본화면 / 초·중·고 / 연도별 변화 / 관리자)
- `data.json` — 학교 현황 데이터(원본). 페이지가 열릴 때 이 파일을 불러와 화면에 표시합니다.
- `data/` — 학교 현황 원본 엑셀 파일 보관 폴더 (나이스 학교현황 파일 등). `scripts/build_data.py`가 이 폴더 전체를 읽어 `data.json`을 다시 만듭니다.
- `scripts/build_data.py` — `data/` 폴더의 엑셀 파일들로 `data.json`을 재생성하는 스크립트.
- `.claude/launch.json` — (개발용) 로컬 미리보기 서버 설정. 배포에는 필요 없습니다.

## 로컬에서 미리보기

`data.json`을 `fetch`로 불러오기 때문에, `index.html`을 더블클릭해서 바로 열면(`file://`) 브라우저 보안 정책 때문에 데이터가 로드되지 않습니다. 반드시 간단한 로컬 서버를 통해 열어야 합니다.

```bash
cd /Users/hanro/jyny_ai/school_dashboard_web
python3 -m http.server 8000
```

이후 브라우저에서 `http://localhost:8000` 접속.

## 깃허브에 배포하기 (GitHub Pages)

1. 깃허브에서 새 저장소를 만듭니다 (예: `school-dashboard`).
2. 이 폴더 전체(`index.html`, `data.json` 포함)를 저장소에 올립니다.

   ```bash
   cd /Users/hanro/jyny_ai/school_dashboard_web
   git init
   git add index.html data.json data/ scripts/ README.md
   git commit -m "Initial dashboard"
   git branch -M main
   git remote add origin https://github.com/<계정명>/<저장소명>.git
   git push -u origin main
   ```

3. 깃허브 저장소 페이지에서 **Settings → Pages**로 이동합니다.
4. **Branch**를 `main`, 폴더를 `/ (root)`로 선택하고 저장합니다.
5. 잠시 후 `https://<계정명>.github.io/<저장소명>/` 주소로 접속하면 대시보드가 보입니다.

## 학교 현황 자료를 업데이트하면 반영되게 하기

이 사이트는 서버가 없는 정적 페이지이므로, 자료를 바꾼 뒤 **`data.json`을 다시 만들어서 깃허브에 커밋·푸시**해야 모든 방문자에게 반영됩니다. 두 가지 방법이 있습니다.

### 방법 A. `data/` 폴더 + 스크립트로 반영 (파일이 여러 개거나, 나이스 원본 파일을 그대로 쓸 때 추천)

`data/` 폴더가 원본 데이터의 기준입니다. 이 폴더에 파일을 추가·교체한 뒤 스크립트를 실행하면 `data.json`이 **`data/` 폴더 전체 내용을 기준으로 새로** 만들어집니다.

1. 새 학교 현황 엑셀 파일을 `data/` 폴더에 넣습니다 (나이스에서 내려받은 "학교현황" 원본 파일을 그대로 넣어도 되고, 관리자 페이지의 업로드 양식으로 만든 파일도 됩니다).
2. 스크립트를 실행합니다 (파이썬과 `openpyxl` 필요: `pip install openpyxl`).

   ```bash
   cd /Users/hanro/jyny_ai/school_dashboard_web
   python3 scripts/build_data.py
   ```

   실행 결과로 파일별 인식 개수와 경고(지역/학교급을 인식하지 못해 제외된 행)가 출력됩니다.
3. 바뀐 `data.json`(및 `data/`에 추가한 파일)을 커밋·푸시합니다.

   ```bash
   git add data.json data/
   git commit -m "Update school data"
   git push
   ```

### 방법 B. 관리자 페이지에서 업로드 (빠르게 몇 건만 확인하며 반영할 때)

1. 사이트 우측 상단 **관리자** 버튼 → 비밀번호 입력 후 로그인 (기본 비밀번호: `gwedu2026`, 관리자 페이지에서 변경 가능).
2. **학교 데이터 파일 추가**에서 엑셀(.xlsx) 파일을 선택 후 **저장** — 지금 보고 있는 브라우저에 반영(미리보기)됩니다.
   - 여러 파일을 한 번에 선택할 수 있습니다 (예: 초·중·고 파일 3개를 한 번에 선택).
   - 관리자 페이지의 업로드 양식뿐 아니라, **나이스(NEIS) 학교현황 원본 파일도 그대로 업로드**하면 자동으로 항목(학교급·지역·학급수·학생수 등)을 인식해서 반영합니다.
   - 필요하면 **데이터 관리** 표에서 학교를 직접 추가/수정/삭제할 수도 있습니다.
3. 결과가 원하는 대로 보이면 **웹사이트(깃허브)에 자료 반영하기** 카드의 **data.json 다운로드 (배포용)** 버튼을 클릭합니다.
4. 다운로드된 `data.json` 파일로, 저장소의 `data.json`을 덮어씁니다.
5. 변경 사항을 커밋하고 푸시합니다.

   ```bash
   cd /Users/hanro/jyny_ai/school_dashboard_web
   git add data.json
   git commit -m "Update school data"
   git push
   ```

두 방법 모두, 1~2분 후 배포된 사이트를 새로고침하면 모든 방문자에게 새 자료가 반영됩니다.

## 오프라인용 페이지 다운로드

관리자 페이지의 **오프라인용 페이지 다운로드** 카드에서 **오프라인용 HTML 파일 다운로드** 버튼을 누르면, 지금 화면에 표시된 자료가 그대로 포함된 단일 HTML 파일이 만들어집니다. 이 파일은 인터넷 연결이나 서버 없이 더블클릭만으로 열 수 있어, 발표·출장 등 오프라인 환경에서 대시보드를 보여줄 때 유용합니다.

## 관리자 비밀번호

기본 비밀번호는 `gwedu2026`입니다. 배포 전에 관리자 페이지에서 꼭 변경하세요. 다만 이 비밀번호는 브라우저에만 저장되며 서버 인증이 아니므로(정적 사이트 특성상), 페이지 소스에서 확인 가능한 수준의 보호임을 참고하세요.
