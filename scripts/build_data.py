#!/usr/bin/env python3
"""
data/ 폴더의 학교 현황 엑셀 파일들을 읽어 data.json을 다시 생성한다.

data/ 폴더에 파일을 추가·교체한 뒤 이 스크립트를 다시 실행하면 data.json이
data/ 폴더 내용 전체를 기준으로 새로 만들어진다 (data/ 폴더가 원본 데이터의
단일 기준이 된다). data.json을 깃허브에 커밋·푸시하면 배포된 웹페이지에도
반영된다 (README.md 참고).

지원 서식
  1) 나이스(NEIS) 학교현황 원본 파일 ("...초등학교현황...xlsx" 등) - 헤더 행에
     "학교코드" 칸이 있는 표 형태를 자동 인식해서 항목을 추출한다.
  2) 웹페이지 관리자 화면에서 내려받을 수 있는 업로드 양식(.xlsx) - 1행이
     UPLOAD_HEADERS와 정확히 같은 표.

사용법:
  python3 scripts/build_data.py
"""
import json
import re
import sys
import unicodedata
from pathlib import Path

import openpyxl

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
OUT_FILE = ROOT / "data.json"

REGION_ORDER = ["춘천시","원주시","강릉시","속초시","양양군","동해시","태백시","삼척시",
                "홍천군","횡성군","영월군","평창군","정선군","철원군","화천군","양구군","인제군","고성군"]
GRADE_COUNT = {"초": 6, "중": 3, "고": 3}
UPLOAD_HEADERS = ["기준연도","학교급","학교유형","지역","설립","학교명",
    "1학년 학급수","2학년 학급수","3학년 학급수","4학년 학급수","5학년 학급수","6학년 학급수",
    "1학년 학생수","2학년 학생수","3학년 학생수","4학년 학생수","5학년 학생수","6학년 학생수",
    "교사수"]


def short_region(r):
    return re.sub(r"(시|군)$", "", r)


def normalize_region(val):
    v = str(val or "").strip()
    if not v:
        return None
    if v in REGION_ORDER:
        return v
    for r in REGION_ORDER:
        if short_region(r) == v:
            return r
    return None


def normalize_level(val):
    v = str(val or "").strip()
    if v == "초" or v.startswith("초등"):
        return "초"
    if v == "중" or v.startswith("중학"):
        return "중"
    if v == "고" or v.startswith("고등"):
        return "고"
    return None


def level_from_filename(name):
    # macOS(APFS)는 파일명을 NFD(분해형)로 반환하므로, 코드에 적힌 NFC 리터럴과
    # 그냥 비교하면 한글이 일치하지 않는다. 비교 전에 NFC로 정규화한다.
    name = unicodedata.normalize("NFC", str(name or ""))
    if "초등학교" in name:
        return "초"
    if "중학교" in name:
        return "중"
    if "고등학교" in name:
        return "고"
    return None


def sheet_to_rows(ws):
    rows = []
    for row in ws.iter_rows(values_only=True):
        rows.append(list(row))
    return rows


def find_header_index(header, predicate):
    for i, h in enumerate(header):
        if predicate(str(h or "").strip()):
            return i
    return -1


def find_neis_header_row(rows):
    for i, r in enumerate(rows[:25]):
        if any(str(v or "").strip() == "학교코드" for v in r):
            return i
    return -1


def find_neis_year(rows):
    for r in rows[:25]:
        if str(r[0] or "").strip() == "기준년월":
            m = re.search(r"(\d{4})", str(r[1] or ""))
            if m:
                return int(m.group(1))
    return None


def to_number(val):
    try:
        if val is None or str(val).strip() == "":
            return 0
        n = float(val)
        return int(n) if n.is_integer() else n
    except (TypeError, ValueError):
        return 0


