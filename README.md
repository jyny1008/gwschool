# 강원특별자치도 학교 현황 대시보드

순수 HTML/CSS/JS로 만든 정적 웹페이지입니다. 별도의 서버나 데이터베이스 없이 깃허브 페이지(GitHub Pages)에서 바로 호스팅할 수 있습니다.

## 폴더 구성

- `index.html` — 대시보드 페이지 (기본화면 / 초·중·고 / 연도별 변화 / 관리자)
- `data.json` — 학교 현황 데이터(원본). 페이지가 열릴 때 이 파일을 불러와 화면에 표시합니다.
- `data/` — 학교 현황 원본 엑셀 파일 보관 폴더 (나이스 학교현황 파일 등). `scripts/build_data.py`가 이 폴더 전체를 읽어 `data.json`을 다시 만듭니다.
- `scripts/build_data.py` — `data/` 폴더의 엑셀 파일들로 `data.json`을 재생성하는 스크립트.
- `.github/workflows/build-data.yml` — `data/` 폴더가 바뀌어 깃허브에 푸시되면 위 스크립트를 자동으로 실행해 `data.json`을 다시 커밋하는 깃허브 액션.
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
   git add index.html data.json data/ scripts/ .github/ README.md
   git commit -m "Initial dashboard"
   git branch -M main
   git remote add origin https://github.com/<계정명>/<저장소명>.git
   git push -u origin main
   ```

3. 깃허브 저장소 페이지에서 **Settings → Pages**로 이동합니다.
4. **Branch**를 `main`, 폴더를 `/ (root)`로 선택하고 저장합니다.
5. `data/` 폴더가 바뀔 때 `data.json`을 자동으로 다시 만드는 깃허브 액션을 쓰려면, **Settings → Actions → General → Workflow permissions**에서 **"Read and write permissions"**를 선택하고 저장합니다 (자세한 내용은 아래 "학교 현황 자료를 업데이트하면 반영되게 하기" 참고).
5. 잠시 후 `https://<계정명>.github.io/<저장소명>/` 주소로 접속하면 대시보드가 보입니다.

## 학교 현황 자료를 업데이트하면 반영되게 하기

이 사이트는 서버가 없는 정적 페이지이므로, 결국은 **`data.json`이 깃허브 저장소에 커밋·푸시**되어야 모든 방문자에게 반영됩니다. 아래 세 가지 방법 중 편한 것을 쓰면 됩니다. **방법 A와 C는 `data.json`을 직접 만들거나 다운로드할 필요 없이, 깃허브 액션(`.github/workflows/build-data.yml`)이 자동으로 만들어 줍니다.**

### 방법 A. `data/` 폴더에 파일을 넣고 깃허브에 올리기만 하면 자동 반영 (추천)

`data/` 폴더가 원본 데이터의 기준입니다. 이 폴더에 나이스 학교현황 원본 파일(또는 업로드 양식 파일)을 추가·교체해서 깃허브에 푸시하면(직접 `git push`를 하든, 깃허브 웹사이트에서 파일을 드래그해서 올리든 상관없습니다), **깃허브 액션이 자동으로 `scripts/build_data.py`를 실행해서 `data.json`을 다시 만들고 커밋**합니다. 로컬에서 스크립트를 실행하거나 `data.json`을 따로 만들 필요가 없습니다.

```bash
cd /Users/hanro/jyny_ai/school_dashboard_web
git add data/새파일.xlsx
git commit -m "Add school data"
git push
```

푸시 후 저장소의 **Actions** 탭에서 `Build data.json` 워크플로가 실행되는 것을 확인할 수 있습니다. 완료되면(보통 1분 이내) `data.json`이 자동으로 갱신된 커밋이 추가되고, 이어서 깃허브 페이지가 다시 배포됩니다.

> 이 자동화는 저장소에 `.github/workflows/build-data.yml`이 있어야 동작합니다. 저장소 **Settings → Actions → General**에서 Actions가 허용되어 있는지, **Workflow permissions**가 "Read and write permissions"로 되어 있는지 확인하세요 (그래야 액션이 `data.json`을 커밋할 수 있습니다).