def extract_neis_records(rows, file_name, warnings):
    header_row_idx = find_neis_header_row(rows)
    if header_row_idx == -1:
        return None
    header = [str(h or "").strip() for h in rows[header_row_idx]]

    name_idx = find_header_index(header, lambda h: h == "학교")
    region_idx = find_header_index(header, lambda h: h == "자치구")
    est_idx = find_header_index(header, lambda h: h == "설립구분")
    if -1 in (name_idx, region_idx, est_idx):
        return None

    type_idx = find_header_index(header, lambda h: h == "고교유형")
    level_col_idx = find_header_index(header, lambda h: h == "학교급")
    staff_idx = find_header_index(header, lambda h: h.startswith("교직원수_교원_계"))
    code_idx = find_header_index(header, lambda h: h == "학교코드")
    grade_class_idx, grade_student_idx = [], []
    for g in range(1, 7):
        grade_class_idx.append(find_header_index(
            header, lambda h, g=g: "학급수" in h and f"{g}학년" in h and "주간" not in h and "야간" not in h and "특수" not in h))
        grade_student_idx.append(find_header_index(
            header, lambda h, g=g: "학생수" in h and f"{g}학년" in h and "주간" not in h and "야간" not in h and h.endswith("계")))

    default_level = level_from_filename(file_name)
    year = find_neis_year(rows) or 2024

    records = []
    for i in range(header_row_idx + 1, len(rows)):
        r = rows[i]
        name = str(r[name_idx] or "").strip() if name_idx < len(r) else ""
        if not name:
            continue
        level = None
        if level_col_idx != -1 and level_col_idx < len(r):
            level = normalize_level(r[level_col_idx])
        level = level or default_level
        if not level:
            warnings.append(f"[{file_name}] {i+1}행: 학교급 인식 불가 - 건너뜀 ({name})")
            continue

        region = normalize_region(r[region_idx] if region_idx < len(r) else None)
        if not region:
            warnings.append(f"[{file_name}] {i+1}행: 지역 인식 불가(\"{r[region_idx] if region_idx < len(r) else ''}\") - 건너뜀 ({name})")
            continue

        est = str(r[est_idx] or "-").strip() if est_idx < len(r) else "-"
        est = est or "-"
        school_type = str(r[type_idx] or "").strip() if type_idx != -1 and type_idx < len(r) else ""
        staff = to_number(r[staff_idx]) if staff_idx != -1 and staff_idx < len(r) else 0
        code_raw = r[code_idx] if code_idx != -1 and code_idx < len(r) else None
        code = str(code_raw).strip() if code_raw else f"NEIS-{level}-{year}-{i}"

        grade_count = GRADE_COUNT[level]
        classes = {"total": 0, "g1": 0, "g2": 0, "g3": 0, "g4": 0, "g5": 0, "g6": 0, "special": 0}
        students = {"total": 0, "g1": 0, "g2": 0, "g3": 0, "g4": 0, "g5": 0, "g6": 0, "male": 0, "female": 0}
        for g in range(1, 7):
            if g <= grade_count:
                ci = grade_class_idx[g - 1]
                si = grade_student_idx[g - 1]
                c = to_number(r[ci]) if ci != -1 and ci < len(r) else 0
                s = to_number(r[si]) if si != -1 and si < len(r) else 0
                classes[f"g{g}"] = c
                students[f"g{g}"] = s
        classes["total"] = sum(classes[f"g{g}"] for g in range(1, 7))
        students["total"] = sum(students[f"g{g}"] for g in range(1, 7))

        records.append({
            "region": region, "est": est, "name": name, "code": code,
            "type": school_type if level == "고" else "", "coed": "-",
            "level": level, "year": year, "staff": staff,
            "classes": classes, "students": students,
        })
    return records


def extract_template_records(rows, file_name, warnings):
    header = [str(h or "").strip() for h in rows[0]]
    if header[:len(UPLOAD_HEADERS)] != UPLOAD_HEADERS:
        return None
    idx = {h: i for i, h in enumerate(UPLOAD_HEADERS)}
    records = []
    for i in range(1, len(rows)):
        r = rows[i]
        if not r or all(v is None or str(v).strip() == "" for v in r):
            continue
        level = normalize_level(r[idx["학교급"]])
        region = normalize_region(r[idx["지역"]])
        name = str(r[idx["학교명"]] or "").strip()
        if not (level and region and name):
            warnings.append(f"[{file_name}] {i+1}행: 학교급/지역/학교명 확인 필요 - 건너뜀")
            continue
        year = int(to_number(r[idx["기준연도"]])) or 2024
        grade_count = GRADE_COUNT[level]
        classes = {"total": 0, "g1": 0, "g2": 0, "g3": 0, "g4": 0, "g5": 0, "g6": 0, "special": 0}
        students = {"total": 0, "g1": 0, "g2": 0, "g3": 0, "g4": 0, "g5": 0, "g6": 0, "male": 0, "female": 0}
        for g in range(1, 7):
            if g <= grade_count:
                classes[f"g{g}"] = to_number(r[idx[f"{g}학년 학급수"]])
                students[f"g{g}"] = to_number(r[idx[f"{g}학년 학생수"]])
        classes["total"] = sum(classes[f"g{g}"] for g in range(1, 7))
        students["total"] = sum(students[f"g{g}"] for g in range(1, 7))
        records.append({
            "region": region, "est": str(r[idx["설립"]] or "-").strip() or "-", "name": name,
            "code": f"TEMPLATE-{level}-{year}-{i}",
            "type": str(r[idx["학교유형"]] or "").strip() if level == "고" else "", "coed": "-",
            "level": level, "year": year, "staff": to_number(r[idx["교사수"]]),
            "classes": classes, "students": students,
        })
    return records


def main():
    if not DATA_DIR.is_dir():
        print(f"data 폴더가 없습니다: {DATA_DIR}", file=sys.stderr)
        sys.exit(1)

    files = sorted(DATA_DIR.glob("*.xlsx"))
    if not files:
        print(f"data 폴더에 .xlsx 파일이 없습니다: {DATA_DIR}", file=sys.stderr)
        sys.exit(1)

    all_records = []
    warnings = []
    for f in files:
        wb = openpyxl.load_workbook(f, data_only=True)
        ws = wb.worksheets[0]
        rows = sheet_to_rows(ws)
        records = extract_neis_records(rows, f.name, warnings)
        if records is None:
            records = extract_template_records(rows, f.name, warnings)
        if records is None:
            warnings.append(f"[{f.name}] 인식할 수 없는 서식이라 건너뜀")
            continue
        print(f"{f.name}: {len(records)}개교 추출")
        all_records.extend(records)

    # 같은 학교급·연도·지역·학교명이 여러 파일에 있으면 나중 파일 내용으로 갱신
    merged = {}
    for rec in all_records:
        key = (rec["level"], rec["year"], rec["region"], rec["name"])
        merged[key] = rec

    result = list(merged.values())
    result.sort(key=lambda r: (r["level"], r["year"], REGION_ORDER.index(r["region"]) if r["region"] in REGION_ORDER else 99, r["name"]))

    with open(OUT_FILE, "w", encoding="utf-8") as out:
        json.dump(result, out, ensure_ascii=False, indent=1)

    print(f"\n총 {len(result)}개교 -> {OUT_FILE}")
    by_level = {}
    for r in result:
        by_level[r["level"]] = by_level.get(r["level"], 0) + 1
    for lv, cnt in sorted(by_level.items()):
        print(f"  {lv}: {cnt}개교")

    if warnings:
        print(f"\n경고 {len(warnings)}건:")
        for w in warnings[:30]:
            print("  " + w)
        if len(warnings) > 30:
            print(f"  ... 외 {len(warnings) - 30}건")


if __name__ == "__main__":
    main()