### 방법 B. 관리자 페이지에서 깃허브 자동 저장 (파일 업로드만으로 반영, 터미널/깃 명령 불필요)

관리자 페이지에서 엑셀 파일을 올리면, 깃허브 저장소의 `data/` 폴더에 그 파일을 **직접 저장**할 수 있습니다. 이후 방법 A의 자동화가 이어서 `data.json`을 다시 만들어 배포합니다. 즉, 터미널이나 `git` 명령 없이 브라우저에서 업로드만으로 사이트에 반영할 수 있습니다.

1. 사이트 우측 상단 **관리자** 버튼 → 비밀번호 입력 후 로그인 (기본 비밀번호: `gwedu2026`, 관리자 페이지에서 변경 가능).
2. **깃허브에 자동 저장** 카드의 안내를 따라 깃허브 개인 액세스 토큰(fine-grained, 이 저장소만, Contents: Read and write 권한)을 발급받아 저장소(`owner/repo`)와 함께 등록합니다 (최초 1회만 하면 됩니다).
3. **학교 데이터 파일 추가**에서 엑셀(.xlsx) 파일을 선택합니다 (여러 파일 동시 선택 가능, 나이스 원본 파일도 그대로 인식됩니다).
4. **깃허브에 자동 저장** 카드의 **"방금 업로드한 파일을 깃허브 data 폴더에 저장"** 버튼을 클릭합니다. 파일이 저장소의 `data/` 폴더에 바로 커밋됩니다.
5. 1~2분 뒤 깃허브 액션이 `data.json`을 자동으로 다시 만들고, 배포된 사이트에 모든 방문자에게 반영됩니다.

> 토큰은 이 브라우저(기기)에만 저장됩니다. 공용/공유 컴퓨터에서는 사용을 피하고, 더 이상 쓰지 않을 때는 깃허브 설정에서 토큰을 바로 폐기(Revoke)하세요.

### 방법 C. 관리자 페이지 미리보기 + `data.json` 수동 업로드 (깃허브 토큰 없이 반영하고 싶을 때)

1. 관리자 로그인 후 **학교 데이터 파일 추가**에서 파일을 올리고 **저장**을 눌러, 지금 보고 있는 브라우저에 반영(미리보기)합니다.
   - 필요하면 **데이터 관리** 표에서 학교를 직접 추가/수정/삭제할 수도 있습니다.
2. 결과가 원하는 대로 보이면 **웹사이트(깃허브)에 자료 반영하기** 카드의 **data.json 다운로드 (배포용)** 버튼을 클릭합니다.
3. 다운로드된 `data.json` 파일로, 저장소의 `data.json`을 덮어씁니다.
4. 변경 사항을 커밋하고 푸시합니다.

   ```bash
   cd /Users/hanro/jyny_ai/school_dashboard_web
   git add data.json
   git commit -m "Update school data"
   git push
   ```

세 방법 모두, 배포까지 1~2분 정도 걸리며 이후 사이트를 새로고침하면 모든 방문자에게 새 자료가 반영됩니다.

## 오프라인용 페이지 다운로드

관리자 페이지의 **오프라인용 페이지 다운로드** 카드에서 **오프라인용 HTML 파일 다운로드** 버튼을 누르면, 지금 화면에 표시된 자료가 그대로 포함된 단일 HTML 파일이 만들어집니다. 이 파일은 인터넷 연결이나 서버 없이 더블클릭만으로 열 수 있어, 발표·출장 등 오프라인 환경에서 대시보드를 보여줄 때 유용합니다.

## 관리자 비밀번호

기본 비밀번호는 `gwedu2026`입니다. 배포 전에 관리자 페이지에서 꼭 변경하세요. 다만 이 비밀번호는 브라우저에만 저장되며 서버 인증이 아니므로(정적 사이트 특성상), 페이지 소스에서 확인 가능한 수준의 보호임을 참고하세요.
